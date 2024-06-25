from re import L
from docplex.mp.model import Model
from graph import dfs

"""
drl_bf_m
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
            self._name = "{}:{}".format("drl_bf_m", name)
        else:
            self._name = "drl_bf_m"

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
        l = m.binary_var_dict(keys=[(d, i, j, t, s)
                                    for d in range(len(demands))
                                    for i, j in edges
                                    for t in demands[d][1]
                                    for s in range(0, S_L[d] + 1)], name="l")
        # flow constraints
        for d, t in [(d, t)
                     for d in range(len(demands))
                     for t in demands[d][1]
                     ]:
            s = demands[d][0]
            T = demands[d][1]

            m.add_constraint(sum([
                l[d, e[0], e[1], t, sl]
                for e in edges if e[0] == s
                for sl in range(S_L[d] + 1)
            ]) == 1, ctname="one outgoing from source")

            m.add_constraint(sum([
                l[d, e[0], e[1], t, sl]
                for e in edges if e[1] == s
                for sl in range(S_L[d] + 1)
            ]) == 0, ctname="none incoming to source")

        for d, j, t, sl in [
            (d, j, t, sl)
            for d in range(len(demands))
            for t in demands[d][1]
            for j in range(len(graph)) if j != demands[d][0] and j != t
            for sl in range(S_L[d] + 1)
        ]:
            incoming_sum = sum([
                l[d, e[0], e[1], t, sl]
                for e in edges if e[1] == j
            ])

            outgoing_sum = sum([
                l[d, e[0], e[1], t, sl]
                for e in edges if e[0] == j
            ])

            m.add_constraint(incoming_sum - outgoing_sum == 0,
                             ctname="flow is conserved on internal nodes")

        for d, e1, e2, t1, t2, sl in [
            (d, e1, e2, t1, t2, sl)
            for d in range(len(demands))
            for e1 in edges if demands[d][0] == e1[0]
            for e2 in edges if demands[d][0] == e2[0]
            for t1 in demands[d][1]
            for t2 in demands[d][1] if t1 != t2
            for sl in range(S_L[d] + 1)
        ]:
            lsum = sum([l[d, e1[0], e1[1], t1, sl2] for sl2 in range(S_L[d] + 1)])
            m.add_constraint(lsum <= 1 - (l[d, e2[0], e2[1], t2, sl] - l[d, e1[0],
                             e1[1], t1, sl]), ctname="paths with same demands use the same slots")

        for d, e, t, sl in [
            (d, e, t, sl)
            for d in range(len(demands))
            for e in edges
            for t in demands[d][1]
            for sl in range(S_L[d] + 1)
        ]:
            i, j = e[0], e[1]
            v = demands[d][2]
            lsum = sum([
                l[d2, i, j, t2, sl2]
                for d2 in range(len(demands)) if d != d2
                for t2 in demands[d2][1]
                for sl2 in range(sl, min(S_L[d2] + 1, sl+v))
            ])
            m.add_constraint(
                lsum <= S*(1-l[d, i, j, t, sl]), ctname="avoid overlap")

        m.set_objective("min",
                        sum([l[d, i, j, t, sl]/len(demands[d][1])
                             for d, i, j, t, sl in l]))

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

    for d, i, j, t, s in l:
        if abs(l[d, i, j, t, s] - 1) < 0.001:
            v = demands[d][2]
            slot_assignations[d] = (int(s), int(s) + v)

    for d, i, j, t, s in l:
        if s not in range(slot_assignations[d][0], slot_assignations[d][1]):
            continue
        if abs(l[d, i, j, t, s] - 1) < 0.001:
            demand_graph = demand_graphs[d]
            if j not in demand_graph[i]:
                demand_graph[i].append(j)

    res = []
    for d in range(len(demands)):
        res.append((demand_graphs[d], slot_assignations[d]))
    return res
