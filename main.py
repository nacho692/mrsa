from sample_problems.problems import problems
from graph import dfs

from solvers.dr_bf_r import Solver as DR_BF_R
from solvers.dr_bf_m import Solver as DR_BF_M
from solvers.dr_bf_f import Solver as DR_BF_F
from solvers.dr_bf_c import Solver as DR_BF_C
from solvers.dr_aov_c import Solver as DR_AOV_C
from solvers.dr_aov_f import Solver as DR_AOV_F
from solvers.dr_aov_m import Solver as DR_AOV_M
from solvers.ds_bf_m import Solver as DS_BF_M
from solvers.dsl_bf_m import Solver as DSL_BF_M


def validate_solution(graph, S, demands, solution):
    """
    Validate solution checks wether the given solution is valid.

    A solution is a list with an element per original demand.
    Each element i is a tuple, t1_i and t2_i.

    * t1_i is the tree that satisfies the ith demand. Expressed as a list of ady.
    * t2_i is the slot allocation, it represented by [t2_i[0], t2_i[1])
    """

    """
    We generate a graph that joins all solutions and indicates the demand the edge belongs to

    solcum_graph might be [[(1, [0, 1])], [(2, [0])], []]
    edge (0, 1) is used for demands [0, 1]
    edge (1, 2) is used for demands [0] 
    """
    solcum_graph = [[] for _ in range(len(graph))]
    for d, s in enumerate(solution):
        for i, outgoing in enumerate(s[0]):
            for j in outgoing:
                edge_exists = list(
                    filter(lambda x: x[0] == j, solcum_graph[i]))
                if len(edge_exists) > 0:
                    edge = edge_exists[0]
                    edge[1].append(d)
                else:
                    solcum_graph[i].append((j, [d]))

    # Verify original edge existence
    for u, outgoing in enumerate(solcum_graph):
        for v1 in outgoing:
            # [0] is the outgoing node, [1] is the demand
            if not any([v2 == v1[0] for v2 in graph[u]]):
                raise AssertionError(
                    f'edge {u}_{v1[0]} used in solution not found in original graph')

    # Verify that demands allocation have the required slots and that they don't go over S
    for d, s in enumerate(solution):
        (l, r) = s[1]
        required = demands[d][2]
        if r-l != required:
            raise AssertionError(
                f'demand {d} does not allocate the required amount: l={l}, r={r}, required={required}')
        if r > S:
            raise AssertionError(f'demand {d} allocates over S: r={r}, S={S}')

    # Verify that demands allocation do not overlap on the same edge
    for outgoing in solcum_graph:
        for (_, used_by_demands) in outgoing:
            for d1 in used_by_demands:
                for d2 in used_by_demands:
                    if d1 == d2:
                        continue
                    (l1, r1) = solution[d1][1]
                    (l2, r2) = solution[d2][1]
                    if r1 > l2 and l1 < r2:
                        raise AssertionError(
                            f'overlap in allocation: demand_1={d1}=({l1},{r1}), demand_2={d2}=({l2},{r2})')
    for d in range(len(demands)):
        s = demands[d][0]
        T = demands[d][1]
        reached = dfs(solution[d][0], s)
        for t in T:
            if t not in reached:
                raise AssertionError(f"cannot reach node {t} in demand solution {d}")

solvers = [
    #DR_BF_R,
    #DR_BF_M,
    #DR_BF_F,
    #DR_BF_C,
    #DR_AOV_F,
    #DR_AOV_M,
    #DR_AOV_C,
    #DS_BF_M,
    DSL_BF_M,
]

not_ok = []
for s in solvers:
    for p in problems[:1]:
        g = p["graph"]
        S = p["S"]
        ds = p["demands"]
        solver = s(g, S, ds, name=p["name"])
        print(f"problem: {solver._name}")
        try:
            solution = solver.solve(export = True)
            print(f"solution: {solution}")
            validate_solution(g, S, ds, solution)

        except AssertionError as ex:
            print(ex)
            not_ok.append({
                "name": solver._name,
                "error": ex,
                })
            continue
        print("validation: OK")
        print()

print(not_ok)