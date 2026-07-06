from __future__ import annotations

from collections.abc import Sequence

from common import KEYWORDS, SINGLE_CHAR_TOKENS, SourceLocation, Token, TokenType, TokenizeError
from interfaces import Tokenizer


class SExpressionTokenizer(Tokenizer):
    def tokenize(self, source: str) -> Sequence[Token]:
        tokens: list[Token] = []
        line = 1
        column = 1
        index = 0

        while index < len(source):
            char = source[index]

            if char in " \r\t":
                index += 1
                column += 1
                continue

            if char == "\n":
                index += 1
                line += 1
                column = 1
                continue

            location = SourceLocation(line=line, column=column, index=index)

            if char in SINGLE_CHAR_TOKENS:
                tokens.append(Token(SINGLE_CHAR_TOKENS[char], char, location=location))
                index += 1
                column += 1
                continue

            if char == '"':
                lexeme, value, index, line, column = self._read_string(source, index, line, column)
                tokens.append(Token(TokenType.STRING, lexeme, value, location))
                continue

            if char.isdigit() or (char == "-" and self._next_is_digit(source, index)):
                lexeme, value, index, column = self._read_number(source, index, column)
                tokens.append(Token(TokenType.NUMBER, lexeme, value, location))
                continue

            if self._is_identifier_start(char):
                lexeme, index, column = self._read_identifier(source, index, column)
                token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
                literal = True if token_type is TokenType.TRUE else False if token_type is TokenType.FALSE else None
                tokens.append(Token(token_type, lexeme, literal, location))
                continue

            raise TokenizeError(f"Unexpected character {char!r} at {line}:{column}")

        tokens.append(Token(TokenType.EOF, "", location=SourceLocation(line=line, column=column, index=index)))
        return tokens

    def _read_string(
        self,
        source: str,
        start: int,
        line: int,
        column: int,
    ) -> tuple[str, str, int, int, int]:
        index = start + 1
        current_column = column + 1
        chars: list[str] = []

        while index < len(source):
            char = source[index]
            if char == '"':
                lexeme = source[start : index + 1]
                return lexeme, "".join(chars), index + 1, line, current_column + 1
            if char == "\n":
                raise TokenizeError(f"Unterminated string at {line}:{column}")
            chars.append(char)
            index += 1
            current_column += 1

        raise TokenizeError(f"Unterminated string at {line}:{column}")

    def _read_number(self, source: str, start: int, column: int) -> tuple[str, float, int, int]:
        index = start
        if source[index] == "-":
            index += 1

        while index < len(source) and source[index].isdigit():
            index += 1

        if index < len(source) and source[index] == ".":
            index += 1
            while index < len(source) and source[index].isdigit():
                index += 1

        lexeme = source[start:index]
        return lexeme, float(lexeme), index, column + len(lexeme)

    def _read_identifier(self, source: str, start: int, column: int) -> tuple[str, int, int]:
        index = start
        while index < len(source) and self._is_identifier_part(source[index]):
            index += 1

        lexeme = source[start:index]
        return lexeme, index, column + len(lexeme)

    def _next_is_digit(self, source: str, index: int) -> bool:
        return index + 1 < len(source) and source[index + 1].isdigit()

    def _is_identifier_start(self, char: str) -> bool:
        return char.isalpha() or char == "_"

    def _is_identifier_part(self, char: str) -> bool:
        return char.isalnum() or char in "_-?"


DefaultTokenizer = SExpressionTokenizer


def tokenize(source: str) -> Sequence[Token]:
    return SExpressionTokenizer().tokenize(source)


__all__ = ["DefaultTokenizer", "SExpressionTokenizer", "tokenize"]

