import pytest
import unittest.mock as umock
from common import *
from Executor import *
from Executor import Function, ClassDef, ClassInstance, Environment, _ReturnSignal
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

def test_execute_varstmt_twice():
    program_error = Program(
        (VarStmt(name='test', initializer=ListExpr((LiteralExpr(3), IdentifierExpr("*"), LiteralExpr(3)))),)
    )

    program = Program(
        (VarStmt(name='test', initializer=ListExpr((IdentifierExpr("*"), LiteralExpr(2), LiteralExpr(3)))),)
    )

    program_output = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("+"), IdentifierExpr('test'), LiteralExpr(3)))),)
    )

    calc = SExpressionExecutor()
    try:
        calc.execute(program_error)
    except ExecuteError:
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


# ============================================================
# OOP 실행 테스트
# ============================================================

def _make_method(name: str, params: tuple, *body_stmts) -> MethodDef:
    return MethodDef(name=name, params=params, body=tuple(body_stmts))


def _make_class(name: str, parent=None, fields=(), methods=()):
    return ClassStmt(name=name, parent=parent, fields=fields, methods=tuple(methods))


class TestClassDef:

    def test_get_all_field_names_no_parent(self):
        """부모 없는 ClassDef의 get_all_field_names는 자신의 필드만 반환."""
        cls = ClassDef(name="Dog", parent=None, field_names=("name", "age"), methods={})
        assert cls.get_all_field_names() == ["name", "age"]

    def test_get_all_field_names_with_parent(self):
        """부모 ClassDef의 필드가 자식 필드보다 먼저 나온다."""
        parent = ClassDef(name="Animal", parent=None, field_names=("species",), methods={})
        child = ClassDef(name="Dog", parent=parent, field_names=("name",), methods={})
        all_fields = child.get_all_field_names()
        assert all_fields == ["species", "name"]

    def test_get_all_field_names_deduplicates(self):
        """부모와 자식에 같은 필드 이름이 있으면 한 번만 등록된다."""
        parent = ClassDef(name="A", parent=None, field_names=("x",), methods={})
        child = ClassDef(name="B", parent=parent, field_names=("x", "y"), methods={})
        assert child.get_all_field_names() == ["x", "y"]

    def test_lookup_method_own(self):
        """자신의 메서드를 찾아 반환한다."""
        method = MethodDef(name="speak", params=(), body=())
        cls = ClassDef(name="Dog", parent=None, field_names=(), methods={"speak": method})
        result = cls.lookup_method("speak")
        assert result is not None
        found_method, defining_class = result
        assert found_method is method
        assert defining_class is cls

    def test_lookup_method_from_parent(self):
        """자신에게 없으면 부모 클래스에서 메서드를 찾는다."""
        method = MethodDef(name="breathe", params=(), body=())
        parent = ClassDef(name="Animal", parent=None, field_names=(), methods={"breathe": method})
        child = ClassDef(name="Dog", parent=parent, field_names=(), methods={})
        result = child.lookup_method("breathe")
        assert result is not None
        found_method, defining_class = result
        assert found_method is method
        assert defining_class is parent

    def test_lookup_method_not_found_returns_none(self):
        """정의되지 않은 메서드 조회는 None을 반환."""
        cls = ClassDef(name="Dog", parent=None, field_names=(), methods={})
        assert cls.lookup_method("fly") is None


class TestClassInstance:

    def test_repr(self):
        """ClassInstance.__repr__는 '<ClassName instance>' 형태다."""
        cls = ClassDef(name="Dog", parent=None, field_names=(), methods={})
        instance = ClassInstance(class_def=cls)
        assert repr(instance) == "<Dog instance>"


class TestEnvironmentAssign:

    def test_assign_existing_var(self):
        """정의된 변수는 assign으로 값을 바꿀 수 있다."""
        env = Environment()
        env.define("x", 1)
        env.assign("x", 42)
        assert env.lookup("x") == 42

    def test_assign_undefined_raises(self):
        """미정의 변수에 assign하면 ExecuteError."""
        env = Environment()
        with pytest.raises(ExecuteError):
            env.assign("undefined", 99)

    def test_assign_in_parent_scope(self):
        """자식 환경에서 부모 스코프 변수에 assign 가능."""
        parent = Environment()
        parent.define("x", 0)
        child = Environment(parent=parent)
        child.assign("x", 7)
        assert parent.lookup("x") == 7


