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
        try:
            reading = Reading.objects.create(
                station__uuid=self.kwargs.get('station'),
                reading=self.kwargs.get('reading'),
                filename=self.kwargs.get('filename')
            )
            reading.save()
            response['success'] = True
            response['add_reading_msg'] = "Successfully added %s readings to" \
                                          " database" % self.kwargs.get(
                'filename')
        except Exception as err:
            response['add_reading_msg'] = err

        return to_db_info
