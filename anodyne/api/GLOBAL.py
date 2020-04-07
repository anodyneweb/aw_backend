# !/usr/bin/python
# -*- coding: utf-8 -*-
import os

# Parent Directory where all Industry dirs are created and files are saved
BASE_LOCATION = os.path.dirname(os.path.dirname(__file__))

FILES_REPO = os.path.join(BASE_LOCATION, 'MISC_FILES')
# here we keep 'formatted' site files coming from gatekeeper
FILES_BASE_LOCATION = os.path.join(FILES_REPO, 'DATA_FILES')
# zipped metadata + site_file
ZIP_DIR = os.path.join(FILES_REPO, 'ZIP_DIR')
# keep files from database
CSV_FROM_DB = os.path.join(FILES_REPO, 'FILES_FROM_DB')
# path for metadata.csv
METADATA_FILE = os.path.join(FILES_REPO, 'metadata.csv')
# path for stations.csv and industries.csv
STATIONS_CACHE = os.path.join(CSV_FROM_DB, 'stations.csv')
INDUSTRIES_CACHE = os.path.join(CSV_FROM_DB, 'industries.csv')

# Temp folder
TEMP_DIR = os.path.join(FILES_REPO, 'TEMP_DIR')
# pass all directories which needs to be created
VEPOLINK_DIRS = [FILES_BASE_LOCATION, ZIP_DIR, CSV_FROM_DB, TEMP_DIR]

###################################Madhya Pradesh##############################
MPPCB_REALTIME = 'http://esc.mp.gov.in/MPPCBServer/realtimeUpload'
MPPCB_DELAYED = 'http://esc.mp.gov.in/MPPCBServer/DelayedUpload'

###################################Mumbai###################################
MPCB_REALTIME = 'http://onlinecems.ecmpcb.in/mpcb/realtimeUpload'
MPCB_DELAYED = 'http://onlinecems.ecmpcb.in/mpcb/delayedUpload'

###################################KERELA###################################
KSPCB_REALTIME = 'http://keralapcb.glensserver.com/KSPCBGLensServer/realTimeUpload'
KSPCB_DELAYED = 'http://keralapcb.glensserver.com/KSPCBGLensServer/delayedUpload'

###################################CPCB###################################
# TODO: check this
CPCB_REALTIME = 'http://cpcbrtdms.nic.in/v1.0/industry/{industry_id}/data'
CPCB_DELAYED = 'http://cpcbrtdms.nic.in/v1.0/industry/{industry_id}/data'

###################################OSPCB###################################
OSPCB_REALTIME = 'http://117.239.117.27:9091/OSPCBserver/realTimeUpload'
OSPCB_DELAYED = 'http://117.239.117.27:9091/OSPCBserver/delayedUpload'

###################################UKPC###################################
UKPCB_REALTIME = 'http://gangatarang.ilens.io/GangaTarang/LiveData'
UKPCB_DELAYED = 'http://onlinecems.ecmpcb.in/mpcb/delayedUpload'

###################################DPCC###################################
DPCC_REALTIME = 'http://173.208.244.178/dlcpcb'

URLS = [MPCB_REALTIME,
        MPCB_DELAYED,
        KSPCB_REALTIME,
        KSPCB_DELAYED,
        CPCB_REALTIME,
        CPCB_DELAYED,
        OSPCB_REALTIME,
        OSPCB_DELAYED,
        UKPCB_REALTIME,
        UKPCB_DELAYED,
        DPCC_REALTIME,
        MPPCB_REALTIME,
        MPPCB_DELAYED]

UPLOAD_TYPE_CHOICES = (
    ('realtime', 'Realtime'),
    ('delayed', 'Delayed')
)
PERMISSIONS = (
    ('view_site', 'View Site'),
    ('download_report', 'Download Report'),
    ('manage_site', 'Site Management'),
    ('upload_data', 'Upload Data to PCB'),
    ('view_upload_details', 'View Upload Details'),
    ('view_graph', 'View Graph'),
    ('client_management', 'Client Management'),
)
USER_CHOICES = (
    ('CUSTOMER', 'Customer'),
    ('CPCB', 'CPCB'),
    ('ADMIN', 'Super Admin'),
    ('STAFF', 'Staff User'),
)


