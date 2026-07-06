from __future__ import annotations

from collections.abc import Sequence

from common import AssembleError, Program, Token
from interfaces import Assembler


class SExpressionAssembler(Assembler):
    def assemble(self, tokens: Sequence[Token]) -> Program:
        raise AssembleError("Assembler implementation is not ready yet.")


DefaultAssembler = SExpressionAssembler


def assemble(tokens: Sequence[Token]) -> Program:
    return SExpressionAssembler().assemble(tokens)


__all__ = ["DefaultAssembler", "SExpressionAssembler", "assemble"]
