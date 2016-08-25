# Nestmap

A tool for locating & analyzing nests the easy way.


## Installation

1. Clone/Download this Git.
2. Get pgoapi from [link]https://github.com/pogodevorg/pgoapi
3. Optain libencrypt for your OS&arch (some popular maps include it)
4. **pip install -r requirements.txt** (may require sudo / Admin)

### Prereqs

If you don't have a Fastmap bootstrap db.sqlite yet,
- Get https://github.com/Tr4sHCr4fT/fastmap and create one

1. Have your Fastmap *db.sqlite* in Nestmap's dir
2. run nestgen.py ++once++ to create *db2.sqlite*
3. Put your account credentials in *config.json*

### Usage

Basic:
```
python nestmap.py
```
