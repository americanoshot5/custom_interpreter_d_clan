from __future__ import annotations

from collections.abc import Sequence

from common import Token, TokenizeError, TokenType, SINGLE_CHAR_TOKENS, KEYWORDS, SourceLocation
from interfaces import Tokenizer
import re


class SExpressionTokenizer(Tokenizer):
    def __init__(self):
        ...

    def tokenize(self, source: str) -> Sequence[Token]:
        raise TokenizeError("Tokenizer implementation is not ready yet.")

DefaultTokenizer = SExpressionTokenizer

def tokenize(source: str) -> Sequence[Token]:
    print('\n')
    print(source)

    pattern = r'\s+|[()]|"[^"]*"|[^\s()]+'
    tokens = re.findall(pattern, source)
    token = [token for token in tokens if not token.isspace()]
    ret = []

    for t in token:
        if t.isdigit():
            type = TokenType.NUMBER
            literal = float(t)
        else:
            type = SINGLE_CHAR_TOKENS[t]
            literal = t

        ret.append(Token(type=type, lexeme=t, literal=literal))
    ret.append(Token(TokenType.EOF, ""))
    return ret

__all__ = ["DefaultTokenizer", "SExpressionTokenizer", "tokenize"]
