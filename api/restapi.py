import datetime

from django.contrib.auth.management.commands.createsuperuser import is_valid_email
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.db import IntegrityError

from models import Account, ScoreFunction, Package, Service

from flaptor.indextank.rpc import ttypes

from restresource import ProvisionerResource, Resource, JsonResponse, non_empty_argument, int_argument, required_data, optional_data, int_querystring, json_querystring, querystring_argument, required_querystring_argument, check_public_api, get_index_param, get_index_param_or404, wakeup_if_hibernated, authorized_method

from lib import encoder
from lib import mail
from lib.indextank.client import ApiClient

import rpc
import re
from api import models
import time
import storage

LOG_STORAGE_ENABLED = True

""" Data validation and parsing functions """
def _encode_utf8(s):
    try:
        return s.encode('utf-8')
    except:
        try:
            str(s).decode('utf-8')
            return str(s)
        except:
            try:
                return str(s).encode('utf-8')
            except:
                return None

def __validate_boolean(field_name):
    def dovalidate(arg):
        if type(arg) != bool:
            return HttpResponse('"Invalid \\"%s\\" argument, it should be a json boolean"' % field_name, status=400)
    return dovalidate

def __validate_docid(docid):
    """
    Validates that a document id is a string, a unicode, or an int (for backwards compatibility).
    It can't be empty, nor longer than 1024 bytes.
    Valid inputs
    >>> __validate_docid("a")
    >>> __validate_docid("\xc3\xb1")
    >>> __validate_docid(u"\xc3\xb1")
    >>> # for backwards compatibility
    >>> __validate_docid(123)
    >>> __validate_docid(0)
    >>> __validate_docid(-1)

    Validate length
    >>> __validate_docid("a"*1024)
    >>> __validate_docid(u"a"*1024)
    >>> # 512 2-byte chars are ok
    >>> __validate_docid("\xc3\xb1"*512)
    >>> e = __validate_docid("a"*1025)
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_docid(u"\xc3"*1025)
    >>> isinstance(e, HttpResponse)
    True
    >>> # 512 2-byte chars are not ok
    >>> e = __validate_docid("\xc3\xb1"*513)
    >>> isinstance(e, HttpResponse)
    True

    Validate emptyness
    >>> e = __validate_docid(" ")
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_docid("")
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_docid(" "*80)
    >>> isinstance(e, HttpResponse)
    True

    Validate not supported types
    >>> e = __validate_docid(80.0)
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_docid([1,2,3])
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_docid({"a":"b"})
    >>> isinstance(e, HttpResponse)
    True

    Validate None
    >>> e = __validate_docid(None)
    >>> isinstance(e, HttpResponse)
    True
    
    
    """
    if type(docid) in [int, long]:
        docid = str(docid)
    
    if not type(docid) in [str,unicode]:
        return HttpResponse('"Invalid docid, it should be a String."', status=400)

    if docid.strip() == '':
        return HttpResponse('"Invalid docid, it shouldnt be empty."', status=400)

    udocid = _encode_utf8(docid)
    if len(udocid) > 1024:
        return HttpResponse('"Invalid docid, it shouldnt be longer than 1024 bytes. It was %d"'%len(udocid), status=400)


def __parse_docid(docid):
    if not type(docid) in [str,unicode]:
        docid = str(docid)
    return docid
            
def __str_is_integer(val):
    try:
        i = int(val)
        return True
    except:
        return False

def __validate_fields(fields):
    """
    Validates that a document fields is a dictionary with string (or unicode) keys and string (or unicode) values.
    The only exception is 'timestamp', that can be an int or a string representation of an int.

    The sum of the sizes of all the field values can not be bigger than 100kb.
    Returns nothing, unless a validation error was found. In that case, it returns an HttpResponse with the error as body.

    Validate documents without errors
    >>> __validate_fields({'field1':'value1', 'field2':'value2'})
    >>> __validate_fields({'text':'', 'title':u''})
    >>> __validate_fields({'text':u'just one field'})
    >>> __validate_fields({'field1':'value1 and value2 and value 3 or value4', 'field2':'value2', 'field3':'123'})
   
    Validate documents with errors on field values (int, float, array, dict and None)
    As the input for this method comes from json, there can't be objects as values
    >>> __validate_fields({'text': 123})
    >>> __validate_fields({'text': 42.8})
    
    >>> e = __validate_fields({'text': ['123']})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields({'text': None})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields({'text': {'k':'v'}})
    >>> isinstance(e,HttpResponse)
    True
    
    Validate documents with errors on field names (int, float and None)
    As the input for this method comes from json, there can't be objects as keys
    >>> e = __validate_fields({None: '123'})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields({123: 'text'})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields({42.5: 'value'})
    >>> isinstance(e,HttpResponse)
    True
    
    Validate timestamps
    >>> __validate_fields({'timestamp': 123, 'field1':'value1'})
    >>> __validate_fields({'timestamp': '123', 'fieldN':'valueN'})
    >>> __validate_fields({'timestamp': -123, 'field1':'value1'})
    >>> __validate_fields({'timestamp': '-123', 'fieldN':'valueN'})
    >>> e = __validate_fields({'timestamp': 'something', 'fieldN': 'valueN'})
    >>> isinstance(e,HttpResponse)
    True

    Validate document size
    >>> __validate_fields({'text': 'a'*1024})
    >>> __validate_fields({'text': 'a'*1024, 'title':'b'*1024})
    >>> # this is the boundary case for 1 field
    >>> __validate_fields({'text': 'a'*1024*100})
    >>> # a boundary case for 2 fields .. 1 * 9 * 1024 + 10 * 9 * 1024
    >>> __validate_fields({'text': 'a'*9*1024, 'title': 'a b c d e '*9*1024})
    >>> # a boundary case for 2-byte chars on fields
    >>> __validate_fields({'text': '\xc3\xb1'*100*512})
    >>> # this is an error case for 1 field
    >>> e = __validate_fields({'text': 'a'*1024*101})
    >>> isinstance(e,HttpResponse)
    True
    >>> # this is an error case for 2 fields
    >>> e = __validate_fields({'text': 'a'*50*1024, 'title': 'a b c d e '*9*1024})
    >>> isinstance(e,HttpResponse)
    True
    >>> # this is an error case for 10 fields .. 10 * ( 1024 * 11 ) 
    >>> fields = {}
    >>> fields.update([("text%d"%i,"123 456 789"*1024) for i in range(0,10)])
    >>> e = __validate_fields(fields)
    >>> isinstance(e,HttpResponse)
    True
    >>> # this is an error case for 2-byte chars on fields
    >>> e = __validate_fields({"text":"\xc3\xb1"*100*513})
    >>> isinstance(e,HttpResponse)
    True
    >>> # disallow no fields
    >>> e = __validate_fields({})
    >>> isinstance(e,HttpResponse)
    True

    >>> # disallow None, Arrays, Numbers and Strings
    >>> e = __validate_fields(None)
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields([1, 2, 3])
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields(123)
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields("this is some text")
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_fields(True)
    >>> isinstance(e,HttpResponse)
    True

    """
    
    if not fields:
        return HttpResponse('"At least one field is required. If you\'re trying to delete the document, you should use the delete api"', status=400)
    
   
    if not isinstance(fields, dict):
        return HttpResponse('"fields should be a JSON Object, e.g: {\'text\': \'something\'} "', status=400)


    for k, v in fields.iteritems():
        # timestamp gets special treatment, it should be an integer
        if 'timestamp' == k:
            if not type(v) == int and not (type(v) == str and __str_is_integer(v)):
                return HttpResponse('"Invalid timestamp: %s. It should be an integer."' % fields['timestamp'], status=400)
            continue
        
        # any other key should be a string or unicode
        if not isinstance(k,str) and not isinstance(k,unicode):
            return HttpResponse('"Name for field %s is not a String"' % (k), status=400)
        

        if isinstance(v,int) or isinstance(v,float):
            v = str(v) 
        if not isinstance(v,str) and not isinstance(v,unicode):
            return HttpResponse('"Value for field %s is not a String nor a number"' % (k), status=400)
        
        ev = _encode_utf8(v)
        ek = _encode_utf8(k)
        
        if ek is None:
            return HttpResponse('"Invalid name for field %s"' % (k), status=400)
        if ev is None:
            return HttpResponse('"Invalid content for field %s: %s"' % (k, v), status=400)

    # verify document size
    doc_size = sum(map(lambda (k,v) : len(v) if type(v) in [str, unicode] else 0, fields.iteritems()))
    if doc_size > 1024 * 100:
        return HttpResponse('"Invalid document size. It shouldn\'t be bigger than 100KB. Got %d bytes"' % (doc_size), status=400)
      

