from __future__ import annotations

import operator as _op
from collections.abc import Callable as _Callable
from dataclasses import dataclass

from common import (
    ArrayExpr,
    ArrayIndexExpr,
    BUILTIN_OPS,
    BlockStmt,
    ClassStmt,
    DotExpr,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDefStmt,
    IdentifierExpr,
    IfStmt,
    ImportStmt,
    ListExpr,
    LiteralExpr,
    NewExpr,
    PrintStmt,
    Program,
    ReturnStmt,
    SetStmt,
    SourceLocation,
    Stmt,
    SuperExpr,
    VarStmt,
)

# ── 정적 바인딩 (Static Binding) ─────────────────────────────────────────────
#
# 각 IdentifierExpr/SetStmt에 대해 해당 변수가 몇 번째 상위 스코프에 있는지
# (distance)를 미리 계산한다.
#
#   BindingMap[id(node)] = distance
#   distance 0 = 현재 스코프, 1 = 1단계 위, n = n단계 위

BindingMap = dict[int, int]  # id(IdentifierExpr | SetStmt) → scope distance


class StaticBinder:
    """
    검사된 AST를 순회하며 변수 참조·할당마다 스코프 거리를 미리 계산한다.

    반환된 BindingMap 은 Executor 가 스코프 체인을 탐색하지 않고
    계산된 위치로 즉시 접근하는 데 활용할 수 있다.
    """

    def bind(self, program: Program) -> BindingMap:
        bindings: BindingMap = {}
        scopes: list[set[str]] = [set(BUILTIN_OPS)]
        for stmt in program.statements:
            self._bind_stmt(stmt, scopes, bindings)
        return bindings

    # ── Stmt ──────────────────────────────────────────────────────────────

    def _bind_stmt(
        self, stmt: Stmt, scopes: list[set[str]], bindings: BindingMap
    ) -> None:
        if isinstance(stmt, VarStmt):
            if stmt.initializer is not None:
                self._bind_expr(stmt.initializer, scopes, bindings)
            scopes[-1].add(stmt.name)

        elif isinstance(stmt, SetStmt):
            dist = self._resolve_distance(stmt.target, scopes)
            if dist is not None:
                bindings[id(stmt)] = dist
            self._bind_expr(stmt.value, scopes, bindings)

        elif isinstance(stmt, PrintStmt):
            self._bind_expr(stmt.expression, scopes, bindings)

        elif isinstance(stmt, ExpressionStmt):
            self._bind_expr(stmt.expression, scopes, bindings)

        elif isinstance(stmt, BlockStmt):
            scopes.append(set())
            for s in stmt.statements:
                self._bind_stmt(s, scopes, bindings)
            scopes.pop()

        elif isinstance(stmt, IfStmt):
            self._bind_expr(stmt.condition, scopes, bindings)
            self._bind_stmt(stmt.then_branch, scopes, bindings)
            if stmt.else_branch is not None:
                self._bind_stmt(stmt.else_branch, scopes, bindings)

        elif isinstance(stmt, ForStmt):
            self._bind_expr(stmt.start, scopes, bindings)
            self._bind_expr(stmt.end, scopes, bindings)
            scopes.append({stmt.iterator})
            self._bind_stmt(stmt.body, scopes, bindings)
            scopes.pop()

        elif isinstance(stmt, FuncDefStmt):
            scopes[-1].add(stmt.name)
            scopes.append(set(stmt.params))
            self._bind_stmt(stmt.body, scopes, bindings)
            scopes.pop()

        elif isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                self._bind_expr(stmt.value, scopes, bindings)

        elif isinstance(stmt, ClassStmt):
            scopes[-1].add(stmt.name)

        elif isinstance(stmt, ImportStmt):
            # import 는 alias 를 현재 스코프에 등록한다
            scopes[-1].add(stmt.alias)

    # ── Expr ──────────────────────────────────────────────────────────────

    def _bind_expr(
        self, expr: Expr, scopes: list[set[str]], bindings: BindingMap
    ) -> None:
        if isinstance(expr, LiteralExpr):
            return
        if isinstance(expr, IdentifierExpr):
            dist = self._resolve_distance(expr.name, scopes)
            if dist is not None:
                bindings[id(expr)] = dist
        elif isinstance(expr, ListExpr):
            for element in expr.elements:
                self._bind_expr(element, scopes, bindings)
        elif isinstance(expr, ArrayExpr):
            self._bind_expr(expr.size, scopes, bindings)
        elif isinstance(expr, ArrayIndexExpr):
            self._bind_expr(expr.array, scopes, bindings)
            self._bind_expr(expr.index, scopes, bindings)
        elif isinstance(expr, NewExpr):
            for arg in expr.args:
                self._bind_expr(arg, scopes, bindings)
        elif isinstance(expr, DotExpr):
            self._bind_expr(expr.obj, scopes, bindings)
            for arg in expr.args:
                self._bind_expr(arg, scopes, bindings)
        elif isinstance(expr, SuperExpr):
            for arg in expr.args:
                self._bind_expr(arg, scopes, bindings)

    def _resolve_distance(self, name: str, scopes: list[set[str]]) -> int | None:
        """name이 있는 스코프까지의 거리를 반환한다. 없으면 None."""
        for distance, scope in enumerate(reversed(scopes)):
            if name in scope:
                return distance
        return None


