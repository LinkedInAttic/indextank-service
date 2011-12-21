#!/usr/bin/python

from amazon_credential import AMAZON_USER, AMAZON_PASSWORD

from flaptor.indextank.rpc import WorkerManager as TWorkerManager
from nebu.models import Worker

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

import boto, time
import socket
from lib import flaptor_logging, mail
import rpc

IMAGE_ID = 'ami-c6fa07af'

logger = flaptor_logging.get_logger('WorkerMgr')

def logerrors(func):
    def decorated(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            logger.exception("Failed while executing %s", func.__name__)
            raise e
    return decorated


class WorkerManager:
    
    @logerrors
    def ec2_connection(self):
        return boto.connect_ec2(AMAZON_USER, AMAZON_PASSWORD)

    """ Return values for add_worker """
    WORKER_CREATION_FAILED = 0
    WORKER_CREATED = 1

    @logerrors
    def add_worker(self, instance_type):
        ''' table of instance_type -> available ram. '''
        AVAILABLE_RAM = {
            'm1.large': 7500,
            'm1.xlarge' : 15000,
            'm2.xlarge' : 17000,
            'm2.2xlarge' : 34000,
            'm2.4xlarge' : 68000,
        }
        if not instance_type in AVAILABLE_RAM:
            logger.error("instance type %s is not on AVAILABLE_RAM table. Choose another type or update the table.")
            return WorkerManager.WORKER_CREATION_FAILED

        logger.info("Creating new worker using image %s, using a %s instance", IMAGE_ID, instance_type)
        conn = self.ec2_connection()
        res = conn.run_instances(image_id=IMAGE_ID, security_groups=['indextank-worker'], instance_type=instance_type, placement='us-east-1a')
        if len(res.instances) == 0:
            logger.error("New instance failed")
            return WorkerManager.WORKER_CREATION_FAILED
        else:
            w = Worker()
            w.status = Worker.States.created
            w.instance_name = res.instances[0].id
            w.ram = AVAILABLE_RAM[instance_type]
            w.save()
            '''
            UNCOMMENT ME WHEN WE UPDATE BOTO'S VERSION
            conn.create_tags(res, {'Name': 'Worker:%i' % (w.id)})
            '''
            mail.report_new_worker(w)
            return WorkerManager.WORKER_CREATED
        
    """ Return values for update_status """
    WORKER_CONTROLLABLE = 0
    WORKER_UPDATING = 1
    WORKER_INITIALIZING = 2
    WORKER_NOT_READY = 3
    
    @logerrors
    def update_status(self, instance_name):
        worker = Worker.objects.filter(instance_name=instance_name)[0]
        if worker.status == Worker.States.created:
            conn = self.ec2_connection()
            reservations = conn.get_all_instances([instance_name])
            instance = reservations[0].instances[0]
            if instance.state == 'running':
                logger.info('Worker %s is now initializing: %s', worker.instance_name, instance.public_dns_name)
                worker.status = Worker.States.initializing
                worker.lan_dns = instance.private_dns_name
                worker.wan_dns = instance.public_dns_name
                worker.save()
                mail.report_new_worker(worker)
            else:
                logger.debug('Worker %s is still reporting as %s', worker.instance_name, instance.state)
                return WorkerManager.WORKER_NOT_READY
    
        if worker.status == Worker.States.initializing:
            logger.debug('Trying to update controller on %s', worker.instance_name)
            if self.update_worker(worker.lan_dns):
                worker.status = Worker.States.updating
                worker.save()
                logger.info('Worker %s is now updating', worker.instance_name)
                return WorkerManager.WORKER_UPDATING
            else:
                return WorkerManager.WORKER_INITIALIZING

        if worker.status == Worker.States.updating:
            logger.debug('Checking if controller is up on %s', worker.instance_name)
            try:
                controller = rpc.getThriftControllerClient(worker.lan_dns)
                controller.get_worker_load_stats()
                worker.status = Worker.States.controllable
                worker.save()
                logger.info('Worker %s is now controllable', worker.instance_name)
                return WorkerManager.WORKER_CONTROLLABLE
            except Exception, e:
                if isinstance(e, TTransport.TTransportException) and e.type == TTransport.TTransportException.NOT_OPEN:
                    logger.info('Controller on worker %s not responding yet.', worker.lan_dns)
                else:
                    logger.exception('Unexpected exception while checking worker %s', worker.lan_dns)
                return WorkerManager.WORKER_UPDATING

    @logerrors
    def update_worker(self, dns):
        try:
            controller = rpc.getThriftControllerClient(dns)
            host = socket.gethostbyname_ex(socket.gethostname())[0]
            retcode = controller.update_worker(host)
            if retcode == 0:
                try:
                    logger.debug('Worker %s updated. Restarting...', dns)
                    controller.restart_controller()
                    logger.warn("Restart controller didn't throw an exception. Did it restart?")
                except TTransport.TTransportException:
                    # restart will always fail
                    pass 
        except Exception, e:
            if isinstance(e, TTransport.TTransportException) and e.type == TTransport.TTransportException.NOT_OPEN:
                logger.info('Controller on worker %s not responding yet.', dns)
            else:
                logger.exception('Unexpected exception while updating worker %s', dns)
            return False
        return True

    @logerrors
    def remove_worker(self,instance_name):
        print 'removing host'
        return 1


    # TODO this method should be called periodically
    @logerrors
    def poll_controllers(self):
        for worker in Worker.objects.all():
            controller = rpc.getThriftControllerClient(worker.lan_dns)
            if controller:
                stats = controller.stats()
                print controller,stats
                # TODO update worker stats.
            else:
                print "could not connect to controller on %s" % worker
    

if __name__ == "__main__":
    handler = WorkerManager()
    processor = TWorkerManager.Processor(handler)
    transport = TSocket.TServerSocket(rpc.worker_manager_port)
    tfactory  = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
    print 'Starting the server...'
    server.serve()
    print 'done.'
 

