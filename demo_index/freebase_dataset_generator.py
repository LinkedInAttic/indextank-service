#!/usr/bin/python
import freebase
import pickle

query = [{ "/music/instrument/family": [{"name": None}], "id": None, "name": None,  "a:type": "/music/instrument",  "b:type": "/common/topic",  "/common/topic/article": {"id": None},  "/common/topic/image": [{"id": None}], "/music/instrument/instrumentalists": {"return": "count", "optional": True}}]

data={}
counter = 0
for row in freebase.mqlreaditer(query):
    datum = {}
    datum['name'] = row['name']
    datum['url'] = 'http://freebase.com/view%s' % (row['id'])
    datum['image'] = 'http://img.freebase.com/api/trans/raw%s' % (row['/common/topic/image'][0]['id'])
    datum['thumbnail'] = 'http://indextank.com/_static/common/demo/%s.jpg' % (row['/common/topic/image'][0]['id'].split('/')[2])
    datum['text'] = freebase.blurb(row['/common/topic/article']['id'], maxlength=500)
    datum['variables'] = {}
    datum['variables'][0] = row['/music/instrument/instrumentalists']
    families = []
    for f in row['/music/instrument/family']:
        families.append(f['name'])
    datum['families'] = families

    data[datum['name']] = datum
    print('done %i' % counter)
    counter+=1


family = {}
for datum in data.values():
    for f in datum['families']:
        if family.has_key(f):
            family[f] += 1
        else:
            family[f] = 1


for datum in data.values():
    datum['categories'] = {}
    t = datum['families']
    if t:
        t.sort(key=family.get, reverse=True)
        datum['categories']['family'] = t[0]
    del(datum['families']) 

results = []
for datum in data.values():
    t = {}
    t['docid'] = datum['name']
    t['fields'] = {'name': datum['name'], 'url': datum['url'], 'text': datum['text'], 'image':datum['image'], 'thumbnail': datum['thumbnail']}
    t['categories'] = datum['categories']
    t['variables'] = datum['variables']
    results.append(t)
pickle.dump(results, file('instruments.dat', 'w'))
