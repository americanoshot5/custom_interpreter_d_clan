from __future__ import annotations

from pathlib import Path
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
from interfaces import Checker
from Tokenizer import tokenize
from Assembler import assemble


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
        self._imported_paths_stack: list[set[str]] = [set()]
        self._declaring: str | None = None

    def push(self) -> None:
        self._stack.append({})
        self._class_names_stack.append(set())
        self._imported_paths_stack.append(set())

    def pop(self) -> None:
        self._stack.pop()
        self._class_names_stack.pop()
        self._imported_paths_stack.pop()

    def add_class_name(self, name: str) -> None:
        self._class_names_stack[-1].add(name)

    def is_class_name(self, name: str) -> bool:
        return any(name in level for level in reversed(self._class_names_stack))

    def mark_imported(self, abs_path: str) -> bool:
        """현재(가장 안쪽) 스코프에 이 경로가 이미 임포트돼 있으면 False,
        아니면 등록하고 True 를 반환한다."""
        current = self._imported_paths_stack[-1]
        if abs_path in current:
            return False
        current.add(abs_path)
        return True

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


class StaticChecker(Checker):
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
        ImportStmt:     "_check_import_stmt",
    }

    def check(self, program: Program) -> None:
        scopes = _ScopeStack()
        self._method_stack: list[dict] = []  # [{class_name, has_parent, is_init}]
        self._import_stack: list[str] = []  # 순환 임포트 감지용 (절대경로 스택)
        self._check_program(program, scopes)

    def _check_program(self, program: Program, scopes: _ScopeStack) -> None:
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
        # start / end 는 for 스코프 밖(현재 스코프)에서 평가된다
        self._check_expr(stmt.start, scopes)
        self._check_expr(stmt.end, scopes)

        # 반복자 변수는 for 전용 스코프에 선언한다
        scopes.push()
        scopes.declare(stmt.iterator, stmt.location)
        self._in_for = getattr(self, "_in_for", 0) + 1
        self._check_stmt(stmt.body, scopes)
        self._in_for -= 1
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
        if stmt.value is not None:
            self._check_expr(stmt.value, scopes)
            if in_method and self._method_stack[-1]["is_init"]:
                raise CheckError("'init' method cannot use 'return' with a value")

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

    def _check_import_stmt(self, stmt: ImportStmt, scopes: _ScopeStack) -> None:
        loc = stmt.location
        loc_str = f" at {loc.line}:{loc.column}" if loc else ""

        if getattr(self, "_in_for", 0) > 0:
            raise CheckError(f"'import' cannot be used inside a for loop{loc_str}")

        if not isinstance(stmt.path, LiteralExpr) or not isinstance(stmt.path.value, str):
            raise CheckError(f"import path must be a string literal{loc_str}")

        path = stmt.path.value
        file_path = Path(path)
        if not file_path.exists():
            raise CheckError(f"Imported file not found: '{path}'{loc_str}")

        abs_path = str(file_path.resolve())
        if abs_path in self._import_stack:
            raise CheckError(f"Circular import (순환 참조) detected: '{path}'{loc_str}")
        if not scopes.mark_imported(abs_path):
            raise CheckError(
                f"'{path}' is already imported in this scope (duplicate import){loc_str}"
            )

        source = file_path.read_text(encoding="utf-8")
        self._import_stack.append(abs_path)
        try:
            imported_program = assemble(tokenize(source))
            self._check_program(imported_program, _ScopeStack())
        finally:
            self._import_stack.pop()

        scopes.declare(stmt.alias, stmt.location)

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


DefaultChecker = StaticChecker


def check(program: Program) -> None:
    StaticChecker().check(program)


__all__ = ["DefaultChecker", "StaticChecker", "check"]
