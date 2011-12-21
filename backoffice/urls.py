from django.conf.urls.defaults import *  #@UnusedWildImport

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^_static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'static'}, name='static'),
    url(r'^$', 'backoffice.views.home', name='home'),

    url(r'^beta_invitation_export', 'backoffice.views.beta_invitation_export', name='beta_invitation_export'),
    url(r'^log_info', 'backoffice.views.log_info', name='log_info'),
    url(r'^control_panel$', 'backoffice.views.control_panel', name='control_panel'),
    url(r'^biz_stats$', 'backoffice.views.biz_stats', name='biz_stats'),
    url(r'^biz_stats.json$', 'backoffice.views.biz_stats_json', name='biz_stats_json'),
    url(r'^biz_stats.json.daily$', 'backoffice.views.biz_stats_json_daily', name='biz_stats_json_daily'),
    url(r'^accounts_info', 'backoffice.views.accounts_info', name='accounts_info'),
    url(r'^resource_map', 'backoffice.views.resource_map', name='resource_map'),
    url(r'^beta_requests$', 'backoffice.views.beta_requests_list', name='beta_requests'),
    url(r'^beta_invitations$', 'backoffice.views.beta_invitations', name='beta_invitations'),
    url(r'^beta_request_invite/(?P<request_id>.*)$', 'backoffice.views.beta_request_invite', name='beta_request_invite'),
    url(r'^worker_resource_map/(?P<worker_id>.*)$', 'backoffice.views.worker_resource_map', name='worker_resource_map'),

    
    url(r'^manage_worker/(?P<worker_id>.*)$', 'backoffice.views.manage_worker', name='manage_worker'),
    url(r'^mount_history/(?P<worker_id>[^/]*)/(?P<mount>.*)$', 'backoffice.views.mount_history', name='mount_history'),
    url(r'^index_history/(?P<worker_id>[^/]*)/(?P<index_id>.*)$', 'backoffice.views.index_history', name='index_history'),
    url(r'^load_history/(?P<worker_id>[^/]*)', 'backoffice.views.load_history', name='load_history'),

    url(r'^operations', 'backoffice.views.operations', name='operations'),
    
    
    url(r'^login$', 'backoffice.views.login', name='login'),
    url(r'^logout$', 'backoffice.views.logout', name='logout'),
)
