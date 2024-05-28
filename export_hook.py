from cplex.callbacks import MIPInfoCallback
import json

class ExportHook:
    def __init__(self, path="export"):
        self.path = path
        self.name = ""
        self.info_cb = InfoCallback

    def hook_before_solve(self, m):
        self.name = m.name
        self.info_cb = m.register_callback(InfoCallback)
        m.print_information()
        m.export_as_lp(f"{self.path}/{self.name}.lp")

    def hook_after_solve(self, m):
        if m.solve_details is not None:
            json_export = m.solve_details.__dict__.copy()
            json_export["constraints"] = m.number_of_constraints
            json_export["name"] = self.name
            json_export["linear_relaxation"] = self.info_cb.linear_relaxation
            with open(f"{self.path}/{self.name}_solution_details.json", "w") as f:
                json.dump(json_export, f, sort_keys=True)
        if m.solution is not None:
            m.solution.export(f"{self.path}/{self.name}_solution.json")

class InfoCallback(MIPInfoCallback):
    linear_relaxation = None
    
    def __call__(self):
        if self.linear_relaxation == None:
            self.linear_relaxation = self.get_best_objective_value()