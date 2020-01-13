from django.conf.urls import url, include
from rest_framework import routers, serializers, viewsets

# Routers provide an easy way of automatically determining the URL conf.
from api.views import UserViewSet, IndustryViewSet, StationViewSet

router = routers.DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'industry', IndustryViewSet)
router.register(r'station', StationViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^', include(router.urls)),
    # Below is required to show login/logout option
    url(r'^api-auth/',
        include('rest_framework.urls', namespace='rest_framework'))
]