# ── 상수 접기 (Constant Folding) ─────────────────────────────────────────────
#
# 컴파일 타임에 100% 확정 가능한 리터럴 상수 연산을 LiteralExpr로 치환한다.
# 원본 AST는 변경하지 않으며 새 Program 을 반환한다.

_FOLD_UNARY: dict[str, _Callable] = {
    "+": lambda a: a,
    "-": _op.neg,
    "not": _op.not_,
    "!": _op.not_,
}

_FOLD_BINARY: dict[str, _Callable] = {
    "+": _op.add,
    "-": _op.sub,
    "*": _op.mul,
    "/": _op.truediv,
    "<": _op.lt,
    ">": _op.gt,
    "=": _op.eq,
    "and": lambda a, b: a and b,
    "or":  lambda a, b: a or b,
}


class ConstantFolder:
    """
    AST를 순회하며 상수 표현식을 LiteralExpr로 치환한 새 Program을 반환한다.

    예)  (+ 1 (* 2 3))  →  LiteralExpr(7.0)
         (/ 1 0)        →  변경 없음 (ZeroDivisionError 방지)
         (+ x 1)        →  변경 없음 (x가 변수이므로)
    """

    def fold(self, program: Program) -> Program:
        return Program(tuple(self._fold_stmt(s) for s in program.statements))

    # ── Stmt ──────────────────────────────────────────────────────────────

    def _fold_stmt(self, stmt: Stmt) -> Stmt:
        if isinstance(stmt, ExpressionStmt):
            return ExpressionStmt(self._fold_expr(stmt.expression), location=stmt.location)
        if isinstance(stmt, PrintStmt):
            return PrintStmt(self._fold_expr(stmt.expression), location=stmt.location)
        if isinstance(stmt, VarStmt):
            init = self._fold_expr(stmt.initializer) if stmt.initializer is not None else None
            return VarStmt(name=stmt.name, initializer=init, location=stmt.location)
        if isinstance(stmt, SetStmt):
            return SetStmt(
                target=stmt.target,
                value=self._fold_expr(stmt.value),
                location=stmt.location,
            )
        if isinstance(stmt, BlockStmt):
            return BlockStmt(
                tuple(self._fold_stmt(s) for s in stmt.statements),
                location=stmt.location,
            )
        if isinstance(stmt, IfStmt):
            return IfStmt(
                condition=self._fold_expr(stmt.condition),
                then_branch=self._fold_stmt(stmt.then_branch),
                else_branch=(
                    self._fold_stmt(stmt.else_branch)
                    if stmt.else_branch is not None else None
                ),
                location=stmt.location,
            )
        if isinstance(stmt, ForStmt):
            return ForStmt(
                iterator=stmt.iterator,
                start=self._fold_expr(stmt.start),
                end=self._fold_expr(stmt.end),
                body=self._fold_stmt(stmt.body),
                location=stmt.location,
            )
        return stmt

    # ── Expr ──────────────────────────────────────────────────────────────

    def _fold_expr(self, expr: Expr) -> Expr:
        if isinstance(expr, (LiteralExpr, IdentifierExpr)):
            return expr
        if isinstance(expr, ListExpr):
            folded_elems = tuple(self._fold_expr(e) for e in expr.elements)
            return self._try_fold(folded_elems, expr.location)
        return expr

    def _try_fold(
        self,
        elements: tuple[Expr, ...],
        location: SourceLocation | None,
    ) -> Expr:
        if not elements:
            return ListExpr(elements, location=location)
        head = elements[0]
        if not isinstance(head, IdentifierExpr):
            return ListExpr(elements, location=location)
        op_name = head.name
        args = elements[1:]
        if not args or not all(isinstance(a, LiteralExpr) for a in args):
            return ListExpr(elements, location=location)
        values = [a.value for a in args]
        n = len(values)
        try:
            if n == 1 and op_name in _FOLD_UNARY:
                result = _FOLD_UNARY[op_name](values[0])
            elif n == 2 and op_name in _FOLD_BINARY:
                result = _FOLD_BINARY[op_name](values[0], values[1])
            else:
                return ListExpr(elements, location=location)
        except Exception:
            return ListExpr(elements, location=location)
        return LiteralExpr(result, location=location)


