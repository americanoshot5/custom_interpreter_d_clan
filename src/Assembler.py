from __future__ import annotations

from collections.abc import Sequence

from common import (
    AssembleError,
    Expr,
    ExpressionStmt,
    IdentifierExpr,
    ListExpr,
    LiteralExpr,
    Program,
    Token,
    TokenType,
)
from interfaces import Assembler


class SExpressionAssembler(Assembler):
    def assemble(self, tokens: Sequence[Token]) -> Program:
        self._tokens = list(tokens)
        self._current = 0

        statements: list[ExpressionStmt] = []
        while not self._is_at_end():
            statements.append(ExpressionStmt(self._expression()))

        return Program(tuple(statements))

    def _expression(self) -> Expr:
        token = self._advance()

        if token.type is TokenType.LEFT_PAREN:
            elements: list[Expr] = []
            while not self._check(TokenType.RIGHT_PAREN):
                if self._is_at_end():
                    raise AssembleError(f"Missing ')' for list opened at {token.location.line}:{token.location.column}")
                elements.append(self._expression())
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after S-expression")
            return ListExpr(tuple(elements), location=token.location)

        if token.type is TokenType.RIGHT_PAREN:
            raise AssembleError(f"Unexpected ')' at {token.location.line}:{token.location.column}")

        if token.type in {TokenType.NUMBER, TokenType.STRING, TokenType.TRUE, TokenType.FALSE}:
            return LiteralExpr(token.literal, location=token.location)

        return IdentifierExpr(token.lexeme, location=token.location)

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
    return SExpressionAssembler().assemble(tokens)


__all__ = ["DefaultAssembler", "SExpressionAssembler", "assemble"]

