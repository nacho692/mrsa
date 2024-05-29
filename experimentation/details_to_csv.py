import json
import os
import csv

path = "export"

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
            details.append(json.load(jsonf))
    return details

def solution_details_to_csv(path: str):

    jsons = json_compiler(path)
    if len(jsons) == 0:
        return
    
    with open("experimentation/data.csv", "w", newline="") as output_file:
        writer = csv.DictWriter(output_file, jsons[0].keys())
        writer.writeheader()
        writer.writerows(jsons)

solution_details_to_csv(path)