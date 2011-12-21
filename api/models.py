import hashlib
import random
import binascii

from lib.indextank.client import ApiClient, IndexAlreadyExists
from lib.authorizenet import AuthorizeNet, BillingException

from django.db import models
from django.contrib.auth.models import User
from django.utils import simplejson as json
from django.db import IntegrityError
from django.db.models.aggregates import Sum, Count

from lib import encoder, flaptor_logging

from django.conf import settings
from datetime import datetime

logger = flaptor_logging.get_logger('Models')

# idea taken from https://www.grc.com/passwords.htm
def generate_apikey(id):
    key = "2A1A8AE7CAEFAC47D6F74920CE4B0CE46430CDA6CF03D254C1C29402D727E570"
    while True:
        hash = hashlib.md5()
        hash.update('%d' % id)
        hash.update(key)
        hash.update('%d' % random.randint(0,1000000))
        random_part = binascii.b2a_base64(hash.digest())[:14]
        if not '/' in random_part:
            break
       
    unique_part = encoder.to_key(id)  
    
    return unique_part + '-' + random_part 

def generate_onetimepass(id):
    key = "CAEFAC47D6F7D727E57024920CE4B0CE46430CDA6CF03D254C1C29402A1A8AE7"
    while True:
        hash = hashlib.md5()
        hash.update('%d' % id)
        hash.update(key)
        hash.update('%d' % random.randint(0,1000000))
        random_part = binascii.b2a_base64(hash.digest())[:5]
        if not '/' in random_part:
            break
       
    unique_part = encoder.to_key(id)  
    
    return unique_part + random_part 

def generate_forgotpass(id):
    key = "E57024920CE4B0CE4643CAEFAC47D6F7D7270CDA6CF03D254C1C29402A1A8AE7"
    while True:
        hash = hashlib.md5()
        hash.update('%d' % id)
        hash.update(key)
        hash.update('%d' % random.randint(0,1000000))
        random_part = binascii.b2a_base64(hash.digest())[:6]
        if not '/' in random_part:
            break
       
    unique_part = encoder.to_key(id)  
    
    return random_part + unique_part  


