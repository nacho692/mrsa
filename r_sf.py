from docplex.mp.model import Model


def solve(graph, s, demands):
    m = Model(name='Steiner Forest')

    # y_de variables
    idx = []
    for u, outgoing in enumerate(graph):
        for v in outgoing:
            for d in range(len(demands)):
                idx.append((d, u, v))
    y = m.binary_var_dict(keys=idx, name="y")

    # p_dd' variables
    # p = m.binary_var_dict(keys=[(d, d2) for d2 in range(demands) for d in range(demands) if d != d2], name="p")

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
                    m.add_constraint(e <= sum(inputs), ctname="intermediate_flow: " + e.name)

    m.set_objective("min", sum([y[d, u, v] for d, u, v in y]))
    m.print_information()
    m.export_as_lp("prob.lp")
    m.solve()
    m.print_solution()