# ── 고수준 Optimizer API ──────────────────────────────────────────────────────
#
#   resolve_bindings(program)   → BindingTable  (name → distance 조회)
#   fold_constants(program)     → Program       (상수 접기된 새 AST)
#   optimization_stats(program) → dict          (접기 횟수 등 통계)
#   optimize(program)           → Program       (모든 최적화 적용)


@dataclass(frozen=True)
class BindingInfo:
    """단일 변수의 스코프 거리 정보."""
    distance: int


class BindingTable:
    """
    변수 이름 → 스코프 거리 조회 테이블 (사람이 읽기 좋은 이름 기반 인터페이스).

    StaticBinder 의 id-기반 BindingMap 과 달리
    변수 이름으로 직접 거리를 조회할 수 있다.
    """

    def __init__(self, data: dict[str, int]) -> None:
        self._data = data

    def lookup(self, name: str) -> BindingInfo:
        if name not in self._data:
            raise KeyError(f"No binding found for variable '{name}'")
        return BindingInfo(distance=self._data[name])


def _resolve_dist(name: str, scopes: list[set[str]]) -> int | None:
    for dist, scope in enumerate(reversed(scopes)):
        if name in scope:
            return dist
    return None


def _collect_stmt(stmt: Stmt, scopes: list[set[str]], out: dict[str, int]) -> None:
    if isinstance(stmt, VarStmt):
        if stmt.initializer is not None:
            _collect_expr(stmt.initializer, scopes, out)
        scopes[-1].add(stmt.name)
    elif isinstance(stmt, SetStmt):
        dist = _resolve_dist(stmt.target, scopes)
        if dist is not None:
            out[stmt.target] = dist
        _collect_expr(stmt.value, scopes, out)
    elif isinstance(stmt, PrintStmt):
        _collect_expr(stmt.expression, scopes, out)
    elif isinstance(stmt, ExpressionStmt):
        _collect_expr(stmt.expression, scopes, out)
    elif isinstance(stmt, BlockStmt):
        scopes.append(set())
        for s in stmt.statements:
            _collect_stmt(s, scopes, out)
        scopes.pop()
    elif isinstance(stmt, IfStmt):
        _collect_expr(stmt.condition, scopes, out)
        _collect_stmt(stmt.then_branch, scopes, out)
        if stmt.else_branch is not None:
            _collect_stmt(stmt.else_branch, scopes, out)
    elif isinstance(stmt, ForStmt):
        _collect_expr(stmt.start, scopes, out)
        _collect_expr(stmt.end, scopes, out)
        scopes.append({stmt.iterator})
        _collect_stmt(stmt.body, scopes, out)
        scopes.pop()
    elif isinstance(stmt, FuncDefStmt):
        scopes[-1].add(stmt.name)
        scopes.append(set(stmt.params))
        _collect_stmt(stmt.body, scopes, out)
        scopes.pop()
    elif isinstance(stmt, ReturnStmt):
        if stmt.value is not None:
            _collect_expr(stmt.value, scopes, out)
    elif isinstance(stmt, ClassStmt):
        scopes[-1].add(stmt.name)
    elif isinstance(stmt, ImportStmt):
        scopes[-1].add(stmt.alias)


