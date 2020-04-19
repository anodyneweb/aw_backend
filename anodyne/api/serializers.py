# Serializers define the API representation.
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from anodyne import settings
from .models import User, Station, Industry, StationInfo, City, State, PCB, \
    StationParameter, Reading, Registration, Category, Parameter, Unit
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
        html_content = render_to_string('registration/welcome_mail.html',
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
    uuid = serializers.UUIDField(required=False)
    city = serializers.ReadOnlyField(source='city.name')

    class Meta:
        model = Industry
        # fields = '__all__'
        exclude = ('industry_code', 'country', 'address',)


class StationSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(required=False)
    city = serializers.ReadOnlyField(source='city.name')

    class Meta:
        model = Station
        # fields = '__all__'
        exclude = ('key', 'pub_key', 'pvt_key', 'country', 'address')
        widgets = {
            'address': serializers.CharField(),
            'key': serializers.CharField(),
            'pub_key': serializers.CharField(),
            'pvt_key': serializers.CharField(),
            'user_email': serializers.CharField(),
            'user_ph': serializers.CharField(),
            'cpcb_email': serializers.CharField(),
            'cpcb_ph': serializers.CharField(),

        }

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


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = '__all__'


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super(MyTokenObtainPairSerializer, cls).get_token(user)

        # Add custom claims
        token['fav_color'] = user.fav_color
        return token


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)

    def validate(self, data):
        # The `validate` method is where we make sure that the current
        # instance of `LoginSerializer` has "valid". In the case of logging a
        # user in, this means validating that they've provided an email
        # and password and that this combination matches one of the users in
        # our database.
        email = data.get('email', None)
        password = data.get('password', None)
        # Raise an exception if an
        # email is not provided.
        if email is None:
            raise serializers.ValidationError(
                'An email address is required to log in.'
            )

        # Raise an exception if a
        # password is not provided.
        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )

        # The `authenticate` method is provided by Django and handles checking
        # for a user that matches this email/password combination. Notice how
        # we pass `email` as the `username` value since in our User
        # model we set `USERNAME_FIELD` as `email`.
        user = authenticate(username=email, password=password)
        # If no user was found matching this email/password combination then
        # `authenticate` will return `None`. Raise an exception in this case.
        if user is None:
            raise serializers.ValidationError(
                'A user with this email and password was not found.'
            )

        # Django provides a flag on our `User` model called `is_active`. The
        # purpose of this flag is to tell us whether the user has been banned
        # or deactivated. This will almost never be the case, but
        # it is worth checking. Raise an exception in this case.
        if not user.is_active:
            raise serializers.ValidationError(
                'This user has been deactivated.'
            )

        # The `validate` method should return a dictionary of validated data.
        # This is the data that is passed to the `create` and `update` methods
        # that we will see later on.
        return {
            'email': user.email,
            # 'username': user.username,
            'token': user.token
        }