class TestUnsupportedStmt:

    def test_unsupported_stmt_type_raises(self):
        """_STMT_DISPATCH에 없는 Stmt 타입은 ExecuteError."""
        from dataclasses import dataclass
        from common import Stmt

        @dataclass(frozen=True, slots=True)
        class _UnknownStmt(Stmt):
            pass

        program = Program((_UnknownStmt(),))
        with pytest.raises(ExecuteError):
            execute(program)


class TestIfStmtNoElse:

    def test_if_false_no_else_returns_none(self):
        """조건이 False이고 else 없으면 None을 반환."""
        program = Program((
            IfStmt(
                condition=LiteralExpr(False),
                then_branch=PrintStmt(LiteralExpr(1.0)),
                else_branch=None,
            ),
        ))
        result = execute(program)
        assert result is None


class TestClassExecution:

    def test_define_class_registers_in_env(self):
        """ClassStmt 실행 후 환경에 ClassDef가 등록된다."""
        stmt = _make_class("Dog", fields=("name",))
        program = Program((stmt,))
        ex = SExpressionExecutor()
        ex.execute(program)
        val = ex._environment.lookup("Dog")
        assert isinstance(val, ClassDef)
        assert val.name == "Dog"

    def test_create_instance_via_new_expr(self):
        """(new Dog) → ClassInstance."""
        class_stmt = _make_class("Dog", fields=("name",))
        new_expr_stmt = ExpressionStmt(NewExpr(class_name="Dog", args=()))
        program = Program((class_stmt, new_expr_stmt))
        result = execute(program)
        assert isinstance(result, ClassInstance)
        assert result.class_def.name == "Dog"

    def test_create_instance_via_list_expr(self):
        """(Dog) → creates ClassInstance (ClassDef callable via list_expr)."""
        class_stmt = _make_class("Cat")
        call_stmt = ExpressionStmt(
            ListExpr((IdentifierExpr("Cat"),))
        )
        program = Program((class_stmt, call_stmt))
        result = execute(program)
        assert isinstance(result, ClassInstance)

    def test_instance_has_init_fields(self):
        """init 없는 클래스의 인스턴스는 필드가 None으로 초기화된다."""
        class_stmt = _make_class("Box", fields=("width", "height"))
        new_stmt = ExpressionStmt(NewExpr(class_name="Box", args=()))
        program = Program((class_stmt, new_stmt))
        result = execute(program)
        assert isinstance(result, ClassInstance)
        assert result.fields == {"width": None, "height": None}

    def test_init_method_sets_fields(self):
        """init 메서드로 필드를 설정한다."""
        init_method = _make_method(
            "init", ("val",),
            ExpressionStmt(DotExpr(
                obj=IdentifierExpr("self"),
                slot="x",
                args=(IdentifierExpr("val"),),
            )),
        )
        class_stmt = _make_class("Box", fields=("x",), methods=[init_method])
        new_stmt = ExpressionStmt(NewExpr(class_name="Box", args=(LiteralExpr(42.0),)))
        program = Program((class_stmt, new_stmt))
        result = execute(program)
        assert isinstance(result, ClassInstance)
        assert result.fields["x"] == 42.0

    def test_call_method_via_dot_expr(self):
        """(. obj speak) → 메서드 실행 후 반환값."""
        get_method = _make_method(
            "getValue", (),
            ReturnStmt(value=LiteralExpr(99.0)),
        )
        class_stmt = _make_class("MyClass", methods=[get_method])
        var_stmt = VarStmt(name="obj", initializer=NewExpr(class_name="MyClass", args=()))
        call_stmt = ExpressionStmt(
            DotExpr(obj=IdentifierExpr("obj"), slot="getValue", args=())
        )
        program = Program((class_stmt, var_stmt, call_stmt))
        result = execute(program)
        assert result == 99.0

    def test_read_field_via_dot_expr(self):
        """(. obj x) → 필드 값 읽기."""
        set_method = _make_method(
            "init", ("v",),
            ExpressionStmt(DotExpr(
                obj=IdentifierExpr("self"),
                slot="x",
                args=(IdentifierExpr("v"),),
            )),
        )
        class_stmt = _make_class("P", fields=("x",), methods=[set_method])
        var_stmt = VarStmt(name="p", initializer=NewExpr(class_name="P", args=(LiteralExpr(7.0),)))
        read_stmt = ExpressionStmt(
            DotExpr(obj=IdentifierExpr("p"), slot="x", args=())
        )
        program = Program((class_stmt, var_stmt, read_stmt))
        result = execute(program)
        assert result == 7.0

    def test_write_field_via_dot_expr(self):
        """(. obj x 100) → 필드 쓰기 후 값 반환."""
        class_stmt = _make_class("Box", fields=("x",))
        var_stmt = VarStmt(name="b", initializer=NewExpr(class_name="Box", args=()))
        write_stmt = ExpressionStmt(
            DotExpr(obj=IdentifierExpr("b"), slot="x", args=(LiteralExpr(100.0),))
        )
        program = Program((class_stmt, var_stmt, write_stmt))
        result = execute(program)
        assert result == 100.0

    def test_dot_expr_on_non_instance_raises(self):
        """인스턴스가 아닌 값에 dot_expr 적용 → ExecuteError."""
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(42.0)),
            ExpressionStmt(DotExpr(obj=IdentifierExpr("x"), slot="foo", args=())),
        ))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_new_expr_non_class_raises(self):
        """NewExpr에 클래스가 아닌 값 → ExecuteError."""
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(42.0)),
            ExpressionStmt(NewExpr(class_name="x", args=())),
        ))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_create_instance_args_without_init_raises(self):
        """init 없는 클래스에 인수 전달 → ExecuteError."""
        class_stmt = _make_class("Empty")
        new_stmt = ExpressionStmt(NewExpr(class_name="Empty", args=(LiteralExpr(1.0),)))
        program = Program((class_stmt, new_stmt))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_read_undefined_field_raises(self):
        """없는 필드 읽기 → ExecuteError."""
        class_stmt = _make_class("X", fields=())
        var_stmt = VarStmt(name="obj", initializer=NewExpr(class_name="X", args=()))
        read_stmt = ExpressionStmt(
            DotExpr(obj=IdentifierExpr("obj"), slot="noSuchField", args=())
        )
        program = Program((class_stmt, var_stmt, read_stmt))
        with pytest.raises(ExecuteError):
            execute(program)


