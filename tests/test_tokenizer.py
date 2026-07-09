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


def test_tokenize_tracks_line_and_column_locations():
    src = SExpressionTokenizer("\n(print 1)\n  (print 2)")
    tokens = src.tokenize()

    assert tokens[0].lexeme == "("
    assert tokens[0].location.line == 2
    assert tokens[0].location.column == 1
    assert tokens[4].lexeme == "("
    assert tokens[4].location.line == 3
    assert tokens[4].location.column == 3


def test_tokenize_boolean_keywords():
    src = SExpressionTokenizer("true false")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.TRUE
    assert tokens[0].literal is True
    assert tokens[1].type == TokenType.FALSE
    assert tokens[1].literal is False


def test_tokenize_null_keyword():
    src = SExpressionTokenizer("null")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.NULL
    assert tokens[0].literal is None


def test_tokenize_null_keyword_is_case_insensitive():
    src = SExpressionTokenizer("Null NULL")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.NULL
    assert tokens[0].literal is None
    assert tokens[1].type == TokenType.NULL
    assert tokens[1].literal is None


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

def test_tokenize_empty():
    src = SExpressionTokenizer("")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.EOF
    assert tokens[0].literal == ""

def test_tokenize_a_a_plus_1():
    src = SExpressionTokenizer("a = a + 1")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].literal == "a"

def test_tokenize_paren_brace():
    src = SExpressionTokenizer("if ( a > 5 ) { print 3 + 2 }")
    tokens = src.tokenize()
    assert tokens[1].type == TokenType.LEFT_PAREN
    assert tokens[5].type == TokenType.RIGHT_PAREN
    assert tokens[6].type == TokenType.LEFT_BRACE
    assert tokens[11].type == TokenType.RIGHT_BRACE

def test_tokenize_invalid_lparenidentifier():
    src = SExpressionTokenizer("if (a > 5 ) { print 3 + 2 }")
    tokens = src.tokenize()
    assert tokens[1].type == TokenType.LEFT_PAREN
    assert tokens[5].type == TokenType.RIGHT_PAREN
    assert tokens[6].type == TokenType.LEFT_BRACE
    assert tokens[11].type == TokenType.RIGHT_BRACE

def test_tokenize_invalid_rparenidentifier():
    src = SExpressionTokenizer("if ( a > 5) { print 3 + 2 }")
    tokens = src.tokenize()
    assert tokens[1].type == TokenType.LEFT_PAREN
    assert tokens[5].type == TokenType.RIGHT_PAREN
    assert tokens[6].type == TokenType.LEFT_BRACE
    assert tokens[11].type == TokenType.RIGHT_BRACE


def test_tokenize_invalid_lbraceidentifier():
    src = SExpressionTokenizer("if ( a > 5 ) {print 3 + 2 }")
    tokens = src.tokenize()
    assert tokens[1].type == TokenType.LEFT_PAREN
    assert tokens[5].type == TokenType.RIGHT_PAREN
    assert tokens[6].type == TokenType.LEFT_BRACE
    assert tokens[11].type == TokenType.RIGHT_BRACE


def test_tokenize_invalid_rbraceidentifier():
    src = SExpressionTokenizer("if ( a > 5 ) { print 3 + 2}")
    tokens = src.tokenize()
    assert tokens[1].type == TokenType.LEFT_PAREN
    assert tokens[5].type == TokenType.RIGHT_PAREN
    assert tokens[6].type == TokenType.LEFT_BRACE
    assert tokens[11].type == TokenType.RIGHT_BRACE

def test_tokenize_var_assign():
    src = SExpressionTokenizer("var a 10")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.VAR
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[2].type == TokenType.NUMBER

def test_tokenize_floating_point():
    src = SExpressionTokenizer("(print 3.14)")
    tokens = src.tokenize()
    assert tokens[1].type == TokenType.PRINT
    assert tokens[2].type == TokenType.NUMBER
    assert tokens[2].literal == 3.14
    assert tokens[3].type == TokenType.RIGHT_PAREN

def test_tokenize_1item_operation():
    src = SExpressionTokenizer("-5")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].literal == -5.0

def test_tokenize_1item_operation_w_split():
    src = SExpressionTokenizer("- 5")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.MINUS
    assert tokens[1].type == TokenType.NUMBER
    assert tokens[1].literal == 5.0

def test_tokenize_Not_operation():
    src = SExpressionTokenizer("~ True")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.NOT
    assert tokens[1].type == TokenType.TRUE

def test_tokenize_Null_operation():
    src = SExpressionTokenizer("Null")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.NULL

def test_tokenize_Dot_operation():
    src = SExpressionTokenizer("Null.Null")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.DOTIDENTIFIER
    assert tokens[0].literal == "Null.Null"


# ============================================================
# func / return 키워드 토크나이징
# ============================================================

def test_tokenize_func_keyword():
    src = SExpressionTokenizer("func")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.FUNC
    assert tokens[0].lexeme == "func"


def test_tokenize_return_keyword():
    src = SExpressionTokenizer("return")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.RETURN
    assert tokens[0].lexeme == "return"


def test_tokenize_func_keyword_case_insensitive():
    src = SExpressionTokenizer("FUNC")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.FUNC


def test_tokenize_func_in_expression():
    src = SExpressionTokenizer("(func add (a b) (print a))")
    tokens = src.tokenize()
    types = [t.type for t in tokens]
    assert TokenType.FUNC in types
    assert types[1] == TokenType.FUNC


def test_tokenize_return_in_expression():
    src = SExpressionTokenizer("(return 42)")
    tokens = src.tokenize()
    assert tokens[1].type == TokenType.RETURN


def test_tokenize_return_no_value():
    src = SExpressionTokenizer("(return)")
    tokens = src.tokenize()
    assert tokens[0].type == TokenType.LEFT_PAREN
    assert tokens[1].type == TokenType.RETURN
    assert tokens[2].type == TokenType.RIGHT_PAREN
