import pytest
from common import *
from Executor import *
from Checker import *
from Optimizer import StaticBinder


def test_calculate_error_division_by_zero():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("/"), LiteralExpr(6), LiteralExpr(0)))),)
    )
    with pytest.raises(ZeroDivisionError):
        execute(program)

def test_calculate_error_multiple_one_operand():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("*"), LiteralExpr(6)))),)
    )
    with pytest.raises(ExecuteError):
        execute(program)

def test_calculate_error_unsupported_operand():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("$"), LiteralExpr(6), LiteralExpr(3)))),)
    )
    with pytest.raises(ExecuteError):
        execute(program)

def test_calculate_minus_one_operand():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("-"), LiteralExpr(6)))),)
    )
    assert execute(program) == -6


def test_calculate_single_literal():
    program = Program(
        (ExpressionStmt(LiteralExpr(42.0)),)
    )
    assert execute(program) == 42.0

def test_calculate_simple_plus():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("+"), LiteralExpr(1), LiteralExpr(2)))),)
    )
    assert execute(program) == 3

def test_calculate_simple_minus():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("-"), LiteralExpr(1), LiteralExpr(2)))),)
    )
    assert execute(program) == -1

def test_calculate_simple_multiple():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("*"), LiteralExpr(2), LiteralExpr(3)))),)
    )
    assert execute(program) == 6

def test_calculate_simple_division():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("/"), LiteralExpr(6), LiteralExpr(3)))),)
    )
    assert execute(program) == 2.0

def test_calculate_simple_less_than():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("<"), LiteralExpr(6), LiteralExpr(3)))),)
    )
    assert execute(program) == False

def test_calculate_simple_greater_than():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr(">"), LiteralExpr(6), LiteralExpr(5)))),)
    )
    assert execute(program) == True

def test_calculate_simple_not():
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("!"), LiteralExpr(True)))),)
    )
    assert execute(program) == False

def test_calculate_nested_arithmetic1():
    inner = ListExpr((IdentifierExpr("*"), LiteralExpr(2), LiteralExpr(3)))
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("+"), LiteralExpr(1), inner))),)
    )
    assert execute(program) == 7

def test_calculate_nested_arithmetic2():
    inner1 = ListExpr((IdentifierExpr("*"), LiteralExpr(2), LiteralExpr(3)))
    inner2 = ListExpr((IdentifierExpr("-"), LiteralExpr(10), LiteralExpr(2)))
    inner3 = ListExpr((IdentifierExpr("/"), inner2, LiteralExpr(4)))
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("+"), inner1, inner3))),)
    )
    assert execute(program) == 8.0

def test_execute_ifstmt_then_branch():
    condition = ListExpr((IdentifierExpr("<"), LiteralExpr(2), LiteralExpr(3)))
    then_branch = VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(1), LiteralExpr(3))))
    else_branch = VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(3), LiteralExpr(3))))
    program = Program(
        (IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch),)
    )

    calc = SExpressionExecutor()
    calc.execute(program)

    assert calc._environment.lookup('test') == 3

def test_execute_ifstmt_else_branch():
    condition = ListExpr((IdentifierExpr("<"), LiteralExpr(4), LiteralExpr(3)))
    then_branch = VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(1), LiteralExpr(3))))
    else_branch = VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(3), LiteralExpr(3))))
    program = Program(
        (IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch),)
    )

    calc = SExpressionExecutor()
    calc.execute(program)

    assert calc._environment.lookup('test') == 9

def test_execute_forstmt():
    iterator = 'i'
    start = LiteralExpr(4)
    end = LiteralExpr(7)
    body = SetStmt(target='pre', value=ListExpr((IdentifierExpr("+"), IdentifierExpr(iterator), LiteralExpr(3))))

    program_pre = Program(
        (VarStmt(name='pre', initializer=LiteralExpr(1)),)
    )

    program = Program(
        (VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(1), LiteralExpr(3)))),)
    )

    program_for = Program(
        (ForStmt(iterator=iterator,start=start, end=end, body=body),)
    )

    calc = SExpressionExecutor()
    calc.execute(program_pre)
    calc.execute(program)
    calc.execute(program_for)

    assert calc._environment.lookup('pre') == 9

