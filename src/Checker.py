from __future__ import annotations

from typing import ClassVar

from common import (
    ArrayExpr,
    ArrayIndexExpr,
    BUILTIN_OPS,
    BlockStmt,
    CheckError,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDefStmt,
    IdentifierExpr,
    IfStmt,
    ListExpr,
    LiteralExpr,
    PrintStmt,
    Program,
    ReturnStmt,
    SetStmt,
    SourceLocation,
    Stmt,
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
                선언 중인 변수가 초기화식 안에서 참조되면 자기 참조로 판정한다.
                이는 같은 스코프의 outer 변수와 동명인 경우에도 적용된다.
                  예) var x = 5; { var x = x * 2; }  →  self-reference error
    """

    def __init__(self) -> None:
        # 전역 스코프에 내장 연산자를 미리 등록한다
        self._stack: list[dict[str, SourceLocation | None]] = [
            {name: None for name in BUILTIN_OPS}
        ]
        self._declaring: str | None = None

    # ── 스코프 관리 ───────────────────────────────────────────────────────────

    def push(self) -> None:
        self._stack.append({})

    def pop(self) -> None:
        self._stack.pop()

    # ── 선언 ─────────────────────────────────────────────────────────────────

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

    # ── 참조 ─────────────────────────────────────────────────────────────────

    def resolve(self, name: str, location: SourceLocation | None) -> None:
        """name 이 접근 가능한지 검사한다."""
        # 자기 참조: 현재 초기화 중인 변수 이름과 같으면 에러
        if name == self._declaring:
            loc_str = f" at {location.line}:{location.column}" if location else ""
            raise CheckError(
                f"Variable '{name}' references itself in its own initializer{loc_str}"
            )
        # 미정의 변수
        for scope in reversed(self._stack):
            if name in scope:
                return
        loc_str = f" at {location.line}:{location.column}" if location else ""
        raise CheckError(f"Undefined variable '{name}'{loc_str}")

    # ── 선언 구간 마킹 ────────────────────────────────────────────────────────

    def begin_declaring(self, name: str) -> None:
        self._declaring = name

    def end_declaring(self) -> None:
        self._declaring = None


class StaticChecker(Checker):
    """
    의미 분석 정적 검사기.

    검사 항목
    ---------
    1. 변수 중복 선언 : 동일 스코프 내 같은 이름 재선언
    2. 자기 참조      : 변수 초기화식에서 선언 중인 자기 자신을 참조
                        (외부 스코프에 동명 변수가 있어도 에러)
    3. 미정의 변수    : 선언되지 않은 변수를 식에서 사용
    4. for 반복자 재선언 : for 스코프 안(블록 없이)에서 반복자와 동일 이름 선언
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
    }

    def check(self, program: Program) -> None:
        scopes = _ScopeStack()
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
        self._check_expr(stmt.expression, scopes)

    def _check_set_stmt(self, stmt: SetStmt, scopes: _ScopeStack) -> None:
        scopes.resolve(stmt.target, stmt.location)
        self._check_expr(stmt.value, scopes)

    def _check_var_stmt(self, stmt: VarStmt, scopes: _ScopeStack) -> None:
        if stmt.initializer is not None:
            # 초기화식 검사 시 자기 이름을 "선언 중" 으로 마킹한다.
            # 초기화식 안에서 같은 이름이 나오면 자기 참조로 판정된다.
            scopes.begin_declaring(stmt.name)
            self._check_expr(stmt.initializer, scopes)
            scopes.end_declaring()

        # 초기화식 검사가 통과된 후 현재 스코프에 등록한다 (중복 선언 검출)
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
        # start / end 는 for 스코프 밖(현재 스코프)에서 평가된다
        self._check_expr(stmt.start, scopes)
        self._check_expr(stmt.end, scopes)

        # 반복자 변수는 for 전용 스코프에 선언한다
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
        if getattr(self, "_in_function", 0) == 0:
            raise CheckError("'return' is used outside function")
        if stmt.value is not None:
            self._check_expr(stmt.value, scopes)

    # ── 식(Expr) ──────────────────────────────────────────────────────────────

    def _check_expr(self, expr: Expr, scopes: _ScopeStack) -> None:
        if isinstance(expr, LiteralExpr):
            return
        if isinstance(expr, IdentifierExpr):
            scopes.resolve(expr.name, expr.location)
        elif isinstance(expr, ListExpr):
            for element in expr.elements:
                self._check_expr(element, scopes)
        elif isinstance(expr, ArrayExpr):
            self._check_expr(expr.size, scopes)
        elif isinstance(expr, ArrayIndexExpr):
            self._check_expr(expr.array, scopes)
            self._check_expr(expr.index, scopes)
        else:
            raise CheckError(f"Unknown expression type: {type(expr).__name__}")


DefaultChecker = StaticChecker


def check(program: Program) -> None:
    StaticChecker().check(program)


__all__ = ["DefaultChecker", "StaticChecker", "check"]
