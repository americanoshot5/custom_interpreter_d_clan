from __future__ import annotations
from common import *
from interfaces import *

class SExpressionExecutor(Executor):
    def execute(self, program: Program) -> RuntimeValue:
        result = None

        for stmt in program.statements:
            result = self._execute_stmt(stmt)

        return result

    def _execute_stmt(self, stmt: Stmt) -> RuntimeValue:
        if isinstance(stmt, ExpressionStmt):
            return self._calculate_expr(stmt.expression)
        if isinstance(stmt, PrintStmt):
            ...
        if isinstance(stmt, VarStmt):
            ...
        if isinstance(stmt, IfStmt):
            ...
        if isinstance(stmt, ForStmt):
            ...
        if isinstance(stmt, BlockStmt):
            ...

        raise ExecuteError(f"Unsupported statement: {type(stmt).__name__}")

    def _calculate_expr(self, expr: Expr) -> RuntimeValue:
        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, IdentifierExpr):
            return expr.name

        if isinstance(expr, ListExpr):
            return self._calculate_list_expr(expr)

        raise ExecuteError(f"Unsupported expression: {type(expr).__name__}")

    def _calculate_list_expr(self, expr: ListExpr) -> RuntimeValue:
        if not expr.elements:
            raise ExecuteError("Empty s-expression")

        operator = self._calculate_expr(expr.elements[0])
        operands = [self._calculate_expr(arg) for arg in expr.elements[1:]]

        match operator:
            case "+":
                if len(operands) == 1:  return operands[0]
                return operands[0] + operands[1]

            case "-":
                if len(operands) == 1:  return -operands[0]
                return operands[0] - operands[1]

            case "*":
                if len(operands) == 1:  raise ExecuteError("'*' expects exactly two operands")
                return operands[0] * operands[1]

            case "/":
                if len(operands) == 1:  raise ExecuteError("'/' expects exactly two operands")
                if operands[1] == 0:    raise ZeroDivisionError("Division by zero")
                return operands[0] / operands[1]

            case "<":
                if len(operands) == 1:  raise ExecuteError("'<' expects exactly two operands")
                return operands[0] < operands[1]

            case ">":
                if len(operands) == 1:  raise ExecuteError("'>' expects exactly two operands")
                return operands[0] > operands[1]

            case "!":
                if len(operands) == 2: raise ExecuteError("'!' expects exactly one operand")
                return not operands[0]

            case _:
                raise ExecuteError(f"Unsupported operator")


DefaultExecutor = SExpressionExecutor


def execute(program: Program) -> RuntimeValue:
    return SExpressionExecutor().execute(program)


__all__ = ["DefaultExecutor", "SExpressionExecutor", "execute"]

