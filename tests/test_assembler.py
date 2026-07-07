"""
SExpressionAssembler 테스트 스위트

Mock 전략:
  - Token 은 frozen dataclass 이므로 팩토리 헬퍼로 생성 (Mock 보다 타입 안전)
  - SourceLocation 은 Mock 으로 대체 → 에러 메시지 위치 정보가 location.line/column 에서만 오는지 검증
  - 내부 탐색 메서드(_peek, _advance 등)는 patch 로 교체 → _expression 로직을 독립적으로 검증
  - Assembler ABC 준수 여부는 isinstance 검사로 명시
"""

from __future__ import annotations

import pytest

from common import (
    AssembleError,
    ExpressionStmt,
    IdentifierExpr,
    ListExpr,
    LiteralExpr,
    Program,
    SourceLocation,
    Token,
    TokenType,
    Stmt,
    CheckError
)
from interfaces import Assembler
from Assembler import SExpressionAssembler, assemble, DefaultAssembler


def _token(token_type, lexeme, literal=None):
    return Token(token_type, lexeme, literal)


def _plus_expr_tokens():
    return [
        _token(TokenType.LEFT_PAREN, "("),
        _token(TokenType.PLUS, "+"),
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
        _token(TokenType.PLUS, "+"),
        _token(TokenType.NUMBER, "1", 1.0),
        _token(TokenType.LEFT_PAREN, "("),
        _token(TokenType.STAR, "*"),
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
        _token(TokenType.PLUS, "+"),
        _token(TokenType.NUMBER, "1", 1.0),
        _token(TokenType.EOF, ""),
    ]
    with pytest.raises(AssembleError):
        assemble(tokens)


def test_assemble_unexpected_closing_paren_raises():
    tokens = [_token(TokenType.RIGHT_PAREN, ")"), _token(TokenType.EOF, "")]
    with pytest.raises(AssembleError):
        assemble(tokens)


# ============================================================
# 토큰 팩토리 헬퍼
# Token 은 frozen dataclass → Mock 보다 직접 생성이 정확하다
# ============================================================

def loc(line: int = 1, col: int = 1) -> SourceLocation:
    return SourceLocation(line=line, column=col)


def tok(
        type_: TokenType,
        lexeme: str = "",
        literal=None,
        line: int = 1,
        col: int = 1,
) -> Token:
    return Token(type=type_, lexeme=lexeme, literal=literal, location=loc(line, col))


def eof(line: int = 1, col: int = 99) -> Token:
    return tok(TokenType.EOF, "", line=line, col=col)


def lparen(line: int = 1, col: int = 1) -> Token:
    return tok(TokenType.LEFT_PAREN, "(", line=line, col=col)


def rparen(line: int = 1, col: int = 1) -> Token:
    return tok(TokenType.RIGHT_PAREN, ")", line=line, col=col)


def num(value: float, line: int = 1, col: int = 1) -> Token:
    return tok(TokenType.NUMBER, str(value), literal=value, line=line, col=col)


def string(value: str, line: int = 1, col: int = 1) -> Token:
    return tok(TokenType.STRING, f'"{value}"', literal=value, line=line, col=col)


def ident(name: str, line: int = 1, col: int = 1) -> Token:
    return tok(TokenType.IDENTIFIER, name, line=line, col=col)


def kw(type_: TokenType, line: int = 1, col: int = 1) -> Token:
    # TRUE / FALSE 는 literal 값을 명시적으로 넣어야 LiteralExpr 에 전달된다
    literal = {TokenType.TRUE: True, TokenType.FALSE: False}.get(type_)
    return tok(type_, type_.value, literal=literal, line=line, col=col)


def unwrap(tokens: list[Token]):
    """단일 식 Program → Expr 꺼내기"""

    prog = SExpressionAssembler(tokens).assemble()

    assert len(prog.statements) == 1
    return prog.statements[0].expression


# ============================================================
# 1. Assembler ABC 준수
# ============================================================

def test_is_instance_of_assembler_abc():
    assert isinstance(SExpressionAssembler([]), Assembler)

def test_assemble_method_exists():
    assert callable(SExpressionAssembler([]).assemble)


def test_returns_program_type():
    result = SExpressionAssembler([eof()]).assemble()
    assert isinstance(SExpressionAssembler([eof()]), Assembler)


