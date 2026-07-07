from __future__ import annotations

from typing import Any

from common import *
from common import VarStmt
from interfaces import *
from dataclasses import dataclass

OPERATORS = ["+", "-", "*", "/", "<", ">", "!"]

@dataclass
class Environment:
    parent: Environment | None = None

    def __post_init__(self):
        self._values: dict[str, RuntimeValue] = {}

    def define(self, name: str, value: RuntimeValue) -> None:
        self._values[name] = value

    def lookup(self, name: str) -> RuntimeValue:
        if name in self._values:
            return self._values[name]

        if self.parent is not None:
            return self.parent.lookup(name)

        raise ExecuteError(f"Undefined variable '{name}'")

    def assign(self, name: str, value: RuntimeValue) -> None:
        if name in self._values:
            self._values[name] = value
            return

        if self.parent is not None:
            self.parent.assign(name, value)
            return

        raise ExecuteError(f"Undefined variable '{name}'")

class SExpressionExecutor(Executor):
    def __init__(self):
        self._environment = Environment()

    def execute(self, program: Program) -> RuntimeValue:
        result = None

        for stmt in program.statements:
            result = self._execute_stmt(stmt)

        return result

    def _execute_stmt(self, stmt: Stmt) -> RuntimeValue:
        if isinstance(stmt, ExpressionStmt):    return self._execute_expr(stmt.expression)
        if isinstance(stmt, PrintStmt):         return self._execute_printstmt(stmt.expression)
        if isinstance(stmt, VarStmt):           return self._execute_varstmt(stmt)
        if isinstance(stmt, IfStmt):            return self._execute_ifstmt(stmt)
        if isinstance(stmt, ForStmt):           return self._execute_forstmt(stmt)
        if isinstance(stmt, BlockStmt):         return self._execute_blockstmt(stmt)

        raise ExecuteError(f"Unsupported statement: {type(stmt).__name__}")

    def _execute_printstmt(self, expr: Expr) -> RuntimeValue:
        value = self._execute_expr(expr)
        print(value)
        return None

    def _execute_ifstmt(self, stmt: IfStmt) -> RuntimeValue:
        if self._execute_expr(stmt.condition):
            return self._execute_stmt(stmt.then_branch)
        else:
            return self._execute_stmt(stmt.else_branch)

    def _execute_forstmt(self, stmt: ForStmt) -> RuntimeValue:
        ...

    def _execute_varstmt(self, stmt: VarStmt) -> Any | None:
        value = None

        if stmt.initializer is not None:
            value = self._execute_expr(stmt.initializer)

        self._environment.define(stmt.name, value)

        return stmt.name

    def _execute_blockstmt(self, block: BlockStmt):

        previous = self._environment
        self._environment = Environment(parent=previous)

        try:
            result = None

            for stmt in block.statements:
                result = self._execute_stmt(stmt)

            return result

        finally:
            self._environment = previous

    def _execute_expr(self, expr: Expr) -> RuntimeValue:
        if isinstance(expr, LiteralExpr):       return expr.value
        if isinstance(expr, IdentifierExpr):
            if expr.name in OPERATORS:          return expr.name
            else:                               return self._environment.lookup(expr.name)
        if isinstance(expr, ListExpr):          return self._execute_list_expr(expr)

        raise ExecuteError(f"Unsupported expression: {type(expr).__name__}")

    def _execute_list_expr(self, expr: ListExpr) -> RuntimeValue:
        if not expr.elements:
            raise ExecuteError("Empty s-expression")

        operator = self._execute_expr(expr.elements[0])
        operands = [self._execute_expr(arg) for arg in expr.elements[1:]]

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

