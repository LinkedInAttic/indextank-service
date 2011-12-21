
from threading import Thread
from traceback import format_tb
import time, datetime
import sys
import shelve

from django.core.mail import send_mail

from lib import flaptor_logging

try:
    ENV=open('/data/env.name').readline().strip()
except Exception:
    ENV='PROD+EXC'

#helper functions
def is_prod():
    return ENV == 'PROD' or ENV == 'QoS_Monitor'

def env_name():
    if ENV == 'PROD':
        return 'PRODUCTION'
    elif ENV == 'QoS_Monitor':
        return 'QoS_Monitor'
    else:
        return ENV

class Monitor(Thread):
    def __init__(self, pagerduty_email='api-monitor@flaptor.pagerduty.com'):
        super(Monitor, self).__init__()
        self.name = self.__class__.__name__
        self.statuses = shelve.open('/data/monitor-%s.shelf' % self.name)
        self.logger = flaptor_logging.get_logger(self.name)
        self.failure_threshold = 1
        self.fatal_failure_threshold = 0
        self.severity = 'WARNING'
        self.title_template = '%s::%s: [%s] %s'
        self.pagerduty_email = pagerduty_email
        
    def iterable(self):
        return [None]

    def run(self):
        self.step = 1
        while True:
            starttime = int(time.time())
            try:
                self.logger.info("running cycle  %d", self.step)
                for object in self.iterable():
                    self._monitor(object)
                self.report_ok("unexpected error in monitor cycle")
                self.clean()
            except Exception:
                self.logger.exception("Unexpected error while executing cycle")
                self.report_bad("unexpected error in monitor cycle", 1, 0, 'UNEXPECTED ERROR IN THE CYCLE OF %s\n\n%s' % (self.name, self.describe_error()))
            self.step += 1
            self.statuses.sync()
            time.sleep(max(0, self.period - (int(time.time()) - starttime)))
            
    def clean(self):
        for title, status in self.statuses.items():
            if not status['working']:
                if status['last_update'] != self.step:
                    self.report_ok(title)
            else:
                del self.statuses[title] 
                
            
    def _monitor(self, object):
        try:
            if self.monitor(object):
                self.report_ok(str(self.alert_title(object)))
            else:
                self.report_bad(str(self.alert_title(object)), self.failure_threshold, self.fatal_failure_threshold, self.alert_msg(object))
            self.report_ok("unexpected error in monitor")
        except Exception, e:
            self.logger.exception("Unexpected error while executing monitor. Exception is: %s" % (e))
            message = 'UNEXPECTED ERROR IN THE MONITORING OF %s FOR TITLE: %s\n\n%s' % (self.name, self.alert_title(object), self.describe_error())
            self.report_bad("unexpected error in monitor", 1, 'WARNING', message)
        
    def describe_error(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        return 'EXCEPTION: %s : %s\ntraceback:\n%s' % (exc_type, exc_value, ''.join(format_tb(exc_traceback)))
        
    def update_status(self, key, **kwargs):
        self.statuses[key] = kwargs
    
    def send_alert(self, title, message, severity):
        try:
            if is_prod():
                if severity == 'FATAL':
                    name = 'FATAL ALERT (%s)' % env_name()
                else:
                    name = 'ALERT (%s)' % env_name()
            else:
                name = '%s test alert' % ENV

            title = self.title_template % (ENV, self.name, severity, title)
            message += '\n\n--------SENT AT ' + str(datetime.datetime.now())
            to = ['alerts@indextank.com']
            if severity == 'FATAL' and is_prod(): 
                to.append('alerts+fatal@indextank.com')
                to.append(self.pagerduty_email)
            send_mail(title, message, '"%s" <alerts@flaptor.com>' % name, to, fail_silently=False)
            self.logger.info('Sending alert for title: %s\n============\n%s', title, message)
        except Exception, e:
            self.logger.exception("Unexpected error while sending alerts. Exception is: %s" % (e))
    
    def report_ok(self, title):
        if title in self.statuses and not self.statuses[title]['working'] and (self.statuses[title]['alerted'] or self.statuses[title]['alerted_fatal']):
            # it has just been resolved
            self.send_alert(title, 'The problem is no longer reported. The last message was:\n %s' % (self.statuses[title]['message']), self.severity)
        if title in self.statuses:
            del self.statuses[title]
    
    def report_bad(self, title, threshold, fatal_threshold, message):
        if title in self.statuses and not self.statuses[title]['working']:
            # this object had already failed, let's grab the first step in which it failed
            first_failure = self.statuses[title]['first_failure']
            has_alerted = self.statuses[title]['alerted']
            has_alerted_fatal = self.statuses[title]['alerted_fatal']
        else:
            # this object was fine, first failure is now             
            first_failure = self.step
            has_alerted = False
            has_alerted_fatal = False

        
        should_alert = self.step - first_failure + 1 >= threshold
        should_alert_fatal = fatal_threshold > 0 and self.step - first_failure + 1 >= fatal_threshold

        if should_alert_fatal:
            if not has_alerted_fatal:
                has_alerted_fatal = True
                if is_prod():
                    self.send_alert(title, 'A new problem on IndexTank has been detected:\n %s' % (message), 'FATAL')
            else:
                self.logger.info('Fatal error was found but alert has already been sent')
        elif should_alert:
            if not has_alerted:
                has_alerted = True
                self.send_alert(title, 'A new problem on IndexTank has been detected:\n %s' % (message), self.severity)
            else:
                self.logger.info('Error was found but alert has already been sent')

        # save current state of the object (is_failed, message, first_failure, last_update)
        self.update_status(title, working=False, last_update=self.step, message=message, first_failure=first_failure, alerted=has_alerted, alerted_fatal=has_alerted_fatal)
