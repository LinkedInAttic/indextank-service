#!/bin/bash

# Starts the IndexesServer process. 
# The IndexesServer fulfills different functionalities:
# - Serves the records to the IndexRecoverer (Reader)
# - Takes records from the raw files and deals them to the different indexes files (Dealer)
# - Optimizes log files. Merges all mergable operations (Optimizer) 

/usr/bin/nohup ionice -c 2 -n 3 /usr/bin/java -cp conf:lib/indextank-engine-1.0.0-jar-with-dependencies.jar com.flaptor.indextank.storage.IndexesLogServer -rp 15100 -mp 16000 2>&1 > /data/logs/indexes.log &
echo $! > indexes.pid
