import numpy as np

import utils
from flexible_project import decorate_project, decorate_quality_attributes

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
    'precedence_relation': [(0, 1), (0, 2), (1, 3), (1, 4), (0, 5), (3, 5), (2, 4), (2, 8), (4, 6), (4, 7), (5, 9), (6, 9), (7, 9), (8, 9)]}

o1 = {
    'zmax': [5, 15],
    'kappa': [4, 2]}

q1 = {
    'nqlevels': 3,
    'nqattributes': 2,
    'costs': [0, 5, 3, 2, 1, 7, 10, 6, 1, 0],
    'base_qualities': [20, 0],  # FIXME: Change signature
    'quality_improvements': [{
        4: 10,
        5: 12,
        7: 15,
        8: 5,
        9: 8}, {
        4: 0,
        5: 10,
        7: 15,
        8: 0,
        9: 20}],
    'qlevel_requirement': np.matrix('40 35 30; 20 15 10'),
    'revenue_periods': [12, 13, 14],
    'revenues': np.matrix('50 49 48; 40 39 38; 30 29 28')}


def example_project_with_quality():
    decorated_p1 = decorate_project(p1)
    return utils.ObjectFromDict(**{**decorated_p1, **decorate_quality_attributes(decorated_p1, q1)})


def example_project_with_overtime():
    decorated_p1 = decorate_project(p1)
    return utils.ObjectFromDict(**{**decorated_p1, **o1})
