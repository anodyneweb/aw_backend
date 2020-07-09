import json
import logging
import math
from django.db import IntegrityError
from django.db.models import F
from datetime import datetime, timedelta

from django.template.loader import render_to_string

from anodyne import settings
from api.models import Reading, Station, StationInfo, StationParameter, \
    Exceedance, SMSAlert
from api.utils import send_mail, send_sms

log = logging.getLogger('vepolink')


class ToDatabase:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def send_alert(self, exceedances):
        log.info('Sending Alert')
        log.info(exceedances)
        try:
            for exceedance in exceedances:
                station = exceedance.get('station')
                parameter = exceedance.get('parameter')
                param = StationParameter.objects.get(
                    station=station,
                    allowed=True,
                    parameter__name=parameter
                )
                context = {
                    'param': parameter,
                    'value': '%s %s against Pres. Stand. %s %s' % (
                        exceedance.get('value'), param.parameter.unit,
                        param.maximum, parameter),
                    'category': station.industry.type,
                    'industry': '%s, %s, %s' % (
                        station.industry, station.industry.city,
                        station.industry.state),
                    'timestamp': exceedance.get('timestamp').strftime(
                        '%a, %d-%b-%Y %H:%M'),
                    'alert_type': station.monitoring_type,
                    'location': param.monitoring_id
                }

                mail_receipients = station.industry.user.email.split(';')

                html_content = render_to_string(
                    'alerts-mail/exceedance.html', context)
                send_mail(subject='Exceedance Alert',
                          recipient_list=mail_receipients,
                          cc=['info@anodyne.in', 'incompletesagar@gmail.com'],
                          html_message=html_content,
                          message='',
                          from_email=settings.EMAIL_HOST_USER
                          )
                phone_receipients = station.industry.user.phone
                sms_context = "SMS ALERT FROM VEPOLINK\n" \
                              "ALERT:{alert_type}\nIndustry Name:{industry}\n" \
                              "CATEGORY:{category}\nLOCATION:{location}\n" \
                              "EXCEEDING PARAMETER:{param}\nVALUE: {value}\n{timestamp}\n" \
                              "Avg Value for last 15 Min\n" \
                              "Respond at customercare@anodyne.in".format(**context)
                log.info('Initiating Exceedance SMS')
                send_sms(numbers=phone_receipients, content=sms_context)
        except:
            log.exception('Failing to Send Mail alert')

    def check_exceedance(self, station, reading):
        log.info('Checking exceedance %s' % station)
        q = {
            'param': F('parameter__name'),
            'min': F('minimum'),
            'max': F('maximum')

        }
        params = StationParameter.objects.filter(
            station=station,
            allowed=True
        ).values(**q)
        exceedances_rec = []
        for meta in params:
            exceedances = {}
            param = meta.get('param')
            pmax = float(meta.get('max', 0))
            pmin = float(meta.get('min', 0))
            if pmin == pmax or pmax == 0:
                continue
            else:
                current_val = float(reading.get(param, 0))
                if current_val > pmax:
                    exceedances.update({
                        'parameter': param,
                        'value': current_val,
                    })
                if param.lower() == 'ph' and pmin > current_val > pmax:
                    exceedances.update({
                        'parameter': param,
                        'value': current_val,
                    })
                if exceedances:
                    log.info('Exceedances %s' % exceedances)
                    exceedances.update({'timestamp': reading.get('timestamp'),
                                        'station': station})
                    exceedances_rec.append(exceedances)

        if exceedances_rec:
            try:
                Exceedance.objects.bulk_create(
                    [Exceedance(**q) for q in exceedances_rec])
                log.info('Exceedance observed %s' % station)
            except IntegrityError:
                pass

            self.send_alert(exceedances_rec)

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
                            clean_reading[k] = float('{0:.2f}'.format(value))
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
                self.check_exceedance(station, readings)
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
