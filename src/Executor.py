from __future__ import annotations
from common import *
from interfaces import *

class SExpressionExecutor(Executor):
    def execute(self, program: Program):
        result = None
        for stmt in program.statements:
            result = self._execute_stmt(stmt)
        return result

    def _execute_stmt(self, stmt):
        if isinstance(stmt, ExpressionStmt):
            return self._evaluate(stmt.expression)
        raise ExecuteError("Unsupported statement")

    def _evaluate(self, expr):
        if isinstance(expr, LiteralExpr):
            return expr.value

        raise ExecuteError("Unsupported expression")


DefaultExecutor = SExpressionExecutor


def execute(program: Program) -> RuntimeValue:
    return SExpressionExecutor().execute(program)


__all__ = ["DefaultExecutor", "SExpressionExecutor", "execute"]

