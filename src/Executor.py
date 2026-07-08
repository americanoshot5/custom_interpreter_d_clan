from __future__ import annotations

import operator as _op
from collections.abc import Callable
from typing import Any, ClassVar

from common import *
from common import BUILTIN_OPS, FuncDefStmt, ReturnStmt, SetStmt, VarStmt
from interfaces import *
from dataclasses import dataclass

# ── 연산자 테이블 ─────────────────────────────────────────────────────────────
#
# 새로운 연산자 추가 시: _UNARY 또는 _BINARY에 한 줄만 추가하면 됩니다.
# Checker의 BUILTIN_OPS(common.py)도 함께 업데이트하는 것을 잊지 마세요.

_UNARY: dict[str, Callable[[RuntimeValue], RuntimeValue]] = {
    "+":   lambda a: a,
    "-":   _op.neg,
    "not": _op.not_,
    "!":   _op.not_,
}

_BINARY: dict[str, Callable[[RuntimeValue, RuntimeValue], RuntimeValue]] = {
    "+":   _op.add,
    "-":   _op.sub,
    "*":   _op.mul,
    "/":   _op.truediv,  # ZeroDivisionError은 자연스럽게 전파됩니다
    "<":   _op.lt,
    ">":   _op.gt,
    "=":   _op.eq,
    "and": lambda a, b: a and b,
    "or":  lambda a, b: a or b,
}

_ALL_OPS: frozenset[str] = frozenset(_UNARY) | frozenset(_BINARY)


# ── 함수 런타임 값 / 반환 시그널 ──────────────────────────────────────────────

@dataclass
class Function:
    params: tuple[str, ...]
    body: "Stmt"
    closure: "Environment"


class _ReturnSignal(Exception):
    def __init__(self, value: "RuntimeValue") -> None:
        self.value = value


# ── 환경(스코프) ──────────────────────────────────────────────────────────────

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


# ── 실행기 ────────────────────────────────────────────────────────────────────

class SExpressionExecutor(Executor):

    # 새로운 Stmt 종류 추가 시: 이 테이블에 한 줄 + 실행 메서드 하나만 추가하면 됩니다.
    _STMT_DISPATCH: ClassVar[dict[type, str]] = {
        ExpressionStmt: "_execute_exprstmt",
        PrintStmt:      "_execute_printstmt",
        VarStmt:        "_execute_varstmt",
        SetStmt:        "_execute_setstmt",
        IfStmt:         "_execute_ifstmt",
        ForStmt:        "_execute_forstmt",
        BlockStmt:      "_execute_blockstmt",
        FuncDefStmt:    "_execute_funcdefstmt",
        ReturnStmt:     "_execute_returnstmt",
    }

    def __init__(self):
        self._environment = Environment()

    def execute(self, program: Program) -> RuntimeValue:
        result = None
        for stmt in program.statements:
            result = self._execute_stmt(stmt)
        return result

    # ── 문(Stmt) 실행 ─────────────────────────────────────────────────────────

    def _execute_stmt(self, stmt: Stmt) -> RuntimeValue:
        method_name = self._STMT_DISPATCH.get(type(stmt))
        if method_name is None:
            raise ExecuteError(f"Unsupported statement: {type(stmt).__name__}")
        return getattr(self, method_name)(stmt)

    def _execute_exprstmt(self, stmt: ExpressionStmt) -> RuntimeValue:
        return self._execute_expr(stmt.expression)

    def _execute_printstmt(self, stmt: PrintStmt) -> RuntimeValue:
        print(self._execute_expr(stmt.expression))
        return None

    def _execute_varstmt(self, stmt: VarStmt) -> Any | None:
        value = self._execute_expr(stmt.initializer) if stmt.initializer is not None else None
        self._environment.define(stmt.name, value)
        return stmt.name

    def _execute_setstmt(self, stmt: SetStmt) -> RuntimeValue:
        value = self._execute_expr(stmt.value)
        self._environment.assign(stmt.target, value)
        return value

    def _execute_ifstmt(self, stmt: IfStmt) -> RuntimeValue:
        if self._execute_expr(stmt.condition):
            return self._execute_stmt(stmt.then_branch)
        if stmt.else_branch is not None:
            return self._execute_stmt(stmt.else_branch)
        return None

    def _execute_forstmt(self, stmt: ForStmt) -> RuntimeValue:
        start = int(self._execute_expr(stmt.start))
        end   = int(self._execute_expr(stmt.end))
        previous = self._environment
        self._environment = Environment(parent=previous)
        try:
            result = None
            for i in range(start, end):
                self._environment.define(stmt.iterator, i)
                result = self._execute_stmt(stmt.body)
            return result
        finally:
            self._environment = previous

    def _execute_blockstmt(self, block: BlockStmt) -> RuntimeValue:
        previous = self._environment
        self._environment = Environment(parent=previous)
        try:
            result = None
            for stmt in block.statements:
                result = self._execute_stmt(stmt)
            return result
        finally:
            self._environment = previous

    def _execute_funcdefstmt(self, stmt: FuncDefStmt) -> RuntimeValue:
        func = Function(params=stmt.params, body=stmt.body, closure=self._environment)
        self._environment.define(stmt.name, func)
        return stmt.name

    def _execute_returnstmt(self, stmt: ReturnStmt) -> RuntimeValue:
        value = self._execute_expr(stmt.value) if stmt.value is not None else None
        raise _ReturnSignal(value)

    def _call_function(self, func: Function, args: list) -> RuntimeValue:
        if len(args) != len(func.params):
            raise ExecuteError(
                f"Function expects {len(func.params)} argument(s) but got {len(args)}"
            )
        call_env = Environment(parent=func.closure)
        for param, arg in zip(func.params, args):
            call_env.define(param, arg)
        previous = self._environment
        self._environment = call_env
        try:
            self._execute_stmt(func.body)
            return None
        except _ReturnSignal as sig:
            return sig.value
        finally:
            self._environment = previous

    # ── 식(Expr) 평가 ─────────────────────────────────────────────────────────

    def _execute_expr(self, expr: Expr) -> RuntimeValue:
        if isinstance(expr, LiteralExpr):
            return expr.value
        if isinstance(expr, IdentifierExpr):
            return expr.name if expr.name in _ALL_OPS else self._environment.lookup(expr.name)
        if isinstance(expr, ListExpr):
            return self._execute_list_expr(expr)
        raise ExecuteError(f"Unsupported expression: {type(expr).__name__}")

    def _execute_list_expr(self, expr: ListExpr) -> RuntimeValue:
        if not expr.elements:
            raise ExecuteError("Empty s-expression")

        op = self._execute_expr(expr.elements[0])

        if isinstance(op, Function):
            args = [self._execute_expr(arg) for arg in expr.elements[1:]]
            return self._call_function(op, args)

        if not isinstance(op, str) or op not in _ALL_OPS:
            raise ExecuteError(f"'{op}' is not a callable operator")

        args = [self._execute_expr(arg) for arg in expr.elements[1:]]
        n = len(args)

        try:
            if n == 1 and op in _UNARY:
                return _UNARY[op](args[0])
            if n == 2 and op in _BINARY:
                return _BINARY[op](args[0], args[1])
            raise ExecuteError(f"Operator '{op}' does not support {n} argument(s)")
        except ExecuteError:
            raise
        except TypeError as e:
            raise ExecuteError(str(e)) from e


DefaultExecutor = SExpressionExecutor


def execute(program: Program) -> RuntimeValue:
    return SExpressionExecutor().execute(program)


__all__ = ["DefaultExecutor", "SExpressionExecutor", "execute"]
