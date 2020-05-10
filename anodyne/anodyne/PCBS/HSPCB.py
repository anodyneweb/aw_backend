import json

import requests
import logging

from api import utils
from api.models import Parameter

log = logging.getLogger('vepolink')


class Handle:
    def __init__(self, **kwargs):
        self.site = kwargs.get('station')
        self.params = kwargs.get('params')
        self.readings = kwargs.get('readings')
        self.key = self.key
        industry_id = self.site.industry.industry_id
        self.URL = 'http://164.100.160.248/hrcpcb-api/api/industry/' \
                   '{industryId}/station/{stationId}/data'.format(
            industryId=industry_id, stationId=self.site.site_id)

    def get_headers(self):
        headers = {
            'Authorization': 'Basic {key}'.format(key=self.key),
            'Content-Type': 'application/json',
        }
        return headers

    def upload(self):
        status = requests.post(
            self.URL,
            headers=self.get_headers(),
            data=self._get_data()
        )
        log.info('HSPCB Upload Status :%s' % status)
        return status

    def _get_data(self):
        data = []
        for row in self.readings:
            ts = row.get('timestamp')
            ts = utils.epoch_timestamp(ts)
            for param in self.params:
                param = param.strip() if param else param
                if not param: break

                reading = row.get(param) or 0
                try:
                    p = Parameter.objects.get(
                        parameter=param.lower()
                    )
                    param_unit = p.unit
                    param = str(param).lower()
                    deviceId = '_'.join(['an',
                                         self.site.industry.industry_id,
                                         self.site.site_id,
                                         param])
                    tmp_data = {
                        "deviceId": deviceId,
                        "params": [{
                            "flag": "U",
                            "parameter": param,
                            "timestamp": ts,
                            "unit": param_unit,
                            "value": reading
                        }]
                    }
                    data.append(tmp_data)
                except Exception as err:
                    log.exception('HSPCB Upload failure:%s' % err)

        log.info('HSPCB URL:%s' % self.URL)
        log.info('HSPCB DATA:%s' % data)
        return json.dumps(data)
