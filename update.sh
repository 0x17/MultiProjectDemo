#!/bin/sh

python3.6 mip_main.py

python3.6 exceltojsonfiles.py
python3.6 visualizestructure.py
python3.6 visualizestructure.py sequential

python3.6 copyresults.py

#python3.6 clearfiles.py