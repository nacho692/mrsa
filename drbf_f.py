from docplex.mp.model import Model

"""
drbr_f is a drbr constraints system that uses integer variables to mantain flow constraints.
"""
name = "drbf_f"

def solve(graph, S, demands, name=name, export=False):
    m = Model(name=name)

    edges = []
    for u, outgoing in enumerate(graph):
        for v in outgoing:
            edges.append((u, v))

    # y_de variables
    y = m.binary_var_dict(keys=[(d, i, j) for d in range(len(demands)) for i, j in edges], name="y")

    #f_de variables
    f = m.integer_var_dict(keys=[(d, i, j) for d in range(len(demands)) for i, j in edges], lb=0, name="f")
    for d, i, j in f:
        f[d, i, j].ub = len(demands[d][1])

    # p_dd' variables, p_dd' = 1 means that r_d < l_d'
    p = m.binary_var_dict(keys=[(d, d2) for d2 in range(len(demands)) for d in range(len(demands)) if d != d2], name="p")

    # r_d variables and l_d variables (right and left slot allocation), if r_d = 200 then freq allocation for d starts at 200
    r = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S-1, name="r")
    l = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S-1, name="l")

    # flow constraints
    for d, _ in enumerate(demands):
        s = demands[d][0]
        T = demands[d][1]

        for j, _ in enumerate(graph):
            inputs = []
            outputs = []
            for d2, u, v in f:
                if d2 != d:
                    continue
                # incoming edge to j
                if v == j:
                    inputs.append(f[d, u, v])
                # outgoing edge from j
                if u == j:
                    outputs.append(f[d, u, v])

            if j == s:
                # source input - output = - |T(d)|
                m.add_constraint(sum(inputs) - sum(outputs) == -len(T), ctname=f"source {j} input - output is -{len(T)}")
            elif j in T:
                m.add_constraint(sum(inputs) - sum(outputs) == 1, ctname=f"terminal {j} input - output equals 1")
            else:
                m.add_constraint(sum(inputs) - sum(outputs) == 0, ctname=f"node {j} input - output equals 0")

    for d, i, j in f:
        m.add_constraint(y[d,i,j]*len(demands[d][1]) >= f[d,i,j], ctname="if f_e is set, y_e must be set")

    # slot constraints
    for d1, d2 in p:
        if d1 > d2:
            m.add_constraint(p[d1,d2] + p[d2,d1] == 1, ctname="either d1 is before d2 or d2 is before d1")


    # demands do not overlap
    for d1, d2 in p:
        for i, j in edges:
            m.add_constraint(r[d1] + 1 <= l[d2] + S*(3-p[d1,d2] - y[d1,i,j] - y[d2, i, j]), ctname="avoid overlap between demands")     
    
    # difference between right and left is slots required per demand
    for d in range(len(demands)):
        m.add_constraint(r[d] - l[d] + 1 == demands[d][2], ctname="slots are the required amount")

    for d in range(len(demands)):
        m.add_constraint(l[d] <= r[d], ctname="right is greater than left")

    m.set_objective("min", sum([y[d, u, v] for d, u, v in y]))
    
    if export:
        m.print_information()
    
    if export:
        m.export_as_lp("{}.lp".format(name))
    
    solution = m.solve()
    if solution == None:
        raise AssertionError(f"Solution not found: {m.solve_details}")
    if export:
        solution.export("{}.json".format(name))


    res = [[[[] for _ in range(len(graph))], (0, 0)] for _ in range(len(demands))]
    for d, i, j in y:
        if y[d, i, j].sv == 1:
            demand_graph = res[d][0]
            demand_graph[i].append(j)
    for d in l:
        res[d][1] = (l[d].sv, l[d].sv + demands[d][2])

    for i, r in enumerate(res):
        res[i] = (r[0], r[1])
    m.end()

    return res