# ViewSets define the view behavior.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.fields import IntegerField
from rest_framework.response import Response

from api.serializers import UserSerializer, IndustrySerializer, \
    StationSerializer, StationInfoSerializer, StateSerializer, CitySerializer, \
    PCBSerializer, StationParameterSerializer
from api.models import User, Industry, Station, StationInfo, State, City, PCB, \
    StationParameter


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    # @action(detail=True, methods=['post'])
    # def change_password(self, request, pk=None):
    #     user = self.get_object()
    #     serializer = ChangePasswordSerializer(data=request.data)
    #     if serializer.is_valid():
    #         user.set_password(serializer.data['password'])
    #         user.save()
    #         return Response({'status': 'password set'})
    #     else:
    #         return Response(serializer.errors,
    #                         status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False)
    def recent_users(self, request):
        recent_users = User.objects.all().order_by('-last_login')

        page = self.paginate_queryset(recent_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(recent_users, many=True)
        return Response(serializer.data)


class IndustryViewSet(viewsets.ModelViewSet):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer


class StationInfoViewSet(viewsets.ModelViewSet):
    queryset = StationInfo.objects.all()
    serializer_class = StationInfoSerializer


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer


class PCBViewSet(viewsets.ModelViewSet):
    queryset = PCB.objects.all()
    serializer_class = PCBSerializer


class StationParameterViewSet(viewsets.ModelViewSet):
    queryset = StationParameter.objects.all()
    serializer_class = StationParameterSerializer
