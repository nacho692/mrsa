from typing import Callable
from docplex.mp.model import Model
from cplex.callbacks import MIPInfoCallback
import json

class HookExport:
    @staticmethod
    def callback(callback: MIPInfoCallback, exportcall: 'HookExport'):
        if exportcall.linear_relaxation == None:
            exportcall.linear_relaxation = callback.get_best_objective_value()
        return
    
    def __init__(self, path="export"):
        self.path = path
        self.linear_relaxation = None

    def call(self) -> Callable[[MIPInfoCallback], None]:
        return lambda c: HookExport.callback(c, self)

    def hook_before_solve(self, m):
        m.print_information()
        m.export_as_lp(f"{self.path}/{m.name}.lp")

    def hook_after_solve(self, m: Model):
        if m.solve_details is not None:
            json_export = m.solve_details.__dict__.copy()
            json_export["constraints"] = m.number_of_constraints
            json_export["name"] = m.name
            json_export["linear_relaxation"] = self.linear_relaxation

            if m.solution is not None:
                for k, v in m.solution.get_cuts().items():
                    json_export[f"cuts_{k}"] = v
            
                json_export["objective_value"] = m.solution.objective_value

            with open(f"{self.path}/{m.name}_solution_details.json", "w") as f:
                json.dump(json_export, f, sort_keys=True)
        if m.solution is not None:
            m.solution.export(f"{self.path}/{m.name}_solution.json")