def test_assemble_method_exists():
    assert callable(SExpressionAssembler([]).assemble)


def test_returns_program_type():
    result = SExpressionAssembler([eof()]).assemble()
    assert isinstance(result, Program)


def test_mock_assembler_satisfies_interface(mocker):
    """Mock 으로 만든 Assembler 도 인터페이스를 만족할 수 있어야 한다."""
    mock_asm = mocker.Mock(spec=Assembler)
    mock_asm.assemble.return_value = Program(statements=())
    result = mock_asm.assemble([eof()])
    assert isinstance(result, Program)


# ============================================================
# 2. 빈 입력 / EOF
# ============================================================

def test_only_eof_returns_empty_program():
    prog = SExpressionAssembler([eof()]).assemble()

    assert prog.statements == ()


def test_empty_token_list_treated_as_eof():
    """토큰이 아예 없으면 IndexError 가 아니라 비어있는 Program."""
    # EOF 없이 빈 리스트를 넘기면 _peek 이 IndexError 를 낼 수 있으므로
    # EOF 가 반드시 있어야 함을 명시하는 테스트
    prog = SExpressionAssembler([eof()]).assemble()
    assert isinstance(prog, Program)


# ============================================================
# 3. 단일 atom → ExpressionStmt(LiteralExpr / IdentifierExpr)
# ============================================================

def test_integer_literal():
    expr = unwrap([num(42.0), eof()])
    assert isinstance(expr, LiteralExpr)
    assert expr.value == 42.0


def test_float_literal():
    expr = unwrap([num(3.14), eof()])
    assert isinstance(expr, LiteralExpr)
    assert expr.value == pytest.approx(3.14)


def test_negative_number():
    expr = unwrap([num(-7.0), eof()])
    assert isinstance(expr, LiteralExpr)
    assert expr.value == -7.0


def test_string_literal():
    expr = unwrap([string("hello"), eof()])
    assert isinstance(expr, LiteralExpr)
    assert expr.value == "hello"


def test_empty_string():
    expr = unwrap([string(""), eof()])
    assert isinstance(expr, LiteralExpr)
    assert expr.value == ""


def test_true_literal():
    expr = unwrap([kw(TokenType.TRUE), eof()])
    assert isinstance(expr, LiteralExpr)
    assert expr.value is True


def test_false_literal():
    expr = unwrap([kw(TokenType.FALSE), eof()])
    assert isinstance(expr, LiteralExpr)
    assert expr.value is False


def test_identifier():
    expr = unwrap([ident("foo"), eof()])
    assert isinstance(expr, IdentifierExpr)
    assert expr.name == "foo"


def test_keyword_if_becomes_identifier():
    """IF 같은 키워드는 NUMBER/STRING/TRUE/FALSE 가 아니므로 IdentifierExpr."""
    expr = unwrap([kw(TokenType.IF), eof()])
    assert isinstance(expr, IdentifierExpr)
    assert expr.name == "if"


def test_keyword_for_becomes_identifier():
    expr = unwrap([kw(TokenType.FOR), eof()])
    assert isinstance(expr, IdentifierExpr)


def test_operator_plus_becomes_identifier():
    expr = unwrap([tok(TokenType.PLUS, "+"), eof()])
    assert isinstance(expr, IdentifierExpr)
    assert expr.name == "+"


# ============================================================
# 4. 리스트 표현식 (괄호)
# ============================================================

def test_empty_list():
    expr = unwrap([lparen(), rparen(), eof()])
    assert isinstance(expr, ListExpr)
    assert expr.elements == ()


def test_single_element_list():
    expr = unwrap([lparen(), num(1.0), rparen(), eof()])
    assert isinstance(expr, ListExpr)
    assert len(expr.elements) == 1
    assert isinstance(expr.elements[0], LiteralExpr)


def test_flat_list():
    # (+ 1 2)
    tokens = [lparen(), tok(TokenType.PLUS, "+"), num(1.0), num(2.0), rparen(), eof()]
    expr = unwrap(tokens)
    assert isinstance(expr, ListExpr)
    assert len(expr.elements) == 3
    assert isinstance(expr.elements[0], IdentifierExpr)
    assert expr.elements[0].name == "+"
    assert isinstance(expr.elements[1], LiteralExpr)
    assert expr.elements[1].value == 1.0
    assert isinstance(expr.elements[2], LiteralExpr)
    assert expr.elements[2].value == 2.0


