import logging
import time
from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login
from django.core.mail import get_connection, EmailMultiAlternatives
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect
from django.template.context_processors import csrf
from django.template.loader import get_template
from geopy import Nominatim
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import Station, Reading, City
import pandas as pd
log = logging.getLogger('vepolink')


def epoch_timestamp(ts, tformat="%Y-%m-%d %H:%M:%S"):
    try:
        return int(time.mktime(datetime.strptime(
            ts, tformat).timetuple()))
    except ValueError:
        log.info('Warning: Incorrect time format, trying other')
    # try other formats if above fails
    try:
        # 2019.08.26 17:04:00
        tformat = "%Y.%m.%d %H:%M:%S"
        return int(time.mktime(datetime.strptime(
            ts, tformat).timetuple()))
    except ValueError:
        pass
    try:
        # 20191231606290
        tformat = "%Y%m%d%H%M%S"
        return int(time.mktime(datetime.strptime(
            ts, tformat).timetuple()))
    except ValueError:
        raise


def send_mail(subject, message, from_email,
              recipient_list, bcc=None, cc=None,
              fail_silently=False, auth_user=None,
              auth_password=None, connection=None, attachments=None,
              headers=None, alternatives=None, reply_to=[],
              html_message=None):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If auth_user is None, use the EMAIL_HOST_USER setting.
    If auth_password is None, use the EMAIL_HOST_PASSWORD setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = connection or get_connection(
        username=auth_user,
        password=auth_password,
        fail_silently=fail_silently,
    )
    mail = EmailMultiAlternatives(
        subject=subject, body=message,
        from_email=from_email, to=recipient_list,
        bcc=bcc, connection=connection,
        attachments=attachments, headers=headers,
        alternatives=alternatives, cc=cc,
        reply_to=reply_to
    )
    if html_message:
        mail.attach_alternative(html_message, 'text/html')

    return mail.send()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def long_lat_zip(request):
    geolocator = Nominatim()
    city = request.GET.get('city', '')
    city = City.objects.get(id=city)

    lat = zipcode = lng = ''
    location = geolocator.geocode("%s, %s" % (city.state, city))
    if location:
        lat, lng = location.latitude, location.longitude
    try:
        zipcode = location.raw.get('display_name')
        if zipcode:
            zipcode = zipcode.split(',')[-2].strip()
    except (ValueError, AttributeError):
        pass
    return JsonResponse(dict(longitude=lng, latitude=lat, zipcode=zipcode))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cities(request):
    state = request.GET.get('state') or None
    if state:
        try:
            state = int(state)
            cities = City.objects.filter(state__id=state)
        except ValueError:
            cities = City.objects.filter(state__name=state)
        cities = cities.values_list('id', 'name')
    else:
        cities = City.objects.all().values_list('id', 'name')
    return JsonResponse(dict(cities=sorted(cities, key=lambda x: x[1])))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_station_reading(request):
    # User /api/reading to POST
    message = []
    pk = request.GET.get('pk')
    if not pk:
        return HttpResponseBadRequest('Station missing')
    # date format 200213122657 => strptime '%y%m%d%H%M%S'
    from_dt = request.GET.get('from_dt')
    to_dt = request.GET.get('to_dt')
    if from_dt and to_dt:
        from_dt = datetime.strptime(from_dt, '%y%m%d%H%M%S')
        to_dt = datetime.strptime(to_dt, '%y%m%d%H%M%S')
    else:
        from_dt = datetime.now() - timedelta(hours=48)
        to_dt = datetime.now()
    try:
        station = Station.objects.get(pk=pk)
        qs = Reading.objects.filter(station=station,
                                    # reading__ph__gte=5,
                                    reading__timestamp__gte=from_dt,
                                    reading__timestamp__lte=to_dt,
                                    )
        if not qs:
            message.append({'error': 'No records for the selected range'})
        qs = qs.select_related('station')
        qs = qs.values_list('reading', flat=True)
        qs = dict(
            name=station.name,
            prefix=station.prefix,
            status='success',
            start=from_dt,
            end=to_dt,
            count=len(qs),
            message=message,
            readings=list(qs)
        )
        return JsonResponse(qs, status=status.HTTP_200_OK)
    except Station.DoesNotExist:
        return HttpResponseBadRequest('Station missing')


def buttonsview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    template = get_template('buttons.html')
    html = template.render(context, request)
    return HttpResponse(html)


def cardsview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    template = get_template('cards.html')
    html = template.render(context, request)
    return HttpResponse(html)


def chartsview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    print(request.GET)
    template = get_template('charts.html')
    html = template.render(context, request)
    return HttpResponse(html)


def tablesview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """

    reading = Reading.objects.all().values_list('reading', flat=True)
    df = pd.DataFrame(reading)
    columns = list(df.columns)
    new_order = ['timestamp']
    for col in columns:
        if col != 'timestamp':
            new_order.append(col)
    df = df[new_order]

    # TODO: order the column and capitalize it
    # <table class="table table-bordered" id="dataTable" width="100%" cellspacing="0">
    context = {
        'tabular': df.to_html(classes="table table-bordered",
                              table_id="dataTable", index=False,
                              justify='center')
    }
    template = get_template('tables.html')
    html = template.render(context, request)
    return HttpResponse(html)


def utilities_animationview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    print(request.GET)
    template = get_template('utilities-animation.html')
    html = template.render(context, request)
    return HttpResponse(html)


def utilities_borderview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    print(request.GET)
    template = get_template('utilities-border.html')
    html = template.render(context, request)
    return HttpResponse(html)


def utilities_colorview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    print(request.GET)
    template = get_template('utilities-color.html')
    html = template.render(context, request)
    return HttpResponse(html)


def utilities_otherview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    print(request.GET)
    template = get_template('utilities-other.html')
    html = template.render(context, request)
    return HttpResponse(html)


def blankview(request):
    """Show the login page.

    If 'next' is a URL parameter, add its value to the context.  (We're
    mimicking the standard behavior of the django login auth view.)
    """
    context = {}
    print(request.GET)
    template = get_template('blank.html')
    html = template.render(context, request)
    return HttpResponse(html)
