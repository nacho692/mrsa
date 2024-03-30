from docplex.mp.model import Model

"""
*** This formulation does not work, check the mrsa PDF ***

dr_bf_r is a drbr constraints system that relaxes the flow constraints so that a node might have more than one outgoing arrow.
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
            self._name = "{}: {}".format("dr_bf_r", name)
        else:
            self._name = "dr_bf_r"

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
                if j == s:
                    # source has no input edges
                    inputs = []
                    for d2, u, v in y:
                        if d == d2 and v == j:
                            inputs.append(y[d, u, v])
                    m.add_constraint(sum(inputs) == 0, ctname="source " + str(s) + " has no input edges")

                    # source has one output edge
                    outputs = []
                    for d2, u, v in y:
                        # variable is source
                        if d2 == d and u == j:
                            outputs.append(y[d, u, v])
                    m.add_constraint(sum(outputs) >= 1, ctname="source " + str(s) + " has at least one output edge")
                elif j in T:
                    inputs = []
                    for d2, u, v in y:
                        if d2 == d and v == j:
                            inputs.append(y[d, u, v])
                    m.add_constraint(sum(inputs) == 1, ctname="terminal " + str(j) + " has one input edge")
                else:
                    inputs = []
                    outputs = []
                    for d2, u, v in y:
                        if d2 != d:
                            continue
                        # incoming edge to j
                        if v == j:
                            inputs.append(y[d, u, v])
                        # outgoing edge from j
                        if u == j:
                            outputs.append(y[d, u, v])

                    for e in outputs:
                        m.add_constraint(e <= sum(inputs), ctname="intermediate_flow for {}".format(j))

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
        
        if export:
            m.print_information()
        
        if export:
            m.export_as_lp("{}.lp".format(name))
        
        solution = m.solve()
        if solution == None:
            raise AssertionError(f"Solution not found: {m.solve_details}")
        if export:
            solution.export("{}.json".format(name))


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