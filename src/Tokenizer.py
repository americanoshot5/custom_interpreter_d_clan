from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from common import Token, TokenizeError, TokenType, SINGLE_CHAR_TOKENS, KEYWORDS, SourceLocation, SINGLE_INVALID_CHAR_TOKENS
from interfaces import Tokenizer
import re

_NUMBER_RE = re.compile(r'^-?\d+(\.\d+)?$')


class SExpressionTokenizer(Tokenizer):
    def __init__(self, source):
        self.token = []
        self.source = source
        self._line = 1
        self._column = 1

    def tokenize(self) -> Sequence[Token]:
        initial_token = self.get_initial_token()

        for t, location in initial_token:
            if _NUMBER_RE.match(t):
                self.set_digit_token(t, location)
            else:
                self.set_non_digit_token(t, location)
        self.token.append(
            Token(
                TokenType.EOF,
                lexeme="",
                literal="",
                location=SourceLocation(
                    line=self._line,
                    column=self._column,
                    index=len(self.source),
                ),
            )
        )
        return self.token

    def get_initial_token(self) -> list[tuple[str, SourceLocation]]:
        pattern = r'\s+|[(){}\[\]]|"[^"]*"|[^\s(){}\[\]]+'
        tokens: list[tuple[str, SourceLocation]] = []
        for match in re.finditer(pattern, self.source):
            text = match.group(0)
            location = SourceLocation(
                line=self._line,
                column=self._column,
                index=match.start(),
            )
            self._advance_location(text)
            if not text.isspace():
                tokens.append((text, location))
        return tokens

    def _advance_location(self, text: str) -> None:
        parts = text.split("\n")
        if len(parts) == 1:
            self._column += len(text)
            return
        self._line += len(parts) - 1
        self._column = len(parts[-1]) + 1

    def is_float(self, t):
        try:
            float(t)
            return True
        except:
            return False

    def set_non_digit_token(self, t, location):
        if len(t) == 1:
            self.set_single_char_token(t, location)
        elif t.lower() in KEYWORDS.keys():
            self.set_keword_token(t.lower(), location)
        else:
            self.set_string_identifier_token(t, location)

    def set_string_identifier_token(self, t, location):
        if "\'" in t or "\"" in t:
            type = TokenType.STRING
            literal = t.strip("\"")
        else:
            self.check_invalid_identifier_name(t)
            type = self.check_dot_identifier(t)
            literal = t
        self.token.append(Token(type=type, lexeme=t, literal=literal, location=location))

    def check_dot_identifier(self, t) -> Literal[TokenType.DOTIDENTIFIER]:
        if "." in t:
            return TokenType.DOTIDENTIFIER
        else:
            return TokenType.IDENTIFIER

    def check_invalid_identifier_name(self, t):
        if "(" in t:
            raise TokenizeError(f'{t} is not a valid identifier with LEFT_PAREN')
        if ")" in t:
            raise TokenizeError(f'{t} is not a valid identifier with RIGHT_PAREN')
        if "{" in t:
            raise TokenizeError(f'{t} is not a valid identifier with LEFT_BRACE')
        if "}" in t:
            raise TokenizeError(f'{t} is not a valid identifier with RIGHT_BRACE')

    def set_keword_token(self, t, location):
        type = KEYWORDS[t]
        literal = t
        if type == TokenType.FALSE:
            literal = False
        if type == TokenType.TRUE:
            literal = True
        if type == TokenType.NULL:
            literal = None
        self.token.append(Token(type=type, lexeme=t, literal=literal, location=location))


    def set_single_char_token(self, t, location):
        if t in SINGLE_CHAR_TOKENS.keys():
            type = SINGLE_CHAR_TOKENS[t]
            literal = t
        elif t in SINGLE_INVALID_CHAR_TOKENS.keys():
            raise TokenizeError(f'{t} is not a valid literal')
        else:
            type = TokenType.IDENTIFIER
            literal = t
        self.token.append(Token(type=type, lexeme=t, literal=literal, location=location))

    def set_digit_token(self, t, location):
        type = TokenType.NUMBER
        literal = float(t)
        self.token.append(Token(type=type, lexeme=t, literal=literal, location=location))


DefaultTokenizer = SExpressionTokenizer


def tokenize(source: str) -> Sequence[Token]:
    return SExpressionTokenizer(source).tokenize()


__all__ = ["DefaultTokenizer", "SExpressionTokenizer", "tokenize"]
