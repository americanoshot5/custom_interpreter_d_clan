import pytest
from common import *
from Executor import *


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
