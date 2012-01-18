# Django settings for the indextank project.

from os import environ

LOCAL = (environ.get('DJANGO_LOCAL') == '1')

DEBUG = False 
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'mysql'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = 'indextank'             # Or path to database file if using sqlite3.
DATABASE_USER = '****'             # Not used with sqlite3.
DATABASE_PASSWORD = '****'         # Not used with sqlite3.
DATABASE_HOST = 'database'             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Etc/GMT+0'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'api.lib.error_logging.ViewErrorLoggingMiddleware',
    'django.middleware.gzip.GZipMiddleware',                      
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
)

ROOT_URLCONF = 'api.urls'

TEMPLATE_DIRS = (
    'templates'
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'api',
    'django.contrib.contenttypes',
    'django.contrib.auth'
)

STORAGE_ENV = 'PROD'

STATIC_URLS = [ '/_static' ]
ALLOWED_INCLUDE_ROOTS = ('static')

USER_COOKIE_NAME = "pf_user"
COMMON_DOMAIN = 'localhost'
#SESSION_COOKIE_DOMAIN = COMMON_DOMAIN
FORCE_SCRIPT_NAME = ''
USE_MULTITHREADED_SERVER = True
LOGGER_CONFIG_FILE='logging.conf'

EMAIL_HOST='localhost'
EMAIL_PORT=25
EMAIL_HOST_USER='user%localhost'
EMAIL_HOST_PASSWORD='****'

# Seeds for the api key generation. These are examples, they should be changed at each installation.
# You can find good seeds at https://www.grc.com/passwords.htm
APIKEY_KEY='5AD2CFAEEFAA93EC114DB414D7C3C18BBFB591784729DA33B2D779E65DB65DA5'
ONETIMEPASS_KEY='AC031B479497B86321EAC0E2D66A5A9C6EC6B4F891174E8016420DA1B9CC3320'
FORGOTPASS_KEY='2455B8EFEBBED1367A4DC2B732DBF08EF6BA5E009CC9C97A192C2C442BDD091A'