# StoreFront models 
class Account(models.Model):
    apikey = models.CharField(max_length=22, unique=True)
    creation_time = models.DateTimeField()
    package = models.ForeignKey('Package', null=True)
    status = models.CharField(max_length=30, null=False)
    provisioner = models.ForeignKey('Provisioner', null=True)
     
    configuration = models.ForeignKey('IndexConfiguration', null=True)
    default_analyzer = models.ForeignKey('Analyzer', null=True, related_name="accounts")
    
    class Statuses:
        operational = 'OPERATIONAL'
        creating = 'CREATING'
        closed = 'CLOSED'

    def __repr__(self):
        return 'Account (%s):\n\tuser_email: %s\n\tapikey: %s\n\tcreation_time: %s\n\tstatus: %s\n\tpackage: %s\n\tconfiguration: %s\n' % (self.id, PFUser.objects.filter(account=self)[0].email, str(self.apikey), str(self.creation_time), str(self.status), self.package.name, self.configuration.description)

    def __str__(self):
        return '(apikey: %s; creation_time: %s; status: %s)' % (str(self.apikey), str(self.creation_time), str(self.status))

    def count_indexes(self):
        return self.indexes.aggregate(cnt=Count('id'))['cnt']

    def count_documents(self):
        return self.indexes.aggregate(cnt=Sum('current_docs_number'))['cnt']

    def is_operational(self):
        return self.status == Account.Statuses.operational
    
    def is_heroku(self):
        # HACK UNTIL HEROKU IS A PROVISIONER
        return self.package.code.startswith('HEROKU_')
        #return self.provisioner and self.provisioner.name == 'heroku'
    
    @classmethod
    def create_account(cls, dt, email=None, password=None):
        account = Account()
        
        account.creation_time = datetime.now()
        account.status = Account.Statuses.creating
        account.save()
        
        account.apikey = generate_apikey(account.id)
        account.save()
        
        unique_part, random_part = account.apikey.split('-', 1)
        if email is None:
            email = '%s@indextank.com' % unique_part
           
        if password is None:
            password = random_part
        
        try:
            user = User.objects.create_user(email, '', password)
        except IntegrityError, e:
            account.delete()
            raise e
        
        try:
            pfu = PFUser()
            pfu.account = account
            pfu.user = user
            pfu.email = email
        
            pfu.save()
        except IntegrityError, e:
            account.delete()
            user.delete()
            raise e
            
        return account, pfu
    
    def create_index(self, index_name, public_search=None):
        index = Index()
        
        # basic index data
        index.populate_for_account(self)
        index.name = index_name
        index.creation_time = datetime.now()
        index.language_code = 'en'
        index.status = Index.States.new
        if not public_search is None:
          index.public_api = public_search
        
        # test for name uniqueness
        # raises IntegrityError if the index name already exists
        index.save()
        
        # define the default function
        function = ScoreFunction()
        function.index = index
        function.name = '0'
        function.definition = '-age'
        function.save()
        
        # deduce code from id
        index.code = encoder.to_key(index.id)
        index.save()
        
        return index
    
    def create_demo_index(self):
        try:
            dataset = DataSet.objects.get(code='DEMO')
        except DataSet.DoesNotExist:
            logger.exception('DemoIndex dataset not present in database. Aborting demo index creation')
            return

        index = self.create_index('DemoIndex')
        
        index.public_api = True
        index.save()
        
        population = IndexPopulation()
        population.index = index
        population.status = IndexPopulation.Statuses.created
        population.dataset = dataset
        population.time = datetime.now()
        population.populated_size = 0
    
        population.save()
    
    def close(self):
        # Dropping an account implies:
        
        #    - removing the payment information from the account
        #    - removing the subscriptions from authorize.net
        for info in self.payment_informations.all():
            auth = AuthorizeNet()
            for subscription in info.subscriptions.all():
                auth.subscription_cancel(subscription.reference_id, subscription.subscription_id)
                subscription.delete()
            info.delete()
            
        
        #    - changing the status to CLOSED
        self.status = Account.Statuses.closed
        
        #    - removing and stopping the indexes for the account
        for index in self.indexes.all():
            self.drop_index(index)
            
        #    - notify
        #    send_notification(//close account)
        
        #    - FIXME: handle authorize net errors!
        
        
        self.save()
        
    def drop_index(self, index):
        client = ApiClient(self.get_private_apiurl())
        client.delete_index(index.name)    
    
    def apply_package(self, package):
        self.package = package
        
        self.configuration = package.configuration
    
    def update_apikey(self):
        self.apikey = generate_apikey(self.id)
    
    def get_private_apikey(self):
        return self.apikey.split('-', 1)[1]
        
    def get_public_apikey(self):
        return self.apikey.split('-', 1)[0]
    
    def get_private_apiurl(self):
        return 'http://:%s@%s.api.indextank.com' % (self.get_private_apikey(), self.get_public_apikey())

    def get_public_apiurl(self):
        return 'http://%s.api.indextank.com' % self.get_public_apikey()

    class Meta:
        db_table = 'storefront_account'

class AccountPayingInformation(models.Model):
    account = models.ForeignKey('Account', related_name='payment_informations')
        
    first_name = models.CharField(max_length=50, null=True)
    last_name = models.CharField(max_length=50, null=True)
    address = models.CharField(max_length=60, null=True)
    city = models.CharField(max_length=60, null=True)
    state = models.CharField(max_length=2, null=True)
    zip_code = models.CharField(max_length=60, null=True)
    country = models.CharField(max_length=2, null=True)
    
    company = models.CharField(max_length=50, null=True)
    
    credit_card_last_digits = models.CharField(max_length=4, null=True)
    contact_email = models.EmailField(max_length=255, null=True)

    #custom subscription
    monthly_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    subscription_status = models.CharField(max_length=30, null=True)
    subscription_type = models.CharField(max_length=30, null=True)
  
    
    class Meta:
        db_table = 'storefront_accountpayinginformation'


