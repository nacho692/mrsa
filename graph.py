def dfs(graph, start):
    reached = []
    
    to_visit = [start]
    while len(to_visit) > 0:
        u = to_visit.pop()
        if u in reached:
            continue
        reached.append(u)
        to_visit =  to_visit + graph[u]

    return reached