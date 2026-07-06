from __future__ import annotations

from collections.abc import Sequence

from common import Token, TokenizeError
from interfaces import Tokenizer


class SExpressionTokenizer(Tokenizer):
    def tokenize(self, source: str) -> Sequence[Token]:
        raise TokenizeError("Tokenizer implementation is not ready yet.")


DefaultTokenizer = SExpressionTokenizer


def tokenize(source: str) -> Sequence[Token]:
    return SExpressionTokenizer().tokenize(source)


__all__ = ["DefaultTokenizer", "SExpressionTokenizer", "tokenize"]