def test_execute_printstmt(capsys):
    program = Program(
        (PrintStmt(ListExpr((IdentifierExpr("+"), LiteralExpr(1), LiteralExpr(2)))),)
    )

    execute(program)
    captured = capsys.readouterr()

    assert captured.out == "3\n"

def test_execute_varstmt():
    program = Program(
        (VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(2), LiteralExpr(3)))),)
    )
    program_output = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("+"), IdentifierExpr('test'), LiteralExpr(3)))),)
    )

    calc = SExpressionExecutor()
    calc.execute(program)

    assert calc.execute(program_output) == 9

def test_execute_error_varstmt():
    program = Program(
        (VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(2), LiteralExpr(3)))),)
    )

    calc = SExpressionExecutor()
    calc.execute(program)

    with pytest.raises(ExecuteError):
        calc._environment.lookup('test_fail')


# ── 정적 바인딩 Executor 통합 테스트 ─────────────────────────────────────────
#
# 검증 전략:
#  - Environment.lookup_at / assign_at 단위 동작 확인
#  - SExpressionExecutor(bindings=...) 가 올바른 결과를 내는지 확인
#  - mocker.spy 로 바인딩 맵 사용 시 lookup_at 이 호출되고
#    lookup 은 호출되지 않음을 계량 검증 (스코프 탐색 제거 증명)
#  - assign_at 도 동일하게 검증

class TestEnvironmentDirectAccess:
    """Environment.lookup_at / assign_at 단위 테스트."""

    def test_lookup_at_distance_zero(self):
        """현재 스코프에서 직접 읽기."""
        env = Environment()
        env.define("x", 42.0)
        assert env.lookup_at(0, "x") == 42.0

    def test_lookup_at_distance_one(self):
        """1단계 위 스코프에서 직접 읽기."""
        parent = Environment()
        parent.define("x", 10.0)
        child = Environment(parent=parent)
        assert child.lookup_at(1, "x") == 10.0

    def test_lookup_at_distance_two(self):
        """2단계 위 스코프에서 직접 읽기."""
        grandparent = Environment()
        grandparent.define("x", 99.0)
        parent = Environment(parent=grandparent)
        child = Environment(parent=parent)
        assert child.lookup_at(2, "x") == 99.0

    def test_lookup_at_reads_correct_value_not_shadowed(self):
        """distance가 있으면 중간 스코프의 동명 변수를 건너뛰고 정확한 깊이에서 읽는다."""
        grandparent = Environment()
        grandparent.define("x", 100.0)
        parent = Environment(parent=grandparent)
        parent.define("x", 200.0)  # 중간 스코프에 동명 변수
        child = Environment(parent=parent)
        # distance=2 → grandparent의 x=100
        assert child.lookup_at(2, "x") == 100.0
        # distance=1 → parent의 x=200
        assert child.lookup_at(1, "x") == 200.0

    def test_assign_at_distance_zero(self):
        """현재 스코프에 직접 쓰기."""
        env = Environment()
        env.define("x", 0.0)
        env.assign_at(0, "x", 77.0)
        assert env._values["x"] == 77.0

    def test_assign_at_distance_one(self):
        """1단계 위 스코프에 직접 쓰기."""
        parent = Environment()
        parent.define("x", 0.0)
        child = Environment(parent=parent)
        child.assign_at(1, "x", 55.0)
        assert parent._values["x"] == 55.0

    def test_assign_at_does_not_affect_wrong_scope(self):
        """assign_at(1, ...) 은 현재 스코프(distance=0)를 변경하지 않는다."""
        parent = Environment()
        parent.define("x", 1.0)
        child = Environment(parent=parent)
        child.define("x", 2.0)
        child.assign_at(1, "x", 99.0)
        assert child._values["x"] == 2.0    # 자신은 그대로
        assert parent._values["x"] == 99.0  # 부모만 변경


