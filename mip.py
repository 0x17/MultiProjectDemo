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
    return {key: getattr(obj, key) for key in keys}


def compute_solution_attrs(projects, sts):
    nprojs, njobs = len(sts), len(sts[0])

    def compute_overtime_costs():
        overtime_costs = 0
        max_periods = max(projects, key=lambda p: len(p.periods)).periods
        for t in max_periods:
            for r in projects[0].renewables:
                cum_demand = 0
                for l, p in enumerate(projects):
                    for j in projects[0].jobs:
                        stj = sts[l][j]
                        if stj != -1 and stj < t <= stj + p.durations[j]:
                            cum_demand += p.demands[j, r]
                overtime_costs += projects[0].kappa[r] * max(cum_demand - projects[0].capacities[r], 0)
        return overtime_costs

    def reached_quality_level(p, psts):
        reached_values = [sum(p.quality_improvements[j, qattr] for j in p.jobs if psts[j] != -1) + p.base_qualities[qattr] for qattr in p.qattributes]
        return next(qlevel for qlevel in p.qlevels if all(reached_values[qattr] >= p.qlevel_requirement[qattr, qlevel] for qattr in p.qattributes))

    def attrs_for_project(l):
        p, psts = projects[l], sts[l]
        makespan = max(psts)
        job_costs = sum(p.costs[j] for j in range(njobs) if psts[j] != -1)
        rql = reached_quality_level(p, psts)
        print(f'The project {l} has reached quality level {rql}...')
        revenue = p.u[rql, makespan]
        return dict(makespan=makespan, job_costs=job_costs, revenue=revenue)

    project_specific = [attrs_for_project(l) for l in range(nprojs)]
    overtime_cost = compute_overtime_costs()
    profit = sum(project_specific[l]['revenue'] - project_specific[l]['job_costs'] for l in range(len(projects))) - overtime_cost
    return dict(overtime_cost=overtime_cost, profit=profit, project_specific=project_specific)


