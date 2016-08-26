#!/usr/bin/env python

import time
import os
import sys
import uuid
import platform
import logging

from pgoapi import PGoApi

log = logging.getLogger(__name__)


class Status3Exception(Exception):
    pass

def api_init(config):
    api = PGoApi()
    
    api.set_position(360,360,0)  
    api.set_authentication(provider = config.auth_service, username = config.username, password =  config.password)
    api.activate_signature(get_encryption_lib_path()); api.get_player()

    time.sleep(1)
    response = api.get_inventory()
    
    if response:
        if 'status_code' in response:
            if response['status_code'] == 1 or response['status_code'] == 2:
                return api
            elif response['status_code'] == 3:
                log.error('Account banned!'); return None
            else: return None


def get_response(cell_ids, lat, lng, alt, api, config):
    
    timestamps = [0,] * len(cell_ids)
    response_dict = []
    delay = 11
    
    while True:
        api.set_position(lat, lng, alt)
        response_dict = api.get_map_objects(latitude=lat, longitude=lng, since_timestamp_ms = timestamps, cell_id = cell_ids)
        if response_dict:
            if 'responses' in response_dict:
                if 'status' in response_dict['responses']['GET_MAP_OBJECTS']:
                    if response_dict['responses']['GET_MAP_OBJECTS']['status'] == 1:
                        return response_dict
                    if response_dict['responses']['GET_MAP_OBJECTS']['status'] == 3:
                        log.critical("Account banned!")
                        raise Status3Exception

        time.sleep(delay)
        delay += 5

def get_encryption_lib_path():
    # win32 doesn't mean necessarily 32 bits
    if sys.platform == "win32" or sys.platform == "cygwin":
        if platform.architecture()[0] == '64bit':
            lib_name = "encrypt64bit.dll"
        else:
            lib_name = "encrypt32bit.dll"

    elif sys.platform == "darwin":
        lib_name = "libencrypt-osx-64.so"

    elif os.uname()[4].startswith("arm") and platform.architecture()[0] == '32bit':
        lib_name = "libencrypt-linux-arm-32.so"

    elif os.uname()[4].startswith("aarch64") and platform.architecture()[0] == '64bit':
        lib_name = "libencrypt-linux-arm-64.so"

    elif sys.platform.startswith('linux'):
        if "centos" in platform.platform():
            if platform.architecture()[0] == '64bit':
                lib_name = "libencrypt-centos-x86-64.so"
            else:
                lib_name = "libencrypt-linux-x86-32.so"
        else:
            if platform.architecture()[0] == '64bit':
                lib_name = "libencrypt-linux-x86-64.so"
            else:
                lib_name = "libencrypt-linux-x86-32.so"

    elif sys.platform.startswith('freebsd'):
        lib_name = "libencrypt-freebsd-64.so"

    else:
        err = "Unexpected/unsupported platform '{}'".format(sys.platform)
        log.error(err)
        raise Exception(err)

    lib_path = os.path.join(os.path.dirname(__file__), "../pgoapi/magiclib", lib_name)

    if not os.path.isfile(lib_path):
        err = "Could not find {} encryption library {}".format(sys.platform, lib_path)
        log.error(err)
        raise Exception(err)

    return lib_path

def limit_cells(cells, limit=100):
    return cells[:limit]