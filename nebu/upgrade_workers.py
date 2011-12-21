#!/usr/bin/python

#
# This script is used from the upgrade_frontend.sh
# to issue commands to every worker so they can update 
# their nebu installations from this frontend and 
# restart their controllers.
#
# author: santip
#

from nebu.models import Worker
import rpc
import socket
from thrift.transport import TTransport

for w in Worker.objects.all():
    print 'Upgrading worker %d at %s' % (w.id, w.wan_dns)
    dns = w.lan_dns
    controller = rpc.getThriftControllerClient(dns)
    host = socket.gethostbyname_ex(socket.gethostname())[0]
    retcode = controller.update_worker(host)
    if retcode == 0:
        try:
            print 'Worker %s updated. Restarting...' % dns
            controller.restart_controller()
            print "Restart controller didn't throw an exception. Did it restart?"
        except TTransport.TTransportException:
            # restart will always fail
            pass 
print 'Done'
