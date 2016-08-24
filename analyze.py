#!/usr/bin/env python

import os, sys, sqlite3
from s2sphere import CellId

if __name__ == '__main__':
    #if os.path.isfile('nests.sqlite'): os.remove('nests.sqlite')
    dbin = sqlite3.connect(sys.argv[1])
    #dbout = sqlite3.connect('nests.sqlite')
    
    encs = dbin.cursor().execute("SELECT encounter_id, spawn_id, pokemon_id FROM encounters WHERE spawn_id IS NOT NULL ").fetchall()
    
    f = open(sys.argv[2],'w')
    f.write('latitude,longitude,pokemon\n')
    for enc in encs:
        cell = CellId.from_token(enc[1]);_ll = CellId.to_lat_lng(cell)
        lat, lng, = _ll.lat().degrees, _ll.lng().degrees
        f.write("{},{},{}\n".format(lat, lng, enc[2]))

    f.flush(); f.close()
    print('Donezo!')