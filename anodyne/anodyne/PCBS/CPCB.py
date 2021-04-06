import json
import requests
from datetime import datetime
from api.models import Parameter, Station, StationParameter
from api import utils

import logging

log = logging.getLogger('vepolink')

class Handle:
    def __init__(self, **kwargs):
        self.site = Station.objects.get(prefix=kwargs.get('prefix')) 
        log.info('cpcb site: %s' % self.site)
        self.prefix = kwargs.get('prefix')
        log.info('cpcb prefix: %s' % self.prefix)
        self.readings = kwargs.get('readings')
        log.info('cpcb readings: %s' % self.readings)
        self.key = 'N2ZiMWIyMWVmY2MwNGU4NmIyMTJmYWIyMjAwNGQ0ZGI='
        self.industry_id = self.site.industry.industry_id
        log.info('cpcb industry: %s' % self.industry_id)
        log.info('cpcb site id: %s' % self.site.site_id)
        self.URL = 'http://rtdms.cpcb.gov.in/v1.0/industry/{industryId}/station/{stationId}/data'.format(
            industryId=self.industry_id, stationId=self.site.site_id)

    def get_headers(self):
        header = {
            'Authorization': 'Basic {key}'.format(key=self.key),
            'Content-Type': 'application/json'
        }
        log.info('CPCB headers: %s' % header)
        return header

    def get_data(self):
        log.info('Preparing data to upload')
        if self.readings:
            for param, value in self.readings.items():
                if param != 'timestamp':
                    reading = value
                    param = param

                ts = str(self.readings.get('timestamp'))
                ts = utils.epoch_timestamp(ts)
                try:
                    if param != 'timestamp':
                        p = Parameter.objects.get(name__iexact=param)
                    unt = p.unit.name
                    alias = p.alias
                    site_param = StationParameter.objects.get(parameter=p, station=self.site, allowed=True)
                    mon_id = site_param.monitoring_id
                    tmp_data = [{
                        u"params": [{
                            u"timestamp": str(ts),
                            u"flag": u"U",
                            u"parameter": alias.lower(),
                            u"unit": unt,
                            u"value": reading
                        }],
                        u"deviceId": mon_id,
                        u"diagnostics": []
                    }]

                except Exception as err:
                    log.exception('CPCB Upload failure:%s' % err)

        log.info('CPCB DATA:%s' % json.dumps(tmp_data))
        return json.dumps(tmp_data)

    def upload(self):
        log.info('CPCB Initiating Data Uploading')
        try:
            response = requests.post(
            self.URL,
            headers=self.get_headers(),
            data=self.get_data()
                )
            if response.status_code == 200:
                log.info('Status of the data upload: %s ' % response.json())
                return True, response.json()
            else:
                return False, response
        except Exception as err:
            return False, str(err)
