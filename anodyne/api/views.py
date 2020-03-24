# ViewSets define the view behavior.
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import User, Industry, Station, StationInfo, State, City, \
    PCB, StationParameter, Reading, Registration
from api.serializers import UserSerializer, IndustrySerializer, \
    StationSerializer, StationInfoSerializer, StateSerializer, \
    CitySerializer, PCBSerializer, StationParameterSerializer, \
    ReadingSerializer, RegistrationSerializer
from django_filters import rest_framework as filters


class UserViewSet(viewsets.ModelViewSet):
    # queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        id = self.request.query_params.get('id', None)
        if id is not None:
            queryset = queryset.filter(id=id)
        return queryset

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

    # example:
    # /api/users/recent_users/ (will give users ordered by latest login
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
    # queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('type', 'status', 'city', 'state', 'name')

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = Industry.objects.all()
        print(self.request.query_params)
        q = {}
        if self.request.query_params:
            uuid = self.request.query_params.getlist('uuid')
            industry_code = self.request.query_params.getlist('industry_code')
            status = self.request.query_params.getlist('status')
            type = self.request.query_params.getlist('category')
            state = self.request.query_params.getlist('state')
            city = self.request.query_params.getlist('city')
            if uuid:
                q['uuid__in'] = uuid
            if industry_code:
                q['industry_code'] = industry_code
            if status:
                q['status__in'] = status
            if type:
                q['type__in'] = type
            if state:
                q['state__in'] = state
            if city:
                q['city__in'] = state
            queryset = queryset.filter(**q)
        return queryset


class StationViewSet(viewsets.ModelViewSet):
    # queryset = Station.objects.all()
    serializer_class = StationSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('pcb', 'city', 'state', 'prefix')

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = Station.objects.all()
        q = {}
        if self.request.query_params:
            uuid = self.request.query_params.getlist('uuid')
            name = self.request.query_params.getlist('name')
            prefix = self.request.query_params.getlist('prefix')
            status = self.request.query_params.getlist('status')
            state = self.request.query_params.getlist('state')
            city = self.request.query_params.getlist('city')
            if uuid:
                q['uuid__in'] = uuid
            if name:
                q['name__in__icontains'] = name
            if prefix:
                q['prefix__in'] = prefix
            if status:
                q['status__in'] = status
            if type:
                q['type__in'] = type
            if state:
                q['state__in'] = state
            if city:
                q['city__in'] = state
            queryset = queryset.filter(**q)
        return queryset


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
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('station', 'parameter')


class ReadingViewSet(viewsets.ModelViewSet):
    queryset = Reading.objects.all()
    serializer_class = ReadingSerializer


class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
