import dr_bf_r

"""
Validate solution checks wether the given solution is valid.

A solution is a list with an element per original demand.
Each element i is a tuple, t1_i and t2_i.

* t1_i is the tree that satisfies the ith demand. Expressed as a list of ady.
* t2_i is the slot allocation, it represented by [t2_i[0], t2_i[1])
"""
def validate_solution(graph, S, demands, solution):

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
                edge_exists = list(filter(lambda x: x[0] == j, solcum_graph[i]))
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
                raise AssertionError(f'edge {u}_{v1[0]} used in solution not found in original graph' )

    # Verify that demands allocation have the required slots and that they don't go over S
    for d, s in enumerate(solution):
        (l, r) = s[1]
        required = demands[d][2]
        if r-l != required:
            raise AssertionError(f'demand {d} does not allocate the required amount: l={l}, r={r}, required={required}')
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
                        raise AssertionError(f'overlap in allocation: demand_1={d1}=({l1},{r1}), demand_2={d2}=({l2},{r2})')
# g1 is a DAG
g1 = [
    # v0 
    [1],
    # v1
    [2, 0],
    # v2
    [1],
]

ds = [(0, {2}, 500), (0, {1}, 500)]
S = 1000


solution = dr_bf_r.solve(g1, S, ds)

validate_solution(g1, S, ds, solution)