class TestInstanceOf:

    def test_instanceof_same_class(self):
        """instanceof: 같은 클래스 → True."""
        class_stmt = _make_class("Dog")
        var_stmt = VarStmt(name="d", initializer=NewExpr(class_name="Dog", args=()))
        check_stmt = ExpressionStmt(ListExpr((
            IdentifierExpr("instanceof"),
            IdentifierExpr("d"),
            IdentifierExpr("Dog"),
        )))
        program = Program((class_stmt, var_stmt, check_stmt))
        result = execute(program)
        assert result is True

    def test_instanceof_different_class(self):
        """instanceof: 다른 클래스 → False."""
        dog_stmt = _make_class("Dog")
        cat_stmt = _make_class("Cat")
        var_stmt = VarStmt(name="d", initializer=NewExpr(class_name="Dog", args=()))
        check_stmt = ExpressionStmt(ListExpr((
            IdentifierExpr("instanceof"),
            IdentifierExpr("d"),
            IdentifierExpr("Cat"),
        )))
        program = Program((dog_stmt, cat_stmt, var_stmt, check_stmt))
        result = execute(program)
        assert result is False

    def test_instanceof_parent_class(self):
        """instanceof: 부모 클래스 → True."""
        animal_stmt = _make_class("Animal")
        dog_stmt = _make_class("Dog", parent="Animal")
        var_stmt = VarStmt(name="d", initializer=NewExpr(class_name="Dog", args=()))
        check_stmt = ExpressionStmt(ListExpr((
            IdentifierExpr("instanceof"),
            IdentifierExpr("d"),
            IdentifierExpr("Animal"),
        )))
        program = Program((animal_stmt, dog_stmt, var_stmt, check_stmt))
        result = execute(program)
        assert result is True

    def test_instanceof_non_instance(self):
        """instanceof: 인스턴스가 아닌 값 → False."""
        class_stmt = _make_class("Dog")
        var_stmt = VarStmt(name="x", initializer=LiteralExpr(5.0))
        check_stmt = ExpressionStmt(ListExpr((
            IdentifierExpr("instanceof"),
            IdentifierExpr("x"),
            IdentifierExpr("Dog"),
        )))
        program = Program((class_stmt, var_stmt, check_stmt))
        result = execute(program)
        assert result is False

    def test_instanceof_non_class_second_arg_raises(self):
        """instanceof 두 번째 인수가 클래스가 아니면 ExecuteError."""
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(1.0)),
            VarStmt(name="y", initializer=LiteralExpr(2.0)),
            ExpressionStmt(ListExpr((
                IdentifierExpr("instanceof"),
                IdentifierExpr("x"),
                IdentifierExpr("y"),
            ))),
        ))
        with pytest.raises(ExecuteError):
            execute(program)