UNIT = ((None, '-Select Unit-'),
        ('C', 'C',),
        ('%', '%',),
        ('µg/m3', 'µg/m3'),
        ('celsius', 'celsius'),
        ('Deg', 'Deg'),
        ('Hazen-eq.', 'Hazen-eq.'),
        ('hu', 'hu'),
        ('m/sec', 'm/sec'),
        ('m3/h', 'm3/h'),
        ('m3/hr', 'm3/hr'),
        ('mg/Nm3', 'mg/Nm3'),
        ('mm', 'mm'),
        ('mm-Hg', 'mm-Hg'),
        ('NTU', 'NTU'),
        ('ppb', 'ppb'),
        ('units', 'units'),
        ('uS/cm', 'uS/cm'),
        ('w/m2', 'w/m2'),
        ('mld', 'mld'),
        ('mlu', 'mlu'),
        ('l/h', 'l/h'),
        ('kg/hr', 'kg/hr'),
        ('myUnit1', 'myUnit1'),
        ('I/hr', 'I/hr'),
        ('m', 'm'),
        ('m3/s', 'm3/s'),
        ('ppm', 'ppm'),)

HTML_COLOR = [
    '#808080',
    '#000000',
    '#FF0000',
    '#800000',
    '#FFFF00',
    '#808000',
    '#00FF00',
    '#008000',
    '#00FFFF',
    '#008080',
    '#0000FF',
    '#000080',
    '#FF00FF',
    '#800080',
    '#DB7093',
    '#B0E0E6',
    '#800080',
    '#663399',
    '#4169E1',
    '#00FF7F',
    '#4682B4',
    '#008080',
    '#2E8B57',
    '#A52A2A',
]

PCB_API_ERRORS = {
    'ERROR 1001': 'Issues or missing header Timestamp.',
    'ERROR 1002': 'Issues or missing header Authorization.',
    'ERROR E_1003': 'Issues or missing header site Id',
    'ERROR 1004': 'Missing headers',
    'ERROR 1005': 'Invalid Request, Request Format',
    'ERROR 1007': 'Invalid Request, Request Format',
    'ERROR 1008': 'Invalid Request, Request Format',
    'ERROR 1006 TYPE1': 'Invalid Site Details, Header Information Missing',
    'ERROR 1006 TYPE2': 'Error in Encryption. Missing fields in header',
    'ERROR 1006 TYPE3': 'Site ID Mismatch in Header',
    'ERROR 1006 TYPE4': 'Timestamp Mismatch in Header',
    'ERROR 1006 TYPE5': 'Software Version Mismatch in Header',
    'ERROR 1006 TYPE6': 'Timestamp not within the Required Timeframe, '
                        '(Either Filestamps are of future date or Timestamp '
                        'in header is incorrect)',
    'ERROR 1006 TYPE7': 'Invalid Details in Request. Error in Encryption'
}

MPCB_METADATA = ['SITE_ID', 'SITE_UID', 'MONITORING_UNIT_ID', 'ANALYZER_ID',
                 'PARAMETER_ID', 'PARAMETER_NAME', 'READING', 'UNIT_ID',
                 'DATA_QUALITY_CODE', 'RAW_READING', 'UNIX_TIMESTAMP',
                 'CALIBRATION_FLAG', 'MAINTENANCE_FLAG']

REPORT_TYPE = (
    ('LODR', 'Live Offline Delay Report'),
    ('LOR', 'Latest Offline Report'),
    ('INDUSTRIES', 'Industries Added Report'),
    ('MBR', 'Monthly Backup Report'),
    ('SMSR', 'SMS Report'),
    ('SDR', 'Station Data Report'),
    ('CPCBAR', 'CPCB Alarm Report'),
    ('SHR', 'Station Halt Report'),
    ('DR', 'Distillery Report'),
    ('CRPR', 'CRP Report'),
)

ISO_CODES = {'PM': '22/23', 'pH': '50', 'NOx': '35', 'PM10': '24',
             'PM2.5': '39', 'O3': '8', 'SO2': '1', 'CO': '4',
             'NO2': '3',
             'IR Radiation': '71', 'UV Radiation': '72',
             'Humidity': '58',
             'Rain': 'G6', 'Flow': 'G5', 'SOx': '10',
             'Temperature': '54',
             'Wind Speed': '51', 'Wind Direction': '52',
             'Hydrogen Chloride': '7', 'HF': '6', 'Pressure': '53',
             'TSS': 'G1', 'BOD': 'G3', 'COD': 'G2', 'TDS': 'G7',
             'Totalizer Flow': 'D1', 'CS2': 'D2', 'Opacity': 'D3',
             'VOC': 'D4',
             'Effluent (Temperature)': 'G4', 'CO2': '17',
             'Primay_Temp': 'D5',
             'Seconday_Temp': 'D6'}