def __parse_fields(fields):
    if 'timestamp' not in fields:
        fields['timestamp'] = str(int(time.time()))
    for k, v in fields.iteritems():
        fields[k] = _encode_utf8(v)
    return fields

def __validate_categories(categories):
    """
    Validates that a document categories is a dictionary with string (or unicode) keys and string (or unicode) values.
    Returns nothing, unless a validation error was found. In that case, it returns an HttpResponse with the error as body

    Validate categories without errors
    >>> __validate_categories({'field1':'value1', 'field2':'value2'})
    >>> __validate_categories({'text':'', 'title':u''})
    >>> __validate_categories({'text':u'just one field'})
    >>> __validate_categories({'field1':'value1 and value2 and value 3 or value4', 'field2':'value2', 'field3':'123'})
   
    Validate documents with errors on category values (int, float, array, dict and None)
    As the input for this method comes from json, there can't be objects as values
    >>> e = __validate_categories({'text': 123})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_categories({'text': 42.8})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_categories({'text': ['123']})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_categories({'text': None})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_categories({'text': {'k':'v'}})
    >>> isinstance(e,HttpResponse)
    True
    
    Validate documents with errors on category names (int, float and None)
    As the input for this method comes from json, there can't be objects as keys
    >>> e = __validate_categories({None: '123'})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_categories({123: 'text'})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_categories({42.5: 'value'})
    >>> isinstance(e,HttpResponse)
    True
    """
    for k, v in categories.iteritems():
        ev = _encode_utf8(v)
        ek = _encode_utf8(k)
    
        if not isinstance(k,str) and not isinstance(k,unicode):
            return HttpResponse('"Name for category %s is not a String"' % (k), status=400)
        
        if not isinstance(v,str) and not isinstance(v,unicode):
            return HttpResponse('"Value for category %s is not a String"' % (k), status=400)

        if ek is None:
            return HttpResponse('"Invalid name for category %s"' % (k), status=400)
        if ev is None:
            return HttpResponse('"Invalid content for category %s: %s"' % (k, v), status=400)
            
def __parse_categories(categories):
    parsed = {}
    for k, v in categories.iteritems():
        parsed[k] = _encode_utf8(v).strip()
    return parsed


def __validate_variables(variables):
    """
    Validates that variables for a document is a dict with string representations of positive ints as keys and floats as values

    variable mappings without errors
    >>> __validate_variables({"4":8, "5":2.5})
    >>> __validate_variables({"1":2})
    >>> __validate_variables({"10":2})
    >>> # the next line is kinda valid. "2" can be parsed to float.
    >>> __validate_variables({"1":"2"})
    

    variable mappings with errors on keys
    >>> e = __validate_variables({"-10":2})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_variables({"var1":2})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_variables({"10":2, "v3":4.5})
    >>> isinstance(e,HttpResponse)
    True
    
    variable mappings with errors on values
    >>> e = __validate_variables({"1":[2.5]})
    >>> isinstance(e,HttpResponse)
    True
    >>> e = __validate_variables({"1":2, "2":{2.5:2}})
    >>> isinstance(e,HttpResponse)
    True
    
    """
    for k, v in variables.iteritems():
        if not k.isdigit():
            return HttpResponse('"Invalid variable index: %s. It should be integer."' % k, status=400)
        try:
            float(v)
        except (ValueError, TypeError):
            return HttpResponse('"Invalid variable value for index %s: %s. It should be a float"' % (k,v), status=400)
            

def __parse_variables(variables):
    parsed = {}
    for k, v in variables.iteritems():
        parsed[int(k)] = float(v)
    return parsed

def __validate_document(document):
    if type(document) is not dict:
        return HttpResponse('"Document should be a JSON object"', status=400)
    if 'docid' not in document:
        return HttpResponse('"Document should have a docid attribute"', status=400)
    if 'fields' not in document:
        return HttpResponse('"Document should have a fields attribute"', status=400)
    response = None
    response = response or __validate_docid(document['docid'])
    response = response or __validate_fields(document['fields'])
    if 'variables' in document:
        response = response or __validate_variables(document['variables'])
    if 'categories' in document:
        response = response or __validate_categories(document['categories'])
    if response:
        return response
        
def __parse_document(document):
    document['docid'] = __parse_docid(document['docid'])
    document['fields'] = __parse_fields(document['fields'])
    if 'variables' in document:
        document['variables'] = __parse_variables(document['variables'])
    if 'categories' in document:
        document['categories'] = __parse_categories(document['categories'])
    return document

def __validate_query(query):
    """
    Validates that a query is a string or a unicode.
    It can't be empty.
    Valid inputs
    >>> __validate_query("a")
    >>> __validate_query("\xc3\xb1")
    >>> __validate_query(u"\xc3\xb1")
    
    Validate emptyness
    >>> e = __validate_query(" ")
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_query("")
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_query(" "*80)
    >>> isinstance(e, HttpResponse)
    True

    Validate not supported types
    >>> e = __validate_query(80.0)
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_query([1,2,3])
    >>> isinstance(e, HttpResponse)
    True
    >>> e = __validate_query({"a":"b"})
    >>> isinstance(e, HttpResponse)
    True

    Validate None
    >>> e = __validate_query(None)
    >>> isinstance(e, HttpResponse)
    True
    """
    
    if query is None:
        return HttpResponse('"Invalid query. It cannot be NULL"', status=400)

    if type(query) not in [str,unicode]:
        return HttpResponse('"Invalid query. It MUST be a String"', status=400)
    
    if query.strip() == '' :
        return HttpResponse('"Invalid query. It cannot be a empty"', status=400)
        
