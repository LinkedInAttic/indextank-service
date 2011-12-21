#!/bin/bash
port=`echo $1 | rev | cut -c2- | rev`
(netstat -ln |egrep -m 1 "$port[0-9]")
VAL=$?
echo $VAL
exit $VAL
