from docplex.mp.model import Model

"""
dsl_bf_m
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
            self._name = "{}: {}".format("dsl_bf_m", name)
        else:
            self._name = "dsl_bf_m"

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

        u = m.binary_var_dict(keys=[(d, i, j, t, s) 
                                    for d in range(len(demands)) 
                                    for i, j in edges
                                    for t in demands[d][1]
                                    for s in range(0, S+1)], name="u")
        # flow constraints
        for d, _ in enumerate(demands):
            s = demands[d][0]
            T = demands[d][1]
            v = demands[d][2]
            for j, _ in enumerate(graph):
                for t, sl in [(t, sl) for t in T for sl in range(0, S)]:
                    incoming = []
                    outgoing = []
                    
                    for d2, i2, j2, t2, sl2 in u:
                        if d != d2 or t != t2 or sl != sl2:
                            continue
                        if i2 == j:
                            outgoing.append(u[d2,i2,j2,t2,sl2])
                        if j2 == j:
                            incoming.append(u[d2,i2,j2,t2,sl2])
                    if j == s:
                        m.add_constraint(sum(incoming) - sum(outgoing) == -v, ctname="source has v outgoing")
                    elif j == t:
                        m.add_constraint(sum(incoming) - sum(outgoing) == v, ctname="terminal has v incoming")
                    else:
                        m.add_constraint(sum(incoming) - sum(outgoing) == 0, ctname="same incoming as outgoing for non source/terminal")

        # demands do not overlap sots
        for e, t, sl in [(e, t, sl) 
                         for e in edges
                         for t in range(]
            m.add_constraint(sum([u[d,i,j,t,s] for d2, i, j, t, s in u if d2 == d]) <= 1, 
                             ctname="demands do not overlap slots")
        
        for d, i, j, t in [(d, i, j, t)
                           for d in range(len(demands))
                           for i, j in edges
                           for t in demands[d][1]]:
            m.add_constraint(u[d, i, j, t, S] == 0, ctname="s+1 is set to zero")

        for d, i, j, t, sl in [(d, i, j, t, sl)
                           for d in range(len(demands))
                           for i, j in edges
                           for t in demands[d][1]
                           for sl in range(demands[d][2], S)]:
            v = demands[d][2]
            m.add_constraint(
                sum(u[d,i,j,t,sl2] for sl2 in range(S-v, sl+1)) >= 
                v*(u[d,i,j,t,sl] - u[d,i,j,t,sl+1]),
                ctname="slots are contiguous")

        for d, e, e2, t, t2, sl in [(d, e, e2, t, t2, sl)
                           for d in range(len(demands))
                           for e in edges
                           for e2 in edges
                           for t in demands[d][1]
                           for t2 in demands[d][1] if t != t2
                           for sl in range(1, S)]:
            v = demands[d][2]
            m.add_constraint(
                sum(u[d,e[0],e[1],t,sl2] for sl2 in range(0, S)) <= 
                v*(1 - u[d,e2[0],e2[1],t2,sl] - u[d,e[0],e[1],t,sl]),
                ctname="demand/terminal pair path use the same slots")
            
        m.set_objective("min", 
                        sum([u[d, i, j, t, sl]/(demands[d][2]*len(demands[d][1]))
                             for d, i, j, t, sl in u]))
        
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
            solution.get_value_dict(u),
            len(graph), demands)
        m.end()

        return res

def to_res(u, n, demands) -> list[tuple[T_graph, tuple[int, int]]]:
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    slot_assignations = [(int(0), int(0)) for _ in range(len(demands))]

    for d, i, j, t, sl in u:
        if u[d, i, j, t, sl] == 1:
            demand_graph = demand_graphs[d]
            demand_graph[i].append(j)
            if slot_assignations[d][0] == slot_assignations[d][1] or sl < slot_assignations[d][0]:
                slot_assignations[d] = (int(sl), int(sl) + demands[d][2])

    res = []
    for i in range(len(demands)):
        res.append((demand_graphs[i], slot_assignations[i]))
    return res