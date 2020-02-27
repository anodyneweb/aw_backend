#!/usr/bin/python3
"""
Task of this watchdog is to only keep track in any new file has come to the
server this will intimate application about new files for processing.
This file will run as independent entity.
"""
import logging
import os
import shutil
import sys
from multiprocessing import Queue, Process
from datetime import date
from os.path import basename
import json
# coding: utf-8
import django
import inotify.adapters
from inotify.constants import *
from rest_framework import status
import threading

# from anodyne.fileformatter import GenFile4PCB

PROJ_PATH = "/var/www/apps/anodyne"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "anodyne.settings")
sys.path.append(PROJ_PATH)
django.setup()
# from anodyne import tasks, celerytasks
# Setup Gatekeeper to use anodyne django environment
# from anodyne import formatter

# Logging format to follow for this is FILENAME: LOG MESSAGE
reception_log = logging.getLogger('reception')
log = logging.getLogger('anodyne')


# API_URL = 'http://' + os.environ.get('APP_URL', 'localhost') + '/reception'
# USERNAME = os.environ.get('HEIMDALL_USERNAME', 'test')
# PASSWORD = os.environ.get('HEIMDALL_PASSWD', 't3$t')
FTP_BASE = os.environ.get('GATEKEEPER_PATH', '/var/www/ftp_home/')
tday = date.today().strftime('%d%b%Y')
TODAYS_BASE = os.path.join(FTP_BASE, tday)


def check4file():
    """
    Keeps an eye on gatekeeper directory for every entry of file and puts it
    in a queue.

    """
    i = inotify.adapters.Inotify()
    i.add_watch(FTP_BASE, mask=(IN_OPEN | IN_CLOSE_WRITE))
    # IN_OPEN -> IN_MODIFY (this will repeat untill it ends writing -> IN_CLOSE_WRITE

    for event in i.event_gen():
        if event is not None:
            (header, type_names, watch_path, filename) = event
            reception_log.info("\nFilename:%s\nLENGTH:%d\nTYPE:%s\n" % (filename,
                                                                   header.len,
                                                                   type_names)
                          )
            # reception_log.info("WD=(%d) MASK=(%d) COOKIE=(%d) LEN=(%d)
            # MASK->NAMES=%s WATCH-PATH=[%s] FILENAME=[%s]" % ( header.wd,
            # header.mask, header.cookie, header.len, type_names,
            # watch_path, filename))
            if 'IN_CLOSE_WRITE' in type_names and filename.endswith('.csv'):
                loc = os.path.join(FTP_BASE, filename)
                # new_loc = os.path.join(TODAYS_BASE, filename)
                # try:
                #     shutil.move(old_loc, new_loc)
                #     dest = new_loc
                # except:
                #     dest = old_loc
                thread = threading.Thread(target=process, args=(loc,))
                thread.start()
                thread.join(60)


def process(f):
    """
    picks file from check4file queue and processes it further...
    """
    try:
        reception_log.info('Received: %s' % basename(f))
        # g = GenFile4PCB(f)
        # g.initiate()
    except Exception as error:
        if type(error).__name__ == 'ConnectionError':
            log.error('%s: Server not responding...', basename(f))
        elif type(error).__name__ == 'ReadTimeout':
            log.error('%s: Server took too long to respond.',
                      basename(f))
        else:
            log.error("ERROR: %s\n"
                      "Reason: %s", basename(f), error)
        log.exception('%s: %s', basename(f), error)


def prerequisite():
    reception_log.debug('_______ SERVER RESTARTING _______')
    log.debug('_______ SERVER RESTARTING _______')
    if not os.path.exists(FTP_BASE):
        os.mkdir(FTP_BASE)
    if not os.path.exists(TODAYS_BASE):
        os.mkdir(TODAYS_BASE)


def main():
    prerequisite()
    # TODO: Too much delay to reach here from FTP (ftp writing slow)
    p = Process(target=check4file, daemon=True)
    p.start()
    p.join()


if __name__ == '__main__':
    main()
