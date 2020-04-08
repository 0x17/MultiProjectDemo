#!/bin/sh

python3.6 mip_main.py no_excel

python3.6 visualizestructure.py
python3.6 visualizestructure.py sequential

python3.6 copyresults.py

#python clearfiles.py