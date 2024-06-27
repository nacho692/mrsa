import os
import datetime
import signal
import pandas as pd

instances_folder = "../MRSAinstances/instances"
topologies_folder = "../MRSAinstances/topologies"
export_folder = "export"
group = 1

# Get a list of all instance files in the instances folder recursively
instance_files = []
for root, dirs, files in os.walk(instances_folder):
    for file in files:
        instance_files.append(os.path.join(root, file))

solvers = ["DR_BF_M", "DR_BF_F", "DR_BF_C", "DR_OB_M", "DR_OB_F", "DR_OB_C", "DR_BSA_M", "DR_BSA_F", "DR_BSA_C", "DR_SC_M", "DR_SC_F", "DR_SC_C", "DR_AOV_F", "DR_AOV_M", "DR_AOV_C", "DS_BF_F", "DS_BF_M", "DS_BF_C", "DS_ACC_M", "DS_ACC_F", "DS_ACC_C", "NLS_F", "NLS_M", "NLS_C", "DSL_BF_M", "DSL_BF_C", "DSL_ASCC_C", "DSL_ASB_C", "DRL_BF_M", "DRL_BF_C"]


instances = pd.read_csv("experimentation/instances.csv")
instances = instances[instances["group"] == group]
total = len(instances)*len(solvers)
i = 1

for instance_name in instances["instance"]:
    filtered_files = list(filter(lambda file: instance_name in file, instance_files))
    if len(filtered_files) != 1:
        raise AssertionError(f"More than 1 or no {instance_name} found in the instance files")
    file_path = filtered_files[0]
    file_name = os.path.basename(file_path)
    
    for solver in solvers:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} - Processing {i}/{total}")
        i+=1

        execution_name = f"{solver.lower()}:{instance_name}"

        if f"{execution_name}_solution_details.json" in os.listdir(export_folder):
            print(f"Skipping {file_name} as it already exists in the export folder")
            continue
        print(f"Running instance loader for {file_name} with solver {solver}")

        solver_arguments = [
            "-t", topologies_folder, 
            "-i", file_path, 
            "-e", export_folder,
            "-v", "True",
            "-m", solver,
            "-to", "60"]
        os.system(f"python instance_solver.py {' '.join(solver_arguments)}")
        print()