def __parse_query(query):
    return _encode_utf8(query.lower()) 

""" Argument validation decorators """
required_index_name = non_empty_argument('index_name', 'Index name cannot be empty')

""" Data validation decorators """
required_categories_data = required_data('categories', __validate_categories, __parse_categories)
required_variables_data = required_data('variables', __validate_variables, __parse_variables)
required_fields_data = required_data('fields', __validate_fields, __parse_fields)
required_docid_data = required_data('docid', __validate_docid, __parse_docid)
optional_public_search_data = optional_data('public_search', __validate_boolean('public_search'))
optional_docid_data = optional_data('docid', __validate_docid, __parse_docid)
required_definition_data = required_data('definition')
required_query_data = required_data('query', __validate_query, __parse_query)
optional_variables_data = optional_data('variables', __validate_variables, __parse_variables)
required_integer_function = int_argument('function', 'Function number should be a non-negative integer')

def required_documents(func):
    def decorated(self, request, data, **kwargs):
        if type(data) is list:
            if not data:
                return HttpResponse('"Invalid batch insert. At least one document is required"', status=400)
            for i in xrange(len(data)):
                response = __validate_document(data[i])
                if response:
                    response.content = '"Invalid batch insert, in document #%d of %d: %s"' % (i+1, len(data), response.content[1:-1])
                    return response
                data[i] = __parse_document(data[i])
            kwargs['batch_mode'] = True
            kwargs['documents'] = data
        else:
            response = __validate_document(data)
            if response:
                return response
            kwargs['batch_mode'] = False
            kwargs['documents'] = [__parse_document(data)]
        return func(self, request, data=data, **kwargs)
    return decorated

def required_docids(func):
    def decorated(self, request, data, **kwargs):

        if not data:
            docids = request.GET.getlist('docid')
            if docids:
                if len(docids) > 1:
                    data = []
                    for docid in docids:
                        data.append({'docid':docid})
                else:
                    data = {'docid':docids[0]}
            else:
                return HttpResponse('"If no body is given, you should include a docid argument in the querystring"', status=400)
        
        if type(data) is list:
            if not data:
                return HttpResponse('"Invalid batch delete. At least one docid is required"', status=400)
            for i in xrange(len(data)):
                if not data[i].has_key('docid'):
                    return HttpResponse('"Invalid batch delete. Document #%d of %d doesn\'t have a docid parameter"' % (i+1, len(data)), status=400)

                response = __validate_docid(data[i]['docid'])
                if response:
                    response.content = '"Invalid batch delete, in docid #%d of %d: %s"' % (i+1, len(data), response.content[1:-1])
                    return response
                data[i]['docid'] = __parse_docid(data[i]['docid'])
            kwargs['bulk_mode'] = True
            kwargs['documents'] = data
        else:
            if 'docid' in data:
                response = __validate_docid(data['docid'])
                if response:
                    response.content
                    return response
                data['docid'] = __parse_docid(data['docid'])
                kwargs['bulk_mode'] = False
                kwargs['documents'] = [data]
            else:
                return HttpResponse('"Argument docid is required in the request body"', status=400)
        return func(self, request, data=data, **kwargs)
    return decorated

""" Shared bulk delete code """
def delete_docs_from_index(resource, index, documents):
    """
        resource: A Resource (from restresource.py). Needed just to LOG errors
        index: The index to delete documents from. Every deploy for that index will be hit.
        documents: list of documents to delete. **Need** 'docid' on each of them.
    """
    indexers = rpc.get_indexer_clients(index)

    try:
        responses = []

        for doc in documents:
            ret = {'deleted': True}
            try:
                for indexer in indexers:
                    indexer.delDoc(doc['docid'])
            except Exception:
                resource.logger.exception('"Failed to delete %s on %s (%s)', doc['docid'], index.code, index.name)
                resource.error_logger.exception('"Failed to delete %s on %s (%s)', doc['docid'], index.code, index.name)
                ret['deleted'] = False
                ret['error'] = '"Currently unable to delete the requested document"'
        
            responses.append(ret)
        return responses
    finally:
        rpc.close_thrift(indexers)
 
""" Util functions for request processing """
def metadata_for_index(index):
    return dict(code=index.code, creation_time=index.creation_time.isoformat(), started=index.is_ready(), size=index.current_docs_number, public_search=index.public_api, status=index.status)

def build_logrecord_for_add(index, document):
    return ttypes.LogRecord(index_code=index.code, 
                            docid=document['docid'], 
                            deleted=False, 
                            fields=document['fields'],
                            variables=document.get('variables', {}), 
                            categories=document.get('categories', {}))

def build_logrecord_for_delete(index, document):
    return ttypes.LogRecord(index_code=index.code, 
                            docid=document['docid'], 
                            deleted=True)
log_writers = None
log_addresses = None


def send_log_storage_batch(resource, index, records):
    global log_addresses
    global log_writers
    try:
        storage_services = Service.objects.filter(name='storage')
        if storage_services:
            addresses = set((service.host, int(service.port), service.type) for service in storage_services)
            if addresses != log_addresses:
                log_writers = [(rpc.getReconnectingLogWriterClient(h,p), t == 'optional') for h,p,t in addresses]
                log_addresses = addresses
            for writer, optional in log_writers:
                try:
                    writer.send_batch(ttypes.LogBatch(records=records))
                except:
                    if optional:
                        resource.logger.exception('Optional storage failed to receive batch - IGNORING. %d records for index %s', len(records), index.code)
                        resource.error_logger.exception('Optional storage failed to receive batch - IGNORING. %d records for index %s', len(records), index.code)
                    else:
                        raise
                        
            return True
        else:
            resource.logger.error('No storage services found. %d records for index %s', len(records), index.code)
            resource.error_logger.error('No storage services found. %d records for index %s', len(records), index.code)
            return False
    except:
        resource.logger.exception('Error sending batch to log storage. %d records for index %s', len(records), index.code)
        resource.error_logger.exception('Error sending batch to log storage. %d records for index %s', len(records), index.code)
        return False

""" 
    Version resource ======================================================
""" 
class Version(Resource):
    authenticated = False
    def GET(self, request, version):
        return HttpResponse('"API V %s : Documentation"' % version)

""" 
    Indexes resource ======================================================
""" 
class Indexes(Resource):
    authenticated = True
    def GET(self, request, version):
        metadata = {}
        for index in self.get_account().indexes.all():
            metadata[index.name] = metadata_for_index(index)
        # 200 OK : json of the indexes metadata
        return JsonResponse(metadata)