class PaymentSubscription(models.Model):
    account = models.ForeignKey('AccountPayingInformation', related_name='subscriptions')
    
    # authorizenet id
    subscription_id = models.CharField(max_length=20, null=False, blank=False)
    # indextank id
    reference_id = models.CharField(max_length=13, null=False, blank=False)
    
    amount = models.DecimalField(max_digits=8, decimal_places=2, null=False)
    
    # Frequency
    start_date = models.DateTimeField()
    frequency_length = models.IntegerField(null=False)
    frequency_unit = models.CharField(max_length=10, null=False, blank=False)
    
    class Meta:
        db_table = 'storefront_paymentsubscription'

    
class EffectivePayment(models.Model):
    account = models.ForeignKey('AccountPayingInformation', related_name='payments')
    
    transaction_date = models.DateTimeField()

    # authorizenet data
    transaction_id = models.CharField(max_length=12, null=False, blank=False)
    customer_id = models.CharField(max_length=8, null=False, blank=False)
    transaction_message = models.CharField(max_length=300, null=True)
    subscription_id = models.CharField(max_length=20, null=False, blank=False)
    subscription_payment_number = models.IntegerField(null=False)
    first_name = models.CharField(max_length=50, null=False, blank=False)
    last_name = models.CharField(max_length=50, null=False, blank=False)
    address = models.CharField(max_length=60, null=True)
    city = models.CharField(max_length=60, null=True)
    state = models.CharField(max_length=2, null=True)
    zip_code = models.CharField(max_length=60, null=True)
    country = models.CharField(max_length=2, null=True)
    company = models.CharField(max_length=50, null=True)

    # Inherited data (from account information
    credit_card_last_digits = models.CharField(max_length=4, null=False, blank=False)
    contact_email = models.EmailField(max_length=255)
    
    amount = models.DecimalField(max_digits=8, decimal_places=2, null=False)

    class Meta:
        db_table = 'storefront_effectivepayment'

class DataSet(models.Model):
    name = models.CharField(null=True, max_length=50, unique=True)
    code = models.CharField(null=True, max_length=15, unique=True)
    filename = models.CharField(null=True, max_length=100, unique=True)
    size = models.IntegerField(default=0)

    class Meta:
        db_table = 'storefront_dataset'
    
class IndexPopulation(models.Model):
    index = models.ForeignKey('Index', related_name='datasets')
    dataset = models.ForeignKey('DataSet', related_name='indexes')
    time = models.DateTimeField()
    populated_size = models.IntegerField(default=0)

    status = models.CharField(max_length=50,null=True)
     
    class Statuses:
       created = 'CREATED'
       populating = 'POPULATING'
       finished = 'FINISHED'
    
    class Meta:
        db_table = 'storefront_indexpopulation'

    
class Index(models.Model):
    account = models.ForeignKey('Account', related_name='indexes')
    code = models.CharField(null=True, max_length=22, unique=True)
    name = models.CharField(max_length=50)
    language_code = models.CharField(max_length=2)
    creation_time = models.DateTimeField()
    
    analyzer_config = models.TextField(null=True) 
    configuration = models.ForeignKey('IndexConfiguration', null=True)       
    public_api = models.BooleanField(default=False, null=False)

    status = models.CharField(max_length=50)    
    
    deleted = models.BooleanField(default=False, null=False)
    
    class States:
        new = 'NEW'
        live = 'LIVE'
        hibernate_requested = 'HIBERNATE_REQUESTED'
        hibernated = 'HIBERNATED'
        waking_up = 'WAKING_UP'
    
    def get_json_for_analyzer(self):
        if self.analyzer_config is None:
            return None
        configuration = json.loads(self.analyzer_config)
        final_configuration = {}
        
        if configuration.has_key('per_field'):
            per_field_final = {}
            per_field = configuration.get('per_field')
            for field in per_field.keys():
                per_field_final[field] = Index.get_analyzer(per_field[field])
            final_configuration['perField'] = per_field_final
            final_configuration['default'] = Index.get_analyzer(per_field.get('default'))
        else:
            final_configuration = Index.get_analyzer(configuration)
        
        return final_configuration
            
    @classmethod
    def get_analyzer(cls, configuration):
        analyzer_map = {}
        code = configuration.get('code')
        if code is None:
            raise ValueError('Analyzer configuration has no "code" key')
        
        try:
            analyzer = AnalyzerComponent.objects.get(code=code)
        except AnalyzerComponent.DoesNotExist:
            raise ValueError('Analyzer configuration "code" key doesn\'t match any analyzers')
            
        analyzer_map['factory'] = analyzer.factory
        analyzer_map['configuration'] = json.loads(analyzer.config)
        
        if configuration.has_key('filters'):
            filters_list = []
            for filter in configuration.get('filters'):
                filters_list.append(Index.get_analyzer(filter))
            analyzer_map['configuration']['filters'] = filters_list
        
        return analyzer_map
            
