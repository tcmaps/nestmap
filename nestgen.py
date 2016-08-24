#!/usr/bin/env python

import os, sqlite3
from s2sphere import CellId

def main():
    if not os.path.isfile('db.sqlite'): print('Fastmap DB missing!')
    if not os.path.isfile('db2.sqlite'):
        if os.name =='nt': os.system('copy db2.temp db2.sqlite')
        elif os.name =='posix': os.system('cp db2.temp db2.sqlite')
    
    spawns = [x[0] for x in sqlite3.connect('db.sqlite').cursor()\
            .execute("SELECT spawn_id FROM 'spawns' ORDER BY spawn_id").fetchall()]

    db = sqlite3.connect('db2.sqlite')
    cells = 0
    for spawn in spawns:
        cellid = CellId.from_token(spawn).parent(15).to_token()
        db.cursor().execute("INSERT OR IGNORE INTO queque (cell_id) VALUES ('{}')".format(cellid))
        db.cursor().execute("UPDATE queque SET spawn_count = spawn_count + 1 WHERE cell_id = '{}'".format(cellid))
        cells+=1
    db.commit(); print 'Done!'
if __name__ == '__main__': main()