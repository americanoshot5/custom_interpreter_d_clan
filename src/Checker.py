from __future__ import annotations

from common import CheckError, Expr, ExpressionStmt, ListExpr, Program, Stmt
from interfaces import Checker


class StaticChecker(Checker):
    def check(self, program: Program) -> None:
        for statement in program.statements:
            self._check_statement(statement)

    def _check_statement(self, statement: Stmt) -> None:
        if isinstance(statement, ExpressionStmt):
            self._check_expression(statement.expression)
            return
        raise CheckError(f"Unsupported statement type: {type(statement).__name__}")

    def _check_expression(self, expression: Expr) -> None:
        if isinstance(expression, ListExpr):
            for element in expression.elements:
                self._check_expression(element)


DefaultChecker = StaticChecker


def check(program: Program) -> None:
    StaticChecker().check(program)


__all__ = ["DefaultChecker", "StaticChecker", "check"]

