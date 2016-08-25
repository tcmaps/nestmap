#!/usr/bin/env python

import os, sqlite3
from utils import sub_cells
from s2sphere import CellId

def main():
    if not os.path.isfile('db.sqlite'):
        print('Fastmap DB missing!'); return
    if not os.path.isfile('db2.sqlite'):
        db = sqlite3.connect('db2.sqlite')
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
                            WITHOUT ROWID") ; del db
    
    dbtmp = sqlite3.connect(':memory:')
    dbtmp.cursor().execute("CREATE TABLE queque (\
                            cell     VARCHAR PRIMARY KEY,\
                            count INT     DEFAULT (0) )")
    
    # tiling up
    spawns = [x[0] for x in sqlite3.connect('db.sqlite').cursor()\
            .execute("SELECT spawn_id FROM 'spawns' ORDER BY spawn_id").fetchall()]
    
    for spawn in spawns:
        cellid = CellId.from_token(spawn).parent(14).to_token()
        dbtmp.cursor().execute("INSERT OR IGNORE INTO queque (cell) VALUES ('{}')".format(cellid))
        dbtmp.cursor().execute("UPDATE queque SET count = count + 1 WHERE cell = '{}'".format(cellid))
    
    # tiling down
    cells = [x[0] for x in dbtmp.cursor()\
            .execute("SELECT cell FROM 'queque' ORDER BY count DESC").fetchall()]
    
    db = sqlite3.connect('db2.sqlite')
    db.cursor().execute("DELETE FROM _queue")
    
    for cell in cells:
        subcells = sub_cells(CellId.from_token(cell))
        for subcell in subcells:
            db.cursor().execute("INSERT OR IGNORE INTO _queue (cell_id) VALUES ('{}')".format(subcell.to_token()))

    db.cursor().execute("VACUUM")
    db.commit(); print 'Donezo!'
    
if __name__ == '__main__': main()
