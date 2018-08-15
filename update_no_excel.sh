#!/bin/sh

python mip_main.py no_excel

python visualizestructure.py
python visualizestructure.py sequential

python copyresults.py

#python clearfiles.py