"""This file will be called by gatekeeper"""
import csv
import json
import logging
import os
import re
from datetime import datetime, timedelta
from os.path import basename

import pandas as pd

from api.models import Station

log = logging.getLogger('anodyne')
# readings_log = logging.getLogger('readings')
# alert_log = logging.getLogger('alerts')
# sampler_log = logging.getLogger('sampler')

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


class GenFile4PCB:
    def __init__(self, filepath):
        self.stn_file = filepath
        self.stn_filename = basename(self.stn_file)
        self.station = None
        self.ftype = None

    def initiate(self):
        details = self.get_details()
        station = details.get('station')
        if station and isinstance(station, Station):  # OBJECT REQ
            if station.is_allowed:
                details['station'] = station.uuid
                # TODO(sagar) : to make upload a celery task we have to take
                # care of response
                response = celerytasks.upload(**details)
            else:
                response = dict(message='%s: BLOCKED.'
                                        'To enable upload check site '
                                        'settings' % station.name)
            # log.info(response)
            if 'timestamp' in response:
                response['timestamp'] = response.get('timestamp').strftime(
                    "%Y-%m-%d %H:%M:%S")

            details['station'] = station.uuid
            try:
                celerytasks.update_site_info.delay(station.uuid, response,
                                                   readings=details.get(
                                                       'readings'))
            except:
                celerytasks.update_site_info.delay(station.uuid, '',
                                                   readings=details.get(
                                                       'readings'))
            # self.add_reading(**details)
            celerytasks.add_reading.delay(**details)

            from anodyne.models import Reading2
            Reading2.objects.create(site=station,
                                    reading=details.get('readings'),
                                    filename=self.stn_filename,
                                    timestamp=datetime.now())
            # tasks.organize_stn_file.delay(self.stn_file, response)
            return response

    def get_details(self):
        """
        checks type of file and format the reading
        :return: site or error info
        """
        details = {}
        prefix, self.ftype = self.get_prefix()
        if prefix and self.ftype:
            # Get site object using prefix
            # station = Station.get_site(prefix)
            try:
                station = Station.objects.get(prefix=prefix)
                # self.ftype can be _scan, _analog or _max
                get_params = getattr(self, self.ftype)
                preadings, pmters = get_params()
                # TODO: SETTING PARAMETERS TO LOWERCASE
                params = [p.lower().strip() for p in pmters]
                # TODO: as requested by the team to used existing format
                # params = [HQ_PARAMS.get(p, p) for p in params]
                readings = [{k.strip().lower(): v for k, v in row.items()}
                            for row in preadings]
                df = pd.DataFrame.from_records(readings)
                if not df.empty:
                    readings_log.info('\n'
                                      '====================>{fn}'
                                      '<====================\n{df}'.format(
                        fn=self.stn_filename, df=df)
                    )
                details = {
                    'params': list(params), 'readings': readings,
                    'station': station, 'filename': self.stn_file,
                    'prefix': prefix, 'stn_filename': self.stn_filename,
                    'uuid': station.uuid, 'orig_params': list(pmters),
                    'filetype': self.ftype
                }
                # log.info('Station File Details:\n%s' % details)
            except Station.DoesNotExist:
                alert_log.warning('Station with prefix: %s not added yet '
                                  'for: %s' %
                                  (prefix, self.stn_filename)
                                  )
        return details

    def get_prefix(self):
        prefix = None
        try:
            with open(self.stn_file, encoding='utf-8') as f:
                first_row = next(f).split(',')
                key = first_row[0]
                # Get prefix first
                if key.endswith('Timestamp'):
                    prefix = self.stn_filename.split('_')[0]
                    self.ftype = '_scan'
                elif key.startswith('#T'):
                    prefix = first_row[-2]
                    self.ftype = '_max'
                elif key.startswith('@'):
                    prefix = first_row[0][-15:]
                    self.ftype = '_analog'
                elif len(first_row) == 3 and key in ['1', 1]:
                    prefix = first_row[-1].split('_')[0]
                    self.ftype = '_shreetech'
                elif first_row and 'SAMPLER' in first_row[1]:
                    sampler_log.info('Sampler File Detected')
                    prefix = first_row[3]
                    # self.ftype = '_sampler'
                    self._sampler()
                    self.ftype = None
                else:
                    log.warning('%s: Cannot Detect File Type' \
                                ' (max, scan or analog)' % self.stn_filename)
        except StopIteration:
            # log.error('%s seems empty' % self.stn_filename)
            pass
        except FileNotFoundError:
            log.error('%s exists no more.' % self.stn_file)
        except Exception as err:
            log.exception(err)
        if prefix:
            prefix = prefix.strip()
            try:
                # checking here only to avoid DB query
                df = pd.read_csv(STATIONS_CACHE)
                station = df.loc[df.prefix == prefix]
                if station.empty:
                    alert_log.warning(
                        'Cache: Station with prefix: %s missing | Filename: %s ' %
                        (prefix, self.stn_filename)
                    )
                    prefix = None
            except FileNotFoundError:
                # 'If file doesnt exists let DB handle'
                pass
        return prefix, self.ftype

    def _scan(self):
        with open(self.stn_file, encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = []
            rows = []
            for idx, row in enumerate(reader):
                # if idx == 0:
                #     prefix = row[1]
                if idx == 1:
                    headers = row  # first row
                elif idx > 1:
                    val = dict(zip(headers, row))  # straight from csv
                    # Formatting of key starts here
                    for key in list(val.keys()):
                        if key.startswith('Status'):
                            val.pop(key)
                        elif key.startswith('Measurement interval'):
                            val['timestamp'] = val.pop(key)
                        else:
                            # explained below
                            # COD - Measured value [mg/l] (Limit:0.00-....
                            # splitting with 'value ['
                            # or
                            # COD - Result (Limit:....
                            # splitting with '(Limit'
                            param = re.split('value \[|, |\(Limit',
                                             key)[0].replace(' ', '')
                            val[param] = val.pop(key)
                    rows.append(val)
        parameters = set([p.split('-')[0] for p in list(rows[0].keys())])
        # we need only parameters
        if 'timestamp' in parameters:
            parameters.remove('timestamp')
        param_readings = []
        for row in rows:
            tmp = {}
            for param in parameters:
                clean = param + '-Clean'
                cleanN = param + '-N-Clean'
                cleanvalue = param + '-Cleanvalue'
                measured = param + '-Measured'
                measuredN = param + '-N-Measured'
                result = param + '-Result'
                try:
                    # we have taken clean value,
                    # if clean not available use measured
                    reading = row.get(clean) or row.get(cleanN) or row.get(
                        cleanvalue) or \
                              row.get(measured) or row.get(measuredN) or \
                              row.get(result)
                    if reading:
                        tmp[param] = reading
                    else:
                        break
                    # lets add time and site back to data
                    tmp['timestamp'] = row.get('timestamp')
                    # tmp['site'] = site.site_id
                except Exception as err:
                    log.exception('%s: Format Error %s', self.stn_filename,
                                  err)
            if not (len(tmp) == 1 and 'timestamp' in tmp) and tmp:
                param_readings.append(tmp)
        return param_readings, parameters

    def _max(self):
        with open(self.stn_file, encoding='utf-8') as f:
            reader = csv.reader(f)
            params = []
            param_readings = []
            for idx, row in enumerate(reader):
                if idx == 0:
                    params = row[3:-2:2]
                    params.append('timestamp')
                row = [val.strip() for val in row]
                timestamp = datetime.strptime(
                    row[2] + row[1], '%d/%m/%Y%H:%M:%S').strftime(
                    "%Y-%m-%d %H:%M:%S")
                values = row[4:-2:2]
                readings = [
                    re.match(r"([-]?[0-9.]+)([a-z%]+)", a, re.I).groups()[0]
                    for a in values]
                readings.append(timestamp)
                # readings.append(site.site_id)
                val = dict(zip(params, readings))
                param_readings.append(val)
        if 'timestamp' in params:
            params.remove('timestamp')
        # params.remove('site')
        return param_readings, params

    def _analog(self):
        with open(self.stn_file, encoding='utf-8') as f:
            reader = csv.reader(f)
            params = []
            param_readings = []
            for idx, row in enumerate(reader):
                if idx == 0:
                    params = row[4::2]
                    params.append('timestamp')
                row = [val.strip() for val in row]
                values = row[5::2]
                readings = [
                    re.match(r"([-]?[0-9.]+)([a-z%]+)", a, re.I).groups()[0]
                    for a in values]
                timestamp = datetime.strptime(
                    row[1] + row[2],
                    '%d/%m/%Y%H:%M:%S'
                ).strftime("%Y-%m-%d %H:%M:%S")
                readings.append(timestamp)
                val = dict(zip(params, readings))
                param_readings.append(val)
        if 'timestamp' in params:
            params.remove('timestamp')
        # params.remove('site')
        return param_readings, params

    def _shreetech(self):
        with open(self.stn_file, encoding='utf-8') as f:
            reader = list(csv.reader(f))
            frow = reader[0]
            srow = reader[1]
            lrow = reader[-2] if len(reader[-1]) < 3 else reader[-1]

        prefix, param = frow[-1].split('_')[0], frow[-1].split('_')[-1]
        timestamp = lrow[0]
        param_reading = lrow[1]
        params = ['timestamp', param]
        readings = [timestamp, param_reading]
        try:
            calib_m_factor, calib_c_factor, calib_s_factor, temprature = srow
            calib_val = lrow[5]
            zero, span, drift, status = lrow[8:12]
            params.append('diagnostics')
            readings.append(
                {
                    'param': param,
                    'timestamp': timestamp,
                    'calib_m_factor': calib_m_factor,
                    'calib_c_factor': calib_c_factor,
                    # 'calib_s_factor': calib_s_factor,
                    'calib_val': calib_val,
                    'zero': zero,
                    'span': span,
                    'drift': drift,
                    'status': status,
                    # 'temprature': temprature
                }
            )
        except:
            log.exception('Failed to fetch diagnostics from %s' % self.stn_file)
        param_readings = [dict(zip(params, readings))]
        params.remove('diagnostics')
        if 'timestamp' in params:
            params.remove('timestamp')
        return param_readings, params

    def _sampler(self):
        with open(self.stn_file, encoding='utf-8') as f:
            data = next(f).split(',')

        tmp_dct = {data[i]: data[i + 1] for i in range(0, len(data), 2)}
        # prefix is sampler_id
        sampler_id = tmp_dct.get('ID')

        record = {'readings': {k: self.format_sampler_time(v) for k, v in
                               tmp_dct.items() if str(k).startswith('B')}}
        record.update({'raw': data})

        try:
            site = SamplerIndustry.objects.get(sampler_id=sampler_id)
            sr = SamplerReading.objects.create(
                timestamp=datetime.now(),
                filename=basename(self.stn_filename),
                site=site,
                reading=json.dumps(record),

            )
            sr.save()
            sampler_log.info('Sampler Record Added')
        except SamplerIndustry.DoesNotExist:
            sampler_log.exception(
                'Sampler Industry Doesnt Exists with Sampler ID:%s' % sampler_id)
        except:
            sampler_log.exception('Failed to Save sampler readings')
        return record

    def format_sampler_time(self, timestamp):

        try:
            days, sec = timestamp.split('.')
            sec = float('0.' + sec)
            # logic shared for calculation of time
            minutes = (sec * (10 ** 9)) / (11574 * 60)
            new_date = datetime(1900, 1, 1) + timedelta(
                days=int(days), minutes=minutes)
            return new_date.strftime("%Y-%m-%d %H:%M:%S")
        except:
            sampler_log.exception('Failed to format sampler timestamp')
            return timestamp


# TODO(Sagar): Units are found in file can be used
def scan_param_units(filename):
    with open(filename, encoding='utf-8') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx == 1:
                unit_row = row
                break
    param_units = {}
    if unit_row:
        units = [a for a in unit_row if
                 not a.startswith(('Status', 'Measurement'))]
        for u in units:
            param = u.split()[0]
            m = re.search('\[(.+?)]', u)
            unt = ''
            if m:
                unt = m.group(1)
            param_units[param] = unt
    log.info('SCAN FILE UNTIS:\n%s' % param_units)
    return param_units