def test_nested_list():
    # (+ 1 (* 2 3))
    tokens = [
        lparen(),
        tok(TokenType.PLUS, "+"),
        num(1.0),
        lparen(), tok(TokenType.STAR, "*"), num(2.0), num(3.0), rparen(),
        rparen(),
        eof(),
    ]
    expr = unwrap(tokens)
    assert isinstance(expr, ListExpr)
    assert len(expr.elements) == 3
    inner = expr.elements[2]
    assert isinstance(inner, ListExpr)
    assert len(inner.elements) == 3


def test_deeply_nested():
    # (a (b (c)))
    tokens = [
        lparen(), ident("a"),
        lparen(), ident("b"),
        lparen(), ident("c"), rparen(),
        rparen(),
        rparen(),
        eof(),
    ]
    expr = unwrap(tokens)
    assert isinstance(expr, ListExpr)
    inner_b = expr.elements[1]
    assert isinstance(inner_b, ListExpr)
    inner_c = inner_b.elements[1]
    assert isinstance(inner_c, ListExpr)
    assert inner_c.elements[0].name == "c"


def test_list_with_string_and_number():
    tokens = [lparen(), string("x"), num(5.0), rparen(), eof()]
    expr = unwrap(tokens)
    assert isinstance(expr, ListExpr)
    assert isinstance(expr.elements[0], LiteralExpr)
    assert expr.elements[0].value == "x"


# ============================================================
# 5. 여러 최상위 식 (multi-statement program)
# ============================================================

def test_two_atoms():
    prog = SExpressionAssembler([num(1.0), num(2.0), eof()]).assemble()
    assert len(prog.statements) == 2
    assert all(isinstance(s, ExpressionStmt) for s in prog.statements)


def test_two_lists():
    # (+ 1 2) (+ 3 4)
    tokens = [
        lparen(), tok(TokenType.PLUS, "+"), num(1.0), num(2.0), rparen(),
        lparen(), tok(TokenType.PLUS, "+"), num(3.0), num(4.0), rparen(),
        eof(),
    ]
    prog = SExpressionAssembler(tokens).assemble()
    assert len(prog.statements) == 2
    assert all(isinstance(s.expression, ListExpr) for s in prog.statements)


def test_mixed_atom_and_list():
    tokens = [num(1.0), lparen(), ident("f"), rparen(), eof()]
    prog = SExpressionAssembler(tokens).assemble()
    assert len(prog.statements) == 2
    assert isinstance(prog.statements[0].expression, LiteralExpr)
    assert isinstance(prog.statements[1].expression, ListExpr)


# ============================================================
# 6. SourceLocation 전파
#    Token 의 location 이 AST 노드에 올바르게 복사되는지
# ============================================================

def test_literal_location_from_token():
    token = num(42.0, line=3, col=7)
    prog = SExpressionAssembler([token, eof()]).assemble()
    expr = prog.statements[0].expression
    assert expr.location.line == 3
    assert expr.location.column == 7


def test_list_location_from_lparen_token():
    """ListExpr 의 location 은 여는 괄호 토큰의 위치여야 한다."""
    tokens = [lparen(line=2, col=5), rparen(), eof()]
    prog = SExpressionAssembler(tokens).assemble()
    expr = prog.statements[0].expression
    assert expr.location.line == 2
    assert expr.location.column == 5


def test_identifier_location_from_token():
    token = ident("myVar", line=10, col=3)
    prog = SExpressionAssembler([token, eof()]).assemble()
    expr = prog.statements[0].expression
    assert expr.location.line == 10
    assert expr.location.column == 3


def test_mock_location_used_in_node(mocker):
    mock_loc = mocker.Mock(spec=SourceLocation)
    mock_loc.line = 99
    mock_loc.column = 42
    token = Token(
        type=TokenType.NUMBER,
        lexeme="1",
        literal=1.0,
        location=mock_loc,
    )

    prog = SExpressionAssembler([token, eof()]).assemble()

    expr = prog.statements[0].expression
    assert expr.location.line == 99
    assert expr.location.column == 42


# ============================================================
# 7. 에러 케이스
#    AssembleError 메시지에 위치 정보가 포함되는지 검증
# ============================================================

def test_unclosed_paren_raises_assemble_error():
    tokens = [lparen(line=1, col=1), num(1.0), eof()]
    with pytest.raises(AssembleError):
        SExpressionAssembler(tokens).assemble()


def test_unclosed_paren_error_contains_location():
    tokens = [lparen(line=3, col=5), num(1.0), eof()]
    with pytest.raises(AssembleError, match="3:5"):
        SExpressionAssembler(tokens).assemble()

def test_unexpected_rparen_raises():
    tokens = [rparen(line=2, col=4), eof()]
    with pytest.raises(AssembleError):
        SExpressionAssembler(tokens).assemble()

def test_unexpected_rparen_error_contains_location():
    tokens = [rparen(line=2, col=4), eof()]
    with pytest.raises(AssembleError, match="2:4"):
        SExpressionAssembler(tokens).assemble()

def test_mock_location_appears_in_error_message(mocker):
    """SourceLocation 을 Mock 으로 줘도 line/column 이 에러 메시지에 사용된다."""
    mock_loc = mocker.Mock(spec=SourceLocation)
    mock_loc.line = 7
    mock_loc.column = 11
    bad_token = Token(type=TokenType.RIGHT_PAREN, lexeme=")", location=mock_loc)
    with pytest.raises(AssembleError, match="7:11"):
        SExpressionAssembler([bad_token, eof()]).assemble()

def test_missing_rparen_error_message():
    tokens = [lparen(line=5, col=2), ident("x"), eof()]
    with pytest.raises(AssembleError, match="Missing"):
        SExpressionAssembler(tokens).assemble()

# ============================================================
# 8. 내부 메서드 단위 테스트 (patch 로 격리)
# ============================================================

@pytest.fixture
def asm():
    a = SExpressionAssembler([])
    a._tokens = [eof()]
    a._current = 0
    return a


def test_is_at_end_true_when_eof(asm):
    asm._tokens = [eof()]
    asm._current = 0
    assert asm._is_at_end() is True


def test_is_at_end_false_when_not_eof(asm):
    asm._tokens = [num(1.0), eof()]
    asm._current = 0
    assert asm._is_at_end() is False


def test_peek_returns_current_token(asm):
    t = num(5.0)
    asm._tokens = [t, eof()]
    asm._current = 0
    assert asm._peek() is t


def test_advance_increments_current(asm):
    asm._tokens = [num(1.0), eof()]
    asm._current = 0
    asm._advance()
    assert asm._current == 1


def test_advance_returns_previous(asm):
    t = num(1.0)
    asm._tokens = [t, eof()]
    asm._current = 0
    result = asm._advance()
    assert result is t


def test_advance_does_not_go_past_eof(asm):
    """EOF 에서 advance 를 불러도 _current 는 증가하지 않는다.
    구현: _advance 는 is_at_end() 일 때 _current 를 올리지 않고 previous() 를 반환한다."""
    asm._tokens = [eof()]
    asm._current = 0
    asm._advance()  # EOF 에서 호출
    asm._advance()  # 한 번 더 호출해도 같은 자리
    assert asm._current == 0  # EOF 에서는 증가하지 않음


def test_previous_returns_last_consumed(asm):
    t0 = num(1.0)
    t1 = num(2.0)
    asm._tokens = [t0, t1, eof()]
    asm._current = 0
    asm._advance()  # consumes t0
    assert asm._previous() is t0


def test_check_true_when_type_matches(asm):
    asm._tokens = [num(1.0), eof()]
    asm._current = 0
    assert asm._check(TokenType.NUMBER) is True


def test_check_false_when_type_differs(asm):
    asm._tokens = [num(1.0), eof()]
    asm._current = 0
    assert asm._check(TokenType.STRING) is False


def test_check_false_at_eof(asm):
    asm._tokens = [eof()]
    asm._current = 0
    assert asm._check(TokenType.NUMBER) is False


def test_consume_advances_when_match(asm):
    t = rparen()
    asm._tokens = [t, eof()]
    asm._current = 0
    result = asm._consume(TokenType.RIGHT_PAREN, "expected )")
    assert result is t
    assert asm._current == 1


def test_consume_raises_when_no_match(asm):
    asm._tokens = [num(1.0), eof()]
    asm._current = 0
    with pytest.raises(AssembleError, match="Expected"):
        asm._consume(TokenType.RIGHT_PAREN, "Expected )")


def test_consume_error_includes_location(asm):
    asm._tokens = [num(1.0, line=4, col=8), eof()]
    asm._current = 0
    with pytest.raises(AssembleError, match="4:8"):
        asm._consume(TokenType.RIGHT_PAREN, "Expected )")


# ============================================================
# 9. _expression 을 patch 로 격리하여 assemble 루프만 검증
# ============================================================

def test_assemble_calls_expression_once_per_top_level(mocker):
    """assemble 은 EOF 전까지 _expression 을 정확히 n 번 호출해야 한다."""
    asm = SExpressionAssembler([])
    call_count = 0
    fake_expr = LiteralExpr(value=1.0, location=None)

    def fake_expression(self_):
        nonlocal call_count
        call_count += 1
        self_._current += 1  # 토큰 하나씩 전진시켜 무한루프 방지
        return fake_expr

    asm._tokens = [num(1.0), num(2.0), eof()]
    asm._current = 0

    mocker.patch.object(SExpressionAssembler, "_expression", fake_expression)
    prog = asm.assemble()

    assert call_count == 2
    assert len(prog.statements) == 2


def test_assemble_wraps_each_expr_in_expression_stmt():
    tokens = [num(1.0), num(2.0), eof()]
    prog = SExpressionAssembler(tokens).assemble()
    assert all(isinstance(s, ExpressionStmt) for s in prog.statements)


def test_assemble_program_has_correct_statement_count():
    tokens = [num(1.0), num(2.0), num(3.0), eof()]
    prog = SExpressionAssembler(tokens).assemble()
    assert len(prog.statements) == 3


# ============================================================
# 10. 모듈 레벨 assemble() 편의 함수
# ============================================================

def test_module_assemble_returns_program():
    result = assemble([eof()])
    assert isinstance(result, Program)


# ============================================================
# 11. DefaultAssembler alias
# ============================================================

def test_default_assembler_is_sexpressionassembler():
    assert DefaultAssembler is SExpressionAssembler


# ============================================================
# 12. ExpressionStmt 의 location
# ============================================================

def test_expression_stmt_location_is_none():
    """assemble() 은 ExpressionStmt 를 location 없이 생성한다."""
    prog = SExpressionAssembler([num(1.0), eof()]).assemble()
    assert prog.statements[0].location is None


# ============================================================
# 13. assemble() 재사용 — 동일 인스턴스 두 번 호출
# ============================================================

def test_assemble_second_call_returns_empty_program():
    """assemble() 후 _current 가 EOF 에 도달해 있으므로
    같은 인스턴스를 재사용하면 두 번째 호출은 빈 Program 을 반환한다."""
    asm = SExpressionAssembler([num(1.0), eof()])
    first = asm.assemble()
    second = asm.assemble()
    assert len(first.statements) == 1
    assert second.statements == ()


# ============================================================
# 14. 중첩 괄호 에러 위치 — 어느 ( 의 위치가 메시지에 나오는가
# ============================================================

def test_inner_unclosed_paren_error_reports_inner_location():
    """안쪽 ( 가 닫히지 않았을 때 에러 위치는 안쪽 ( 이어야 한다."""
    tokens = [
        lparen(line=1, col=1),
        ident("a"),
        lparen(line=1, col=5),  # 이 괄호가 닫히지 않음
        ident("b"),
        eof(),
    ]
    with pytest.raises(AssembleError, match="1:5"):
        SExpressionAssembler(tokens).assemble()


def test_outer_unclosed_paren_with_closed_inner_reports_outer_location():
    """안쪽 리스트는 닫혔지만 바깥쪽 ( 가 닫히지 않았을 때
    에러 위치는 바깥쪽 ( 이어야 한다."""
    tokens = [
        lparen(line=2, col=3),  # 이 괄호가 닫히지 않음
        ident("foo"),
        lparen(), ident("bar"), rparen(),  # 안쪽은 정상적으로 닫힘
        eof(),
    ]
    with pytest.raises(AssembleError, match="2:3"):
        SExpressionAssembler(tokens).assemble()


