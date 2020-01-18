# ViewSets define the view behavior.
from rest_framework import viewsets

from api.serializers import UserSerializer, IndustrySerializer, \
    StationSerializer
from api.models import User, Industry, Station


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class IndustryViewSet(viewsets.ModelViewSet):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer

