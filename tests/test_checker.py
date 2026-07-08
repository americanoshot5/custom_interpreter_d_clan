"""
StaticChecker 단위 테스트

검사 항목별로 클래스로 분리:
    1. 유효한 프로그램 (에러 없이 통과해야 할 케이스)
    2. 변수 중복 선언
    3. 자기 참조 (초기화식에서 선언 중인 변수 참조)
    4. 미정의 변수 참조
    5. BlockStmt 스코프 격리
    6. IfStmt 의 조건/분기 검사
    7. ForStmt 반복자 스코프 및 중복 선언
    8. 복합 시나리오
    9. 모듈 수준 check() 함수
"""

import sys
import os
from dataclasses import dataclass

import pytest

from common import (
    BlockStmt,
    CheckError,
    ExpressionStmt,
    ForStmt,
    IdentifierExpr,
    IfStmt,
    ImportStmt,
    ListExpr,
    LiteralExpr,
    PrintStmt,
    Program,
    SourceLocation,
    Stmt,
    VarStmt,
)
from Checker import StaticChecker, check


# ── AST 헬퍼 ─────────────────────────────────────────────────────────────────

def loc(line: int = 1, col: int = 1) -> SourceLocation:
    return SourceLocation(line=line, column=col)


def prog(*stmts) -> Program:
    return Program(tuple(stmts))


def lit(v) -> LiteralExpr:
    return LiteralExpr(v)


def ident(name: str, line: int = 1, col: int = 1) -> IdentifierExpr:
    return IdentifierExpr(name, location=loc(line, col))


def list_expr(*elems, line: int = 1, col: int = 1) -> ListExpr:
    return ListExpr(tuple(elems), location=loc(line, col))


def expr_stmt(expr) -> ExpressionStmt:
    return ExpressionStmt(expr)


def var(name: str, init=None, line: int = 1, col: int = 1) -> VarStmt:
    return VarStmt(name=name, initializer=init, location=loc(line, col))


def print_stmt(expr) -> PrintStmt:
    return PrintStmt(expr)


def block(*stmts) -> BlockStmt:
    return BlockStmt(tuple(stmts))


def if_stmt(cond, then_branch, else_branch=None) -> IfStmt:
    return IfStmt(condition=cond, then_branch=then_branch, else_branch=else_branch)


def for_stmt(
    iterator: str, start, end, body, line: int = 1, col: int = 1
) -> ForStmt:
    return ForStmt(
        iterator=iterator, start=start, end=end, body=body, location=loc(line, col)
    )


def import_stmt(path_expr, alias: str, line: int = 1, col: int = 1) -> ImportStmt:
    return ImportStmt(path=path_expr, alias=alias, location=loc(line, col))


# ── 기존 스켈레톤 테스트 유지 ────────────────────────────────────────────────

@dataclass(frozen=True, slots=True, kw_only=True)
class _DummyStmt(Stmt):
    pass


def test_check_unsupported_statement_raises():
    program = Program((_DummyStmt(),))
    with pytest.raises(CheckError):
        check(program)


# ── 1. 유효한 프로그램 ────────────────────────────────────────────────────────

class TestValidPrograms:
    def test_empty_program(self):
        StaticChecker().check(prog())

    def test_literal_only(self):
        StaticChecker().check(prog(expr_stmt(lit(42.0))))

    def test_builtin_operator_expression(self):
        StaticChecker().check(prog(
            expr_stmt(list_expr(ident("+"), lit(1.0), lit(2.0)))
        ))

    def test_nested_list_expression(self):
        # 기존 스켈레톤 테스트와 동일한 케이스
        StaticChecker().check(prog(
            expr_stmt(list_expr(
                ident("+"),
                lit(1.0),
                list_expr(lit(2.0)),
            ))
        ))

    def test_var_declare_and_use(self):
        StaticChecker().check(prog(
            var("x", lit(10.0)),
            expr_stmt(ident("x")),
        ))

    def test_var_no_initializer(self):
        StaticChecker().check(prog(var("x")))

    def test_var_uses_previously_declared_var(self):
        StaticChecker().check(prog(
            var("x", lit(1.0)),
            var("y", list_expr(ident("+"), ident("x"), lit(1.0))),
        ))

    def test_print_literal(self):
        StaticChecker().check(prog(print_stmt(lit("hello"))))

    def test_print_declared_var(self):
        StaticChecker().check(prog(
            var("x", lit(5.0)),
            print_stmt(ident("x")),
        ))

    def test_nested_arithmetic_expression(self):
        StaticChecker().check(prog(
            var("a", lit(2.0)),
            var("b", lit(3.0)),
            expr_stmt(list_expr(
                ident("*"),
                list_expr(ident("+"), ident("a"), ident("b")),
                ident("a"),
            )),
        ))

    def test_all_builtins_are_accessible(self):
        for op in ("+", "-", "*", "/", ">", "<", "=", "and", "or", "not"):
            StaticChecker().check(prog(expr_stmt(ident(op))))


# ── 2. 변수 중복 선언 ────────────────────────────────────────────────────────

class TestDuplicateDeclaration:
    def test_duplicate_in_global_scope(self):
        with pytest.raises(CheckError, match="already declared"):
            StaticChecker().check(prog(
                var("x", lit(1.0), line=1),
                var("x", lit(2.0), line=2),
            ))

    def test_error_contains_variable_name(self):
        with pytest.raises(CheckError, match="'x'"):
            StaticChecker().check(prog(
                var("x", lit(1.0)),
                var("x", lit(2.0)),
            ))

    def test_error_contains_second_declaration_location(self):
        with pytest.raises(CheckError, match="2:5"):
            StaticChecker().check(prog(
                var("x", lit(1.0), line=1, col=1),
                var("x", lit(2.0), line=2, col=5),
            ))

    def test_error_contains_first_declaration_location(self):
        with pytest.raises(CheckError, match="1:1"):
            StaticChecker().check(prog(
                var("x", lit(1.0), line=1, col=1),
                var("x", lit(2.0), line=2, col=1),
            ))

    def test_duplicate_in_same_block(self):
        with pytest.raises(CheckError, match="already declared"):
            StaticChecker().check(prog(
                block(
                    var("x", lit(1.0)),
                    var("x", lit(2.0)),
                )
            ))

    def test_shadowing_in_inner_scope_is_allowed(self):
        # 다른 스코프(내부 블록)에서 같은 이름 선언 → shadowing, 허용
        StaticChecker().check(prog(
            var("x", lit(1.0)),
            block(var("x", lit(2.0))),
        ))

    def test_multiple_different_names_allowed(self):
        StaticChecker().check(prog(
            var("x", lit(1.0)),
            var("y", lit(2.0)),
            var("z", lit(3.0)),
        ))

    def test_third_declaration_is_duplicate(self):
        with pytest.raises(CheckError, match="already declared"):
            StaticChecker().check(prog(
                var("a", lit(1.0)),
                var("b", lit(2.0)),
                var("a", lit(3.0)),  # 세 번째가 중복
            ))


# ── 3. 자기 참조 검출 ────────────────────────────────────────────────────────

