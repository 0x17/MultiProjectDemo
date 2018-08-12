#!/usr/bin/python

import time
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import asyncio
import websockets

last_update = datetime.datetime.now()
MIN_SECONDS_BETWEEN = 1
should_reload = False

class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global last_update, should_reload
        if event.event_type == 'modified' and event.src_path == '.':
            if (datetime.datetime.now() - last_update).total_seconds() > MIN_SECONDS_BETWEEN:
                last_update = datetime.datetime.now()
                os.system('sh update.sh')
                should_reload = True
        print(f'event type: {event.event_type}  path : {event.src_path}')


if __name__ == "__main__":
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        async def time(websocket, path):
            global should_reload
            while True:
                if should_reload:
                    await websocket.send('please-reload')
                    should_reload = False
                await asyncio.sleep(1)

        start_server = websockets.serve(time, '127.0.0.1', 5678)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        observer.stop()
    except websockets.exceptions.ConnectionClosed:
        print('Connection closed')
    observer.join()
