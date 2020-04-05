import base64
import csv
import json
import logging
import os
import re
import sys
import zipfile
from datetime import datetime, timedelta

import pandas as pd
import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_v1_5_signature

from api.GLOBAL import ISO_CODES, ZIP_DIR

from api.models import StationParameter, Parameter, Station

log = logging.getLogger('vepolink')
# MPPCB_REALTIME = 'http://esc.mp.gov.in/MPPCBServer/realtimeUpload'
MPPCB_SVER_PEM = "-----BEGIN RSA PUBLIC KEY-----\nMEgCQQDfrM65tIZkhGRqoE5mGNIP+bWsIY26idnEftR1r2r4aSFPyUNIr84WuCjl\no09oyKXdtkDCNuzRDKaeP9zIoIvVAgMBAAE=\n-----END RSA PUBLIC KEY-----\n"


class Handle:
    def __init__(self, **kwargs):
        try:
            from Crypto.Random import atfork
            atfork()
        except:
            # pycrypto versions that have no "Random" module also do not
            # detect the missing atfork() call, so they do not raise.
            pass
        self.basename = kwargs.get('basename')
        self.site = Station.objects.get(prefix=kwargs.get('prefix'))
        self.kwargs = kwargs
        self.BLOCK_SIZE = 16
        self.KEY_SIZE = 16
        self.PADDING = '#'
        self.IV = 16 * '\x00'

    def _pad(self, key=None, data=None):
        if key:
            return key + (self.KEY_SIZE - len(
                data) % self.BLOCK_SIZE) * self.PADDING
        if data:
            return data + (self.BLOCK_SIZE - len(
                data) % self.BLOCK_SIZE) * self.PADDING

    # TODO(sagar): key_encrypt and key_decrypt are part of signature not in use
    def key_encrypt(self, key):
        return self._pad(key=base64.b64encode(key))

    def key_decrypt(self, key):
        return base64.b64decode(key)

    def encrypt(self, key, data):
        cipher = AES.new(self._pad(key, data)[:32], AES.MODE_CBC, IV=self.IV)
        encrypted = base64.b64encode(cipher.encrypt(self._pad(data=data)))
        if sys.version_info[0] <= 3:
            encrypted = encrypted.decode('utf-8')
        return encrypted

    def decrypt(self, key, data):
        cipher = AES.new(self._pad(key, data)[:32], AES.MODE_CBC, IV=self.IV)
        decrypted = cipher.decrypt(base64.b64decode(data))
        if sys.version_info[0] <= 3:
            decrypted = decrypted.decode('utf-8').rstrip(self.PADDING)
        return decrypted.rstrip(self.PADDING)

    def get_headers(self):
        data_enc_tstamp = datetime.now() - timedelta(minutes=0)
        # utils2.format_timestamp to be used below
        data_enc_tstamp = data_enc_tstamp.strftime(
            '%Y-%m-%dT%H:%M:%SZ')  # time wen data was encrypted
        authz = '^'.join([self.site.site_id, 'ver1.0', data_enc_tstamp])

        # MPPCB_SVER_PEM = "-----BEGIN RSA PUBLIC KEY-----\nMEgCQQDfrM65tIZkhGRqoE5mGNIP+bWsIY26idnEftR1r2r4aSFPyUNIr84WuCjl\no09oyKXdtkDCNuzRDKaeP9zIoIvVAgMBAAE=\n-----END RSA PUBLIC KEY-----\n"
        ################ HEADER ENCRYPTION ################
        # MPPCB_SVER_PEM = RSA.importKey(MPPCB_SVER_PEM)
        # cipher = PKCS1_v1_5.new(MPPCB_SVER_PEM)
        MPPCB_SVER_PEM = RSA.importKey(self.site.pub_key.replace('\\n', '\n'))
        cipher = PKCS1_v1_5.new(MPPCB_SVER_PEM)
        ciphertext = cipher.encrypt(authz.encode())
        authorization = base64.b64encode(ciphertext).decode()
        ####################################################

        ############## RSA Signature Generation ############
        digest = SHA256.new()
        digest.update(authz.encode())
        SITE_PVT_PPK = RSA.importKey(self.site.pvt_key.replace('\\n', '\n'))
        signer = PKCS1_v1_5_signature.new(SITE_PVT_PPK)
        signature = signer.sign(digest)
        signature = base64.b64encode(signature).decode()
        ####################################################
        TSTAMP = datetime.now()  # time wen data is uploaded
        tstamp = TSTAMP.strftime('%Y-%m-%dT%H:%M:%SZ')

        headers = {
            'Timestamp': tstamp,
            'siteId': self.site.site_id,
            "Authorization": "BASIC %s" % authorization,
            "Signature": signature,
        }
        return headers

    def _param_units(self):
        unit_row = []
        with open(self.kwargs.get('filename'), encoding='utf-8') as f:
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
                    if not unt:
                        try:
                            p = Parameter.objects.get(parameter=param.lower())
                            unt = p.unit or ''
                            if not unt:
                                log.warning(
                                    'MPPCB: Unit for %s not available' % param)
                                unt = ''
                        except Parameter.DoesNotExist:
                            log.warning(
                                'MPPCB: Unit for %s not available' % param)
                # if param.lower() == 'ph':
                #     unt = 'units'
                param_units[param] = unt
        return param_units

    def _iso_format(self):
        zip_name = self.site.site_id
        readings = self.kwargs.get('readings')
        params = self.kwargs.get('orig_params')
        # PARAM_UNIT = self._param_units()
        df = pd.DataFrame(readings)
        df = df.dropna()
        df = df.sort_values(
            by='timestamp')  # we need only latest timestamp only

        string3 = """"""
        string2 = """"""
        cnt = 0
        txt_site_id = str(self.site.site_id).split('_')[-1]
        for idx, row in df.iterrows():
            for param in params:
                try:
                    param_val = row[str(param).lower()]
                    if param_val is 'NaN':
                        continue
                except KeyError:
                    log.info('Failing MPPCB KEY Error:%s ' % param)
                    log.info('Failing MPPCB KEY Error:%s ' % row)
                    continue
                # print(param, j[param], j.timestamp)
                try:
                    site_param = StationParameter.objects.get(site=self.site,
                                                              parameter_name=str(
                                                                  param).lower(),
                                                              )
                    if not site_param.allowed:
                        log.info(
                            'MPPCB Upload Parameter:%s not allowed for %s' % (
                                param, self.site))
                        continue

                    if param.lower().startswith('spm'):
                        param = 'pm'

                    if not ISO_CODES.get(param.upper()):
                        log.error('MPPCB ISO Code not found for:%s (%s)' %
                                  (param, self.basename))
                        continue
                    else:
                        iso_code = ISO_CODES.get(param.upper())

                    zip_name = '%s_%s' % (
                        self.site.site_id, site_param.monitoring_id)

                    string2 += """\n1{param_code_from_iso}1{param} {param_unit} {analyser_id} 3 {threshold_min} {threshold_max}\n{site_id} {monitoring_id} {latitude}    {longitude}""".format(
                        param_code_from_iso=iso_code,
                        param=str(param).upper(),
                        param_unit=site_param.unit,
                        analyser_id=site_param.analyzer_id,
                        # count_of_params='{cnt}',
                        count_of_params=3,
                        # threshold_min=site_param.minimum or 0,
                        # threshold_max=site_param.maximum or 0,
                        threshold_min=0,
                        threshold_max=0,
                        monitoring_id=site_param.monitoring_id,
                        site_id=txt_site_id,
                        latitude=str(self.site.latitude),
                        longitude=str(self.site.longitude)
                    )
                    string3 += """\n1{param_code_from_iso}1{site_id} 119 7261836 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1   1   0    1\n{data_qcode} {reading}""".format(
                        param_code_from_iso=iso_code,
                        site_id=txt_site_id,
                        param=param,
                        data_qcode='U',
                        reading=param_val)
                    cnt += 1
                except StationParameter.DoesNotExist:
                    log.info(
                        'MPPCB Upload Parameter:%s doesnt exists for %s' % (
                            param, self.site))
                    continue
            break  # we need only latest timestamp row

        string1 = """{industry_name}\n{city}\n{state}\nIndia\n{count_of_params} {count_of_params}""".format(
            industry_name=self.site.industry.name,
            industry_addr=self.site.address,
            city=self.site.city,
            state=self.site.state,
            count_of_params=cnt
        )

        iso_file_content = string1 + string2.format(cnt=cnt) + string3
        log.info('MPPCB format for %s:\n%s' % (self.basename,
                                               iso_file_content))
        return iso_file_content, zip_name

    def encrypt_and_zip(self, content, zip_name):
        """
        encrypt and zip iso formatted data
        :param content:
        :return:
        """
        file_tstamp = (datetime.now() - timedelta(minutes=4)).strftime(
            '%Y%m%d%H%M%S')
        fname = self.kwargs.get('filename')
        dtf = fname.replace(fname.split('_')[-1], file_tstamp + '.dat')
        # log.info('MPPCB Plain Content %s:\n%s' % (fname, content))
        encrypted_file_content = self.encrypt(self.site.key, content)
        with open(dtf, 'w') as wfile:
            # writing encrypted content to .dat file
            wfile.write(encrypted_file_content)

        # log.info('MPPCB Encrypted Content %s:\n%s' % (dtf, encrypted_file_content))
        # _fnm = '%s_%s_' % (self.site.site_id,
        file_name = os.path.join(ZIP_DIR, '%s_%s.zip' % (zip_name, file_tstamp)
                                 )
        with zipfile.ZipFile(file_name, mode='w',
                             compression=zipfile.ZIP_DEFLATED) as zipObj:
            # zipping encrypted .dat file
            zipObj.write(dtf, os.path.basename(dtf))
        try:
            os.remove(dtf)
        except:
            pass
        log.info('MPPCB zipped file:%s' % file_name)
        return file_name

    def upload(self):
        # TO upload we need to format station file as per ISO-7168
        log.info('%s: Initiating upload' % self.basename)
        format_data2iso, zip_name = self._iso_format()
        headers = self.get_headers()
        log.info('MPPCB Headers:\n%s\nISO_Format:%s\n'
                 'Key:\n%s\nPUB_KEY:\n%s\nPVT_KEY:\n%s' % (
                     headers, format_data2iso, self.site.key,
                     self.site.pub_key, self.site.pvt_key)
                 )
        file_name = self.encrypt_and_zip(format_data2iso, zip_name)
        with open(file_name, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                self.site.realtime_url,
                headers=headers,
                files=files
            )
        try:
            log.info('MPPCB UPLOAD Status %s:\n%s' % (
                self.kwargs.get('stn_filename'),
                response.json()))
            response = response.json()
            return response
        except json.decoder.JSONDecodeError:
            log.error('Failed to MPPCB upload: %s' % response)
            response = {'to_pcb': {'status': 'failed',
                                   'message': 'Failed to upload: %s' % self.kwargs.get(
                                       'stn_filename'),
                                   'url': self.site.realtime_url
                                   }
                        }
        return response
