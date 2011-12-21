About IndexTank Service
=======================

IndexTank Service (http://indextank.com) contains the source code that implementing the Search-as-a-Service platform. It contains the components that allows managing user accounts, server instances (worker) and index instances (deploy); depends on IndexTank Engine (https://github.com/linkedin/indextank-engine) binary.

### Homepage:

Find out more about at: TBD

### License:

Apache Public License (APL) 2.0

### Components:

1. API
2. Backoffice
3. Storefront
4. Nebu

### Dependencies:

* Django tested with 1.2.7
* Python tested with 2.6.6
* Java(TM) SE Runtime Environment tested with build 1.6.0_24-b07
* nginx
* uWSGI (http://projects.unbit.it/uwsgi/)
* MySQL
* daemontools (http://cr.yp.to/daemontools.html)
* Thrift library (generated sources with version 0.5.0 are provided)

### Getting started:

1. Create the database schema (python manage.py syncdb).
2. Create an account.
3. Start an index instance (IndexTank Engine).
4. Start API.

## API

Django application implementing the REST JSON API, enables index management per account, indexing functions and search. Interacts via Thrift with specific index instances (deploy).

## Backoffice

Django application that allows manual administration.

## Storefront

Django application with the service web, contains the user registration form (allows creating accounts).

## Nebu

Index, deploy & worker manager. A worker (server instance) may contain a deploy (index instance) or many. 