#    allows_adds = models.BooleanField(null=False,default=True)
#    allows_queries = models.BooleanField(null=False,default=True)
    
    # index creation data
#    allows_snippets = models.BooleanField()
#    
#    allows_autocomplete = models.BooleanField(default=True)
#    autocomplete_type = models.models.CharField(max_length=10, null=True) # NEW
#
#    allows_faceting = models.BooleanField()
#    facets_bits = models.IntegerField(null=True) # NEW
#    
#    max_variables = models.IntegerField(null=False) # NEW
#    
#    max_memory_mb = models.IntegerField(null=False) # NEW
#    rti_documents_number = models.IntegerField(null=False) # NEW
    
    # statistics
    current_size = models.FloatField(default=0)
    current_docs_number = models.IntegerField(default=0)
    queries_per_day = models.FloatField(default=0) 

    #demo
    base_port = models.IntegerField(null=True)

    def __repr__(self):
        return 'Index (%s):\n\tname: %s\n\tcode: %s\n\tcreation_time: %s\n\tconfiguration: %s\n\taccount\'s package: %s\ncurrent deploys: %r' % (self.id, self.name, self.code, self.creation_time, self.configuration.description, self.account.package.name, self.deploys.all())
    
    def is_populating(self):
        for population in self.datasets.all():
            if not population.status == IndexPopulation.Statuses.finished:
                return True
        return False
    
    def is_demo(self):
        return self.name == 'DemoIndex' and self.datasets.count() > 0

        
    def is_ready(self):
        '''
          Returns True if the end-user can use the index.
          (this means for read and write, and it's meant to
          be shown in the storefront page). Internally, this
          means that at least one deployment for this index
          is readable, and at least one is writable.
        '''
        return self.is_writable() and self.is_readable()

    def is_hibernated(self):
        return self.status in (Index.States.hibernated, Index.States.waking_up)

    def is_writable(self):
        '''
          Returns true if there's at least one index that can be written.
        '''
        for deploy in self.deploys.all():
            if deploy.is_writable():
                return True

    def is_readable(self):
        '''
          Returns true if there's at least one index that can be read.
        '''
        for deploy in self.deploys.all():
            if deploy.is_readable():
                return True

    def populate_for_account(self, account):
        self.account = account
        self.configuration = account.configuration
        if account.default_analyzer is not None:
            self.analyzer_config = account.default_analyzer.configuration

    def searchable_deploy(self):
        '''Returns a single deploy that can be used to search. If no deploy is searcheable
        it returns None. Note that if more than one deploy is searcheable, there are no warranties
        of wich one will be returned.'''
        # TODO : should change once deploy roles are implemented
        ds = self.deploys.all()
        ds = [d for d in ds if d.is_readable()]
        return ds[0] if ds else None

    def indexable_deploys(self):
        '''Returns the list of all deploys that should be updated (adds/updates/deletes/etc)'''
        # TODO : should change once deploy roles are implemented
        ds = self.deploys.all()
        ds = [d for d in ds if d.is_writable()]
        return ds
    
    def get_functions_dict(self):
        return dict((str(f.name), f.definition) for f in self.scorefunctions.all())
    
    def get_debug_info(self):
        info = 'Index: %s [%s]\n' % (self.name, self.code) +\
               'Account: %s\n' % self.account.user.email +\
               'Deploys:\n'
        for d in self.deploys.all():
            info += ' [deploy:%d] %s on [worker:%s] %s:%s' % (d.id, d.status, d.worker.id, d.worker.wan_dns, d.base_port)
        return info

    def update_status(self, new_status):
        print 'updating status %s for %r' % (new_status, self)
        logger.debug('Updating status to %s for idnex %r', new_status, self)
        Index.objects.filter(id=self.id).update(status=new_status)

    def mark_deleted(self):
        Index.objects.filter(id=self.id).update(deleted=True)

    class AutocompleTypes:
        created = 'DOCUMENTS'
        initializing = 'QUERIES'

    class Meta:
        unique_together = (('code','account'),('name','account'))
        db_table = 'storefront_index'

