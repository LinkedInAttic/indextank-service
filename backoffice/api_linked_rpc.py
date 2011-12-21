from flaptor.indextank.rpc import Indexer, Searcher, Suggestor, Storage, LogWriter, WorkerManager,\
    DeployManager, Controller, FrontendManager
    
from flaptor.indextank.rpc.ttypes import NebuException, IndextankException

''' =========================== 
           THRIFT STUFF
    =========================== '''
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from lib import flaptor_logging, exceptions
from thrift.transport.TTransport import TTransportException
from socket import socket
from socket import error as SocketError


logger = flaptor_logging.get_logger('RPC')

# Missing a way to close transport 
def getThriftControllerClient(host, timeout_ms=None):
    protocol, transport = __getThriftProtocolTransport(host,19010, timeout_ms)
    client = Controller.Client(protocol)
    transport.open()
    return client

# Missing a way to close transport 
def getThriftIndexerClient(host, base_port, timeout_ms=None):
    protocol, transport = __getThriftProtocolTransport(host, base_port + 1, timeout_ms)
    client = Indexer.Client(protocol)
    transport.open()
    return client
    
def getThriftSearcherClient(host, base_port, timeout_ms=None):
    protocol, transport = __getThriftProtocolTransport(host, base_port + 2, timeout_ms)
    client = Searcher.Client(protocol)
    transport.open()
    return client

def getThriftSuggestorClient(host, base_port):
    protocol, transport = __getThriftProtocolTransport(host, base_port + 3)
    client = Suggestor.Client(protocol)
    transport.open()
    return client

storage_port = 10000
def getThriftStorageClient():
    protocol, transport = __getThriftProtocolTransport('storage',storage_port)
    client = Storage.Client(protocol)
    transport.open()
    return client

def getThriftLogWriterClient(host, port, timeout_ms=500):
    protocol, transport = __getThriftProtocolTransport(host,port,timeout_ms)
    client = LogWriter.Client(protocol)
    transport.open()
    return client

def getThriftLogReaderClient(host, port, timeout_ms=None):
    protocol, transport = __getThriftProtocolTransport(host,port,timeout_ms)
    client = LogWriter.Client(protocol)
    transport.open()
    return client

class ReconnectingClient:
    def __init__(self, factory):
        self.factory = factory
        self.delegate = None #factory()
        
    def __getattr__(self, name):
        import types
        if self.delegate is None:
            self.delegate = self.factory()
        att = getattr(self.delegate, name)
        if type(att) is types.MethodType:
            def wrap(*args, **kwargs):
                try:
                    return att(*args, **kwargs)
                except (NebuException, IndextankException):
                    logger.warn('raising catcheable exception')
                    raise
                except (TTransportException, IOError, SocketError):
                    logger.warn('failed to run %s, reconnecting once', name)
                    self.delegate = self.factory()
                    att2 = getattr(self.delegate, name)
                    return att2(*args, **kwargs)
                except Exception:
                    logger.exception('Unexpected failure to run %s, reconnecting once', name)
                    self.delegate = self.factory()
                    att2 = getattr(self.delegate, name)
                    return att2(*args, **kwargs)
                    
            return wrap
        else:
            return att

def getReconnectingStorageClient():
    return ReconnectingClient(getThriftStorageClient)

def getReconnectingLogWriterClient(host, port):
    return ReconnectingClient(lambda: getThriftLogWriterClient(host, port))

worker_manager_port = 8799
def getThriftWorkerManagerClient(host):
    protocol, transport = __getThriftProtocolTransport(host,worker_manager_port)
    client = WorkerManager.Client(protocol)
    transport.open()
    return client

deploymanager_port = 8899
def get_deploy_manager():
    protocol, transport = __getThriftProtocolTransport('deploymanager',deploymanager_port)
    client = DeployManager.Client(protocol)
    transport.open()
    return client


def __getThriftProtocolTransport(host, port=0, timeout_ms=None):
    ''' returns protocol,transport'''
    # Make socket
    transport = TSocket.TSocket(host, port)

    if timeout_ms is not None:
        transport.setTimeout(timeout_ms)
    
    # Buffering is critical. Raw sockets are very slow
    transport = TTransport.TBufferedTransport(transport)
 
    # Wrap in a protocol
    protocol = TBinaryProtocol.TBinaryProtocol(transport) 
    return protocol, transport


def get_searcher_client(index, timeout_ms=None):
    '''
        This method returns a single searcherclient, or None
    '''
    deploy = index.searchable_deploy()
    if deploy:
        return getThriftSearcherClient(deploy.worker.lan_dns, int(deploy.base_port), timeout_ms)
    else:
        return None

def get_worker_controller(worker, timeout_ms=None):
    return getThriftControllerClient(worker. lan_dns)

def get_suggestor_client(index):
    '''
        This method returns a single suggestorclient, or None
    '''
    deploy = index.searchable_deploy()
    if deploy:
        return getThriftSuggestorClient(deploy.worker.lan_dns, int(deploy.base_port))
    else:
        return None

def get_indexer_clients(index, timeout_ms=1000):
    '''
        This method returns the list of all indexerclients that should be updated
        on add,delete,update, and category updates.
        @raise exceptions.NoIndexerException if this index has no writable deploy.
    '''
    deploys = index.indexable_deploys()
    retval = []
    for d in deploys:
        retval.append(getThriftIndexerClient(d.worker.lan_dns, int(d.base_port), timeout_ms))
    if retval:
        return retval
    else:
        raise exceptions.NoIndexerException()
