from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'dasmon.views.summary'),
    url(r'^update/', 'dasmon.views.summary_update'),
    url(r'^help/', 'dasmon.views.help'),
    url(r'^activity/$', 'dasmon.views.activity_summary'),
    url(r'^activity/update/$', 'dasmon.views.activity_update'),
    url(r'^(?P<instrument>[\w]+)/$', 'dasmon.views.live_monitor'),
    url(r'^(?P<instrument>[\w]+)/runs/$', 'dasmon.views.live_runs'),
    url(r'^(?P<instrument>[\w]+)/update/$', 'dasmon.views.get_update'),
    url(r'^(?P<instrument>[\w]+)/diagnostics/$', 'dasmon.views.diagnostics'),
    url(r'^(?P<instrument>[\w]+)/signals/$', 'dasmon.views.get_signal_table'),
    url(r'^(?P<instrument>[\w]+)/legacy/$', 'dasmon.views.legacy_monitor'),
    url(r'^(?P<instrument>[\w]+)/legacy/update/$', 'dasmon.views.get_legacy_data'),
    
)
