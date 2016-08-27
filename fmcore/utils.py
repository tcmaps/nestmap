#!/usr/bin/env python

import math
import logging

from geopy.geocoders import GoogleV3
from geographiclib.geodesic import Geodesic
from s2sphere import CellId, Angle, LatLng, LatLngRect, Cap, RegionCoverer

log = logging.getLogger(__name__)


class PoGoAccount():
    def __init__(self, auth, login, passw):
        self.auth_service = auth
        self.username = login
        self.password = passw

def set_bit(value, bit):
    return value | (1<<bit)

def get_pos_by_name(location_name):
    geolocator = GoogleV3()
    loc = geolocator.geocode(location_name)
    if not loc:
        return None
    return (loc.latitude, loc.longitude, loc.altitude)

def get_pokenames(filename):
    plist = []
    f = open(filename,'r')
    for l in f.readlines():
        plist.append(l.strip())
    return plist

def get_accounts(filename):
    accs = []
    f = open(filename,'r')
    for l in f.readlines():
        acc = (l.strip().split(':'))
        accs.append(PoGoAccount('ptc',acc[0],acc[1]))
    return accs

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

def sub_cells_normalized(cell, level=15):
    cells = [cell]

    for dummy in range(level-cell.level()):
        loopcells = cells; cells = []
        for loopcell in loopcells:
            for subcell in sub_cells(loopcell):
                cells.append(subcell)

    return sorted(cells)

def get_cell_ids(cells):
    cell_ids = sorted([x.id() for x in cells])
    return cell_ids

def cover_circle(lat, lng, radius, level=15):
    EARTH = 6371000
    region = Cap.from_axis_angle(\
             LatLng.from_degrees(lat, lng).to_point(), \
             Angle.from_degrees(360*radius/(2*math.pi*EARTH)))
    coverer = RegionCoverer()
    coverer.min_level = level
    coverer.max_level = level
    cells = coverer.get_covering(region)
    return cells

def cover_square(lat, lng, width, level=15):
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

def get_cell_walk(lat, lng, radius, level=15):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, lng)).parent(level)
    walk = [origin]
    right = origin.next()
    left = origin.prev()
    for dummy in range(radius):
        walk.append(right)
        walk.append(left)
        right = right.next()
        left = left.prev()
    return sorted(walk)

class cell_neighbor:
    def __init__(self, cell):
        self.cell = cell
    def north(self):
        return self.cell.get_edge_neighbors()[0]
    def east(self):
        return self.cell.get_edge_neighbors()[3]
    def south(self):
        return self.cell.get_edge_neighbors()[2]
    def west(self):
        return self.cell.get_edge_neighbors()[1]