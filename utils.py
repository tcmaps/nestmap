#!/usr/bin/env python

import sqlite3
import math
import time
import os
import sys
import uuid
import platform
import logging

from pgoapi import PGoApi
from geopy.geocoders import GoogleV3
from geographiclib.geodesic import Geodesic
from s2sphere import CellId, Angle, LatLng, LatLngRect, Cap, RegionCoverer

log = logging.getLogger(__name__)

# TC's stuff
class Status3Exception(Exception):
    pass

def check_db(dbfile='db.sqlite'):
    
    if not os.path.isfile(dbfile):
        if os.name =='nt':
            os.system('copy temp.db ' + dbfile)
        elif os.name =='posix':
            os.system('cp temp.db ' + dbfile)
    
    db = sqlite3.connect(dbfile)
    version = db.cursor().execute("SELECT version FROM '_config'").fetchone()
    
    return version[0]

def init_db(cells, dbfilename):
    db = sqlite3.connect(dbfilename)
    counter=0    
    for cell in cells:
        db.cursor().execute("INSERT OR IGNORE INTO _queue (cell_id,cell_level) "
                            "VALUES ('{}',{})".format(cell.to_token(),cell.level()))
        counter+=1
    db.commit()
    return counter

def api_init(config):
    api = PGoApi()
    
    api.set_position(360,360,0)  
    api.set_authentication(provider = config.auth_service, username = config.username, password =  config.password)
    api.activate_signature(get_encryption_lib_path())
    api.get_player()
    time.sleep(1)
    response = api.get_inventory()
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
        if 'status' in response_dict['responses']['GET_MAP_OBJECTS']:
            if response_dict['responses']['GET_MAP_OBJECTS']['status'] == 1:
                return response_dict
            if response_dict['responses']['GET_MAP_OBJECTS']['status'] == 3:
                print "Account banned!"
                raise Status3Exception

        time.sleep(delay)
        delay += 5


def set_bit(value, bit):
    return value | (1<<bit)

def cover_square(lat, lng, width, level):
    
    offset = int(width / 2)
    g = Geodesic.WGS84
    r = RegionCoverer()
    r.min_level, r.min_level = level, level
    g1 = g.Direct(lat, lng, 360, offset)
    g1 = g.Direct(g1['lat2'],g1['lon2'],270,offset)
    p1 = LatLng.from_degrees(g1['lat2'],g1['lon2'])
    g2 = g.Direct(lat, lng, 180, offset)
    g2 = g.Direct(g2['lat2'],g2['lon2'], 90,offset)
    p2 = LatLng.from_degrees(g2['lat2'],g2['lon2'])
    cells = r.get_covering(LatLngRect.from_point_pair(p1, p2))
    
    return cells

def sub_cells(cell):
    cells = []
    for i in range(4):
        cells.append(cell.child(i))    
    return sorted(cells)

def susub_cells(cell):
    cells = []
    for subcell in sub_cells(cell):
        for susubcell in sub_cells(subcell):
            cells.append(susubcell)    
    return sorted(cells)

def get_pokenames(filename):
    plist = []
    f = open(filename,'r')
    for l in f.readlines():
        plist.append(l.strip())
    return plist

def get_watchlist(filename):
    wlist = []
    f = open(filename,'r')
    for l in f.readlines():
        wlist.append(int(l.strip()))
    return wlist

def north(cell):
    return cell.get_edge_neighbors()[0]
def east(cell):
    return cell.get_edge_neighbors()[3]
def south(cell):
    return cell.get_edge_neighbors()[2]
def west(cell):
    return cell.get_edge_neighbors()[1]

# tejado's stuff
def get_pos_by_name(location_name):
    geolocator = GoogleV3()
    loc = geolocator.geocode(location_name)
    if not loc:
        return None

    return (loc.latitude, loc.longitude, loc.altitude)

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

    lib_path = os.path.join(os.path.dirname(__file__), "magiclib", lib_name)

    if not os.path.isfile(lib_path):
        err = "Could not find {} encryption library {}".format(sys.platform, lib_path)
        log.error(err)
        raise Exception(err)

    return lib_path

def get_cell_ids(lat, lng, radius, level=15):
    # Max values allowed by server according to this comment:
    # https://github.com/AeonLucid/POGOProtos/issues/83#issuecomment-235612285
    if radius > 1500: radius = 1500  # radius = 1500 is max allowed by the server
    cells = cover_circle(lat, lng, radius, level)
    cell_ids = sorted([x.id() for x in cells])
    return cell_ids[:100]

def cover_circle(lat, lng, radius, level):
    EARTH_RADIUS = 6371 * 1000
    region = Cap.from_axis_angle(LatLng.from_degrees(lat, lng).to_point(), \
                                 Angle.from_degrees(360*radius/(2*math.pi*EARTH_RADIUS)))
    coverer = RegionCoverer()
    coverer.min_level = level
    coverer.max_level = level
    cells = coverer.get_covering(region)
    return cells

def get_cell_walk(lat, lng, radius):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, lng)).parent(15)
    walk = [origin]
    right = origin.next()
    left = origin.prev()

    # Search around provided radius
    for i in range(radius):
        walk.append(right)
        walk.append(left)
        right = right.next()
        left = left.prev()

    # Return everything
    return sorted(walk)