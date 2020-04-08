import os

directories = ['JSMultiScheduleVisualizer', '.']
suffixes = ['lst', 'log', 'lxi', 'json', 'pdf', '~gm', 'gdx', 'dot', 'txt']

keep_infixes = ['jobnames', 'required_python_packages', 'MoeglicheArbeitsschritte']


def keep(fn):
    return any(keep_infix in fn for keep_infix in keep_infixes)


for directory in directories:
    for fn in os.listdir(directory):
        suffix = fn.split('.')[-1]
        if suffix in suffixes and not (keep(fn)):
            print(f'Deleting file {fn} in directory {directory}...')
            #cmd = f'del {directory}\\{fn}'
            #os.system(cmd)
            os.remove(f'{directory}/{fn}')
