from docplex.mp.model import Model
from typing import Any, Callable

T_graph = list[list[int]]
Res = list[tuple[T_graph, tuple[int, int]]]

def solve_hook(func: Callable[[Any, Model], Res]):
    def wrapper(self: Any, m: Model):
        return self._hook.wrap_solve(m, lambda: func(self, m))
    return wrapper

class BaseHook:
    def __init__(self):
        return
    
    def hook_before_solve(self, m: Model):
        return
    
    def wrap_solve(self, m: Model, func):
        return func()