class TestSelfReference:
    def test_self_ref_no_outer_variable(self):
        # var x = x + 1 — x 가 전혀 선언된 적 없는 경우
        with pytest.raises(CheckError, match="references itself"):
            StaticChecker().check(prog(
                var("x", list_expr(ident("+"), ident("x"), lit(1.0)))
            ))

    def test_self_ref_with_outer_same_name(self):
        # 외부 스코프에 x 가 있어도 내부 var x 초기화식에서 x 사용 → 자기 참조
        with pytest.raises(CheckError, match="references itself"):
            StaticChecker().check(prog(
                var("x", lit(5.0)),
                block(
                    var("x", list_expr(ident("*"), ident("x"), lit(2.0)))
                ),
            ))

    def test_error_contains_variable_name(self):
        with pytest.raises(CheckError, match="'counter'"):
            StaticChecker().check(prog(
                var("counter", list_expr(ident("+"), ident("counter"), lit(1.0)))
            ))

    def test_error_contains_location(self):
        with pytest.raises(CheckError, match="3:5"):
            StaticChecker().check(prog(
                var("x", list_expr(ident("+"), ident("x", line=3, col=5), lit(1.0)))
            ))

    def test_self_ref_in_deeply_nested_expression(self):
        # var x = ((x + 1) * 2)
        with pytest.raises(CheckError, match="references itself"):
            StaticChecker().check(prog(
                var("x", list_expr(
                    ident("*"),
                    list_expr(ident("+"), ident("x"), lit(1.0)),
                    lit(2.0),
                ))
            ))

    def test_no_self_ref_different_var(self):
        # var y = x + 1 — 다른 변수 사용은 정상
        StaticChecker().check(prog(
            var("x", lit(10.0)),
            var("y", list_expr(ident("+"), ident("x"), lit(1.0))),
        ))

    def test_no_self_ref_outer_var_different_name_in_block(self):
        # 안쪽 스코프에서 완전히 다른 이름 사용 → 정상
        StaticChecker().check(prog(
            var("x", lit(5.0)),
            block(var("y", list_expr(ident("*"), ident("x"), lit(2.0)))),
        ))


# ── 4. 미정의 변수 참조 ──────────────────────────────────────────────────────

class TestUndefinedVariable:
    def test_undefined_in_expression_stmt(self):
        with pytest.raises(CheckError, match="Undefined variable 'z'"):
            StaticChecker().check(prog(expr_stmt(ident("z"))))

    def test_undefined_in_print_stmt(self):
        with pytest.raises(CheckError, match="Undefined variable"):
            StaticChecker().check(prog(print_stmt(ident("unknown"))))

    def test_undefined_in_var_initializer(self):
        with pytest.raises(CheckError, match="Undefined variable 'missing'"):
            StaticChecker().check(prog(var("x", ident("missing"))))

    def test_error_contains_location(self):
        with pytest.raises(CheckError, match="5:10"):
            StaticChecker().check(prog(expr_stmt(ident("nope", line=5, col=10))))

    def test_var_not_visible_before_declaration(self):
        with pytest.raises(CheckError, match="Undefined variable 'x'"):
            StaticChecker().check(prog(
                expr_stmt(ident("x")),
                var("x", lit(1.0)),
            ))

    def test_undefined_in_nested_list_expression(self):
        with pytest.raises(CheckError, match="Undefined variable 'ghost'"):
            StaticChecker().check(prog(
                expr_stmt(list_expr(ident("+"), lit(1.0), ident("ghost")))
            ))


# ── 5. BlockStmt 스코프 격리 ─────────────────────────────────────────────────

class TestBlockScope:
    def test_var_in_block_not_visible_outside(self):
        with pytest.raises(CheckError, match="Undefined variable 'inner'"):
            StaticChecker().check(prog(
                block(var("inner", lit(1.0))),
                expr_stmt(ident("inner")),
            ))

    def test_outer_var_visible_inside_block(self):
        StaticChecker().check(prog(
            var("outer", lit(1.0)),
            block(expr_stmt(ident("outer"))),
        ))

    def test_nested_blocks_see_all_outer_scopes(self):
        StaticChecker().check(prog(
            var("a", lit(1.0)),
            block(
                var("b", list_expr(ident("+"), ident("a"), lit(1.0))),
                block(
                    var("c", list_expr(ident("+"), ident("b"), lit(1.0))),
                    print_stmt(ident("c")),
                ),
            ),
        ))

    def test_sibling_blocks_do_not_share_scope(self):
        with pytest.raises(CheckError, match="Undefined variable"):
            StaticChecker().check(prog(
                block(var("x", lit(1.0))),
                block(expr_stmt(ident("x"))),  # 다른 블록 — x 없음
            ))