class TestSuperExpr:

    def test_super_calls_parent_method(self):
        """super.method는 부모 클래스 메서드를 호출한다."""
        parent_method = _make_method(
            "greet", (),
            ReturnStmt(value=LiteralExpr("hello from Animal")),
        )
        animal_stmt = _make_class("Animal", methods=[parent_method])

        dog_method = _make_method(
            "greet", (),
            ReturnStmt(value=SuperExpr(method="greet", args=())),
        )
        dog_stmt = _make_class("Dog", parent="Animal", methods=[dog_method])

        var_stmt = VarStmt(name="d", initializer=NewExpr(class_name="Dog", args=()))
        call_stmt = ExpressionStmt(
            DotExpr(obj=IdentifierExpr("d"), slot="greet", args=())
        )
        program = Program((animal_stmt, dog_stmt, var_stmt, call_stmt))
        result = execute(program)
        assert result == "hello from Animal"

    def test_super_outside_method_raises(self):
        """super를 메서드 외부에서 사용하면 ExecuteError."""
        program = Program((
            ExpressionStmt(SuperExpr(method="greet", args=())),
        ))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_super_no_parent_raises(self):
        """부모 없는 클래스에서 super 사용 → ExecuteError."""
        method = _make_method(
            "test", (),
            ReturnStmt(value=SuperExpr(method="test", args=())),
        )
        class_stmt = _make_class("Lone", methods=[method])
        var_stmt = VarStmt(name="obj", initializer=NewExpr(class_name="Lone", args=()))
        call_stmt = ExpressionStmt(
            DotExpr(obj=IdentifierExpr("obj"), slot="test", args=())
        )
        program = Program((class_stmt, var_stmt, call_stmt))
        with pytest.raises(ExecuteError):
            execute(program)


# ============================================================
# 배열 실행 테스트
# ============================================================

