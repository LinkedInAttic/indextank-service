# Copyright (c) 2006-2008 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
Represents an EC2 Instance
"""
import boto
from boto.ec2.ec2object import EC2Object
from boto.resultset import ResultSet
from boto.ec2.address import Address
from boto.ec2.blockdevicemapping import BlockDeviceMapping
from boto.ec2.image import ProductCodes
import base64

class Reservation(EC2Object):
    
    def __init__(self, connection=None):
        EC2Object.__init__(self, connection)
        self.id = None
        self.owner_id = None
        self.groups = []
        self.instances = []

    def __repr__(self):
        return 'Reservation:%s' % self.id

    def startElement(self, name, attrs, connection):
        if name == 'instancesSet':
            self.instances = ResultSet([('item', Instance)])
            return self.instances
        elif name == 'groupSet':
            self.groups = ResultSet([('item', Group)])
            return self.groups
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'reservationId':
            self.id = value
        elif name == 'ownerId':
            self.owner_id = value
        else:
            setattr(self, name, value)

    def stop_all(self):
        for instance in self.instances:
            instance.stop()
            
class Instance(EC2Object):
    
    def __init__(self, connection=None):
        EC2Object.__init__(self, connection)
        self.id = None
        self.dns_name = None
        self.public_dns_name = None
        self.private_dns_name = None
        self.state = None
        self.state_code = None
        self.key_name = None
        self.shutdown_state = None
        self.previous_state = None
        self.instance_type = None
        self.instance_class = None
        self.launch_time = None
        self.image_id = None
        self.placement = None
        self.kernel = None
        self.ramdisk = None
        self.product_codes = ProductCodes()
        self.ami_launch_index = None
        self.monitored = False
        self.instance_class = None
        self.spot_instance_request_id = None
        self.subnet_id = None
        self.vpc_id = None
        self.private_ip_address = None
        self.ip_address = None
        self.requester_id = None
        self._in_monitoring_element = False
        self.persistent = False
        self.root_device_name = None
        self.block_device_mapping = None

    def __repr__(self):
        return 'Instance:%s' % self.id

    def startElement(self, name, attrs, connection):
        if name == 'monitoring':
            self._in_monitoring_element = True
        elif name == 'blockDeviceMapping':
            self.block_device_mapping = BlockDeviceMapping()
            return self.block_device_mapping
        elif name == 'productCodes':
            return self.product_codes
        return None

    def endElement(self, name, value, connection):
        if name == 'instanceId':
            self.id = value
        elif name == 'imageId':
            self.image_id = value
        elif name == 'dnsName' or name == 'publicDnsName':
            self.dns_name = value           # backwards compatibility
            self.public_dns_name = value
        elif name == 'privateDnsName':
            self.private_dns_name = value
        elif name == 'keyName':
            self.key_name = value
        elif name == 'amiLaunchIndex':
            self.ami_launch_index = value
        elif name == 'shutdownState':
            self.shutdown_state = value
        elif name == 'previousState':
            self.previous_state = value
        elif name == 'name':
            self.state = value
        elif name == 'code':
            try:
                self.state_code = int(value)
            except ValueError:
                boto.log.warning('Error converting code (%s) to int' % value)
                self.state_code = value
        elif name == 'instanceType':
            self.instance_type = value
        elif name == 'instanceClass':
            self.instance_class = value
        elif name == 'rootDeviceName':
            self.root_device_name = value
        elif name == 'launchTime':
            self.launch_time = value
        elif name == 'availabilityZone':
            self.placement = value
        elif name == 'placement':
            pass
        elif name == 'kernelId':
            self.kernel = value
        elif name == 'ramdiskId':
            self.ramdisk = value
        elif name == 'state':
            if self._in_monitoring_element:
                if value == 'enabled':
                    self.monitored = True
                self._in_monitoring_element = False
        elif name == 'instanceClass':
            self.instance_class = value
        elif name == 'spotInstanceRequestId':
            self.spot_instance_request_id = value
        elif name == 'subnetId':
            self.subnet_id = value
        elif name == 'vpcId':
            self.vpc_id = value
        elif name == 'privateIpAddress':
            self.private_ip_address = value
        elif name == 'ipAddress':
            self.ip_address = value
        elif name == 'requesterId':
            self.requester_id = value
        elif name == 'persistent':
            if value == 'true':
                self.persistent = True
            else:
                self.persistent = False
        else:
            setattr(self, name, value)

    def _update(self, updated):
        self.updated = updated
        if hasattr(updated, 'dns_name'):
            self.dns_name = updated.dns_name
            self.public_dns_name = updated.dns_name
        if hasattr(updated, 'private_dns_name'):
            self.private_dns_name = updated.private_dns_name
        if hasattr(updated, 'ami_launch_index'):
            self.ami_launch_index = updated.ami_launch_index
        self.shutdown_state = updated.shutdown_state
        self.previous_state = updated.previous_state
        if hasattr(updated, 'state'):
            self.state = updated.state
        else:
            self.state = None
        if hasattr(updated, 'state_code'):
            self.state_code = updated.state_code
        else:
            self.state_code = None

    def update(self):
        rs = self.connection.get_all_instances([self.id])
        if len(rs) > 0:
            self._update(rs[0].instances[0])
        return self.state

    def stop(self):
        rs = self.connection.terminate_instances([self.id])
        self._update(rs[0])

    def reboot(self):
        return self.connection.reboot_instances([self.id])

    def get_console_output(self):
        return self.connection.get_console_output(self.id)

    def confirm_product(self, product_code):
        return self.connection.confirm_product_instance(self.id, product_code)

    def use_ip(self, ip_address):
        if isinstance(ip_address, Address):
            ip_address = ip_address.public_ip
        return self.connection.associate_address(self.id, ip_address)

    def monitor(self):
        return self.connection.monitor_instance(self.id)

    def unmonitor(self):
        return self.connection.unmonitor_instance(self.id)

class Group:

    def __init__(self, parent=None):
        self.id = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'groupId':
            self.id = value
        else:
            setattr(self, name, value)
    
class ConsoleOutput:

    def __init__(self, parent=None):
        self.parent = parent
        self.instance_id = None
        self.timestamp = None
        self.comment = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'instanceId':
            self.instance_id = value
        elif name == 'output':
            self.output = base64.b64decode(value)
        else:
            setattr(self, name, value)

class InstanceAttribute(dict):

    def __init__(self, parent=None):
        dict.__init__(self)
        self._current_value = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'value':
            self._current_value = value
        else:
            self[name] = self._current_value
