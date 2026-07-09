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
import unittest.mock as umock

from common import (
    ArrayExpr,
    ArrayIndexExpr,
    BlockStmt,
    CheckError,
    ClassStmt,
    DotExpr,
    ExpressionStmt,
    ForStmt,
    FuncDefStmt,
    IdentifierExpr,
    IfStmt,
    ImportStmt,
    ListExpr,
    LiteralExpr,
    MethodDef,
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
from Checker import StaticChecker, check
from Optimizer import (
    BindingInfo,
    BindingMap,
    BindingTable,
    ConstantFolder,
    StaticBinder,
    fold_constants,
    optimize,
    optimization_stats,
    resolve_bindings,
)


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
def func_def(name: str, params: tuple, body, line: int = 1, col: int = 1) -> FuncDefStmt:
    return FuncDefStmt(name=name, params=params, body=body, location=loc(line, col))


def ret(value=None) -> ReturnStmt:
    return ReturnStmt(value=value)


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

    def test_duplicate_import_same_scope_raises(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            import_stmt(lit(str(lib)), alias="a"),
            import_stmt(lit(str(lib)), alias="b"),
        )
        with pytest.raises(CheckError, match="already imported|duplicate"):
            check(program)

    def test_alias_collision_with_existing_variable_raises(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            var("sum", init=lit(0.0)),
            import_stmt(lit(str(lib)), alias="sum"),
        )
        with pytest.raises(CheckError, match="already declared"):
            check(program)

    def test_import_cycle_raises(self, tmp_path):
        a = tmp_path / "a.cf"
        b = tmp_path / "b.cf"
        a.write_text(f'(import "{b}" alias b)', encoding="utf-8")
        b.write_text(f'(import "{a}" alias a)', encoding="utf-8")
        program = prog(import_stmt(lit(str(a)), alias="a"))
        with pytest.raises(CheckError, match="circular|cycle|순환"):
            check(program)

    def test_import_inside_for_loop_raises(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            for_stmt("i", lit(0.0), lit(1.0), import_stmt(lit(str(lib)), alias="m")),
        )
        with pytest.raises(CheckError, match="for|loop"):
            check(program)

    def test_imported_file_own_errors_propagate_as_check_error(self, tmp_path):
        lib = tmp_path / "broken.cf"
        lib.write_text("(print notDefined)", encoding="utf-8")
        program = prog(import_stmt(lit(str(lib)), alias="m"))
        with pytest.raises(CheckError, match="notDefined"):
            check(program)
# ── 10. FuncDefStmt / ReturnStmt 검사 ────────────────────────────────────────

class TestFuncDefStmt:
    def test_func_valid_declaration(self):
        StaticChecker().check(prog(
            func_def("add", ("a", "b"), print_stmt(lit(1.0)))
        ))

    def test_func_params_visible_in_body(self):
        StaticChecker().check(prog(
            func_def("add", ("a", "b"),
                print_stmt(list_expr(ident("+"), ident("a"), ident("b"))))
        ))

    def test_func_name_declared_in_outer_scope(self):
        StaticChecker().check(prog(
            func_def("add", ("a", "b"), print_stmt(lit(0.0))),
            expr_stmt(ident("add")),
        ))

    def test_func_recursive_call_allowed(self):
        StaticChecker().check(prog(
            func_def("fac", ("n",),
                print_stmt(list_expr(ident("fac"), ident("n"))))
        ))

    def test_func_duplicate_param_raises(self):
        with pytest.raises(CheckError, match="already declared"):
            StaticChecker().check(prog(
                func_def("f", ("x", "x"), print_stmt(lit(0.0)))
            ))

    def test_func_params_not_visible_outside(self):
        with pytest.raises(CheckError, match="Undefined variable 'a'"):
            StaticChecker().check(prog(
                func_def("add", ("a", "b"), print_stmt(lit(0.0))),
                expr_stmt(ident("a")),
            ))

    def test_func_undefined_var_in_body_raises(self):
        with pytest.raises(CheckError, match="Undefined variable 'missing'"):
            StaticChecker().check(prog(
                func_def("f", ("x",), print_stmt(ident("missing")))
            ))

    def test_return_inside_function_valid(self):
        StaticChecker().check(prog(
            func_def("f", ("x",), block(ret(ident("x"))))
        ))

    def test_return_no_value_inside_function_valid(self):
        StaticChecker().check(prog(
            func_def("f", ("x",), block(ret()))
        ))

    def test_return_outside_function_raises(self):
        with pytest.raises(CheckError, match="outside function"):
            StaticChecker().check(prog(ret(lit(1.0))))

    def test_return_value_checked_for_undefined_var(self):
        with pytest.raises(CheckError, match="Undefined variable 'ghost'"):
            StaticChecker().check(prog(
                func_def("f", (), block(ret(ident("ghost"))))
            ))

    def test_func_name_duplicate_with_outer_var_raises(self):
        with pytest.raises(CheckError, match="already declared"):
            StaticChecker().check(prog(
                var("f", lit(1.0)),
                func_def("f", (), print_stmt(lit(0.0))),
            ))

    def test_func_outer_var_visible_in_body(self):
        StaticChecker().check(prog(
            var("global_x", lit(10.0)),
            func_def("use_global", (),
                print_stmt(ident("global_x"))),
        ))

    def test_return_outside_function_top_level_raises(self):
        with pytest.raises(CheckError):
            StaticChecker().check(prog(ret()))


# ── 11. 정적 바인딩 (StaticBinder) ───────────────────────────────────────────
#
# 검증 전략:
#  - 바인딩 맵의 distance 값이 실제 스코프 깊이와 일치하는지 확인
#  - unittest.mock.patch.object(..., wraps=...) 로 _resolve_distance 호출 횟수 = 식별자 개수와 같음을 검증
#  - 계산된 distance 로 Environment 체인에서 직접 접근 가능함을 실증

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
        """바깥 변수를 for body에서 참조 → distance 1."""
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
        with umock.patch.object(binder, "_resolve_distance", wraps=binder._resolve_distance) as spy:
            binder.bind(program)
        assert spy.call_count == 3  # x, y, + 각 1회

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


# ── 12. 상수 접기 (ConstantFolder) ───────────────────────────────────────────
#
# 검증 전략:
#  - fold() 후 AST 노드 타입이 LiteralExpr로 치환됐는지 직접 확인
#  - unittest.mock.patch.object(..., wraps=...)로 Executor._execute_list_expr 호출 횟수를
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

        exec_before = SExpressionExecutor()
        with umock.patch.object(exec_before, "_execute_list_expr", wraps=exec_before._execute_list_expr) as spy_before:
            exec_before.execute(program)
        assert spy_before.call_count == 2

        folded = ConstantFolder().fold(program)
        exec_after = SExpressionExecutor()
        with umock.patch.object(exec_after, "_execute_list_expr", wraps=exec_after._execute_list_expr) as spy_after:
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
        with umock.patch.object(exec_before, "_execute_list_expr", wraps=exec_before._execute_list_expr) as spy_before:
            exec_before.execute(program)
        assert spy_before.call_count == 10

        folded = ConstantFolder().fold(program)
        exec_after = SExpressionExecutor()
        with umock.patch.object(exec_after, "_execute_list_expr", wraps=exec_after._execute_list_expr) as spy_after:
            exec_after.execute(folded)
        assert spy_after.call_count == 0

    def test_fold_if_condition_constant(self):
        """if 조건식이 상수이면 접힌다."""
        cond = list_expr(ident(">"), lit(5.0), lit(3.0))
        program = prog(if_stmt(cond, print_stmt(lit("yes"))))
        folded = ConstantFolder().fold(program)
        assert isinstance(folded.statements[0].condition, LiteralExpr)
        assert folded.statements[0].condition.value is True


# ── 13. Optimizer 고수준 API ──────────────────────────────────────────────────
#
# resolve_bindings(program) → BindingTable  (name → distance)
# fold_constants(program)   → Program       (상수 접기)
# optimization_stats(prog)  → dict          ("folded_expressions" 키)
# optimize(program)         → Program       (모든 최적화 적용)

class TestResolveBindings:
    """resolve_bindings() — 이름 기반 스코프 거리 테이블 검증."""

    def test_returns_binding_table(self):
        result = resolve_bindings(prog(var("x", lit(1.0))))
        assert isinstance(result, BindingTable)

    def test_variable_same_scope_distance_zero(self):
        """선언된 스코프와 동일 스코프에서 참조 → distance 0."""
        program = prog(var("x", lit(1.0)), print_stmt(ident("x")))
        table = resolve_bindings(program)
        assert table.lookup("x").distance == 0

    def test_variable_one_scope_up(self):
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
        program = prog(var("x", lit(1.0)), print_stmt(ident("x")))
        info = resolve_bindings(program).lookup("x")
        assert isinstance(info, BindingInfo)
        assert hasattr(info, "distance")

    def test_lookup_unknown_name_raises(self):
        table = resolve_bindings(prog())
        with pytest.raises(KeyError):
            table.lookup("unknown")

    def test_for_iterator_distance_zero(self):
        """for 반복자는 for 전용 스코프에 있으므로 body에서 distance 0."""
        program = prog(for_stmt("i", lit(0.0), lit(3.0), print_stmt(ident("i"))))
        table = resolve_bindings(program)
        assert table.lookup("i").distance == 0


class TestFoldConstantsAndStats:
    """fold_constants() 와 optimization_stats() 검증."""

    def test_fold_constants_returns_program(self):
        program = prog(expr_stmt(list_expr(ident("+"), lit(1.0), lit(2.0))))
        result = fold_constants(program)
        assert isinstance(result, Program)

    def test_fold_constants_computes_literal(self):
        """(+ 1 2) → LiteralExpr(3.0)."""
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

    def test_optimization_stats_has_key(self):
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), lit(1.0), inner)
        folded = fold_constants(prog(expr_stmt(outer)))
        stats = optimization_stats(folded)
        assert "folded_expressions" in stats
        assert stats["folded_expressions"] >= 1

    def test_optimization_stats_two_folds(self):
        """(+ 1 (* 2 3)) → 2회 접기."""
        inner = list_expr(ident("*"), lit(2.0), lit(3.0))
        outer = list_expr(ident("+"), lit(1.0), inner)
        folded = fold_constants(prog(expr_stmt(outer)))
        assert optimization_stats(folded)["folded_expressions"] == 2

    def test_optimization_stats_unoptimized_program_zero(self):
        """일반 Program 에 대해서는 접기 횟수 0."""
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
        program = prog(expr_stmt(list_expr(ident("+"), lit(1.0), lit(2.0))))
        assert isinstance(optimize(program), Program)

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
        check(optimized)

    def test_optimize_result_produces_correct_execution(self, capsys):
        """optimize() 결과물을 execute() 했을 때 올바른 결과를 낸다."""
        from Executor import execute
        program = prog(print_stmt(list_expr(ident("+"), lit(10.0), lit(5.0))))
        optimized = optimize(program)
        execute(optimized)
        assert capsys.readouterr().out.strip() == "15.0"


