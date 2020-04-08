import json
import os
import random
import shutil
import sys

VERY_TRANSPARENT = '#00000033'
SLIGHTLY_TRANSPARENT = '#00000077'


def has_arg(s): return any(arg == s for arg in sys.argv)


hide_result, sequential = has_arg('noresult'), has_arg('sequential')

random.seed(2)


########################################################################
# Helpers
########################################################################


def log(s): print(f'{s}...')


def extract_int(s): return int(float(s))


def extract_float(s): return float(s)


def to_hex_str(v):
    return ('%X' % v).zfill(2)


def rand_rgb(ub):
    return tuple(int(random.random() * ub) for v in range(3))


def brightness_for_rgb(r, g, b):
    return (r + g + b) / (3.0 * 255.0)


def rgb_color_to_hex(r, g, b):
    return f'#{to_hex_str(r)}{to_hex_str(g)}{to_hex_str(b)}'


def brightness_to_font_color(brightness):
    return '#000000' if brightness > 0.5 else '#ffffff'


def brighten_color(col, incstep, ub=255):
    return tuple(min(v + incstep, ub) for v in col)


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

        self.num_decisions = len(self.pobjs[0]['job_in_decision'][0])
        self.num_jobs = len(self.durations[0])

        self.jobs = range(1, self.num_jobs + 1)

        project_colors = [rand_rgb(150) for l in range(NUM_PROJECTS)]
        self.job_colors = [{j: self.get_color_for_job(project_colors, j, l) for j in self.jobs} for l in
                           range(NUM_PROJECTS)]
        self.write_job_colors()

        self.decision_triggers = []
        for l in range(NUM_PROJECTS):
            self.decision_triggers.append([None] * self.num_decisions)
            for ix in range(self.num_decisions):
                for j in range(self.num_jobs):
                    if self.pobjs[l]['job_activating_decision'][j][ix]:
                        self.decision_triggers[l][ix] = j
                        break

        self.decision_sets = [[[j for j in range(self.num_jobs) if self.pobjs[l]['job_in_decision'][j][ix]] for ix in
                               range(self.num_decisions)] for l in range(NUM_PROJECTS)]

        with open('ergebnisse' + ('Sequentiell' if sequential else '') + '.json', 'r') as fp:
            sts = json.load(fp)
            self.executed_jobs = [[j - 1 for j in self.jobs if int(sts[l][str(j-1)]) != -1] for l in range(NUM_PROJECTS)]

    def write_job_colors(self):
        with open('jobcolors.json', 'w') as fp:
            fp.write(json.dumps([{j: {'jobColor': self.job_colors[l][j]['color'],
                                      'textColor': brightness_to_font_color(self.job_colors[l][j]['brightness'])} for j
                                  in self.jobs} for l in range(NUM_PROJECTS)],
                                sort_keys=True, indent=4))
        shutil.move('jobcolors.json', OUT_DIR_PREFIX + 'jobcolors.json')

    def get_color_for_job(self, project_colors, j, l):
        INCSTEP = 10
        r, g, b = brighten_color(project_colors[l], INCSTEP * j)
        return {'color': rgb_color_to_hex(r, g, b), 'brightness': brightness_for_rgb(r, g, b)}

    ########################################################################
    # Generate graphviz code
    ########################################################################

    def build_precedence_edges(self, l, ostr):
        for pred in range(self.num_jobs):
            for succ in range(self.num_jobs):
                if self.pobjs[l]['precedence'][pred][succ]:
                    color_attr = ' [color="' + VERY_TRANSPARENT + '"]' if not hide_result and (
                            pred not in self.executed_jobs[l] or succ not in self.executed_jobs[l]) else ''
                    ostr += str(pred + 1) + '->' + str(succ + 1) + color_attr + ';\n'
        return ostr

    def build_decision_clusters(self, l, ostr):
        for i in range(self.num_decisions):
            decision_caption = str(i + 1)
            ostr += 'subgraph cluster_' + decision_caption + ' {\n'
            for j in self.decision_sets[l][i]: ostr += str(j + 1) + ';\n'
            ostr += 'label=<Entscheidung ' + decision_caption + '<br /><font point-size="8">a(' + decision_caption + ')=' + str(
                self.decision_triggers[l][i] + 1) + '</font>>;\n}\n'
        return ostr

    def build_graphviz_code(self, l=0):
        viz_str = 'digraph G {\nnode [shape=box];\nedge [color="' + SLIGHTLY_TRANSPARENT + '"];\n'

        costs = self.pobjs[l]['costs']

        with open('jobnames.json', 'r') as fp:
            job_names = json.load(fp)
        #jobNames = [ [ ''.join(random.choice(string.ascii_lowercase) for i in range(8)) for j in range(self.numJobs) ] for l in range(NUM_PROJECTS) ]

        for j in range(self.num_jobs):
            qincr_descr = 'q=('+','.join([ str(qplus) for qplus in self.pobjs[l]['quality_improvements'][j]])+')'
            descr = 'd=' + str(self.durations[l][j]) + ', k=' + str(self.demands[l][0][j]) + ', c=' + str(int(costs[j])) + ',<br/>' + qincr_descr
            viz_str += str(j + 1) + '[label=<AG ' + str(j + 1) + '<br />' + job_names[l][j] + '<br/><font point-size="8">' + descr + '</font>>] ;\n'
            if not hide_result and j not in self.executed_jobs[l]:
                viz_str += str(j + 1) + ' [color="' + VERY_TRANSPARENT + '",fontcolor="' + VERY_TRANSPARENT + '"];\n'

        # precedence
        log('Writing precedence relation')

        viz_str = self.build_precedence_edges(l, viz_str)

        # decisions
        log('Writing decisions')

        viz_str = self.build_decision_clusters(l, viz_str)

        # conditionals
        log('Writing conditional activities')

        cluster_ix = self.num_decisions

        for pred in range(self.num_jobs):
            for succ in range(self.num_jobs):
                if self.pobjs[l]['job_causing_job'][pred][succ]:
                    viz_str += 'subgraph cluster_' + str(cluster_ix + 1) + ' {\n' + str(
                        succ + 1) + '\nlabel=<<font point-size="10">Bedingt durch ' + str(pred + 1) + '</font>>;\n}\n'
                    cluster_ix += 1

        # colorize mandatory jobs
        log('Colorize mandatory jobs')
        mandatory_jobs = self.pobjs[l]['mandatory_activities']
        for j in range(self.num_jobs):
            is_mandatory = j + 1 in mandatory_jobs
            border_color = 'blue' if is_mandatory else 'black'
            penwidth = 1.5 if is_mandatory else 1
            if j in self.executed_jobs[l] or hide_result:
                viz_str += str(j + 1) + ' [fontcolor="' + brightness_to_font_color(
                    self.job_colors[l][j + 1]['brightness']) + '",color=' + border_color + ',fillcolor="' + \
                          self.job_colors[l][j + 1]['color'] + '",style=filled,penwidth=' + str(penwidth) + ']\n'

        viz_str += '}\n'

        return viz_str


def main():
    sv = StructureVisualizer()
    seq_infix = ('Sequentiell' if sequential else '')
    for l in range(NUM_PROJECTS):
        infn = 'forgviz' + str(l + 1) + seq_infix + '.dot'
        with open(infn, 'w') as fp:
            fp.write(sv.build_graphviz_code(l))
        outfn = 'forgviz' + str(l + 1) + seq_infix + '.pdf'
        os.system('dot ' + infn + ' -o ' + outfn + ' -Tpdf -Gmargin=0')
        shutil.move(outfn, OUT_DIR_PREFIX + outfn)
        os.remove(infn)


if __name__ == '__main__':
    main()
