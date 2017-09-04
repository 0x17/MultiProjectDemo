import codecs
from collections import OrderedDict
import json


def right_part(s):
    remove_suffixes = ['R', 'N']
    parts = s.split(':')
    for suffix in remove_suffixes:
        if parts[-1].strip().endswith(suffix):
            parts[-1] = parts[-1].replace(suffix, '')
    return int(parts[1])


prefix_to_object_key = {
    'projects': 'numProjects',
    'jobs (incl. supersource/sink )': 'numJobsTotal',
    '  - renewable': 'numRenewable',
    '  - nonrenewable': 'numNonRenewable',
    'Entscheidungen': 'numDecisions',
    'Bedingungen': 'numConditions'
}


def parse_pairs(obj, line):
    for prefix, object_key in prefix_to_object_key.items():
        if line.startswith(prefix):
            obj[object_key] = right_part(line)


def index_of_line_starting_with(lines, prefix):
    if prefix is None:
        return len(lines)
    else:
        ctr = 0
        for line in lines:
            if line.startswith(prefix):
                return ctr
            ctr += 1


def pre_processing(obj, lines):
    for line in lines:
        parse_pairs(obj, line)


def parse_project_infos(obj, sublines):
    for l in range(obj['numProjects']):
        parts = sublines[l].split()
        pobj = obj['projects'][l]
        pobj['numJobs'] = int(parts[1]) + 2
        pobj['deadline'] = int(parts[3])
        pobj['delaycost'] = float(parts[4])


def job_num_to_project_num(obj, j):
    njobs = obj['projects'][0]['numJobs']
    assert (0 < j < obj['numProjects'] * (njobs - 2) + 2)
    return int((j - 2) / (njobs - 2))


def get_num_jobs_from_sublines(obj, sublines):
    return int(float(len(sublines) - 2) / float(obj['numProjects'])) + 2


def minus_offset(l, j, num_jobs=10):
    if j == -10: return 9
    return j - 1 - (num_jobs - 2) * l


def parse_precedence_relations(obj, sublines):
    numJobs = get_num_jobs_from_sublines(obj, sublines)
    dummy_end_jobnum = sublines[-1].split()[1]

    def translate_dummy(s):
        return s.replace(dummy_end_jobnum, '-10')

    for l in range(obj['numProjects']):
        obj['projects'][l]['successors'] = {}
        succs = obj['projects'][l]['successors']
        for j in range(numJobs):
            if j == 0:
                succs[j] = [minus_offset(l, int(jprimestr)) for jprimestr in translate_dummy(sublines[0]).split()[4:] if job_num_to_project_num(obj, int(jprimestr)) == l or jprimestr == '-10']
            elif j == numJobs - 1:
                succs[j] = []
            else:
                succs[j] = [minus_offset(l, int(jprimestr)) for jprimestr in translate_dummy(sublines[j + l * 8]).split()[4:]]


def parse_requests_durations(obj, sublines):
    numJobs = get_num_jobs_from_sublines(obj, sublines)

    def subline_for_job_in_proj(j, l):
        ix = j + l * (numJobs - 2)
        return sublines[ix]

    for l in range(obj['numProjects']):
        pobj = obj['projects'][l]
        pobj['durations'] = []
        pobj['demands'] = []
        for j in range(numJobs):
            if j == 0 or j == numJobs - 1:
                pobj['durations'].append(0)
                pobj['demands'].append([0, 0])
            else:
                jobline_parts = subline_for_job_in_proj(j, l).split()
                pobj['durations'].append(int(jobline_parts[3]))
                pobj['demands'].append([int(demand) for demand in jobline_parts[4:]])


def parse_availabilities(obj, sublines):
    parts = sublines[0].split()
    obj['Kr'] = [int(parts[ix]) for ix in range(obj['numRenewable'])]
    obj['Kn'] = [int(parts[ix]) for ix in range(obj['numRenewable'], obj['numRenewable'] + obj['numNonRenewable'])]


def parse_decisions(obj, sublines):
    for l in range(obj['numProjects']):
        pobj = obj['projects'][l]
        pobj['numDecisions'] = 0
        pobj['jobCausingDecision'] = {}
        pobj['jobsInDecision'] = {}

    for subline in sublines:
        parts = subline.split()
        dn = int(parts[0]) - 1
        l = int(parts[1]) - 1
        pobj = obj['projects'][l]
        pobj['numDecisions'] += 1
        pobj['jobCausingDecision'][str(minus_offset(l, int(parts[2])))] = dn
        pobj['jobsInDecision'][dn] = [minus_offset(l, int(j)) for j in parts[4:]]


def parse_conditions(obj, sublines):
    for l in range(obj['numProjects']):
        pobj = obj['projects'][l]
        pobj['jobCausingJob'] = {}

    for subline in sublines:
        parts = subline.split()
        l = int(parts[1]) - 1
        pobj = obj['projects'][l]
        pobj['jobCausingJob'][str(minus_offset(l, int(parts[2])))] = minus_offset(l, int(parts[4]))


def parse_json_from_psplib(fn):
    caption_to_action_offset = OrderedDict([
        ('PROJECT INFORMATION:', (parse_project_infos, 2)),
        ('PRECEDENCE RELATIONS:', (parse_precedence_relations, 2)),
        ('REQUESTS/DURATIONS:', (parse_requests_durations, 3)),
        ('RESOURCEAVAILABILITIES:', (parse_availabilities, 2)),
        ('Entscheidungen', (parse_decisions, 2)),
        ('Bedingungen', (parse_conditions, 2))])
    captions = list(caption_to_action_offset.keys())

    with codecs.open(fn, 'r', 'iso-8859-1') as fp:
        lines = fp.readlines()
        obj = {}
        pre_processing(obj, lines)
        obj['projects'] = [{'index': l} for l in range(obj['numProjects'])]
        ctr = 0
        for line in lines:
            for caption, action_offset in caption_to_action_offset.items():
                if line.startswith(caption):
                    next_caption = None if caption == captions[-1] else captions[captions.index(caption) + 1]
                    action_offset[0](obj, lines[
                                          ctr + action_offset[1]: index_of_line_starting_with(lines, next_caption) - 1])
            ctr += 1
        return obj


def main():
    obj = parse_json_from_psplib('Instanzen_Begehung/Modellendogen0001.DAT')
    with open('myobject.json', 'w') as fp:
        fp.write(json.dumps(obj, sort_keys=True, indent=4))


if __name__ == '__main__': main()
