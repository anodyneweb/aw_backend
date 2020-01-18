from django.core.mail import send_mail
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from anodyne import settings


class HelloView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        content = {'message': 'Hello, World!'}
        # x = send_mail(subject='Welcome from VepoLink',
        #               message='',
        #               from_email='VepoLink',
        #               recipient_list=['incompletesagar@gmail.com'],
        #               )
        # print(x)

        return Response(content)