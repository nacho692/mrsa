problems = [
    {
        "name": "simple graph",
        "graph": [
            # v0
            [1],
            # v1
            [2],
            # v2
            [],
        ],
        "demands": [(0, {2}, 1)],
        "S": 1,
    },
    {
        "name": "two terminals simple",
        "graph": [
            # v0
            [1],
            # v1
            [2],
            # v2
            [],
        ],
        "demands": [(0, {1, 2}, 1)],
        "S": 1,
    },
    {
        "name": "two terminals",
        "graph": [
            # v0
            [1],
            # v1
            [2],
            # v2
            [],
        ],
        "demands": [(0, {1, 2}, 2)],
        "S": 2,
    },
    {
        "name": "two demands simple",
        "graph": [
            # v0
            [1],
            # v1
            [2],
            # v2
            [],
        ],
        "demands": [(0, {2}, 1), (0, {1}, 1)],
        "S": 2,
    },
        {
        "name": "two demands",
        "graph": [
            # v0
            [1],
            # v1
            [2, 0],
            # v2
            [1],
        ],
        "demands": [(0, {2}, 1), (0, {1}, 1)],
        "S": 2,
    },
    {
        "name": "g2",
        "graph": [
            # v0
            [1, 2],
            # v1
            [0, 3],
            # v2
            [0, 3],
            # v3
            [1, 2],
        ],
        "demands": [(0, {3}, 10), (0, {3}, 10)],
        "S": 10,
    },
    {
        "name": "g2",
        "graph": [
            # v0
            [1, 2],
            # v1
            [0, 3],
            # v2
            [0, 3],
            # v3
            [1, 2],
        ],
        "demands": [(0, {3}, 10), (0, {3}, 10)],
        "S": 10,
    },
    {
        "name": "g3",
        "graph": [
            # v0
            [1, 4],
            # v1
            [0, 2, 3],
            # v2
            [1],
            # v3
            [1],
            # v4
            [0],
        ],
        "demands": [(0, {2, 3}, 5), (0, {3, 4}, 5)],
        "S": 10,
    },
]
