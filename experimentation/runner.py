import os
import datetime
import signal
import pandas as pd

instances_folder = "../MRSAinstances/instances"
topologies_folder = "../MRSAinstances/topologies"
export_folder = "export"

# Get a list of all instance files in the instances folder recursively
instance_files = []
for root, dirs, files in os.walk(instances_folder):
    for file in files:
        instance_files.append(os.path.join(root, file))

solvers = ["DR_BF_M", "DR_BF_F", "DR_BF_C", "DR_OB_M", "DR_OB_F", "DR_OB_C", "DR_BSA_M", "DR_BSA_F", "DR_BSA_C", "DR_SC_M", "DR_SC_F", "DR_SC_C", "DR_AOV_F", "DR_AOV_M", "DR_AOV_C", "DS_BF_F", "DS_BF_M", "DS_BF_C", "DS_ACC_M", "DS_ACC_F", "DS_ACC_C", "NLS_F", "NLS_M", "NLS_C", "DSL_BF_M", "DSL_BF_C", "DSL_ASCC_C", "DSL_ASB_C", "DRL_BF_M", "DRL_BF_C"]

total = len(instance_files)*len(solvers)
i = 1

# Group selection
group = 1
instances = pd.read_csv("experimentation/instances.csv")

# Iterate over each instance file
for instance_file in instance_files:
    file_name = os.path.basename(instance_file)
    
    instance_name = file_name.replace('instance_','').replace('.txt','')
    if instances[(instances["instance"] == instance_name) & (instances["group"] == group)].size == 0:
        continue

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
            "-i", instance_file, 
            "-e", export_folder,
            "-v", "True",
            "-m", solver,
            "-to", "600"]
        os.system(f"python instance_solver.py {' '.join(solver_arguments)}")
        print()


    