def _collect_expr(expr: Expr, scopes: list[set[str]], out: dict[str, int]) -> None:
    if isinstance(expr, LiteralExpr):
        return
    if isinstance(expr, IdentifierExpr):
        if expr.name not in BUILTIN_OPS:
            dist = _resolve_dist(expr.name, scopes)
            if dist is not None:
                out[expr.name] = dist
    elif isinstance(expr, ListExpr):
        for e in expr.elements:
            _collect_expr(e, scopes, out)


def resolve_bindings(program: Program) -> BindingTable:
    """
    프로그램 내 변수 참조를 분석해 이름 기반 스코프 거리 테이블을 반환한다.

    같은 이름이 여러 위치에서 참조된 경우 마지막으로 만난 거리가 기록된다.
    """
    data: dict[str, int] = {}
    scopes: list[set[str]] = [set(BUILTIN_OPS)]
    for stmt in program.statements:
        _collect_stmt(stmt, scopes, data)
    return BindingTable(data)


# ── fold_constants + optimization_stats ──────────────────────────────────────

_stats_store: dict[int, dict[str, int]] = {}
_program_keepalive: list[Program] = []


class _CountingFolder(ConstantFolder):
    """접기 횟수를 카운트하는 ConstantFolder 서브클래스."""

    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def _try_fold(self, elements: tuple, location: SourceLocation | None) -> Expr:
        result = super()._try_fold(elements, location)
        if isinstance(result, LiteralExpr):
            self.count += 1
        return result


def fold_constants(program: Program) -> Program:
    """
    상수 접기를 수행한 새 Program 을 반환한다.

    반환된 Program 은 optimization_stats() 로 접기 횟수를 조회할 수 있다.
    """
    folder = _CountingFolder()
    folded = folder.fold(program)
    _stats_store[id(folded)] = {"folded_expressions": folder.count}
    _program_keepalive.append(folded)
    return folded


def optimization_stats(program: Program) -> dict[str, int]:
    """
    fold_constants() 로 생성된 Program 의 최적화 통계를 반환한다.

    반환 키:
      "folded_expressions": 컴파일 타임에 접힌 ListExpr 노드 수
    """
    return _stats_store.get(id(program), {"folded_expressions": 0})


def optimize(program: Program) -> Program:
    """
    가능한 모든 컴파일 타임 최적화를 적용한 새 Program 을 반환한다.

    현재 적용 순서:
      1. 상수 접기 (ConstantFolder) — 리터럴 연산 사전 계산
      (정적 바인딩 분석은 resolve_bindings() 로 별도 수행 가능)

    반환된 Program 은 check() 와 execute() 를 정상적으로 통과한다.
    """
    return fold_constants(program)


__all__ = [
    "BindingInfo",
    "BindingMap",
    "BindingTable",
    "ConstantFolder",
    "StaticBinder",
    "fold_constants",
    "optimize",
    "optimization_stats",
    "resolve_bindings",
]
