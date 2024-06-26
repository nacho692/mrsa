from docplex.mp.model import Model
from cplex.callbacks import LazyConstraintCallback
from docplex.mp.callbacks.cb_mixin import *
from graph import dfs
from solvers.solvers import BaseHook, T_graph, Res, solve_hook

"""
nls_c is a constraints system which adds a cut based approach to guarantee the demands arborescense.

For each demand, every subgraph that constains the source node and does not contain a terminal, must have at least one ougoing edge.

nls has a variable per demand-slot, l_ds for slots lower than the selected ones for demand d, r_ds for the upper bound
and x_ds for the selected slots.
"""

class Solver():
    
    def __init__(self, graph: T_graph, S: int, demands: list[tuple[int, set[int], int]], name: str = "") -> None:
        self._graph = graph

        if name != "":
            self._name = "{}:{}".format("nls_c", name)
        else:
            self._name = "nls_c"

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
        for u, outgoing in enumerate(iterable=self._graph):
            for v in outgoing:
                edges.append((u, v))
        y = m.binary_var_dict(keys=[(d, i, j) for d in range(len(demands)) for i, j in edges], name="y")

        
        # upper bound, lower bound and selected slots
        b = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="b")
        a = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="a")
        x = m.binary_var_dict(keys=[(d,s) for d in range(len(demands)) for s in range(S)], name="x")

        # cut based constraints
        for di, d in enumerate(demands):
            s = d[0]
            m.add_constraint(sum([y[di, s, o] for o in graph[s]]) >= 1)

        cb = m.register_callback(DOLazyCallback)
        cb._y = y
        cb._x = x
        cb._graph = graph
        cb._demands = demands

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
        
        self._hook.hook_before_solve(m)
        solution = m.solve()

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

class DOLazyCallback(ConstraintCallbackMixin, LazyConstraintCallback):
    

    def __init__(self, env):
        self._graph: list[list[int]]
        self._name: str
        self._S: int
        self._demands: list[tuple[int, set[int], int]]
        self._y: dict
        self._x: dict
        self._export: bool = False
        LazyConstraintCallback.__init__(self, env)
        ConstraintCallbackMixin.__init__(self)
    
    def __call__(self):
        sol = self.make_complete_solution() 
        
        y = sol.get_value_dict(self._y)
        x = sol.get_value_dict(self._x)

        res = to_res(y, x, len(self._graph), self._demands)
        new_constraints = []
        for di, d in enumerate(self._demands):
            reached = set(dfs(res[di][0], d[0]))
            T = d[1]
            t_diff = T.difference(reached)
            if len(t_diff) > 0:
                outgoing_edges = set()
                for r in reached:
                    for outgoing in self._graph[r]:
                        if outgoing not in reached:
                            outgoing_edges.add(self._y[di, r, outgoing])
                if self._export:
                    print(f"Demand {di} not reaching some terminals: reached={reached}, diff={t_diff}")
                new_constraints.append(sum(outgoing_edges) >= 1)

        unsats = self.get_cpx_unsatisfied_cts(new_constraints, sol, tolerance=1e-6)
        for _, cpx_lhs, sense, cpx_rhs in unsats:
            self.add(cpx_lhs, sense, cpx_rhs)