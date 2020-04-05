#!/usr/bin/python3
"""
Task of this watchdog is to only keep track in any new file has come to the
server this will intimate application about new files for processing.
This file will run as independent entity.
"""
import logging
import os
import threading
from multiprocessing import Process
from os.path import basename

# coding: utf-8
import inotify.adapters
from inotify.constants import *

from anodyne.connectors import connector

FTP_BASE = os.environ.get('FTP_PATH', '/var/www/ftp_home/')

logging.basicConfig(filename='/var/log/anodyne/reception.log',
                    level=logging.DEBUG)
import os


#  you have to set the correct path to you settings module
# TODO: to enable this host django app properly on server

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "anodyne.settings")
# PROJ_PATH = "/home/aw_backend/anodyne/anodyne"
# sys.path.append(PROJ_PATH)
# django.setup()


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
            logging.debug(
                "\nFilename:%s\nLENGTH:%d\nTYPE:%s\n" % (filename,
                                                         header.len,
                                                         type_names)
            )
            if 'IN_CLOSE_WRITE' in type_names and filename.endswith('.csv'):
                loc = os.path.join(FTP_BASE, filename)
                thread = threading.Thread(target=process, args=(loc,))
                thread.start()
                thread.join(60)


def process(f):
    """
    picks file from check4file queue and processes it further...
    """
    try:
        logging.debug('Received: %s' % basename(f))
        start = connector.ReadCSV(f)
        details = start.process()
        logging.info('%s:%s' % (basename(f), details))
    except Exception as error:
        if type(error).__name__ == 'ConnectionError':
            logging.debug('%s: Server not responding...', basename(f))
        elif type(error).__name__ == 'ReadTimeout':
            logging.debug('%s: Server took too long to respond.',
                          basename(f))
        else:
            logging.debug("ERROR: %s\n"
                          "Reason: %s", basename(f), error)
        logging.debug('%s: %s', basename(f), error)


def prerequisite():
    logging.debug('_______ SERVER RESTARTING _______')
    if not os.path.exists(FTP_BASE):
        os.mkdir(FTP_BASE)


def main():
    # prerequisite()
    # TODO: Too much delay to reach here from FTP (ftp writing slow)
    p = Process(target=check4file, daemon=True)
    p.start()
    p.join()


if __name__ == '__main__':
    main()
