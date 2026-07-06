import pytest

from common import (
    AssembleError,
    ExpressionStmt,
    IdentifierExpr,
    ListExpr,
    LiteralExpr,
    Token,
    TokenType,
)
from Assembler import assemble


def _token(token_type, lexeme, literal=None):
    return Token(token_type, lexeme, literal)


def _plus_expr_tokens():
    return [
        _token(TokenType.LEFT_PAREN, "("),
        _token(TokenType.IDENTIFIER, "+"),
        _token(TokenType.NUMBER, "1", 1.0),
        _token(TokenType.NUMBER, "2", 2.0),
        _token(TokenType.RIGHT_PAREN, ")"),
        _token(TokenType.EOF, ""),
    ]


def test_assemble_single_literal():
    tokens = [_token(TokenType.NUMBER, "42", 42.0), _token(TokenType.EOF, "")]
    program = assemble(tokens)
    assert len(program.statements) == 1
    stmt = program.statements[0]
    assert isinstance(stmt, ExpressionStmt)
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value == 42.0


def test_assemble_list_expression():
    program = assemble(_plus_expr_tokens())
    stmt = program.statements[0]
    assert isinstance(stmt, ExpressionStmt)
    expr = stmt.expression
    assert isinstance(expr, ListExpr)
    head, first_arg, second_arg = expr.elements
    assert isinstance(head, IdentifierExpr) and head.name == "+"
    assert isinstance(first_arg, LiteralExpr) and first_arg.value == 1.0
    assert isinstance(second_arg, LiteralExpr) and second_arg.value == 2.0


def test_assemble_nested_list_expression():
    tokens = [
        _token(TokenType.LEFT_PAREN, "("),
        _token(TokenType.IDENTIFIER, "+"),
        _token(TokenType.NUMBER, "1", 1.0),
        _token(TokenType.LEFT_PAREN, "("),
        _token(TokenType.IDENTIFIER, "*"),
        _token(TokenType.NUMBER, "2", 2.0),
        _token(TokenType.NUMBER, "3", 3.0),
        _token(TokenType.RIGHT_PAREN, ")"),
        _token(TokenType.RIGHT_PAREN, ")"),
        _token(TokenType.EOF, ""),
    ]
    program = assemble(tokens)
    outer = program.statements[0].expression
    assert isinstance(outer, ListExpr)
    head, first_arg, inner = outer.elements
    assert isinstance(head, IdentifierExpr) and head.name == "+"
    assert isinstance(first_arg, LiteralExpr) and first_arg.value == 1.0
    assert isinstance(inner, ListExpr)
    inner_head, inner_a, inner_b = inner.elements
    assert isinstance(inner_head, IdentifierExpr) and inner_head.name == "*"
    assert inner_a.value == 2.0
    assert inner_b.value == 3.0


def test_assemble_missing_closing_paren_raises():
    tokens = [
        _token(TokenType.LEFT_PAREN, "("),
        _token(TokenType.IDENTIFIER, "+"),
        _token(TokenType.NUMBER, "1", 1.0),
        _token(TokenType.EOF, ""),
    ]
    with pytest.raises(AssembleError):
        assemble(tokens)


def test_assemble_unexpected_closing_paren_raises():
    tokens = [_token(TokenType.RIGHT_PAREN, ")"), _token(TokenType.EOF, "")]
    with pytest.raises(AssembleError):
        assemble(tokens)
