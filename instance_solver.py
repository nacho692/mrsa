import argparse
import sys

import resource

resource.setrlimit(resource.RLIMIT_AS, (int(6 * 1024 * 1024 * 1024), int(6 * 1024 * 1024 * 1024)))

import solve
from sample_problems.problems import problems as def_problems
from instance_loader import Loader

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
from solvers.ds_bf_f import Solver as DS_BF_F
from solvers.ds_bf_c import Solver as DS_BF_C

from solvers.ds_acc_m import Solver as DS_ACC_M
from solvers.ds_acc_f import Solver as DS_ACC_F
from solvers.ds_acc_c import Solver as DS_ACC_C

from solvers.nls_f import Solver as NLS_F
from solvers.nls_m import Solver as NLS_M
from solvers.nls_c import Solver as NLS_C

from solvers.ds_bf_m import Solver as DS_BF_M

from solvers.dsl_bf_m import Solver as DSL_BF_M
from solvers.dsl_bf_c import Solver as DSL_BF_C
from solvers.dsl_ascc_c import Solver as DSL_ASCC_C
from solvers.dsl_asb_c import Solver as DSL_ASB_C

from solvers.drl_bf_m import Solver as DRL_BF_M
from solvers.drl_bf_c import Solver as DRL_BF_C

solvers = [
    DR_BF_M,
    DR_BF_F,
    DR_BF_C,

    DR_OB_M,
    DR_OB_F,
    DR_OB_C,

    DR_BSA_M,
    DR_BSA_F,
    DR_BSA_C,

    DR_SC_M,
    DR_SC_F,
    DR_SC_C,

    DR_AOV_F,
    DR_AOV_M,
    DR_AOV_C,

    DS_BF_F,
    DS_BF_M,
    DS_BF_C,

    DS_ACC_M,
    DS_ACC_F,
    DS_ACC_C,

    NLS_F,
    NLS_M,
    NLS_C,

    DSL_BF_M,
    DSL_BF_C,
    DSL_ASCC_C,
    DSL_ASB_C,

    DRL_BF_M,
    DRL_BF_C
]

if __name__ == "__main__":
    
    models_dict = dict(zip(map(lambda s: str(s.__module__.split(".")[1]).lower(), solvers), solvers))

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", "--model", type=str, help=f"The model to execute \
                    {','.join(models_dict.keys())}", default="dr_bf_m")
    parser.add_argument("-t", "--topology", type=str, help="The topologies "
                        "directory, there must be at least one compatible "
                        "topology with the instance file")
    parser.add_argument("-i", "--instance", type=str, help="The instance file, "
                        "must be compatible with the topology")
    parser.add_argument("-e", "--export", type=str, help="Indicates the export "
                        "path, if empty there will be no export", default="export")
    parser.add_argument("-te", "--test", type=bool, help="Runs all solvers with default simple problems", 
                        default=False)
    parser.add_argument("-v", "--validate", type=bool, help="Indicates if the "
                        "solution should be validated", default=True)
    parser.add_argument("-to", "--timeout", type=int, help="Indicates the timeout "
                        "in seconds for the solver, if 0, there is no timeout", 
                        default=60)
    args = parser.parse_args()

    export = args.export != ""
    if args.test:
        # Running default problems
        for p in def_problems:
            for s in solvers:
                solve.solve(
                    s,
                    p,
                    export=export,
                    export_path = args.export,
                    validate=args.validate,
                )
        sys.exit()

    model = args.model.lower()
    if model not in models_dict.keys():
        print(f"Model {model} not found")
        sys.exit()
    if args.instance is None:
        print("If topology is set, instance file must be provided")
        sys.exit()
    if args.timeout < 0:
        print("Timeout must be greater than 0")
        sys.exit()
    timeout = args.timeout
    if timeout == 0:
        timeout = None

    p = Loader.load(args.topology, args.instance)
    solve.solve(
        models_dict[model],
        p,
        export=export,
        export_path = args.export,
        validate=args.validate,
        timeout_seconds=timeout,
    )
    