from django.conf.urls import url, include
from rest_framework import routers

# Routers provide an easy way of automatically determining the URL conf.
from api.utils import long_lat_zip, get_station_reading, cities
from api.views import UserViewSet, IndustryViewSet, StationViewSet, \
    StateViewSet, CityViewSet, PCBViewSet, \
    StationParameterViewSet, RegistrationViewSet, \
    CategoryViewSet, ParameterViewSet

router = routers.DefaultRouter()

router.register(r'industry', IndustryViewSet, basename='industry')
router.register(r'station', StationViewSet, basename='station')
# router.register(r'station-info', StationInfoViewSet, basename='station-info')
router.register(r'users', UserViewSet, basename='user')
router.register(r'state', StateViewSet, basename='state')
router.register(r'city', CityViewSet, basename='city')
router.register(r'pcb', PCBViewSet, basename='pcb')
router.register(r'unit', RegistrationViewSet, basename='unit')
router.register(r'parameters', ParameterViewSet, basename='parameters')
router.register(r'category', CategoryViewSet, basename='category')
# router.register(r'reading', ReadingViewSet, basename='reading')
router.register(r'registrations', RegistrationViewSet, basename='register')
router.register(r'station-parameter', StationParameterViewSet,
                basename='station-parameter')
# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.


app_name = 'api'  # this hides login option in api comment this to see it
urlpatterns = [
    url(r'^', include(router.urls)),
    # Below is required to show login/logout option


    url(r'readings', get_station_reading),

    # Ajax
    url(r'^GetCities', cities),
    url(r'GetLongLat', long_lat_zip),

    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework'))
]
