from docplex.mp.model import Model


def solve(graph, S, demands):
    m = Model(name='Steiner Forest')

    # y_de variables
    edges = []
    for u, outgoing in enumerate(graph):
        for v in outgoing:
            edges.append((u, v))
    y = m.binary_var_dict(keys=[(d, i, j) for d in range(len(demands)) for i, j in edges], name="y")

    # p_dd' variables, p_dd' = 1 means that r_d < l_d'
    p = m.binary_var_dict(keys=[(d, d2) for d2 in range(len(demands)) for d in range(len(demands)) if d != d2], name="p")

    # r_d variables and l_d variables (right and left slot allocation), if r_d = 200 then freq allocation for d starts at 200
    r = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S, name="r")
    l = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S, name="l")

    # flow constraints
    for d, _ in enumerate(demands):
        s = demands[d][0]
        T = demands[d][1]

        for j, _ in enumerate(graph):
            if j == s:
                # source has no input edges
                inputs = []
                for d2, u, v in y:
                    if d == d2 and v == j:
                        inputs.append(y[d, u, v])
                m.add_constraint(sum(inputs) == 0, ctname="source " + str(s) + " has no input edges")

                # source has one output edge
                outputs = []
                for d2, u, v in y:
                    # variable is source
                    if d2 == d and u == j:
                        outputs.append(y[d, u, v])
                m.add_constraint(sum(outputs) >= 1, ctname="source " + str(s) + " has at least one output edge")
            elif j in T:
                inputs = []
                for d2, u, v in y:
                    if d2 == d and v == j:
                        inputs.append(y[d, u, v])
                m.add_constraint(sum(inputs) == 1, ctname="terminal " + str(j) + " has one input edge")
            else:
                inputs = []
                outputs = []
                for d2, u, v in y:
                    if d2 != d:
                        continue
                    # incoming edge to j
                    if v == j:
                        inputs.append(y[d, u, v])
                    # outgoing edge from j
                    if u == j:
                        outputs.append(y[d, u, v])

                for e in outputs:
                    m.add_constraint(e <= sum(inputs), ctname="intermediate_flow for {}".format(j))

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
    m.print_information()
    m.export_as_lp("prob.lp")
    m.solve()
    m.print_solution()
