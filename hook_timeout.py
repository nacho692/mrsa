from datetime import datetime, timedelta
from typing import Callable
from cplex.callbacks import MIPInfoCallback

class HookTimeout:
    @staticmethod
    def callback(callback: MIPInfoCallback, timeoutcall: 'HookTimeout'):
        if timeoutcall.aborted:
            pass

        if callback.get_time() - callback.get_start_time() > timeoutcall.timeout.seconds:
            timeoutcall.aborted = True
            callback.abort()
        return
    
    def __init__(self, timeout: timedelta):
        self.timeout = timeout
        self.aborted = False

    def call(self) -> Callable[[MIPInfoCallback], None]:
        return lambda c: HookTimeout.callback(c, self)

    def hook_before_solve(self, m):
        pass

    def hook_after_solve(self, m):
        pass