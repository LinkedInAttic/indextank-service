#!/usr/bin/python
import os
import sys
import subprocess
import simplejson as json


# prevent everyone from importing
if __name__ != "__main__":
    print >> sys.stderr, 'this script is not meant to be imported. Exiting'
    sys.exit(1)


# ok, good to go
# parse the environment
if os.path.exists('/data/env.name'):
    env = open('/data/env.name').readline().rstrip("\n")
else:
    env = 'PROD'
    print >>sys.stderr, 'WARNING, the instance does not have a /data/env.name. USING PROD AS ENV'



# parse json
config_file = sys.argv[1]
config = json.load(open(config_file))

# setup logging files
log_dir = 'logs'
log_file = "%s/indextank.log" % log_dir
gc_log_file = "%s/gc.log" % log_dir
os.makedirs(log_dir)
pid_file = open('pid', 'w')

# setup index directory
index_dir = 'index'
os.makedirs(index_dir)

# first, generate vm args
vm_args = config.get('vmargs',[])
vm_args.append('-cp')
vm_args.append('.:lib/indextank-trunk.jar:lib/indextank-trunk-deps.jar')
vm_args.append('-verbose:gc')
vm_args.append('-Xloggc:%s'%gc_log_file)
vm_args.append('-XX:+PrintGCTimeStamps')
vm_args.append("-XX:+UseConcMarkSweepGC")
vm_args.append("-XX:+UseParNewGC")
vm_args.append("-Dorg.apache.lucene.FSDirectory.class=org.apache.lucene.store.MMapDirectory")
vm_args.append("-Dapp=INDEX-ENGINE-%s"%config['index_code'])
vm_args.append("-Xmx%sM"%config['xmx'])


# a list of possible IndexEngine params
app_params_mapping = {}
app_params_mapping['base_port'] = "--port"
app_params_mapping['index_code'] = "--index-code"
app_params_mapping['allow_snippets'] = "--snippets" # we may remove this line
app_params_mapping['allows_snippets'] = "--snippets"
app_params_mapping['snippets'] = "--snippets"
app_params_mapping['allow_facets'] = "--facets" # we may remove this line
app_params_mapping['allows_facets'] = "--facets"
app_params_mapping['max_variables'] = "--boosts"
app_params_mapping['autocomplete'] = "--suggest"
app_params_mapping['didyoumean'] = "--didyoumean"
app_params_mapping['rti_size'] = "--rti-size"
app_params_mapping['functions'] = "--functions"
app_params_mapping['storage'] = "--storage"
app_params_mapping['bdb_cache'] = "--bdb-cache"


def adapt_config_kv(key, value, json_config):
    if key == '--suggest':
        if value:
            value = json_config.get('autocomplete_type', 'documents')
        else:
            key, value = '', ''
    if key == '--facets':
        if value:
            value = ''
        else:
            key, value = '', ''
    if key == '--snippets':
        if value:
            value = ''
        else:
            key, value = '', ''
    if key == '--didyoumean' and value == True:
        value = "" # didyoumean does not take arguments
    if key == '--functions':
        value = "|".join("%s:%s"%(k,v) for k,v in value.iteritems())
    return key, value


# now, app params
app_params = {}

app_params['--conf-file'] = config_file

app_params.update(adapt_config_kv(app_params_mapping.get(k),v, config) for k,v in config.iteritems() if k in app_params_mapping)


# dependency checking
# --didyoumean needs --suggest documents
if '--didyoumean' in app_params:
    app_params['--suggest'] == 'documents'

# just make sure to use index dir
app_params['--dir'] =               index_dir
app_params['--environment-prefix'] = config.get('environment',env) # let configuration override env.
app_params['--recover'] =           '' # recover does not take arguments


# We want to use everything 64 bits because mmap doesn't like things it can't map to 31 bits.
java = 'java'
os.putenv('LD_LIBRARY_PATH','lib/berkeleydb_libs_64/')


full_args = ['nohup', java]
full_args.extend(vm_args)
full_args.append('com.flaptor.indextank.index.IndexEngine')
for k,v in app_params.iteritems():
    full_args.extend((k,str(v)))
log_file = open(log_file, 'w')


print >>log_file, ""
print >>log_file, ""
print >>log_file, "="*80
print >>log_file, "%s STARTING JVM %s" % ( "="*33, "="*33)
print >>log_file, "="*80
print >>log_file, "== %s ==" % full_args
print >>log_file, "="*80
pid = subprocess.Popen(full_args, stderr=log_file, stdout=log_file, close_fds=True)
print >>pid_file, pid.pid

