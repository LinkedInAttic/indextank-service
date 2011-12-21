import subprocess, sys, json
from config_dbslave import config_dbslave
from launch_ami import launch_ami

def create_dbslave(master_host):
  print 'Creating DB SLAVE from MASTER %s' % master_host
  instance_data = launch_ami('db')

  slave_host = instance_data['public_dns']
  config_dbslave(master_host, slave_host, '****', '****')

  print 'DB Slave succesfully started in: %s' % slave_host

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print "Usage: %s <master_host>" % sys.argv[0]
    sys.exit(1)

  master_host = sys.argv[1]
  create_dbslave(master_host)


