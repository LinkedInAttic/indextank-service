import re
import time
import base64

from django.http import Http404, HttpResponse, HttpResponseNotAllowed, HttpResponseServerError, HttpResponseNotFound
from django.utils import simplejson as json
from django.shortcuts import get_object_or_404

from models import Account, Index, Provisioner
from lib import encoder
from lib.flaptor_logging import get_logger
import logging

class HttpMethodNotAllowed(Exception):
    """ 
    Signals that request.method was not part of
    the list of permitted methods.
    """
    
class AccountFilter(logging.Filter):
    def __init__(self, resource):
        logging.Filter.__init__(self)
        self.resource = resource
        
    def filter(self, record):
        record.prefix = ' $PIDCOLOR%s$RESET' % (self.resource.get_code())
        if self.resource.executing:
            # indent internal log lines
            record.msg = '  ' + record.msg
        else:
            record.prefix += '$BOLD'
            record.suffix = '$RESET'
        return True

class FakeLogger():
    '''
    Logger wrapper that adds:
       - pid
       - coloring
    '''
    def __init__(self, logger, resource, compname=None):
        self.logger = logger
        self.resource = resource
        self.compname = compname or logger.name
    
    def _add_extra(self, msg, kwargs):
        prefix = ' $PIDCOLOR%s$RESET' % (self.resource.get_code())
        suffix = ''
        if self.resource.executing:
            # indent internal log lines
            msg = '  ' + msg
        else:
            prefix += '$BOLD'
            suffix += '$RESET'
        if 'extra' in kwargs:
            kwargs['extra']['prefix'] = prefix 
            kwargs['extra']['suffix'] = suffix
            kwargs['extra']['compname'] = self.compname
        else:
            kwargs['extra'] = dict(prefix=prefix, suffix=suffix, compname=self.compname)
        return msg 
    
    def debug(self, msg, *args, **kwargs):
        msg = self._add_extra(msg, kwargs)
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        msg = self._add_extra(msg, kwargs)
        self.logger.info(msg, *args, **kwargs)
    
    def warn(self, msg, *args, **kwargs):
        msg = self._add_extra(msg, kwargs)
        self.logger.warn(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        msg = self._add_extra(msg, kwargs)
        self.logger.error(msg, *args, **kwargs)

    def fatal(self, msg, *args, **kwargs):
        msg = self._add_extra(msg, kwargs)
        self.logger.fatal(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        msg = self._add_extra(msg, kwargs)
        kwargs['exc_info'] = 1
        self.logger.error(msg, *args, **kwargs)

class Resource(object):
    authenticated = False
    mimetype = None
    permitted_methods = 'GET'
    
    def __init__(self):
        self.__name__ = self.__class__.__name__
        self._account = None
        self.permitted_methods = []
        if hasattr(self, 'GET'):
            self.permitted_methods.append('GET')
        if hasattr(self, 'POST'):
            self.permitted_methods.append('POST')
        if hasattr(self, 'PUT'):
            self.permitted_methods.append('PUT')
            if not hasattr(self, 'POST'):
                self.permitted_methods.append('POST')
                self.POST = self.PUT
        if hasattr(self, 'DELETE'):
            self.permitted_methods.append('DELETE')
        self.logger = FakeLogger(get_logger(self.__name__), self)
        self.error_logger = FakeLogger(get_logger('Errors'), self, compname=self.__name__)
        self.executing = True
    
    def dispatch(self, request, target, **kwargs):
        '''
          Delegates to the appropriate method (PUT, GET, DELETE)
          if the derived class defines the handler
          Returns and HttpMethodNotAllowed if not.
          For all methods but get, it also parses the body as json, and
          passes it to the handler method. Returns http 400 if it's
          unparsable.
        '''
        request_method = request.method.upper()
        if request_method not in self.permitted_methods:
            raise HttpMethodNotAllowed
        
        if request_method == 'GET':
            return target.GET(request, **kwargs)
        elif request_method == 'POST' or request_method == 'PUT' or request_method == 'DELETE':
            data = request._get_raw_post_data()
            if data:
                try:
                    data = json.loads(data)
                except ValueError, e:
                    return HttpResponse('"Invalid JSON input: %s"' % e, status=400)
            else:
                data = {}
            if request_method == 'DELETE':
                return target.DELETE(request, data=data, **kwargs)
            if request_method == 'POST':
                return target.POST(request, data=data, **kwargs)
            else:
                return target.PUT(request, data=data, **kwargs)
        else:
            raise Http404
    
    def get_code(self):
        '''
          Returns the account code (the public part of
          the api-key
        '''
        return self._code
    
    def get_account(self):
        '''
          Returns an Account object for this call.
          If account cannot be validated, it returns 404.
        '''
        if self._account_id and not self._account:
            self._account = get_object_or_404(Account, pk=self._account_id)
        return self._account
    
    def get_index(self, index_name):
        '''
          Returns an Index Object for this call.
          If and index with index_name cannot be found for this account,
          it returns None.
        '''
        idx = Index.objects.filter(account=self._account_id, name=index_name)
        if len(idx):
            return idx[0]
        else:
            return None
    
    def get_index_or_404(self, index_name):
        return get_object_or_404(Index, account=self._account_id, name=index_name)
    
    def __parse_account(self, request):
        host = request.get_host()
        code = re.search(r'([^\.]+)\.api\..*', host)
        self._code = None
        self._account_id = None
        self._account = None
        if code:
            self._code = code.group(1)
            self._account_id = encoder.from_key(self._code)
            
    def _authorize(self, request, force=False):
        auth = request.META.get('HTTP_AUTHORIZATION')
        if self._account_id and auth:
            auth = auth.split()
            if auth and len(auth) > 1 and auth[0].lower() == "basic":
                parts = base64.b64decode(auth[1]).split(':')
                if len(parts) == 2:
                    key = '%s-%s' % (self._code, parts[1])
                    #self.logger.debug('AUTH: comparing %s vs %s', key, self.get_account().apikey)
                    if self.get_account().apikey == key:
                        return True
        return False
                    
    def __call__(self, request, **kwargs):
        self._start_time = time.time()
        self.__parse_account(request)

        self.message = None
        
        response = HttpResponseServerError('Unreachable response')
        
        
        authorize_response = self.validate_request(request)

        if authorize_response:
            response = authorize_response
        else:
            try:
                response = self.dispatch(request, self, **kwargs)
            except HttpMethodNotAllowed:
                response = HttpResponseNotAllowed(self.permitted_methods)
                response.mimetype = self.mimetype
            except Http404:
                response = HttpResponseNotFound()
            except Exception:
                self.logger.exception('Unexpected error while processing request')
                self.error_logger.exception('Unexpected error while processing request')
                response = HttpResponseServerError('Unexpected error')
        elapsed_time = time.time() - self._start_time
        
        if self.message is None:
            self.message = response.content[:120]
            
        self.executing = False
        self.logger.info('[%d] in %.3fs for [%s %s] : %s', response.status_code, elapsed_time, request.method, request.path, self.message)
        self.executing = True
        return response
    
    def _check_authorize(self, request):
        """
          Checks authorization. Returns None if ok and the proper response
          if it does not pass.
        """
        response = None
        if not self._authorize(request):
            response = HttpResponse('"Authorization Required"', mimetype=self.mimetype, status=401)
            response['WWW-Authenticate'] = 'Basic realm=""'
        
        return response

    def validate_request(self, request):
        response = None
        if self.authenticated:
            response = self._check_authorize(request)
        if response is None and self.get_account().status != Account.Statuses.operational:
            response = HttpResponse('"Account not active"', mimetype=self.mimetype, status=409)
        return response

    def set_message(self, message):
        self.message = message
        
    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            instance = cls(**initkwargs)
            return instance(request, *args, **kwargs)
        return view
            

class JsonResponse(HttpResponse):
    def __init__(self, json_object, *args, **kwargs):
        body = json.dumps(json_object)
        if not ('mimetype' in kwargs and kwargs['mimetype']):
          if 'callback' in kwargs and kwargs['callback']:
            kwargs['mimetype'] = 'application/javascript'
          else:
            kwargs['mimetype'] = 'application/json'

        if 'callback' in kwargs:
            callback = kwargs.pop('callback')
            if callback:
                body = '%s(%s)' % (callback, body)
        super(JsonResponse, self).__init__(body, *args, **kwargs)

class ProvisionerResource(Resource):
    provisioner = None

    def get_code(self):
        '''
          Returs a human readable string identifying the provider.
        '''
        return self.provisioner.name if self.provisioner else '?????'

    def _authorize(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth:
            auth = auth.split()
            if auth and len(auth) > 1 and auth[0].lower() == "basic":
                parts = base64.b64decode(auth[1]).split(':')
                if len(parts) == 2:
                    token = parts[1]
                    provisioner = Provisioner.objects.filter(token=token)
                    if provisioner:
                        self.provisioner = provisioner[0]
                        return True
        return False

    def validate_request(self, request):
        return None


"""
    Standard validators and parsers
"""

def int_validator(message, status=400):
    '''
      Returns a validation function that, on error,
      return an HttpResponse with the given status code
      and message.

      >>> validator = int_validator('foo', status=401)
      >>> validator(1)
      >>> response = validator('bar')
      >>> response.code
      401

    '''
    def validate_int(string):
        if not string.isdigit():
            return HttpResponse(message, status=status)
    return validate_int

def json_validator(message, status=400):
    '''
      Return a validation function for json, that on error
      returns an HttpResponse with the given status code and
      message

      >>> validator = json_validator('foo', status=401)
      >>> validator('{"menu": {"foo": "bar", "bar": "foo"}}')
      >>> response = validator("{'menu': {'foo': 'bar', 'bar': 'foo'}}")
      >>> response.code
      401

    '''
    def validate_json(string):
        try:
            data = json.loads(string)
        except ValueError, e:
            return HttpResponse(message, status=status)
    return validate_json

ALWAYS_VALID = lambda x: None
IDENTITY = lambda x: x

"""
    Data extraction and validation for PUT requests decorators
"""
def optional_data(name, validate=ALWAYS_VALID, parse=IDENTITY):
    return __check_data(name, validate, parse, False)
def required_data(name, validate=ALWAYS_VALID, parse=IDENTITY):
    return __check_data(name, validate, parse, True)
    
def __check_data(name, validate, parse, required):
    def decorate(func):
        def decorated(self, request, data, **kwargs):
            if name in data:
                response = validate(data[name])
                if response:
                    return response
                kwargs[name] = parse(data[name])
            elif required:
                return HttpResponse('"Argument %s is required in the request body"' % name, status=400)
            return func(self, request, data=data, **kwargs)
        return decorated
    return decorate
        
""" 
    Keyword argument validation decorators 
"""
def validate_argument(name, validate, parse):
    '''
      Decorator that validates a request arguments, and returns a
      parsed version.
      Arguments:
      name -- The name of the parameter to validate.
      validate -- a validation function that returns None for sucess
        or an HttpResponse for failure
      parse -- The parsing function.
    '''
    def decorate(func):
        def decorated(self, request, **kwargs):
            if name in kwargs:
                response = validate(kwargs[name])
                if response:
                    return response
                kwargs[name] = parse(kwargs[name])
            return func(self, request, **kwargs)
        return decorated
    return decorate

def utf8_argument(name, message=None, status=400):
    '''
      Decorator that validates and parses utf-8 arguments into str.
      Arguments:
      message -- ignored
      status -- ignored
    '''
    def validate_utf8(string):
        try:
            string.encode('utf-8')
        except:
            return HttpResponse('"%s should be valid utf-8. Was: %s"' % (name, string))
    def encode_utf8(string):
        return string.encode('utf-8')
    return validate_argument(name, validate_utf8, encode_utf8)

def int_argument(name, message=None, status=400):
    return validate_argument(name, int_validator(message, status), int)

def non_empty_argument(name, message, status=400):
    def validate_non_empty(string):
        if string.strip() == '':
            return HttpResponse(message, status=status)
    return validate_argument(name, validate_non_empty, IDENTITY)

"""
    GET querystring argument validation decorators
"""
def required_querystring_argument(name, validate=ALWAYS_VALID, parse=IDENTITY):
    def decorate(func):
        def decorated(self, request, **kwargs):
            if name in request.GET:
                response = validate(request.GET[name])
                if response:
                    return response
                kwargs[name] = parse(request.GET[name])
            else:
                return HttpResponse('"Argument %s is required in the QueryString"' % (name), status=400)
            return func(self, request, **kwargs)
        return decorated
    return decorate

def querystring_argument(name, validate=ALWAYS_VALID, parse=IDENTITY):
    def decorate(func):
        def decorated(self, request, **kwargs):
            if name in request.GET:
                response = validate(request.GET[name])
                if response:
                    return response
                kwargs[name] = parse(request.GET[name])
            return func(self, request, **kwargs)
        return decorated
    return decorate
    
def int_querystring(name, message=None, status=400):
    if not message:
        message = 'Query string argument %s should be a non negative integer.' % name
    return querystring_argument(name, int_validator(message, status), int) 

def json_querystring(name, message=None, status=400):
    if not message:
        message = 'Query string argument %s should be a valid json.' % name
    return querystring_argument(name, json_validator(message, status), json.loads) 


def authorized_method(func):
    '''
      Decorator that forces request to be authorized.
      Using it on a method ensures that in the case that the
      user isn't authorized, the body of the method won't be run.
    '''
    def decorated(self, request, **kwargs):
        return self._check_authorize(request) or func(self, request, **kwargs)
    return decorated

def check_public_api(func):
    '''
      Checks that the defined index has public access enabled OR
      that the request is (privately) authorized.

      Depends on the "index" param so get_index_param_or404 should
      be called first.
      
      In case that the index doesn't have public access enabled and
      the request is not authorized, it return 404.
    '''
    def decorated(self, request, **kwargs):
        if 'index' in kwargs:
            index = kwargs['index']
            if not index.public_api:
                authorize_response = self._check_authorize(request)
                if authorize_response:
                    return authorize_response
        else:
            return HttpResponse('"Index name cannot be empty"', status=400)
        return func(self, request, **kwargs)
    return decorated

def get_index_param(func):
    '''
      Decorator that validates the existence of an index_name
      param, and parses it into the "index" variable.
      If no index with that name exist, it parses "None" into
      the index param, but the decorated function does run.
    '''
    def decorated(self, request, **kwargs):
        if 'index_name' in kwargs:
            index = self.get_index(kwargs['index_name'])
            kwargs['index'] = index
            del kwargs['index_name']
        return func(self, request, **kwargs)
    return decorated

def get_index_param_or404(func):
    '''
      Decorator that validates the existence of an index_name
      param, and parses it into the "index" variable.
      In case of error, an 404 HttpResponse is returned and
      the decorated function doesn't run.
    '''
    def decorated(self, request, **kwargs):
        if 'index_name' in kwargs:
            index = self.get_index_or_404(kwargs['index_name'])
            kwargs['index'] = index
            del kwargs['index_name']
        return func(self, request, **kwargs)
    return decorated

def wakeup_if_hibernated(func):
    '''
      Decorator that makes sure an index is not hibernated.
      It takes the "index" argument from the request, and checks
      the index's state. If it was hibernated, it triggers wake up
      and returns a 503 response.
    '''
    def decorated(self, request, **kwargs):
        if 'index' in kwargs:
            index = kwargs['index']
            if index.status in (Index.States.hibernated, Index.States.waking_up):
                if index.status == Index.States.hibernated:
                    index.update_status(Index.States.waking_up)
                return HttpResponse('"Wellcome back! Your index has been hibernating and is now waking up. Please retry in a few seconds"', status=503)
            return func(self, request, **kwargs)
        else:
            return HttpResponse('"Index name cannot be empty"', status=400)
    return decorated