""" 
    Index resource ======================================================
""" 
class Index(Resource):
    authenticated = True
    
    # gets index metadata
    @required_index_name
    @get_index_param_or404
    def GET(self, request, version, index):
        return JsonResponse(metadata_for_index(index))
    
    # creates a new index for the given name
    @required_index_name
    @optional_public_search_data
    def PUT(self, request, data, version, index_name, public_search=None):
        account = self.get_account()
        
        indexes = account.indexes.filter(name=index_name)
        if indexes.count() > 1:
            self.logger.exception('Inconsistent state: more than one index with name %s', index_name)
            self.error_logger.exception('Inconsistent state: more than one index with name %s', index_name)
            
            return HttpResponse('Unable to create/update your index. Please contact us.', status=500)
        elif indexes.count() == 1:
            if not public_search is None:
                index = indexes[0]
                index.public_api = public_search
                index.save()

            # 204 OK: index already exists
            return HttpResponse(status=204)
        else:
            current_count = account.indexes.filter(deleted=False).count()
            max_count = account.package.max_indexes

            if not current_count < max_count:
                msg = '"Unable to create. Too many indexes for the account (maximum: %d)"' % max_count
                return HttpResponse(msg, status=409) #conflict
            
            # basic index data
            try:
                index = account.create_index(index_name, public_search)
            except IntegrityError:
                return HttpResponse(status=204) # already exists
            
            mail.report_new_index(index)
            
            # 201 OK : index created
            return JsonResponse(metadata_for_index(index), status=201)
    

    @required_index_name
    @get_index_param
    def DELETE(self, request, data, version, index):
        if not index:
            return HttpResponse(status=204)   
        deploy_manager = rpc.get_deploy_manager()
        try:
            deploy_manager.delete_index(index.code)
        finally:
            rpc.close_thrift(deploy_manager)
        mail.report_delete_index(index)
        return HttpResponse()
    

""" 
    Document resource ======================================================
""" 
class Document(Resource):
    authenticated = True
    
    @required_index_name
    @required_querystring_argument('docid')
    @get_index_param_or404
    def GET(self, request, version, index, docid):
        self.logger.debug('id=%s', docid)
        doc = storage.storage_get(index.code, docid)
        if doc is None:
            raise Http404
        self.set_message('Retrieved document %s' % docid)
        return JsonResponse(doc)
    
    def _insert_document(self, index, indexers, document):
        tdoc = ttypes.Document(fields=document['fields'])
        docid = document['docid']
        variables = document.get('variables', {})
        categories = document.get('categories', {})
        
        success = { 'added': True }
        try:
            for indexer in indexers:
                indexer.addDoc(docid, tdoc, int(tdoc.fields['timestamp']), variables)
                if categories:
                    indexer.updateCategories(docid, categories)
                    
        except Exception, e:
            self.logger.exception('Failed to index %s on %s (%s)', docid, index.code, index.name)
            self.error_logger.exception('Failed to index %s on %s (%s)', docid, index.code, index.name)
            success['added'] = False
            success['error'] = '"Currently unable to index the requested document"'

        return success

    def _validate_variables(self, index, documents):    
        max_variables = index.configuration.get_data().get('max_variables')
        for i in xrange(len(documents)):
            if 'variables' in documents[i]:
                for k in documents[i]['variables'].keys():
                    if k < 0 or k >= max_variables:
                        if len(documents) == 1:
                            return HttpResponse('"Invalid key in variables: \'%d\' (it should be in the range [0..%d]"' % (k, max_variables-1), status=400)
                        else:
                            return HttpResponse('"Invalid batch insert, in document #%d of %d: Invalid variable index %d. Valid keys are in range [0-%d]"' % (i+1, len(documents), k, max_variables-1), status=400)
        
    @required_index_name
    @required_documents
    @get_index_param_or404
    @wakeup_if_hibernated
    def PUT(self, request, data, version, index, documents, batch_mode):
        if batch_mode:
            self.logger.debug('batch insert: %d docs', len(documents))
        else:
            self.logger.debug('id=%s fields=%s variables=%s categories=%s', documents[0].get('docid'), documents[0].get('fields'), documents[0].get('variables'), documents[0].get('categories'))
            
        if not index.is_ready():
            return HttpResponse('"Index is not ready."', status=409)
        
        response = self._validate_variables(index, documents)
        if response:
            return response
        
        rt = []
        
        indexers = rpc.get_indexer_clients(index)
        
        try:
            if LOG_STORAGE_ENABLED:
                records = [build_logrecord_for_add(index, d) for d in documents]
                if not send_log_storage_batch(self, index, records):
                    return HttpResponse('"Currently unable to insert the requested document(s)."', status=503)
        
            for document in documents:
                rt.append(self._insert_document(index, indexers, document))
        
            if not batch_mode:
                if rt[0]['added']:
                    return HttpResponse()
                else:
                    return HttpResponse(rt[0]['error'], status=503)
            
            return JsonResponse(rt)
        finally:
            rpc.close_thrift(indexers)




    @required_index_name
    @required_docids
    @get_index_param_or404
    @wakeup_if_hibernated
    def DELETE(self, request, data, version, index, documents, bulk_mode):
        if bulk_mode:
            self.logger.debug('bulk delete: %s docids', len(documents))
        else:
            self.logger.debug('id=%s qsid=%s', data['docid'], request.GET.get('docid'))
        
        if not index.is_ready():
            return HttpResponse('"Index is not ready"', status=409)
        
        if LOG_STORAGE_ENABLED:
            records = [build_logrecord_for_delete(index, d) for d in documents]
            
            if not send_log_storage_batch(self, index, records):
                return HttpResponse('"Currently unable to delete the requested document."', status=503)

        indexers = rpc.get_indexer_clients(index)
        
        try:
            responses = delete_docs_from_index(self, index, documents)

            if not bulk_mode:
                if responses[0]['deleted']:
                    return HttpResponse()
                else:
                    return HttpResponse(responses[0]['error'], status=503)
            
            return JsonResponse(responses)
        finally:
            rpc.close_thrift(indexers)

       
""" 
    Categories resource  ======================================================
""" 
class Categories(Resource):
    authenticated = True
    
    @required_index_name
    @required_docid_data
    @required_categories_data
    @get_index_param_or404
    @wakeup_if_hibernated
    def PUT(self, request, data, version, categories, index, docid):
        self.logger.debug('id=%s categories=%s', docid, categories)
        
        if not index.is_writable():
            return HttpResponse('"Index is not ready"', status=409)
        
        if LOG_STORAGE_ENABLED:
            records = [ttypes.LogRecord(index_code=index.code, docid=docid, deleted=False, categories=categories)]
            if not send_log_storage_batch(self, index, records):
                return HttpResponse('"Currently unable to update the requested document."', status=503)

        
        indexers = rpc.get_indexer_clients(index)
        
        try:
            failed = False
            for indexer in indexers:
                try:
                    indexer.updateCategories(docid, categories)
                except Exception, e:
                    if isinstance(e, ttypes.IndextankException):
                        return HttpResponse(e.message, status=400)
                    else:
                        self.logger.exception('Failed to update variables for %s on %s (%s)', docid, index.code, index.name)
                        self.error_logger.exception('Failed to update variables for %s on %s (%s)', docid, index.code, index.name)
                        failed = True
                        break                
        
            if failed:
                return HttpResponse('"Currently unable to update the categories for the requested document."', status=503)
            else:
                self.set_message('Updated categories for %s' % docid)            
                return HttpResponse()
        finally:
            rpc.close_thrift(indexers)
       

