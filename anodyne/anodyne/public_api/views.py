import logging

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
log = logging.getLogger('vepolink')


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
            query = 'Thanks for your query, our team will get back to you soon.\n'
            query += request.POST.get('query')
            fname = request.POST.get('fname')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            send_mail(subject='Query Has been received: %s %s %s' % (fname, phone, email),
                      message=query,
                      from_email=settings.EMAIL_HOST_USER,
                      cc=['customercare@anodyne.in', settings.EMAIL_HOST_USER],
                      recipient_list=[email],
                      )
        except:
            log.exception('Email Error')

        if form.is_valid():
            form.save()
            messages.success(request, 'Query Submitted Successfully',
                             extra_tags='success')
        else:
            errors = get_error(form.errors)
            for err in errors:
                messages.info(request, err, extra_tags='danger')
        return redirect(reverse('login'))
