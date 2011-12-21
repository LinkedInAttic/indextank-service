#!/bin/bash

# kill all api workers (those that match the pattern but are not `cat pid`)
# the master should then take care of respawning workers
echo "slowly killing workers and allowing the master to respawn them" 
for pid in `pgrep -f 'api-uwsgi' | grep -v \`cat pid\``; do
  count=`pgrep -f 'api-uwsgi' | grep -v \`cat pid\` | wc -l`
  echo "killing $pid - live workers: $count"
  kill $pid
  sleep 1
done