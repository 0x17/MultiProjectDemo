from collections import OrderedDict
import json


def right_part(s): return int(s.split(':')[1])


def parse_pairs(obj, line):
    prefix_to_object_key = {
        'projects': 'numProjects',
        'jobs (incl. supersource/sink )': 'numJobsTotal',
        ' - renewable': 'numRenewable',
        ' - nonrenewable': 'numNonRenewable',
        'Entscheidungen': 'numDecisions',
        'Bedingungen': 'numConditions'
    }
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
        pobj['numJobs'] = parts[1] + 2
        pobj['deadline'] = parts[3]
        pobj['delaycost'] = parts[4]


def job_num_to_project_num(obj, j):
    njobs = obj['projects'][0]['numJobs']
    assert (0 < j < obj['numProjects'] * (njobs - 2) + 2)
    return (j - 1) % (njobs - 2)


def get_num_jobs_from_sublines(obj, sublines):
    return int(float(len(sublines) - 2) / float(obj['numProjects'])) + 2


def parse_precedence_relations(obj, sublines):
    numJobs = get_num_jobs_from_sublines(obj, sublines)

    def minus_offset(l, j):
        return (j % (numJobs - 2)) + 1

    for l in range(obj['numProjects']):
        obj['projects'][l]['successors'] = {}
        succs = obj['projects'][l]['successors']
        for j in range(numJobs):
            if j == 0:
                succs[j] = [minus_offset(l, jprime) for jprime in sublines[0].split()[4:] if
                            job_num_to_project_num(obj, jprime) == l]
            elif j == numJobs - 1:
                succs[j] = []
            else:
                succs[j] = [minus_offset(l, jprime) for jprime in sublines[1 + j * l].split()[4:]]


def parse_requests_durations(obj, sublines):
    numJobs = get_num_jobs_from_sublines(obj, sublines)
    nr = obj['numRenewable']
    nnr = obj['numNonRenewable']
    for l in range(obj['numProjects']):
        pobj = obj['projects'][l]
        pobj['durations'] = []
        for j in range(numJobs):
            if j == 0 or j == numJobs - 1:
                pobj['durations'].append(0)
                pobj['demands'].append([0, 0])
            else:
                jobline_parts = sublines[1 + j * l].split()
                pobj['durations'].append(jobline_parts[3])
                pobj['demands'].append(jobline_parts[4:4 + nr + nnr])


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
        dn = int(parts[0])
        l = int(parts[1])
        pobj = obj['projects'][l]
        pobj['numDecisions'] += 1
        pobj['jobCausingDecision'][parts[2]] = dn
        pobj['jobsInDecision'][dn] = parts[4:]


def parse_conditions(obj, sublines):
    for l in range(obj['numProjects']):
        pobj = obj['projects'][l]
        pobj['numConditions'] = 0
        pobj['jobCausingJob'] = {}

    for subline in sublines:
        parts = subline.split()
        cn = int(parts[0])
        l = int(parts[1])
        pobj = obj['projects'][l]
        pobj['numConditions'] += 1
        pobj['jobCausingJob'][parts[2]] = parts[4]


def parse_json_from_psplib(fn):
    caption_to_action_offset = OrderedDict([
        ('PROJECT_INFORMATION:', (parse_project_infos, 2)),
        ('PRECEDENCE RELATIONS:', (parse_precedence_relations, 2)),
        ('REQUESTS/DURATIONS:', (parse_requests_durations, 3)),
        ('RESOURCEAVAILABILITIES:', (parse_availabilities, 2)),
        ('Entscheidungen', (parse_decisions, 2)),
        ('Bedingungen', (parse_conditions, 2))])
    captions = list(caption_to_action_offset.keys())

    with open(fn) as fp:
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


obj = parse_json_from_psplib('Instanzen_Begehung/Modellendogen0001.DAT')

with open('myobject.json', 'w') as fp:
    fp.write(json.dumps(obj, sort_keys=True, indent=4))

# TODO: fill_excel_with_obj(obj, 'NewInput.xlsx')

