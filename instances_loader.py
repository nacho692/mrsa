import os
import collections

T_graph = list[list[int]]
T_demand = tuple[int, set[int], int]


class Loader:
    @staticmethod
    def load(topologies_path="../RSAinstances/topologies",
             instances_path="../RSAinstances/instances",
             ) -> list[dict]:

        problems = []

        graphs = {}
        for root, _, files in os.walk(topologies_path):
            for f in files:
                with open(f"{root}/{f}", 'r') as file:
                    graphs[f.replace(".txt", "")] = Loader.to_graph(file)

        for root, _, files in os.walk(instances_path):
            for f in files:
                with open(f"{root}/{f}", 'r') as file:
                    graph_name = f.split("_")[1]
                    problem_name = f.replace("instance_", "").replace(".txt", "")
                    demands, S = Loader.to_demands(file)
                    problems.append({
                        "name": problem_name,
                        "graph": graphs[graph_name],
                        "S": S,
                        "demands": demands,
                    })

        return problems

    @staticmethod
    def to_graph(file) -> T_graph:
        line = file.readline()
        while line.startswith("#"):
            line = file.readline()
        # nodes, edges; edges is ignored
        nodes, _ = line.split()
        graph = [[] for _ in range(int(nodes))]

        for line in file:
            l = line.split()
            graph[int(l[0])].append(int(l[1]))

        return graph

    @staticmethod
    def to_demands(file) -> tuple[list[T_demand], int]:

        d = {}
        line = file.readline()
        while line.startswith("#"):
            line = file.readline()
        # S, |D|, ignore |D|
        S, _ = line.split()

        for line in file:
            source, terminal, slots = line.split()
            if source not in d:
                d[source] = [[], 0]
            d[source][0].append(int(terminal))
            d[source][1] += int(slots)

        demands = []
        for k, v in d.items():
            demands.append((k, set(v[0]), v[1]))

        return demands, S

Loader.load()
