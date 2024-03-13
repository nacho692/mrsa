from docplex.mp.model import Model

def solve(graph):
    m = Model(name='Steiner Forest')

    # edges is an n*n matrix with either the variable edge set or not 
    edges = [[(False, 0) for _ in range(len(graph))] for _ in range(len(graph))]
    for v, outgoing in enumerate(graph):
        for u in outgoing:
            edges[v][u] = (True, m.binary_var(name="edge:" + str(v) + "_" + str(u)))

    demands = [(0, set([2, 3]))]

    for d in demands:
        s = d[0]
        T = d[1]

        # source has no input edges
        inputs = []
        for e in [row[s] for row in edges]:
            if e[0]:
                inputs.append(e[1])
        
        m.add_constraint(sum(inputs) == 0, ctname="source " + str(s) + " has no input edges")

        outputs = []
        for e in edges[s]:
            if e[0]:
                outputs.append(e[1])
        m.add_constraint(sum(outputs) >= 1, ctname="source " + str(s) + " has at least one output edge")

        for t in T:
            inputs = []
            for e in [row[t] for row in edges]:
                if e[0]:
                    inputs.append(e[1])
            m.add_constraint(sum(inputs) == 1, ctname="terminal " + str(t) + " has one input edge")
        
        for v in range(0, len(graph)):
            if v == s or v in T:
                continue
            for u, e in enumerate(edges[v]):
                if e[0] == False:
                    continue

                i = []
                for e2 in [row[v] for row in edges]:
                    if e2[0]:
                        i.append(e2[1])
                m.add_constraint(e[1] <= sum(i), ctname="if outgoing by " + str(v) + "_" + str(u) + " then it must have incoming")

    to_min = []
    for h in edges:
        for e in h:
            if e[0]:
                to_min.append(e[1])
    m.set_objective("min", sum(to_min))
    m.print_information()
    m.export_as_lp("prob.lp")
    m.solve()
    m.print_solution()