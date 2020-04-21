import logging

from api.models import StationParameter, Parameter, Station, Reading

log = logging.getLogger('vepolink')


def check_station_parameters(**details):
    prefix = details.get('prefix')
    readings = details.get('readings')
    station = Station.objects.get(prefix=prefix)
    for parameter in readings.keys():
        parameter = parameter.lower()
        if parameter == 'timestamp':
            continue
        param, _ = Parameter.objects.get_or_create(name=parameter)
        sparam, created = StationParameter.objects.get_or_create(
            station=station,
            parameter=param  # lower case only
        )
        if created:
            print('Creating parameter %s' % parameter)
            log.warning('%s param added on Station:%s' % (parameter,
                                                          sparam.station))
