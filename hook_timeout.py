from datetime import datetime, timedelta
from typing import Callable
from cplex.callbacks import MIPInfoCallback

class HookTimeout:
    @staticmethod
    def callback(callback: MIPInfoCallback, timeoutcall: 'HookTimeout'):
        return
    
    def __init__(self, timeout: timedelta):
        self.timeout = timeout

    def call(self) -> Callable[[MIPInfoCallback], None]:
        return lambda c: HookTimeout.callback(c, self)

    def hook_before_solve(self, m):
        m.set_time_limit(self.timeout.seconds)
        return

    def hook_after_solve(self, m):
        pass