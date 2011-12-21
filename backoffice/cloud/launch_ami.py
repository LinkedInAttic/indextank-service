import boto, sys, json, re

from amazon_credential import AMAZON_USER, AMAZON_PASSWORD

from replicate_instance import replicate_instance

def ec2_connection():
    return boto.connect_ec2(AMAZON_USER, AMAZON_PASSWORD)

def launch_ami(ami_type):
  print 'Launching %s instance' % ami_type
  print 'Finding %s ami' % ami_type
  
  conn = ec2_connection()
  amis = conn.get_all_images()
  
  sort_function = lambda x: x.location
  
  selected_amis = []
  for ami in amis:
    if re.search('indextank-%s' % ami_type, ami.location):
      selected_amis.append(ami)

  if len(selected_amis) == 0:
    print 'ERROR: no ami for type %s' % ami_type
    sys.exit(1)

  selected_amis.sort(key=sort_function)

  ami = selected_amis[-1]

  print 'AMI found: %s %s' % (ami.id, ami.location)
  return replicate_instance(ami_type, ami.id, logging=True)

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print "Usage: %s [fend|api|db]" % sys.argv[0]
    sys.exit(1)

  ami_type = sys.argv[1]
  print json.dumps(launch_ami(ami_type))
  
