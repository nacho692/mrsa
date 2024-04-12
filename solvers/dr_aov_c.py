from docplex.mp.model import Model
from cplex.callbacks import LazyConstraintCallback
from docplex.mp.callbacks.cb_mixin import *
from graph import dfs

"""
dr_aov_c is a dr_aov constraints system which adds a cut based approach to guarantee the demands arborescense.

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
            self._name = "{}: {}".format("dr_aov_c", name)
        else:
            self._name = "dr_aov_c"

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

        # n_dd' variables, n_dd' = 1 means that r_d < l_d' and there's an overlap over a path between demands
        n = m.binary_var_dict(keys=[(d, d2) for d2 in range(len(demands)) for d in range(len(demands)) if d != d2], name="n")

        # r_d variables and l_d variables (right and left slot allocation), if r_d = 200 then freq allocation for d starts at 200
        r = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S-1, name="r")
        l = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S-1, name="l")

        # cut based constraints
        for di, d in enumerate(demands):
            s = d[0]
            m.add_constraint(sum([y[di, s, o] for o in graph[s]]) >= 1)

        cb = m.register_callback(DOLazyCallback)
        cb._y = y
        cb._l = l
        cb._r = r
        cb._graph = graph
        cb._demands = demands
        cb._export = export

        # slot constraints
        for d1, i, j in y:
            for d2 in range(len(demands)):
                if d1 <= d2:
                    continue
                m.add_constraint(n[d1,d2] + n[d2,d1] >= y[d1,i,j] + y[d2,i,j]- 1, ctname="if d, d' share an arc then either n_dd' or n_d'd = 1")

        # demands do not overlap
        for d1, d2 in n:
            for i, j in edges:
                m.add_constraint(r[d1] + 1 <= l[d2] + S*(1-n[d1,d2]), ctname="avoid overlap between demands")
        
        # difference between right and left is slots required per demand
        for d in range(len(demands)):
            m.add_constraint(r[d] - l[d] + 1 == demands[d][2], ctname="slots are the required amount")

        for d in range(len(demands)):
            m.add_constraint(l[d] <= r[d], ctname="right is greater than left")

        m.set_objective("min", sum([y[d, u, v] for d, u, v in y]))
        
        if export:
            m.print_information()
        
        if export:
            m.export_as_lp("{}.lp".format(name))

        solution = m.solve()
        if solution == None:
            raise AssertionError(f"Solution not found: {m.solve_details}")

        if export:
            solution.export("{}.json".format(name))


        res = to_res(
            solution.get_value_dict(y), 
            solution.get_value_dict(l), 
            len(graph), demands
            )
        m.end()

        return res

def to_res(y, l, n, demands) -> list[tuple[T_graph, tuple[int, int]]]:
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    for d, i, j in y:
        if y[d, i, j] == 1:
            demand_graph = demand_graphs[d]
            demand_graph[i].append(j)
    
    slot_assignations = [(int(0), int(0)) for _ in range(len(demands))]
    for d in l:
        slot_assignations[d] = (int(l[d]), int(l[d]) + demands[d][2])

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
    _l: dict
    _r: dict
    _export: bool = False

    def __init__(self, env):
        LazyConstraintCallback.__init__(self, env)
        ConstraintCallbackMixin.__init__(self)
    
    def __call__(self):
        sol = self.make_complete_solution() 
        
        y = sol.get_value_dict(self._y)
        l = sol.get_value_dict(self._l)
        r = sol.get_value_dict(self._r)

        res = to_res(y, l, len(self._graph), self._demands)
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