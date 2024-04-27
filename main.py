from sample_problems.problems import problems

import solve

from solvers.dr_bf_r import Solver as DR_BF_R
from solvers.dr_bf_m import Solver as DR_BF_M
from solvers.dr_bf_f import Solver as DR_BF_F
from solvers.dr_bf_c import Solver as DR_BF_C
from solvers.dr_aov_c import Solver as DR_AOV_C
from solvers.dr_aov_f import Solver as DR_AOV_F
from solvers.dr_aov_m import Solver as DR_AOV_M
from solvers.ds_bf_m import Solver as DS_BF_M
from solvers.dsl_bf_m import Solver as DSL_BF_M



solvers = [
    #DR_BF_R,
    #DR_BF_M,
    #DR_BF_F,
    #DR_BF_C,
    #DR_AOV_F,
    #DR_AOV_M,
    #DR_AOV_C,
    DS_BF_M,
    #DSL_BF_M,
]

solve.solve(
    solvers,
    problems,
    True
)
