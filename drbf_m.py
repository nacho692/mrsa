from docplex.mp.model import Model

"""
drbr_mr is a drbr constraints system that generates a specific path per pair (demand, terminal) and then joins them all together.
"""
name = "drbf_m"

def solve(graph, S, demands, name=name, export=False):
    m = Model(name=name)

    # y_de variables
    edges = []
    for u, outgoing in enumerate(graph):
        for v in outgoing:
            edges.append((u, v))

    y = m.binary_var_dict(keys=[(d, i, j) for d in range(len(demands)) for i, j in edges], name="y")
    yp = m.binary_var_dict(keys=[(d, t, i, j) for d in range(len(demands)) for t in demands[d][1] for i, j in edges], name="y'")


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
            for t in T:    
                incoming = []
                outgoing = []
                
                for d2, t2, u, v in yp:
                    if d != d2 or t != t2:
                        continue
                    if u == j:
                        outgoing.append(yp[d2,t2,u,v])
                    if v == j:
                        incoming.append(yp[d2,t2,u,v])
                if j == s:
                    m.add_constraint(sum(incoming) - sum(outgoing) == -1, ctname="at least one more outgoing than incoming for source")
                elif j == t:
                    m.add_constraint(sum(incoming) - sum(outgoing) == 1, ctname="at least one more incoming than outgoing for terminal")
                else:
                    m.add_constraint(sum(incoming) - sum(outgoing) == 0, ctname="same incoming as outgoing for non source/terminal")
        for i, j in edges:
            yps = []
            for d2, t, u, v in yp:
                if u == i and v == j and d2 == d:
                    yps.append(yp[d2, t, u, v])
            m.add_constraint(y[d,i,j]*len(T) >= sum(yps), ctname="if one yp is set, y must be set")
            
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