class Insight(models.Model):
    index = models.ForeignKey(Index, related_name='insights')
    code = models.CharField(max_length=30, null=False)
    data = models.TextField(null=False)
    last_update = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('index', 'code')
        db_table = 'storefront_insight'

class IndexConfiguration(models.Model):
    description = models.TextField(null=False)
    creation_date = models.DateField()
    json_configuration = models.TextField(null=False)

    def __repr__(self):
        j_map = json.loads(self.json_configuration)
        mapStr = '{\n'
        for m in j_map:
            mapStr += '\t\t%s -> %s\n' % (m, j_map[m])
        mapStr += '\t}\n'
        return 'IndexConfiguration (%s):\n\tdescription: %s\n\tcreation_date: %s\n\tjson_configuration: %s\n' % (self.id, self.description, str(self.creation_date), mapStr)

    def __str__(self):
        return '(description: %s; creation_date: %s; json_configuration: %s)' % (self.description, str(self.creation_date), self.json_configuration)

    def get_data(self):
        map = json.loads(self.json_configuration)
        data = {}
        for k,v in map.items():
            data[str(k)] = v
        data['ram'] = data.get('xmx',0) + data.get('bdb_cache',0)
        return data
    def set_data(self, data):
        self.json_configuration = json.dumps(data)
        
    class Meta:
        db_table = 'storefront_indexconfiguration'

class Analyzer(models.Model):
    account = models.ForeignKey('Account', related_name='analyzers')
    code = models.CharField(max_length=64)
    configuration = models.TextField()

    class Meta:
        db_table = 'storefront_analyzer'

class AnalyzerComponent(models.Model):
    code = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=1000)
    config = models.TextField(null=False,blank=False)
    factory = models.CharField(max_length=200)
    type = models.CharField(max_length=20)
    enabled = models.BooleanField()

    class Types:
        tokenizer = 'TOKENIZER'
        filter = 'FILTER'

    class Meta:
        db_table = 'storefront_analyzercomponent'

def create_analyzer(code, name, config, factory, type, enabled):
    analyzer = None
    try:
        analyzer = AnalyzerComponent.objects.get(code=code)
        
        analyzer.name = name
        analyzer.config = config
        analyzer.factory = factory
        analyzer.type = type
        analyzer.enabled = enabled
        
        analyzer.save()
    except AnalyzerComponent.DoesNotExist:
        analyzer = AnalyzerComponent(code=code, name=name, config=config, type=type, enabled=enabled)
        analyzer.save()

