#!/usr/bin/env python
DBVERSION = 1.3

"""
based on: pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>

Author: TC    <reddit.com/u/Tr4sHCr4fT>
Version: 1.1
"""

import os
import time
import json
import sqlite3
import logging
import argparse

from s2sphere import CellId
from fmcore.db import check_db
from fmcore.apiwrap import api_init, get_response
from fmcore.utils import get_cell_ids, cover_circle, sub_cells, susub_cells, get_pokenames
from pgoapi.exceptions import NotLoggedInException

log = logging.getLogger(__name__)

def init_config():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
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
    parser.add_argument("-s", "--step", help="instance / scan part", default=1, type=int)
    parser.add_argument("--limit", help="cells per queue", default=100, type=int)
    parser.add_argument("--ndbfile", help="Nestmap database", default='nm.sqlite')
    parser.add_argument("--fdbfile", help="Fastmap database", default='db.sqlite')
    parser.add_argument("--regen", help="Reset scan queue", action='store_true', default=0)    
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

    if config.ndbfile == 'nm.sqlite':
        if os.path.isfile('db2.sqlite'):
            config.ndbfile = 'db2.sqlite';
    
    if os.path.isfile(config.ndbfile):
        log.info('Will use existing Nestmap DB.')
    else:
        create_db2(config.ndbfile)
        log.info('Nestmap DB created!')
    
    dbversion = check_db(config.ndbfile)     
    if dbversion != DBVERSION:
        if convert_db2(config.ndbfile, dbversion):
            log.info('Nestmap DB updated.')
        else:
            log.critical('Nestmap DB version %d not compatible!' % dbversion)

    return config

