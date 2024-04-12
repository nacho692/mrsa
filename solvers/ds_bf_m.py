from docplex.mp.model import Model

"""
ds_bf_m is a ds_bf constraints system that generates a specific path per pair (demand, terminal) and then joins them all together.
"""

T_graph = list[list[int]]

class Solver():
    _graph: list[list[int]]
    _name: str
    _S: int
    _demands: list[tuple[int, set[int], int]]
    
    def __init__(self, graph: T_graph, S: int, demands: list[tuple[int, set[int], int]], name: str = "") -> None:
        self._graph = graph

        if name != "":
            self._name = "{}: {}".format("ds_bf_m", name)
        else:
            self._name = "ds_bf_m"

        self._demands = demands
        self._S = S

    def solve(self, export=False):
        m = Model(name=self._name)

        demands = self._demands
        S = self._S
        graph = self._graph
        name = self._name

        # y_de variables
        edges = []
        for u, outgoing in enumerate(graph):
            for v in outgoing:
                edges.append((u, v))

        y = m.binary_var_dict(keys=[(d, i, j) 
                                    for d in range(len(demands)) for i, j in edges], name="y")
        yp = m.binary_var_dict(keys=[(d, t, i, j) 
                                     for d in range(len(demands)) 
                                     for t in demands[d][1] for i, j in edges], name="y'")
        x = m.binary_var_dict(keys=[(d, s) 
                                    for d in range(len(demands))
                                    for s in range(0, S+1)])

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
                            outgoing.append(yp[d2, t2, u, v])
                        if v == j:
                            incoming.append(yp[d2, t2, u, v])
                    if j == s:
                        m.add_constraint(sum(incoming) - sum(outgoing) == -1,
                                         ctname="at least one more outgoing than incoming for source")
                    elif j == t:
                        m.add_constraint(sum(incoming) - sum(outgoing) == 1,
                                         ctname="at least one more incoming than outgoing for terminal")
                    else:
                        m.add_constraint(sum(incoming) - sum(outgoing) == 0,
                                         ctname="same incoming as outgoing for non source/terminal")
            for i, j in edges:
                yps = []
                for d2, t, u, v in yp:
                    if u == i and v == j and d2 == d:
                        yps.append(yp[d2, t, u, v])
                m.add_constraint(y[d, i, j]*len(T) >= sum(yps), ctname="if one yp is set, y must be set")

        for d1, d2 in [(d1, d2) 
                       for d1 in range(len(demands)) 
                       for d2 in range(len(demands)) if d1 != d2]:
            for i, j in edges:
                for s in range(S):
                    m.add_constraint(x[d1, s] + y[d1, i, j] + x[d2, s] + y[d2, i, j] <= 3,
                                     ctname="demands do not overlap slots")

        for d in range(len(demands)):
            m.add_constraint(x[d,S] == 0)

        for d in range(len(demands)):
            v = demands[d][2]
            for s in range(v, S):
                m.add_constraint(
                    sum([x[d, s2] for s2 in range(S - v, s + 1)]) >= 
                    v*(x[d, s] - x[d, s+1]), 
                    ctname="slots are continuous")

        for d in range(len(demands)):
            v = demands[d][2]
            m.add_constraint(sum([x[d,s] for s in range(0, S)]) == v, 
                             ctname="slots accumulate to demand")

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

        res = to_res(
            solution.get_value_dict(y), 
            solution.get_value_dict(x), 
            len(graph), demands,
            S)
        m.end()

        return res

def to_res(y, x, n, demands, S) -> list[tuple[T_graph, tuple[int, int]]]:
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    for d, i, j in y:
        if y[d, i, j] == 1:
            demand_graph = demand_graphs[d]
            demand_graph[i].append(j)
    
    slot_assignations = [(int(S), int(S)) for _ in range(len(demands))]
    for d, s in x:
        if x[d,s] != 1:
            continue

        v = demands[d][2]
        if slot_assignations[d][0] > s:
            slot_assignations[d] = (s, s + v)

    res = []
    for i in range(len(demands)):
        res.append((demand_graphs[i], slot_assignations[i]))
    return res