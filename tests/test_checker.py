"""
SExpressionChecker 단위 테스트

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
    ListExpr,
    LiteralExpr,
    PrintStmt,
    Program,
    SetStmt,
    SourceLocation,
    Stmt,
    VarStmt,
)
from Checker import SExpressionChecker, check
from Optimizer import BindingMap, ConstantFolder, StaticBinder


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
        SExpressionChecker().check(prog())

    def test_literal_only(self):
        SExpressionChecker().check(prog(expr_stmt(lit(42.0))))

    def test_builtin_operator_expression(self):
        SExpressionChecker().check(prog(
            expr_stmt(list_expr(ident("+"), lit(1.0), lit(2.0)))
        ))

    def test_nested_list_expression(self):
        # 기존 스켈레톤 테스트와 동일한 케이스
        SExpressionChecker().check(prog(
            expr_stmt(list_expr(
                ident("+"),
                lit(1.0),
                list_expr(lit(2.0)),
            ))
        ))

    def test_var_declare_and_use(self):
        SExpressionChecker().check(prog(
            var("x", lit(10.0)),
            expr_stmt(ident("x")),
        ))

    def test_var_no_initializer(self):
        SExpressionChecker().check(prog(var("x")))

    def test_var_uses_previously_declared_var(self):
        SExpressionChecker().check(prog(
            var("x", lit(1.0)),
            var("y", list_expr(ident("+"), ident("x"), lit(1.0))),
        ))

    def test_print_literal(self):
        SExpressionChecker().check(prog(print_stmt(lit("hello"))))

    def test_print_declared_var(self):
        SExpressionChecker().check(prog(
            var("x", lit(5.0)),
            print_stmt(ident("x")),
        ))

    def test_nested_arithmetic_expression(self):
        SExpressionChecker().check(prog(
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
            SExpressionChecker().check(prog(expr_stmt(ident(op))))


# ── 2. 변수 중복 선언 ────────────────────────────────────────────────────────

class TestDuplicateDeclaration:
    def test_duplicate_in_global_scope(self):
        with pytest.raises(CheckError, match="already declared"):
            SExpressionChecker().check(prog(
                var("x", lit(1.0), line=1),
                var("x", lit(2.0), line=2),
            ))

    def test_error_contains_variable_name(self):
        with pytest.raises(CheckError, match="'x'"):
            SExpressionChecker().check(prog(
                var("x", lit(1.0)),
                var("x", lit(2.0)),
            ))

    def test_error_contains_second_declaration_location(self):
        with pytest.raises(CheckError, match="2:5"):
            SExpressionChecker().check(prog(
                var("x", lit(1.0), line=1, col=1),
                var("x", lit(2.0), line=2, col=5),
            ))

    def test_error_contains_first_declaration_location(self):
        with pytest.raises(CheckError, match="1:1"):
            SExpressionChecker().check(prog(
                var("x", lit(1.0), line=1, col=1),
                var("x", lit(2.0), line=2, col=1),
            ))

    def test_duplicate_in_same_block(self):
        with pytest.raises(CheckError, match="already declared"):
            SExpressionChecker().check(prog(
                block(
                    var("x", lit(1.0)),
                    var("x", lit(2.0)),
                )
            ))

    def test_shadowing_in_inner_scope_is_allowed(self):
        # 다른 스코프(내부 블록)에서 같은 이름 선언 → shadowing, 허용
        SExpressionChecker().check(prog(
            var("x", lit(1.0)),
            block(var("x", lit(2.0))),
        ))

    def test_multiple_different_names_allowed(self):
        SExpressionChecker().check(prog(
            var("x", lit(1.0)),
            var("y", lit(2.0)),
            var("z", lit(3.0)),
        ))

    def test_third_declaration_is_duplicate(self):
        with pytest.raises(CheckError, match="already declared"):
            SExpressionChecker().check(prog(
                var("a", lit(1.0)),
                var("b", lit(2.0)),
                var("a", lit(3.0)),  # 세 번째가 중복
            ))


# ── 3. 자기 참조 검출 ────────────────────────────────────────────────────────

class TestSelfReference:
    def test_self_ref_no_outer_variable(self):
        # var x = x + 1 — x 가 전혀 선언된 적 없는 경우
        with pytest.raises(CheckError, match="references itself"):
            SExpressionChecker().check(prog(
                var("x", list_expr(ident("+"), ident("x"), lit(1.0)))
            ))

    def test_self_ref_with_outer_same_name(self):
        # 외부 스코프에 x 가 있어도 내부 var x 초기화식에서 x 사용 → 자기 참조
        with pytest.raises(CheckError, match="references itself"):
            SExpressionChecker().check(prog(
                var("x", lit(5.0)),
                block(
                    var("x", list_expr(ident("*"), ident("x"), lit(2.0)))
                ),
            ))

    def test_error_contains_variable_name(self):
        with pytest.raises(CheckError, match="'counter'"):
            SExpressionChecker().check(prog(
                var("counter", list_expr(ident("+"), ident("counter"), lit(1.0)))
            ))

    def test_error_contains_location(self):
        with pytest.raises(CheckError, match="3:5"):
            SExpressionChecker().check(prog(
                var("x", list_expr(ident("+"), ident("x", line=3, col=5), lit(1.0)))
            ))

    def test_self_ref_in_deeply_nested_expression(self):
        # var x = ((x + 1) * 2)
        with pytest.raises(CheckError, match="references itself"):
            SExpressionChecker().check(prog(
                var("x", list_expr(
                    ident("*"),
                    list_expr(ident("+"), ident("x"), lit(1.0)),
                    lit(2.0),
                ))
            ))

    def test_no_self_ref_different_var(self):
        # var y = x + 1 — 다른 변수 사용은 정상
        SExpressionChecker().check(prog(
            var("x", lit(10.0)),
            var("y", list_expr(ident("+"), ident("x"), lit(1.0))),
        ))

    def test_no_self_ref_outer_var_different_name_in_block(self):
        # 안쪽 스코프에서 완전히 다른 이름 사용 → 정상
        SExpressionChecker().check(prog(
            var("x", lit(5.0)),
            block(var("y", list_expr(ident("*"), ident("x"), lit(2.0)))),
        ))


# ── 4. 미정의 변수 참조 ──────────────────────────────────────────────────────

class TestUndefinedVariable:
    def test_undefined_in_expression_stmt(self):
        with pytest.raises(CheckError, match="Undefined variable 'z'"):
            SExpressionChecker().check(prog(expr_stmt(ident("z"))))

    def test_undefined_in_print_stmt(self):
        with pytest.raises(CheckError, match="Undefined variable"):
            SExpressionChecker().check(prog(print_stmt(ident("unknown"))))

    def test_undefined_in_var_initializer(self):
        with pytest.raises(CheckError, match="Undefined variable 'missing'"):
            SExpressionChecker().check(prog(var("x", ident("missing"))))

    def test_error_contains_location(self):
        with pytest.raises(CheckError, match="5:10"):
            SExpressionChecker().check(prog(expr_stmt(ident("nope", line=5, col=10))))

    def test_var_not_visible_before_declaration(self):
        with pytest.raises(CheckError, match="Undefined variable 'x'"):
            SExpressionChecker().check(prog(
                expr_stmt(ident("x")),
                var("x", lit(1.0)),
            ))

    def test_undefined_in_nested_list_expression(self):
        with pytest.raises(CheckError, match="Undefined variable 'ghost'"):
            SExpressionChecker().check(prog(
                expr_stmt(list_expr(ident("+"), lit(1.0), ident("ghost")))
            ))


# ── 5. BlockStmt 스코프 격리 ─────────────────────────────────────────────────

class TestBlockScope:
    def test_var_in_block_not_visible_outside(self):
        with pytest.raises(CheckError, match="Undefined variable 'inner'"):
            SExpressionChecker().check(prog(
                block(var("inner", lit(1.0))),
                expr_stmt(ident("inner")),
            ))

    def test_outer_var_visible_inside_block(self):
        SExpressionChecker().check(prog(
            var("outer", lit(1.0)),
            block(expr_stmt(ident("outer"))),
        ))

    def test_nested_blocks_see_all_outer_scopes(self):
        SExpressionChecker().check(prog(
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
            SExpressionChecker().check(prog(
                block(var("x", lit(1.0))),
                block(expr_stmt(ident("x"))),  # 다른 블록 — x 없음
            ))


# ── 6. IfStmt 검사 ────────────────────────────────────────────────────────────

class TestIfStmt:
    def test_if_valid_with_declared_var(self):
        SExpressionChecker().check(prog(
            var("x", lit(5.0)),
            if_stmt(
                list_expr(ident(">"), ident("x"), lit(3.0)),
                print_stmt(lit("big")),
                print_stmt(lit("small")),
            ),
        ))

    def test_if_without_else(self):
        SExpressionChecker().check(prog(
            if_stmt(lit(True), print_stmt(lit("yes")))
        ))

    def test_if_undefined_condition(self):
        with pytest.raises(CheckError, match="Undefined variable 'flag'"):
            SExpressionChecker().check(prog(
                if_stmt(ident("flag"), print_stmt(lit("yes")))
            ))

    def test_if_undefined_in_then_branch(self):
        with pytest.raises(CheckError, match="Undefined variable"):
            SExpressionChecker().check(prog(
                if_stmt(lit(True), expr_stmt(ident("undefined")))
            ))

    def test_if_undefined_in_else_branch(self):
        with pytest.raises(CheckError, match="Undefined variable"):
            SExpressionChecker().check(prog(
                if_stmt(
                    lit(True),
                    print_stmt(lit("ok")),
                    expr_stmt(ident("undefined")),
                )
            ))

    def test_if_then_block_scope_not_visible_outside(self):
        with pytest.raises(CheckError, match="Undefined variable 'x'"):
            SExpressionChecker().check(prog(
                if_stmt(lit(True), block(var("x", lit(1.0)))),
                expr_stmt(ident("x")),  # 블록 스코프 밖
            ))


# ── 7. ForStmt 반복자 스코프 및 중복 선언 ────────────────────────────────────

class TestForStmt:
    def test_for_valid(self):
        SExpressionChecker().check(prog(
            for_stmt("i", lit(1.0), lit(5.0), print_stmt(lit("loop")))
        ))

    def test_for_iterator_visible_in_body(self):
        SExpressionChecker().check(prog(
            for_stmt("i", lit(1.0), lit(5.0), print_stmt(ident("i")))
        ))

    def test_for_iterator_not_visible_after_loop(self):
        with pytest.raises(CheckError, match="Undefined variable 'i'"):
            SExpressionChecker().check(prog(
                for_stmt("i", lit(1.0), lit(5.0), print_stmt(lit("ok"))),
                expr_stmt(ident("i")),
            ))

    def test_for_start_checked_in_outer_scope(self):
        with pytest.raises(CheckError, match="Undefined variable 'start'"):
            SExpressionChecker().check(prog(
                for_stmt("i", ident("start"), lit(5.0), print_stmt(lit("ok")))
            ))

    def test_for_end_checked_in_outer_scope(self):
        with pytest.raises(CheckError, match="Undefined variable 'end'"):
            SExpressionChecker().check(prog(
                for_stmt("i", lit(1.0), ident("end"), print_stmt(lit("ok")))
            ))

    def test_for_uses_outer_var_for_range(self):
        SExpressionChecker().check(prog(
            var("n", lit(10.0)),
            for_stmt("i", lit(1.0), ident("n"), print_stmt(ident("i"))),
        ))

    def test_for_iterator_not_visible_in_start_expr(self):
        # start/end 는 for 스코프 진입 전 평가 → 반복자 미노출
        with pytest.raises(CheckError, match="Undefined variable 'i'"):
            SExpressionChecker().check(prog(
                for_stmt("i", ident("i"), lit(5.0), print_stmt(lit("ok")))
            ))

    def test_for_iterator_redeclare_in_same_for_scope(self):
        # 블록 없는 for body 에서 반복자 이름을 var 로 재선언 → 중복
        with pytest.raises(CheckError, match="already declared"):
            SExpressionChecker().check(prog(
                for_stmt("i", lit(1.0), lit(3.0), var("i", lit(99.0)))
            ))

    def test_for_iterator_shadow_in_body_block_is_allowed(self):
        # body 가 BlockStmt 이면 별도 스코프 → shadowing 허용
        SExpressionChecker().check(prog(
            for_stmt("i", lit(1.0), lit(3.0), block(
                var("i", lit(99.0)),
            ))
        ))

    def test_nested_for_different_iterators(self):
        SExpressionChecker().check(prog(
            for_stmt("i", lit(1.0), lit(3.0),
                for_stmt("j", lit(1.0), lit(3.0),
                    print_stmt(list_expr(ident("+"), ident("i"), ident("j")))
                )
            )
        ))

    def test_nested_for_same_iterator_name_shadows(self):
        # 안쪽 for 가 바깥 i 를 shadowing — 허용
        SExpressionChecker().check(prog(
            for_stmt("i", lit(1.0), lit(3.0),
                for_stmt("i", lit(1.0), lit(3.0),
                    print_stmt(ident("i"))
                )
            )
        ))


# ── 8. 복합 시나리오 ──────────────────────────────────────────────────────────

class TestComplexPrograms:
    def test_accumulate_with_for(self):
        SExpressionChecker().check(prog(
            var("total", lit(0.0)),
            for_stmt("i", lit(1.0), lit(5.0),
                expr_stmt(list_expr(ident("+"), ident("total"), ident("i")))
            ),
            print_stmt(ident("total")),
        ))

    def test_var_chain_with_arithmetic(self):
        SExpressionChecker().check(prog(
            var("a", lit(1.0)),
            var("b", list_expr(ident("+"), ident("a"), lit(1.0))),
            var("c", list_expr(ident("+"), ident("b"), lit(1.0))),
            print_stmt(ident("c")),
        ))

    def test_if_with_outer_var(self):
        SExpressionChecker().check(prog(
            var("x", lit(10.0)),
            if_stmt(
                list_expr(ident(">"), ident("x"), lit(5.0)),
                print_stmt(lit("big")),
                print_stmt(lit("small")),
            ),
        ))

    def test_for_body_uses_outer_var(self):
        SExpressionChecker().check(prog(
            var("factor", lit(2.0)),
            for_stmt("i", lit(1.0), lit(5.0),
                print_stmt(list_expr(ident("*"), ident("i"), ident("factor")))
            ),
        ))

    def test_block_and_for_share_outer_scope(self):
        SExpressionChecker().check(prog(
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


# ── 10. 정적 바인딩 (StaticBinder) ───────────────────────────────────────────
#
# 검증 전략:
#  - 바인딩 맵의 distance 값이 실제 스코프 깊이와 일치하는지 확인
#  - mocker.spy로 _resolve_distance 호출 횟수가 식별자 개수와 정확히 같음을 검증
#    (런타임이 아닌 컴파일 타임에 정확히 1회씩만 계산됨을 보장)
#  - 계산된 distance를 사용해 Environment 체인에서 직접 접근 가능함을 실증

class TestStaticBinder:

    def test_variable_in_same_scope_distance_zero(self):
        """현재 스코프에 선언된 변수를 같은 스코프에서 참조 → distance 0."""
        x_ref = IdentifierExpr("x")
        program = prog(var("x", lit(1.0)), expr_stmt(x_ref))
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 0

    def test_variable_one_scope_up(self):
        """바깥 스코프 변수를 안쪽 블록에서 참조 → distance 1."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(10.0)),
            block(print_stmt(x_ref)),
        )
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 1

    def test_variable_two_scopes_up(self):
        """두 단계 위 스코프 변수 참조 → distance 2."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(10.0)),
            block(block(print_stmt(x_ref))),
        )
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 2

    def test_deeply_nested_three_scopes_up(self):
        """세 단계 위 스코프 변수 참조 → distance 3."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(1.0)),
            block(block(block(expr_stmt(x_ref)))),
        )
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 3

    def test_for_iterator_distance_zero_in_body(self):
        """for 반복자는 for 전용 스코프(distance 0)에서 직접 접근."""
        i_ref = IdentifierExpr("i")
        program = prog(for_stmt("i", lit(0.0), lit(3.0), print_stmt(i_ref)))
        bindings = StaticBinder().bind(program)
        assert bindings[id(i_ref)] == 0

    def test_outer_variable_from_for_body_distance_one(self):
        """바깥 변수를 for body에서 참조 → distance 1 (for 스코프가 1단계)."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(5.0)),
            for_stmt("i", lit(0.0), lit(3.0), print_stmt(x_ref)),
        )
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 1

    def test_two_different_references_get_own_entries(self):
        """동일 이름이라도 서로 다른 IdentifierExpr 객체는 각자의 엔트리를 가진다."""
        x_ref1 = IdentifierExpr("x")
        x_ref2 = IdentifierExpr("x")
        program = prog(
            var("x", lit(1.0)),
            print_stmt(x_ref1),
            print_stmt(x_ref2),
        )
        bindings = StaticBinder().bind(program)
        assert id(x_ref1) in bindings
        assert id(x_ref2) in bindings
        assert bindings[id(x_ref1)] == bindings[id(x_ref2)] == 0

    def test_set_stmt_target_binding_stored(self):
        """SetStmt의 할당 대상 변수도 바인딩 거리가 기록된다."""
        set_node = SetStmt(target="x", value=lit(42.0))
        program = prog(
            var("x", lit(0.0)),
            block(set_node),  # x는 1단계 위 스코프
        )
        bindings = StaticBinder().bind(program)
        assert bindings[id(set_node)] == 1

    def test_builtin_op_distance_recorded(self):
        """내장 연산자(+)는 전역 스코프에 있으므로 최상위에서 distance 0."""
        plus_ref = IdentifierExpr("+")
        program = prog(expr_stmt(plus_ref))
        bindings = StaticBinder().bind(program)
        assert bindings[id(plus_ref)] == 0

    def test_spy_resolve_distance_called_once_per_identifier(self, mocker):
        """
        _resolve_distance는 IdentifierExpr 당 컴파일 타임에 정확히 1회만 호출된다.
        (런타임에 N번 반복하는 대신 사전 계산 1회로 끝남을 spy로 검증)
        """
        x_ref = IdentifierExpr("x")
        y_ref = IdentifierExpr("y")
        plus_ref = IdentifierExpr("+")
        program = prog(
            var("x", lit(1.0)),
            var("y", lit(2.0)),
            print_stmt(list_expr(plus_ref, x_ref, y_ref)),
        )
        binder = StaticBinder()
        spy = mocker.spy(binder, "_resolve_distance")
        binder.bind(program)
        # x, y, + 각 1회 → 총 3회 (런타임 반복 횟수와 무관)
        assert spy.call_count == 3

    def test_distance_enables_direct_environment_access(self):
        """
        바인딩 맵의 distance를 사용해 Environment 체인을 distance만큼만
        이동하면 스코프 전체를 탐색하지 않고도 변수에 직접 접근할 수 있음을 검증.
        """
        from Executor import Environment

        x_ref = IdentifierExpr("x", location=loc(3, 1))
        program = prog(
            var("x", lit(10.0)),
            block(block(print_stmt(x_ref))),  # x는 2단계 위
        )
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 2

        # 동일한 스코프 구조를 Environment로 재현
        env_global = Environment()
        env_global.define("x", 10.0)
        env_block1 = Environment(parent=env_global)
        env_block2 = Environment(parent=env_block1)

        # distance=2만큼 parent를 타고 올라가면 바로 x를 찾을 수 있음
        target = env_block2
        for _ in range(bindings[id(x_ref)]):
            target = target.parent
        assert target._values["x"] == 10.0

    def test_binding_map_is_dict(self):
        """bind() 반환값은 dict 타입이다."""
        result = StaticBinder().bind(prog())
        assert isinstance(result, dict)

    def test_empty_program_returns_empty_map(self):
        """빈 프로그램 → 빈 바인딩 맵."""
        bindings = StaticBinder().bind(prog())
        assert bindings == {}


# ── 11. 상수 접기 (ConstantFolder) ───────────────────────────────────────────
#
# 검증 전략:
#  - fold() 후 AST 노드 타입이 LiteralExpr로 치환됐는지 직접 확인
#  - mocker.spy로 Executor._execute_list_expr 호출 횟수를
#    접기 전 N회 → 접기 후 0회로 줄었음을 계량적으로 검증
#  - 원본 Program이 불변(frozen dataclass)임을 확인

class TestConstantFolder:

    def test_fold_basic_addition(self):
        """(+ 1.0 2.0) → LiteralExpr(3.0)"""
        expr = list_expr(ident("+"), lit(1.0), lit(2.0))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value == pytest.approx(3.0)

    def test_fold_multiplication(self):
        """(* 3.0 4.0) → LiteralExpr(12.0)"""
        expr = list_expr(ident("*"), lit(3.0), lit(4.0))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value == pytest.approx(12.0)

    def test_fold_nested_fully_constant(self):
        """(+ 1.0 (* 2.0 3.0)) → LiteralExpr(7.0) — 중첩 상수도 한 번에 접힘."""
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), lit(1.0), inner)
        folded = ConstantFolder().fold(prog(expr_stmt(outer)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value == pytest.approx(7.0)

    def test_fold_comparison_less_than(self):
        """(< 1.0 2.0) → LiteralExpr(True)"""
        expr = list_expr(ident("<"), lit(1.0), lit(2.0))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value is True

    def test_fold_unary_negation(self):
        """(- 5.0) → LiteralExpr(-5.0)"""
        expr = list_expr(ident("-"), lit(5.0))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value == pytest.approx(-5.0)

    def test_fold_boolean_and(self):
        """(and True False) → LiteralExpr(False)"""
        expr = list_expr(ident("and"), lit(True), lit(False))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value is False

    def test_fold_boolean_not(self):
        """(not True) → LiteralExpr(False)"""
        expr = list_expr(ident("not"), lit(True))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value is False

    def test_fold_string_concatenation(self):
        """(+ "hello" " world") → LiteralExpr("hello world")"""
        expr = list_expr(ident("+"), lit("hello"), lit(" world"))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, LiteralExpr)
        assert result.value == "hello world"

    def test_fold_with_variable_not_folded(self):
        """(+ x 1.0) — x가 변수이므로 접기 불가, ListExpr 유지."""
        x_ref = IdentifierExpr("x")
        expr = list_expr(ident("+"), x_ref, lit(1.0))
        folded = ConstantFolder().fold(prog(var("x", lit(0.0)), expr_stmt(expr)))
        result = folded.statements[1].expression
        assert isinstance(result, ListExpr)

    def test_fold_partial_constant_not_folded(self):
        """(+ x (* 2.0 3.0)) — 내부 (* 2 3)은 접히지만 외부는 x 때문에 유지."""
        x_ref = IdentifierExpr("x")
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), x_ref, inner)
        folded = ConstantFolder().fold(prog(var("x", lit(0.0)), expr_stmt(outer)))
        result = folded.statements[1].expression
        # 외부 ListExpr는 유지, 내부는 LiteralExpr(6.0)으로 접혀야 함
        assert isinstance(result, ListExpr)
        assert isinstance(result.elements[2], LiteralExpr)
        assert result.elements[2].value == pytest.approx(6.0)

    def test_fold_division_by_zero_preserved(self):
        """(/ 1.0 0.0) — ZeroDivisionError 발생 가능 → 접기 안 함, ListExpr 유지."""
        expr = list_expr(ident("/"), lit(1.0), lit(0.0))
        folded = ConstantFolder().fold(prog(expr_stmt(expr)))
        result = folded.statements[0].expression
        assert isinstance(result, ListExpr)

    def test_fold_in_for_loop_body(self):
        """for 루프 body 안의 상수 표현식도 접힌다 (루프 내 반복 계산 제거)."""
        const_expr = list_expr(ident("*"), lit(2.0), lit(3.0))
        program = prog(for_stmt("i", lit(0.0), lit(10.0), print_stmt(const_expr)))
        folded = ConstantFolder().fold(program)
        body_expr = folded.statements[0].body.expression
        assert isinstance(body_expr, LiteralExpr)
        assert body_expr.value == pytest.approx(6.0)

    def test_fold_in_var_initializer(self):
        """var 선언의 초기화식도 상수 접기 대상이다."""
        init_expr = list_expr(ident("+"), lit(10.0), lit(5.0))
        program = prog(var("x", init_expr))
        folded = ConstantFolder().fold(program)
        assert isinstance(folded.statements[0].initializer, LiteralExpr)
        assert folded.statements[0].initializer.value == pytest.approx(15.0)

    def test_fold_preserves_original_program(self):
        """fold()는 새 Program을 반환하고 원본 AST를 변경하지 않는다."""
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        program = prog(expr_stmt(inner))
        _ = ConstantFolder().fold(program)
        # 원본은 여전히 ListExpr
        assert isinstance(program.statements[0].expression, ListExpr)

    def test_fold_reduces_executor_calls_from_n_to_zero(self, mocker):
        """
        수식 합치기 후 Executor._execute_list_expr 호출 횟수가
        N → 0 으로 줄어드는지 spy로 계량 검증.
        (+ 1 (* 2 3)) → list expr 2개 → 접기 후 0개
        """
        from Executor import SExpressionExecutor

        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), lit(1.0), inner)
        program = prog(expr_stmt(outer))

        # 접기 전: ListExpr 2개가 실행됨
        exec_before = SExpressionExecutor()
        spy_before = mocker.spy(exec_before, "_execute_list_expr")
        exec_before.execute(program)
        assert spy_before.call_count == 2

        # 접기 후: 모든 상수가 LiteralExpr로 치환 → list expr 실행 0회
        folded = ConstantFolder().fold(program)
        exec_after = SExpressionExecutor()
        spy_after = mocker.spy(exec_after, "_execute_list_expr")
        exec_after.execute(folded)
        assert spy_after.call_count == 0

    def test_fold_nested_loop_constant_reduces_repeated_calls(self, mocker):
        """
        루프 body 내 상수 표현식 접기의 효과: 10회 반복에서
        접기 전 10회 계산 → 접기 후 0회 계산.
        """
        from Executor import SExpressionExecutor

        const_expr = list_expr(ident("*"), lit(3.0), lit(4.0))
        program = prog(for_stmt("i", lit(0.0), lit(10.0), print_stmt(const_expr)))

        exec_before = SExpressionExecutor()
        spy_before = mocker.spy(exec_before, "_execute_list_expr")
        exec_before.execute(program)
        assert spy_before.call_count == 10  # 루프 10회 × list expr 1개

        folded = ConstantFolder().fold(program)
        exec_after = SExpressionExecutor()
        spy_after = mocker.spy(exec_after, "_execute_list_expr")
        exec_after.execute(folded)
        assert spy_after.call_count == 0  # 접기 후 계산 없음

    def test_fold_if_condition_constant(self):
        """if 조건식이 상수이면 접힌다."""
        cond = list_expr(ident(">"), lit(5.0), lit(3.0))
        program = prog(if_stmt(cond, print_stmt(lit("yes"))))
        folded = ConstantFolder().fold(program)
        assert isinstance(folded.statements[0].condition, LiteralExpr)
        assert folded.statements[0].condition.value is True


# ── 12. Optimizer 고수준 API ──────────────────────────────────────────────────
#
# src/Optimizer.py 의 공개 함수를 검증한다.
#
#   resolve_bindings(program) → BindingTable  (name → distance)
#   fold_constants(program)   → Program       (상수 접기)
#   optimization_stats(prog)  → dict          ("folded_expressions" 키)
#   optimize(program)         → Program       (모든 최적화 적용)

from Optimizer import BindingInfo, BindingTable, fold_constants, optimize, optimization_stats, resolve_bindings


class TestResolveBindings:
    """resolve_bindings() — 이름 기반 스코프 거리 테이블 검증."""

    def test_returns_binding_table(self):
        """반환값이 BindingTable 인스턴스이다."""
        result = resolve_bindings(prog(var("x", lit(1.0))))
        assert isinstance(result, BindingTable)

    def test_variable_same_scope_distance_zero(self):
        """선언된 스코프와 동일 스코프에서 참조 → distance 0."""
        program = prog(var("x", lit(1.0)), print_stmt(ident("x")))
        table = resolve_bindings(program)
        assert table.lookup("x").distance == 0

    def test_variable_one_scope_up(self):
        """1단계 위 스코프 변수 → distance 1."""
        program = prog(var("x", lit(1.0)), block(print_stmt(ident("x"))))
        table = resolve_bindings(program)
        assert table.lookup("x").distance == 1

    def test_variable_three_scopes_up(self):
        """3단계 위 스코프 변수 → distance 3."""
        program = prog(
            var("a", lit(1.0)),
            block(block(block(print_stmt(ident("a"))))),
        )
        table = resolve_bindings(program)
        assert table.lookup("a").distance == 3

    def test_lookup_returns_binding_info(self):
        """lookup() 반환값이 BindingInfo 이고 distance 속성을 갖는다."""
        program = prog(var("x", lit(1.0)), print_stmt(ident("x")))
        info = resolve_bindings(program).lookup("x")
        assert isinstance(info, BindingInfo)
        assert hasattr(info, "distance")

    def test_lookup_unknown_name_raises(self):
        """선언되지 않은 이름 조회 시 KeyError."""
        table = resolve_bindings(prog())
        with pytest.raises(KeyError):
            table.lookup("unknown")

    def test_for_iterator_distance_zero(self):
        """for 반복자는 for 전용 스코프에 있으므로 body 에서 distance 0."""
        program = prog(for_stmt("i", lit(0.0), lit(3.0), print_stmt(ident("i"))))
        table = resolve_bindings(program)
        assert table.lookup("i").distance == 0


class TestFoldConstantsAndStats:
    """fold_constants() 와 optimization_stats() 검증."""

    def test_fold_constants_returns_program(self):
        """fold_constants() 는 Program 을 반환한다."""
        program = prog(expr_stmt(list_expr(ident("+"), lit(1.0), lit(2.0))))
        result = fold_constants(program)
        assert isinstance(result, Program)

    def test_fold_constants_computes_literal(self):
        """(+ 1 2) → LiteralExpr(3.0) 로 치환된다."""
        program = prog(expr_stmt(list_expr(ident("+"), lit(1.0), lit(2.0))))
        folded = fold_constants(program)
        assert isinstance(folded.statements[0].expression, LiteralExpr)
        assert folded.statements[0].expression.value == pytest.approx(3.0)

    def test_fold_constants_nested(self):
        """(+ 1 (* 2 3)) → LiteralExpr(7.0)."""
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), lit(1.0), inner)
        folded = fold_constants(prog(expr_stmt(outer)))
        assert isinstance(folded.statements[0].expression, LiteralExpr)
        assert folded.statements[0].expression.value == pytest.approx(7.0)

    def test_optimization_stats_folded_count(self):
        """fold_constants() 로 접힌 노드 수가 통계에 기록된다."""
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), lit(1.0), inner)
        folded = fold_constants(prog(expr_stmt(outer)))
        stats = optimization_stats(folded)
        assert "folded_expressions" in stats
        assert stats["folded_expressions"] >= 1

    def test_optimization_stats_two_folds(self):
        """(+ 1 (* 2 3)) → 2회 접기 (inner + outer)."""
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), lit(1.0), inner)
        folded = fold_constants(prog(expr_stmt(outer)))
        assert optimization_stats(folded)["folded_expressions"] == 2

    def test_optimization_stats_unoptimized_program_zero(self):
        """일반 Program 에 대해서는 접기 횟수 0 을 반환한다."""
        program = prog(expr_stmt(lit(42.0)))
        assert optimization_stats(program)["folded_expressions"] == 0

    def test_fold_constants_preserves_original(self):
        """원본 Program 은 불변이다."""
        original_expr = list_expr(ident("+"), lit(1.0), lit(2.0))
        program = prog(expr_stmt(original_expr))
        fold_constants(program)
        assert isinstance(program.statements[0].expression, ListExpr)

    def test_fold_constants_variable_not_folded(self):
        """변수를 포함한 식은 접히지 않는다."""
        program = prog(
            var("x", lit(1.0)),
            expr_stmt(list_expr(ident("+"), ident("x"), lit(2.0))),
        )
        folded = fold_constants(program)
        assert isinstance(folded.statements[1].expression, ListExpr)
        assert optimization_stats(folded)["folded_expressions"] == 0


class TestOptimize:
    """optimize() — 전체 최적화 파이프라인 검증."""

    def test_optimize_returns_program(self):
        """optimize() 는 Program 을 반환한다."""
        program = prog(expr_stmt(list_expr(ident("+"), lit(1.0), lit(2.0))))
        result = optimize(program)
        assert isinstance(result, Program)

    def test_optimize_applies_constant_folding(self):
        """optimize() 후 상수 표현식이 LiteralExpr 로 치환된다."""
        program = prog(expr_stmt(list_expr(ident("*"), lit(3.0), lit(4.0))))
        optimized = optimize(program)
        assert isinstance(optimized.statements[0].expression, LiteralExpr)
        assert optimized.statements[0].expression.value == pytest.approx(12.0)

    def test_optimize_result_passable_to_check(self):
        """optimize() 결과물은 check() 를 정상 통과한다."""
        program = prog(
            var("x", lit(1.0)),
            print_stmt(list_expr(ident("+"), ident("x"), list_expr(ident("*"), lit(2.0), lit(3.0)))),
        )
        check(program)
        optimized = optimize(program)
        check(optimized)  # 최적화 후 semantic check 재통과

    def test_optimize_result_produces_correct_execution(self, capsys):
        """optimize() 결과물을 execute() 했을 때 올바른 결과를 낸다."""
        from Executor import execute
        program = prog(print_stmt(list_expr(ident("+"), lit(10.0), lit(5.0))))
        optimized = optimize(program)
        execute(optimized)
        assert capsys.readouterr().out.strip() == "15.0"
