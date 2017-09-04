import shutil

NUM_JOBS = 3
pindices = range(1, NUM_JOBS + 1)

out_dir = 'JSMultiScheduleVisualizer/'

to_copy = ['ergebnisse.json', 'jobcolors.json'] + ['Projekt' + str(pix) + '.json' for pix in pindices] + [
    'forgviz' + str(pix) + '.pdf' for pix in pindices]

for tc in to_copy:
    out_fn = out_dir + tc
    print('Copying ' + tc + ' into path ' + out_fn + ' ...')
    shutil.copyfile(tc, out_fn)
