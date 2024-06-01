from docplex.mp.model import Model

"""
nls_f is a constraints system that uses integer variables to mantain flow constraints.

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
            self._name = "{}:{}".format("nls_f", name)
        else:
            self._name = "nls_f"

        self._demands = demands
        self._S = S
        self._hooks = []
        
    def register_hook(self, hook):
        self._hooks.append(hook)

    def solve(self) -> list[tuple[T_graph, tuple[int, int]]]:
        with Model(name=self._name) as m:
            return self._solve(m)

    def _solve(self, m) -> list[tuple[T_graph, tuple[int, int]]]:

        demands = self._demands
        S = self._S
        graph = self._graph
        name = self._name

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

        # upper bound, lower bound and selected slots
        b = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="b")
        a = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="a")
        x = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="x")

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