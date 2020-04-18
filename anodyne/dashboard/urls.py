from django.conf.urls import url, include
from django.urls import path

# Routers provide an easy way of automatically determining the URL conf.
from dashboard.views import StationView, IndustryView, UserView, ParameterView, \
    DashboardView
from api.utils import *

app_name = 'dashboard'
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
url(r'^blankview$', blankview, name='blank'),
    url(r'^buttonsview$', buttonsview, name='buttons'),
    url(r'^cardsview$', cardsview, name='cards'),
    url(r'^chartsview$', chartsview, name='charts'),
    url(r'^tablesview$', tablesview, name='tables'),
    url(r'^utilities-animationview$', utilities_animationview, name='utilities-animation'),
    url(r'^utilities-borderview$', utilities_borderview, name='utilities-border'),
    url(r'^utilities-colorview$', utilities_colorview, name='utilities-color'),
    url(r'^utilities-otherview$', utilities_otherview, name='utilities-other'),
    # Below is required to show login/logout option
    path('', DashboardView.as_view(), name='dashboard'),
    path('stations', StationView.as_view(), name='stations'),
    path('stationinfo/<uuid:uuid>', StationView.as_view(), name='station-info'),

    path('industries', IndustryView.as_view(), name='industries'),
    path('industryinfo/<uuid:uuid>', IndustryView.as_view(), name='industry-info'),


    path('users', UserView.as_view(), name='users'),
    path('parameters', ParameterView.as_view(), name='parameters'),
]
