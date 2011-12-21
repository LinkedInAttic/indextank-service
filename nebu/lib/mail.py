from django.core.mail import send_mail

try:
    ENV=open('/data/env.name').readline().strip()
except Exception:
    ENV='PROD+EXC'

def _no_fail(method, *args, **kwargs):
    def decorated(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception, e:
            print e
            return
    return decorated



@_no_fail
def report_payment_data(account):
    activity_report = 'An Account has entered payment data\n'
    activity_report += '---------------------------\n'
    activity_report += 'Plan: ' + account.package.name + '\n'
    activity_report += 'Email: ' + account.user.email + '\n'
    activity_report += 'API KEY: ' + account.apikey + ''
    
    report_activity('Payment Data for ' + account.package.name + ' Account (' + account.user.email + ')', activity_report)

@_no_fail
def report_new_account(account):
    activity_report = 'A new Account was created\n'
    activity_report += '---------------------------\n'
    activity_report += 'Plan: ' + account.package.name + '\n'
    activity_report += 'Email: ' + account.user.email + '\n'
    activity_report += 'API KEY: ' + account.apikey + ''
    
    report_activity('New ' + account.package.name + ' Account (' + account.user.email + ')', activity_report)

@_no_fail
def report_new_index(index):
    activity_report = 'A new Index was created\n'
    activity_report += '---------------------------\n'
    activity_report += 'Plan: ' + index.account.package.name + '\n'
    activity_report += 'User Email: ' + index.account.user.email + '\n'
    activity_report += 'Index Name: ' + index.name + ''
    
    report_activity('Index activity (' + index.code + ')', activity_report, 'l')

@_no_fail
def report_new_deploy(deploy):
    activity_report = 'A new Deploy is now controllable\n'
    activity_report += '---------------------------\n'
    activity_report += 'Plan: ' + deploy.index.account.package.name + '\n'
    activity_report += 'User Email: ' + deploy.index.account.user.email + '\n'
    activity_report += 'Index Name: ' + deploy.index.name + '\n'
    activity_report += 'Worker:  #' + str(deploy.worker.id) + '\n'
    activity_report += ('Deploy:  %r' % deploy) + '\n'
    activity_report += ('Container Index:  %r' % deploy.index) + '\n'
    
    report_activity('Index activity (' + deploy.index.code + ')', activity_report, 'l')

@_no_fail
def report_delete_index(index):
    activity_report = 'An Index has been deleted\n'
    activity_report += '---------------------------\n'
    activity_report += 'Plan: ' + index.account.package.name + '\n'
    activity_report += 'User Email: ' + index.account.user.email + '\n'
    activity_report += 'Index Name: ' + index.name + '\n'
    
    report_activity('Index activity (' + index.code + ')', activity_report, 'l')

@_no_fail
def report_new_worker(worker):
    activity_report = 'A new Worker was created\n'
    activity_report += '---------------------------\n'
    activity_report += repr(worker)

    report_activity('New Worker (%d)' % (worker.pk), activity_report, 't')

@_no_fail
def report_automatic_redeploy(deploy, initial_xmx, new_xmx):
    activity_report = 'Automatic redeploy.\n'
    activity_report += '---------------------------\n'
    activity_report += 'initial xmx value: %d\n' % (initial_xmx)
    activity_report += 'new xmx value: %d\n' % (new_xmx)
    activity_report += repr(deploy)

    report_activity('Automatic redeploy', activity_report, 't')

@_no_fail
def report_activity(subject, body, type='b'):
    if type == 'b':
        mail_to = 'activity@indextank.com'
    elif type == 't':
        mail_to = 'activitytech@indextank.com'
    elif type == 'l':
        mail_to = 'lowactivity@indextank.com'
    else:
        raise Exception('Wrong report type')
    
    send_mail(ENV + ' - ' + subject, body, 'IndexTank Activity <activity@flaptor.com>', [mail_to], fail_silently=False)
