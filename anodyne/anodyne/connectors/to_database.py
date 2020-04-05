import logging
import os

from django.db import IntegrityError

from api.models import Reading, Station

log = logging.getLogger('vepolink')


class ToDatabase:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def insert(self):
        basename = self.kwargs.get('basename')
        response = {
            'success': False,
            'msg': ''
        }
        db_status = {
            'db': response
        }
        try:
            station = Station.objects.get(prefix=self.kwargs.get('prefix'))
            Reading.objects.create(
                station=station,
                reading=self.kwargs.get('readings')
            )
            response['success'] = True
            response['msg'] = "%s: Added Readings" % basename
        except IntegrityError:
            response['msg'] = "%s: Reading exists." % basename
            return db_status
        except Exception as err:
            response['success'] = False
            response['msg'] = "%s: Failed to readings to databse %s" % (
                basename, err
            )

        return db_status
