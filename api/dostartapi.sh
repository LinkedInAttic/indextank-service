#!/bin/bash

TEE="tee -a /data/logs/api.log"
ROTATELOG="/usr/sbin/rotatelogs -l -f /data/logs/api-rot/api.log.%Y-%m-%d_%H.%M.%S 200M"
ERRORLOG="/data/logs/apierrors.log"

echo | $TEE | $ROTATELOG
echo "######################## START API "`date`" ##########################" | $TEE | $ROTATELOG
echo "######################## START API "`date`" ##########################" > $ERRORLOG

export PYTHONPATH=.:..

nohup uwsgi-python2.6 -C -s /var/nginx/api-uwsgi.sock -i -M -w wsgi -z 30 -p 150 -l 50 -L -R 10000 -b 8192 --no-orphans --pidfile pid 2>$ERRORLOG | $TEE | $ROTATELOG &


