from docplex.mp.model import Model

"""
dr_aov_m is a draov constraints system that generates a specific path per pair (demand, terminal) and then joins them all together.
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
            self._name = "{}: {}".format("dr_aov_m", name)
        else:
            self._name = "dr_aov_m"

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
        for u, outgoing in enumerate(graph):
            for v in outgoing:
                edges.append((u, v))

        y = m.binary_var_dict(keys=[(d, i, j) for d in range(len(demands)) for i, j in edges], name="y")
        yp = m.binary_var_dict(keys=[(d, t, i, j) for d in range(len(demands)) for t in demands[d][1] for i, j in edges], name="y'")

        # n_dd' variables, n_dd' = 1 means that r_d < l_d' and there's an overlap over a path between demands
        n = m.binary_var_dict(keys=[(d, d2) for d2 in range(len(demands)) for d in range(len(demands)) if d != d2], name="n")

        # r_d variables and l_d variables (right and left slot allocation), if r_d = 200 then freq allocation for d starts at 200    
        r = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S-1, name="r")
        l = m.integer_var_dict(keys=[d for d in range(len(demands))], lb=0, ub=S-1, name="l")

        # flow constraints
        for d, _ in enumerate(demands):
            s = demands[d][0]
            T = demands[d][1]

            for j, _ in enumerate(graph):
                for t in T:    
                    incoming = []
                    outgoing = []
                    
                    for d2, t2, u, v in yp:
                        if d != d2 or t != t2:
                            continue
                        if u == j:
                            outgoing.append(yp[d2,t2,u,v])
                        if v == j:
                            incoming.append(yp[d2,t2,u,v])
                    if j == s:
                        m.add_constraint(sum(incoming) - sum(outgoing) == -1, ctname="at least one more outgoing than incoming for source")
                    elif j == t:
                        m.add_constraint(sum(incoming) - sum(outgoing) == 1, ctname="at least one more incoming than outgoing for terminal")
                    else:
                        m.add_constraint(sum(incoming) - sum(outgoing) == 0, ctname="same incoming as outgoing for non source/terminal")
            for i, j in edges:
                yps = []
                for d2, t, u, v in yp:
                    if u == i and v == j and d2 == d:
                        yps.append(yp[d2, t, u, v])
                m.add_constraint(y[d,i,j]*len(T) >= sum(yps), ctname="if one yp is set, y must be set")
                
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