# ── helpers for OOP tests ────────────────────────────────────────────────────

def make_method(name: str, params: tuple = (), *body_stmts, has_return: bool = False) -> MethodDef:
    body = body_stmts if body_stmts else ()
    return MethodDef(name=name, params=params, body=tuple(body))


def class_stmt(name: str, parent: str | None = None, fields=(), methods=()) -> ClassStmt:
    return ClassStmt(name=name, parent=parent, fields=tuple(fields), methods=tuple(methods))


# ============================================================
# 14. ClassStmt 검사
# ============================================================

class TestClassStmtChecking:

    def test_simple_class_passes(self):
        """기본 클래스 정의는 체크를 통과한다."""
        program = prog(class_stmt("Dog"))
        check(program)

    def test_class_with_field_passes(self):
        """필드가 있는 클래스 정의도 통과한다."""
        program = prog(class_stmt("Box", fields=("x", "y")))
        check(program)

    def test_class_with_valid_parent_passes(self):
        """부모 클래스가 존재하면 통과한다."""
        program = prog(
            class_stmt("Animal"),
            class_stmt("Dog", parent="Animal"),
        )
        check(program)

    def test_class_self_inheritance_raises(self):
        """자기 자신 상속 → CheckError."""
        program = prog(class_stmt("Dog", parent="Dog"))
        with pytest.raises(CheckError, match="cannot inherit from itself"):
            check(program)

    def test_class_undefined_parent_raises(self):
        """정의되지 않은 부모 클래스 → CheckError (undefined variable)."""
        program = prog(class_stmt("Dog", parent="Animal"))
        with pytest.raises(CheckError):
            check(program)

    def test_class_parent_not_a_class_raises(self):
        """클래스가 아닌 이름을 부모로 사용 → CheckError."""
        program = prog(
            var("Animal", lit(42.0)),
            class_stmt("Dog", parent="Animal"),
        )
        with pytest.raises(CheckError, match="not a class"):
            check(program)

    def test_class_method_with_return_value_passes(self):
        """메서드 안 return 값은 허용된다."""
        method = MethodDef(
            name="getValue", params=(), body=(ReturnStmt(value=lit(1.0)),)
        )
        program = prog(class_stmt("Box", methods=[method]))
        check(program)

    def test_init_method_return_with_value_raises(self):
        """init 메서드에서 return 값 사용 → CheckError."""
        init_m = MethodDef(
            name="init", params=(), body=(ReturnStmt(value=lit(1.0)),)
        )
        program = prog(class_stmt("Box", methods=[init_m]))
        with pytest.raises(CheckError, match="init"):
            check(program)

    def test_class_method_uses_self(self):
        """메서드 본문에서 self 참조는 허용된다."""
        method = MethodDef(
            name="test", params=(), body=(ExpressionStmt(IdentifierExpr("self")),)
        )
        program = prog(class_stmt("X", methods=[method]))
        check(program)

    def test_class_method_with_params(self):
        """메서드 파라미터 참조는 허용된다."""
        method = MethodDef(
            name="add", params=("a", "b"),
            body=(ExpressionStmt(IdentifierExpr("a")),),
        )
        program = prog(class_stmt("Calc", methods=[method]))
        check(program)


