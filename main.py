import r_sf

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
s = 1000


r_sf.solve(g1, s, ds)
