from datetime import datetime, timedelta
from cplex.callbacks import MIPInfoCallback
import json

class TimeoutHook:
    def __init__(self, timeout: timedelta):
        self.timeout = timeout

    def hook_before_solve(self, m):
        cb = m.register_callback(TimeoutCallback)
        cb._starttime = datetime.now()
        cb._timeout = self.timeout

    def hook_after_solve(self, m):
        pass            

class TimeoutCallback(MIPInfoCallback):

    _starttime: datetime
    _timeout: timedelta
    aborted = False

    def __call__(self):
        if not self.aborted:
            timeused = datetime.now() - self._starttime
            if timeused > self._timeout:
                self.abort()
                self.aborted = True
