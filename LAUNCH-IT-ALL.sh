python -m http.server &
python watcher.py &
open "Input.xlsx"
open "http://localhost:8000/JSMultiScheduleVisualizer/schedulevis.html?sequential=0" -a "Google Chrome"
#open "http://localhost:8000/JSMultiScheduleVisualizer/schedulevis.html?sequential=1" -a "Google Chrome"