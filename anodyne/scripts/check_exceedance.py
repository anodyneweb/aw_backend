#!/usr/bin/python3
"""
Task of this watchdog is to only keep track in any new file has come to the
server this will intimate application about new files for processing.
This file will run as independent entity.
"""
import os
import sys

import django
from django.db import IntegrityError
from django.db.models import F

from anodyne import settings
from api.utils import send_mail

FTP_BASE = os.environ.get('FTP_PATH', '/var/www/ftp_home/')
#  you have to set the correct path to you settings module
# TODO: to enable this host django app properly on server
PROJ_PATH = "/home/ubuntu/aw_backend/anodyne"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "anodyne.settings")
sys.path.append(PROJ_PATH)
django.setup()
from api.models import Station, Reading, StationParameter, \
    Exceedance, SMSAlert
from datetime import datetime, timedelta
import pandas as pd


# Runs every 3rd hour
def check4exceedance():
    to_date = datetime.now()
    from_date = to_date - timedelta(hours=24)
    q = {
        'reading__timestamp__gte': from_date,
        'reading__timestamp__lte': to_date,
    }
    stations = Station.objects.filter(
        stationinfo__last_seen__gte=from_date).select_related()
    for station in stations:
        reading = Reading.objects.filter(station=station,
                                         **q).values_list('reading', flat=True)
        df = pd.DataFrame(reading)
        if not df.empty:
            pd.set_option('display.float_format', lambda x: '%.2f' % x)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cols = df.columns.drop('timestamp')
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            qry = {
                'param': F('parameter__name'),
                'max': F('maximum'),
                'min': F('minimum'),
            }
            params = StationParameter.objects.filter(station=station,
                                                     parameter__name__in=cols
                                                     ).values(**qry)
            pmeta = {}
            for p in params:
                param = p.get('param')
                max, min = p.get('max'), p.get('min')
                pmeta[param] = (max, min)
            for col in cols:
                if pmeta.get(col):
                    max = pmeta.get(col)[0]
                    min = pmeta.get(col)[1]
                    exceed_df = df[(df[col] > max) | (df[col] < min)]
                    if not exceed_df.empty:
                        exceedances = []
                        for idx, row in exceed_df.iterrows():
                            # print(row['timestamp'], row[col])
                            tstamp, value = row['timestamp'], row[col]
                            tmp = {
                                "station": station,
                                "parameter": col,
                                "value": value,
                                "timestamp": tstamp
                            }
                            exceedances.append(tmp)
                        if exceedances:
                            try:
                                Exceedance.objects.bulk_create(
                                    [Exceedance(**q) for q in exceedances])
                            except IntegrityError:
                                print('Exists..........')
                            msg = '%s exceeds %s times in last 3 hours.' % (
                            col, len(exceed_df[col]))
                            #TODO: send sms here
                            SMSAlert.objects.create(
                                station=station,
                                message=msg,
                                contact=station.user_ph
                            )
                            email_id = station.industry.user.email
                            try:
                                send_mail(subject='Alert From VepoLink',
                                          message=msg,
                                          from_email=settings.EMAIL_HOST_USER,
                                          # recipient_list=[station.industry.user.email],
                                          recipient_list=[email_id],
                                          # html_message=html_content,
                                          #                fail_silently=True
                                          )
                            except Exception as err:
                                print('Failed to send exceedance email to %s due to %s' % (email_id,
                                                                                           err))
