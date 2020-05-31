from django.conf.urls import url, include
from django.urls import path

# Routers provide an easy way of automatically determining the URL conf.
from dashboard.views import StationView, IndustryView, UserView, ParameterView, \
    DashboardView, CameraView, industry_sites, site_details, GeographicalView, \
    plot_chart, ReportView, plot_table, StationDataReportView, \
    StationParameterView, ExceedanceDataReportView, SMSReportView, \
    IndustryReportView, MaintenanceView, DeviceView
from api.utils import *

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.


app_name = 'dashboard'
urlpatterns = [
    url(r'^blankview$', blankview, name='blank'),
    url(r'^buttonsview/$', buttonsview, name='buttons'),
    url(r'^cardsview/$', cardsview, name='cards'),
    url(r'^chartsview/$', chartsview, name='charts'),

    url(r'^utilities-animationview/$', utilities_animationview,
        name='utilities-animation'),
    url(r'^utilities-borderview/$', utilities_borderview,
        name='utilities-border'),
    url(r'^utilities-colorview/$', utilities_colorview,
        name='utilities-color'),
    url(r'^utilities-otherview/$', utilities_otherview,
        name='utilities-other'),

    # Below is required to show login/logout option
    url(r'^$', DashboardView.as_view(), name='dashboard'),

    url(r'^stations/$', StationView.as_view(), name='stations'),
    # https://docs.djangoproject.com/en/3.0/topics/http/urls/ path converters
    path('station-info/<uuid:uuid>', StationView.as_view(),
         # path support uuid directly
         name='station-info'),

    url(r'^industries/$', IndustryView.as_view(), name='industries'),
    path('industry-info/<uuid:uuid>', IndustryView.as_view(),
         name='industry-info'),

    url(r'^users/$', UserView.as_view(), name='users'),
    path('user-info/<uuid:uuid>', UserView.as_view(), name='user-info'),

    url(r'^parameters/$', ParameterView.as_view(), name='parameters'),
    path('parameter-info/<int:pk>', ParameterView.as_view(),
         name='parameter-info'),
    path('station-parameter-info/<int:pk>', StationParameterView.as_view(),
         name='sparameter-info'),

    url(r'^cameras/$', CameraView.as_view(), name='cameras'),
    url(r'^management/$', CameraView.as_view(), name='management'),
    url(r'^geographical/$', GeographicalView.as_view(), name='geographical'),
    url(r'^stationdata$', StationDataReportView.as_view(),
        name='station-data'),
    url(
        r'^stationdata/(?P<pk>[0-9a-f-]+)/(?P<freq>[aA-zZ0-9]+)/('
        r'?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/['
        r'0-9]{2}/[0-9]{4})$',
        StationDataReportView.as_view(), name='station-data-table'),
    url(
        r'^stationdata/(?P<pk>[0-9a-f-]+)/(?P<freq>[aA-zZ0-9]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<dwld>[aA-zZ0-9.xlsx]+)$',
        StationDataReportView.as_view(), name='dwld-station-data'),

    url(r'^exceedancedata$', ExceedanceDataReportView.as_view(),
        name='exceedance'),
    url(
        r'^exceedancedata/(?P<pk>[0-9a-f-]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})$',
        ExceedanceDataReportView.as_view(), name='exceedance-details'),
    url(
        r'^exceedancedata/(?P<pk>[0-9a-f-]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<dwld>[aA-zZ0-9.xlsx]+)$',
        ExceedanceDataReportView.as_view(), name='dwld-exceedance'),

    url(r'^reports/$', ReportView.as_view(), name='reports'),
    url(
        r'^reports/(?P<rtype>[aA-zZ]+)/(?P<freq>[aA-zZ0-9]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})$',
        # url(r'^reports/(?P<rtype>[aA-zZ]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<freq>[aA-zZ]+)$',
        ReportView.as_view(), name='report-date'),
    url(
        r'^reports/(?P<rtype>[aA-zZ]+)/(?P<freq>[aA-zZ0-9]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<dwld>[aA-zZ0-9.xlsx]+)$',
        ReportView.as_view(),
        name='download-report'),

    url(r'^smsreport$', SMSReportView.as_view(),
        name='smsreport'),
    url(
        r'^smsreport/(?P<pk>[aA-zZ0-9-]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})$',
        SMSReportView.as_view(), name='smsreport-details'),
    url(
        r'^smsreport/(?P<pk>[0-9a-f-]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<dwld>[aA-zZ0-9.xlsx]+)$',
        SMSReportView.as_view(), name='dwld-smsreport'),

    url(r'^industryreport$', IndustryReportView.as_view(),
        name='industryreport'),
    url(
        r'^industryreport/(?P<pk>[aA-zZ0-9-]+)/(?P<type>[aA-zZ0-9]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})$',
        IndustryReportView.as_view(), name='industryreport-details'),
    url(
        r'^industryreport/(?P<pk>[0-9a-f-]+)/(?P<type>[aA-zZ0-9]+)/(?P<from_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<to_date>[0-9]{2}/[0-9]{2}/[0-9]{4})/(?P<dwld>[aA-zZ0-9.xlsx]+)$',
        IndustryReportView.as_view(), name='dwld-industryreport'),

    url(r'^maintenance/$', MaintenanceView.as_view(), name='maintenance'),
    path('maintenance-info/<int:pk>', MaintenanceView.as_view(),
         name='maintenance-info'),

url(r'^device/$', DeviceView.as_view(), name='device'),
    path('device-info/<int:pk>', DeviceView.as_view(),
         name='device-info'),

    url(r'graphdata$', plot_chart),
    url(r'tabulardata$', plot_table),

    # get industry sites
    url(r'^GetSites/', industry_sites),
    url(r'^GetSiteDetails/', site_details),

]
