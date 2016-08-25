#!/usr/bin/env python

import sqlite3, sys
from s2sphere import CellId
from utils import get_pokenames

def gen_csv_counted(filename, dbfile):

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
                dbcur.execute("UPDATE encount SET count = count + 1 WHERE spawn = '%s' AND poke = %d" % (e,i))
                
    dbout.commit()
        
    f = open(filename,'w')
    pname = get_pokenames('pokes.txt')
    f.write('spawn_id, latitude, longitude, count, pokemon_id, pokemon_name\n')

    spwns = dbout.execute("SELECT spawn, poke, count FROM encount ORDER BY poke ASC, count DESC").fetchall()
    
    if len(spwns) > 0:
        for s,p,c in spwns:
            _ll = CellId.from_token(s).to_lat_lng()
            lat, lng, = _ll.lat().degrees, _ll.lng().degrees
            f.write("{},{},{},{},{},{}\n".format(s,lat,lng,c,p,pname[p]))
                
    print('Done!')

def gen_csv(filename, dbfile):
    
    f = open(filename,'w')
    db = sqlite3.connect(dbfile)
    pname = get_pokenames('pokes.txt')
    f.write('spawn_id, latitude, longitude, pokemon_id, pokemon_name\n')

    spwns = db.execute("SELECT spawn_id, pokemon_id FROM encounters WHERE spawn_id IS NOT NULL").fetchall()
    
    if len(spwns) > 0:
        for s,p in spwns:
            _ll = CellId.from_token(s).to_lat_lng()
            lat, lng, = _ll.lat().degrees, _ll.lng().degrees
            f.write("{},{},{},{},{}\n".format(s,lat,lng,p,pname[p]))
                
    print('Done!')

def main():
    dbfilename = 'db2.sqlite'
    
    if len(sys.argv)<=1:
        print('currently supported commands:\n')
        print('analyze.py export csv <filename>')
        print('analyze.py export csv count <filename>')
        return
    
    if sys.argv[1] == 'export' and sys.argv[2] == 'csv':
        if sys.argv[3] == 'count':
            gen_csv_counted(sys.argv[4],dbfilename)
        else:
            gen_csv(sys.argv[3],dbfilename)
    
if __name__ == '__main__':
    main()