# ============================================================
# 15. This / Super 검사
# ============================================================

class TestThisAndSuperChecking:

    def test_this_inside_method_passes(self):
        """메서드 안에서 This 사용 → 통과."""
        method = MethodDef(
            name="test", params=(), body=(ExpressionStmt(IdentifierExpr("This")),)
        )
        program = prog(class_stmt("X", methods=[method]))
        check(program)

    def test_this_outside_class_raises(self):
        """클래스 밖에서 This 사용 → CheckError."""
        program = prog(ExpressionStmt(IdentifierExpr("This")))
        with pytest.raises(CheckError, match="This"):
            check(program)

    def test_super_inside_method_with_parent_passes(self):
        """부모 있는 클래스 메서드 안에서 Super → 통과."""
        super_expr = SuperExpr(method="init", args=())
        method = MethodDef(
            name="init", params=(), body=(ExpressionStmt(super_expr),)
        )
        program = prog(
            class_stmt("Animal"),
            class_stmt("Dog", parent="Animal", methods=[method]),
        )
        check(program)

    def test_super_in_class_without_parent_raises(self):
        """부모 없는 클래스 메서드에서 Super → CheckError."""
        super_expr = SuperExpr(method="init", args=())
        method = MethodDef(
            name="init", params=(), body=(ExpressionStmt(super_expr),)
        )
        program = prog(class_stmt("Lone", methods=[method]))
        with pytest.raises(CheckError, match="Super"):
            check(program)

    def test_super_outside_class_raises(self):
        """클래스 밖에서 Super → CheckError."""
        program = prog(ExpressionStmt(SuperExpr(method="foo", args=())))
        with pytest.raises(CheckError, match="Super"):
            check(program)