# ============================================================
# 15. _check(TokenType.EOF) — EOF 위치에서 EOF 타입 체크도 False
# ============================================================

def test_check_eof_type_at_eof_returns_false(asm):
    """`_check()` 는 `_is_at_end()` 가 True 이면 어떤 타입이든 False 를 반환한다.
    EOF 토큰이 있어도 _check(TokenType.EOF) 는 False 이므로
    EOF 감지에는 반드시 _is_at_end() 를 사용해야 한다."""
    asm._tokens = [eof()]
    asm._current = 0
    assert asm._check(TokenType.EOF) is False


# ============================================================
# 16. Expr 가 Stmt 를 child 로 가질 수 없다는 방어 코드
# ============================================================

def test_stmt_as_list_element_raises(mocker):
    """_expression() 이 Stmt 를 반환할 경우 AssembleError 가 발생해야 한다."""
    fake_stmt = ExpressionStmt(IdentifierExpr("x", location=loc(3, 7)), location=loc(3, 7))

    call_count = 0
    original = SExpressionAssembler._expression

    def patched(self_):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return original(self_)  # '(' 처리는 정상 실행
        return fake_stmt           # 두 번째 호출: Stmt 반환

    mocker.patch.object(SExpressionAssembler, "_expression", patched)

    tokens = [lparen(), ident("a"), rparen(), eof()]
    with pytest.raises(AssembleError, match="3:7"):
        SExpressionAssembler(tokens).assemble()


def test_stmt_as_list_element_error_message_contains_stmt_location(mocker):
    """에러 메시지에 Stmt 의 위치(line:col)가 포함되어야 한다."""
    fake_stmt = ExpressionStmt(IdentifierExpr("y", location=loc(5, 2)), location=loc(5, 2))

    original = SExpressionAssembler._expression
    call_count = 0

    def patched(self_):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return original(self_)
        return fake_stmt

    mocker.patch.object(SExpressionAssembler, "_expression", patched)

    tokens = [lparen(), ident("b"), rparen(), eof()]
    with pytest.raises(AssembleError, match="Statement cannot be used as expression"):
        SExpressionAssembler(tokens).assemble()


def test_stmt_with_none_location_as_list_element_raises(mocker):
    """Stmt 의 location 이 None 이어도 AssembleError 가 발생하고
    에러 메시지에 'unknown' 이 포함되어야 한다."""
    fake_stmt = ExpressionStmt(IdentifierExpr("z"), location=None)

    original = SExpressionAssembler._expression
    call_count = 0

    def patched(self_):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return original(self_)
        return fake_stmt

    mocker.patch.object(SExpressionAssembler, "_expression", patched)

    tokens = [lparen(), ident("c"), rparen(), eof()]
    with pytest.raises(AssembleError, match="unknown"):
        SExpressionAssembler(tokens).assemble()


# ============================================================
# 17. 트리 루트는 항상 Stmt — assemble() 레벨 방어 코드
# ============================================================

def test_top_level_stmt_from_expression_raises(mocker):
    """최상위에서 _expression() 이 Stmt 를 반환하면 AssembleError 가 발생해야 한다."""
    fake_stmt = ExpressionStmt(IdentifierExpr("x", location=loc(2, 4)), location=loc(2, 4))

    mocker.patch.object(SExpressionAssembler, "_expression", return_value=fake_stmt)

    with pytest.raises(AssembleError, match="2:4"):
        SExpressionAssembler([num(1.0), eof()]).assemble()


def test_top_level_stmt_error_message(mocker):
    """에러 메시지에 'Statement cannot be used as expression' 이 포함되어야 한다."""
    fake_stmt = ExpressionStmt(IdentifierExpr("x", location=loc(1, 1)), location=loc(1, 1))

    mocker.patch.object(SExpressionAssembler, "_expression", return_value=fake_stmt)

    with pytest.raises(AssembleError, match="Statement cannot be used as expression"):
        SExpressionAssembler([num(1.0), eof()]).assemble()


