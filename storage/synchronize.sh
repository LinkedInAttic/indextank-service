#!/bin/bash

# Keeps slave server up to date with merged files.

output_rsync() {
  lastcode="?"
  while read data
  do
    code=`echo "$data" | sed -r "s;indexes/([^/]*?)/.*$;\1;"`
    unsorted=`echo "$data" | egrep "___unsorted"`
    index=`echo "$data" | egrep "___index"`
    segm=`echo "$data" | egrep "indexes/$code/segments/(.+)$"`
    opti=`echo "$data" | egrep "indexes/$code/optimized/(.+)$"`
    count=`echo $data | cut -d "_" -f 7`
    if [ -n "$code" ]; then
      if [ -n "$segm$opti" ]; then
        if [ "$code" != "$lastcode" ]; then
          echo
          echo -n "$code"
          lastcode="$code"
        fi
      fi
      if [ -z "$index" ]; then
        if [ -n "$segm" ]; then
          if [ -n "$unsorted" ]; then
            echo -n " [unsorted]"
          else
            echo -n " [$count]"
          fi
        fi
        if [ -n "$opti" ]; then
          echo -n " <$count>"
        fi
      fi
    else
      echo "$data" | egrep "^sent"
      echo "$data" | egrep "^total size"
    fi
  done
}

if [[ ! -f "/data/master" || ! -f "/data/storage/safe_to_read" ]]; then

  if [ -d "/data/storage/migrated" ]; then
    # the dealer hasn't switched the migrated data. nothing to do yet
    echo "[ ] The IndexesLogServer hasn't picked up last synchronization yet. Waiting."
    exit 0
  else
    MASTER="ec2-174-129-33-117.compute-1.amazonaws.com"
    
    echo "[+] Preparing directory..."
    rm -fr /data/storage/migrating
    mkdir -p /data/storage/migrating
    
    echo "[+] Synchronizing dealer info to /data/storage/migrating..."
    rsync -av $MASTER:/data/storage/dealer*.info /data/storage/migrating > /dev/null
    if [[ $? != 0 ]]; then echo ">>>>>>>>>>>>>>>>>> FAILED to rsync dealer info :("; exit 1; fi
    
    CURRENT=`cat /data/storage/dealer.next_timestamp.info`
    NEW=`cat /data/storage/migrating/dealer.next_timestamp.info`
    
    if [ "$NEW" != "$CURRENT" ]; then
      #echo "[+] Locally hard-linking unsorted segments to /data/storage/migrating..."
      #rsync -ahv --link-dest /data/storage/ --include-from unsorted_files_pattern /data/storage/indexes /data/storage/migrating 
      #if [[ $? != 0 ]]; then echo "Failed to ??? :("; exit 1; fi
      
      #echo "[+] Synchronizing unsorted segments to /data/storage/migrating..."
      #rsync -ahbv --suffix "" --backup-dir "." --append-verify --include-from unsorted_files_pattern $MASTER:/data/storage/indexes /data/storage/migrating 
      #if [[ $? != 0 ]]; then echo "Failed to ??? :("; exit 1; fi

      echo "[+] Synchronizing unsorted segments to /data/storage/migrating..."
      rsync -ahv --link-dest /data/storage/ --include-from unsorted_files_pattern $MASTER:/data/storage/indexes /data/storage/migrating 
      if [[ $? != 0 ]]; then echo ">>>>>>>>>>>>>>>>>> FAILED to synchronize unsorted segments :("; exit 1; fi
      
      echo "[+] Synchronizing sorted segments to /data/storage/migrating..."
      rsync -ahv --link-dest /data/storage/ --include-from sorted_files_pattern $MASTER:/data/storage/indexes /data/storage/migrating 
      if [[ $? != 0 ]]; then echo ">>>>>>>>>>>>>>>>>> FAILED to synchronize sorted segments :("; exit 1; fi
      
      echo "[+] Synchronizing optimized segments to /data/storage/migrating..."
      rsync -ahv --link-dest /data/storage/ --include-from optimized_files_pattern $MASTER:/data/storage/indexes /data/storage/migrating 
      if [[ $? != 0 ]]; then echo ">>>>>>>>>>>>>>>>>> FAILED to synchronize optimized segments :("; exit 1; fi
      
      echo "[+] Removing duplicates between sorted and unsorted segments..."
      find /data/storage/migrating/indexes -name *.sorted_* | cut -d. -f1 | awk '{printf "%s.unsorted_*\n",$1}' | xargs -L 100 rm -f
      
      echo "[+] Fetching time delta with master..."
      MASTER_DATE=`ssh $MASTER date "+%s"`
      LOCAL_DATE=`date "+%s"`
      echo $(( LOCAL_DATE - MASTER_DATE )) > /data/storage/migrating/master_delta.info 2> /dev/null      
      
      echo "[+] Moving complete snapshot to /data/storage/migrated"
      mv /data/storage/migrating /data/storage/migrated
    fi
  fi
  
  echo "Synchronization complete"
  
fi


#echo "[+] Synchronizing segments to /data/migrating..."
#rsync -ahv --link-dest /data/storage/ $MASTER:/data/storage/indexes /data/migrating
#echo
#if [[ $? != 0 ]]; then echo "Failed to create /data/previous :("; exit 1; fi
#if [[ ${PIPESTATUS[0]} != 0 ]]; then echo "Failed to rsync segments :("; exit 1; fi
#echo

#if [ -d "/data/previous" ]; then
#  echo "Removing /data/previous..."
#  rm -fr /data/previous
#fi
#mkdir -p /data/previous/
#if [[ $? != 0 ]]; then echo "Failed to create /data/previous :("; exit 1; fi
#
#echo "Moving /data/storage/indexes to /data/previous..."
#mv /data/storage/indexes /data/previous/

#echo "Copying dealer info files from /data/storage to /data/previous..."
#cp /data/storage/dealer*.info /data/previous/
#
#echo "Moving migrated data to /data/storage..."
#mv /data/migrating/* /data/storage/
#if [[ $? != 0 ]]; then echo "Failed to move migrated segments :("; exit 1; fi



