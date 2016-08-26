FMDBVERSION = 2.1
import sqlite3, os, logging
log = logging.getLogger(__name__)

def check_db(dbfile):
    
    if not os.path.isfile(dbfile):
        create_db(dbfile)
    
    db = sqlite3.connect(dbfile)
    version = db.cursor().execute("SELECT version FROM '_config'").fetchone()
    
    return version[0]

def fill_db(dbfile, cells):
    db = sqlite3.connect(dbfile)
    counter=0    
    for cell in cells:
        db.cursor().execute("INSERT OR IGNORE INTO _queue (cell_id,cell_level) "
                            "VALUES ('{}',{})".format(cell.to_token(),cell.level()))
        counter+=1
    db.commit()
    return counter

def create_db(dbfile):
    db = sqlite3.connect(dbfile); dbc = db.cursor()
    dbc.execute("CREATE TABLE _config (version VARCHAR DEFAULT '1.0')")
    dbc.execute("CREATE TABLE _queue (cell_id VARCHAR PRIMARY KEY, cell_level INT)")
    dbc.execute("CREATE TABLE cells (cell_id VARCHAR PRIMARY KEY, content INT, last_scan TIMESTAMP)")
    dbc.execute("CREATE TABLE forts (fort_id VARCHAR PRIMARY KEY, cell_id VARCHAR, \
    pos_lat DOUBLE, pos_lng DOUBLE, fort_enabled BOOLEAN, fort_type INT, fort_description TEXT, \
    fort_image BLOB, fort_sponsor TEXT, fort_last_modified TIMESTAMP, last_scan TIMESTAMP,\
    FOREIGN KEY ( cell_id ) REFERENCES cells (cell_id) )")
    dbc.execute("CREATE TABLE spawns (spawn_id VARCHAR PRIMARY KEY, cell_id VARCHAR, \
    pos_lat DOUBLE, pos_lng DOUBLE, static_spawner INT DEFAULT (0), nest_spawner INT DEFAULT (0), \
    spawn_time_base TIME, spawn_time_offset TIME, spawn_time_dur TIME, last_scan TIMESTAMP, \
    FOREIGN KEY (cell_id) REFERENCES cells (cell_id) )")
    dbc.execute("INSERT INTO _config (version) VALUES (%s)" % FMDBVERSION); db.commit()
    log.info('DB created!')

if __name__ == '__main__':
    create_db('db.sqlite')