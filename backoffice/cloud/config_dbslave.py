import sys, time
import subprocess, shlex
import MySQLdb

from optparse import OptionParser

def config_dbslave(master_host, slave_host, user, password):

  print 'Configuring DB slave'
  print 'MASTER:%s' % master_host
  print 'SLAVE:%s' % slave_host

  # ASSIGN SERVER-ID AND CONFIGURE MY.CNF FILE
  slave_id = int(time.time())
  print 'SLAVE: Configuring mysql slave with id: %s' % slave_id
  
  set_up_mysql_config = (
    "sudo service mysql stop;" +
    "sudo sed -i 's/server-id = 0/server-id = %s/' /etc/mysql/my.cnf;" % slave_id +
    "sudo service mysql start"
  )

  retry = 0
  ssh_done = False

  while not ssh_done:
    ret_code = subprocess.call(['ssh','-oUserKnownHostsFile=/dev/null','-oStrictHostKeyChecking=no', 'flaptor@%s' % slave_host, set_up_mysql_config])

    if ret_code:
      if retry < 3:
        print 'WARNING: Couldn\'t configure and start mysql service at slave %s. Retrying' % slave_host
        retry += 1
        time.sleep(1)
      else:
        print 'ERROR:Couldn\'t configure and start mysql service at slave %s' % slave_host
        sys.exit(1)
    else:
      ssh_done = True

  #############################################################################################
  # This script requires a machine running with mysql, '****' user, and 'indextank' database
  # 1.- Promote master_host to master (if applies)
  # 2.- Dump data from master
  # 3.- Import data in slave
  # 4.- turn on replication
  # 5.- check tables are synced
  #############################################################################################

  ####################
  # Open connections #
  ####################

  dbmaster = MySQLdb.connect(host=master_host,user=user,passwd=password,db='indextank')
  dbslave = MySQLdb.connect(host=slave_host,user=user,passwd=password,db='indextank')

  ##########################################
  # 1.- Promote master to slave (if applies)
  ##########################################
    
  print 'MASTER: Checking master_host is master (and promoting to master if not)'

  mc = dbmaster.cursor()
  is_slave = mc.execute('SHOW SLAVE STATUS')
  if is_slave:
    mc.execute('STOP SLAVE')
    mc.execute('RESET MASTER')
    mc.execute("CHANGE MASTER TO MASTER_HOST=''")
    
    is_slave = mc.execute('SHOW SLAVE STATUS')
    if is_slave:
      print 'Warning: MASTER (%s) seems to still work as slave'
  
  ############################
  # 2.- dump data from master
  ############################
  print 'MASTER: Locking tables'
  start_lock_time = time.time()
  mc.execute('FLUSH TABLES WITH READ LOCK')

  print 'MASTER: Dumping data'
  command_line = 'mysqldump --tables -h%s -u%s -p%s indextank' % (master_host, user, password)
  dump_data_process = subprocess.Popen(shlex.split(command_line), stdout=subprocess.PIPE)

  ##########################
  # 3.- import data in slave
  ##########################
  
  # 3.1.- Stop slave
  print 'SLAVE: Stopping slave process'
  sc = dbslave.cursor()
  sc.execute('stop slave')

  # 2.2.- import data
  print 'SLAVE: Importing master dump'
  ret_code = subprocess.call(['mysql', '-h%s' % slave_host, '-u%s' % user, '-p%s' % password, 'indextank'], stdin=dump_data_process.stdout)
  dump_data_process.stdout.close()

  if ret_code:
    print 'ERROR SLAVE: Import data failed on (%s)' % slave_host
    sys.exit(1)

  #########################  
  # 4.- turn on replication
  #########################

  # 4.1 Request master status
  print 'MASTER: request master status'
  mc.execute('SHOW MASTER STATUS')
  master_status = mc.fetchone()
  if not master_status:
    print "ERROR: Couldn't turn replication on"
    sys.exit(1)
    
  binlog_filename = master_status[0]
  binlog_position = master_status[1]

  # 4.2 config master in slave and start slave
  print 'SLAVE: config master in slave'

  sc.execute("CHANGE MASTER TO MASTER_HOST=%s, MASTER_USER=%s, MASTER_PASSWORD=%s, MASTER_LOG_FILE=%s, MASTER_LOG_POS=%s", [master_host, user, password, binlog_filename, binlog_position])

  sc.execute('START SLAVE')

  is_slave = sc.execute('SHOW SLAVE STATUS')

  if not is_slave:
    print 'WARNING SLAVE: Setting up slave failed'

  # 4.3 unlock master tables
  print 'MASTER: unlock tables'
  mc.execute('UNLOCK TABLES')
  end_lock_time = time.time()
  
  print 'Locking time: %s sec.' % (end_lock_time - start_lock_time)
  
  #####################
  # Close connections #
  #####################
  mc.close()
  dbmaster.close()
  
  sc.close()
  dbslave.close()
  
  ##################################
  # 5. check tables are synchronized
  ##################################
  print 'Checking tables are synchronized'
  chescksum_process = subprocess.Popen(['mk-table-checksum', '--databases', 'indextank', '-u'+user, '-p'+password, master_host, slave_host], stdout=subprocess.PIPE)

  checksum_output = chescksum_process.communicate()[0]

  checksum_lines = checksum_output.splitlines()

  found_error = False
  for i in range(0,len(checksum_lines)/2):
    table_check1 = checksum_lines[2*i+1].split()
    table_check2 = checksum_lines[2*i+2].split()
    is_synchronized = table_check1[0] == table_check2[0] and table_check1[1] == table_check2[1] and table_check1[4] == table_check2[4] and table_check1[6] == table_check2[6]
    if not is_synchronized:
      found_error = True
      print 'ERROR: table %s.%s out of sync \n%s \n%s' % (table_check1[0], table_check1[1], table_check1, table_check2)

  if found_error:
    print 'Some errors were found in synchronization. Please check master-slave status.'
  else:
    print 'Synchronization succesful.'

# SET AND READ PARAMETERS
if __name__ == '__main__':
  parser = OptionParser(usage="usage: %prog -m master_host -s slave_host -u db_user -p db_pass")
  parser.add_option("-m", "--master_host", dest="master", help="Master host")
  parser.add_option("-s", "--slave_host", dest="slave", help="Slave host")
  parser.add_option("-u", "--user", dest="user", default=True, help="Database user")
  parser.add_option("-p", "--passwd", dest="password", help="Database user")

  options, _ = parser.parse_args()

  if not options.master:
    print 'master_host option is required'
    sys.exit(1)
  master_host = options.master

  if not options.slave:
    print 'master_slave option is required'
    sys.exit(1)
  slave_host = options.slave

  if not options.user:
    print 'user option is required'
    sys.exit(1)
  user = options.user

  if options.password:
    password = options.password
  else:
    print 'Enter DB password:'
    password = sys.stdin.readline()

  config_dbslave(master_host, slave_host, user, password)

