#!/bin/bash

LOGFILE="/data/logs/storefront.log"
python manage.py runfcgi method=prefork maxchildren=30 host=127.0.0.1 port=4300 pidfile=pid workdir="$PWD" outlog="$LOGFILE" errlog="$LOGFILE" >>$LOGFILE 2>&1 
