import os
import sys
import random
import json
import shutil

VERY_TRANSPARENT = '#00000033'
SLIGHTLY_TRANSPARENT = '#00000077'
hide_result = any(arg == 'noresult' for arg in sys.argv)

random.seed(2)


########################################################################
# Helpers
########################################################################


def log(s): print(s + '...')


def extract_int(s): return int(float(s))


def extract_float(s): return float(s)


def to_hex_str(v):
    return ('%X' % v).zfill(2)


def rand_rgb(ub):
    r = int(random.random() * ub)
    g = int(random.random() * ub)
    b = int(random.random() * ub)
    return r, g, b


def brightness_for_rgb(r, g, b):
    return (r + g + b) / (3.0 * 255.0)


def rgb_color_to_hex(r, g, b):
    return '#' + to_hex_str(r) + to_hex_str(g) + to_hex_str(b)


def brightness_to_font_color(brightness):
    return '#000000' if brightness > 0.5 else '#ffffff'


def brighten_color(col, incstep, ub=255):
    r, g, b = col
    return min(r + incstep, ub), min(g + incstep, ub), min(b + incstep, ub)


def parse_json(fn):
    with open(fn, 'r') as fp:
        return json.load(fp)


NUM_PROJECTS = 3
OUT_DIR_PREFIX = 'JSMultiScheduleVisualizer/'


class StructureVisualizer:
    ########################################################################
    # Read project data
    ########################################################################
    def __init__(self, prefix='Projekt', suffix='.json'):
        log('Loading project data')

        self.durations, self.demands, self.pobjs = 3 * [[]]

        proj_filenames = [prefix + str(l + 1) + suffix for l in range(NUM_PROJECTS)]
        self.pobjs = [parse_json(fn) for fn in proj_filenames]
        self.durations = [obj['durations'] for obj in self.pobjs]
        self.demands = [obj['demands'] for obj in self.pobjs]

        self.numDecisions = len(self.pobjs[0]['job_in_decision'][0])
        self.numJobs = len(self.durations[0])

        self.jobs = range(1, self.numJobs + 1)

        project_colors = [rand_rgb(150) for l in range(NUM_PROJECTS)]
        self.job_colors = [{j: self.get_color_for_job(project_colors, j, l) for j in self.jobs} for l in range(NUM_PROJECTS)]
        self.write_job_colors()

        self.decisionTriggers = []
        for l in range(NUM_PROJECTS):
            self.decisionTriggers.append([None] * self.numDecisions)
            for ix in range(self.numDecisions):
                for j in range(self.numJobs):
                    if self.pobjs[l]['job_activating_decision'][j][ix]:
                        self.decisionTriggers[l][ix] = j
                        break

        self.decisionSets = [[[j for j in range(self.numJobs) if self.pobjs[l]['job_in_decision'][j][ix]] for ix in range(self.numDecisions)] for l in range(NUM_PROJECTS)]

        with open('ergebnisse.json', 'r') as fp:
            sts = json.load(fp)
            self.executed_jobs = [[j for j in self.jobs if int(sts[l][str(j)]) != -1] for l in range(NUM_PROJECTS)]

    def write_job_colors(self):
        with open('jobcolors.json', 'w') as fp:
            fp.write(json.dumps([ {j: {'jobColor': self.job_colors[l][j]['color'],
                                     'textColor': brightness_to_font_color(self.job_colors[l][j]['brightness'])} for j in self.jobs} for l in range(NUM_PROJECTS)],
                                sort_keys=True, indent=4))
        shutil.copyfile('jobcolors.json', OUT_DIR_PREFIX+'jobcolors.json')

    def get_color_for_job(self, project_colors, j, l):
        INCSTEP = 10
        r, g, b = brighten_color(project_colors[l], INCSTEP * j)
        return {'color': rgb_color_to_hex(r, g, b), 'brightness': brightness_for_rgb(r, g, b)}

    ########################################################################
    # Generate graphviz code
    ########################################################################

    def build_precedence_edges(self, l, ostr):
        for pred in range(self.numJobs):
            for succ in range(self.numJobs):
                if self.pobjs[l]['precedence'][pred][succ]:
                    colorAttr = ' [color="' + VERY_TRANSPARENT + '"]' if not hide_result and (
                        pred not in self.executed_jobs[l] or succ not in self.executed_jobs[l]) else ''
                    ostr += str(pred+1) + '->' + str(succ+1) + colorAttr + ';\n'
        return ostr

    def build_decision_clusters(self, l, ostr):
        for i in range(self.numDecisions):
            decision_caption = str(i + 1)
            ostr += 'subgraph cluster_' + decision_caption + ' {\n'
            for j in self.decisionSets[l][i]: ostr += str(j+1) + ';\n'
            ostr += 'label=<Entscheidung ' + decision_caption + '<br /><font point-size="8">a(' + decision_caption + ')=' + str(
                self.decisionTriggers[l][i]) + '</font>>;\n}\n'
        return ostr

    def build_graphviz_code(self, l=0):
        vizStr = 'digraph G {\nnode [shape=box];\nedge [color="' + SLIGHTLY_TRANSPARENT + '"];\n'

        for j in self.jobs:
            descr = 'd=' + str(self.durations[l][j - 1]) + ', k=' + str(self.demands[l][0][j - 1])
            vizStr += str(j) + '[label=<' + str(j) + '<br/><font point-size="8">' + descr + '</font>>] ;\n'
            if not hide_result and j not in self.executed_jobs[l]:
                vizStr += str(j) + ' [color="' + VERY_TRANSPARENT + '",fontcolor="' + VERY_TRANSPARENT + '"];\n'

        # precedence
        log('Writing precedence relation')

        vizStr = self.build_precedence_edges(l, vizStr)

        # decisions
        log('Writing decisions')

        vizStr = self.build_decision_clusters(l, vizStr)

        # conditionals
        log('Writing conditional activities')

        clusterIx = self.numDecisions

        for pred in range(self.numJobs):
            for succ in range(self.numJobs):
                if self.pobjs[l]['job_causing_job'][pred][succ]:
                    vizStr += 'subgraph cluster_' + str(clusterIx + 1) + ' {\n' + str(succ+1) + '\nlabel=<<font point-size="10">Bedingt durch ' + str(pred+1) + '</font>>;\n}\n'
                    clusterIx += 1

        # colorize mandatory jobs
        log('Colorize mandatory jobs')
        mandatoryJobs = self.pobjs[l]['mandatory_activities']
        for j in self.jobs:
            borderColor = 'blue' if j in mandatoryJobs else 'black'
            if j in self.executed_jobs[l]:
                vizStr += str(j) + ' [fontcolor="' + brightness_to_font_color(self.job_colors[l][j]['brightness']) + '",color=' + borderColor + ',fillcolor="' + self.job_colors[l][j]['color'] + '",style=filled]'

        vizStr += '}\n'

        return vizStr


sv = StructureVisualizer()
for l in range(NUM_PROJECTS):
    with open('forgviz'+str(l+1)+'.dot', 'w') as fp:
        fp.write(sv.build_graphviz_code(l))
    outfn = 'forgviz'+str(l+1)+'.pdf'
    os.system('dot forgviz'+str(l+1)+'.dot -o '+outfn+' -Tpdf')
    shutil.copyfile(outfn, OUT_DIR_PREFIX+outfn)