""" 
    Variables resource  ======================================================
""" 
class Variables(Resource):
    authenticated = True
    
    @required_index_name
    @required_docid_data
    @required_variables_data
    @get_index_param_or404
    @wakeup_if_hibernated
    def PUT(self, request, data, version, variables, index, docid):
        self.logger.debug('id=%s variables=%s', docid, variables)
        
        if not index.is_writable():
            return HttpResponse('"Index is not ready"', status=409)
        
        if LOG_STORAGE_ENABLED:
            records = [ttypes.LogRecord(index_code=index.code, docid=docid, deleted=False, variables=variables)]
            if not send_log_storage_batch(self, index, records):
                return HttpResponse('"Currently unable to update the requested document."', status=503)

        
        indexers = rpc.get_indexer_clients(index)
        
        try:
            failed = False
            for indexer in indexers:
                try:
                    indexer.updateBoost(docid, variables)
                except Exception, e:
                    if isinstance(e, ttypes.IndextankException) and e.message.startswith('Invalid boost index'):
                        return HttpResponse(e.message.replace('boost', 'variable'), status=400)
                    else:
                        self.logger.exception('Failed to update variables for %s on %s (%s)', docid, index.code, index.name)
                        self.error_logger.exception('Failed to update variables for %s on %s (%s)', docid, index.code, index.name)
                        failed = True
                        break                
        
            if failed:
                return HttpResponse('"Currently unable to index the requested document."', status=503)
            else:
                self.set_message('Updated variables for %s' % docid)            
                return HttpResponse()
        finally:
            rpc.close_thrift(indexers)
       
""" 
    Functions resource ======================================================
""" 
class Functions(Resource):
    # gets the functions metadata
    @required_index_name
    @get_index_param_or404
    @wakeup_if_hibernated
    def GET(self, request, version, index):
        #asking for writability in a get sounds odd... but jorge and spike
        #think it's ok for functions.
        if not index.is_writable():
            return HttpResponse('"Index not ready to list functions."', status=409)

        indexers = rpc.get_indexer_clients(index)
        try:
            functions = indexers[0].listScoreFunctions()
            return JsonResponse(functions)
        finally:
            rpc.close_thrift(indexers)
    

""" 
    Function resource ======================================================
""" 
class Function(Resource):
    authenticated = True
    
    
    # TODO GET could return the function definition 
    
    # writes a function for the given number
    @required_index_name 
    @required_integer_function
    @required_definition_data
    @get_index_param_or404
    @wakeup_if_hibernated
    def PUT(self, request, data, version, index, function, definition):
        self.logger.debug('f=%d', function)

        if (function < 0):
            return HttpResponse('"Function index cannot be negative."', status=400)
                
        if not index.is_writable():
            return HttpResponse('"Index is not writable"', status=409)

        indexers = rpc.get_indexer_clients(index)
        
        try:
            failed = False
            for indexer in indexers:
                try:
                    indexer.addScoreFunction(function, definition)
                except:
                    self.logger.warn('Failed to add function %s with definition: %s', function, data)
                    failed = True
                    break
    
            if failed:
                return HttpResponse('"Unable to add the requested function. Check your syntax."', status=400)
            else:
                sf, _ = ScoreFunction.objects.get_or_create(index=index, name=function)
                sf.definition = definition
                sf.save()
            
                self.set_message('set to %s' % (definition))
                return HttpResponse()
        finally:
            rpc.close_thrift(indexers)
            
    @required_index_name
    @required_integer_function
    @get_index_param_or404
    @wakeup_if_hibernated
    def DELETE(self, request, data, version, index, function):
        self.logger.debug('f=%d', function)
        
        if (function < 0):
            return HttpResponse('"Function index cannot be negative."', status=400)
        
        if not index.is_writable():
            return HttpResponse('"Index is not writable"', status=409)

        indexers = rpc.get_indexer_clients(index)
        
        try:
            failed = False
            for indexer in indexers:
                try:
                    indexer.removeScoreFunction(function)
                except:
                    self.logger.exception('Failed to remove function %s', function)
                    self.error_logger.exception('Failed to remove function %s', function)
                    failed = True
                    break
    
            if failed:
                return HttpResponse('"Failed to remove the requested function."', status=503)
            else:
                models.ScoreFunction.objects.filter(index=index, name=function).delete()
                return HttpResponse()
        finally:
            rpc.close_thrift(indexers)
    
