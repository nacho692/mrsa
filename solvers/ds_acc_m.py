from docplex.mp.model import Model
from solvers.solvers import BaseHook, T_graph, Res, solve_hook

"""
ds_acc_m is a ds constraints system that generates a specific path per pair (demand, terminal) and then joins them all together.
"""

class Solver():

    def __init__(self, graph: T_graph, S: int, demands: list[tuple[int, set[int], int]], name: str = "") -> None:
        self._graph = graph

        if name != "":
            self._name = "{}:{}".format("ds_acc_m", name)
        else:
            self._name = "ds_acc_m"

        self._demands = demands
        self._S = S
        self._hook: BaseHook

    def register_hook(self, hook: BaseHook):
        self._hook = hook

    def solve(self) -> list[tuple[T_graph, tuple[int, int]]]:
        with Model(name=self._name) as m:
            return self._solve(m)

    @solve_hook
    def _solve(self, m: Model) -> Res:

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
                                    for s in range(0, S+1)], name="x")

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

        # slot constraints
        for d1, d2 in [(d1, d2) 
                       for d1 in range(len(demands)) 
                       for d2 in range(len(demands)) if d1 != d2]:
            for i, j in edges:
                for s in range(S):
                    m.add_constraint(x[d1, s] + y[d1, i, j] + x[d2, s] + y[d2, i, j] <= 3,
                                     ctname="demands do not overlap slots")

        for d in range(len(demands)):
            m.add_constraint(x[d,S] == 0)

        for d, s1, s2 in [(d, s1, s2)
                          for d in range(len(demands))
                          for s1 in range(S)
                          for s2 in range(S) if s2 > s1]:            
            m.add_constraint(x[d,s1] + x[d,s2] <= x[d,s1+1] + 1, ctname="slots are continuous")

        for d in range(len(demands)):
            v = demands[d][2]
            m.add_constraint(sum([x[d,s] for s in range(0, S)]) == v, 
                             ctname="slots accumulate to demand")

        m.set_objective("min", sum([y[d, u, v] for d, u, v in y]))
        
        self._hook.hook_before_solve(m)
        solution = m.solve()

        if solution == None:
            
            raise AssertionError(f"Solution not found: {m.solve_details}")

        res = to_res(
            solution.get_value_dict(y), 
            solution.get_value_dict(x), 
            len(graph), demands,
            S)
        

        return res

    def name(self):
        return self._name

def to_res(y, x, n, demands, S) -> list[tuple[T_graph, tuple[int, int]]]:
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    for d, i, j in y:
        if abs(y[d, i, j] - 1) < 0.001:
            demand_graph = demand_graphs[d]
            demand_graph[i].append(j)
    
    slot_assignations = [(int(S), int(S)) for _ in range(len(demands))]
    for d, s in x:
        if abs(x[d,s]-1) > 0.001:
            continue

        v = demands[d][2]
        if slot_assignations[d][0] > s:
            slot_assignations[d] = (s, s + v)

    res = []
    for i in range(len(demands)):
        res.append((demand_graphs[i], slot_assignations[i]))
    return res