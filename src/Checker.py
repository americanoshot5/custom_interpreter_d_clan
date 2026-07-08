from __future__ import annotations

import operator as _op
from collections.abc import Callable as _Callable
from typing import ClassVar

from common import (
    ArrayExpr,
    ArrayIndexExpr,
    BUILTIN_OPS,
    BlockStmt,
    CheckError,
    ClassStmt,
    DotExpr,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDefStmt,
    IdentifierExpr,
    IfStmt,
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
from interfaces import Checker


class _ScopeStack:
    """
    스코프 스택.

    - push / pop: BlockStmt 및 ForStmt 진입/탈출 시 호출
    - declare : 현재(가장 안쪽) 스코프에 변수를 등록.
                같은 스코프 내 중복 선언 시 CheckError.
    - resolve : 이름이 어느 스코프에도 없으면 "Undefined variable" CheckError.
                현재 선언 중(begin_declaring)인 이름과 일치하면
                "references itself" CheckError.
    - begin_declaring / end_declaring :
                VarStmt 초기화식 검사 구간을 감싸서 자기 참조를 감지한다.
    - add_class_name / is_class_name :
                클래스 선언인 이름을 별도로 추적하여 "superclass must be a class" 검사에 활용한다.
    """

    def __init__(self) -> None:
        # 전역 스코프에 내장 연산자를 미리 등록한다
        self._stack: list[dict[str, SourceLocation | None]] = [
            {name: None for name in BUILTIN_OPS}
        ]
        self._class_names_stack: list[set[str]] = [set()]
        self._declaring: str | None = None

    def push(self) -> None:
        self._stack.append({})
        self._class_names_stack.append(set())

    def pop(self) -> None:
        self._stack.pop()
        self._class_names_stack.pop()

    def add_class_name(self, name: str) -> None:
        self._class_names_stack[-1].add(name)

    def is_class_name(self, name: str) -> bool:
        return any(name in level for level in reversed(self._class_names_stack))

    def declare(self, name: str, location: SourceLocation | None) -> None:
        """현재 스코프에 name 을 등록한다. 같은 스코프 내 중복이면 CheckError."""
        current = self._stack[-1]
        if name in current:
            prev = current[name]
            loc_str = f" at {location.line}:{location.column}" if location else ""
            prev_str = (
                f" (previously declared at {prev.line}:{prev.column})" if prev else ""
            )
            raise CheckError(
                f"Variable '{name}' is already declared in this scope{loc_str}{prev_str}"
            )
        current[name] = location

    def resolve(self, name: str, location: SourceLocation | None) -> None:
        """name 이 접근 가능한지 검사한다."""
        if name == self._declaring:
            loc_str = f" at {location.line}:{location.column}" if location else ""
            raise CheckError(
                f"Variable '{name}' references itself in its own initializer{loc_str}"
            )
        for scope in reversed(self._stack):
            if name in scope:
                return
        loc_str = f" at {location.line}:{location.column}" if location else ""
        raise CheckError(f"Undefined variable '{name}'{loc_str}")

    def begin_declaring(self, name: str) -> None:
        self._declaring = name

    def end_declaring(self) -> None:
        self._declaring = None


class SExpressionChecker(Checker):
    """
    의미 분석 정적 검사기.

    검사 항목
    ---------
    1. 변수 중복 선언 : 동일 스코프 내 같은 이름 재선언
    2. 자기 참조      : 변수 초기화식에서 선언 중인 자기 자신을 참조
    3. 미정의 변수    : 선언되지 않은 변수를 식에서 사용
    4. for 반복자 재선언 : for 스코프 안에서 반복자와 동일 이름 선언
    5. 클래스 부모 존재 여부 확인
    """

    # 새로운 Stmt 종류 추가 시: 이 테이블에 한 줄 + 검사 메서드 하나만 추가하면 됩니다.
    _STMT_DISPATCH: ClassVar[dict[type, str]] = {
        VarStmt:        "_check_var_stmt",
        SetStmt:        "_check_set_stmt",
        PrintStmt:      "_check_print_stmt",
        ExpressionStmt: "_check_exprstmt",
        BlockStmt:      "_check_block_stmt",
        IfStmt:         "_check_if_stmt",
        ForStmt:        "_check_for_stmt",
        FuncDefStmt:    "_check_func_stmt",
        ReturnStmt:     "_check_return_stmt",
        ClassStmt:      "_check_class_stmt",
    }

    def check(self, program: Program) -> None:
        scopes = _ScopeStack()
        self._method_stack: list[dict] = []  # [{class_name, has_parent, is_init}]
        for stmt in program.statements:
            self._check_stmt(stmt, scopes)

    # ── 문(Stmt) ──────────────────────────────────────────────────────────────

    def _check_stmt(self, stmt: Stmt, scopes: _ScopeStack) -> None:
        method_name = self._STMT_DISPATCH.get(type(stmt))
        if method_name is None:
            raise CheckError(f"Unsupported statement type: {type(stmt).__name__}")
        getattr(self, method_name)(stmt, scopes)

    def _check_print_stmt(self, stmt: PrintStmt, scopes: _ScopeStack) -> None:
        self._check_expr(stmt.expression, scopes)

    def _check_exprstmt(self, stmt: ExpressionStmt, scopes: _ScopeStack) -> None:
        expr = stmt.expression
        # 'init' 메서드 내부에서 return 값 사용 검사
        if (isinstance(expr, ListExpr) and
                expr.elements and
                isinstance(expr.elements[0], IdentifierExpr) and
                expr.elements[0].name == "return" and
                len(expr.elements) > 1 and
                self._method_stack and
                self._method_stack[-1]["is_init"]):
            raise CheckError("'init' method cannot use 'return' with a value")
        self._check_expr(expr, scopes)

    def _check_set_stmt(self, stmt: SetStmt, scopes: _ScopeStack) -> None:
        scopes.resolve(stmt.target, stmt.location)
        self._check_expr(stmt.value, scopes)

    def _check_var_stmt(self, stmt: VarStmt, scopes: _ScopeStack) -> None:
        if stmt.initializer is not None:
            scopes.begin_declaring(stmt.name)
            self._check_expr(stmt.initializer, scopes)
            scopes.end_declaring()
        scopes.declare(stmt.name, stmt.location)

    def _check_block_stmt(self, stmt: BlockStmt, scopes: _ScopeStack) -> None:
        scopes.push()
        for s in stmt.statements:
            self._check_stmt(s, scopes)
        scopes.pop()

    def _check_if_stmt(self, stmt: IfStmt, scopes: _ScopeStack) -> None:
        self._check_expr(stmt.condition, scopes)
        self._check_stmt(stmt.then_branch, scopes)
        if stmt.else_branch is not None:
            self._check_stmt(stmt.else_branch, scopes)

    def _check_for_stmt(self, stmt: ForStmt, scopes: _ScopeStack) -> None:
        self._check_expr(stmt.start, scopes)
        self._check_expr(stmt.end, scopes)
        scopes.push()
        scopes.declare(stmt.iterator, stmt.location)
        self._check_stmt(stmt.body, scopes)
        scopes.pop()

    def _check_func_stmt(self, stmt: FuncDefStmt, scopes: _ScopeStack) -> None:
        # 재귀 호출을 허용하기 위해 함수 이름을 외부 스코프에 먼저 등록한다.
        scopes.declare(stmt.name, stmt.location)
        # 파라미터 스코프 생성 후 파라미터 등록 (중복 파라미터 검출 포함)
        scopes.push()
        for param in stmt.params:
            scopes.declare(param, stmt.location)
        self._in_function = getattr(self, "_in_function", 0) + 1
        self._check_stmt(stmt.body, scopes)
        self._in_function -= 1
        scopes.pop()

    def _check_return_stmt(self, stmt: ReturnStmt, scopes: _ScopeStack) -> None:
        in_function = getattr(self, "_in_function", 0) > 0
        in_method = bool(self._method_stack)
        if not in_function and not in_method:
            raise CheckError("'return' is used outside function")
        # init 메서드에서 값 반환 금지 (함수 안이 아닐 때만 — 함수 안에서는 허용)
        if in_method and not in_function and stmt.value is not None:
            if self._method_stack[-1]["is_init"]:
                raise CheckError("'init' method cannot use 'return' with a value")
        if stmt.value is not None:
            self._check_expr(stmt.value, scopes)

    def _check_class_stmt(self, stmt: ClassStmt, scopes: _ScopeStack) -> None:
        # 자기 자신 상속 검사
        if stmt.parent is not None and stmt.parent == stmt.name:
            raise CheckError(f"A class cannot inherit from itself: '{stmt.name}'")
        # 부모 존재 확인 + 클래스인지 확인
        if stmt.parent is not None:
            scopes.resolve(stmt.parent, stmt.location)
            if not scopes.is_class_name(stmt.parent):
                raise CheckError(
                    f"'{stmt.parent}' is not a class and cannot be used as a superclass"
                )
        # 클래스 이름을 현재 스코프에 등록
        scopes.declare(stmt.name, stmt.location)
        scopes.add_class_name(stmt.name)
        # 메서드 본문 검사
        for method in stmt.methods:
            self._method_stack.append({
                "class_name": stmt.name,
                "has_parent": stmt.parent is not None,
                "is_init": method.name == "init",
            })
            scopes.push()
            scopes.declare("self", None)
            for param in method.params:
                scopes.declare(param, method.location)
            for s in method.body:
                self._check_stmt(s, scopes)
            scopes.pop()
            self._method_stack.pop()

    # ── 식(Expr) ──────────────────────────────────────────────────────────────

    def _check_expr(self, expr: Expr, scopes: _ScopeStack) -> None:
        if isinstance(expr, LiteralExpr):
            return
        if isinstance(expr, IdentifierExpr):
            # 'This' 는 클래스 메서드 내부에서만 유효
            if expr.name == "This":
                if not self._method_stack:
                    raise CheckError("'This' used outside class")
                return
            scopes.resolve(expr.name, expr.location)
        elif isinstance(expr, ListExpr):
            for element in expr.elements:
                self._check_expr(element, scopes)
        elif isinstance(expr, ArrayExpr):
            self._check_expr(expr.size, scopes)
        elif isinstance(expr, ArrayIndexExpr):
            self._check_expr(expr.array, scopes)
            self._check_expr(expr.index, scopes)
        elif isinstance(expr, NewExpr):
            scopes.resolve(expr.class_name, expr.location)
            for arg in expr.args:
                self._check_expr(arg, scopes)
        elif isinstance(expr, DotExpr):
            self._check_expr(expr.obj, scopes)
            for arg in expr.args:
                self._check_expr(arg, scopes)
        elif isinstance(expr, SuperExpr):
            if not self._method_stack:
                raise CheckError("'Super' used outside class")
            if not self._method_stack[-1]["has_parent"]:
                raise CheckError(
                    f"'Super' cannot be used in class '{self._method_stack[-1]['class_name']}' "
                    f"which has no parent class"
                )
            for arg in expr.args:
                self._check_expr(arg, scopes)
        else:
            raise CheckError(f"Unknown expression type: {type(expr).__name__}")


DefaultChecker = SExpressionChecker


def check(program: Program) -> None:
    SExpressionChecker().check(program)


# ── 정적 바인딩 (Static Binding) ─────────────────────────────────────────────
#
# 각 IdentifierExpr/SetStmt에 대해 해당 변수가 몇 번째 상위 스코프에 있는지
# (distance)를 미리 계산한다.
#
#   BindingMap[id(node)] = distance
#   distance 0 = 현재 스코프, 1 = 1단계 위, n = n단계 위
#
# Executor가 이 맵을 사용하면 Environment.lookup() 시 매번 parent 체인을
# 거슬러 올라가는 대신 계산된 거리만큼만 이동하여 O(1)로 접근 가능하다.
#
# 전제: StaticChecker.check()를 통과한 프로그램 (미정의 변수 없음 가정)

BindingMap = dict[int, int]  # id(IdentifierExpr | SetStmt) → scope distance


class SExpressionBinder:
    """
    검사된 AST를 순회하며 변수 참조·할당마다 스코프 거리를 미리 계산한다.

    반환된 BindingMap을 이용하면 Executor가 런타임에 스코프 체인 탐색 없이
    계산된 위치로 즉시 접근할 수 있어 중첩 스코프에서 성능이 향상된다.
    """

    def bind(self, program: Program) -> BindingMap:
        bindings: BindingMap = {}
        scopes: list[set[str]] = [set(BUILTIN_OPS)]  # 전역 스코프 (내장 연산자 포함)
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
            # 재귀 허용을 위해 함수 이름을 외부 스코프에 먼저 등록
            scopes[-1].add(stmt.name)
            scopes.append(set(stmt.params))
            self._bind_stmt(stmt.body, scopes, bindings)
            scopes.pop()

        elif isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                self._bind_expr(stmt.value, scopes, bindings)

        elif isinstance(stmt, ClassStmt):
            # 클래스 이름만 등록; 메서드 본문은 런타임 클로저로 처리
            scopes[-1].add(stmt.name)

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
# 컴파일 타임에 100% 확정 가능한 리터럴 상수 연산을 미리 계산하여
# LiteralExpr로 치환한 새 Program을 반환한다 (원본 AST 불변).
#
# 접기 조건:
#   - ListExpr head가 알려진 연산자 이름(IdentifierExpr)
#   - 모든 피연산자가 LiteralExpr (재귀적으로 접은 뒤 판정)
#   - 계산 중 예외(ZeroDivisionError, TypeError 등) 발생 시 원형 보존
#
# 루프 내 상수 표현식처럼 반복 계산이 예상되는 곳에서 효과가 크다.

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
         (< 1 2)        →  LiteralExpr(True)
         (+ x 1)        →  변경 없음 (x가 변수이므로)
         (/ 1 0)        →  변경 없음 (ZeroDivisionError 방지)
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
            # 자식을 먼저 재귀적으로 접은 뒤 현재 노드 접기 시도
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


__all__ = [
    "BindingMap",
    "ConstantFolder",
    "DefaultChecker",
    "SExpressionBinder",
    "SExpressionChecker",
    "check",
]