builtin_len = len
""" 
    Search resource ======================================================
""" 
class Search(Resource):
    authenticated = False
    
    @required_index_name
    @required_querystring_argument('q')
    @int_querystring('start')
    @int_querystring('function')
    @json_querystring('category_filters')
    def DELETE(self, request, version, index_name, q, start=0, function=0, category_filters={}, data=None):
        #kwarg 'data' is added in Resource.dispatch for 'DELETE' requests
        self.logger.debug('f=%d pag=%d q=%s', function, start, q)
        index = self.get_index_or_404(index_name)
        
        authorize_response = self._check_authorize(request)
        if authorize_response:
            return authorize_response
    
        if not index.is_readable():
            return HttpResponse('"Index is not searchable"', status=409)
        
        if not index.is_writable():
            return HttpResponse('"Index is not writable"', status=409)
        q = _encode_utf8(q)
        
        if start > 5000:
          return HttpResponse('"Invalid start parameters (start shouldn\'t exceed 5000)"', status=400)

        query_vars = {}
        for i in xrange(10):
            k = 'var%d' % i
            if k in request.GET:
                try:
                    v = float(request.GET[k])
                except ValueError:
                    return HttpResponse('"Invalid query variable, it should be a decimal number (var%d = %s)"', status=400)
                query_vars[i] = v

        # range facet_filters
        function_filters = []
        docvar_filters = []
        docvar_prefix = ''
        function_prefix = 'filter_function'
        
        for key in request.GET.keys():
            doc_match = re.match('filter_docvar(\\d+)',key)
            func_match = re.match('filter_function(\\d+)',key)
            if doc_match:
                self.logger.info('got docvar filter: ' + request.GET[key])
                extra_filters = self._get_range_filters(int(doc_match.group(1)), request.GET[key])
                if extra_filters == None:
                    return HttpResponse('"Invalid document variable range filter (' + request.GET[key] + ')"', status=400)
                docvar_filters.extend(extra_filters)
            elif func_match:
                extra_filters = self._get_range_filters(int(func_match.group(1)), request.GET[key])
                if extra_filters == None:
                    return HttpResponse('"Invalid function range filter (' + request.GET[key] + ')"', status=400)
                function_filters.extend(extra_filters)
            
        facet_filters = []
        for k,v in category_filters.items():
            if type(v) is str or type(v) is unicode:
                facet_filters.append(ttypes.CategoryFilter(_encode_utf8(k), _encode_utf8(v)))
            elif type(v) is list:
                for element in v:
                    facet_filters.append(ttypes.CategoryFilter(_encode_utf8(k), _encode_utf8(element)))
            else:
                return HttpResponse('"Invalid facets filter"', status=400)
                
        extra_parameters = {}
        
        searcher = rpc.get_searcher_client(index)
        if searcher is None:
            self.logger.warn('cannot find searcher for index %s (%s)', index.name, index.code)
            self.error_logger.warn('cannot find searcher for index %s (%s)', index.name, index.code)
            return HttpResponse('"Currently unable to perform the requested query"', status=503)

        try:
            len = 1000
            iterations = None
            while True:
                if iterations is not None:
                    iterations -= 1
                    if iterations < 0:
                        return HttpResponse('"Currently unable to perform the requested query - some or all documents may not have been deleted."', status=503)
                try:
                    rs = searcher.search(q, start, len, function, query_vars, facet_filters, docvar_filters, function_filters, extra_parameters)
                except ttypes.InvalidQueryException, iqe:
                    return HttpResponse('"Invalid query: %s"' % q, status=400)
                except ttypes.MissingQueryVariableException, qve:
                    return HttpResponse('"%s"' % qve.message, status=400)
                except ttypes.IndextankException, ite:
                    if ite.message == 'Invalid query':
                        return HttpResponse('"Invalid query: %s"' % q, status=400)
                    else:
                        self.logger.exception('Unexpected IndextankException while performing query')
                        self.error_logger.exception('Unexpected IndextankException while performing query')
                        if iterations is None:
                            return HttpResponse('"Currently unable to perform the requested query."', status=503)
                        else:
                            continue
            
                if iterations is None:
                    iterations = ((rs.matches - start) / len) * 2
            
                self.logger.debug('query delete: %s docids', rs.matches) 

                if LOG_STORAGE_ENABLED:
                    records = [build_logrecord_for_delete(index, d) for d in rs.docs]
            
                    if not send_log_storage_batch(self, index, records):
                        continue

                delete_docs_from_index(self, index, rs.docs)
                if (rs.matches - start) < len:
                    break

            return HttpResponse()
        finally:
            rpc.close_thrift(searcher)
    
    @required_index_name
    @required_querystring_argument('q')
    @int_querystring('start')
    @int_querystring('len')
    @int_querystring('function')
    @querystring_argument('fetch')
    @querystring_argument('fetch_variables')
    @querystring_argument('fetch_categories')
    @querystring_argument('snippet')
    @querystring_argument('snippet_type')
    @json_querystring('category_filters')
    @querystring_argument('callback')
    @get_index_param_or404
    @check_public_api
    @wakeup_if_hibernated
    def GET(self, request, version, index, q, start=0, len=10, function=0, fetch='', fetch_variables='', fetch_categories='', snippet='', snippet_type='', category_filters={}, callback=None):
        self.logger.debug('f=%d pag=%d:%d q=%s snippet=%s fetch=%s fetch_variables=%s fetch_categories=%s ', function, start, start+len, q, snippet, fetch, fetch_variables, fetch_categories)
        
        dymenabled = index.configuration.get_data().get('didyoumean')
        
        if not index.is_readable():
            return HttpResponse('"Index is not searchable"', status=409)
        
        q = _encode_utf8(q)
        q = self._sanitize_query(q)
        
        if start + len > 5000:
          return HttpResponse('"Invalid start and len parameters (start+len shouldn\'t exceed 5000)"', status=400)

        query_vars = {}
        for i in xrange(10):
            k = 'var%d' % i
            if k in request.GET:
                try:
                    v = float(request.GET[k])
                except ValueError:
                    return HttpResponse('"Invalid query variable, it should be a decimal number (var%d = %s)"', status=400)
                query_vars[i] = v

        # range facet_filters
        function_filters = []
        docvar_filters = []
        docvar_prefix = ''
        function_prefix = 'filter_function'
        
        for key in request.GET.keys():
            doc_match = re.match('filter_docvar(\\d+)',key)
            func_match = re.match('filter_function(\\d+)',key)
            if doc_match:
                self.logger.info('got docvar filter: ' + request.GET[key])
                extra_filters = self._get_range_filters(int(doc_match.group(1)), request.GET[key])
                if extra_filters == None:
                    return HttpResponse('"Invalid document variable range filter (' + request.GET[key] + ')"', status=400)
                docvar_filters.extend(extra_filters)
            elif func_match:
                extra_filters = self._get_range_filters(int(func_match.group(1)), request.GET[key])
                if extra_filters == None:
                    return HttpResponse('"Invalid function range filter (' + request.GET[key] + ')"', status=400)
                function_filters.extend(extra_filters)
            
        facet_filters = []
        for k,v in category_filters.items():
            if type(v) is str or type(v) is unicode:
                facet_filters.append(ttypes.CategoryFilter(_encode_utf8(k), _encode_utf8(v)))
            elif type(v) is list:
                for element in v:
                    facet_filters.append(ttypes.CategoryFilter(_encode_utf8(k), _encode_utf8(element)))
            else:
                return HttpResponse('"Invalid facets filter"', status=400)

        extra_parameters = {}
        if snippet:
            extra_parameters['snippet_fields'] = snippet
        if snippet_type:
            extra_parameters['snippet_type'] = snippet_type
        if fetch:
            extra_parameters['fetch_fields'] = ','.join([f.strip() for f in fetch.split(',')])
        if fetch_variables:
            extra_parameters['fetch_variables'] = fetch_variables
        if fetch_categories:
            extra_parameters['fetch_categories'] = fetch_categories

        
        searcher = rpc.get_searcher_client(index)
        if searcher is None:
            self.logger.warn('cannot find searcher for index %s (%s)', index.name, index.code)
            self.error_logger.warn('cannot find searcher for index %s (%s)', index.name, index.code)
            return HttpResponse('"Currently unable to perform the requested search"', status=503)

        try:
            t1 = time.time()
            rs = searcher.search(q, start, len, function, query_vars, facet_filters, docvar_filters, function_filters, extra_parameters)
            t2 = time.time()
        except ttypes.InvalidQueryException, iqe:
            return HttpResponse('"Invalid query: %s"' % q, status=400)
        except ttypes.MissingQueryVariableException, qve:
            return HttpResponse('"%s"' % qve.message, status=400)
        except ttypes.IndextankException, ite:
            if ite.message == 'Invalid query':
                return HttpResponse('"Invalid query: %s"' % q, status=400)
            else:
                self.logger.exception('Unexpected IndextankException while performing query')
                self.error_logger.exception('Unexpected IndextankException while performing query')
                return HttpResponse('"Currently unable to perform the requested search"', status=503)
        finally:
            rpc.close_thrift(searcher)
            

        formatted_time = '%.3f' % (t2-t1)
        for i in xrange(builtin_len(rs.docs)):
            if rs.variables:
                for k,v in rs.variables[i].iteritems():
                    rs.docs[i]['variable_%d' % k] = v
            if rs.categories:
                for k,v in rs.categories[i].iteritems():
                    rs.docs[i]['category_%s' % k] = v
            if rs.scores:
                rs.docs[i]['query_relevance_score'] = rs.scores[i]
        rsp = dict(matches=rs.matches, results=rs.docs, search_time=formatted_time, facets=rs.facets, query=q)
        #only add didyoumean to customers who have it enabled.
        if dymenabled:
            rsp['didyoumean'] = rs.didyoumean

        return JsonResponse(rsp, callback=callback)
    
    def _get_range_filters(self, id, filter_string):
        filter_strings = filter_string.split(',')
        range_filters = []
        for filter in filter_strings:
            parts = filter.split(':')
            if (len(parts) != 2):
                return None
            
            if parts[0] == '*':
                floor = 0
                no_floor = True
            else:
                try:
                    floor = float(parts[0])
                    no_floor = False
                except ValueError:
                    return None

            if parts[1] == '*':
                ceil = 0
                no_ceil = True
            else:
                try:
                    ceil = float(parts[1])
                    no_ceil = False
                except ValueError:
                    return None
                        
            range_filters.append(ttypes.RangeFilter(key=id, floor=floor, no_floor=no_floor, ceil=ceil, no_ceil=no_ceil))
        
        return range_filters
    
    def _sanitize_query(self, q):
        s = self._try_to_sanitize_parentheses_and_quotes(q)
        s = s.replace(r'{', r'\{')
        s = s.replace(r'}', r'\}')
        s = s.replace(r'[', r'\[')
        s = s.replace(r']', r'\]')
        s = s.replace(r'!', r'\!')
        s = s.replace(r'?', r'\?')
        s = s.replace(r'~', r'\~')
        #s = s.replace(r'*', r'\*')
        s = s.replace(r': ', r'\: ')
        s = s.replace(r' :', r' \:')
        s = s.replace(r'ssh:/', r'ssh\:/')
        s = s.replace(r'ftp:/', r'ftp\:/')
        s = s.replace(r'http:/', r'http\:/')
        s = s.replace(r'https:/', r'https\:/')
        if s != q:
            self.logger.debug('query sanitized it was (%s) now (%s)', q, s)
        return s

    def _try_to_sanitize_parentheses_and_quotes(self, q):
        # should solve most 'solveable' queries
        lp = q.count('(')
        rp = q.count(')')
        while (lp > rp):
            q = q.rstrip()
            q += ')'
            rp += 1
        while (lp < rp):
            q = '(' + q
            lp += 1
        while '()' in q:
            q = q.replace(r'()',r'')
        if (q.count('"') % 2):
            q += '"'
        return q

