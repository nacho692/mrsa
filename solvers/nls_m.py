from docplex.mp.model import Model
import math

"""
nls_f is a constraints system that generates a specific path per pair (demand, terminal) and then joins them all together.

For each demand, every subgraph that constains the source node and does not contain a terminal, must have at least one ougoing edge.

nls has a variable per demand-slot, l_ds for slots lower than the selected ones for demand d, r_ds for the upper bound
and x_ds for the selected slots.
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
            self._name = "{}:{}".format("nls_m", name)
        else:
            self._name = "nls_m"

        self._demands = demands
        self._S = S
        self._hooks = []
        
    def register_hook(self, hook):
        self._hooks.append(hook)

    def solve(self) -> list[tuple[T_graph, tuple[int, int]]]:
        try:
            with Model(name=self._name) as m:
                return self._solve(m)
        except Exception as e:
            for h in self._hooks:
                h.hook_on_exception(e, m)
            raise e

    def _solve(self, m) -> list[tuple[T_graph, tuple[int, int]]]:

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

        # upper bound, lower bound and selected slots
        b = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="b")
        a = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="a")
        x = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="x")

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
        for d1, d2, e, s in [(d1, d2, e, s)
                             for d1 in range(len(demands))
                             for d2 in range(len(demands)) if d1 != d2
                             for e in edges
                             for s in range(S)]:
            m.add_constraint(y[d1,e[0],e[1]] + x[d1,s] + y[d2,e[0],e[1]] + x[d2,s] <= 3, ctname="demands do not overlap slots")
        
        for d,s in [(d, s)
                    for d in range(len(demands))
                    for s in range(S-1)]:
            m.add_constraint(a[d,s] >= a[d,s+1], ctname="lower bound is continuous")

        for d,s in [(d, s)
                    for d in range(len(demands))
                    for s in range(1, S)]:
            m.add_constraint(b[d,s] >= b[d,s-1], ctname="upper bound is continuous")

        for d,s in [(d, s)
            for d in range(len(demands))
            for s in range(0, S)]:
            m.add_constraint(x[d,s] + a[d,s] + b[d,s] == 1, ctname="upper bound, lower bound and selected slots are disjointed")

        for d in range(len(demands)):
            m.add_constraint(sum([x[d,s] for s in range(S)]) >= demands[d][2], ctname="demands satisfy required values")

        m.set_objective("min", sum([y[d, u, v] for d, u, v in y]))
        
        for h in self._hooks:
            h.hook_before_solve(m)

        solution = m.solve()

        for h in self._hooks:
            h.hook_after_solve(m)

        if solution == None:
            
            raise AssertionError(f"Solution not found: {m.solve_details}")

        res = to_res(
            solution.get_value_dict(y), 
            solution.get_value_dict(x), 
            len(graph), demands
            )
        

        return res

    def name(self):
        return self._name

def to_res(y, x, n, demands) -> list[tuple[T_graph, tuple[int, int]]]:
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    for d, i, j in y:
        if abs(y[d, i, j] - 1) <= 0.001:
            demand_graph = demand_graphs[d]
            demand_graph[i].append(j)
    
    slot_assignations = [(int(-1), int(-1)) for _ in range(len(demands))]
    for d,s in x:
        rng = slot_assignations[d]
        if abs(x[d,s] - 1) <= 0.001 and (s <= rng[0] or rng[0] == -1):
            slot_assignations[d] = (s, s + demands[d][2])

    res = []
    for i in range(len(demands)):
        res.append((demand_graphs[i], slot_assignations[i]))
    return res