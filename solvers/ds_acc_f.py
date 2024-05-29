from docplex.mp.model import Model

"""
ds_acc_f is a constraints system that uses integer variables to mantain flow constraints.
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
            self._name = "{}:{}".format("ds_acc_f", name)
        else:
            self._name = "ds_acc_f"

        self._demands = demands
        self._S = S
        self._hooks = []
        
    def register_hook(self, hook):
        self._hooks.append(hook)

    def solve(self, export=False):
        m = Model(name=self._name)

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

        x = m.binary_var_dict(keys=[(d, s) 
                                    for d in range(len(demands))
                                    for s in range(0, S+1)], name="x")

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
            len(graph), demands, 
            S
            )
        m.end()

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