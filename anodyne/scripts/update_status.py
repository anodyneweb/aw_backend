#!/usr/bin/python3
"""
Task of this watchdog is to only keep track in any new file has come to the
server this will intimate application about new files for processing.
This file will run as independent entity.
"""
import argparse
import os
import sys

import django

FTP_BASE = os.environ.get('FTP_PATH', '/var/www/ftp_home/')
#  you have to set the correct path to you settings module
# TODO: to enable this host django app properly on server
PROJ_PATH = "/home/ubuntu/aw_backend/anodyne"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "anodyne.settings")
sys.path.append(PROJ_PATH)
django.setup()

from api.models import Station, Industry
from datetime import datetime, timedelta
import pandas as pd
import logging

log = logging.getLogger('vepolink')


# 0 0,2,4,6,8,10,12,14,16,18,20,22 * * * sudo python3 /home/ubuntu/aw_backend/anodyne/scripts/check_exceedance.py
# Runs every 2nd hour
def update_status():
    log.info('Updating Industry and Station Status')
    live_threshold = datetime.now() - timedelta(hours=4)
    delay_threshold = datetime.now() - timedelta(hours=48)

    live_stations = Station.objects.filter(
        stationinfo__last_seen__gte=live_threshold,
        status__in=['Offline', 'Delay'])

    offline_stations = Station.objects.filter(
        stationinfo__last_seen__lt=delay_threshold,
        status__in=['Live', 'Delay'])
    delay_stations = Station.objects.filter(
        stationinfo__last_seen__gte=delay_threshold,
        stationinfo__last_seen__lt=live_threshold,
        status__in=['Live', 'Offline']
    )
    delayed_stations_cnt = delay_stations.count()
    offline_stations_cnt = offline_stations.count()
    live_stations_cnt = live_stations.count()

    if delayed_stations_cnt > 0:
        log.info('Updating %s Station Delay' % delayed_stations_cnt)
        delay_stations.update(status='Delay')

    if offline_stations_cnt > 0:
        log.info('Updating %s Station offline' % offline_stations_cnt)
        offline_stations.update(status='Offline')

    if live_stations_cnt > 0:
        log.info('Updating %s Station Live' % live_stations_cnt)
        live_stations.update(status='Live')

    # industry update
    industries = Industry.objects.all().values('uuid', 'station__status')
    df = pd.DataFrame(industries)
    records = df.groupby('uuid').station__status.apply(list).to_dict()
    live_industries = []
    offline_industries = []
    delay_industries = []
    for industry, curr_status in records.items():
        if 'Live' in curr_status:
            live_industries.append(industry)
        elif 'Delay' in curr_status:
            delay_industries.append(industry)
        else:
            offline_industries.append(industry)
    lv_industry = Industry.objects.filter(uuid__in=live_industries,
                                          status__in=['Delay', 'Offline'])
    off_industry = Industry.objects.filter(uuid__in=offline_industries,
                                           status__in=['Delay', 'Live'])
    dl_industry = Industry.objects.filter(uuid__in=delay_industries,
                                          status__in=['Live', 'Offline'])

    delayed_industry_cnt = dl_industry.count()
    offline_industry_cnt = off_industry.count()
    live_industry_cnt = lv_industry.count()
    if delayed_industry_cnt > 0:
        log.info('Updating %s Industry to Delay' % delayed_stations_cnt)
        dl_industry.update(status='Delay')
    if offline_industry_cnt > 0:
        log.info('Updating %s Industry to Offline' % offline_stations_cnt)
        off_industry.update(status='Offline')
    if live_industry_cnt > 0:
        log.info('Updating %s Industry to Live' % live_stations_cnt)
        lv_industry.update(status='Live')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update Status')
    update_status()