def main():
      
    config = init_config()
    if not config:
        return
    
    watchlist = get_watchlist('watch.txt')
    pokenames = get_pokenames('pokes.txt')
    
    db = sqlite3.connect(config.ndbfile)
    dbc = db.cursor()
    
    run = 1
    while run:
        
        _ccnt, y, z = 1, config.limit, (config.step-1)*config.limit 
        
        dbc.execute("SELECT cell_id FROM _queue ORDER BY cell_id LIMIT %d,%d" % (z,y)); del y
        # http://stackoverflow.com/questions/3614277/how-to-strip-from-python-pyodbc-sql-returns
        scan_queque = [x[0] for x in dbc.fetchall()]
        
        if config.regen or len(scan_queque) == 0:
            log.info('Generating scan queue...')
            if gen_que(config.ndbfile, config.fdbfile): continue
            else: return

        api = api_init(config)
        if api == None:   
            log.error('Login failed!'); return
        else:
            log.info('API online! starting Scan...')
        time.sleep(5)
  
        for queq in scan_queque:    
            
            try:      
                
                _ecnt = [0,0]
                traverse = 0; targets = []
                
                cell = CellId.from_token(queq)
                lat = CellId.to_lat_lng(cell).lat().degrees
                lng = CellId.to_lat_lng(cell).lng().degrees
                
                cell_ids = [cell.id()]
                
                response_dict = get_response(api, cell_ids, lat, lng)
                
                log.info('Scanning cell {} of {}.'.format(_ccnt+z,z+(len(scan_queque))))
                        
                for _map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:                        
                    
                    if 'nearby_pokemons' in _map_cell:
                        for _poke in _map_cell['nearby_pokemons']:
                            _ecnt[0]+=1;                            
                            _s = hex(_poke['encounter_id'])
                            _c = CellId(_map_cell['s2_cell_id']).to_token()
                            dbc.execute("INSERT OR IGNORE INTO encounters (encounter_id, cell_id, pokemon_id, encounter_time) VALUES ('{}','{}',{},{})"
                            "".format(_s.strip('L'),_c,_poke['pokemon_id'],int(_map_cell['current_timestamp_ms']/1000)))
                            
                            if _poke['pokemon_id'] in watchlist:
                                traverse = 1
                                targets.append(_poke['encounter_id'])
                                log.info('{} nearby!'.format(pokenames[_poke['pokemon_id']]))
                                
                    if 'catchable_pokemons' in _map_cell:
                        for _poke in _map_cell['catchable_pokemons']:
                            _ecnt[1]+=1;
                            _s = hex(_poke['encounter_id'])
                            dbc.execute("INSERT OR REPLACE INTO encounters (spawn_id, encounter_id, pokemon_id, encounter_time, expire_time) VALUES ('{}','{}',{},{},{})"
                            "".format(_poke['spawn_point_id'],_s.strip('L'),_poke['pokemon_id'],int(_map_cell['current_timestamp_ms']/1000),int(_poke['expiration_timestamp_ms']/1000)))
                                    
                db.commit()
    
                if traverse:                                     
                    _remaining = len(targets)
                    log.info('Narrow search for %d Pokemon...' % len(targets))
                    time.sleep(config.delay)
                    
                    _scnt = 1
                    subcells = susub_cells(cell)
                    for _sub in subcells:
                        log.debug('Scanning subcell {} of up to 16.'.format(_scnt,(len(scan_queque))))
                        
                        lat = CellId.to_lat_lng(_sub).lat().degrees
                        lng = CellId.to_lat_lng(_sub).lng().degrees
                        cell_ids = get_cell_ids(cover_circle(lat, lng, 100))
                        
                        try: response_dict = get_response(api, cell_ids, lat, lng)
                        except NotLoggedInException: api = None; api = api_init(config); response_dict = get_response(api, cell_ids, lat, lng)
                                                    
                        for _map_cell in response_dict['responses']['GET_MAP_OBJECTS']['map_cells']:
                            if 'catchable_pokemons' in _map_cell:
                                for _poke in _map_cell['catchable_pokemons']:
                                    _ecnt[1]+=1;
                                    _s = hex(_poke['encounter_id'])
                                    dbc.execute("INSERT OR REPLACE INTO encounters (spawn_id, encounter_id, pokemon_id, encounter_time, expire_time) VALUES ('{}','{}',{},{},{})"
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
            
            except NotLoggedInException: api = None; break
        
        log.info("Rinsing 'n' Repeating...")           

    
def create_db2(dbfile):  
    db = sqlite3.connect(dbfile)
    db.cursor().execute("CREATE TABLE _config (version DECIMAL (3) DEFAULT (1))")
    db.cursor().execute("INSERT INTO _config (version) VALUES (1.3)") 
    db.cursor().execute("CREATE TABLE _queue (cell_id    VARCHAR    PRIMARY KEY)")
    db.cursor().execute("CREATE TABLE encounters (\
                        encounter_id   VARCHAR,\
                        spawn_id       VARCHAR,\
                        cell_id        VARCHAR,\
                        pokemon_id     INT,\
                        expire_time    TIME,\
                        encounter_time TIME,\
                        PRIMARY KEY (encounter_id))\
                        WITHOUT ROWID")
    db.commit()
    db.close()

def convert_db2(dbfile, olddbv):
    db = sqlite3.connect(dbfile) 
    newdbv = olddbv
    
    if newdbv == 1.1:
        log.info('Converting DB from 1.1 to 1.2')

        db.cursor().execute("ALTER TABLE encounters ADD cell_id VARCHAR")
        db.cursor().execute("UPDATE _config SET version = 1.2 WHERE version = 1.1")
        db.commit(); newdbv = 1.2
    
    if newdbv == 1.2:
        log.info('Converting DB from 1.2 to 1.3')
        db.cursor().execute("DROP TABLE queque")
        db.cursor().execute("CREATE TABLE _queue (cell_id VARCHAR PRIMARY KEY)")        
        db.cursor().execute("UPDATE _config SET version = 1.3 WHERE version = 1.2")
        db.commit(); newdbv = 1.3
    
    db.cursor().execute("VACUUM"); 
    db.close()

    if newdbv == DBVERSION:
        return True
    else:
        return False
    
def gen_que(ndbfile, fdbfile): 
    if not os.path.isfile(fdbfile):
        log.critical('Fastmap DB missing!!')
        log.info('Run bootstrap.py!')
        return False
    
    db =  sqlite3.connect(ndbfile)
    
    dbtmp = sqlite3.connect(':memory:')
    dbtmp.cursor().execute("CREATE TABLE queque (\
                            cell     VARCHAR PRIMARY KEY,\
                            count INT     DEFAULT (0) )")
    
    # tiling up
    spawns = [x[0] for x in sqlite3.connect(fdbfile).cursor()\
            .execute("SELECT spawn_id FROM 'spawns' ORDER BY spawn_id").fetchall()]
    
    for spawn in spawns:
        cellid = CellId.from_token(spawn).parent(14).to_token()
        dbtmp.cursor().execute("INSERT OR IGNORE INTO queque (cell) VALUES ('{}')".format(cellid))
        dbtmp.cursor().execute("UPDATE queque SET count = count + 1 WHERE cell = '{}'".format(cellid))
    
    # tiling down
    cells = [x[0] for x in dbtmp.cursor()\
            .execute("SELECT cell FROM 'queque' ORDER BY count DESC").fetchall()]
    dbtmp.close(); del dbtmp
    
    db.cursor().execute("DELETE FROM _queue")
    
    for cell in cells:
        subcells = sub_cells(CellId.from_token(cell))
        for subcell in subcells:
            db.cursor().execute("INSERT OR IGNORE INTO _queue (cell_id) VALUES ('{}')".format(subcell.to_token()))

    db.cursor().execute("VACUUM"); db.commit(); 
    log.info('Scan queue generated.')
    return True

def get_watchlist(filename):
    wlist = []
    f = open(filename,'r')
    for l in f.readlines():
        wlist.append(int(l.strip()))
    return wlist

if __name__ == '__main__':
    main()