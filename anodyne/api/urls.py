from django.conf.urls import url, include
from rest_framework import routers, serializers, viewsets

# Routers provide an easy way of automatically determining the URL conf.
from api.views import UserViewSet, IndustryViewSet, StationViewSet, \
    StationInfoViewSet, StateViewSet, CityViewSet, PCBViewSet, \
    StationParameterViewSet, ReadingViewSet, RegistrationViewSet, \
    CategoryViewSet

router = routers.DefaultRouter()

router.register(r'industry', IndustryViewSet, basename='industry')
router.register(r'station', StationViewSet, basename='station')
router.register(r'station-info', StationInfoViewSet, basename='station-info')
router.register(r'users', UserViewSet, basename='user')
router.register(r'state', StateViewSet, basename='state')
router.register(r'city', CityViewSet, basename='city')
router.register(r'pcb', PCBViewSet, basename='pcb')
router.register(r'category', CategoryViewSet, basename='category')
router.register(r'station-parameter', StationParameterViewSet,
                basename='station-parameter')
router.register(r'reading', ReadingViewSet, basename='reading')
router.register(r'registrations', RegistrationViewSet, basename='register')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^', include(router.urls)),
    # Below is required to show login/logout option
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework'))
]