class Package(models.Model):
    '''
    Packages define what a user have the right to when creating an Account and how does the indexes in that Account
    behave.
    There are two sections for what the Package configures. A fixed section with the control and limits information
    that is used by nebu, storefront or api (base_price, index_max_size, searches_per_day, max_indexes). A dynamic 
    section that is handled by the IndexConfiguration object. The information of that section is passed to the IndexEngine
    as it is and handled by it.     
    '''
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30)
    base_price = models.FloatField()
    index_max_size = models.IntegerField()
    searches_per_day = models.IntegerField()
    max_indexes = models.IntegerField()
    
    configuration = models.ForeignKey('IndexConfiguration', null=True)
    
    def __repr__(self):
        return 'Package (%s):\n\tname: %s\n\tcode: %s\n\tbase_price: %.2f\n\tindex_max_size: %i\n\tsearches_per_day: %i\n\tmax_indexes: %i\n' % (self.id, self.name, self.code, self.base_price, self.index_max_size, self.searches_per_day, self.max_indexes)

    def __str__(self):
        return '(name: %s; code: %s; base_price: %.2f; index_max_size: %i; searches_per_day: %i; max_indexes: %i)' % (self.name, self.code, self.base_price, self.index_max_size, self.searches_per_day, self.max_indexes)

    def max_size_mb(self): 
        return self.index_max_size * settings.INDEX_SIZE_RATIO
    class Meta:
        db_table = 'storefront_package'

class ScoreFunction(models.Model):
    index       = models.ForeignKey(Index, related_name='scorefunctions')
    name        = models.IntegerField(null=False) # TODO the java API expects an int. But a String may be nicer for name.
    definition  = models.CharField(max_length=255, blank=False, null=True)

    class Meta:
        db_table = 'storefront_scorefunction'
        unique_together = (('index','name'))


def create_configuration(description, data, creation_date=None):
    configuration = IndexConfiguration()
    configuration.description = description
    configuration.creation_date = creation_date or datetime.now()
    configuration.json_configuration = json.dumps(data)
    
    configuration.save()
    return configuration

def create_package(code, name, base_price, index_max_size, searches_per_day, max_indexes, configuration_map):
#    The configuration_map will only be considered if the package if new or if it didn't already have a configuration

    package = None
    try:
        package = Package.objects.get(code=code)
        
        package.name = name
        package.base_price = base_price
        package.index_max_size = index_max_size
        package.searches_per_day = searches_per_day
        package.max_indexes = max_indexes
        
        if not package.configuration: 
            package.configuration = create_configuration('package:' + code, configuration_map)
        
        package.save()
    except Package.DoesNotExist:
        configuration = create_configuration('package:' + code, configuration_map)
        package = Package(code=code, base_price=base_price, index_max_size=index_max_size, searches_per_day=searches_per_day, max_indexes=max_indexes, configuration=configuration)
        package.save()
    
def create_provisioner(name, token, email, plans):
    provisioner = None
    try:
        provisioner = Provisioner.objects.get(name=name)
    except Provisioner.DoesNotExist:
        provisioner = Provisioner()
        provisioner.name = name
    provisioner.token = token
    provisioner.email = email
    provisioner.save()
    
    provisioner.plans.all().delete()
    for plan, code in plans.items():
        pp = ProvisionerPlan()
        pp.plan = plan
        pp.provisioner = provisioner
        pp.package = Package.objects.get(code=code)
        pp.save()
    
    
class AccountMovement(models.Model):
    account = models.ForeignKey('Account', related_name='movements')
    class Meta:
        db_table = 'storefront_accountmovement'

class ActionLog(models.Model):
    account = models.ForeignKey('Account', related_name='actions')
    class Meta:
        db_table = 'storefront_actionlog'
        
class PFUser(models.Model):
    user = models.ForeignKey(User, unique=True)
    account = models.OneToOneField('Account', related_name='user')
    email = models.EmailField(unique=True, max_length=255)
    change_password = models.BooleanField(default=False, null=False)
    class Meta:
        db_table = 'storefront_pfuser'



