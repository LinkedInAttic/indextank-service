from django.conf.urls.defaults import *  #@UnusedWildImport

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('',
    url(r'^_static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'static'}, name='static'),
    url(r'^$', 'storefront.views.root', name='root'),
    url(r'^home$', 'storefront.views.home', name='home'),
    url(r'^poweredby$', 'storefront.views.poweredby', name='poweredby'),
    url(r'^packages$', 'storefront.views.packages', name='packages'),
    url(r'^documentation/$', 'storefront.views.documentation', name='documentation'),
    url(r'^documentation/(?P<path>.*)$', 'storefront.views.documentation', name='documentation'),
    url(r'^login$', 'storefront.views.login', name='login'),
    url(r'^forgot-password$', 'storefront.views.forgot_password', name='forgot_password'),
    url(r'^thanks-notice$', 'storefront.views.thanks_notice', name='thanks_notice'),
    url(r'^change-password/$', 'storefront.views.change_password', name='change_password'),
    #url(r'^invite_sign_up/(?P<password>.*)$', 'storefront.views.invite_sign_up', name='invite_sign_up'),
    #url(r'^beta-request$', 'storefront.views.beta_request', name='beta_request'),
    #url(r'^get-started/$', 'storefront.views.get_started', name='get_started'),
    #url(r'^upgrade/$', 'storefront.views.upgrade', name='upgrade'),
    url(r'^why/$', 'storefront.views.why', name='why'),
    url(r'^pricing/$', 'storefront.views.pricing', name='pricing'),
    url(r'^enter-payment/$', 'storefront.views.enter_payment', name='enter_payment'),
    url(r'^dashboard$', 'storefront.views.dashboard', name='dashboard'),
    url(r'^heroku-dashboard$', 'storefront.views.heroku_dashboard', name='heroku-dashboard'),
    url(r'^dashboard/insights/(?P<index_code>[^/]*)$', 'storefront.views.insights', name='insights'),
    url(r'^dashboard/manage/(?P<index_code>[^/]*)$', 'storefront.views.manage_index', name='manage_index'),
    url(r'^dashboard/inspect/(?P<index_code>[^/]*)$', 'storefront.views.manage_inspect', name='manage_inspect'),
    url(r'^create-index$', 'storefront.views.create_index', name='create_index'),
    url(r'^close-account$', 'storefront.views.close_account', name='close_account'),
    url(r'^delete-index$', 'storefront.views.delete_index', name='delete_index'),
    url(r'^select-package$', 'storefront.views.select_package', name='select_package'),
    url(r'^logout$', 'storefront.views.logout', name='logout'),
    url(r'^score-functions$', 'storefront.views.score_functions', name='score_functions'),
    url(r'^remove-function$', 'storefront.views.remove_function', name='remove_function'),
    url(r'^search/$', 'storefront.views.search', name='search'),
    url(r'^quotes$', 'storefront.views.quotes', name='quotes'),

    url(r'^provider/resources/(?P<id>.*)$', 'storefront.views.sso', name='sso'),
    url(r'^heroku/resources/(?P<id>.*)$', 'storefront.views.sso_heroku', name='sso_heroku'),
    url(r'^demoindex$', 'storefront.views.demo_index', name='demoindex'),

    url(r'^accounting/register-index$', 'storefront.views.api_register_index'),
    url(r'^accounting/delete-index$', 'storefront.views.api_delete_index'),
    url(r'^accounting/list-indexes$', 'storefront.views.api_list'),

)
