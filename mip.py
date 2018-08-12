from gurobipy import *
import numpy as np
import datetime


def write_solvetime(t, fn='solvetime.txt'):
    with open(fn, 'w') as fp:
        fp.write(f'{t}\n')


def assert_equal_for_projects(projects, attrs):
    for attr in attrs:
        print(f'Assertion for attribute: {attr}')
        assert (all(getattr(p, attr) == getattr(projects[0], attr) for p in projects))

def dict_from_attrs(obj, keys):
    return { key: getattr(obj, key) for key in keys }


def solve_with_gurobi(projects, sequential=False):
    def constraints(name_constr_pairs):
        for name, cstr in name_constr_pairs:
            model.addConstr(cstr, name)

    try:
        quality_consideration = hasattr(projects[0], 'qlevels')
        overtime_consideration = hasattr(projects[0], 'zmax')

        model = Model("rcmpsp-ps" + ("-q" if quality_consideration else "") + ("-oc" if overtime_consideration else ""))

        bigM = 99999999

        model.params.threads = 0
        model.params.mipgap = 0
        model.params.timelimit = GRB.INFINITY
        model.params.displayinterval = 5

        common_keys = ['renewables', 'non_renewables', 'capacities'] + (['qlevels', 'kappa'] if quality_consideration else [])
        assert_equal_for_projects(projects, common_keys)
        globals = dict_from_attrs(projects[0], common_keys)
        maxlen = max(len(p.periods) for p in projects)
        globals['periods'] = next(p.periods for p in projects if len(p.periods) == maxlen)

        x = [np.matrix([[model.addVar(0.0, 1.0, 0.0, GRB.BINARY, f'x_{l}_{j}_{t}') for t in p.periods] for j in p.jobs]) for l, p in enumerate(projects)]
        z = np.matrix([[model.addVar(0.0, 1.0, 0.0, GRB.BINARY, f'z{r}_{t}') for t in globals['periods']] for r in globals['renewables']]) if overtime_consideration else None

        delay = [model.addVar(0.0, GRB.INFINITY, 0.0, GRB.CONTINUOUS, f'delay_{l}') for l in range(len(projects))] if not quality_consideration else None

        def finish_periods_if_active_in(p, j, t):
            return range(t, min(t + p.durations[j], p.T))

        if quality_consideration:
            y = [np.matrix([[model.addVar(0.0, 1.0, 0.0, GRB.BINARY, f'y_{l}_{level}_{t}') for t in globals['periods']] for level in globals['qlevels']]) for l, p in enumerate(projects)]

            overtime_costs = 0 if not overtime_consideration else quicksum(globals['kappa'][r] * z[r, t] for r in globals['renewables'] for t in globals['periods'])
            model.setObjective(
                quicksum(p.u[l, t] * y[l][level, t] for l, p in enumerate(projects) for t in p.periods for level in globals['qlevels']) -
                quicksum(p.costs[j] * quicksum(x[l][j, t] for t in p.periods) for l, p in enumerate(projects) for j in p.actual_jobs) - overtime_costs, GRB.MAXIMIZE)

            constraints((f'qlevel_reached_{o}_{l}',
                         p.base_qualities[o] + quicksum(p.quality_improvements[j,o] * quicksum(x[l][j, t] for t in p.periods) for j in p.actual_jobs) >=
                         p.qlevel_requirement[o, l] -
                         bigM * (1 - quicksum(y[l][level, t] for t in p.periods))) for l, p in enumerate(projects) for o in p.qattributes for level in globals['qlevels'])

            constraints((f'sync_x_y_{l}_{t}', quicksum(y[l][level, t] for level in p.qlevels) == x[l][p.lastJob, t]) for l, p in enumerate(projects) for t in p.periods)

        constraints((f'each_once_{l}_{j}', quicksum(x[l][j, t] for t in p.periods) == 1) for l, p in enumerate(projects) for j in p.mandatory_jobs)
        constraints((f'decision_triggered_{l}_{e}',
                     quicksum(x[l][j, t] for j in p.decision_sets[e] for t in p.periods) == quicksum(x[l][p.decision_causing_jobs[e], t] for t in p.periods)) for l, p in enumerate(projects) for e in p.decisions)
        constraints((f'conditional_jobs_{l}_{e}_{j}_{i}',
                     quicksum(x[l][i, t] for t in p.periods) == quicksum(x[l][j, t] for t in p.periods)) for l, p in enumerate(projects) for e in p.decisions for j in p.decision_sets[e] for i in p.caused_by[j])
        constraints((f'precedence_{l}_{i}_{j}',
                     quicksum(t * x[l][i, t] for t in p.periods) <= quicksum((t - p.durations[j]) * x[l][j, t] for t in p.periods) + p.T * (1 - quicksum(x[l][j, t] for t in p.periods))) for l, p in enumerate(projects) for j in p.jobs for i in p.preds[j])
        constraints((f'renewable_capacity_{r}_{t}',
                     quicksum(p.demands[j, r] * quicksum(x[l][j, tau] for tau in finish_periods_if_active_in(p, j, t)) for l, p in enumerate(projects) for j in p.actual_jobs) <= globals['capacities'][r] + (z[r,t] if overtime_consideration else 0)) for r in globals['renewables'] for t in globals['periods'])
        constraints((f'nonrenewable_capacity_{r}',
                     quicksum(p.demands[j, r] * quicksum(x[l][j, t] for t in p.periods) for l, p in enumerate(projects) for j in p.actual_jobs) <= globals['capacities'][r]) for r in globals['non_renewables'])

        if not quality_consideration:
            constraints((f'sync_delay_{l}', quicksum(t * x[l][p.lastJob,t] for t in p.periods) - p.deadline <= delay[l]) for l, p in enumerate(projects))

        def obj_with_delay_costs(delaycosts):
            model.setObjective(quicksum(delay[l] * delaycosts[l] for l in range(len(projects))), GRB.MINIMIZE)

        if quality_consideration:
            model.update()
            model.optimize()
            write_solvetime(model.runtime)
        else:
            delay_costs = [p.delaycost for p in projects]
            if not sequential:
                obj_with_delay_costs(delay_costs)
                model.update()
                model.write('mymodel.lp')
                model.optimize()
                write_solvetime(model.runtime)
            else:
                def fix_schedule_for_proj_to_result(l):
                    p = projects[l]
                    for j in p.jobs:
                        for t in p.periods:
                            val = x[l][j, t].x
                            x[l][j, t].lb = val
                            x[l][j, t].ub = val

                tstart = datetime.datetime.now()
                obj_with_delay_costs([delay_costs[0], 0, 0])
                model.update()
                model.optimize()
                fix_schedule_for_proj_to_result(0)
                obj_with_delay_costs([delay_costs[0], delay_costs[1], 0])
                model.update()
                model.optimize()
                fix_schedule_for_proj_to_result(1)
                obj_with_delay_costs(delay_costs)
                model.update()
                model.optimize()
                tdelta = datetime.datetime.now() - tstart
                write_solvetime(int(tdelta.total_seconds() * 1000), 'solvetimeSequentiell.txt')

        implemented_jobs = []
        sts = []

        if model.status != GRB.Status.OPTIMAL:
            print(f'Unable to obtain optimal solution. Status code = {model.status}')

        for (l, p) in enumerate(projects):
            if model.status == GRB.Status.OPTIMAL:
                implemented_jobs.append([j for j in p.jobs if any(x[l][j, t].x > 0.0 for t in p.periods)])
                sts.append([next(t for t in p.periods if x[l][j, t].x > 0.0)-p.durations[j] if j in implemented_jobs[l] else -1 for j in p.jobs])
            else:
                sts.append([0] * p.njobs)

        # print(f'Optimal solution for project {l}: sts={sts}, impl_jobs={implemented_jobs}')
        return sts

    except GurobiError as e:
        print(e)
