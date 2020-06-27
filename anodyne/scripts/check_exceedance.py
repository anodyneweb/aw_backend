#!/usr/bin/python3
"""
Task of this watchdog is to only keep track in any new file has come to the
server this will intimate application about new files for processing.
This file will run as independent entity.
"""
import argparse
import os
import sys
import django

FTP_BASE = os.environ.get('FTP_PATH', '/var/www/ftp_home/')
#  you have to set the correct path to you settings module
# TODO: to enable this host django app properly on server
PROJ_PATH = "/home/ubuntu/aw_backend/anodyne"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "anodyne.settings")
sys.path.append(PROJ_PATH)
django.setup()

from django.db import IntegrityError
from django.db.models import F

from anodyne import settings
from api.utils import send_mail, send_sms

from api.models import Station, Reading, StationParameter, \
    Exceedance, SMSAlert
from datetime import datetime, timedelta
import pandas as pd
import logging

log = logging.getLogger('vepolink')


# 0 0,2,4,6,8,10,12,14,16,18,20,22 * * * sudo python3 /home/ubuntu/aw_backend/anodyne/scripts/check_exceedance.py
# Runs every 2nd hour
def check4exceedance(hours=3):
    log.info('Checking Exceedance')
    to_date = datetime.now()
    from_date = to_date - timedelta(hours=hours)
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
        log.info('Exceedance Details:%s' % df.head())
        if not df.empty:
            pd.set_option('display.float_format', lambda x: '%.2f' % x)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cols = df.columns.drop('timestamp')
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            qry = {
                'param': F('parameter__name'),
                'max': F('maximum'),
                'min': F('minimum'),
                'unit': F('parameter__unit'),
            }
            params = StationParameter.objects.filter(station=station,
                                                     parameter__name__in=cols
                                                     ).values(**qry)
            params_message = []
            pmeta = {}
            for p in params:
                param = p.get('param')
                max, min, unit = p.get('max'), p.get('min'), p.get('unit')
                pmeta[param] = (max, min, unit)
            for col in cols:
                if pmeta.get(col):
                    max = pmeta.get(col)[0]
                    min = pmeta.get(col)[1]
                    unit = pmeta.get(col)[2]
                    exceed_df = df[(df[col] > max) | (df[col] < min)]
                    if not exceed_df.empty:
                        exceedances = []
                        for idx, row in exceed_df.iterrows():
                            tstamp, value = row['timestamp'], row[col]
                            tmp = {
                                "station": station,
                                "parameter": col,
                                "value": value,
                                "timestamp": tstamp
                            }

                            sms_details = {
                                "industry": station.industry.name,
                                "industry_address": station.industry.address,
                                "industry_category": station.industry.type,
                                "parameter": col,
                                "current_value": value,
                                "param_threshold": max,
                                "param_unit": 'unit',
                                "monitoring_type": p.get('monitoring_type'),
                                "monitoring_id": p.get('monitoring_id'),
                                "timestamp": tstamp
                            }

                            exceedances.append(tmp)
                        if exceedances:
                            try:
                                Exceedance.objects.bulk_create(
                                    [Exceedance(**q) for q in exceedances])
                            except IntegrityError:
                                pass
                            # tstamp format Mon, 17-Jun-2020 12:15
                            msg = """
SMS ALERT FROM VEPOLINK
ALERT:{monitoring_type}
Industry Name:{industry} {industry_address}
CATEGORY:{industry_category}
LOCATION:{monitoring_id}
EXCEEDING PARAMETER:{param}
VALUE: {current_val} {param_unit} against Pres. Stand. {param_threshold}
{timestamp}

Avg Value for last 15 Min
Respond at customercare@anodyne.in"""
                            msg = '%s exceeds %s times in last 3 hours.' % (
                                col, len(exceed_df[col]))
                            log.info(msg)
                            # TODO: send sms here

                            email_id = station.user_email.split(';')
                            # email_id = station.industry.user.email.split(';')

                            try:
                                send_mail(subject='Alert From VepoLink',
                                          message=msg,
                                          from_email=settings.EMAIL_HOST_USER,
                                          # recipient_list=[station.industry.user.email],
                                          recipient_list=email_id,
                                          # html_message=html_content,
                                          #                fail_silently=True
                                          )
                            except Exception as err:
                                log.exception(
                                    'Failed to send exceedance email to %s due to %s' % (
                                        email_id,
                                        err))
                            SMSAlert.objects.create(
                                station=station,
                                message=msg,
                                contact=station.user_ph
                            )
                            # numbers = station.industry.user.phone
                            numbers = station.user_ph
                            try:
                                send_sms(numbers=numbers, content=msg)
                            except Exception as err:
                                log.exception(
                                    'Failed to send exceedance sms to %s due to %s' % (
                                        numbers,
                                        err))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Exceednace check')
    check4exceedance()
