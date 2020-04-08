import numpy as np

import utils
from flexible_project import decorate_project, decorate_quality_attributes
from mip import solve_with_gurobi
import exceltojsonfiles
import resultscheduletojson
import sys
import json


def convert_quality_attributes(p):
    return {
        'nqlevels': len(p['revenues']),
        'nqattributes': len(p['base_qualities']),
        'costs': p['costs'],
        'base_qualities': p['base_qualities'],
        'quality_improvements': np.matrix(p['quality_improvements']),
        'qlevel_requirement': np.matrix(p['qlevel_requirement']),
        'revenue_periods': p['revenue_periods'],
        'revenues': np.matrix(p['revenues'])}


def convert_project_to_simple_format(p):
    jobs = range(len(p['jobs']))
    decisions = range(len(p['job_in_decision'][0]))
    jcj = np.matrix(p['job_causing_job'])
    prec = np.matrix(p['precedence'])
    demands = np.matrix([[p['demands'][0][j], p['demands_nonrenewable'][0][j]] for j in jobs])
    quality_attrs = convert_quality_attributes(p) if 'base_qualities' in p else {}
    oc_attrs = {
        'zmax': p['zmax'],
        'kappa': p['kappa']} if 'zmax' in p else {}
    return {
        'njobs': len(jobs),
        'delaycost': p['delaycost'],
        'renewables': [0],
        'non_renewables': [1],
        'durations': p['durations'],
        'demands': demands,
        'capacities': p['capacities'],
        'decision_sets': [[j for j in jobs if p['job_in_decision'][j][e]] for e in decisions],
        'decision_causing_jobs': [next(j for j in jobs if p['job_activating_decision'][j][e]) for e in decisions],
        'conditional_jobs': [(i, j) for i in jobs for j in jobs if jcj[i, j]],
        'precedence_relation': [(i, j) for i in jobs for j in jobs if prec[i, j]],
        'deadline': p['deadline'],
        'mandatory_activities': p['mandatory_activities'], **quality_attrs, **oc_attrs}


def convert_results_to_peculiar_json(sts_arr):
    return [{str(j): float(stj) for j, stj in enumerate(sts)} for sts in sts_arr]


def projects_from_disk(nprojects):
    def read_proj(l):
        with open(f'Projekt{l + 1}.json') as fp:
            return json.load(fp)

    return [read_proj(l) for l in range(nprojects)]


def main():
    projects = projects_from_disk(3) if len(sys.argv) > 1 and sys.argv[1] == 'no_excel' else exceltojsonfiles.convert_excel_to_project_jsons('Input.xlsx')
    proj_objs = [utils.ObjectFromDict(**decorate_quality_attributes(decorate_project(convert_project_to_simple_format(p)))) for p in projects]

    results = solve_with_gurobi(proj_objs)
    resultscheduletojson.write_schedule_objs_to_file(convert_results_to_peculiar_json(results), "ergebnisse.json")

    results_sequential = solve_with_gurobi(proj_objs, True)
    resultscheduletojson.write_schedule_objs_to_file(convert_results_to_peculiar_json(results_sequential), "ergebnisseSequentiell.json")


if __name__ == '__main__':
    main()
