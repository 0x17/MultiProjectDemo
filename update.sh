#!/bin/sh

python mip_main.py

python exceltojsonfiles.py
python visualizestructure.py
python visualizestructure.py sequential

python copyresults.py

#python clearfiles.py