import json
import logging
import math
from django.db import IntegrityError
from django.db.models import F
from datetime import datetime, timedelta

from anodyne import settings
from api.models import Reading, Station, StationInfo, StationParameter, \
    Exceedance, SMSAlert
from api.utils import send_mail

log = logging.getLogger('vepolink')


class ToDatabase:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _clean_reading(self, reading):
        if reading:
            clean_reading = {}
            for k, v in reading.items():
                if k.lower() == 'timestamp':
                    k = k.lower()
                    clean_reading[k] = v
                else:
                    try:
                        value = float(v)
                        if not math.isnan(value):
                            clean_reading[k] = '{0:.2f}'.format(value)
                    except ValueError:
                        pass
            if len(clean_reading.keys()) > 1:
                return clean_reading

    def insert(self):
        basename = self.kwargs.get('basename')
        response = {
            'success': False,
            'msg': ''
        }
        db_status = {
            'db': response
        }
        log.info('Adding to database:%s' % self.kwargs)
        try:
            readings = self._clean_reading(self.kwargs.get('readings'))
            if readings:
                station = Station.objects.get(prefix=self.kwargs.get('prefix'))
                Reading.objects.create(
                    station=station,
                    reading=readings
                )
                station.status = 'Live'
                station.save()
                sinfo, created = StationInfo.objects.get_or_create(
                    station=station)
                obj = sinfo if sinfo else created
                obj.last_seen = readings.get('timestamp')
                obj.last_upload_info = json.dumps(response)
                readings['timestamp'] = readings.get('timestamp').strftime(
                    '%Y-%m-%d %H:%M:%S ')
                obj.readings = json.dumps(readings)
                obj.save()
                log.info('Added to Reading successfully')
                response['success'] = True
                response['msg'] = "%s: Added Readings" % basename
            else:
                response['success'] = False
                response['msg'] = "%s: No Readings Found" % basename
        except IntegrityError:
            response['msg'] = "%s: Reading exists." % basename
            return db_status
        except Exception as err:
            response['success'] = False
            response['msg'] = "%s: Failed to readings to databse %s" % (
                basename, err
            )
            log.exception('DB ERROR')

        return db_status


import pandas as pd


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
