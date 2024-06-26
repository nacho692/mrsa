from docplex.mp.model import Model
import math
from solvers.solvers import BaseHook, T_graph, Res, solve_hook

"""
dr_bf_f is a drbr constraints system that uses integer variables to mantain flow constraints.
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
            self._name = "{}:{}".format("dr_bf_f", name)
        else:
            self._name = "dr_bf_f"

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
        slot_assignations[d] = (math.trunc(l[d]), math.trunc(l[d]) + demands[d][2])

    res = []
    for i in range(len(demands)):
        res.append((demand_graphs[i], slot_assignations[i]))
    return res