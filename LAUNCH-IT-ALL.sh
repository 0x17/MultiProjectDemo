#!/bin/bash
python3.6 -m http.server &
python3.6 watcher.py &
#open "Input.xlsx"
#open "http://localhost:8000/JSMultiScheduleVisualizer/schedulevis.html?sequential=0" -a "Google Chrome"
#open "http://localhost:8000/JSMultiScheduleVisualizer/schedulevis.html?sequential=1" -a "Google Chrome"
cd /Applications/Google\ Chrome.app/Contents/MacOS
./Google\ Chrome --start-fullscreen --app=http://localhost:8000/JSMultiScheduleVisualizer/schedulevis.html?sequential=0