# ============================================================
# 16. OOP 표현식 검사 (NewExpr, DotExpr, ArrayExpr, ArrayIndexExpr)
# ============================================================

class TestOopExprChecking:

    def test_new_expr_known_class_passes(self):
        """정의된 클래스를 new로 생성 → 통과."""
        program = prog(
            class_stmt("Dog"),
            ExpressionStmt(NewExpr(class_name="Dog", args=())),
        )
        check(program)

    def test_new_expr_undefined_class_raises(self):
        """정의되지 않은 클래스 new → CheckError."""
        program = prog(ExpressionStmt(NewExpr(class_name="Unknown", args=())))
        with pytest.raises(CheckError):
            check(program)

    def test_new_expr_with_args_checked(self):
        """NewExpr 인수도 검사된다 (undefined var)."""
        program = prog(
            class_stmt("Box"),
            ExpressionStmt(NewExpr(class_name="Box", args=(IdentifierExpr("undefined"),))),
        )
        with pytest.raises(CheckError):
            check(program)

    def test_dot_expr_passes(self):
        """DotExpr obj와 args 검사 통과."""
        program = prog(
            class_stmt("Dog"),
            var("d", NewExpr(class_name="Dog", args=())),
            ExpressionStmt(DotExpr(obj=IdentifierExpr("d"), slot="name", args=())),
        )
        check(program)

    def test_dot_expr_undefined_obj_raises(self):
        """DotExpr의 obj가 미정의 → CheckError."""
        program = prog(
            ExpressionStmt(DotExpr(obj=IdentifierExpr("undefined"), slot="x", args=())),
        )
        with pytest.raises(CheckError):
            check(program)

    def test_array_expr_passes(self):
        """ArrayExpr(size) 검사 통과."""
        program = prog(
            var("n", lit(5.0)),
            ExpressionStmt(ArrayExpr(size=IdentifierExpr("n"))),
        )
        check(program)

    def test_array_expr_undefined_size_raises(self):
        """ArrayExpr의 size가 미정의 → CheckError."""
        program = prog(ExpressionStmt(ArrayExpr(size=IdentifierExpr("undefined"))))
        with pytest.raises(CheckError):
            check(program)

    def test_array_index_expr_passes(self):
        """ArrayIndexExpr(array, index) 검사 통과."""
        program = prog(
            var("arr", lit(None)),
            var("i", lit(0.0)),
            ExpressionStmt(ArrayIndexExpr(
                array=IdentifierExpr("arr"),
                index=IdentifierExpr("i"),
            )),
        )
        check(program)

    def test_array_index_expr_undefined_raises(self):
        """ArrayIndexExpr에서 미정의 변수 참조 → CheckError."""
        program = prog(
            ExpressionStmt(ArrayIndexExpr(
                array=IdentifierExpr("notDefined"),
                index=lit(0.0),
            )),
        )
        with pytest.raises(CheckError):
            check(program)


