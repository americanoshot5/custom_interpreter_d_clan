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

def test_tokenize_pdf_example_test1():
    src = SExpressionTokenizer("age = 37")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].literal == "age"
    assert tokens[1].type == TokenType.EQUAL
    assert tokens[1].literal == "="
    assert tokens[2].type == TokenType.NUMBER
    assert tokens[2].literal == 37.0
    assert tokens[3].type == TokenType.EOF
    assert tokens[3].literal == ""

def test_tokenize_pdf_example_test2():
    src = SExpressionTokenizer("if ( x > 10 )")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.IF
    assert tokens[0].literal == "if"
    assert tokens[1].type == TokenType.LEFT_PAREN
    assert tokens[1].literal == "("
    assert tokens[2].type == TokenType.IDENTIFIER
    assert tokens[2].literal == "x"
    assert tokens[3].type == TokenType.GREATER
    assert tokens[3].literal == ">"
    assert tokens[4].type == TokenType.NUMBER
    assert tokens[4].literal == 10
    assert tokens[5].type == TokenType.RIGHT_PAREN
    assert tokens[5].literal == ")"
    assert tokens[6].type == TokenType.EOF
    assert tokens[6].literal == ""

def test_tokenize_pdf_example_test3():
    src = SExpressionTokenizer("a + b * 3")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].literal == "a"
    assert tokens[1].type == TokenType.PLUS
    assert tokens[1].literal == "+"
    assert tokens[2].type == TokenType.IDENTIFIER
    assert tokens[2].literal == "b"
    assert tokens[3].type == TokenType.STAR
    assert tokens[3].literal == "*"
    assert tokens[4].type == TokenType.NUMBER
    assert tokens[4].literal == 3.0
    assert tokens[5].type == TokenType.EOF
    assert tokens[5].literal == ""

