import re
import commands
import subprocess

def _get_df_lines():
    lines = re.split('\n', commands.getstatusoutput('df')[1])
    for i in range(len(lines)):
        lines[i] = re.split('\s+', lines[i])
    return lines

def get_available_sizes(filesystems=None):
    df = _get_df_lines()
    results = {}
    for fs in df:
        if not fs[0] == 'Filesystem' and (filesystems is None or fs[0] in filesystems):
            results[fs[5]] = [int(fs[2]), int(fs[3])]
    return results

def get_load_averages():
    return [float(x) for x in commands.getstatusoutput('uptime')[1].split('load average: ')[1].split(', ')] 

def get_index_stats(index_code, base_port):
    stats = dict(disk=0)
    
    ps = subprocess.Popen('ps -e -orss=,pcpu=,args= | grep %s | grep -v grep' % index_code, shell=True, stdout=subprocess.PIPE)

    psout, _ = ps.communicate()
    #psout = "36049 0.0 java -Dapp=INDEX-ENGINE-DD9r -Xmx700M -Dorg.apache.lucene.FSDirectory.class=org.apache.lucene.store.MMapDirectory -cp ../../conf:lib/indextank-trunk.jar:lib/indextank-trunk-deps.jar com.flaptor.indextank.index.IndexEngine -dir index -port 20130 -index-code DD9r -rti-size 500 -r -snippets"
    for line in psout.split('\n'):
        if line:
            mem, cpu, args = line.split(None, 2)
            print args
            if args != index_code:
                
                extract = lambda l: l[0] if l else None
                parse = lambda s: extract(re.findall(s, args))
                
                stats.update(mem=(float(mem) / 1024), 
                             cpu=(float(cpu)), 
                             args=args, 
                             xmx=parse(r'-Xmx(\d+\w)'),
                             port=parse(r'-port (\d+)'),
                             rti=parse(r'-rti-size (\d+)'),
                             suggest=parse(r'(-suggest)'),
                             snippets=parse(r'(-snippets)'),
                             boosts=parse(r'-b (\d+)') or 1)
                break
    
    du = subprocess.Popen('du -s /data/indexes/%s-%s/index/' % (index_code, base_port), shell=True, stdout=subprocess.PIPE)
    duout, _ = du.communicate()
    if duout:
        disk = duout.split()[0]
        if disk:
            disk = (float(disk) / 1024)
            stats.update(disk=disk)
    
    return stats