def solve_with_gurobi(projects, sequential=False):
    def constraints(name_constr_pairs):
        for name, cstr in name_constr_pairs:
            model.addConstr(cstr, name)

    try:
        quality_consideration = hasattr(projects[0], 'qlevels')
        overtime_consideration = hasattr(projects[0], 'zmax')

        model = Model("rcmpsp-ps" + ("-q" if quality_consideration else "") + ("-oc" if overtime_consideration else ""))

        bigM = max(p.qlevel_requirement[o, level] for p in projects for o in p.qattributes for level in p.qlevels)

        model.params.threads = 0
        model.params.mipgap = 0
        model.params.timelimit = GRB.INFINITY
        model.params.displayinterval = 5

        common_keys = ['renewables', 'non_renewables', 'capacities', 'zmax'] + (['qlevels', 'kappa'] if quality_consideration else [])
        assert_equal_for_projects(projects, common_keys)
        globals = dict_from_attrs(projects[0], common_keys)
        maxlen = max(len(p.periods) for p in projects)
        globals['periods'] = next(p.periods for p in projects if len(p.periods) == maxlen)

        x = [np.matrix([[model.addVar(0.0, 1.0, 0.0, GRB.BINARY, f'x_{l}_{j}_{t}') for t in p.periods] for j in p.jobs]) for l, p in enumerate(projects)]
        z = np.matrix([[model.addVar(0.0, globals['zmax'][r], 0.0, GRB.CONTINUOUS, f'z{r}_{t}') for t in globals['periods']] for r in globals['renewables']]) if overtime_consideration else None

        delay = [model.addVar(0.0, GRB.INFINITY, 0.0, GRB.CONTINUOUS, f'delay_{l}') for l in range(len(projects))] if not quality_consideration else None

        assert all(p.lastJob in p.mandatory_jobs for p in projects), 'Last job must be mandatory!'

        def finish_periods_if_active_in(p, j, t):
            return range(t, min(t + p.durations[j], p.T))

        if quality_consideration:
            y = [np.matrix([[model.addVar(0.0, 1.0, 0.0, GRB.BINARY, f'y_{l}_{level}_{t}') for t in globals['periods']] for level in globals['qlevels']]) for l, p in enumerate(projects)]

            constraints((f'qlevel_reached_{o}_{l}_{level}', p.base_qualities[o] + quicksum(p.quality_improvements[j, o] * quicksum(x[l][j, t] for t in p.periods) for j in p.actual_jobs) >= p.qlevel_requirement[o, level] - bigM * (1 - quicksum(y[l][level, t] for t in p.periods))) for l, p in enumerate(projects) for o in p.qattributes for level in globals['qlevels'])

            constraints((f'sync_x_y_{l}_{t}', quicksum(y[l][level, t] for level in p.qlevels) == x[l][p.lastJob, t]) for l, p in enumerate(projects) for t in p.periods)

        constraints((f'each_once_{l}_{j}', quicksum(x[l][j, t] for t in p.periods) == 1) for l, p in enumerate(projects) for j in [k - 1 for k in p.mandatory_activities])
        constraints((f'decision_triggered_{l}_{e}', quicksum(x[l][j, t] for j in p.decision_sets[e] for t in p.periods) == quicksum(x[l][p.decision_causing_jobs[e], t] for t in p.periods)) for l, p in enumerate(projects) for e in p.decisions)

        # return list of conditional jobs triggered by job j
        def causes(p, j):
            return [i for i, cb in enumerate(p.caused_by) if j in cb]

        constraints((f'conditional_jobs_{l}_{e}_{j}_{i}', quicksum(x[l][i, t] for t in p.periods) == quicksum(x[l][j, t] for t in p.periods)) for l, p in enumerate(projects) for e in p.decisions for j in p.decision_sets[e] for i in causes(p, j))

        constraints((f'precedence_{l}_{i}_{j}', quicksum(t * x[l][i, t] for t in p.periods) <= quicksum((t - p.durations[j]) * x[l][j, t] for t in p.periods) + p.T * (1 - quicksum(x[l][j, t] for t in p.periods))) for l, p in enumerate(projects) for j in p.jobs for i in p.preds[j])
        constraints((f'renewable_capacity_{r}_{t}', quicksum(p.demands[j, r] * quicksum(x[l][j, tau] for tau in finish_periods_if_active_in(p, j, t)) for l, p in enumerate(projects) for j in p.actual_jobs) <= globals['capacities'][r] + (z[r, t] if overtime_consideration else 0)) for r in globals['renewables'] for t in globals['periods'])
        constraints((f'nonrenewable_capacity_{r}', quicksum(p.demands[j, r] * quicksum(x[l][j, t] for t in p.periods) for l, p in enumerate(projects) for j in p.actual_jobs) <= globals['capacities'][r]) for r in globals['non_renewables'])

        if not quality_consideration:
            constraints((f'sync_delay_{l}', quicksum(t * x[l][p.lastJob, t] for t in p.periods) - p.deadline <= delay[l]) for l, p in enumerate(projects))

        def obj_with_delay_costs(delaycosts):
            model.setObjective(quicksum(delay[l] * delaycosts[l] for l in range(len(projects))), GRB.MINIMIZE)

        def enumerate_active(active_projects):
            return [(l, p) for l, p in enumerate(projects) if active_projects[l]]

        def obj_with_quality_consideration(active_projects):
            # add_derived_expression_variables(model, enumerate_active, x, y, z, active_projects)
            overtime_costs = 0 if not overtime_consideration else quicksum(globals['kappa'][r] * z[r, t] for r in globals['renewables'] for t in globals['periods'])
            revenue = quicksum(p.u[level, t] * y[l][level, t] for l, p in enumerate_active(active_projects) for t in p.periods for level in globals['qlevels'])
            job_costs = quicksum(p.costs[j] * quicksum(x[l][j, t] for t in p.periods) for l, p in enumerate_active(active_projects) for j in p.actual_jobs)
            model.setObjective(revenue - job_costs - overtime_costs, GRB.MAXIMIZE)

        # used in sequential scheduling
        def fix_schedule_for_proj_to_result(l):
            p = projects[l]
            for j in p.jobs:
                for t in p.periods:
                    val = x[l][j, t].x
                    x[l][j, t].lb = val
                    x[l][j, t].ub = val
            if quality_consideration:
                for level in p.qlevels:
                    for t in p.periods:
                        val = y[l][level, t].x
                        y[l][level, t].lb = val
                        y[l][level, t].ub = val

        def solve_integrated_quality():
            obj_with_quality_consideration([True] * 3)
            model.update()
            # model.write('mymodel.lp')
            model.optimize()
            # show_internal_values(projects, model, x)
            write_solvetime(model.runtime)

        def solve_sequential_quality():
            tstart = datetime.datetime.now()
            obj_with_quality_consideration([True, False, False])
            model.update()
            model.optimize()
            fix_schedule_for_proj_to_result(0)
            obj_with_quality_consideration([True, True, False])
            model.update()
            model.optimize()
            fix_schedule_for_proj_to_result(1)
            obj_with_quality_consideration([True] * 3)
            model.update()
            model.optimize()
            tdelta = datetime.datetime.now() - tstart
            write_solvetime(int(tdelta.total_seconds() * 1000), 'solvetimeSequentiell.txt')

        def solve_integrated_delay(delay_costs):
            obj_with_delay_costs(delay_costs)
            model.update()
            model.write('mymodel.lp')
            model.optimize()
            write_solvetime(model.runtime)

        # modify revenue function stepwise on sequential scheduling
        def solve_sequential_delay(delay_costs):
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

        if quality_consideration:
            if not sequential:
                solve_integrated_quality()
            else:
                solve_sequential_quality()
        else:  # no quality consideration: minimize total delays
            delay_costs = [p.delaycost for p in projects]
            if not sequential:
                solve_integrated_delay(delay_costs)
            else:
                solve_sequential_delay(delay_costs)

        implemented_jobs = []
        sts = []

        if model.status != GRB.Status.OPTIMAL:
            print(f'Unable to obtain optimal solution. Status code = {model.status}')

        for (l, p) in enumerate(projects):
            if model.status == GRB.Status.OPTIMAL:
                implemented_jobs.append([j for j in p.jobs if any(x[l][j, t].x > 0.0 for t in p.periods)])
                sts.append([next(t for t in p.periods if x[l][j, t].x > 0.0) - p.durations[j] if j in implemented_jobs[l] else -1 for j in p.jobs])
            else:
                sts.append([0] * p.njobs)

        attrs = compute_solution_attrs(projects, sts)
        print(attrs)

        # print(f'Optimal solution for project {l}: sts={sts}, impl_jobs={implemented_jobs}')
        return sts

    except GurobiError as e:
        print(e)
