#!/bin/bash

# back up log storage

while true; do
  echo starting sync at `/bin/date`
  ionice -c 2 -n 5 rsync -av --append-verify --delete /data/storage/raw/live /archive/
  # we don't use --delete with /data/storage/raw/history so we can safely remove old logs from there
  ionice -c 2 -n 5 rsync -av --append-verify /data/storage/raw/history /archive/
  echo finished sync at `/bin/date`
  sleep 2
done
