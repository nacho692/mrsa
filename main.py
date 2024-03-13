import r_sf

# g1 is a DAG
g1 = [
    # v0 
    [1, 2],
    # v1
    [0, 3, 2],
    # v2
    [0, 1],
    # v3
    [1]
]

r_sf.solve(g1)