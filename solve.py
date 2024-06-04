from graph import dfs
from hook_export import HookExport
from hook_mip_info_callback import HookMIPInfoCallback
from hook_timeout import HookTimeout
from datetime import timedelta,datetime

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

    # Verify that demands allocation do 
    # not overlap on the same edge
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
                            f'overlap in allocation: demand_{d1}=({l1},{r1},v={demands[d1][2]}), demand_{d2}=({l2},{r2},v={demands[d2][2]})')
    for d in range(len(demands)):
        s = demands[d][0]
        T = demands[d][1]
        reached = dfs(solution[d][0], s)
        for t in T:
            if t not in reached:
                raise AssertionError(f"cannot reach node {t} in demand solution {d}")

def solve(solvers: list, problems: list[dict], export = False, export_path = 'export', validate = False):
    not_ok = []
    total = len(solvers)*len(problems)
    i = 1
    for s in solvers:
        for p in problems:
            now = datetime.now()
            print(f"{now}: setting up problem {i}/{total}")
            i += 1

            g = p["graph"]
            S = p["S"]
            ds = p["demands"]
            solver = s(g, S, ds, name=p["name"])

            hook_cb = HookMIPInfoCallback()
            solver.register_hook(hook_cb)
            
            hook_to = HookTimeout(timedelta(seconds=60))
            hook_cb.register_call(hook_to.call())
            solver.register_hook(hook_to)

            if export:
                hook_ex = HookExport(export_path)
                hook_cb.register_call(hook_ex.call())
                solver.register_hook(hook_ex)
                
            print(f"problem: {solver._name}")
            print(p)
            try:
                solution = solver.solve()
                print(f"solution: {solution}")
                if validate:
                    validate_solution(g, S, ds, solution)
            except Exception as ex:
                print(ex)
                print()
                not_ok.append({
                    "name": solver._name,
                    "error": ex,
                    })
                
                continue
            print("validation: OK")
            print()

    print(not_ok)