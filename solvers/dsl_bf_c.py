from docplex.mp.model import Model
from cplex.callbacks import LazyConstraintCallback
from docplex.mp.callbacks.cb_mixin import *
from graph import dfs
import math
from solvers.solvers import BaseHook, T_graph, Res, solve_hook

"""
dsl_bf_c is a single family variable constraints system which adds a cut based approach to guarantee the demands arborescense.

For each demand, every subgraph that constains the source node and does not contain a terminal, must have at least one ougoing edge.
"""

class Solver():
    
    def __init__(self, graph: T_graph, S: int, demands: list[tuple[int, set[int], int]], name: str = "") -> None:
        self._graph = graph

        if name != "":
            self._name = "{}:{}".format("dsl_bf_c", name)
        else:
            self._name = "dsl_bf_c"

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
        u = m.binary_var_dict(keys=[
            (d, i, j, s) 
            for d in range(len(demands)) 
            for i, j in edges
            for s in range(S+1)], name="u")

        # cut based constraints
        for d in range(len(demands)):
            i = demands[d][0]
            v = demands[d][2]
            T = demands[d][1]
            m.add_constraint(sum([u[d, i, j, s] 
                                  for j in graph[i]
                                  for s in range(S)]) >= v, ctname="initial cut based constraint")

        cb = m.register_callback(DOLazyCallback)
        cb._u = u
        cb._S = S
        cb._graph = graph
        cb._demands = demands

        # slot constraints
        for e, s in [(e, s)
                      for e in edges
                      for s in range(S)]:
              m.add_constraint(sum([u[d,e[0],e[1],s] for d in range(len(demands))]) <= 1, ctname="demands do not overlap")

        for e in edges:
             m.add_constraint(sum([u[d,e[0],e[1],S] for d in range(len(demands))]) == 0, ctname="u_deS is 0 for all d,e")
        
        for d,e1,e2,s in [(d,e1,e2,s)
                    for d in range(len(demands))
                    for n in range(len(graph))
                    for e1 in edges if e1[0] == n or e1[1] == n
                    for e2 in edges if e2[1] == n or e2[1] == n and e1 != e2
                    for s in range(S)]:
            v = demands[d][2]
            m.add_constraint(sum([u[d,e1[0],e1[1],s2] for s2 in range(S)]) <= v*(1-u[d,e2[0],e2[1],s]+u[d,e1[0],e1[1],s]), 
                             ctname="node edges slots must match")

        for d, e, s in [(d, e, s)
                         for d in range(len(demands))
                         for e in edges
                         for s in range(demands[d][2]-1, S)]:
             v: int = demands[d][2]
             lsum = sum([u[d,e[0],e[1],s2] for s2 in range(s-v+1, s+1)])
             m.add_constraint(lsum >= v*(u[d,e[0],e[1],s] - u[d,e[0],e[1],s+1]),
                                   ctname=f"slots are contiguous and demand satisfied from {s-v+1}, s {s}")
            
        for d, e, s in [(d, e, s)
                        for d in range(len(demands))
                        for e in edges
                        for s in range(0, demands[d][2])]:
            v: int = demands[d][2]
            lsum = sum([u[d,e[0],e[1],s2] for s2 in range(0, v)])
            m.add_constraint(lsum >= v*(u[d,e[0],e[1],s] - u[d,e[0],e[1],s+1]),
                                  ctname=f"base slots are contiguous and demand satisfied from {0}, s {s}")

        m.set_objective("min", sum([u[d,e[0],e[1],s]/demands[d][2]
                                    for d in range(len(demands))
                                    for e in edges
                                    for s in range(S)]))
        
        self._hook.hook_before_solve(m)
        solution = m.solve()

        if solution == None:
            
            raise AssertionError(f"Solution not found: {m.solve_details}")

        res = to_res(
            solution.get_value_dict(u), 
            len(graph), demands, S)
        

        return res

    def name(self):
        return self._name

def to_res(u, n, demands, S) -> list[tuple[T_graph, tuple[int, int]]]:
    
    slot_assignations = [(int(S), int(S)) for _ in range(len(demands))]
    for d, i, j, s in u:
        if abs(u[d, i, j, s] - 1) < 0.001:
            # We only consider slots taken from the source itself 
            if demands[d][0] == i:
                v = demands[d][2]
                if s < slot_assignations[d][0]:
                    slot_assignations[d] = (s, s+v)

    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    for d, i, j, s in u:
        if s not in range(slot_assignations[d][0], slot_assignations[d][1]):
            continue
            
        if abs(u[d, i, j, s] - 1) < 0.001:
            demand_graph = demand_graphs[d]
            if j not in demand_graph[i]:
                demand_graph[i].append(j)
    res = []
    for i in range(len(demands)):
        # we only return graphs reachable from source
        reached = dfs(demand_graphs[i], demands[i][0])
        for n, outgoing in enumerate(demand_graphs[i]):
            if n not in reached:
                outgoing.clear()
        res.append((demand_graphs[i], slot_assignations[i]))
    return res

def to_graph(u, n, d_filter, s_filter) -> T_graph:
    
    demand_graph = [[] for _ in range(n)]
    for d, i, j, s in u:
        if d != d_filter:
            continue
        if s_filter != None and s_filter != s:
            continue
        if abs(u[d, i, j, s] - 1) < 0.001:
            if j not in demand_graph[i]:
                demand_graph[i].append(j)

    return demand_graph

class DOLazyCallback(ConstraintCallbackMixin, LazyConstraintCallback):
    

    def __init__(self, env):
        self._graph: list[list[int]]
        self._name: str
        self._S: int
        self._demands: list[tuple[int, set[int], int]]
        self._u: dict
        self._export: bool = False
        LazyConstraintCallback.__init__(self, env)
        ConstraintCallbackMixin.__init__(self)
    
    def __call__(self):
        sol = self.make_complete_solution() 
        
        u = sol.get_value_dict(self._u)

        
        new_constraints = []
        for d, s in [(d, s) 
                     for d in range(len(self._demands))
                     for s in range(self._S)]:
            
            demand = self._demands[d]

            res = to_graph(u, len(self._graph), d, s)
            reached = set(dfs(res, demand[0]))
            T = demand[1]

            t_diff = T.difference(reached)
            if len(t_diff) > 0:
                outgoing_edges = set()
                inside_edges = set()
                for r in reached:
                    for outgoing in self._graph[r]:
                        if outgoing not in reached:
                            outgoing_edges |= set([self._u[d, r, outgoing, s]])
                        else:
                            inside_edges |= set([self._u[d, r, outgoing, s]])

                lsum = sum(outgoing_edges)
                rsum = sum(inside_edges)
                new_constraints.append(lsum*len(inside_edges) >= rsum)

                if self._export:
                    print(f"demand:{d} slot:{s} not reaching some terminals: reached={reached}, diff={t_diff}")

        unsats = self.get_cpx_unsatisfied_cts(new_constraints, sol, tolerance=1e-6)
        for _, cpx_lhs, sense, cpx_rhs in unsats:
            self.add(cpx_lhs, sense, cpx_rhs)