#!/bin/bash

# Starts WriterServer process. 
# The writer gets the call from the API when a new doc is added. It writes down the log storage raw files.

/usr/bin/nohup ionice -c 2 -n 1  /usr/bin/java -cp conf:lib/indextank-engine-1.0.0-jar-with-dependencies.jar com.flaptor.indextank.storage.LogWriterServer -p 15000 2>&1 > /data/logs/st_writer.log &
echo $! > writer.pid
