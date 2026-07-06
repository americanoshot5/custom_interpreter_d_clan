from dataclasses import dataclass

import pytest

from common import (
    CheckError,
    ExpressionStmt,
    IdentifierExpr,
    ListExpr,
    LiteralExpr,
    Program,
    Stmt,
)
from Checker import check


@dataclass(frozen=True, slots=True, kw_only=True)
class _DummyStmt(Stmt):
    pass


def test_check_valid_expression_statement_does_not_raise():
    program = Program((ExpressionStmt(LiteralExpr(42.0)),))
    check(program)


def test_check_nested_list_expression_does_not_raise():
    program = Program(
        (
            ExpressionStmt(
                ListExpr(
                    (
                        IdentifierExpr("+"),
                        LiteralExpr(1.0),
                        ListExpr((LiteralExpr(2.0),)),
                    )
                )
            ),
        )
    )
    check(program)


def test_check_unsupported_statement_raises():
    program = Program((_DummyStmt(),))
    with pytest.raises(CheckError):
        check(program)
