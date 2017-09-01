import os

suffixes = ['lst', 'log', 'lxi', 'json', 'pdf', '~gm', 'gdx', 'dot', 'txt']
for suffix in suffixes:
	print('Deleting files with suffix: ' + suffix + ' ...')
	os.system('del *.' + suffix)