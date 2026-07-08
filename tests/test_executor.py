import pytest
from common import *
from Executor import *
from Executor import Function


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
