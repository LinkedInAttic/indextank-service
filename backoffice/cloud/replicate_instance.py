import boto, time
import socket, sys, json

from amazon_credential import AMAZON_USER, AMAZON_PASSWORD

def ec2_connection():
    return boto.connect_ec2(AMAZON_USER, AMAZON_PASSWORD)

def replicate_instance(ami_type, ami_id, zone='us-east-1a', security_group=None, logging=False):
    INSTANCE_TYPES = {
                      'fend': 'c1.medium',
                      'api': 'm1.xlarge',
                      'db': 'm1.large',
                      'log': 'm1.large'
                      }

    SECURITY_GROUPS = {
                      'fend': 'indextank-main',
                      'api': 'indextank-main',
                      'db': 'indextank-db',
                      'log': 'indextank-logstorage'
                      }
    
    if not ami_type in INSTANCE_TYPES or (not security_group and not ami_type in SECURITY_GROUPS):
        raise Exception("Invalid instance type")
    
    if not security_group:
        security_group = SECURITY_GROUPS[ami_type]

    conn = ec2_connection()
    res = conn.run_instances(image_id=ami_id, security_groups=[security_group], instance_type=INSTANCE_TYPES[ami_type], placement=zone)
    
    if len(res.instances) == 0:
        raise Exception("Replicated instance creation failed")
    
    instance = res.instances[0]
    instance_name = instance.id
    
    if logging:
        print "Successfully created replica (Instance: " + instance_name + ")" 
    
    time.sleep(5)

    reservations = conn.get_all_instances([instance_name])
    instance = reservations[0].instances[0]
      
    while not instance.state == 'running':
        if logging:
            print "Waiting for the instance to start..."
        time.sleep(10)
        
        reservations = conn.get_all_instances([instance_name])
        instance = reservations[0].instances[0]

    time.sleep(2)

    return {'id': instance_name, 'public_dns': instance.public_dns_name, 'private_dns': instance.private_dns_name}
    
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print 'replicate_instance receives at least two arguments'
        sys.exit(1)

    if len(sys.argv) == 4:
        print json.dumps(replicate_instance(sys.argv[1], sys.argv[2], sys.argv[3]))
    else:
        print json.dumps(replicate_instance(sys.argv[1], sys.argv[2]))

