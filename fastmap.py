#!/usr/bin/env python
VERSION = '2.1'

"""
based on: pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
        TC    <reddit.com/u/Tr4sHCr4fT>
"""

import os
import sys
import time
import json
import argparse
import sqlite3
import logging

from s2sphere import CellId, LatLng
from pgoapi.exceptions import NotLoggedInException
from utils import api_init, get_response, susub_cells, get_cell_ids
from utils import check_db, init_db, set_bit, cover_circle, cover_square

log = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

def init_config():
    parser = argparse.ArgumentParser()     
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')

    load   = {}
    config_file = "config.json"
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')", default="ptc")
    parser.add_argument("-u", "--username", help="Username")
    parser.add_argument("-p", "--password", help="Password")
    parser.add_argument("-l", "--location", help="Location")
    parser.add_argument("-r", "--radius", help="area circle radius", type=int)
    parser.add_argument("-w", "--width", help="area square width", type=int)
    parser.add_argument("-f", "--dbfile", help="DB filename", default='db.sqlite')
    parser.add_argument("--level", help="cell level used for tiling", default=13, type=int)
    parser.add_argument("-t", "--delay", help="rpc request interval", default=10, type=int)
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true', default=0)
    parser.add_argument("-n", "--test", help="Beta algorithm", action='store_true', default=0)        
    config = parser.parse_args()

    for key in config.__dict__:
        if key in load and config.__dict__[key] == None:
            config.__dict__[key] = load[key]

    if config.auth_service not in ['ptc', 'google']:
        log.error("Invalid Auth service specified! ('ptc' or 'google')")
        return None

    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)
    else:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("pgoapi").setLevel(logging.WARNING)
        logging.getLogger("rpc_api").setLevel(logging.WARNING)
   
    dbversion = check_db(config.dbfile)     
    if dbversion != VERSION:
        log.error('Database version mismatch! Expected {}, got {}...'.format(VERSION,dbversion))
        return
    
    if config.location:
        from utils import get_pos_by_name
        lat, lng, alt = get_pos_by_name(config.location); del alt
        if config.radius:
            cells = cover_circle(lat, lng, config.radius, config.level)
        elif config.width:
            cells = cover_square(lat, lng, config.width, config.level)
        else: log.error('Area size not given!'); return
        log.info('Added %d cells to scan queue.' % init_db(cells, config.dbfile))
        del cells, lat, lng
    
    return config

def main():
    
    config = init_config()
    if not config:
        log.error('Configuration Error!'); return
        
    db = sqlite3.connect(config.dbfile)
    db_cur = db.cursor()
    db_cur.execute("SELECT cell_id FROM '_queue' WHERE cell_level = %d ORDER BY cell_id" % config.level)
    _tstats = [0, 0, 0, 0]
    
    scan_queque = [x[0] for x in db_cur.fetchall()]
    # http://stackoverflow.com/questions/3614277/how-to-strip-from-python-pyodbc-sql-returns 
    if len(scan_queque) == 0: log.info('Nothing to scan!'); return
       
    api = api_init(config)
    if api == None:   
        log.error('Login failed!'); return
    else:
        log.info('API online! Scan starts in 5sec...')
    time.sleep(5)
            
    for que in scan_queque:    
                
        cell_ids = []
        _content = 0
        _tstats[0] += 1
        _cstats = [0, 0, 0]
        
        log.info('Scan {} of {}.'.format(_tstats[0],(len(scan_queque))))
        
        cell = CellId.from_token(que)
        _ll = CellId.to_lat_lng(cell)
        lat, lng, alt = _ll.lat().degrees, _ll.lng().degrees, 0
        
        if config.test:
            cell_ids = get_cell_ids(lat, lng, 1500)
        else:
            cells = susub_cells(cell)
            cell_ids = sorted([x.id() for x in cells])
        
        try:
            response_dict = get_response(cell_ids, lat, lng, alt, api,config)
        except NotLoggedInException:
            del api; api = api_init(config)
            response_dict = get_response(cell_ids, lat, lng, alt, api,config)  
                
        for _map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:
            _cell = CellId(_map_cell['s2_cell_id']).to_token()                        

            if 'forts' in _map_cell:
                for _frt in _map_cell['forts']:
                    if 'gym_points' in _frt:
                        _cstats[0]+=1
                        _type = 0
                        _content = set_bit(_content, 2)
                        db_cur.execute("INSERT OR IGNORE INTO forts (fort_id, cell_id, pos_lat, pos_lng, fort_enabled, fort_type, last_scan) "
                        "VALUES ('{}','{}',{},{},{},{},{})".format(_frt['id'],_cell,_frt['latitude'],_frt['longitude'], \
                        int(_frt['enabled']),0,int(_map_cell['current_timestamp_ms']/1000)))
                    else:
                        _type = 1; _cstats[1]+=1
                        _content = set_bit(_content, 1)
                        db_cur.execute("INSERT OR IGNORE INTO forts (fort_id, cell_id, pos_lat, pos_lng, fort_enabled, fort_type, last_scan) "
                        "VALUES ('{}','{}',{},{},{},{},{})".format(_frt['id'],_cell,_frt['latitude'],_frt['longitude'], \
                        int(_frt['enabled']),1,int(_map_cell['current_timestamp_ms']/1000)))
                                                             
            if 'spawn_points' in _map_cell:
                _content = set_bit(_content, 0)
                for _spwn in _map_cell['spawn_points']:
                    _cstats[2]+=1;
                    spwn_id = CellId.from_lat_lng(LatLng.from_degrees(_spwn['latitude'],_spwn['longitude'])).parent(20).to_token()
                    db_cur.execute("INSERT OR IGNORE INTO spawns (spawn_id, cell_id, pos_lat, pos_lng, last_scan) "
                    "VALUES ('{}','{}',{},{},{})".format(spwn_id,_cell,_spwn['latitude'],_spwn['longitude'],int(_map_cell['current_timestamp_ms']/1000)))
            if 'decimated_spawn_points' in _map_cell:
                _content = set_bit(_content, 0)
                for _spwn in _map_cell['decimated_spawn_points']:
                    _cstats[2]+=1;
                    spwn_id = CellId.from_lat_lng(LatLng.from_degrees(_spwn['latitude'],_spwn['longitude'])).parent(20).to_token()
                    db_cur.execute("INSERT OR IGNORE INTO spawns (spawn_id, cell_id, pos_lat, pos_lng, last_scan) "
                    "VALUES ('{}','{}',{},{},{})".format(spwn_id,_cell,_spwn['latitude'],_spwn['longitude'],int(_map_cell['current_timestamp_ms']/1000)))
                    
            db_cur.execute("INSERT OR IGNORE INTO cells (cell_id, content, last_scan) "
            "VALUES ('{}', {}, {})".format(_cell,_content,int(_map_cell['current_timestamp_ms']/1000)))
            
        _tstats[1] += _cstats[0]; _tstats[2] += _cstats[1]; _tstats[3] += _cstats[2]
        db_cur.execute("DELETE FROM _queue WHERE cell_id='{}'".format(cell.to_token()))
        log.info("Found {} Gyms, {} Pokestops, {} Spawns. Sleeping...".format(*_cstats))
        db.commit()
        time.sleep(int(config.delay))

    log.info('Scanned {} cells; got {} Gyms, {} Pokestops, {} Spawns.'.format(*_tstats))

if __name__ == '__main__':
    main()