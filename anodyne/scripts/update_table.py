#!/usr/bin/python3
"""
Task of this watchdog is to only keep track in any new file has come to the
server this will intimate application about new files for processing.
This file will run as independent entity.
"""
import logging
import os
import sys
import threading
from multiprocessing import Process
from os.path import basename
import django
import inotify.adapters
from inotify.constants import *
FTP_BASE = os.environ.get('FTP_PATH', '/var/www/ftp_home/')
#  you have to set the correct path to you settings module
# TODO: to enable this host django app properly on server
PROJ_PATH = "/home/ubuntu/aw_backend/anodyne"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "anodyne.settings")
sys.path.append(PROJ_PATH)
django.setup()
from api.models import Station, StationInfo


def update_status():
    # script to update Status of Station
    stations = StationInfo.objects.filter(status='Live')
    live_stations = stations.filter()

