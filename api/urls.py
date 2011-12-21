from django.conf.urls.defaults import *  #@UnusedWildImport

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

from api import restapi

admin.autodiscover()

VERSION = r'^v(?P<version>\d+)'
INDEX = r'/indexes/(?P<index_name>[^/]+)'
FUNCTION = r'/functions/(?P<function>-?\d+)'

urlpatterns = patterns('',
    url('^/?$', 'api.restapi.default', name='default'),
    url(VERSION + '/?$', restapi.Version.as_view()),
    url(VERSION + '/indexes/?$', restapi.Indexes.as_view()),
    url(VERSION + INDEX + '/?$', restapi.Index.as_view()),
    url(VERSION + INDEX + '/docs/?$', restapi.Document.as_view()),
    url(VERSION + INDEX + '/docs/variables/?$', restapi.Variables.as_view()),
    url(VERSION + INDEX + '/docs/categories/?$', restapi.Categories.as_view()),
    url(VERSION + INDEX + '/functions/?$', restapi.Functions.as_view()),
    url(VERSION + INDEX + FUNCTION + '/?$', restapi.Function.as_view()),
    url(VERSION + INDEX + '/search/?$', restapi.Search.as_view()),
    url(VERSION + INDEX + '/promote/?$', restapi.Promote.as_view()),
    url(VERSION + INDEX + '/autocomplete/?$', restapi.AutoComplete.as_view()),
    url(VERSION + INDEX + '/instantlinks/?$', restapi.InstantLinks.as_view()),
)
