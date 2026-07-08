import pytest
import unittest.mock as umock
from common import *
from Executor import *
from Executor import Function
from Optimizer import (
    StaticBinder,
    fold_constants,
    optimize,
    optimization_stats,
    resolve_bindings,
    BindingInfo,
    BindingTable,
)


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


def test_execute_import_defines_module_and_reads_variable(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(DotExpr(obj=IdentifierExpr("m"), slot="answer", args=())),
    ))
    assert execute(program) == 42.0


def test_execute_funcstmt(capsys):
    func_name = "add"
    func_params = ("a","b")
    func_body = BlockStmt((VarStmt(name='plus', initializer=ListExpr((IdentifierExpr("+"), IdentifierExpr("a"), IdentifierExpr("b")))),
                      ReturnStmt(IdentifierExpr("plus")),
                      ))

    program = Program(
        (
            FuncDefStmt(name=func_name, params=func_params, body=func_body),
            PrintStmt(ListExpr((IdentifierExpr(func_name), LiteralExpr(6), LiteralExpr(3)))),
        )
    )

    calc = SExpressionExecutor()
    calc.execute(program)

    captured = capsys.readouterr()
    assert captured.out == "9\n"

def test_execute_funcdefstmt_defines_name():
    calc = SExpressionExecutor()
    calc.execute(Program(
        (FuncDefStmt(name="greet", params=(), body=PrintStmt(LiteralExpr("hi"))),)
    ))
    assert isinstance(calc._environment.lookup("greet"), Function)


def test_execute_func_return_value():
    program = Program((
        FuncDefStmt(
            name="square",
            params=("x",),
            body=ReturnStmt(ListExpr((IdentifierExpr("*"), IdentifierExpr("x"), IdentifierExpr("x")))),
        ),
        ExpressionStmt(ListExpr((IdentifierExpr("square"), LiteralExpr(4.0)))),
    ))
    assert execute(program) == 16.0


def test_execute_func_no_params():
    program = Program((
        FuncDefStmt(
            name="get42",
            params=(),
            body=ReturnStmt(LiteralExpr(42.0)),
        ),
        ExpressionStmt(ListExpr((IdentifierExpr("get42"),))),
    ))
    assert execute(program) == 42.0


def test_execute_import_isolates_module_namespace(tmp_path):
    """임포트한 파일 안의 변수는 메인 프로그램 스코프로 새지 않는다."""
    lib = tmp_path / "lib.cf"
    lib.write_text("(var secret 1)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(IdentifierExpr("secret")),
    ))
    with pytest.raises(ExecuteError):
        execute(program)


def test_execute_dot_expr_calls_function_member_of_module(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text(
        "(func add (a b) { (return (+ a b)) })",
        encoding="utf-8",
    )
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(
            DotExpr(
                obj=IdentifierExpr("m"),
                slot="add",
                args=(LiteralExpr(1.0), LiteralExpr(2.0)),
            )
        ),
    ))
    assert execute(program) == 3.0


def test_execute_dot_expr_missing_module_member_raises(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(DotExpr(obj=IdentifierExpr("m"), slot="missing", args=())),
    ))
    with pytest.raises(ExecuteError):
        execute(program)


def test_execute_func_implicit_none_return():
    program = Program((
        FuncDefStmt(
            name="nothing",
            params=(),
            body=PrintStmt(LiteralExpr("side-effect")),
        ),
        ExpressionStmt(ListExpr((IdentifierExpr("nothing"),))),
    ))
    result = execute(program)
    assert result is None


def test_execute_func_return_no_value_is_none():
    program = Program((
        FuncDefStmt(
            name="early_exit",
            params=("x",),
            body=ReturnStmt(value=None),
        ),
        ExpressionStmt(ListExpr((IdentifierExpr("early_exit"), LiteralExpr(99.0)))),
    ))
    assert execute(program) is None


def test_execute_func_arg_count_mismatch_raises():
    program = Program((
        FuncDefStmt(
            name="add",
            params=("a", "b"),
            body=ReturnStmt(LiteralExpr(0.0)),
        ),
        ExpressionStmt(ListExpr((IdentifierExpr("add"), LiteralExpr(1.0)))),
    ))
    with pytest.raises(ExecuteError):
        execute(program)


