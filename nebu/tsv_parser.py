import sys
from django.utils import simplejson as json

def help():
    print """
# tsv_parser.py
# parses a tsv file, and dumps it as JSON.
#
# This is useful to create files for populator.py from FreeBase dumps

# Usage:
tsv_parser.py <file>
"""


if __name__ == "__main__":
    if not len(sys.argv) == 2:
        help()
        sys.exit(-1)
    
    file = open(sys.argv[1], 'r')
    
    header = file.next()
    header = header.replace('\n', '')
    
    field_names = header.split('\t')
    
    for line in file:
        line = line.replace('\n', '')
        fields = {}
        values = line.split('\t')
        
        for i in range(len(values)):
            fields[field_names[i]] = values[i]
        
        final_map = {}
        
        final_map['docid'] = fields['docid']
        del fields['docid']
        
        final_map['fields'] = fields

        print json.dumps(final_map)
    
