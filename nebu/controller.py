#!/usr/bin/python
import subprocess
import shutil
import os
import signal
import systemutils
import subprocess

import flaptor.indextank.rpc.Controller as TController
from flaptor.indextank.rpc.ttypes import WorkerMountStats, WorkerLoadStats, IndexStats


from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
import sys
import commands
from lib import flaptor_logging
import simplejson as json

logger = flaptor_logging.get_logger('Controller')

def _get_working_directory(index_code,base_port):
    return "/data/indexes/%s-%d"% ( index_code, base_port) # XXX /data?

class Controller:
    """ Controls a Host"""

    def __init__(self):
        pass

    def __create_indexengine_environment(self,working_directory):
        shutil.copytree('indextank_lib', working_directory + "/lib")
        shutil.copy('startIndex.py', working_directory)
        shutil.copy('log4j.properties', working_directory)
        

    def _check_port_available(self, port):
        '''Returns true if the port is not being used'''
        o = subprocess.call(['./checkPort.sh', str(port)])
        if o == 0:
            return False
        else:
            return True



    def start_engine(self, json_configuration = '{}'):

        config = json.loads(json_configuration)
        index_code = config['index_code']
        base_port = int(config['base_port'])
        
        if not self._check_port_available(base_port):
            logger.warn("I was requested to start an index engine with code %s, but the port (%i) is not free." % (index_code, base_port))
            return False
        working_directory = _get_working_directory(index_code, base_port)

        self.__create_indexengine_environment(working_directory)

        config_file_name = 'indexengine_config'
        config_file = open(os.path.join(working_directory, config_file_name), 'w')
        config_file.write(json_configuration)
        config_file.close()
        
        logger.info("starting %s on port %d", index_code, base_port)
        cmd = ['python','startIndex.py', config_file_name]

        logger.debug("executing %r", cmd)
        subprocess.call(cmd, cwd=working_directory, close_fds=True)
        return True
    

    def get_worker_mount_stats(self):
        return WorkerMountStats(systemutils.get_available_sizes())

    def get_worker_load_stats(self):
        loads = systemutils.get_load_averages()
        return WorkerLoadStats(loads[0], loads[1], loads[2])

    def get_worker_index_stats(self, index_code, port):
        index_stats = systemutils.get_index_stats(index_code, port)
        return IndexStats(used_disk=index_stats['disk'], used_mem=index_stats.get('mem') or 0)

    def kill_engine(self,index_code, base_port):
        """ Kills the IndexEngine running on base_port. 
            This is a safeguard. The correct way to stop an IndexEngine is 
            asking it to do so through it's thrift api
        """
        
        try:
            f = open("%s/pid"% _get_working_directory(index_code, base_port))
            pid = int(f.read().strip())
            os.kill(pid,signal.SIGKILL) # signal 9
            f.close()
            #shutil.rmtree(_get_working_directory(index_code, base_port))
            return 0
        except Exception, e:
            logger.error(e)
            return 1
    
    def stats(self):
        """ Provides stats about the host it is running on. May need to parse top, free, uptime and such."""
        logger.debug("host stats")
        pass

    def update_worker(self, host):
        logger.info("UPDATING WORKER FROM %s", host)
        retcode = subprocess.call(['bash', '-c', 'rsync -avL -e "ssh -o StrictHostKeyChecking=no -i /home/indextank/.ssh/id_rsa_worker -l indextank" %s:/home/indextank/nebu/ /home/indextank/nebu' % (host)])
        return retcode

    def restart_controller(self):
        logger.info('Attempting restart')
        subprocess.call(['bash', '-c', 'sudo /etc/init.d/indexengine-nebu-controller restart'])
        sys.exit(0)
        logger.error('Survived a restart?')
        
    def tail(self, file, lines, index_code, base_port):
        if index_code:
            file = '/data/indexes/%s-%d/%s' % (index_code, base_port, file)
        return commands.getoutput("tail -n %d %s" % (lines, file))
        
    def head(self, file, lines, index_code, base_port):
        if index_code:
            file = '/data/indexes/%s-%d/%s' % (index_code, base_port, file)
        return commands.getoutput("head -n %d %s" % (lines, file))

    def ps_info(self, pidfile, index_code, base_port):
        if index_code:
            pidfile = '/data/indexes/%s-%d/pid' % (index_code, base_port)
        return commands.getoutput("ps u -p `%s`" % (pidfile))


if __name__ == '__main__':
    handler = Controller()
    processor = TController.Processor(handler)
    transport = TSocket.TServerSocket(19010)
    tfactory  = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
    logger.info('Starting the controller server...')
    server.serve()

