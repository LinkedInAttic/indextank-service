#!/bin/bash

TEE="tee -a /data/logs/api.log"
ROTATELOG="/usr/sbin/rotatelogs -l -f /data/logs/api-rot/api.log.%Y-%m-%d_%H.%M.%S 200M"

echo "######################## KILL API "`date`" ##########################" | $TEE | $ROTATELOG

kill -9 `cat pid`