MAX_USABLE_RAM_PERCENTAGE = 0.9
# Nebulyzer stuff
class Worker(models.Model):
    '''
        Describes an amazon ec2 instance.
    '''
    instance_name   = models.CharField(max_length=50,null=False,blank=False)
    lan_dns         = models.CharField(max_length=100,null=False,blank=False)
    wan_dns         = models.CharField(max_length=100,null=False,blank=False)
    status          = models.CharField(max_length=30)
    timestamp       = models.DateTimeField(auto_now=True,auto_now_add=True)
    #physical memory in MegaBytes
    ram             = models.IntegerField()

    class States:
        created = 'CREATED'
        initializing = 'INITIALIZING'
        updating = 'UPDATING'
        controllable = 'CONTROLLABLE'
        decommissioning = 'DECOMMISSIONING'
        dying = 'DYING'
        dead = 'DEAD'
    
    class Meta:
        db_table = 'storefront_worker'

    def get_usable_ram(self):
        '''Return the amount of ram that can be used in this machine for
        indexengines. It's calculated as a fixed percentage of the physical
        ram. Value returned in MegaBytes'''
        return MAX_USABLE_RAM_PERCENTAGE * self.ram
    
    def get_used_ram(self):
        xmx = self.deploys.aggregate(xmx=Sum('effective_xmx'))['xmx']
        bdb = self.deploys.aggregate(bdb=Sum('effective_bdb'))['bdb']
        if xmx == None:
            xmx = 0
        if bdb == None:
            bdb = 0
        return xmx + bdb
    
    def is_assignable(self):
        return self.status != Worker.States.decommissioning
    
    def is_ready(self):
        return self.status in [Worker.States.controllable, Worker.States.decommissioning]

    def __repr__(self):
        return 'Worker (%s):\n\tinstance_name: %s\n\tlan_dns: %s\n\twan_dns: %s\n\tstatus: %s\n\ttimestamp: %s\n\tram: %s\n' %(self.pk, self.instance_name, self.lan_dns, self.wan_dns, self.status, self.timestamp, self.ram)

class Service(models.Model):
    name            = models.CharField(max_length=50,null=False,blank=False)
    type            = models.CharField(max_length=50,null=True,blank=True )
    host            = models.CharField(max_length=100,null=False,blank=False)
    port            = models.IntegerField()
    timestamp       = models.DateTimeField(auto_now=True,auto_now_add=True)

    class Meta:
        db_table = 'storefront_service'

    def __repr__(self):
        return 'Service (%s):\n\tname: %s\n\ttype: %s\n\thost: %s\n\tport: %s\n\ttimestamp: %s\n' % (self.pk, self.name, self.type, self.host, self.port, self.timestamp)
    

# CPU Stats
class WorkerMountInfo(models.Model):
    worker          = models.ForeignKey(Worker, related_name="disk_infos")
    timestamp       = models.DateTimeField()
    
    mount           = models.CharField(max_length=100,null=False,blank=False)
    available       = models.IntegerField()
    used            = models.IntegerField()
    
    class Meta: 
        db_table = 'storefront_workermountinfo'

    
class WorkerLoadInfo(models.Model):
    worker          = models.ForeignKey(Worker, related_name="load_infos")
    timestamp       = models.DateTimeField()
    
    load_average    = models.FloatField()

    class Meta:
        db_table = 'storefront_workerloadinfo'

class WorkerIndexInfo(models.Model):
    worker          = models.ForeignKey(Worker, related_name="indexes_infos")
    timestamp       = models.DateTimeField()
    
    deploy          = models.ForeignKey('Deploy', related_name="index_infos")
    used_disk       = models.IntegerField()
    used_mem        = models.IntegerField()

    class Meta:
        db_table = 'storefront_workerindexinfo'
    
    
