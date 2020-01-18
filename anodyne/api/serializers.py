# Serializers define the API representation.
from anodyne import settings
from .models import User, Station, Industry
from rest_framework import serializers

from .utils import send_mail


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('name', 'email', 'staff', 'admin', 'country',
                  'state', 'city', 'address', 'zipcode', 'is_active')

        # exclude = ('password', 'last_login',)

    def create(self, validated_data):
        user = super(UserSerializer, self).create(validated_data)
        # user.set_password(validated_data['password'])
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
        send_mail(subject='Welcome from VepoLink',
                      message='',
                      from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        html_message=html_content)

class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        exclude = ('uuid',)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        exclude = ('uuid',)
