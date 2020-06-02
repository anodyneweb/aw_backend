from django.http import HttpResponse
from django.template.loader import get_template
from django.views import View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import RegistrationSerializer


class SignUpView(APIView):
    permission_classes = []  # disabling authentication

    # we cannot list registrations without authentication
    # def get(self, request, format=None):
    #     registrations = Registration.objects.all()
    #     serializer = RegistrationSerializer(registrations, many=True)
    #     return Response(serializer.data)

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswrodView(View):
    permission_classes = []  # disabling authentication

    # we cannot list registrations without authentication
    # def get(self, request, format=None):
    #     registrations = Registration.objects.all()
    #     serializer = RegistrationSerializer(registrations, many=True)
    #     return Response(serializer.data)

    def get(self, request):
        content = {}
        info_template = get_template('forgot-password.html')
        html = info_template.render(content, request)
        return HttpResponse(html)
