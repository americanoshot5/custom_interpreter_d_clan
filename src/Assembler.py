from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from common import (
    ArrayExpr,
    ArrayIndexExpr,
    AssembleError,
    BlockStmt,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDefStmt,
    IdentifierExpr,
    IfStmt,
    ListExpr,
    LiteralExpr,
    PrintStmt,
    Program,
    ReturnStmt,
    SetStmt,
    Stmt,
    Token,
    TokenType,
    VarStmt,
)
from interfaces import Assembler


class SExpressionAssembler(Assembler):

    # 새로운 special form 추가 시: 이 테이블에 한 줄 + 파서 메서드 하나만 추가하면 됩니다.
    _SPECIAL_FORMS: ClassVar[dict[TokenType, str]] = {
        TokenType.VAR:    "_parse_var_stmt",
        TokenType.SET:    "_parse_set_stmt",
        TokenType.PRINT:  "_parse_print_stmt",
        TokenType.IF:     "_parse_if_stmt",
        TokenType.FOR:    "_parse_for_stmt",
        TokenType.FUNC:   "_parse_func_stmt",
        TokenType.RETURN: "_parse_return_stmt",
    }

    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = list(tokens)
        self._current = 0

    def assemble(self) -> Program:
        statements: list[Stmt] = []
        while not self._is_at_end():
            statements.append(self._statement())
        return Program(tuple(statements))

    # ── Statement parsers ────────────────────────────────────────────────────

    def _statement(self) -> Stmt:
        if self._check(TokenType.LEFT_BRACE):
            return self._parse_block()
        if self._check(TokenType.LEFT_PAREN):
            return self._parse_list_stmt()
        expr = self._expression()
        self._assert_expr(expr)
        return ExpressionStmt(expr)

    def _parse_block(self) -> BlockStmt:
        open_brace = self._advance()  # consume '{'
        stmts: list[Stmt] = []
        while not self._check(TokenType.RIGHT_BRACE):
            if self._is_at_end():
                raise AssembleError(
                    f"Missing '}}' for block opened at "
                    f"{open_brace.location.line}:{open_brace.location.column}"
                )
            stmts.append(self._statement())
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after block")
        return BlockStmt(tuple(stmts), location=open_brace.location)

    def _parse_list_stmt(self) -> Stmt:
        open_paren = self._advance()  # consume '('
        method_name = self._SPECIAL_FORMS.get(self._peek().type)
        if method_name:
            return getattr(self, method_name)(open_paren)
        return ExpressionStmt(self._parse_list(open_paren))

    def _parse_set_stmt(self, open_paren: Token) -> SetStmt:
        self._advance()  # consume 'set!'
        target_token = self._peek()
        if target_token.type is not TokenType.IDENTIFIER:
            raise AssembleError(
                f"Invalid assignment target at "
                f"{target_token.location.line}:{target_token.location.column}: "
                f"assignment target must be a variable name"
            )
        self._advance()  # consume the identifier
        value = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close set! statement")
        return SetStmt(target=target_token.lexeme, value=value, location=open_paren.location)

    def _parse_var_stmt(self, open_paren: Token) -> VarStmt:
        self._advance()  # consume 'var'
        name_token = self._consume(TokenType.IDENTIFIER, "Expected variable name after 'var'")
        initializer = None
        if not self._check(TokenType.RIGHT_PAREN):
            initializer = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close var statement")
        return VarStmt(name=name_token.lexeme, initializer=initializer, location=open_paren.location)

    def _parse_print_stmt(self, open_paren: Token) -> PrintStmt:
        self._advance()  # consume 'print'
        expr = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close print statement")
        return PrintStmt(expression=expr, location=open_paren.location)

    def _parse_if_stmt(self, open_paren: Token) -> IfStmt:
        self._advance()  # consume 'if'
        condition = self._expression()
        then_branch = self._statement()
        else_branch = None
        if not self._check(TokenType.RIGHT_PAREN):
            else_branch = self._statement()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close if statement")
        return IfStmt(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            location=open_paren.location,
        )

    def _parse_for_stmt(self, open_paren: Token) -> ForStmt:
        self._advance()  # consume 'for'
        iter_token = self._consume(TokenType.IDENTIFIER, "Expected iterator name after 'for'")
        start = self._expression()
        end = self._expression()
        body = self._statement()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close for statement")
        return ForStmt(
            iterator=iter_token.lexeme,
            start=start,
            end=end,
            body=body,
            location=open_paren.location,
        )

    def _parse_func_stmt(self, open_paren: Token) -> FuncDefStmt:
        self._advance()  # consume 'func'
        name_token = self._consume(TokenType.IDENTIFIER, "Expected function name after 'func'")
        self._consume(TokenType.LEFT_PAREN, "Expected '(' for parameter list in func")
        params: list[str] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError("Unclosed parameter list in func declaration")
            param_token = self._consume(TokenType.IDENTIFIER, "Expected parameter name in func")
            params.append(param_token.lexeme)
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close parameter list in func")
        body = self._statement()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close func declaration")
        return FuncDefStmt(
            name=name_token.lexeme,
            params=tuple(params),
            body=body,
            location=open_paren.location,
        )

    def _parse_return_stmt(self, open_paren: Token) -> ReturnStmt:
        self._advance()  # consume 'return'
        if self._check(TokenType.RIGHT_PAREN):
            self._advance()  # consume ')'
            return ReturnStmt(value=None, location=open_paren.location)
        value = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close return statement")
        return ReturnStmt(value=value, location=open_paren.location)

    # ── Expression parsers ───────────────────────────────────────────────────

    def _expression(self) -> Expr:
        token = self._advance()
        if token.type is TokenType.LEFT_PAREN:
            expr = self._parse_list(token)
        elif token.type is TokenType.LEFT_BRACKET:
            expr = self._parse_array(token)
        else:
            expr = self._parse_atom(token)

        while self._check(TokenType.LEFT_BRACKET):
            bracket = self._advance()
            index = self._expression()
            self._consume(TokenType.RIGHT_BRACKET, "Expected ']' to close array index")
            expr = ArrayIndexExpr(array=expr, index=index, location=bracket.location)

        return expr

    def _parse_array(self, open_bracket: Token) -> ArrayExpr:
        size = self._expression()
        self._consume(TokenType.RIGHT_BRACKET, "Expected ']' to close array literal")
        return ArrayExpr(size=size, location=open_bracket.location)

    def _parse_list(self, open_paren: Token) -> ListExpr:
        elements: list[Expr] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError(
                    f"Missing ')' for list opened at "
                    f"{open_paren.location.line}:{open_paren.location.column}"
                )
            child = self._expression()
            self._assert_expr(child)
            elements.append(child)
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after S-expression")
        return ListExpr(tuple(elements), location=open_paren.location)

    def _parse_atom(self, token: Token) -> Expr:
        if token.type is TokenType.RIGHT_PAREN:
            raise AssembleError(f"Unexpected ')' at {token.location.line}:{token.location.column}")
        if token.type is TokenType.RIGHT_BRACKET:
            raise AssembleError(f"Unexpected ']' at {token.location.line}:{token.location.column}")
        if token.type in {TokenType.NUMBER, TokenType.STRING, TokenType.TRUE, TokenType.FALSE}:
            return LiteralExpr(token.literal, location=token.location)
        return IdentifierExpr(token.lexeme, location=token.location)

    def _assert_expr(self, node: Expr) -> None:
        if isinstance(node, Stmt):
            loc = node.location
            loc_str = f"{loc.line}:{loc.column}" if loc is not None else "unknown"
            raise AssembleError(f"Statement cannot be used as expression at {loc_str}")

    # ── Token navigation ─────────────────────────────────────────────────────

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        raise AssembleError(f"{message} at {token.location.line}:{token.location.column}")

    def _check(self, token_type: TokenType) -> bool:
        return not self._is_at_end() and self._peek().type is token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self._current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type is TokenType.EOF

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]


DefaultAssembler = SExpressionAssembler


def assemble(tokens: Sequence[Token]) -> Program:
    return SExpressionAssembler(tokens).assemble()


__all__ = ["DefaultAssembler", "SExpressionAssembler", "assemble"]