def test_execute_dot_expr_calling_non_function_member_raises(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(
            DotExpr(obj=IdentifierExpr("m"), slot="answer", args=(LiteralExpr(1.0),))
        ),
    ))
    with pytest.raises(ExecuteError):
        execute(program)


def test_execute_func_too_many_args_raises():
    program = Program((
        FuncDefStmt(
            name="one_param",
            params=("x",),
            body=ReturnStmt(LiteralExpr(0.0)),
        ),
        ExpressionStmt(ListExpr((
            IdentifierExpr("one_param"), LiteralExpr(1.0), LiteralExpr(2.0)
        ))),
    ))
    with pytest.raises(ExecuteError):
        execute(program)


def test_execute_func_recursive_factorial():
    fac_body = IfStmt(
        condition=ListExpr((IdentifierExpr("="), IdentifierExpr("n"), LiteralExpr(0.0))),
        then_branch=ReturnStmt(LiteralExpr(1.0)),
        else_branch=ReturnStmt(
            ListExpr((
                IdentifierExpr("*"),
                IdentifierExpr("n"),
                ListExpr((
                    IdentifierExpr("fac"),
                    ListExpr((IdentifierExpr("-"), IdentifierExpr("n"), LiteralExpr(1.0))),
                )),
            ))
        ),
    )
    program = Program((
        FuncDefStmt(name="fac", params=("n",), body=fac_body),
        ExpressionStmt(ListExpr((IdentifierExpr("fac"), LiteralExpr(5.0)))),
    ))
    assert execute(program) == 120.0


def test_execute_func_closure_captures_env():
    program = Program((
        VarStmt(name="factor", initializer=LiteralExpr(3.0)),
        FuncDefStmt(
            name="triple",
            params=("x",),
            body=ReturnStmt(ListExpr((
                IdentifierExpr("*"), IdentifierExpr("x"), IdentifierExpr("factor")
            ))),
        ),
        ExpressionStmt(ListExpr((IdentifierExpr("triple"), LiteralExpr(7.0)))),
    ))
    assert execute(program) == 21.0


def test_execute_func_does_not_leak_params_to_caller():
    calc = SExpressionExecutor()
    calc.execute(Program((
        FuncDefStmt(
            name="f",
            params=("secret",),
            body=ReturnStmt(LiteralExpr(0.0)),
        ),
        ExpressionStmt(ListExpr((IdentifierExpr("f"), LiteralExpr(42.0)))),
    )))
    with pytest.raises(ExecuteError):
        calc._environment.lookup("secret")


# ── Optimizer + Executor 통합 테스트 ─────────────────────────────────────────
#
# optimize() / fold_constants() 로 컴파일된 Program 을 실제로 execute() 하여
# 결과가 올바른지, 런타임 계산이 생략됐는지 end-to-end 로 검증한다.

