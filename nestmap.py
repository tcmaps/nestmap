#!/usr/bin/env python
VERSION = 1.2

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
import sqlite3
import logging
import argparse

from s2sphere import CellId
from utils import get_watchlist, get_pokenames
from pgoapi.exceptions import NotLoggedInException
from utils import check_db, api_init, get_response, get_cell_ids, susub_cells

log = logging.getLogger(__name__)
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

def init_config():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    load   = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')", default="ptc")
    parser.add_argument("-u", "--username", help="Username")
    parser.add_argument("-p", "--password", help="Password")
    parser.add_argument("-t", "--delay", help="rpc request interval", default=10, type=int)
    parser.add_argument("-l", "--limit", help="clusters to monitor", default=100, type=int)
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true', default=0)    
    config = parser.parse_args()

    for key in config.__dict__:
        if key in load and config.__dict__[key] == None:
            config.__dict__[key] = load[key]

    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)
    else:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("pgoapi").setLevel(logging.WARNING)
        logging.getLogger("rpc_api").setLevel(logging.WARNING)

    if config.auth_service not in ['ptc', 'google']:
        log.error("Invalid Auth service specified! ('ptc' or 'google')")
        return None
    
    dbversion = check_db('db2.sqlite')     
    if dbversion != VERSION:
        log.error('Database version mismatch! Expected {}, got {}...'.format(VERSION,dbversion))
        return

    return config

def main():
      
    config = init_config()
    if not config:
        return
        
    if not os.path.isfile('db2.sqlite'):
        log.error('DB not found - please run nestgen.py!')
        return
    
    watchlist = get_watchlist('watch.txt')
    pokenames = get_pokenames('pokes.txt')
        
    log.info("DB ok. Loggin' in...")
    
    db = sqlite3.connect('db2.sqlite')
    db_cur = db.cursor()
    
    run = 1
    while run:
        
        _ccnt = 1
        
        db_cur.execute("SELECT cell_id FROM queque ORDER BY spawn_count LIMIT %d" % config.limit)
        # http://stackoverflow.com/questions/3614277/how-to-strip-from-python-pyodbc-sql-returns
        scan_queque = [x[0] for x in db_cur.fetchall()]
        
        if len(scan_queque) == 0: log.info('Nothing to scan!'); return

        api = api_init(config)
        if api == None:   
            log.error('Login failed!'); return
        else:
            log.info('API online! Scan starts in 5sec...')
        time.sleep(5)
  
        for queq in scan_queque:    
            
            try:      
                
                _ecnt = [0,0]
                traverse = 0; targets = []
                cell = CellId.from_token(queq)
                
                _ll = CellId.to_lat_lng(cell)
                lat, lng, alt = _ll.lat().degrees, _ll.lng().degrees, 0
                cell_ids = [cell.id()]
                
                response_dict = get_response(cell_ids, lat, lng, alt, api, config)
                
                log.info('Scanning macrocell {} of {}.'.format(_ccnt,(len(scan_queque))))
                        
                for _map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:                        
                    
                    if 'nearby_pokemons' in _map_cell:
                        for _poke in _map_cell['nearby_pokemons']:
                            _ecnt[0]+=1;                            
                            _s = hex(_poke['encounter_id'])
                            _c = CellId(_map_cell['s2_cell_id']).to_token()
                            db_cur.execute("INSERT OR IGNORE INTO encounters (encounter_id, cell_id, pokemon_id, encounter_time) VALUES ('{}','{}',{},{})"
                            "".format(_s.strip('L'),_c.strip('L'),_poke['pokemon_id'],int(_map_cell['current_timestamp_ms']/1000)))
                            
                            if _poke['pokemon_id'] in watchlist:
                                traverse = 1
                                targets.append(_poke['encounter_id'])
                                log.info('{} nearby!'.format(pokenames[_poke['pokemon_id']]))
                                
                    if 'catchable_pokemons' in _map_cell:
                        for _poke in _map_cell['catchable_pokemons']:
                            _ecnt[1]+=1;
                            _s = hex(_poke['encounter_id'])
                            db_cur.execute("INSERT OR REPLACE INTO encounters (spawn_id, encounter_id, pokemon_id, encounter_time, expire_time) VALUES ('{}','{}',{},{},{})"
                            "".format(_poke['spawn_point_id'],_s.strip('L'),_poke['pokemon_id'],int(_map_cell['current_timestamp_ms']/1000),int(_poke['expiration_timestamp_ms']/1000)))
                                    
                db.commit
    
                if traverse:                                     
                    _remaining = len(targets)
                    log.info('Narrow search for %d Pokemon...' % len(targets))
                    time.sleep(config.delay)
                    
                    _scnt = 1
                    subcells = susub_cells(cell)
                    for _sub in subcells:
                        log.info('Scanning subcell {} of up to 16.'.format(_scnt,(len(scan_queque))))
                        
                        _ll = CellId.to_lat_lng(_sub)
                        lat, lng, alt = _ll.lat().degrees, _ll.lng().degrees, 0
                        cell_ids = get_cell_ids(lat, lng, 100)
                        
                        try: response_dict = get_response(cell_ids, lat, lng, alt, api,config)
                        except NotLoggedInException: del api; api = api_init(config); response_dict = get_response(cell_ids, lat, lng, alt, api,config)
                                                    
                        for _map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:
                            if 'catchable_pokemons' in _map_cell:
                                for _poke in _map_cell['catchable_pokemons']:
                                    _ecnt[1]+=1;
                                    _s = hex(_poke['encounter_id'])
                                    db_cur.execute("INSERT OR REPLACE INTO encounters (spawn_id, encounter_id, pokemon_id, encounter_time, expire_time) VALUES ('{}','{}',{},{},{})"
                                    "".format(_poke['spawn_point_id'],_s.strip('L'),_poke['pokemon_id'],int(_map_cell['current_timestamp_ms']/1000),int(_poke['expiration_timestamp_ms']/1000)))
                                    
                                    if _poke['encounter_id'] in targets:
                                        log.info('Tracked down {}!'.format(pokenames[_poke['pokemon_id']]))
                                        _remaining -=1
                                        log.info('%d Pokemon remaining...' % _remaining)
                            
                        if _remaining <= 0: break        
                        time.sleep(config.delay)
                        _scnt += 1
    
                db.commit()
                log.info("Encounters: {} coarse, {} fine...".format(*_ecnt))
                time.sleep(config.delay)
                _ccnt +=1
            
            except NotLoggedInException: del api; break
        
        log.info("Rinsing 'n' Repeating...")           
    

if __name__ == '__main__':
    main()