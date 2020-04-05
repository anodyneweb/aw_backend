# Serializers define the API representation.
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from anodyne import settings
from .models import User, Station, Industry, StationInfo, City, State, PCB, \
    StationParameter, Reading, Registration, Category
from .utils import send_mail


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password', 'placeholder': 'Password'}
    )

    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'staff', 'admin', 'country',
                  'state', 'city', 'address', 'zipcode', 'is_active',
                  'password')

        # exclude = ('password', 'last_login',)

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data.get('password'))
        user = super(UserSerializer, self).create(validated_data)
        user.save()
        self._registration_invite(user)
        return user

    def _registration_invite(self, user):
        context = {
            'name': user.name,
            'email': user.email
        }
        from django.template.loader import render_to_string
        html_content = render_to_string('registration/welcome.html',
                                        context)
        try:
            send_mail(subject='Welcome from VepoLink',
                      message='',
                      from_email=settings.EMAIL_HOST_USER,
                      recipient_list=[user.email],
                      html_message=html_content)
        except Exception as err:
            print('Failing to send mail %s' % err)


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        exclude = ('uuid',)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        exclude = ('uuid',)


class StationInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationInfo
        fields = '__all__'


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


class PCBSerializer(serializers.ModelSerializer):
    class Meta:
        model = PCB
        fields = '__all__'


class StationParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationParameter
        fields = '__all__'


class ReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reading
        fields = '__all__'


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


