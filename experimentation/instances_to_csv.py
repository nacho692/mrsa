import os
import csv

def group_selector(row):
    # Group 1
    topology = row["topology"]
    slots = row["slots"]
    if topology == "EuroLarge" and slots in ["10"]:
        return 1
    if topology == "SpanishTelefonica" and slots in ["10", "30"]:
        return 1
    if topology == "PanEuropeanCOST239" and slots in ["10", "30"]:
        return 1
    if topology in ["n6s9"]:
        return 1
    return 0

# Split instance data to columns
def name_to_values(instance):
    instance = instance.replace("instance_", "").replace(".txt","")
    instance_nodes = instance.split("-")[0].replace("n", "")
    instance_edges = instance.split("-")[1].replace("m", "")
    rest = ''.join(instance.split("-")[2:])
    topology = rest.split("_")[0]
    slots = rest.split("_")[1]
    max_sd = rest.split("_")[2]
    terminals = rest.split("_")[3]
    spread = rest.split("_")[4]
    row = {
        "instance": instance,
        "instance_nodes": int(instance_nodes),
        "instance_edges": int(instance_edges),
        "topology": topology,
        "slots": int(slots),
        "max_sd": int(max_sd),
        "terminals": int(terminals),
        "spread": float(spread),
    }
    row["group"] = group_selector(row)
    return row

def get_file_names(directory):
    file_names = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_names.append(file)
    return file_names



directory = '../MRSAinstances/instances'
csv_file = 'experimentation/instances.csv'

file_names = get_file_names(directory)
output = []
for file_name in file_names:
    output.append(name_to_values(file_name))

# Write output to CSV file
with open(csv_file, 'w', newline='') as file:
    fieldnames = output[0].keys()
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output)