from rpc import getThriftWorkerManagerClient
import sys


# Missing a way to close transport 

if __name__ == '__main__':
    client = getThriftWorkerManagerClient('workermanager')
    if len(sys.argv) > 1:
        itype = sys.argv[1]
        retcode = client.add_worker(itype)
        print "Finished adding worker of type [%s] : %s " % (itype, retcode)
    else:
        retcode = client.add_worker()
        print "Finished adding worker: %s" % retcode
        
