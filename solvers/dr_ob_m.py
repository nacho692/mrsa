from docplex.mp.model import Model
from solvers.solvers import BaseHook, T_graph, Res, solve_hook

import math

"""
drbr_mr is a drbr constraints system that generates a specific path per pair (demand, terminal) and then joins them all together.
"""

class Solver():
    
    def __init__(self, graph: T_graph, S: int, demands: list[tuple[int, set[int], int]], name: str = "") -> None:
        self._graph = graph

        if name != "":
            self._name = "{}:{}".format("dr_ob_m", name)
        else:
            self._name = "dr_ob_m"

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

        y = m.binary_var_dict(keys=[(d, i, j) for d in range(len(demands)) for i, j in edges], name="y")
        yp = m.binary_var_dict(keys=[(d, t, i, j) for d in range(len(demands)) for t in demands[d][1] for i, j in edges], name="y'")


        # p_dd' variables, p_dd' = 1 means that r_d < l_d'
        p = m.binary_var_dict(keys=[(d, d2) for d2 in range(len(demands)) for d in range(len(demands)) if d != d2], name="p")

        # l_d variables (left slot allocation), if l_d = 200 then freq allocation for d starts at 200    
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


        # l_d <= S - v(d) - 1
        for d in range(len(demands)):
            m.add_constraint(l[d] <= S - demands[d][2] - 1)

        # slot constraints
        for d1, d2 in p:
            if d1 > d2:
                m.add_constraint(p[d1,d2] + p[d2,d1] == 1, ctname="either d1 is before d2 or d2 is before d1")

        # demands do not overlap
        for d1, d2 in p:
            for i, j in edges:
                m.add_constraint(demands[d1][2] + l[d1] <= l[d2] + S*(3-p[d1,d2] - y[d1,i,j] - y[d2,i,j]), ctname="avoid overlap between demands")

        for d in l:
            m.add_constraint(l[d] + demands[d][2] <= S)

        m.set_objective("min", sum([y[d, u, v] for d, u, v in y]))
        
        self._hook.hook_before_solve(m)
        solution = m.solve()

        if solution == None:
            
            raise AssertionError(f"Solution not found: {m.solve_details}")
        
        res = to_res(
            solution.get_value_dict(y), 
            solution.get_value_dict(l), 
            len(graph), demands
            )
        

        return res

    def name(self):
        return self._name

def to_res(y, l, n, demands) -> list[tuple[T_graph, tuple[int, int]]]:
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    for d, i, j in y:
        if abs(y[d, i, j] - 1) <= 0.001:
            demand_graph = demand_graphs[d]
            demand_graph[i].append(j)
    
    slot_assignations = [(int(0), int(0)) for _ in range(len(demands))]
    for d in l:
        slot_assignations[d] = (round(l[d]), math.ceil(l[d]) + demands[d][2])

    res = []
    for i in range(len(demands)):
        res.append((demand_graphs[i], slot_assignations[i]))
    return res