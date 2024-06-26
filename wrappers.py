from ast import Raise
from typing import Callable
from docplex.mp.model import Model
from cplex.callbacks import MIPInfoCallback
import json
from datetime import datetime, timedelta
from typing import Callable
from cplex.callbacks import MIPInfoCallback
from cplex.callbacks import MIPInfoCallback
from typing import Callable,List
from multiprocessing import Process, Manager
from cplex import Aborter
from solvers.solvers import Res
import time

class Export:
    @staticmethod
    def callback(callback: MIPInfoCallback, exportcall: 'Export'):
        if exportcall.linear_relaxation == None:
            exportcall.linear_relaxation = callback.get_best_objective_value()
        return
    
    def __init__(self, path="export"):
        self.path = path
        self.linear_relaxation = None

    def call(self) -> Callable[[MIPInfoCallback], None]:
        return lambda c: Export.callback(c, self)

    def print_information(self, m: Model):
        m.print_information()
        #m.export_as_lp(f"{self.path}/{m.name}.lp")
    def print_solution_information(self, m: Model):
        print(m.solve_status)

    def export(self, e: Exception | None, m: Model):
        json_export = {}
        if m.solve_details is not None:
            json_export = m.solve_details.__dict__.copy()

            if m.solution is not None:
                for k, v in m.solution.get_cuts().items():
                    json_export[f"cuts_{k}"] = v
            
                json_export["objective_value"] = m.solution.objective_value

        json_export["constraints"] = m.number_of_constraints
        json_export["name"] = m.name
        json_export["variables_binary"] = m.number_of_binary_variables
        json_export["variables_integer"] = m.number_of_integer_variables
        json_export["variables_continuous"] = m.number_of_continuous_variables
        json_export["variables"] = m.number_of_variables
        json_export["variables_user"] = m.number_of_user_variables
        
        json_export["linear_relaxation"] = self.linear_relaxation

        if e is not None:
            json_export["exception"] = f"{e.__class__}:{str(e)}"

        with open(f"{self.path}/{m.name}_solution_details.json", "w") as f:
            json.dump(json_export, f, sort_keys=True)

        if m.solution is not None:
            m.solution.export(f"{self.path}/{m.name}_solution.json")


class Timeout:
    def __init__(self, timeout: timedelta):
        self.timeout = timeout

    def hook_before_solve(self, m: Model):
        m.set_time_limit(self.timeout.seconds)
        return

class HookMIPInfoCallback:
    calls : List[Callable[[MIPInfoCallback], None]] = []

    def register_call(self, call: Callable[[MIPInfoCallback], None]):
        self.calls.append(call)

    def hook_before_solve(self, m):
        cb = m.register_callback(_HookMIPInfoCallback)
        for c in self.calls:
            cb._calls.append(c)

class _HookMIPInfoCallback(MIPInfoCallback):

    _calls : List[Callable[[MIPInfoCallback], None]] = []

    def __call__(self):
        for c in self._calls:
            c(self)