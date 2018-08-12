import numpy as np

import utils
from flexible_project import decorate_project, canonical_choice, decorate_quality_attributes
from mip import solve_with_gurobi
import exceltojsonfiles
import resultscheduletojson

p1 = {
    'njobs': 10,
    'renewables': [0],
    'non_renewables': [1],
    'durations': [0, 3, 4, 3, 5, 6, 4, 2, 2, 0],
    'demands': np.matrix('0 3 7 5 2 8 6 5 4 0; 0 2 5 8 3 5 3 9 3 0').transpose(),
    'capacities': [11, 38],
    'decision_sets': [[3, 4], [6, 7]],
    'decision_causing_jobs': [0, 4],
    'conditional_jobs': [(3, 8)],
    'precedence_relation': [(0, 1), (0, 2), (1, 3), (1, 4), (0, 5), (3, 5), (2, 4), (2, 8), (4, 6), (4, 7), (5, 9),
                            (6, 9), (7, 9), (8, 9)]
}

o1 = {
    'zmax': [5, 15],
    'kappa': [4, 2]
}

q1 = {
    'nqlevels': 3,
    'nqattributes': 2,
    'costs': [0, 5, 3, 2, 1, 7, 10, 6, 1, 0],
    'base_qualities': [20, 0],
    # FIXME: Change signature
    'quality_improvements': [
        {4: 10, 5: 12, 7: 15, 8: 5, 9: 8},
        {4: 0, 5: 10, 7: 15, 8: 0, 9: 20}
    ],
    'qlevel_requirement': np.matrix('40 35 30; 20 15 10'),
    'revenue_periods': [12, 13, 14],
    'revenues': np.matrix('50 49 48; 40 39 38; 30 29 28')
}


def example_project_with_quality():
    decorated_p1 = decorate_project(p1)
    return utils.ObjectFromDict(**{**decorated_p1, **decorate_quality_attributes(decorated_p1, q1)})


def example_project_with_overtime():
    decorated_p1 = decorate_project(p1)
    return utils.ObjectFromDict(**{**decorated_p1, **o1})


def convert_quality_attributes(p):
    return {
        'nqlevels': len(p['revenues']),
        'nqattributes': len(p['base_qualities']),
        'costs': p['costs'],
        'base_qualities': p['base_qualities'],
        'quality_improvements': np.matrix(p['quality_improvements']),
        'qlevel_requirement': np.matrix(p['qlevel_requirement']),
        'revenue_periods': p['revenue_periods'],
        'revenues': np.matrix(p['revenues'])
    }


def convert_project_to_simple_format(p):
    jobs = range(len(p['jobs']))
    decisions = range(len(p['job_in_decision'][0]))
    jcj = np.matrix(p['job_causing_job'])
    prec = np.matrix(p['precedence'])
    demands = np.matrix([[p['demands'][0][j], p['demands_nonrenewable'][0][j]] for j in jobs])
    quality_attrs = convert_quality_attributes(p) if 'base_qualities' in p else {}
    oc_attrs = { 'zmax': p['zmax'], 'kappa': p['kappa'] } if 'zmax' in p else {}
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
        **quality_attrs,
        **oc_attrs
    }


def convert_results_to_peculiar_json(sts_arr):
    return [{str(j): float(stj) for j, stj in enumerate(sts)} for sts in sts_arr]


def main():
    projects = exceltojsonfiles.convert_excel_to_project_jsons('Input.xlsx')
    pobjs = [utils.ObjectFromDict(**decorate_quality_attributes(decorate_project(convert_project_to_simple_format(p)))) for p in projects]

    results = solve_with_gurobi(pobjs)
    resultscheduletojson.write_schedule_objs_to_file(convert_results_to_peculiar_json(results), "ergebnisse.json")

    #resultsSequential = solve_with_gurobi(pobjs, True)
    #resultscheduletojson.write_schedule_objs_to_file(convert_results_to_peculiar_json(resultsSequential), "ergebnisseSequentiell.json")

    # abs_path = "C:\\Users\\a.schnabel\\Seafile\\Dropbox\\Scheduling\\InstanzenLuise\\15\\"
    # p = utils.ObjectFromDict(**decorate_project(p1))
    # p = project_from_disk(abs_path + 'Modellendogen1_1.DAT')  # 'Modellendogen0002.DAT')

    # p = example_project_with_quality()
    # p = example_project_with_overtime()

    # al = p.topOrder
    # choices = canonical_choice(p)

    # al = [0, 2, 5, 3, 1, 7, 4, 6, 8, 9]
    # choices = {0: 1, 1: 0}

    # result = serial_sgs(p, choices, al)
    # print_result(result)
    # solve_with_gurobi(p)


if __name__ == '__main__':
    main()