class TestStaticBindingExecutor:
    """SExpressionExecutor(bindings=...) 통합 테스트."""

    def test_executor_with_binding_produces_correct_result(self):
        """바인딩 맵을 사용한 Executor도 일반 Executor와 동일한 결과를 낸다."""
        x_ref = IdentifierExpr("x")
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(42.0)),
            ExpressionStmt(x_ref),
        ))
        bindings = StaticBinder().bind(program)
        result = SExpressionExecutor(bindings=bindings).execute(program)
        assert result == 42.0

    def test_executor_with_binding_nested_block(self):
        """중첩 블록에서 바인딩 맵을 사용해도 올바른 값을 읽는다."""
        x_ref = IdentifierExpr("x")
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(7.0)),
            BlockStmt((ExpressionStmt(x_ref),)),
        ))
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 1  # x 는 1단계 위
        result = SExpressionExecutor(bindings=bindings).execute(program)
        assert result == 7.0

    def test_executor_without_binding_backward_compatible(self):
        """바인딩 맵 없이도 기존 방식대로 동작한다 (하위 호환성)."""
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(5.0)),
            ExpressionStmt(IdentifierExpr("x")),
        ))
        assert SExpressionExecutor().execute(program) == 5.0

    def test_executor_setstmt_with_binding_correct_result(self):
        """바인딩 맵이 있는 set! 도 올바르게 값을 변경한다."""
        set_node = SetStmt(target="x", value=LiteralExpr(99.0))
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(0.0)),
            BlockStmt((set_node,)),
            ExpressionStmt(IdentifierExpr("x")),
        ))
        bindings = StaticBinder().bind(program)
        calc = SExpressionExecutor(bindings=bindings)
        calc.execute(program)
        assert calc._environment.lookup("x") == 99.0

    def test_executor_for_loop_with_binding(self):
        """바인딩 맵이 있는 for 루프도 올바르게 실행된다."""
        i_ref = IdentifierExpr("i")
        program = Program((
            ForStmt(
                iterator="i",
                start=LiteralExpr(0.0),
                end=LiteralExpr(5.0),
                body=ExpressionStmt(i_ref),
            ),
        ))
        bindings = StaticBinder().bind(program)
        assert bindings[id(i_ref)] == 0  # i 는 for 스코프(distance=0)
        result = SExpressionExecutor(bindings=bindings).execute(program)
        assert result == 4  # 마지막 반복(i=4)의 ExpressionStmt 값

    def test_executor_binding_uses_lookup_at_not_lookup(self, mocker):
        """
        바인딩 맵이 있을 때 IdentifierExpr 평가 시
        Environment.lookup() 대신 lookup_at() 을 호출함을 spy로 검증한다.
        """
        x_ref = IdentifierExpr("x")
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(42.0)),
            ExpressionStmt(x_ref),
        ))
        bindings = StaticBinder().bind(program)

        executor = SExpressionExecutor(bindings=bindings)
        spy_lookup    = mocker.spy(Environment, "lookup")
        spy_lookup_at = mocker.spy(Environment, "lookup_at")

        executor.execute(program)

        # x_ref 에 대해 lookup_at 이 호출되고 lookup 은 호출되지 않음
        assert spy_lookup_at.call_count >= 1
        assert spy_lookup.call_count == 0

    def test_executor_without_binding_uses_lookup(self, mocker):
        """
        바인딩 맵이 없을 때 IdentifierExpr 평가 시 Environment.lookup() 을 호출한다.
        """
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(42.0)),
            ExpressionStmt(IdentifierExpr("x")),
        ))
        executor = SExpressionExecutor()
        spy_lookup    = mocker.spy(Environment, "lookup")
        spy_lookup_at = mocker.spy(Environment, "lookup_at")

        executor.execute(program)

        assert spy_lookup.call_count >= 1
        assert spy_lookup_at.call_count == 0

    def test_executor_nested_binding_lookup_at_correct_distance(self, mocker):
        """
        중첩 스코프에서 lookup_at 이 올바른 distance=1 로 호출됨을 기록으로 검증한다.
        """
        x_ref = IdentifierExpr("x")
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(10.0)),
            BlockStmt((ExpressionStmt(x_ref),)),
        ))
        bindings = StaticBinder().bind(program)
        assert bindings[id(x_ref)] == 1  # sanity check

        calls: list[tuple[int, str]] = []
        original = Environment.lookup_at

        def recording_lookup_at(self_env, distance, name):
            calls.append((distance, name))
            return original(self_env, distance, name)

        mocker.patch.object(Environment, "lookup_at", recording_lookup_at)

        SExpressionExecutor(bindings=bindings).execute(program)

        assert (1, "x") in calls

    def test_executor_setstmt_with_binding_uses_assign_at(self, mocker):
        """
        set! 문 실행 시 바인딩 맵이 있으면 assign_at() 을 호출하고
        assign() 은 호출하지 않음을 spy로 검증한다.
        """
        set_node = SetStmt(target="x", value=LiteralExpr(99.0))
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(0.0)),
            BlockStmt((set_node,)),
        ))
        bindings = StaticBinder().bind(program)

        executor = SExpressionExecutor(bindings=bindings)
        spy_assign    = mocker.spy(Environment, "assign")
        spy_assign_at = mocker.spy(Environment, "assign_at")

        executor.execute(program)

        assert spy_assign_at.call_count >= 1
        assert spy_assign.call_count == 0

    def test_executor_setstmt_without_binding_uses_assign(self, mocker):
        """
        바인딩 맵이 없을 때 set! 문은 assign() 을 호출하고
        assign_at() 은 호출하지 않는다.
        """
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(0.0)),
            BlockStmt((SetStmt(target="x", value=LiteralExpr(99.0)),)),
        ))
        executor = SExpressionExecutor()
        spy_assign    = mocker.spy(Environment, "assign")
        spy_assign_at = mocker.spy(Environment, "assign_at")

        executor.execute(program)

        assert spy_assign.call_count >= 1
        assert spy_assign_at.call_count == 0

    def test_executor_binding_eliminates_scope_traversal_depth(self, mocker):
        """
        3단계 중첩 스코프에서 바인딩 맵 없이는 lookup 이 3번 체인을 타지만,
        바인딩 맵 사용 시 lookup_at 한 번으로 끝남을 검증한다.
        """
        x_ref_no_bind  = IdentifierExpr("x")
        x_ref_with_bind = IdentifierExpr("x")

        # 3단계 중첩: x 는 최상위 선언
        def make_program(ref):
            return Program((
                VarStmt(name="x", initializer=LiteralExpr(1.0)),
                BlockStmt((BlockStmt((BlockStmt((ExpressionStmt(ref),)),)),)),
            ))

        # 바인딩 없는 경우: lookup 체인 탐색
        executor_no_bind = SExpressionExecutor()
        spy_lookup = mocker.spy(Environment, "lookup")
        executor_no_bind.execute(make_program(x_ref_no_bind))
        lookup_calls_no_bind = spy_lookup.call_count
        assert lookup_calls_no_bind >= 1  # 체인 탐색 발생

        spy_lookup.reset_mock()

        # 바인딩 있는 경우: lookup_at 으로 직접 접근
        prog_with_bind = make_program(x_ref_with_bind)
        bindings = StaticBinder().bind(prog_with_bind)
        assert bindings[id(x_ref_with_bind)] == 3  # 3단계 위

        spy_lookup_at = mocker.spy(Environment, "lookup_at")
        SExpressionExecutor(bindings=bindings).execute(prog_with_bind)

        assert spy_lookup.call_count == 0     # 바인딩 시 체인 탐색 없음
        assert spy_lookup_at.call_count >= 1  # 직접 접근


