About Storage
=============

The Storage component is intended to guarantee the durability of the indexes data. It works as a binary log for your indexes keeping track of all operations. This allows for you to regenerate indexes from scratch (this is what the Nebulizer component does when it 'moves' an index).

For more detailed info check https://github.com/linkedin/indextank-service/wiki/Log-Storage

### Components 

The Storage component comprises 2 servers:

* Indexes. The IndexesServer fulfills different functionalities:

> - Serves the records to the IndexRecoverer (Reader)

> - Takes records from the raw files and deals them to the different indexes files (Dealer)

> - Optimizes log files. Merges all mergable operations (Optimizer) 

* Writer

> - The writer gets the call from the API when a new doc is added. It writes down the log storage raw files.

### Running

There are bash scripts in the storage folder for running both components (start_indexes, start_writer). In order for them to work you need to copy the engine jar with dependencies (indextank-engine-1.0.0-jar-with-dependencies.jar) in the lib folder. 



