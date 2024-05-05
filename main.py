from sample_problems.problems import problems as def_problems

import solve
from instances_loader import Loader

from solvers.dr_bf_r import Solver as DR_BF_R

from solvers.dr_bf_m import Solver as DR_BF_M
from solvers.dr_bf_f import Solver as DR_BF_F
from solvers.dr_bf_c import Solver as DR_BF_C

from solvers.dr_ob_m import Solver as DR_OB_M
from solvers.dr_ob_f import Solver as DR_OB_F
from solvers.dr_ob_c import Solver as DR_OB_C

from solvers.dr_bsa_m import Solver as DR_BSA_M
from solvers.dr_bsa_f import Solver as DR_BSA_F
from solvers.dr_bsa_c import Solver as DR_BSA_C

from solvers.dr_sc_m import Solver as DR_SC_M
from solvers.dr_sc_f import Solver as DR_SC_F
from solvers.dr_sc_c import Solver as DR_SC_C

from solvers.dr_aov_f import Solver as DR_AOV_F
from solvers.dr_aov_m import Solver as DR_AOV_M
from solvers.dr_aov_c import Solver as DR_AOV_C

from solvers.ds_bf_m import Solver as DS_BF_M

from solvers.dsl_bf_m import Solver as DSL_BF_M

# Generated Instances
problems = [ p for p in Loader.load() if len(p["graph"]) <= 10]

# Default Problems
#problems = [ p for p in def_problems]


solvers = [
    # DR_BF_R <- Does not work, see doc or pdf,
    #DR_BF_M,
    #DR_BF_F,
    #DR_BF_C,

    #DR_OB_M,
    #DR_OB_F,
    #DR_OB_C,

    #DR_BSA_M,
    #DR_BSA_F,
    #DR_BSA_C,

    DR_SC_M,
    DR_SC_F,
    DR_SC_C,

    #DR_AOV_F,
    #DR_AOV_M,
    #DR_AOV_C,

    #DS_BF_M,

    #DSL_BF_M,
]

solve.solve(
    solvers,
    problems,
    export=False,
    validate=True
)