""" 
    Promote resource ======================================================
""" 
class Promote(Resource):
    authenticated = True
    
    @required_index_name 
    @required_docid_data
    @required_query_data
    @get_index_param_or404
    @wakeup_if_hibernated
    def PUT(self, request, data, version, index, docid, query):
        self.logger.debug('id=%s q=%s', docid, query)
        
        if not index.is_writable():
            return HttpResponse('"Index is not writable"', status=409)
                
        indexers = rpc.get_indexer_clients(index)
        
        try:
            failed = False
            for indexer in indexers:
                try:
                    indexer.promoteResult(docid, query)
                except:
                    self.logger.exception('"Failed to promote result %s for query %s"', docid, query)
                    self.error_logger.exception('"Failed to promote result %s for query %s"', docid, query)
                    failed = True
                    break
    
            if failed:
                return HttpResponse('"Currently unable to perform the requested promote."', status=503)
            else:
                return HttpResponse()
        finally:
            rpc.close_thrift(indexers)
        
""" 
    InstantLinks resource ======================================================
""" 
class InstantLinks(Resource):
    authenticated = False
    
    @required_index_name
    @required_querystring_argument('query', parse=_encode_utf8)
    @querystring_argument('fetch', parse=_encode_utf8)
    @querystring_argument('callback', parse=_encode_utf8)
    @querystring_argument('field', parse=_encode_utf8)
    @get_index_param_or404
    @wakeup_if_hibernated
    def GET(self, request, version, index, query, fetch='name', callback=None, field='name'):
        self.logger.debug('query=%s callback=%s field=%s fetch=%s', query, callback, field, fetch)
        
        if not index.is_readable():
            return HttpResponse('"Index is not readable."', status=409)

        searcher = rpc.get_searcher_client(index)
        if searcher is None:
            self.logger.warn('cannot find searcher for index %s (%s)', index.name, index.code)
            return HttpResponse('"Currently unable to perform the requested search"', status=503)

        suggestor = rpc.get_suggestor_client(index)
        try:
            suggestions = suggestor.complete(query, field)
            if builtin_len(suggestions) == 0:
                rsp = dict(matches=0, results=[],search_time='', facets={})
                return JsonResponse(rsp, callback=callback)

            # got suggestions .. build a query
            print 'suggestions=%s' % suggestions
            query = ' OR '.join( map( lambda x: "(%s)"%x, suggestions))
            query = '%s:(%s)' % (field, query)
            print 'query=%s' % query
            extra_parameters = {}
            extra_parameters['fetch_fields'] = fetch
            try:
                rs = searcher.search(query, 0, 4, 0, {}, {}, {}, {}, extra_parameters)
            except ttypes.IndextankException, ite:
                self.logger.exception('Unexpected IndextankException while performing query for instantlinks')
                self.error_logger.exception('Unexpected IndextankException while performing query for instantlinks')
                return HttpResponse('"Currently unable to perform the requested search"', status=503)
            rsp = dict(matches=rs.matches, results=rs.docs, search_time='', facets=rs.facets)
            return JsonResponse(rsp, callback=callback)
        except:
            self.logger.exception('Failed to provide instant links for "%s"', query)
            self.error_logger.exception('Failed to provide instant links for "%s"', query)
            return HttpResponse('"Currently unable to perform the requested instant links."', status=503)
        finally:
            rpc.close_thrift([searcher, suggestor])
            
        
""" 
    AutoComplete resource ======================================================
""" 
class AutoComplete(Resource):
    authenticated = False
    
    @required_index_name
    @required_querystring_argument('query', parse=_encode_utf8)
    @querystring_argument('callback', parse=_encode_utf8)
    @querystring_argument('field', parse=_encode_utf8)
    @get_index_param_or404
    @wakeup_if_hibernated
    def GET(self, request, version, index, query, callback=None, field='text'):
        self.logger.debug('query=%s callback=%s', query, callback)
        
        if not index.is_readable():
            return HttpResponse('"Index is not readable."', status=409)

        suggestor = rpc.get_suggestor_client(index)
        try:
            suggestions = suggestor.complete(query, field)
            return JsonResponse({'suggestions': suggestions, 'query': query}, callback=callback)
        except:
            self.logger.exception('Failed to provide autocomplete for "%s"', query)
            self.error_logger.exception('Failed to provide autocomplete for "%s"', query)
            return HttpResponse('"Currently unable to perform the requested autocomplete."', status=503)
        finally:
            rpc.close_thrift(suggestor)
            
        
       

