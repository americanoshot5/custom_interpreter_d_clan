from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Any

from common import Token, TokenizeError, TokenType, SINGLE_CHAR_TOKENS, KEYWORDS, SourceLocation, SINGLE_INVALID_CHAR_TOKENS
from interfaces import Tokenizer
import re


class SExpressionTokenizer(Tokenizer):
    def __init__(self, source):
        self.token = []
        self.source = source

    def tokenize(self) -> Sequence[Token]:
        initial_token = self.get_initial_token()

        for t in initial_token:
            if t.isdigit():
                self.set_digit_token(t)
            else:
                self.set_non_digit_token(t)
        self.token.append(Token(TokenType.EOF, lexeme="", literal=""))
        return self.token

    def get_initial_token(self) -> list[Any]:
        pattern = r'\s+|[(){}]|"[^"]*"|[^\s(){}]+'
        tokens = re.findall(pattern, self.source)
        token = [token for token in tokens if not token.isspace()]
        return token

    def set_non_digit_token(self, t):
        if len(t) == 1:
            self.set_single_char_token(t)
        elif t in KEYWORDS.keys():
            self.set_keword_token(t)
        else:
            self.set_string_identifier_token(t)

    def set_string_identifier_token(self, t):
        if "\'" in t or "\"" in t:
            type = TokenType.STRING
            literal = t.strip("\"")
        else:
            self.check_invalid_identifier_name(t)
            type = TokenType.IDENTIFIER
            literal = t
        self.token.append(Token(type=type, lexeme=t, literal=literal))

    def check_invalid_identifier_name(self, t):
        if "(" in t:
            raise TokenizeError(f'{t} is not a valid identifier with LEFT_PAREN')
        if ")" in t:
            raise TokenizeError(f'{t} is not a valid identifier with RIGHT_PAREN')
        if "{" in t:
            raise TokenizeError(f'{t} is not a valid identifier with LEFT_BRACE')
        if "}" in t:
            raise TokenizeError(f'{t} is not a valid identifier with RIGHT_BRACE')

    def set_keword_token(self, t):
        type = KEYWORDS[t]
        literal = t
        if type == TokenType.FALSE:
            literal = False
        if type == TokenType.TRUE:
            literal = True
        self.token.append(Token(type=type, lexeme=t, literal=literal))


    def set_single_char_token(self, t):
        if t in SINGLE_CHAR_TOKENS.keys():
            type = SINGLE_CHAR_TOKENS[t]
            literal = t
        elif t in SINGLE_INVALID_CHAR_TOKENS.keys():
            raise TokenizeError(f'{t} is not a valid literal')
        else:
            type = TokenType.IDENTIFIER
            literal = t
        self.token.append(Token(type=type, lexeme=t, literal=literal))

    def set_digit_token(self, t):
        type = TokenType.NUMBER
        literal = float(t)
        self.token.append(Token(type=type, lexeme=t, literal=literal))


DefaultTokenizer = SExpressionTokenizer


def tokenize(source: str) -> Sequence[Token]:
    return SExpressionTokenizer(source).tokenize()


__all__ = ["DefaultTokenizer", "SExpressionTokenizer", "tokenize"]
