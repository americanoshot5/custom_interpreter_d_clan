from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TokenType(str, Enum):
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    SEMICOLON = ";"

    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    EQUAL = "="
    GREATER = ">"
    LESS = "<"

    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"

    VAR = "var"
    IF = "if"
    ELSE = "else"
    FOR = "for"
    TRUE = "true"
    FALSE = "false"
    AND = "and"
    OR = "or"
    PRINT = "print"

    EOF = "EOF"


KEYWORDS: dict[str, TokenType] = {
    "var": TokenType.VAR,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "print": TokenType.PRINT,
}

SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
    ";": TokenType.SEMICOLON,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "=": TokenType.EQUAL,
    ">": TokenType.GREATER,
    "<": TokenType.LESS,
}

SINGLE_INVALID_CHAR_TOKENS: dict[str, str] = {
    "~": "~",
    "`": "`",
    "!": "!",
    "@": "@",
    "#": "#",
    "$": "$",
    "%": "%"
}

LiteralValue = str | float | bool | None


@dataclass(frozen=True, slots=True)
class SourceLocation:
    line: int = 1
    column: int = 1
    index: int = 0


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    lexeme: str
    literal: LiteralValue = None
    location: SourceLocation = field(default_factory=SourceLocation)


@dataclass(frozen=True, slots=True, kw_only=True)
class Node(ABC):
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Expr(Node, ABC):
    """Base class shared by expression nodes."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Stmt(Node, ABC):
    """Base class shared by statement nodes."""


@dataclass(frozen=True, slots=True)
class LiteralExpr(Expr):
    value: LiteralValue


@dataclass(frozen=True, slots=True)
class IdentifierExpr(Expr):
    name: str


@dataclass(frozen=True, slots=True)
class ListExpr(Expr):
    elements: tuple[Expr, ...]


@dataclass(frozen=True, slots=True)
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass(frozen=True, slots=True)
class VarStmt(Stmt):
    name: str
    initializer: Expr | None = None


@dataclass(frozen=True, slots=True)
class PrintStmt(Stmt):
    expression: Expr


@dataclass(frozen=True, slots=True)
class BlockStmt(Stmt):
    statements: tuple[Stmt, ...]


@dataclass(frozen=True, slots=True)
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Stmt | None = None


@dataclass(frozen=True, slots=True)
class ForStmt(Stmt):
    iterator: str
    start: Expr
    end: Expr
    body: Stmt


@dataclass(frozen=True, slots=True)
class Program:
    statements: tuple[Stmt, ...]


class LanguageError(Exception):
    """Base exception for interpreter pipeline errors."""


class TokenizeError(LanguageError):
    pass


class AssembleError(LanguageError):
    pass


class CheckError(LanguageError):
    pass


class ExecuteError(LanguageError):
    pass


RuntimeValue = Any


__all__ = [
    "AssembleError",
    "BlockStmt",
    "CheckError",
    "ExecuteError",
    "Expr",
    "ExpressionStmt",
    "ForStmt",
    "IdentifierExpr",
    "IfStmt",
    "KEYWORDS",
    "LanguageError",
    "ListExpr",
    "LiteralExpr",
    "LiteralValue",
    "Node",
    "PrintStmt",
    "Program",
    "RuntimeValue",
    "SINGLE_CHAR_TOKENS",
    "SourceLocation",
    "Stmt",
    "Token",
    "TokenType",
    "TokenizeError",
    "VarStmt",
]
