#!/bin/bash

# back up log storage

while true; do
  echo starting sync at `/bin/date`
  ionice -c 2 -n 5 rsync -av --append-verify --delete /data/storage/live /archive/
  ionice -c 2 -n 5 rsync -av --append-verify /data/storage/history /archive/
  echo finished sync at `/bin/date`
  sleep 2
done
