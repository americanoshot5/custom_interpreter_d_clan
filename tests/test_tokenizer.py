import pytest

from common import TokenType, TokenizeError
from Tokenizer import SExpressionTokenizer


def test_tokenize_simple_expression():
    src = SExpressionTokenizer("(+ 1 2)")
    tokens = src.tokenize()
    types = [t.type for t in tokens]


    assert types == [
        TokenType.LEFT_PAREN,
        TokenType.PLUS,
        TokenType.NUMBER,
        TokenType.NUMBER,
        TokenType.RIGHT_PAREN,
        TokenType.EOF,
    ]
    assert tokens[2].literal == 1.0
    assert tokens[3].literal == 2.0


def test_tokenize_string_literal():
    src = SExpressionTokenizer('(print "hi")')
    tokens = src.tokenize()
    string_token = tokens[2]
    assert string_token.type == TokenType.STRING
    assert string_token.literal == "hi"


def test_tokenize_boolean_keywords():
    src = SExpressionTokenizer("true false")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.TRUE
    assert tokens[0].literal is True
    assert tokens[1].type == TokenType.FALSE
    assert tokens[1].literal is False


def test_tokenize_invalid_character_raises():
    src = SExpressionTokenizer("@")
    with pytest.raises(TokenizeError):
        src.tokenize()
