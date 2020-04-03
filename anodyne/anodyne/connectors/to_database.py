import logging

from api.models import Reading, StationParameter, Parameter, Station
import pandas as pd

log = logging.getLogger('anodyne')


class ToDatabase:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def insert(self):
        response = {
            'success': False,
            'msg': ''
        }
        to_db_info = {
            'to_db': response
        }
        # Check for parameters, add if it doesnt exists
        df = pd.DataFrame(self.kwargs.get('reading'))
        parameters = list(df.parameter)
        log.info('Parameters found in %s\n%s' % (
            self.kwargs.get('filename'), parameters)
                 )
        for a in df.index:
            parameter = df.parameter[a]
            value = df.value[a]
            timestamp = df.timestamp[a]
            filename = df.filename[a]
            try:
                reading = Reading.objects.create(
                    station__uuid=self.kwargs.get('station'),
                    parameter__name=parameter,
                    value=value,
                    filename=filename,
                    timestamp=timestamp
                )
                reading.save()
                response['success'] = True
            except Exception as err:
                response['add_reading_%s_msg' % parameter] = err
                continue
        if response.get('success'):
            response[
                'add_reading_msg'] = "Successfully added %s readings to" \
                                     " database" % self.kwargs.get(
                'filename')
        return to_db_info
