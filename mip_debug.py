from gurobipy import *

################################################################################################
# For debugging purposes
def show_internal_values(projects, model, x):
    ocvar = model.getVarByName('ocvar')
    print(f'Overtime variable vlaue = {ocvar.x}')
    revenuevar = model.getVarByName('revenuevar')
    print(f'Revenue variable value = {revenuevar.x}')
    jcvar = model.getVarByName('jcvar')
    print(f'Job cost variable value = {jcvar.x}')

    for l in range(3):
        revvar = model.getVarByName(f'revenuesvar_{l}')
        print(f'Revenue of project {l} varibale value = {revvar.x}')

    for l in range(3):
        for level in globals['qlevels']:
            for t in globals['periods']:
                its_name = f'y_{l}_{level}_{t}'
                its_val = model.getVarByName(its_name).x
                if its_val == 1:
                    print(f'Project {l} has quality level {level} at makespan {t}...')

    for l in range(3):
        p = projects[l]
        for t in p.periods:
            v = x[l][p.lastJob, t].x
            if v == 1:
                print(f'Makespan is {t}')


def add_derived_expression_variables(model, enumerate_active, x, y, z, active_projects):
    ocvar = model.addVar(-GRB.INFINITY, GRB.INFINITY, 0.0, GRB.CONTINUOUS, 'ocvar')
    model.addConstr(ocvar == quicksum(globals['kappa'][r] * z[r, t] for r in globals['renewables'] for t in globals['periods']))
    revenuevar = model.addVar(-GRB.INFINITY, GRB.INFINITY, 0.0, GRB.CONTINUOUS, 'revenuevar')
    model.addConstr(revenuevar == quicksum(p.u[level, t] * y[l][level, t] for l, p in enumerate_active(active_projects) for t in p.periods for level in globals['qlevels']))
    jcvar = model.addVar(-GRB.INFINITY, GRB.INFINITY, 0.0, GRB.CONTINUOUS, 'jcvar')
    model.addConstr(jcvar == quicksum(p.costs[j] * quicksum(x[l][j, t] for t in p.periods) for l, p in enumerate_active(active_projects) for j in p.actual_jobs))

    revenuesvar = [model.addVar(-GRB.INFINITY, GRB.INFINITY, 0.0, GRB.CONTINUOUS, f'revenuesvar_{l}') for l, p in enumerate_active(active_projects)]
    for l, p in enumerate_active(active_projects):
        model.addConstr(revenuesvar[l] == quicksum(p.u[level, t] * y[l][level, t] for t in p.periods for level in globals['qlevels']))


################################################################################################