# ── Optimizer 모듈 + Executor 통합 테스트 ─────────────────────────────────────
#
# Optimizer.py 의 고수준 API 를 통해 최적화한 Program 을
# SExpressionExecutor 로 실행했을 때 올바른 결과를 내는지 검증한다.

from Optimizer import (
    BindingInfo, BindingTable,
    fold_constants, optimize, optimization_stats, resolve_bindings,
)


class TestOptimizerExecutorIntegration:
    """Optimizer API → Executor 실행 통합 테스트."""

    def test_optimize_then_execute_constant_fold(self):
        """optimize() 로 상수 접기 후 execute() 결과가 일반 실행과 동일하다."""
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0)))
        outer = ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), inner))
        program = Program((ExpressionStmt(outer),))

        from Executor import execute
        normal_result = execute(program)
        optimized = optimize(program)
        optimized_result = execute(optimized)
        assert optimized_result == normal_result == pytest.approx(7.0)

    def test_optimize_reduces_list_expr_calls(self, mocker):
        """optimize() 후 Executor._execute_list_expr 호출 횟수가 줄어든다."""
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(3.0), LiteralExpr(4.0)))
        outer = ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), inner))
        program = Program((ExpressionStmt(outer),))

        exec_before = SExpressionExecutor()
        spy_before = mocker.spy(exec_before, "_execute_list_expr")
        exec_before.execute(program)
        count_before = spy_before.call_count  # 2 (inner + outer)

        optimized = optimize(program)
        exec_after = SExpressionExecutor()
        spy_after = mocker.spy(exec_after, "_execute_list_expr")
        exec_after.execute(optimized)
        count_after = spy_after.call_count  # 0

        assert count_after < count_before
        assert count_after == 0

    def test_resolve_bindings_then_execute_with_static_binding(self):
        """resolve_bindings() 로 거리 확인, StaticBinder() 로 맵 생성 → Executor 실행."""
        x_ref = IdentifierExpr("x")
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(99.0)),
            BlockStmt((BlockStmt((ExpressionStmt(x_ref),)),)),
        ))

        table = resolve_bindings(program)
        assert table.lookup("x").distance == 2  # 2단계 위 스코프

        bindings = StaticBinder().bind(program)
        result = SExpressionExecutor(bindings=bindings).execute(program)
        assert result == pytest.approx(99.0)

    def test_fold_constants_stats_match_actual_folds(self):
        """fold_constants() 통계가 실제 접힌 ListExpr 수와 일치한다."""
        program = Program((
            ExpressionStmt(ListExpr((
                IdentifierExpr("+"),
                LiteralExpr(1.0),
                ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0))),
            ))),
        ))
        folded = fold_constants(program)
        stats = optimization_stats(folded)
        # (* 2 3) → 1회, (+ 1 6) → 1회 = 총 2회
        assert stats["folded_expressions"] == 2

    def test_optimize_with_for_loop_constant_body(self, capsys):
        """루프 내 상수를 optimize() 로 사전 계산 후 execute() 가 올바른 결과를 낸다."""
        from Executor import execute
        # (var sum 0) (for i 0 5 (set! sum (+ sum (* 2 3)))) (print sum)
        set_sum = SetStmt(
            target="sum",
            value=ListExpr((
                IdentifierExpr("+"),
                IdentifierExpr("sum"),
                ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0))),
            )),
        )
        program = Program((
            VarStmt(name="sum", initializer=LiteralExpr(0.0)),
            ForStmt(iterator="i", start=LiteralExpr(0.0), end=LiteralExpr(5.0), body=set_sum),
            PrintStmt(IdentifierExpr("sum")),
        ))
        optimized = optimize(program)
        execute(optimized)
        assert capsys.readouterr().out.strip() == "30.0"
