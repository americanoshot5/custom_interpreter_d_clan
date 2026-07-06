from __future__ import annotations

from collections.abc import Sequence

from src.common import (
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
from src.interfaces import Assembler


class SExpressionAssembler(Assembler):
    def assemble(self, tokens: Sequence[Token]) -> Program:
        raise AssembleError("Assembler implementation is not ready yet.")


DefaultAssembler = SExpressionAssembler


def assemble(tokens: Sequence[Token]) -> Program:
    return SExpressionAssembler().assemble(tokens)


__all__ = ["DefaultAssembler", "SExpressionAssembler", "assemble"]
