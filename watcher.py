#!/usr/bin/python

import asyncio
import datetime
import json
import os
import platform

import websockets
from watchdog.events import FileSystemEventHandler

last_update = datetime.datetime.now()
MIN_SECONDS_BETWEEN = 1
should_reload = False
opt_started = False


class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global last_update, should_reload, opt_started
        if event.event_type == 'modified' and event.src_path == '.':
            if (datetime.datetime.now() - last_update).total_seconds() > MIN_SECONDS_BETWEEN:
                last_update = datetime.datetime.now()
                opt_started = True
        print(f'event type: {event.event_type}  path : {event.src_path}')


def extend_command(base_command):
    return f'{base_command}.bat' if 'Windows' in platform.system() else f'sh {base_command}.sh'


if __name__ == "__main__":
    try:
        async def time(websocket, path):
            global should_reload, opt_started
            while True:
                async for message in websocket:
                    obj = json.loads(message)
                    if obj['type'] == 'optimize':
                        projects = obj['payload']
                        print(obj['payload'][0]['zmax'])
                        for l, p in enumerate(projects):
                            with open(f'Projekt{l + 1}.json', 'w') as fp:
                                json.dump(p, fp)
                        await websocket.send('started')
                        os.system(extend_command('update_no_excel'))
                        await websocket.send('finished')
                    elif obj['type'] == 'reset_from_excel':
                        await websocket.send('started')
                        os.system(extend_command('update'))
                        await websocket.send('finished')

                await asyncio.sleep(1)


        start_server = websockets.serve(time, '127.0.0.1', 5678)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        pass
    except websockets.exceptions.ConnectionClosed:
        print('Connection closed')