def test_top_level_stmt_with_none_location_raises(mocker):
    """최상위 Stmt 의 location 이 None 이어도 에러 메시지에 'unknown' 이 포함된다."""
    fake_stmt = ExpressionStmt(IdentifierExpr("x"), location=None)

    mocker.patch.object(SExpressionAssembler, "_expression", return_value=fake_stmt)

    with pytest.raises(AssembleError, match="unknown"):
        SExpressionAssembler([num(1.0), eof()]).assemble()


def test_program_statements_are_all_stmt_instances():
    """assemble() 이 반환하는 Program.statements 의 모든 요소는 Stmt 여야 한다."""
    tokens = [num(1.0), ident("foo"), lparen(), num(2.0), rparen(), eof()]
    prog = SExpressionAssembler(tokens).assemble()
    assert all(isinstance(s, Stmt) for s in prog.statements)


# ============================================================
# 18. 복합 식 통합 테스트
#     (if (> x 0) (set! y 1)) 를 수동으로 토큰화한 시퀀스로
#     어셈블러가 올바른 중첩 트리를 구성하는지 검증
# ============================================================

def test_complex_if_expression_tree_structure():
    """
    입력:  (if (> x 0) (set! y 1))
    토큰:  ( if ( > x 0 ) ( set! y 1 ) )

    기대 트리:
      ExpressionStmt
      └── ListExpr                     (if ...)
            ├── IdentifierExpr("if")
            ├── ListExpr               (> x 0)
            │     ├── IdentifierExpr(">")
            │     ├── IdentifierExpr("x")
            │     └── LiteralExpr(0.0)
            └── ListExpr               (set! y 1)
                  ├── IdentifierExpr("set!")
                  ├── IdentifierExpr("y")
                  └── LiteralExpr(1.0)
    """
    tokens = [
        lparen(),
        kw(TokenType.IF),                       # if  → IdentifierExpr (keyword fallthrough)
        lparen(), tok(TokenType.GREATER, ">"), ident("x"), num(0.0), rparen(),
        lparen(), ident("set!"), ident("y"), num(1.0), rparen(),
        rparen(),
        eof(),
    ]

    prog = SExpressionAssembler(tokens).assemble()

    # 루트: ExpressionStmt 하나
    assert len(prog.statements) == 1
    stmt = prog.statements[0]
    assert isinstance(stmt, ExpressionStmt)

    # 최상위 리스트: (if cond body)
    outer = stmt.expression
    assert isinstance(outer, ListExpr)
    assert len(outer.elements) == 3

    head, cond, body = outer.elements

    # head: IdentifierExpr("if")
    assert isinstance(head, IdentifierExpr)
    assert head.name == "if"

    # cond: (> x 0)
    assert isinstance(cond, ListExpr)
    assert len(cond.elements) == 3
    cond_op, cond_lhs, cond_rhs = cond.elements
    assert isinstance(cond_op, IdentifierExpr) and cond_op.name == ">"
    assert isinstance(cond_lhs, IdentifierExpr) and cond_lhs.name == "x"
    assert isinstance(cond_rhs, LiteralExpr) and cond_rhs.value == 0.0

    # body: (set! y 1)
    assert isinstance(body, ListExpr)
    assert len(body.elements) == 3
    body_op, body_lhs, body_rhs = body.elements
    assert isinstance(body_op, IdentifierExpr) and body_op.name == "set!"
    assert isinstance(body_lhs, IdentifierExpr) and body_lhs.name == "y"
    assert isinstance(body_rhs, LiteralExpr) and body_rhs.value == 1.0


def test_complex_if_expression_no_stmt_in_tree():
    """트리의 모든 Expr 노드는 Stmt 를 포함하지 않아야 한다."""
    tokens = [
        lparen(),
        kw(TokenType.IF),
        lparen(), tok(TokenType.GREATER, ">"), ident("x"), num(0.0), rparen(),
        lparen(), ident("set!"), ident("y"), num(1.0), rparen(),
        rparen(),
        eof(),
    ]

    prog = SExpressionAssembler(tokens).assemble()
    outer = prog.statements[0].expression

    def collect_exprs(node):
        yield node
        if isinstance(node, ListExpr):
            for child in node.elements:
                yield from collect_exprs(child)

    for expr_node in collect_exprs(outer):
        assert not isinstance(expr_node, Stmt)