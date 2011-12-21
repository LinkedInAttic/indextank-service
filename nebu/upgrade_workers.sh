#!/bin/bash

#
# This script is intended to be executed after updating
# the "nebu" folder of a frontend instance. 
# It should be executed while the frontend nebu processes are down:
#  - worker manager
#  - deploy manager
#  - supervisor
# It will then issue commands to every worker so
# they can update their nebu installations from this
# frontend and restart their controllers.
#
# author: santip
#

export DJANGO_SETTINGS_MODULE=settings 
export PYTHONPATH=../:. 

python upgrade_workers.py
