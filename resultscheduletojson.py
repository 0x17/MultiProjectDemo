import json

num_jobs_per_project = 10
num_projects = 3


def schedule_obj_for_project(lines, project_index):
    job_ctr = 1
    start_offset = num_jobs_per_project * project_index
    sts = {}
    for line in lines[start_offset:start_offset + num_jobs_per_project]:
        sts[job_ctr] = float(line.strip())
        job_ctr += 1
    return sts


def schedule_objs_from_file(fn):
    with open(fn, 'r') as fp:
        lines = fp.readlines()
        return [schedule_obj_for_project(lines, ix) for ix in range(num_projects)]


def write_schedule_objs_to_file(objs, fn):
    with open(fn, 'w') as fp:
        fp.write(json.dumps(objs, sort_keys=True, indent=4))


if __name__ == '__main__':
    write_schedule_objs_to_file(schedule_objs_from_file('ergebnisse.txt'), 'ergebnisse.json')
    write_schedule_objs_to_file(schedule_objs_from_file('ergebnisseSequentiell.txt'), 'ergebnisseSequentiell.json')