class TestArrayExecution:

    def test_array_expr_creates_list(self):
        """ArrayExpr(size=3) → [None, None, None]."""
        program = Program((ExpressionStmt(ArrayExpr(size=LiteralExpr(3.0))),))
        result = execute(program)
        assert isinstance(result, list)
        assert result == [None, None, None]

    def test_array_expr_float_size(self):
        """부동소수 크기는 정수로 잘린다."""
        program = Program((ExpressionStmt(ArrayExpr(size=LiteralExpr(2.9))),))
        result = execute(program)
        assert result == [None, None]

    def test_array_expr_zero_size(self):
        """크기 0 → 빈 리스트."""
        program = Program((ExpressionStmt(ArrayExpr(size=LiteralExpr(0.0))),))
        result = execute(program)
        assert result == []

    def test_array_expr_negative_size_raises(self):
        """음수 크기 → ExecuteError."""
        program = Program((ExpressionStmt(ArrayExpr(size=LiteralExpr(-1.0))),))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_array_expr_non_number_size_raises(self):
        """문자열 크기 → ExecuteError."""
        program = Program((ExpressionStmt(ArrayExpr(size=LiteralExpr("abc"))),))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_array_index_expr_read(self):
        """ArrayIndexExpr로 배열 요소를 읽는다."""
        arr_var = VarStmt(name="arr", initializer=ArrayExpr(size=LiteralExpr(3.0)))
        read_stmt = ExpressionStmt(
            ArrayIndexExpr(array=IdentifierExpr("arr"), index=LiteralExpr(0.0))
        )
        program = Program((arr_var, read_stmt))
        result = execute(program)
        assert result is None

    def test_array_index_expr_out_of_bounds_raises(self):
        """범위 밖 인덱스 → ExecuteError."""
        arr_var = VarStmt(name="arr", initializer=ArrayExpr(size=LiteralExpr(3.0)))
        read_stmt = ExpressionStmt(
            ArrayIndexExpr(array=IdentifierExpr("arr"), index=LiteralExpr(10.0))
        )
        program = Program((arr_var, read_stmt))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_array_index_expr_non_array_raises(self):
        """비배열에 인덱스 접근 → ExecuteError."""
        program = Program((
            VarStmt(name="x", initializer=LiteralExpr(42.0)),
            ExpressionStmt(
                ArrayIndexExpr(array=IdentifierExpr("x"), index=LiteralExpr(0.0))
            ),
        ))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_array_op_Array_creates_list(self):
        """(Array 4) → [None]*4."""
        program = Program((
            ExpressionStmt(ListExpr((
                IdentifierExpr("Array"), LiteralExpr(4.0)
            ))),
        ))
        result = execute(program)
        assert result == [None, None, None, None]

    def test_array_op_index_reads(self):
        """(index arr 1) → arr[1]."""
        arr_var = VarStmt(name="arr", initializer=ArrayExpr(size=LiteralExpr(3.0)))
        set_idx = ExpressionStmt(ListExpr((
            IdentifierExpr("set-index!"),
            IdentifierExpr("arr"),
            LiteralExpr(1.0),
            LiteralExpr(55.0),
        )))
        read = ExpressionStmt(ListExpr((
            IdentifierExpr("index"),
            IdentifierExpr("arr"),
            LiteralExpr(1.0),
        )))
        program = Program((arr_var, set_idx, read))
        result = execute(program)
        assert result == 55.0

    def test_array_op_set_index(self):
        """(set-index! arr 2 99) → arr[2] == 99."""
        arr_var = VarStmt(name="arr", initializer=ArrayExpr(size=LiteralExpr(3.0)))
        set_stmt = ExpressionStmt(ListExpr((
            IdentifierExpr("set-index!"),
            IdentifierExpr("arr"),
            LiteralExpr(2.0),
            LiteralExpr(99.0),
        )))
        read_stmt = ExpressionStmt(ListExpr((
            IdentifierExpr("index"),
            IdentifierExpr("arr"),
            LiteralExpr(2.0),
        )))
        program = Program((arr_var, set_stmt, read_stmt))
        result = execute(program)
        assert result == 99.0

    def test_array_op_Array_wrong_args_raises(self):
        """(Array 1 2) → ExecuteError: wrong arg count."""
        program = Program((
            ExpressionStmt(ListExpr((
                IdentifierExpr("Array"), LiteralExpr(1.0), LiteralExpr(2.0)
            ))),
        ))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_array_op_index_wrong_args_raises(self):
        """(index arr) → ExecuteError: wrong arg count."""
        arr_var = VarStmt(name="arr", initializer=ArrayExpr(size=LiteralExpr(3.0)))
        program = Program((
            arr_var,
            ExpressionStmt(ListExpr((
                IdentifierExpr("index"), IdentifierExpr("arr")
            ))),
        ))
        with pytest.raises(ExecuteError):
            execute(program)

    def test_array_op_set_index_wrong_args_raises(self):
        """(set-index! arr 0) → ExecuteError: wrong arg count."""
        arr_var = VarStmt(name="arr", initializer=ArrayExpr(size=LiteralExpr(3.0)))
        program = Program((
            arr_var,
            ExpressionStmt(ListExpr((
                IdentifierExpr("set-index!"), IdentifierExpr("arr"), LiteralExpr(0.0)
            ))),
        ))
        with pytest.raises(ExecuteError):
            execute(program)
