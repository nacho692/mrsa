from docplex.mp.model import Model
from cplex.callbacks import LazyConstraintCallback
from docplex.mp.callbacks.cb_mixin import *
from graph import dfs
import math

"""
ds_acc_c is a constraints system which adds a cut based approach to guarantee the demands arborescense.

For each demand, every subgraph that constains the source node and does not contain a terminal, must have at least one ougoing edge.
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
            self._name = "{}: {}".format("ds_acc_c", name)
        else:
            self._name = "ds_acc_c"

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
        cb._export = export

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
        
        if export:
            m.print_information()
        
        if export:
            m.export_as_lp("{}.lp".format(name))

        solution = m.solve(log_output=True)
        if solution == None:
            raise AssertionError(f"Solution not found: {m.solve_details}")

        if export:
            solution.export("{}.json".format(name))

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

class DOLazyCallback(ConstraintCallbackMixin, LazyConstraintCallback):
    
    _graph: list[list[int]]
    _name: str
    _S: int
    _demands: list[tuple[int, set[int], int]]
    _y: dict
    _x: dict
    _export: bool = False

    def __init__(self, env):
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