from lib.indextank.client import ApiClient
import sys
import time

if len(sys.argv) != 2:
    print 'Usage: testapi.py <API_URL>'

api = ApiClient(sys.argv[1])
index = api.get_index('testapi.py')

if index.exists():
    print 'deleting previous index'
    index.delete_index()

print 'creating index'
index.create_index()

print 'waiting to start...'
while not index.has_started():
    time.sleep(1)

print 'adding docs'
index.add_document(1, {'text': 'a b c1'}, variables={0:1, 1:2, 2:3})
index.add_document(2, {'text': 'a b c2'}, variables={0:2, 1:2, 2:2})
index.add_document(3, {'text': 'a b c3'}, variables={0:3, 1:2, 2:1})

print 'adding functions'
index.add_function(1, 'd[0]')
index.add_function(2, 'd[2]')

print 'checking functions'
assert index.search('a', scoring_function=1)['results'][0]['docid'] == '3'
assert index.search('a', scoring_function=2)['results'][0]['docid'] == '1'

print 'checking fetch'
assert index.search('a', scoring_function=2, fetch_fields=['text'])['results'][0]['text'] == 'a b c1'

print 'checking delete'
index.delete_document(1)

assert index.search('a', scoring_function=2)['results'][0]['docid'] == '2'

print 'success'

