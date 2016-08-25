#!/usr/bin/env python

import sqlite3, sys
from s2sphere import CellId
from utils import get_pokenames

def gen_db(dbfile):

    dbin = sqlite3.connect(dbfile)
    dbout = sqlite3.connect(':memory:'); dbcur = dbout.cursor()
    dbcur.execute("CREATE TABLE encount (spawn VARCHAR, poke INT, count INT DEFAULT 0, \
                    PRIMARY KEY (spawn, poke) )")
    
    for i in range(151):
        
        encs = [x[0] for x in dbin.cursor().execute("SELECT spawn_id FROM encounters "
                        "WHERE spawn_id IS NOT NULL AND pokemon_id = %d" % i).fetchall()]
        
        if len(encs) > 0:
        
            
            for e in encs:
                dbcur.execute("INSERT OR IGNORE INTO encount (spawn, poke) VALUES ('{}',{})".format(e,i))
                dbcur.execute("UPDATE encount SET count = count + 1 WHERE spawn = '%s'" % e)
                
    dbout.commit()
    return dbout

def gen_csv(filename):
    
    f = open(filename,'w')
    db = sqlite3.connect('db2.sqlite')
    pname = get_pokenames('pokes.txt')
    f.write('spawn_id, pokemon_id, pokemon_name, latitude, longitude\n')

    spwns = db.execute("SELECT spawn_id, pokemon_id FROM encounters WHERE spawn_id IS NOT NULL").fetchall()
    
    if len(spwns) > 0:
        for s,i in spwns:
            _ll = CellId.from_token(s).to_lat_lng()
            lat, lng, = _ll.lat().degrees, _ll.lng().degrees
            f.write("{},{},{},{},{}\n".format(s,i,pname[i],lat,lng))
                
    print('Done!')

def main():
    #db = gen_db('db2.sqlite')
    
    if len(sys.argv)<4:
        print('currently only supported command: analyze.py export csv <filename>')
        return
    
    if sys.argv[1] == 'export' and sys.argv[2] == 'csv':
        gen_csv(sys.argv[3])
    
if __name__ == '__main__':
    main()
