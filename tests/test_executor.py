from common import ExpressionStmt, IdentifierExpr, ListExpr, LiteralExpr, Program
from Executor import execute


def test_execute_single_literal():
    program = Program((ExpressionStmt(LiteralExpr(42.0)),))
    assert execute(program) == 42.0


def test_execute_simple_addition():
    program = Program(
        (
            ExpressionStmt(
                ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), LiteralExpr(2.0)))
            ),
        )
    )
    assert execute(program) == 3.0


def test_execute_nested_arithmetic():
    inner = ListExpr((IdentifierExpr("*"), LiteralExpr(2.0), LiteralExpr(3.0)))
    program = Program(
        (ExpressionStmt(ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), inner))),)
    )
    assert execute(program) == 7.0
