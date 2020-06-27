from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.views import View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from anodyne import settings
from api.serializers import RegistrationSerializer
from api.utils import send_mail
from dashboard.forms import RegistrationForm
from dashboard.views import get_error


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


class SubmitQueryView(View):
    permission_classes = []  # disabling authentication

    # we cannot list registrations without authentication
    # def get(self, request, format=None):
    #     registrations = Registration.objects.all()
    #     serializer = RegistrationSerializer(registrations, many=True)
    #     return Response(serializer.data)

    def get(self, request):
        content = {
            'form': RegistrationForm()
        }
        info_template = get_template('submit-query.html')
        html = info_template.render(content, request)
        return HttpResponse(html)

    def post(self, request):
        form = RegistrationForm(request.POST)
        try:
            query = request.GET.get('query')[0]
            fname = request.GET.get('fname')[0]
            phone = request.GET.get('phone')[0]
            email = request.GET.get('email')[0]
            send_mail(subject='Query Received From: %s %s %s' % (
            fname, phone, email),
                      message=query,
                      from_email=settings.EMAIL_HOST_USER,
                      recipient_list=['info@anodyne.in'],
                      # html_message=html_content,
                      #                fail_silently=True
                      )
        except:
            pass

        if form.is_valid():
            form.save()
            messages.success(request, 'Query Submitted Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')
        return redirect(reverse('login'))
