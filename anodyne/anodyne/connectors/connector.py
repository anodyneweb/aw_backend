"""This file will be called by gatekeeper"""
import csv
import logging
import os
from datetime import datetime

from anodyne.connectors.to_database import ToDatabase
from anodyne.connectors.to_pcb import ToPCB
from api.models import Station

log = logging.getLogger('vepolink')


# custom __format__() method
class ReadCSV:

    def __init__(self, filename):
        self.filename = filename
        self.basename = os.path.basename(filename)

    def get_reading(self):
        with open(self.filename, encoding='utf-8') as f:
            reader = list(csv.reader(f))
            readings = {}
            for idx, row in enumerate(reader):
                if row[0].startswith('@'):
                    param = row[0]
                    if '_' in param:
                        param = str(param.split('_')[-1]).lower()
                    tstamp, value = reader[idx + 2]
                    readings[param] = value
                    try:
                        tstamp = datetime.strptime(tstamp, "%y%m%d%H%M%S")
                    except:
                        tstamp = tstamp
            readings['timestamp'] = tstamp
        return readings
        # df = pd.DataFrame([readings])
        # print(df)

    def process(self):
        """
        Process the file as required:
        - to DB
        - to PCB
        :return:
        """
        # prefix_timestamp.csv
        prefix = os.path.basename(self.filename).split('_')[0]
        details = {
            # 'readings': self.to_list,
            'prefix': prefix,
            'filename': self.filename,
            'basename': self.basename,
            'received_on': datetime.now().strftime('%Y%m%d%H%M%S'),
            'processed': False,
            'msg': None,
            'err': None
        }
        try:
            station = Station.objects.get(prefix=prefix)
            details['readings'] = self.get_reading()
            # TODO: each process is different we can use celerytasks for each
            # TODO: Adding Reading to Database is complete
            # task 1: Add Reading to database
            db = ToDatabase(**details)
            db_status = db.insert()
            details.update(db_status)
            log.info('%s: %s' % (self.basename, db_status))
            # task 2: Upload file to PCB if required.
            # TODO: PCB Upload is pending
            if station.active:
                # Upload status should be updated on Station Info
                pcb = ToPCB(**details)
                pcb_status = pcb.upload()
                details.update(pcb_status)
            else:
                details['msg'] = '%s: PCB Upload is blocked.'
                details['status'] = False
        except Station.DoesNotExist:
            message = 'Station with prefix: %s does not exist.'
            log.error(message)
            details['status'] = False
            details['msg'] = message
        return details
