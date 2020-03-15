"""This file will be called by gatekeeper"""
import csv
import json
import logging
import os
import re
from datetime import datetime, timedelta
from os.path import basename
import pandas as pd

from anodyne.connectors.to_database import ToDatabase
from anodyne.connectors.to_pcb import ToPCB
from api.models import Station, StationParameter
import os

log = logging.getLogger('anodyne')


# custom __format__() method
class ReadCSV:

    def __init__(self, file_rcvd):
        self.file_rcvd = file_rcvd

    @property
    def to_list(self):
        with open(self.file_rcvd, encoding='utf-8') as f:
            reader = list(csv.reader(f))
            alist = []
            for idx, row in enumerate(reader):
                if row[0].startswith('@'):
                    param = row[0]
                    # LOWERING THE PARAMETER TO KEEP IT UNIQUE
                    param = str(param).lower()
                    if '_' in param:
                        param = param.split('_')[-1]
                    tstamp, value = reader[idx + 2]
                    try:
                        alist.append(
                            {
                                # column_name : #value
                                'parameter': param,
                                'value': value,
                                'timestamp': tstamp,
                                # 'exceeding': False,
                                # 'min': 0,
                                # 'max': 0
                            }
                        )
                    except IndexError:
                        continue
        return alist

    @property
    def to_df(self):
        try:
            df = pd.DataFrame(self.to_list)
            return df
        except:
            print('Failed to convert to dataframe.')
            pass

    def process(self):
        """
        Process the file as required:
        - to DB
        - to PCB
        :return:
        """

        # prefix_timestamp.csv
        prefix = os.path.basename(self.file_rcvd).split('_')[0]
        details = {
            # 'readings': self.to_list,
            'prefix': prefix,
            'filename': self.file_rcvd,
            'received_on': datetime.now().strftime('%Y%m%d%H%M%S'),
            'processed': False,
            'msg': None,
            'err': None
        }
        try:
            station = Station.objects.get(prefix=prefix)
            details['readings'] = self.update_reading(station)
            details['station'] = station.uuid
            to_db = ToDatabase(**details)
            to_db_status = to_db.insert()
            to_pcb = ToPCB(**details)
            """
            ...
            ...
            ...
            """
        except Station.DoesNotExist:
            message = 'Station with prefix: %s does not exist.'
            log.error(message)
            details['msg'] = message
            return details

    def update_reading(self, station):
        """
        Here we are trying create reading dictionary with all values of each
        parameter
        like:
            min,
            max,
            exceeding,
            etc.
        then all these values will be sent to Reading table
        :return:
        """
        readings = []
        for reading in self.to_list:
            tmp = reading
            try:
                sp, created = StationParameter.objects.get_or_create(
                    station=station,
                    parameter=reading.get('parameter')
                )
                sp = sp if sp else created
                if 0 < float(sp.maximum) < float(
                        reading.get('value')) > float(sp.minimum):
                    tmp['exceeding'] = True
                else:
                    tmp['exceeding'] = False
                tmp['min'] = sp.minimum
                tmp['max'] = sp.maximum
                tmp['allowed'] = sp.allowed
            except Exception as err:
                log.exception('Failed to Update Reading')
                continue
            readings.append(tmp)
        return readings