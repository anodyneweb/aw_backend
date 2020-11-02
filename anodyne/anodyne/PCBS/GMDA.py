import json
import requests
from datetime import datetime
from api.models import Parameter, Station

import logging

log = logging.getLogger('vepolink')

class Handle:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.readings = kwargs.get('readings')
        self.params = kwargs.get('params')
        self.site = Station.objects.get(prefix=kwargs.get('prefix'))
        self.tokenURL = 'https://smartcity.gmda.gov.in/ds/1.0.0/public/token'
        self.URL = "https://smartcity.gmda.gov.in/abstraction/1.0.0/adapters/inbound/LxqlKXMB3RRmL3tUiwL2"

    def get_token_headers(self):
        headers = {
            'Content-Type': 'application/json'
        }
        return headers

    def get_credentials(self):
        cred = {
            'username': 'waterapi@gurugram.com',
            'password': 'Gmda@1234',
            'grant_type': 'password'
        }
        return cred

    def get_token(self):
        res = requests.post(
            url=self.tokenURL,
            data=json.dumps(self.get_credentials()),
            headers=self.get_token_headers()
        )
        res_json = res.json()
        token = res_json.get('access_token')
        return token

    def get_headers(self):
        head = {
            'Authorization': 'Bearer {}'.format(str(self.get_token())),
            'Content-Type': 'application/json'
        }
        return head

    def _get_data(self):
        data = []
        if self.readings:
            for param, value in self.readings.items():
                if param != 'timestamp':
                    reading = value
                    try:
                        p = Parameter.objects.get(name__iexact=param)
                        unt = p.unit.name
                        tmp_data = {
                            "input": {
                                "date_time": self.readings.get('timestamp').strftime('%Y-%m-%dT%H:%M:%SZ'),
                                "WaterMeterReading": reading,
                                "unit": unt,
                                "deviceId": self.site.name,
                                "lat": str(self.site.latitude),
                                "long": str(self.site.longitude),
                                "LocationName": self.site.name,
                                "Address": self.site.address,
                                "providerName": "Anodyne",
                                "providerContactPersonName": "Neeraj",
                                "Designation": "Manager",
                                "email": self.site.user_email,
                                "phone": self.site.user_ph,
                                "make": "UPC",
                                "model": "MAG-110",
                                "serial": "1907800694",
                                "consumerNo": "1232342342",
                                "InstantaneousFlow": 45.56
                            }}
                        log.info('data created from the reading: %s ' % data)
                        data.append(tmp_data)
                    except Exception as err:
                        log.exception('GMDA Upload failure:%s' % err)

        log.info('GMDA URL:%s' % self.URL)
        log.info('GMDA DATA:%s' % data)
        return json.dumps(data)

    def upload(self):
        log.info('Initiating upload for the data upload')
        try:
            response = requests.post(
                url=self.URL,
                headers=self.get_headers(),
                data=self._get_data()
            )
            if response.status_code == 200:
                log.info('Status of the data upload: %s ' % response.json())
                return True, response.json()
            else:
                return False, response

        except Exception as err:
            return False, str(err)