class Deploy(models.Model):
    '''
        Describes a deploy of an index on a worker, and it's status.
        The idea is that an index can be moving from one worker to another,
        so queries and indexing requests have to be mapped to one or more
        index engines.
    '''
    index           = models.ForeignKey(Index, related_name="deploys")
    worker          = models.ForeignKey(Worker, related_name="deploys")
    base_port       = models.IntegerField()
    status          = models.CharField(max_length=30)
    timestamp       = models.DateTimeField(auto_now=True,auto_now_add=True) # Last time we updated this deploy.
    parent          = models.ForeignKey('self', related_name='children', null=True) # For moving deploys.
    effective_xmx   = models.IntegerField()
    effective_bdb   = models.IntegerField()
    dying           = models.BooleanField(default=False, null=False)
    
    # TODO add role fields
    #searching_role  = models.BooleanField()
    #indexing_role   = models.BooleanField()
    
    def __repr__(self):
        return 'Deploy (%s):\n\tparent deploy: %s\n\tindex code: %s\n\tstatus: %s\n\tworker ip: %s\n\tport: %d\n\teffective_xmx: %d\n\teffective_bdb: %d\n' % (self.id, self.parent_id, self.index.code, self.status, self.worker.lan_dns, self.base_port, self.effective_xmx, self.effective_bdb)

    def __unicode__(self):
        return "Deploy: %s on %s:%d" % (self.status, self.worker.lan_dns, self.base_port)

    def is_readable(self):
        '''Returns true if a search can be performed on this deployment, and
        the returned data is up to date'''
        return self.status == Deploy.States.controllable or \
                self.status == Deploy.States.move_requested or \
                self.status == Deploy.States.moving or \
                (self.status == Deploy.States.recovering and not self.parent)

    def is_writable(self):
        '''Returns True if new data has to be written to this deployment.'''
        return self.status == Deploy.States.controllable or \
            self.status == Deploy.States.recovering or \
            self.status == Deploy.States.move_requested or \
            self.status == Deploy.States.moving

    def total_ram(self):
        return self.effective_xmx + self.effective_bdb
            
    def update_status(self, new_status):
        print 'updating status %s for %r' % (new_status, self)
        logger.debug('Updating status to %s for deploy %r', new_status, self)
        Deploy.objects.filter(id=self.id).update(status=new_status, timestamp=datetime.now())
        
    def update_parent(self, new_parent):
        logger.debug('Updating parent to %s for deploy %r', new_parent, self)
        Deploy.objects.filter(id=self.id).update(parent=new_parent)

    class States:
        created = 'CREATED'
        initializing = 'INITIALIZING'
        recovering = 'RECOVERING'
        resurrecting = 'RESURRECTING'
        controllable = 'CONTROLLABLE'
        move_requested = 'MOVE_REQUESTED'
        moving = 'MOVING'
        decommissioning = 'DECOMMISSIONING'

    class Meta:
        db_table = 'storefront_deploy'

class BetaTestRequest(models.Model):
    email = models.EmailField(unique=True, max_length=255)
    site_url = models.CharField(max_length=200,null=False,blank=False)
    summary = models.TextField(null=False,blank=False)
    
    request_date = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=50,null=True)

    class Meta:
        db_table = 'storefront_betatestrequest'
    
class BetaInvitation(models.Model):
    password = models.CharField(max_length=20, null=True)
    account = models.ForeignKey('Account', null=True)
    assigned_customer = models.CharField(max_length=50, null=True)
    beta_requester = models.ForeignKey('BetaTestRequest', null=True, related_name="invitation") 

    invitation_date = models.DateTimeField(default=datetime.now)
    forced_package = models.ForeignKey('Package', null=False)    
    
    class Meta:
        db_table = 'storefront_signupotp'

class ContactInfo(models.Model):
    name = models.CharField(max_length=64)
    email = models.EmailField(unique=True, max_length=255)
    request_date = models.DateTimeField(default=datetime.now)
    source = models.CharField(max_length=64, null=True)
    
    class Meta:
        db_table = 'storefront_contactinfo'



class Provisioner(models.Model):
    name    = models.CharField(max_length=64)
    token   = models.CharField(max_length=64, null=False, blank=False)
    email   = models.EmailField(max_length=255) # contact info for the provisioner

    class Meta:
        db_table = "storefront_provisioner"

class ProvisionerPlan(models.Model):
    plan        = models.CharField(max_length=50)
    provisioner = models.ForeignKey('Provisioner', related_name='plans')
    package     = models.ForeignKey('Package')

    class Meta:
        db_table = "storefront_provisionerplan"

class BlogPostInfo(models.Model):
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=1024)
    date = models.DateTimeField()
    author = models.CharField(max_length=64)
    
    class Meta:
        db_table = 'storefront_blogpost'

