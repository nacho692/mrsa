from docplex.mp.model import Model
from cplex.callbacks import LazyConstraintCallback
from docplex.mp.callbacks.cb_mixin import *
from graph import dfs
import math

"""
drl_bf_c
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
            self._name = "{}:{}".format("drl_bf_c", name)
        else:
            self._name = "drl_bf_c"

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

    def _solve(self, m: Model) -> list[tuple[T_graph, tuple[int, int]]]:

        demands = self._demands
        S = self._S
        graph = self._graph
        name = self._name

        edges = []
        for u, outgoing in enumerate(graph):
            for v in outgoing:
                edges.append((u, v))

        S_L = {}
        for d in range(len(demands)):
            v = demands[d][2]
            S_L[d] = S - v

        # U_dets variables
        l = m.binary_var_dict(keys=[(d, i, j, s)
                                    for d in range(len(demands))
                                    for i, j in edges
                                    for s in range(0, S_L[d] + 1)], name="l")

        cb = m.register_callback(DOLazyCallback)
        cb._l = l
        cb._S_L = S_L
        cb._graph = graph
        cb._demands = demands

        for d, j, e1, e2, sl in [
            (d, j, e1, e2, sl)
            for d in range(len(demands))
            for j in range(len(graph))
            for e1 in edges if e1[0] == j or e1[1] == j
            for e2 in edges if e2[0] == j or e2[1] == j
            for sl in range(S_L[d] + 1)
        ]:
            lsum = sum([
                l[d, e1[0], e1[1], sl2]
                for sl2 in range(S_L[d])
            ])

            m.add_constraint(lsum <= 1 - (l[d, e2[0], e2[1], sl] - l[d, e1[0], e1[1], sl]),
                             ctname="same slot is used on formed paths")

        for d, e, sl in [
            (d, e, sl)
            for d in range(len(demands))
            for e in edges
            for sl in range(S_L[d] + 1)
        ]:
            i, j = e[0], e[1]
            v = demands[d][2]
            lsum = sum([
                l[d2, i, j, sl2]
                for d2 in range(len(demands)) if d != d2
                for sl2 in range(sl, min(S_L[d2] + 1, sl+v))
            ])
            m.add_constraint(
                lsum <= S*(1-l[d, i, j, sl]), ctname="avoid overlap")

        m.set_objective("min",
                        sum([l[d, i, j, sl] for d, i, j, sl in l]))

        for h in self._hooks:
            h.hook_before_solve(m)

        solution = m.solve()

        for h in self._hooks:
            h.hook_after_solve(m)

        if solution == None:
            raise AssertionError(f"Solution not found: {m.solve_details}")

        res = to_res(
            graph,
            solution.get_value_dict(l),
            demands)

        return res

    def name(self):
        return self._name


def to_res(graph, l, demands) -> list[tuple[T_graph, tuple[int, int]]]:
    n = len(graph)
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    slot_assignations = [(int(0), int(0)) for _ in range(len(demands))]

    for d, i, j, s in l:
        if i == demands[d][0] and abs(l[d, i, j, s] - 1) < 0.001:
            v = demands[d][2]
            slot_assignations[d] = (int(s), int(s) + v)

    for d, i, j, s in l:
        if s not in range(slot_assignations[d][0], slot_assignations[d][1]):
            continue
        if abs(l[d, i, j, s] - 1) < 0.001:
            demand_graph = demand_graphs[d]
            if j not in demand_graph[i]:
                demand_graph[i].append(j)

    res = []
    for d in range(len(demands)):
        # we only return graphs reachable from source
        reached = dfs(demand_graphs[d], demands[d][0])
        for n, outgoing in enumerate(demand_graphs[d]):
            if n not in reached:
                outgoing.clear()
        res.append((demand_graphs[d], slot_assignations[d]))
    return res

def filter_graph(graph, l, d_filter, S_L) -> T_graph:
    n = len(graph)
    demand_graph = [[] for _ in range(n)]
    for i, outgoing in enumerate(graph):
        for j in outgoing:
            if j in demand_graph[i]:
                continue
            if any([abs(l[d_filter,i,j,s] - 1) < 0.001 for s in range(S_L + 1)]):
                demand_graph[i].append(j)

    return demand_graph


class DOLazyCallback(ConstraintCallbackMixin, LazyConstraintCallback):

    def __init__(self, env):
        self._graph: list[list[int]]
        self._name: str
        self._S: int
        self._S_L: dict[int, int]
        self._demands: list[tuple[int, set[int], int]]
        self._l: dict
        self._export: bool = False
        LazyConstraintCallback.__init__(self, env)
        ConstraintCallbackMixin.__init__(self)

    def __call__(self):
        sol = self.make_complete_solution()

        l = sol.get_value_dict(self._l)

        new_constraints = []
        for di, d in enumerate(self._demands):
            res = filter_graph(self._graph, l, di, self._S_L[di])

            reached = set(dfs(res, d[0]))
            T = d[1]
            t_diff = T.difference(reached)
            if len(t_diff) > 0:
                outgoing_edges = set()
                for r in reached:
                    for outgoing in self._graph[r]:
                        if outgoing not in reached:
                            outgoing_edges |= set([
                                self._l[di, r, outgoing, sl]
                                for sl in range(self._S_L[di] + 1)
                            ])
                if self._export:
                    print(
                        f"Demand {di} not reaching some terminals: reached={reached}, diff={t_diff}")
                new_constraints.append(sum(outgoing_edges) >= 1)

        unsats = self.get_cpx_unsatisfied_cts(
            new_constraints, sol, tolerance=1e-6)
        for _, cpx_lhs, sense, cpx_rhs in unsats:
            self.add(cpx_lhs, sense, cpx_rhs)
