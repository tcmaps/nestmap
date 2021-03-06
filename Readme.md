# Nestmap

A tool for locating & analyzing nests the easy way.


## Installation

1. Clone/Download this Git.
2. Get pgoapi from https://github.com/pogodevorg/pgoapi
3. Optain libencrypt for your OS&arch (some popular maps include it)
4. **pip install -r requirements.txt** (may require sudo / Admin)

### Prereqs

1. Have your Fastmap *db.sqlite* in Nestmap's dir  
**If you don't have a Fastmap bootstrap db.sqlite yet,** *Get https://github.com/Tr4sHCr4fT/fastmap*   
*or use* **bootstrap.py** *to create one! (refer to mentioned Fastmap project for usage instructions)*

2. Put your account credentials in *config.json*   
3. If used "nestgen.py" before, run *nestmap.py --regen* once

### Usage

###### Example:
```
python nestmap.py
```

###### Options:

```
nestmap.py [-h] [-a AUTH_SERVICE] [-u USERNAME] [-p PASSWORD]
                  [-t DELAY] [-s STEP] [--limit LIMIT] [-d] [--regen]
```

- -a AUTH_SERVICE, --auth_service   
'ptc' or 'google'   
- -u USERNAME, -p PASSWORD,   
lets you use an account not in config.json   
- -t DELAY, --delay DELAY   
delay between requests (currently 10 minimum)   
- -s STEP, --step STEP   
by default, nestmap scans the top *limit* most spawn dense cells    
each increment of 1 here will do the next *step* * *limit* cells   
- --limit LIMIT   
cells to get and loop through (default 100)
- --regen   
regenerates scan queue