"""
    Provisioner for CloudFoundry. This for the transition until we adapt CF to conform to our default provisioner.
""" 
class TransitionCloudFoundryProvisioner(ProvisionerResource):

    @authorized_method
    @required_querystring_argument("code")
    def GET(self, request, code, **kwargs):
        # fetch the account we want info about
        account = Account.objects.get(apikey__startswith=code+"-")
        
        # make sure the provisioner for the account is the same requesting its deletion
        if self.provisioner != account.provisioner:
            return HttpResponse('You are not the provisioner for this account', status=403)
       
        # create the creds
        creds = {
            'INDEXTANK_PRIVATE_API_URL' : account.get_private_apiurl(),
            'INDEXTANK_PUBLIC_API_URL' : account.get_public_apiurl(),
            'INDEXTANK_INDEX_NAMES' : [i.name for i in account.indexes.all()]
        } 
        
        return JsonResponse({"code": account.get_public_apikey(), "config": creds})

    @authorized_method
    @required_data("plan")
    def PUT(self, request, data, **kwargs):
        # only default package right now
        if data['plan'].upper() != "FREE":
            return HttpResponse("Only FREE plan allowed", status=400)
        
        account, _ = Account.create_account(datetime.datetime.now())
        account.status = Account.Statuses.operational
        account.provisioner = self.provisioner
        
        # apply package. see validation above
        account.apply_package(Package.objects.get(name=data['plan'].upper()))
        
        account.save()

        # create an index, using ApiClient
        client = ApiClient(account.get_private_apiurl())
        i = client.create_index("idx")
        
        # ok, write credentials on response
        creds = {
            'INDEXTANK_PRIVATE_API_URL' : account.get_private_apiurl(),
            'INDEXTANK_PUBLIC_API_URL' : account.get_public_apiurl(),
            'INDEXTANK_INDEX_NAMES': ["idx"]
        }

        return JsonResponse({"code": account.get_public_apikey(), "config": creds})

    @authorized_method
    @required_data("code")
    def DELETE(self, request, data, **kwargs):
        # fetch the account that should be deleted
        account = Account.objects.get(apikey__startswith=data['code']+"-")
        
        # make sure the provisioner for the account is the same requesting its deletion
        if self.provisioner != account.provisioner:
            return HttpResponse('You are not the provisioner for this account', status=403)

        # ok, lets do it
        account.close()
        
        return HttpResponse(status=204)
    
   
class BaseProvisioner(ProvisionerResource):
    def _is_valid_provisioner(self, provisioner):
        return True
    
    def _validate(self, request, data, plan, **kwargs):
        if not self._is_valid_provisioner(self.provisioner):
            return HttpResponse('"Invalid provisioner"', status=400)
        if self.provisioner.plans.filter(plan=plan.upper()).count() == 0:
            return HttpResponse('"Plan %s NOT allowed"' % plan, status=400)
    
    def _get_email(self, request, data, plan, **kwargs):
        return None
    
    def _get_id(self, account):
        return account.get_public_apikey()

    @authorized_method
    @required_data("plan")
    def POST(self, request, data, plan=None, **kwargs):
        response = self._validate(request, data, plan, **kwargs)
        if response:
            return response

        package = self.provisioner.plans.get(plan=plan.upper()).package
        account, _ = Account.create_account(datetime.datetime.now(), email=self._get_email(request, data, plan, **kwargs))

        account.status = Account.Statuses.operational
        account.provisioner = self.provisioner
        account.apply_package(package)
        account.save()
        

        # create an index, using ApiClient
        client = ApiClient(account.get_private_apiurl())
        i = client.create_index("idx", options={ 'public_search':True })
        
        # ok, write credentials on response
        creds = {
            'INDEXTANK_API_URL' : account.get_private_apiurl(),
            'INDEXTANK_PRIVATE_API_URL' : account.get_private_apiurl(),
            'INDEXTANK_PUBLIC_API_URL' : account.get_public_apiurl(),
        }

        return JsonResponse({"id": self._get_id(account), "config": creds})

    @authorized_method
    def PUT(self, request, data, id=None):
        return HttpResponse('{ "message": "Sorry, we do not support plan upgrades" }', status=503)


class EmailProvisionerMixin(object):
    def _validate(self, request, data, plan, **kwargs):
        r = super(EmailProvisionerMixin, self)._validate(request, data, plan, **kwargs)
        return r or self._validate_email(data.get('email', None))
    
    def _validate_email(self, email):
        if email is None:
            return HttpResponse('"An email is required"', status=400)
        try:
            is_valid_email(email)
        except:
            return HttpResponse('"Invalid email!"', status=400)

    def _get_email(self, request, data, plan, **kwargs):
        return data['email']

class SSOProvisionerMixin(object):
    def GET(self, request, id=None):
        timestamp = int(request.GET.get('timestamp',0))
        token = request.GET.get('token','')
        navdata = request.GET.get('nav-data','')
        return HttpResponseRedirect("http://indextank.com/provider/resources/%s?token=%s&timestamp=%s&nav-data=%s"%(id,token,timestamp,navdata)) # TODO fix this
    
class DeleteProvisionerMixin(object):
    def _get_account(self, id):
        return Account.objects.get(apikey__startswith=("%s-" % id))
    
    @authorized_method
    def DELETE(self, request, data, id=None):
        # fetch the account that should be deleted
        account = self._get_account(id)
        
        # make sure the provisioner for the account is the same requesting its deletion
        if self.provisioner != account.provisioner:
            return HttpResponse('You are not the provisioner for this account', status=403)

        # ok, lets do it
        account.close()
        
        return HttpResponse()

class FetchCredentialsProvisionerMixin(object):
    @authorized_method
    @required_querystring_argument("id")
    def GET(self, request, code, **kwargs):
        # fetch the account we want info about
        account = self._get_account(id)
        
        # make sure the provisioner for the account is the same requesting its deletion
        if self.provisioner != account.provisioner:
            return HttpResponse('You are not the provisioner for this account', status=403)
       
        # create the creds
        creds = {
            'INDEXTANK_PRIVATE_API_URL' : account.get_private_apiurl(),
            'INDEXTANK_PUBLIC_API_URL' : account.get_public_apiurl(),
            'INDEXTANK_INDEX_NAMES' : [i.name for i in account.indexes.all()]
        } 
        
        return JsonResponse({"id": account.get_public_apikey(), "config": creds})


class PublicProvisioner(EmailProvisionerMixin, BaseProvisioner):
    pass

class DisabledProvisioner(BaseProvisioner):
    @authorized_method
    @required_data("plan")
    def POST(self, request, data, plan=None, **kwargs):
        return HttpResponse('"Provisioning is currently disabled"', status=503)

class CloudFoundryProvisioner(DeleteProvisionerMixin, FetchCredentialsProvisionerMixin, DisabledProvisioner):
    def _is_valid_provisioner(self, provisioner):
        return provisioner.name == 'cloudfoundry'

class AppHarborProvisioner(DeleteProvisionerMixin, SSOProvisionerMixin, DisabledProvisioner):
    def _is_valid_provisioner(self, provisioner):
        return provisioner.name == 'appharbor'

class HerokuProvisioner(DeleteProvisionerMixin, SSOProvisionerMixin, BaseProvisioner):
    def _is_valid_provisioner(self, provisioner):
        return provisioner.name == 'heroku'
    def _get_id(self, account):
        return account.id
    def _get_account(self, id):
        return Account.objects.get(id=id)

def default(request):
    return HttpResponse('"IndexTank API. Please refer to the documentation: http://indextank.com/documentation/api"')