# ============================================================
# 17. StaticBinder — OOP 노드 바인딩
# ============================================================

class TestStaticBinderOOP:

    def test_bind_funcdefstmt(self):
        """FuncDefStmt 본문 변수 바인딩."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(1.0)),
            FuncDefStmt(
                name="f",
                params=(),
                body=ExpressionStmt(x_ref),
            ),
        )
        bindings = StaticBinder().bind(program)
        assert id(x_ref) in bindings

    def test_bind_returnstmt(self):
        """ReturnStmt 안의 식도 바인딩."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(10.0)),
            FuncDefStmt(
                name="f",
                params=(),
                body=ReturnStmt(value=x_ref),
            ),
        )
        bindings = StaticBinder().bind(program)
        assert id(x_ref) in bindings

    def test_bind_classstmt(self):
        """ClassStmt는 클래스 이름을 스코프에 추가한다."""
        cls_ref = IdentifierExpr("Dog")
        program = prog(
            class_stmt("Dog"),
            ExpressionStmt(cls_ref),
        )
        bindings = StaticBinder().bind(program)
        assert id(cls_ref) in bindings

    def test_bind_ifstmt(self):
        """IfStmt 분기도 바인딩된다."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(1.0)),
            IfStmt(
                condition=lit(True),
                then_branch=ExpressionStmt(x_ref),
                else_branch=None,
            ),
        )
        bindings = StaticBinder().bind(program)
        assert id(x_ref) in bindings

    def test_bind_ifstmt_else_branch(self):
        """IfStmt else 분기도 바인딩된다."""
        y_ref = IdentifierExpr("y")
        program = prog(
            var("y", lit(2.0)),
            IfStmt(
                condition=lit(False),
                then_branch=ExpressionStmt(lit(0.0)),
                else_branch=ExpressionStmt(y_ref),
            ),
        )
        bindings = StaticBinder().bind(program)
        assert id(y_ref) in bindings

    def test_bind_new_expr(self):
        """NewExpr 안 args도 바인딩된다."""
        x_ref = IdentifierExpr("x")
        program = prog(
            class_stmt("Box"),
            var("x", lit(1.0)),
            ExpressionStmt(NewExpr(class_name="Box", args=(x_ref,))),
        )
        bindings = StaticBinder().bind(program)
        assert id(x_ref) in bindings

    def test_bind_dot_expr(self):
        """DotExpr obj와 args 바인딩."""
        obj_ref = IdentifierExpr("obj")
        program = prog(
            var("obj", lit(None)),
            ExpressionStmt(DotExpr(obj=obj_ref, slot="x", args=())),
        )
        bindings = StaticBinder().bind(program)
        assert id(obj_ref) in bindings

    def test_bind_super_expr(self):
        """SuperExpr args도 바인딩된다 (FuncDefStmt 본문 내부에서)."""
        x_ref = IdentifierExpr("x")
        program = prog(
            var("x", lit(5.0)),
            FuncDefStmt(
                name="f", params=(),
                body=ExpressionStmt(SuperExpr(method="init", args=(x_ref,))),
            ),
        )
        bindings = StaticBinder().bind(program)
        assert id(x_ref) in bindings


# ============================================================
# 18. ConstantFolder — 누락 경로 보완
# ============================================================

class TestConstantFolderMissingPaths:

    def test_fold_setstmt(self):
        """ConstantFolder가 SetStmt 안의 상수 표현식을 접는다."""
        const_expr = ListExpr((IdentifierExpr("+"), LiteralExpr(3.0), LiteralExpr(4.0)))
        program = prog(
            var("x", lit(0.0)),
            SetStmt(target="x", value=const_expr),
        )
        folded = ConstantFolder().fold(program)
        set_node = folded.statements[1]
        assert isinstance(set_node, SetStmt)
        assert isinstance(set_node.value, LiteralExpr)
        assert set_node.value.value == 7.0

    def test_fold_blockstmt(self):
        """ConstantFolder가 BlockStmt 안의 상수 표현식을 접는다."""
        const_expr = ListExpr((IdentifierExpr("*"), LiteralExpr(6.0), LiteralExpr(7.0)))
        program = prog(
            BlockStmt((PrintStmt(const_expr),)),
        )
        folded = ConstantFolder().fold(program)
        block = folded.statements[0]
        assert isinstance(block, BlockStmt)
        inner_print = block.statements[0]
        assert isinstance(inner_print.expression, LiteralExpr)
        assert inner_print.expression.value == pytest.approx(42.0)

    def test_fold_returns_funcdefstmt_unchanged(self):
        """FuncDefStmt는 ConstantFolder가 그대로 반환한다."""
        func = FuncDefStmt(name="f", params=(), body=ExpressionStmt(lit(1.0)))
        program = prog(func)
        folded = ConstantFolder().fold(program)
        assert folded.statements[0] is func

    def test_fold_returns_classstmt_unchanged(self):
        """ClassStmt는 ConstantFolder가 그대로 반환한다."""
        cls = ClassStmt(name="X", parent=None, fields=(), methods=())
        program = prog(cls)
        folded = ConstantFolder().fold(program)
        assert folded.statements[0] is cls

    def test_try_fold_empty_list_returns_listexpr(self):
        """빈 ListExpr는 그대로 ListExpr로 반환된다."""
        empty_list = ListExpr(())
        program = prog(ExpressionStmt(empty_list))
        folded = ConstantFolder().fold(program)
        expr = folded.statements[0].expression
        assert isinstance(expr, ListExpr)
        assert expr.elements == ()

    def test_try_fold_non_identifier_head(self):
        """ListExpr의 첫 원소가 IdentifierExpr가 아니면 그대로 반환."""
        list_with_lit_head = ListExpr((LiteralExpr(1.0), LiteralExpr(2.0)))
        program = prog(ExpressionStmt(list_with_lit_head))
        folded = ConstantFolder().fold(program)
        expr = folded.statements[0].expression
        assert isinstance(expr, ListExpr)

    def test_try_fold_unknown_op_returns_listexpr(self):
        """알 수 없는 연산자는 상수 접기하지 않고 ListExpr 그대로 반환."""
        unknown_op_list = ListExpr((IdentifierExpr("Array"), LiteralExpr(5.0)))
        program = prog(ExpressionStmt(unknown_op_list))
        folded = ConstantFolder().fold(program)
        expr = folded.statements[0].expression
        assert isinstance(expr, ListExpr)


# ============================================================
# 19. resolve_bindings — 누락 경로 보완
# ============================================================

class TestResolveBindingsMissingPaths:

    def test_resolve_setstmt(self):
        """SetStmt target도 BindingTable에 등록된다."""
        table = resolve_bindings(prog(
            var("x", lit(0.0)),
            SetStmt(target="x", value=lit(1.0)),
        ))
        assert "x" in table._data

    def test_resolve_blockstmt(self):
        """BlockStmt 내부도 바인딩 분석된다."""
        table = resolve_bindings(prog(
            var("x", lit(0.0)),
            BlockStmt((ExpressionStmt(IdentifierExpr("x")),)),
        ))
        assert "x" in table._data

    def test_resolve_ifstmt(self):
        """IfStmt 분기도 분석된다."""
        table = resolve_bindings(prog(
            var("x", lit(0.0)),
            IfStmt(
                condition=IdentifierExpr("x"),
                then_branch=ExpressionStmt(IdentifierExpr("x")),
                else_branch=ExpressionStmt(IdentifierExpr("x")),
            ),
        ))
        assert "x" in table._data

    def test_resolve_forstmt(self):
        """ForStmt 내부도 분석된다."""
        table = resolve_bindings(prog(
            ForStmt(iterator="i", start=lit(0.0), end=lit(3.0),
                    body=ExpressionStmt(IdentifierExpr("i"))),
        ))
        assert "i" in table._data

    def test_resolve_funcdefstmt(self):
        """FuncDefStmt도 분석된다."""
        x_ref = IdentifierExpr("x")
        table = resolve_bindings(prog(
            var("x", lit(0.0)),
            FuncDefStmt(name="f", params=(), body=ExpressionStmt(x_ref)),
        ))
        assert "f" in table._data or "x" in table._data

    def test_resolve_returnstmt(self):
        """ReturnStmt 내부 식도 분석된다."""
        table = resolve_bindings(prog(
            var("x", lit(1.0)),
            FuncDefStmt(
                name="f", params=(),
                body=ReturnStmt(value=IdentifierExpr("x")),
            ),
        ))
        assert "x" in table._data

    def test_resolve_classstmt(self):
        """ClassStmt는 클래스 이름을 스코프에 추가한다."""
        table = resolve_bindings(prog(
            ClassStmt(name="Dog", parent=None, fields=(), methods=()),
            ExpressionStmt(IdentifierExpr("Dog")),
        ))
        assert "Dog" in table._data

    def test_resolve_listexpr_in_collect_expr(self):
        """_collect_expr에 ListExpr 전달 시 내부 원소도 분석된다."""
        table = resolve_bindings(prog(
            var("x", lit(1.0)),
            PrintStmt(ListExpr((IdentifierExpr("+"), IdentifierExpr("x"), lit(2.0)))),
        ))
        assert "x" in table._data
