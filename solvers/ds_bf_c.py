from docplex.mp.model import Model
from cplex.callbacks import LazyConstraintCallback
from docplex.mp.callbacks.cb_mixin import *
from graph import dfs
import math
from solvers.solvers import BaseHook, T_graph, Res, solve_hook

"""
ds_bf_c is a constraints system which adds a cut based approach to guarantee the demands arborescense.

For each demand, every subgraph that constains the source node and does not contain a terminal, must have at least one ougoing edge.
"""

class Solver():
    
    def __init__(self, graph: T_graph, S: int, demands: list[tuple[int, set[int], int]], name: str = "") -> None:
        self._graph = graph

        if name != "":
            self._name = "{}:{}".format("ds_bf_c", name)
        else:
            self._name = "ds_bf_c"

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

        x = m.binary_var_dict(keys=[(d, s) 
                                    for d in range(len(demands))
                                    for s in range(0, S+1)], name="x")
        # cut based constraints
        for di, d in enumerate(demands):
            s = d[0]
            m.add_constraint(sum([y[di, s, o] for o in graph[s]]) >= 1)

        cb = m.register_callback(DOLazyCallback)
        cb._y = y
        cb._x = x
        cb._S = S
        cb._graph = graph
        cb._demands = demands

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

        for d in range(len(demands)):
            v = demands[d][2]
            for s in range(v-1, S):
                m.add_constraint(
                    sum([x[d, s2] for s2 in range(s - v + 1, s + 1)]) >= 
                    v*(x[d, s] - x[d, s+1]), 
                    ctname="slots are contiguous")

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
            S
            )
        

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

        res = to_res(y, x, len(self._graph), self._demands, self._S)
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