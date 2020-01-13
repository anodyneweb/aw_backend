# Serializers define the API representation.
from .models import User, Station, Industry
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ('password', 'last_login',)


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        exclude = ('uuid',)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        exclude = ('uuid',)
