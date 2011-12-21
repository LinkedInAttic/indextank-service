#!/usr/bin/python

from flaptor.indextank.rpc import DeployManager as TDeployManager
from flaptor.indextank.rpc.ttypes import IndexerStatus, NebuException
from nebu.models import Worker, Deploy, Index, IndexConfiguration, Service

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from lib import flaptor_logging, mail
import simplejson as json
import rpc
import sys
import random
from traceback import format_tb
from django.db import transaction
from datetime import datetime, timedelta

logger = flaptor_logging.get_logger('DeployMgr')

INITIAL_XMX = 100
INITIAL_XMX_THRESHOLD = 1000
MAXIMUM_PARALLEL_MOVES = 10
timeout_ms = 1000

def logerrors(func):
    def decorated(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            logger.exception("Failed while executing %s", func.__name__)
            raise e
    return decorated


class DeployManager:
    '''
        Move index from A to B:
            A.Flush {
               switch
               make hardlink copy
            }
        Rsync A/Flushed -> B
        B.Start_Recovery
        Index to A and B
        Wait until B.Finished_Recovery
        Direct index ad search to B
        Kill and delete A
    '''
    
    @logerrors
    def __find_best_worker(self, required_ram):
        '''
            finds the 'best' worker to use for a deploy requiring 'required_ram'
            
            constraints:
            * the worker can accomodate 'required_ram'
            * the worker is not in 'decomissioning' state
            
            for all those workers that comply to the above constraint, pick one considering:
            * workers in 'controllable' state are better than other workers
            * to choose between 2 workers, having less ram available is better

            if there is NO worker matching the constraints, this method will try to create a new worker
        '''


        # make sure at least 1 worker matches the constraints
        workers = Worker.objects.exclude(status=Worker.States.decommissioning).exclude(status=Worker.States.dying).exclude(status=Worker.States.dead)
        
        should_create_worker = True
        for worker in workers:
            used = self.__get_total_ram(worker)
            available = worker.get_usable_ram() - used
            if available > required_ram:
                # found one that could accomodate 'required_ram' .. no need to look further.
                should_create_worker = False
                break

        if should_create_worker:
            # create a new worker. it will be available on next loop iteration
            wm_client = rpc.getThriftWorkerManagerClient('workermanager')
            wm_client.add_worker('m2.xlarge')
            

        # OK, either there were workers that could accomodate 'required_ram', or we just created one.
        # find the best

        # first try only controllable workers
        # this way the deploy will be available FASTER
        workers = Worker.objects.filter(status=Worker.States.controllable)

        for i in range(2):
            best_worker = None
            best_ram = 1000000 # we should bump this number when we get workers with ram > 1TB
            for worker in workers:
                used = self.__get_total_ram(worker) 
                available = worker.get_usable_ram() - used
                if available > required_ram and available < best_ram:
                    best_ram = available
                    best_worker = worker
            
            if best_worker is not None:
                return best_worker
           
            # need to try again. let workers be everything but decomissioning, dying or dead ones.
            workers = Worker.objects.exclude(status=Worker.States.decommissioning).exclude(status=Worker.States.dying).exclude(status=Worker.States.dead)
       
        # tried only controllable, and everything .. still not found
        raise Exception('Second iteration and no suitable worker. Something is wrong...')

    def __get_total_ram(self, worker):
        return sum(d.total_ram() for d in worker.deploys.all())

    
    """ Return values for start_index """
    INDEX_ALREADY_RUNNING = 0
    WORKER_NOT_READY_YET = 1
    INDEX_INITIALIZING = 2
    INDEX_RECOVERING = 4
    INDEX_CONTROLLABLE = 3
    INDEX_MOVE_REQUESTED = 5
    INDEX_MOVING = 6
    INDEX_MOVED = 7
    
    def service_deploys(self):
        error_list = []

        for index in Index.objects.filter(deploys__isnull=True).exclude(status=Index.States.hibernated).exclude(status=Index.States.hibernate_requested).exclude(deleted=True):
            try:
                self._create_new_deploy(index)
            except Exception:
                logger.exception('Failed to service index %s [%s]', index.name, index.code)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_list.append('Failed to service index\n\n%s\n\nEXCEPTION: %s : %s\ntraceback:\n%s' % (index.get_debug_info(), exc_type, exc_value, ''.join(format_tb(exc_traceback))))
            
        for index in Index.objects.filter(deploys__isnull=True, deleted=True):
            index.delete()

        for index in Index.objects.filter(deleted=True):
            index.deploys.all().update(status=Deploy.States.decommissioning)
            
        for index in Index.objects.filter(status=Index.States.hibernate_requested):
            self._hibernate_index(index)


        for worker in Worker.objects.filter(status=Worker.States.dying):
            deploys = worker.deploys.all()
            
            if deploys:
                for deploy in deploys:
                    deploy.dying = True
                    deploy.save()
            else:
                worker.status = Worker.States.dead
                worker.save()
                
        deploys = Deploy.objects.select_related('parent', 'index', 'index__configuration', 'index__account__package', 'worker').all()
        
        for deploy in deploys:
            try:
                if deploy.dying:
                    self._service_dying_deploy(deploy)
                else:
                    self._service_deploy(deploy)
                    
            except Exception:
                logger.exception('Failed to service deploy %s of index %s [%s]', deploy.id, deploy.index.name, deploy.index.code)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_list.append('Failed to service deploy %s for index\n\n%s\n\nEXCEPTION: %s : %s\ntraceback:\n%s' % (deploy.id, deploy.index.get_debug_info(), exc_type, exc_value, ''.join(format_tb(exc_traceback))))
        
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error_list.append('Failed to service deploy %s for index\n\n%s\n\nEXCEPTION: %s : %s\ntraceback:\n%s' % (deploy.id, deploy.index.get_debug_info(), exc_type, exc_value, ''.join(format_tb(exc_traceback))))
            
        if error_list:
            raise NebuException('Deploy manager failed to service some indexes:\n---\n' + '\n---\n'.join(error_list))

    def _get_xmx(self, index):
        if index.current_docs_number < INITIAL_XMX_THRESHOLD:
            config = index.configuration.get_data()
            return config.get('initial_xmx', INITIAL_XMX)
        else:
            return index.configuration.get_data()['xmx']

    def _get_bdb(self, index):
        return index.configuration.get_data().get('bdb_cache',0)

    def _create_new_deploy(self, index, parent=None):
        '''
          Creates a deploy, but doesn't start it
        '''
        if parent:
            assert(parent.index == index)
        logger.debug('Creating new deploy for Index "%s" (%s).', index.name, index.code)

        xmx = self._get_xmx(index)
        bdb = self._get_bdb(index)
        
        worker = self.__find_best_worker(xmx)

        deploy = Deploy()
        deploy.parent = parent
        deploy.base_port = 0
        deploy.worker = worker
        deploy.index = index
        deploy.status = Deploy.States.created
        deploy.effective_xmx = xmx
        deploy.effective_bdb = bdb
        if Index.objects.filter(id=index.id).count() > 0:
            deploy.save()
            logger.info('Deploy %s:%d created for index "%s" (%s).', deploy.worker.instance_name, deploy.base_port, index.name, index.code)
        else:
            logger.error('Deploy %s:%d was NOT created for index "%s" (%s) since the index was deleted.', deploy.worker.instance_name, deploy.base_port, index.name, index.code)


    def _service_deploy(self, deploy):
        # Handle all decommissioning deploys including those for deleted indexes
        if deploy.status == Deploy.States.decommissioning:
            self._handle_decommissioning(deploy)
        # Only handle states if the index is not deleted
        elif not deploy.index.deleted:
            if deploy.status == Deploy.States.moving:
                self._handle_moving(deploy)
            elif deploy.status == Deploy.States.move_requested:
                self._handle_move_requested(deploy)
            elif deploy.status == Deploy.States.controllable:
                self._handle_controllable(deploy)
            elif deploy.status == Deploy.States.recovering:
                self._handle_recovering(deploy)
            elif deploy.status == Deploy.States.initializing:
                self._handle_initializing(deploy)
            elif deploy.status == Deploy.States.created:
                self._handle_created(deploy)
            else:
                logger.error('Unknown deploy state %s for deploy %s. Will do nothing.' % (deploy.status, deploy))
        

    def _service_dying_deploy(self, deploy):
        deploy = Deploy.objects.get(id=deploy.id)
        if deploy.status in [Deploy.States.decommissioning, Deploy.States.initializing, Deploy.States.created, Deploy.States.moving] :
            self._handle_dying_killable(deploy)
        elif deploy.status in [Deploy.States.move_requested, Deploy.States.controllable]:
            self._handle_dying_controllable(deploy)
        elif deploy.status == Deploy.States.recovering:
            self._handle_dying_recovering(deploy)
        else:
            logger.error('Unknown deploy state %s for deploy %s. Will do nothing.' % (deploy.status, deploy))

    def _handle_move_requested(self, deploy):
        if Deploy.objects.filter(status=Deploy.States.moving).count() < MAXIMUM_PARALLEL_MOVES:
            self._create_new_deploy(deploy.index, deploy)
            deploy.update_status(Deploy.States.moving)
        else:
            logger.warn("Too many parallel moves. Waiting to move deploy %s for index %s", deploy, deploy.index.code)

    def _handle_controllable(self, deploy):
        should_have_xmx = self._get_xmx(deploy.index)
        if deploy.effective_xmx < should_have_xmx:
            logger.info("Requesting move. Effective XMX (%dM) was smaller than needed (%dM) for deploy %s for index %s", deploy.effective_xmx, self._get_xmx(deploy.index), deploy, deploy.index.code)
            deploy.update_status(Deploy.States.move_requested)
            mail.report_automatic_redeploy(deploy, deploy.effective_xmx, should_have_xmx)

    def _handle_dying_controllable(self, deploy):
        # Create a new deploy for the index with no parent
        if deploy.index.status != Index.States.hibernate_requested:
            self._create_new_deploy(deploy.index)
        
        # Remove the deploy
        self._delete_deploy(deploy)

    def _handle_dying_recovering(self, deploy):
        logger.info('deleting recovering deploy %s due to dying worker' % (deploy))
        
        if deploy.parent:
            # Re request the move for the original
            deploy.parent.update_status(Deploy.States.move_requested)
        else:
            # Create a new deploy for the index with no parent
            if deploy.index.status != Index.States.hibernate_requested:
                self._create_new_deploy(deploy.index)
                        
        # Remove the deploy
        self._delete_deploy(deploy)

    def _handle_decommissioning(self, deploy):
        td = datetime.now() - deploy.timestamp
        min_delay = timedelta(seconds=10)
        if td > min_delay:
            logger.info('deleting deploy %s' % (deploy))
            self._delete_deploy(deploy)

    def _handle_dying_killable(self, deploy):
        logger.info('deleting deploy %s due to dying worker' % (deploy))
        
        deploy.children.update(parent=None)

        if deploy.parent:
            parent = deploy.parent 
            parent.status=Deploy.States.move_requested
            parent.save()
            
        # Remove the parent relationship for all children
        # That way, those deploys are considered "readable"
        
        # Remove the deploy entirely. RIP.
        self._delete_deploy(deploy)

    def _handle_moving(self, deploy):
        child = deploy.children.all()[0] #Assumes there's only 1 child
        if child.status == Deploy.States.controllable or child.status == Deploy.States.move_requested or child.status == Deploy.States.moving:
            logger.info('deploy %s:%d of Index "%s" (%s), replaces deploy %s:%d', child.worker.instance_name, child.base_port, deploy.index.name, deploy.index.code, deploy.worker.instance_name, deploy.base_port)
            child.update_parent(None)
            deploy.update_status(Deploy.States.decommissioning)
        else:
            logger.info('deploy %s:%d of Index "%s" (%s), moving to deploy %s:%d', deploy.worker.instance_name, deploy.base_port, deploy.index.name, deploy.index.code, child.worker.instance_name, child.base_port)


    def _handle_recovering(self, deploy):
        logger.debug('Contacting %s (%s) on %d of %s to check if it finished recovering', deploy.index.name, deploy.index.code, deploy.base_port, deploy.worker.wan_dns)
        try:
            indexer = rpc.getThriftIndexerClient(deploy.worker.lan_dns, int(deploy.base_port), timeout_ms)
            indexer_status = indexer.getStatus()
            if indexer_status == IndexerStatus.started:
                logger.info('Requesting full recovery for deploy for %s (%s) on %d.', deploy.index.name, deploy.index.code, deploy.base_port)
                indexer.startFullRecovery()
                return DeployManager.INDEX_RECOVERING
            elif indexer_status == IndexerStatus.recovering:
                logger.info("Index %s is in state %s. Waiting untill it's ready", deploy.index.code, indexer_status)
                return DeployManager.INDEX_RECOVERING
            elif indexer_status == IndexerStatus.ready:
                deploy.update_status(Deploy.States.controllable)
                if deploy.index.status == Index.States.waking_up:
                    deploy.index.update_status(Index.States.live)
                mail.report_new_deploy(deploy)
                
                logger.info('Deploy for %s (%s) on %d of %s reports it has finished recovering. New state moved to %s.', deploy.index.name, deploy.index.code, deploy.base_port, deploy.worker.wan_dns, Deploy.States.controllable)

                # The following is a HACK to restore twitvid's promotes after its index was moved
                # because we don't record promotes and they are lost after each move.
                # Luckily we know what twitvid promotes, so we can reproduce it here. This will break if they
                # change their code and start promoting something else. GitHub issue #41 calls for a proper
                # implementaion or to remove the feature altogether. Twitvid could now do this by using the 
                # caret operator like this: "name:(q)^100 OR author:(q)^100 OR (q)".

                if deploy.index.code == 'd7fz1':
                    try:
                        searcher = rpc.getThriftSearcherClient(deploy.worker.lan_dns, int(deploy.base_port), timeout_ms)
                        start = 0
                        while True:
                            rs = searcher.search('verified:1 AND cont_type:user', start, 1000, 0, {}, {}, {}, {}, {'fetch_fields':'author,fullname,name'})
                            if len(rs.docs) == 0:
                                break
                            for d in rs.docs:
                                author = d.get('author')
                                if author:
                                    indexer.promoteResult(d['docid'], author.lower().strip())
                                name = d.get('name', d.get('fullname'))
                                if name:
                                    indexer.promoteResult(d['docid'], name.lower().strip())
                            start += len(rs.docs)
                        logger.info('WARNING: HACK! %s promotes were recovered for TwitVid.', start)
                    except Exception, e:
                        logger.error('HACK ERROR: applying TwitVid promotes', e)

                # Phew. End of HACK. Please let's not do this anymore.

                return DeployManager.INDEX_CONTROLLABLE
            elif indexer_status == IndexerStatus.error:
                logger.error('Deploy for %s (%s) on %d of %s reports it has failed recovering. MANUAL INTERVENTION REQUIRED.', deploy.index.name, deploy.index.code, deploy.base_port, deploy.worker.wan_dns)
                #TODO: Send an alert.
        except Exception, e:
            logger.error('Index %s unreachable: %s, but its state is recovering', deploy.index.code, e)
            return DeployManager.INDEX_RECOVERING

    def _handle_initializing(self, deploy):
        logger.debug('Trying to reach %s (%s) on %d of %s.', deploy.index.name, deploy.index.code, deploy.base_port, deploy.worker.wan_dns)
        try:
            indexer = rpc.getThriftIndexerClient(deploy.worker.lan_dns, int(deploy.base_port), timeout_ms)
            indexer.ping()
            # successfully reported stats()
            if deploy.index.status == Index.States.new:
                deploy.update_status(Deploy.States.controllable)
                index = deploy.index
                index.status = Index.States.live
                index.save()
                logger.info('Deploy for %s (%s) on %d of %s contacted. New status moved to %s.', deploy.index.name, deploy.index.code, deploy.base_port, deploy.worker.wan_dns, Deploy.States.controllable)
                return DeployManager.INDEX_CONTROLLABLE
            else:
                deploy.update_status(Deploy.States.recovering)
                logger.info('Deploy for %s (%s) on %d of %s contacted. New status moved to %s.', deploy.index.name, deploy.index.code, deploy.base_port, deploy.worker.wan_dns, Deploy.States.recovering)
                return DeployManager.INDEX_RECOVERING
        except Exception, e:
            # not ready yet, we'll leave it as initializing
            logger.info('Index %s unreachable: %s', deploy.index.code, e)
            return DeployManager.INDEX_INITIALIZING

    def _get_free_port(self, deploy):
        while (True):
            candidate = random.Random().randrange(20000, stop=23990, step=10)
            if 0 == Deploy.objects.filter(worker=deploy.worker, base_port=candidate).count():
                return candidate

    def _handle_created(self, deploy):
        if not deploy.worker.is_ready():
            logger.info('Waiting to initialize index "%s" (%s) on %s:%d. The worker is not ready yet', deploy.index.name, deploy.index.code, deploy.worker.instance_name, deploy.base_port)
            return DeployManager.WORKER_NOT_READY_YET

        # else
        controller = rpc.getThriftControllerClient(deploy.worker.lan_dns)
        json_config = {}
        json_config['functions']  = deploy.index.get_functions_dict()

        # there should be exactly one recovery service 
        recovery_service = Service.objects.get(name='recovery')
        # log based storage
        json_config['log_based_storage'] = True
        json_config['log_server_host'] = recovery_service.host
        json_config['log_server_port'] = recovery_service.port
        
        json_config.update(deploy.index.configuration.get_data())
        
        proposed_port = self._get_free_port(deploy)
        json_config['base_port'] = proposed_port
        json_config['index_code'] = deploy.index.code

        analyzer_config = deploy.index.get_json_for_analyzer()
        if analyzer_config:
            json_config['analyzer_config'] = analyzer_config 


        logger.info('Initializing index "%s" (%s) on %s:%d', deploy.index.name, deploy.index.code, deploy.worker.instance_name, proposed_port)
        
        # override xmx with the one defined for this deploy
        json_config['xmx'] = deploy.effective_xmx
        
        logger.debug("deploy: %r\n----\nindex: %r\n----\nstart args: %r", deploy, deploy.index, json_config)
        started_ok = controller.start_engine(json.dumps(json_config))
        if started_ok:
            qs = Deploy.objects.filter(id=deploy.id)
            qs.update(base_port=proposed_port)
            qs = Deploy.objects.filter(id=deploy.id,index__deleted=False)
            qs.update(status=Deploy.States.initializing)
            return DeployManager.INDEX_INITIALIZING
        else:
            logger.warn('Deploy failed starting. Will try again in next round.');
            return


    @logerrors
    def delete_index(self, index_code):
        '''
            stops every running IndexEngine associated with the index_code, and
            deletes from MySql deploys and index.
        '''
        Index.objects.filter(code=index_code).update(name='[removed-%s]' % index_code)  
        Index.objects.get(code=index_code).mark_deleted()
        
        logger.info('Marked index %s as deleted', index_code)
        return 1

    def _delete_deploy(self, deploy):
        logger.debug('Deleting deploy: %r', deploy)
        if deploy.base_port:
            try:
                controller = rpc.getThriftControllerClient(deploy.worker.lan_dns)
                controller.kill_engine(deploy.index.code,deploy.base_port)
            except:
                logger.exception('Failed when attempting to kill the IndexEngine for the deploy %s', deploy) 
        
        index = deploy.index
        deploy.delete()
        
        if index.deleted and index.deploys.count() == 0:
            index.delete()

    @logerrors
    def redeploy_index(self,index_code):
        index = Index.objects.get(code=index_code)
        deploys = index.deploys.all()
        if len(deploys) != 1:
            logger.error("Call to redeploy_index for index_code %s failed, this index has %i deploys...", index_code, len(deploys))
        else:
            deploy = deploys[0]
            if deploy.status != Deploy.States.controllable:
                logger.error("Call to redeploy_index for index_code %s failed, this indexe's deploy is in state %s", index_code, deploy.status)
            else:
                deploy.update_status(Deploy.States.move_requested)
                logger.info('Deploy for index_code %s changed from controllable to move_requested.', index_code)


    @logerrors
    def _hibernate_index(self,index):
        if index.account.package.base_price == 0 or index.is_demo():
            for deploy in index.deploys.all():
                self._delete_deploy(deploy)
            index.update_status(Index.States.hibernated)
        else:
            logger.error('Index_code %s was asked to hibernate. Only free or demo indexes can hibernate.', index.code)


if __name__ == "__main__":
    handler = DeployManager()
    processor = TDeployManager.Processor(handler)
    transport = TSocket.TServerSocket(8899)
    tfactory  = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
    logger.info('Starting the deploy manager server...')
    server.serve()
 