# ── 6. IfStmt 검사 ────────────────────────────────────────────────────────────

class TestIfStmt:
    def test_if_valid_with_declared_var(self):
        StaticChecker().check(prog(
            var("x", lit(5.0)),
            if_stmt(
                list_expr(ident(">"), ident("x"), lit(3.0)),
                print_stmt(lit("big")),
                print_stmt(lit("small")),
            ),
        ))

    def test_if_without_else(self):
        StaticChecker().check(prog(
            if_stmt(lit(True), print_stmt(lit("yes")))
        ))

    def test_if_undefined_condition(self):
        with pytest.raises(CheckError, match="Undefined variable 'flag'"):
            StaticChecker().check(prog(
                if_stmt(ident("flag"), print_stmt(lit("yes")))
            ))

    def test_if_undefined_in_then_branch(self):
        with pytest.raises(CheckError, match="Undefined variable"):
            StaticChecker().check(prog(
                if_stmt(lit(True), expr_stmt(ident("undefined")))
            ))

    def test_if_undefined_in_else_branch(self):
        with pytest.raises(CheckError, match="Undefined variable"):
            StaticChecker().check(prog(
                if_stmt(
                    lit(True),
                    print_stmt(lit("ok")),
                    expr_stmt(ident("undefined")),
                )
            ))

    def test_if_then_block_scope_not_visible_outside(self):
        with pytest.raises(CheckError, match="Undefined variable 'x'"):
            StaticChecker().check(prog(
                if_stmt(lit(True), block(var("x", lit(1.0)))),
                expr_stmt(ident("x")),  # 블록 스코프 밖
            ))


# ── 7. ForStmt 반복자 스코프 및 중복 선언 ────────────────────────────────────

class TestForStmt:
    def test_for_valid(self):
        StaticChecker().check(prog(
            for_stmt("i", lit(1.0), lit(5.0), print_stmt(lit("loop")))
        ))

    def test_for_iterator_visible_in_body(self):
        StaticChecker().check(prog(
            for_stmt("i", lit(1.0), lit(5.0), print_stmt(ident("i")))
        ))

    def test_for_iterator_not_visible_after_loop(self):
        with pytest.raises(CheckError, match="Undefined variable 'i'"):
            StaticChecker().check(prog(
                for_stmt("i", lit(1.0), lit(5.0), print_stmt(lit("ok"))),
                expr_stmt(ident("i")),
            ))

    def test_for_start_checked_in_outer_scope(self):
        with pytest.raises(CheckError, match="Undefined variable 'start'"):
            StaticChecker().check(prog(
                for_stmt("i", ident("start"), lit(5.0), print_stmt(lit("ok")))
            ))

    def test_for_end_checked_in_outer_scope(self):
        with pytest.raises(CheckError, match="Undefined variable 'end'"):
            StaticChecker().check(prog(
                for_stmt("i", lit(1.0), ident("end"), print_stmt(lit("ok")))
            ))

    def test_for_uses_outer_var_for_range(self):
        StaticChecker().check(prog(
            var("n", lit(10.0)),
            for_stmt("i", lit(1.0), ident("n"), print_stmt(ident("i"))),
        ))

    def test_for_iterator_not_visible_in_start_expr(self):
        # start/end 는 for 스코프 진입 전 평가 → 반복자 미노출
        with pytest.raises(CheckError, match="Undefined variable 'i'"):
            StaticChecker().check(prog(
                for_stmt("i", ident("i"), lit(5.0), print_stmt(lit("ok")))
            ))

    def test_for_iterator_redeclare_in_same_for_scope(self):
        # 블록 없는 for body 에서 반복자 이름을 var 로 재선언 → 중복
        with pytest.raises(CheckError, match="already declared"):
            StaticChecker().check(prog(
                for_stmt("i", lit(1.0), lit(3.0), var("i", lit(99.0)))
            ))

    def test_for_iterator_shadow_in_body_block_is_allowed(self):
        # body 가 BlockStmt 이면 별도 스코프 → shadowing 허용
        StaticChecker().check(prog(
            for_stmt("i", lit(1.0), lit(3.0), block(
                var("i", lit(99.0)),
            ))
        ))

    def test_nested_for_different_iterators(self):
        StaticChecker().check(prog(
            for_stmt("i", lit(1.0), lit(3.0),
                for_stmt("j", lit(1.0), lit(3.0),
                    print_stmt(list_expr(ident("+"), ident("i"), ident("j")))
                )
            )
        ))

    def test_nested_for_same_iterator_name_shadows(self):
        # 안쪽 for 가 바깥 i 를 shadowing — 허용
        StaticChecker().check(prog(
            for_stmt("i", lit(1.0), lit(3.0),
                for_stmt("i", lit(1.0), lit(3.0),
                    print_stmt(ident("i"))
                )
            )
        ))


