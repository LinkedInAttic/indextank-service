#!/bin/bash

show_help() { echo; echo "Usage: $0 [fend|api|db|log]"; echo; exit; }

if [ $# -lt 1 ]; then
    show_help
fi

ami_type=$1

ami_id=`ec2-describe-images | awk '/^IMAGE/ {if($3~/indextank-'${ami_type}'-/) {print $2,$3}}' | sed -r 's/(ami-[0-9a-f]+) .*indextank-.*-([0-9.]+).*/\2 \1/' | sort -nr | head -1 | awk '{print $2}'`

echo python replicate_instance.py $ami_type $ami_id
python replicate_instance.py $ami_type $ami_id
