import json
import logging
import math
from django.db import IntegrityError

from api.models import Reading, Station, StationInfo

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
                sinfo, created = StationInfo.objects.get_or_create(station=station)
                obj = sinfo if sinfo else created
                obj.last_seen = readings.get('timestamp')
                obj.last_upload_info = json.dumps(response)
                readings['timestamp'] = readings.get('timestamp').strftime('%Y-%m-%d %H:%M:%S ')
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