# ── 8. 복합 시나리오 ──────────────────────────────────────────────────────────

class TestComplexPrograms:
    def test_accumulate_with_for(self):
        StaticChecker().check(prog(
            var("total", lit(0.0)),
            for_stmt("i", lit(1.0), lit(5.0),
                expr_stmt(list_expr(ident("+"), ident("total"), ident("i")))
            ),
            print_stmt(ident("total")),
        ))

    def test_var_chain_with_arithmetic(self):
        StaticChecker().check(prog(
            var("a", lit(1.0)),
            var("b", list_expr(ident("+"), ident("a"), lit(1.0))),
            var("c", list_expr(ident("+"), ident("b"), lit(1.0))),
            print_stmt(ident("c")),
        ))

    def test_if_with_outer_var(self):
        StaticChecker().check(prog(
            var("x", lit(10.0)),
            if_stmt(
                list_expr(ident(">"), ident("x"), lit(5.0)),
                print_stmt(lit("big")),
                print_stmt(lit("small")),
            ),
        ))

    def test_for_body_uses_outer_var(self):
        StaticChecker().check(prog(
            var("factor", lit(2.0)),
            for_stmt("i", lit(1.0), lit(5.0),
                print_stmt(list_expr(ident("*"), ident("i"), ident("factor")))
            ),
        ))

    def test_block_and_for_share_outer_scope(self):
        StaticChecker().check(prog(
            var("x", lit(1.0)),
            block(var("y", list_expr(ident("+"), ident("x"), lit(1.0)))),
            for_stmt("i", ident("x"), lit(5.0), print_stmt(lit("ok"))),
        ))


# ── 9. 모듈 수준 check() 함수 ────────────────────────────────────────────────

class TestCheckFunction:
    def test_valid_program_does_not_raise(self):
        check(prog(var("x", lit(1.0)), print_stmt(ident("x"))))

    def test_raises_on_duplicate_declaration(self):
        with pytest.raises(CheckError):
            check(prog(var("x", lit(1.0)), var("x", lit(2.0))))

    def test_raises_on_undefined_variable(self):
        with pytest.raises(CheckError):
            check(prog(expr_stmt(ident("undefined"))))

    def test_raises_on_self_reference(self):
        with pytest.raises(CheckError):
            check(prog(var("x", list_expr(ident("+"), ident("x"), lit(1.0)))))


# ── 10. import 문 ────────────────────────────────────────────────────────────

class TestImportStmt:
    def test_path_must_be_string_literal(self):
        program = prog(import_stmt(ident("sum"), alias="sum"))
        with pytest.raises(CheckError, match="string"):
            check(program)

    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "missing.cf"
        program = prog(import_stmt(lit(str(missing)), alias="m"))
        with pytest.raises(CheckError, match="not found"):
            check(program)

    def test_valid_import_declares_alias_in_scope(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            import_stmt(lit(str(lib)), alias="m"),
            print_stmt(ident("m")),
        )
        check(program)  # 예외 없이 통과해야 한다
