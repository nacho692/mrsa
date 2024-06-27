import json
import os
import csv
from pydoc import writedoc

path = "group_1"
output_path = "experimentation/group_1.csv"

def subdirs(path: str):
    for entry in os.scandir(path):
        if not entry.name.startswith(".") and entry.is_file():
            yield entry.name

def solution_details_files(path: str):
    for f in subdirs(path):
        if f.endswith("solution_details.json"):
            yield f

def json_compiler(path: str):
    details = []
    if not path.endswith("/"):
        path = path + "/"
    
    for f in solution_details_files(path):
        with open(path + f, "r") as jsonf:
            a = json.load(jsonf)
            details.append(a)
    return details

def solution_details_to_csv(path: str):

    jsons = json_compiler(path)
    if len(jsons) == 0:
        return
    
    # Get all unique keys from the jsons
    keys = set().union(*(d.keys() for d in jsons))

    # Create a list of dictionaries with all keys present in each dictionary
    complete_jsons = [{key: d.get(key) for key in keys} for d in jsons]

    with open(output_path, "w", newline="") as output_file:
        # Write the complete_jsons to the CSV file
        writer = csv.DictWriter(output_file, complete_jsons[0].keys())
        writer.writeheader()
        writer.writerows(complete_jsons)

solution_details_to_csv(path)