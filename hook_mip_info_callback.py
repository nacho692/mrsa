from cplex.callbacks import MIPInfoCallback
from typing import Callable,List

class HookMIPInfoCallback:
    calls : List[Callable[[MIPInfoCallback], None]] = []

    def register_call(self, call: Callable[[MIPInfoCallback], None]):
        self.calls.append(call)

    def hook_before_solve(self, m):
        cb = m.register_callback(_HookMIPInfoCallback)
        for c in self.calls:
            cb._calls.append(c)
    
    def hook_after_solve(self, m):
        pass


class _HookMIPInfoCallback(MIPInfoCallback):

    _calls : List[Callable[[MIPInfoCallback], None]] = []

    def __call__(self):
        for c in self._calls:
            c(self)