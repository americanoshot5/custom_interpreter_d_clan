from __future__ import annotations

from collections.abc import Sequence

from common import Token, TokenizeError, TokenType, SINGLE_CHAR_TOKENS, KEYWORDS, SourceLocation
from interfaces import Tokenizer
import re


class SExpressionTokenizer(Tokenizer):
    def __init__(self, source):
        self.token = []
        self.source = source

    def tokenize(self) -> Sequence[Token]:
        pattern = r'\s+|[()]|"[^"]*"|[^\s()]+'
        tokens = re.findall(pattern, self.source)
        token = [token for token in tokens if not token.isspace()]

        for t in token:
            if t.isdigit():
                type = TokenType.NUMBER
                literal = float(t)
            else:
                if len(t) == 1:
                    if t in SINGLE_CHAR_TOKENS.keys():
                        type = SINGLE_CHAR_TOKENS[t]
                        literal = t
                    else:
                        raise TokenizeError(f'{t} is not a valid literal')
                elif t in KEYWORDS.keys():
                    type = KEYWORDS[t]
                    literal = t
                    if type == TokenType.FALSE:
                        literal = False
                    if type == TokenType.TRUE:
                        literal = True
                else:
                    type = TokenType.STRING
                    literal = t.strip("\"")

            self.token.append(Token(type=type, lexeme=t, literal=literal))
        self.token.append(Token(TokenType.EOF, ""))
        return self.token


DefaultTokenizer = SExpressionTokenizer

__all__ = ["DefaultTokenizer", "SExpressionTokenizer", "tokenize"]
