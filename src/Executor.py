from __future__ import annotations

from common import ExecuteError, Program, RuntimeValue
from interfaces import Executor


class SExpressionExecutor(Executor):
    def execute(self, program: Program) -> RuntimeValue:
        raise ExecuteError("Executor implementation is not ready yet.")


DefaultExecutor = SExpressionExecutor


def execute(program: Program) -> RuntimeValue:
    return SExpressionExecutor().execute(program)


__all__ = ["DefaultExecutor", "SExpressionExecutor", "execute"]

