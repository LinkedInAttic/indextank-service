import sys

from thrift.transport import TTransport, TSocket
from thrift.protocol import TBinaryProtocol

from flaptor.indextank.rpc import DeployManager


# Missing a way to close transport 
def getThriftDeployManagerClient(host):
    protocol, transport = __getThriftProtocolTransport(host,8899)
    client = DeployManager.Client(protocol)
    transport.open()
    return client

def __getThriftProtocolTransport(host,port=0):
    ''' returns protocol,transport'''
    # Make socket
    transport = TSocket.TSocket(host, port)

    # Buffering is critical. Raw sockets are very slow
    transport = TTransport.TBufferedTransport(transport)

    # Wrap in a protocol
    protocol = TBinaryProtocol.TBinaryProtocol(transport)
    return protocol, transport

if __name__ == "__main__":
    client = getThriftDeployManagerClient('deploymanager')
    while True:
        line = sys.stdin.readline()
        if not line : break
        
        line = line.strip()
        if line.startswith('redeploy'):
            code = line[8:].strip()
            client.redeploy_index(code)
            print 'redeploy executed'
        else:
            print 'invalid command'
            
