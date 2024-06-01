from docplex.mp.model import Model
from graph import dfs

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
            self._name = "{}:{}".format("dsl_bf_m", name)
        else:
            self._name = "dsl_bf_m"

        self._demands = demands
        self._S = S
        self._hooks = []
        
    def register_hook(self, hook):
        self._hooks.append(hook)

    def solve(self) -> list[tuple[T_graph, tuple[int, int]]]:
        with Model(name=self._name) as m:
            return self._solve(m)

    def _solve(self, m) -> list[tuple[T_graph, tuple[int, int]]]:
        demands = self._demands
        S = self._S
        graph = self._graph
        name = self._name

        edges = []
        for u, outgoing in enumerate(graph):
            for v in outgoing:
                edges.append((u, v))

        # U_dets variables
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
                for t in T:
                    outgoing_sl = dict([(i, []) for i in range(0, S+1)])
                    incoming_sl = dict([(i, []) for i in range(0, S+1)])
                    for d2, i2, j2, t2, sl in u:
                        if d != d2 or t != t2:
                            continue
                        if i2 == j:
                            outgoing_sl[sl].append(u[d2,i2,j2,t2,sl])
                        if j2 == j:
                            incoming_sl[sl].append(u[d2,i2,j2,t2,sl])
                    if j == s:
                        m.add_constraint(sum(sum(incoming_sl.values(), [])) - sum(sum(outgoing_sl.values(), [])) == -v, ctname="source has v outgoing")
                    elif j == t:
                        m.add_constraint(sum(sum(incoming_sl.values(), [])) - sum(sum(outgoing_sl.values(), [])) == v, ctname="terminal has v incoming")
                    else:
                        for sl in range(0, S):
                            m.add_constraint(ct=sum(incoming_sl[sl]) - sum(outgoing_sl[sl]) == 0, ctname="same incoming as outgoing for non source/terminal")

        # demands do not overlap sots
        for d, d2, e, t, t2, sl in [(d, d2, e, t, t2, sl)
                                    for d in range(len(demands))
                                    for d2 in range(len(demands)) if d != d2
                                    for e in edges
                                    for t in demands[d][1]
                                    for t2 in demands[d2][1]
                                    for sl in range(0, S)]:
            m.add_constraint(u[d,e[0],e[1],t,sl] + u[d2,e[0],e[1],t2,sl] <= 1,
                             ctname="demands do not overlap slots")
        
        for d, i, j, t in [(d, i, j, t)
                           for d in range(len(demands))
                           for i, j in edges
                           for t in demands[d][1]]:
            m.add_constraint(u[d, i, j, t, S] == 0, ctname="s+1 is set to zero")

        for d, e, t, sl in [(d, e, t, sl)
                           for d in range(len(demands))
                           for e in edges
                           for t in demands[d][1]
                           for sl in range(demands[d][2]-1, S)]:
            v = demands[d][2]
            i = e[0]
            j = e[1]
            m.add_constraint(
                sum(u[d,i,j,t,sl2] for sl2 in range(sl-v+1, sl+1)) >= 
                v*(u[d,i,j,t,sl] - u[d,i,j,t,sl+1]),
                ctname="slots are contiguous")
            
        for d, e, t, sl in [(d, e, t, sl)
                    for d in range(len(demands))
                    for e in edges
                    for t in demands[d][1]
                    for sl in range(0, demands[d][2])]:
            v = demands[d][2]
            i = e[0]
            j = e[1]
            m.add_constraint(
                sum(u[d,i,j,t,sl2] for sl2 in range(0, v)) >= 
                v*(u[d,i,j,t,sl] - u[d,i,j,t,sl+1]),
                ctname="base slots are contiguous")


        for d, e, e2, t, t2, sl in [(d, e, e2, t, t2, sl)
                           for d in range(len(demands))
                           for e in edges if e[0] == demands[d][0] or e[1] == demands[d][0]
                           for e2 in edges if e2[0] == demands[d][0] or e2[1] == demands[d][0]
                           for t in demands[d][1]
                           for t2 in demands[d][1] if t != t2
                           for sl in range(0, S)]:
            v = demands[d][2]
            m.add_constraint(
                sum(u[d,e[0],e[1],t,sl2] for sl2 in range(0, S)) <= 
                v*(1 - u[d,e2[0],e2[1],t2,sl] + u[d,e[0],e[1],t,sl]),
                ctname="demand/terminal pair path use the same slots")
            
        # for d, e, e2, t, t2, sl in [(d, e, e2, t, t2, sl)
        #                    for d in range(len(demands))
        #                    for e in edges
        #                    for e2 in edges
        #                    for t in demands[d][1]
        #                    for t2 in demands[d][1] if t != t2
        #                    for sl in range(0, S)]:
        #     v = demands[d][2]
        #     m.add_constraint(
        #         sum(u[d,e[0],e[1],t,sl2] for sl2 in range(0, S)) <= 
        #         v*(1 - u[d,e2[0],e2[1],t2,sl] + u[d,e[0],e[1],t,sl]),
        #         ctname="demand/terminal pair path use the same slots")
            
        # m.set_objective("min", 
        #                 sum([u[d, i, j, t, sl]/(demands[d][2]*len(demands[d][1]))
        #                      for d, i, j, t, sl in u]))
        
        for h in self._hooks:
            h.hook_before_solve(m)

        solution = m.solve()

        for h in self._hooks:
            h.hook_after_solve(m)

        if solution == None:
            raise AssertionError(f"Solution not found: {m.solve_details}")


        res = to_res(
            graph,
            solution.get_value_dict(u),
            demands,
            S)

        return res
    
    def name(self):
        return self._name

def to_res(graph, u, demands, S) -> list[tuple[T_graph, tuple[int, int]]]:
    n = len(graph)
    demand_graphs = [[[] for _ in range(n)] for _ in range(len(demands))]
    slot_assignations = [(int(0), int(0)) for _ in range(len(demands))]

    res = []
    for d in range(len(demands)):
        v = demands[d][2]

        found = False
        for s in range(S-v+1):
            filtered_graph = filter_graph(u, graph, demands, d, s, s+v)
            
            T = demands[d][1]
            reached = dfs(filtered_graph, demands[d][0])
            # If, by using this s,s+v range we can reach all terminals, we take this graph as the demand graph
            if len(set(reached) & T) == len(T):
                demand_graphs[d] = filtered_graph
                slot_assignations[d] = (int(s), int(s) + v)
                found = True
                break
    
        if not found:
            raise AssertionError(f"no graph with volume {v} found for demand {d}")
        
        res.append((demand_graphs[d], slot_assignations[d]))
    return res


def filter_graph(u, graph, demands, d_filter, s_filter_from, s_filter_to) -> T_graph:
    n = len(graph)
    demand_graph = [[] for _ in range(n)]

    for i, outgoing in enumerate(graph):
        for j in outgoing:
            if j in demand_graph[i]:
                continue
            # If for all s in the range, there exists a t such that the variable was taken
            if all([
                any([abs(u[d_filter,i,j,t,s] - 1) < 0.001 for t in demands[d_filter][1]])
                    for s in range(s_filter_from, s_filter_to)]):
                demand_graph[i].append(j)

    return demand_graph