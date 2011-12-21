#!/usr/bin/python

import systemutils

import rpc
from lib import flaptor_logging
from lib.monitor import Monitor

from nebu.models import Index, Worker, Deploy
from flaptor.indextank.rpc.ttypes import IndexerStatus, NebuException 
import datetime


class DeployPingMonitor(Monitor):
    def __init__(self):
        super(DeployPingMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 5
        self.fatal_failure_threshold = 20
        self.period = 30
        
    def iterable(self):
        return (d for d in Deploy.objects.all().select_related('index') if d.is_writable())
        
    def monitor(self, deploy):
        deploy.index # so that it fails if the index foreign key is broken 
        try:
            client = rpc.getThriftIndexerClient(deploy.worker.lan_dns, int(deploy.base_port), 5000)
            client.ping()
            return True
        except Exception:
            self.logger.exception("Failed to ping deploy %s for index %s", deploy.id, deploy.index.code)
            self.err_msg = self.describe_error()
            return False
            #'A writable deploy [%d] is failing to answer to ping.\n\n%s\n\nEXCEPTION: %s : %s\ntraceback:\n%s' % (deploy.id, index.get_debug_info(), exc_type, exc_value, ''.join(format_tb(exc_traceback)))
        
    def alert_title(self, deploy):
        return 'Unable to ping index %s deploy id %d' % (deploy.index.code, deploy.id)
    
    def alert_msg(self, deploy):
        return 'A writable deploy [%d] is failing to answer to ping.\n\n%s\n\n%s' % (deploy.id, deploy.index.get_debug_info(), self.err_msg)

class IndexSizeMonitor(Monitor):
    def __init__(self):
        super(IndexSizeMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 2
        self.fatal_failure_threshold = 5
        self.period = 120
        
    def iterable(self):
        return (i for i in Index.objects.all() if i.is_ready() and not i.deleted)
        
    def monitor(self, index):
        try:
            self.logger.debug("Fetching size for index %s" , index.code)
            searcher = rpc.get_searcher_client(index, 10000)
            current_size = searcher.size()
            Index.objects.filter(id=index.id).update(current_docs_number=current_size)
            self.logger.info("Updated size for index %s: %d" , index.code, index.current_docs_number)
            return True
        except Exception:
            self.logger.exception("Failed to update size for index %s" , index.code)
            self.err_msg = self.describe_error()
            return False
        
    def alert_title(self, index):
        return "Failed to fetch size for index %s" % index.code
    
    def alert_msg(self, index):
        return 'An IndexEngine is failing when attempting to query its size via thrift.\n\n%s\n\n%s' % (index.get_debug_info(), self.err_msg)

class ServiceDeploys(Monitor):
    def __init__(self):
        super(ServiceDeploys, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 2
        
    def monitor(self, object):
        try:
            rpc.get_deploy_manager().service_deploys()
            return True
        except NebuException, e:
            self.nebu_e = e
            return False
        
    def alert_title(self, object):
        return "Nebu exception"
    
    def alert_msg(self, object):
        return self.nebu_e.message

class ServiceWorkers(Monitor):
    def __init__(self):
        super(ServiceWorkers, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 30
        
    def iterable(self):
        return (w for w in Worker.objects.all() if not w.is_ready())
        
    def monitor(self, worker):
        try:
            rpc.getThriftWorkerManagerClient('workermanager').update_status(worker.instance_name)
            return True
        except NebuException, e:
            self.nebu_e = e
            return False
        
    def alert_title(self, worker):
        return "Nebu exception for worker id %d" % worker.id
    
    def alert_msg(self, worker):
        return "INFO ABOUT THE WORKER\ninstance id: %s\nwan_dns: %s\nlan_dns: %s\n\nError message: " % (worker.instance_name, worker.wan_dns, worker.lan_dns, self.nebu_e.message)

class WorkerFreeDiskMonitor(Monitor):
    def __init__(self, threshold):
        super(WorkerFreeDiskMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 60
        self.threshold = threshold
        
    def get_fs_sizes(self, worker):
        controller = rpc.get_worker_controller(worker)
        worker_stats = controller.get_worker_mount_stats()
        return worker_stats.fs_sizes.items()
    
    def iterable(self):
        # generates a list of pairs worker,filesystem with each filesystem in each worker
        return [(w,fs) for w in Worker.objects.all() for fs in self.get_fs_sizes(w) if w.is_ready()]
        
    def monitor(self, info):
        worker, (fs, (used, available)) = info
        self.logger.debug('Checking free space on %s for worker %s', fs, worker.wan_dns)

        ratio = float(available) / (available + used)
        return ratio * 100 > self.threshold
        
    def alert_title(self, info):
        worker, (fs, _) = info
        return 'Filesystem %s free space below %d%% for worker id %d' % (fs, self.threshold, worker.id)
    
    def alert_msg(self, info):
        worker, (fs, (used, available)) = info
        ratio = float(available) / (available + used)
        return 'Worker %d\nFilesystem mounted on %s has only %d%% of available space (%d free of %d)\n\nINFO ABOUT THE WORKER\ninstance id: %s\nwan_dns: %s\nlan_dns: %s' % (worker.id, fs, (ratio * 100), available, used, worker.instance_name, worker.wan_dns, worker.lan_dns)

class FrontendFreeDiskMonitor(Monitor):
    def __init__(self, threshold):
        super(FrontendFreeDiskMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 60
        self.threshold = threshold
        
    
    def iterable(self):
        # generates a list of pairs worker,filesystem with each filesystem in each worker
        return [fs for fs in systemutils.get_available_sizes().items()]
        
    def monitor(self, info):
        fs, (used, available) = info
        self.logger.debug('Checking free space on %s for the frontend', fs)

        ratio = float(available) / (available + used)
        return ratio * 100 > self.threshold
        
    def alert_title(self, info):
        fs, _ = info
        return 'Filesystem %s free space below %d%% for FRONTEND machine' % (fs, self.threshold)
    
    def alert_msg(self, info):
        fs, (used, available) = info
        ratio = float(available) / (available + used)
        return 'Frontend\nFilesystem mounted on %s has only %d%% of available space (%d free of %d)' % (fs, (ratio * 100), available, used)

class IndexStartedMonitor(Monitor):
    def __init__(self):
        super(IndexStartedMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 60
    
    def iterable(self):
        return (i for i in Index.objects.all() if not i.is_ready() and not i.is_hibernated() and not i.deleted)
        
    def monitor(self, index):
        return datetime.datetime.now() - index.creation_time < datetime.timedelta(minutes=5)
        
    def alert_title(self, index):
        return 'Index %s hasn\'t started in at least 5 minutes' % (index.code)
    
    def alert_msg(self, index):
        return 'The following index hasn\'t started in more than 5 minutes:\n\n%s' % (index.get_debug_info())

class MoveIncompleteMonitor(Monitor):
    def __init__(self):
        super(MoveIncompleteMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 360
    
    def iterable(self):
        return Deploy.objects.filter(status=Deploy.States.moving)
        
    def monitor(self, deploy):
        return datetime.datetime.now() - deploy.timestamp < datetime.timedelta(hours=4)
        
    def alert_title(self, deploy):
        return 'Index %s has been moving for over 4 hours' % (deploy.index.code)
    
    def alert_msg(self, deploy):
        return 'The following index has been moving for more than 4 hours:\n\n%s' % (deploy.index.get_debug_info())


class RecoveryErrorMonitor(Monitor):
    '''
        Pings RECOVERING indexes, to find out about recovery errors (status=3).
    '''

    def __init__(self):
        super(RecoveryErrorMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 360

    def iterable(self):
        return Deploy.objects.filter(status=Deploy.States.recovering)

    def monitor(self, deploy):
        # get the current recovery status
        indexer = rpc.getThriftIndexerClient(deploy.worker.lan_dns, int(deploy.base_port), 10000)
        indexer_status = indexer.getStatus()

        # complain only if an error arised
        return indexer_status != IndexerStatus.error
        

    def alert_title(self, deploy):
        return 'Recovery failed for index %s' % (deploy.index.code)
    
    def alert_msg(self, deploy):
        return 'The following index has a recovering deploy that failed:\n\n%s' % (deploy.index.get_debug_info())

class DeployInitializedMonitor(Monitor):
    def __init__(self):
        super(DeployInitializedMonitor, self).__init__(pagerduty_email='index-monitor@flaptor.pagerduty.com')
        self.failure_threshold = 1
        self.period = 20
    
    def iterable(self):
        return Deploy.objects.filter(status=Deploy.States.initializing)
        
    def monitor(self, deploy):
        return datetime.datetime.now() - deploy.timestamp < datetime.timedelta(seconds=20)
        
    def alert_title(self, deploy):
        return 'Deploy %d has been initializing for over 20 seconds' % (deploy.id)
    
    def alert_msg(self, deploy):
        return 'A deploy has been started more than 20 seconds ago (i.e. startIndex.sh has been executed) and it\'s still not responding to its thrift interface.\n\nDeploy id: %d\n\nIndex info:\n%s' % (deploy.id, deploy.index.get_debug_info())

if __name__ == '__main__':
    DeployPingMonitor().start()
    IndexSizeMonitor().start()
    ServiceDeploys().start()
    ServiceWorkers().start()
    WorkerFreeDiskMonitor(15).start()
    WorkerFreeDiskMonitor(10).start()
    WorkerFreeDiskMonitor(5).start()
    FrontendFreeDiskMonitor(15).start()
    FrontendFreeDiskMonitor(10).start()
    FrontendFreeDiskMonitor(5).start()
    IndexStartedMonitor().start()
    MoveIncompleteMonitor().start()
    RecoveryErrorMonitor().start()
    DeployInitializedMonitor().start()