class TestOptimizerExecutorIntegration:

    def test_optimize_then_execute_constant_fold(self):
        """(+ 1 (* 2 3)) → optimize → execute 결과가 7.0이다."""
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0)))
        outer = ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), inner))
        program = Program((ExpressionStmt(outer),))
        optimized = optimize(program)
        assert execute(optimized) == pytest.approx(7.0)

    def test_fold_constants_then_execute_nested(self):
        """fold_constants() 로 접힌 식을 execute 해도 동일한 결과를 낸다."""
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(3.0), LiteralExpr(4.0)))
        outer = ListExpr((IdentifierExpr("+"), LiteralExpr(2.0), inner))
        program = Program((ExpressionStmt(outer),))
        folded = fold_constants(program)
        assert execute(folded) == pytest.approx(14.0)

    def test_optimize_with_variable_still_executes_correctly(self):
        """변수가 섞인 프로그램: 상수 부분만 접히고, 변수 부분은 런타임에 계산된다."""
        # (+ x (* 2 3))  →  (* 2 3)은 접혀 6.0이 되고, + x 6.0은 런타임 처리
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0)))
        outer = ListExpr((IdentifierExpr("+"), IdentifierExpr("x"), inner))
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(10.0)),
            ExpressionStmt(outer),
        ))
        optimized = optimize(program)
        assert execute(optimized) == pytest.approx(16.0)

    def test_fold_constants_reduces_list_expr_calls_to_zero(self, mocker):
        """
        완전 상수 프로그램에서 fold 후 _execute_list_expr 호출 횟수가 0이다.
        """
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0)))
        outer = ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), inner))
        program = Program((ExpressionStmt(outer),))

        folded = fold_constants(program)
        exec_instance = SExpressionExecutor()
        with umock.patch.object(exec_instance, "_execute_list_expr", wraps=exec_instance._execute_list_expr) as spy:
            exec_instance.execute(folded)
        assert spy.call_count == 0

    def test_optimization_stats_after_fold_execute(self):
        """fold_constants() 결과에 optimization_stats 가 정확히 기록된다."""
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0)))
        outer = ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), inner))
        program = Program((ExpressionStmt(outer),))
        folded = fold_constants(program)
        execute(folded)
        stats = optimization_stats(folded)
        assert stats["folded_expressions"] == 2

    def test_resolve_bindings_reports_correct_distance(self):
        """resolve_bindings 는 변수가 N단계 위 스코프에 있음을 올바르게 반환한다."""
        # (var a 1)  { { { (print a) } } }  →  a는 distance 3
        program = Program((
            VarStmt(name="a", initializer=LiteralExpr(1.0)),
            BlockStmt((
                BlockStmt((
                    BlockStmt((
                        PrintStmt(IdentifierExpr("a")),
                    )),
                )),
            )),
        ))
        table = resolve_bindings(program)
        assert table.lookup("a").distance == 3

    def test_optimize_preserves_result_for_nested_constant(self, capsys):
        """optimize() 후 print 결과가 올바른지 캡처로 검증한다."""
        # (print (+ (* 3 3) (* 4 4)))  →  25.0
        inner1 = ListExpr((IdentifierExpr("*"), LiteralExpr(3.0), LiteralExpr(3.0)))
        inner2 = ListExpr((IdentifierExpr("*"), LiteralExpr(4.0), LiteralExpr(4.0)))
        outer = ListExpr((IdentifierExpr("+"), inner1, inner2))
        program = Program((PrintStmt(outer),))
        optimized = optimize(program)
        execute(optimized)
        assert capsys.readouterr().out.strip() == "25.0"

    def test_optimize_result_passable_to_check_then_execute(self):
        """optimize() → check() → execute() 전체 파이프라인이 에러 없이 작동한다."""
        from Checker import check
        inner = ListExpr((IdentifierExpr("*"), LiteralExpr(6.0), LiteralExpr(6.0)))
        outer = ListExpr((IdentifierExpr("+"), inner, LiteralExpr(0.0)))
        program = Program((
            VarStmt(name="result", initializer=outer),
            ExpressionStmt(IdentifierExpr("result")),
        ))
        optimized = optimize(program)
        check(optimized)
        result = execute(optimized)
        assert result == pytest.approx(36.0)

    def test_fold_constants_for_loop_body_reduces_calls(self, mocker):
        """루프 body 상수 접기 후 _execute_list_expr 호출 횟수가 0이 된다."""
        const_expr = ListExpr((IdentifierExpr("*"), LiteralExpr(3.0), LiteralExpr(4.0)))
        program = Program((
            ForStmt(
                iterator="i",
                start=LiteralExpr(0.0),
                end=LiteralExpr(5.0),
                body=PrintStmt(const_expr),
            ),
        ))
        folded = fold_constants(program)
        exec_instance = SExpressionExecutor()
        with umock.patch.object(exec_instance, "_execute_list_expr", wraps=exec_instance._execute_list_expr) as spy:
            exec_instance.execute(folded)
        assert spy.call_count == 0

    def test_binding_table_lookup_returns_binding_info(self):
        """BindingTable.lookup() 반환값이 BindingInfo 타입이다."""
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(1.0)),
            PrintStmt(IdentifierExpr("x")),
        ))
        table = resolve_bindings(program)
        info = table.lookup("x")
        assert isinstance(info, BindingInfo)
        assert info.distance == 0
