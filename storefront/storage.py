
''' ========================= 
    Interaction with SimpleDB
    ========================= '''

import boto
import hashlib
import zlib
import time
import sys
import traceback
import datetime

from amazon_credential import AMAZON_USER, AMAZON_PASSWORD

from django.conf import settings

def get_connection():
    return boto.connect_sdb(AMAZON_USER, AMAZON_PASSWORD)

def get_ids(index_code, doc_id):
    md5 = hashlib.md5()
    md5.update(index_code);
    md5.update(doc_id);
    domain_num = zlib.crc32(md5.digest()) % 100
    domain_id = str(domain_num).rjust(3,'0')
    item_id = index_code+'|'+doc_id
    return domain_id, item_id

VALUE_MAX_LENGTH = 1024
def storage_add(index_code, doc_id, content):
    domain_id, item_id = get_ids(index_code, doc_id)
    try:
        sdb = get_connection()
        domain = sdb.get_domain(domain_id)
        item = domain.new_item(item_id)
        item['timestamp'] = time.time()
        limit = VALUE_MAX_LENGTH-2
        for key, txt in content.iteritems():
            n = 0
            i = 1
            while len(txt) > n:
                part = '['+txt[n:n+limit]+']'
                item['_'+str(i)+'_'+key] = part
                n += limit
                i += 1
        item.save()
        return ""
    except:
        return sys.exc_info()

def storage_get(index_code, doc_id):
    domain_id, item_id = get_ids(index_code, doc_id)
    try:
        sdb = get_connection()
        domain = sdb.get_domain(domain_id)
        item = domain.get_item('|%s|DOC|%s' % (settings.STORAGE_ENV, item_id))
        return item_to_doc(item) if item is not None else None
    except:
        traceback.print_exc()
        return {}, sys.exc_info()

def storage_del(index_code, doc_id):
    domain_id, item_id = get_ids(index_code, doc_id)
    try:
        sdb = get_connection()
        domain = sdb.get_domain(domain_id)
        domain.delete_attributes('DOC|'+item_id)
        return ""
    except:
        return sys.exc_info()


def item_to_doc(item):
    doc = {}
    vars = {}
    cats = {}
    item = dict(item)
    
    fields = item['item_fields'].split(',')
    
    for k, v in item.iteritems():
        if k.startswith('user_boost_'):
            vars[k[11:]] = v
        if k.startswith('user_category_'):
            cats[k[14:]] = v
    
    for f in fields:
        v = ''
        p = 1
        while True:
            part = item.get('_%s_%d' % (f, p))
            if part:
                v += part
                p += 1
            else:
                break
        if f == 'timestamp':
            doc[f] = '%s (%s)' % (v, datetime.datetime.fromtimestamp(int(v)))
        else:
            doc[f] = v
        
    return { 'fields': doc, 'variables': vars, 'categories': cats }




