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
    LEFT_BRACKET = "["
    RIGHT_BRACKET = "]"
    SEMICOLON = ";"

    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    EQUAL = "="
    GREATER = ">"
    LESS = "<"
    DOT = "."

    IDENTIFIER = "IDENTIFIER"
    DOTIDENTIFIER = "DOTIDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"

    VAR = "var"
    IF = "if"
    ELSE = "else"
    FOR = "for"
    SET = "set!"
    TRUE = "true"
    FALSE = "false"
    AND = "and"
    OR = "or"
    PRINT = "print"
    FUNC = "func"
    RETURN = "return"

    CLASS = "class"
    FIELD = "field"
    METHOD = "method"
    NEW = "new"
    SUPER = "super"

    NOT = "~"
    EOF = "EOF"
    NULL = "Null"

KEYWORDS: dict[str, TokenType] = {
    "var": TokenType.VAR,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "set!": TokenType.SET,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "print": TokenType.PRINT,
    "null": TokenType.NULL,
    "func": TokenType.FUNC,
    "return": TokenType.RETURN,
    "class": TokenType.CLASS,
    "field": TokenType.FIELD,
    "method": TokenType.METHOD,
    "new": TokenType.NEW,
    "super": TokenType.SUPER,
}

SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
    "[": TokenType.LEFT_BRACKET,
    "]": TokenType.RIGHT_BRACKET,
    ";": TokenType.SEMICOLON,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "=": TokenType.EQUAL,
    ">": TokenType.GREATER,
    "<": TokenType.LESS,
    "~": TokenType.NOT,
    ".": TokenType.DOT,
}

SINGLE_INVALID_CHAR_TOKENS: dict[str, str] = {
    "`": "`",
    "!": "!",
    "@": "@",
    "#": "#",
    "$": "$",
    "%": "%"
}

BUILTIN_OPS: frozenset[str] = frozenset({
    "+", "-", "*", "/", "<", ">", "=",
    "and", "or", "not",
    "Array", "index", "set-index!",
    "get-field", "set-field!", "instanceof", "return",
})

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


# ── Expression nodes ─────────────────────────────────────────────────────────

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
class ArrayExpr(Expr):
    size: Expr

@dataclass(frozen=True, slots=True)
class ArrayIndexExpr(Expr):
    array: Expr
    index: Expr

@dataclass(frozen=True, slots=True)
class NewExpr(Expr):
    """(new ClassName args...)"""
    class_name: str
    args: tuple[Expr, ...]

@dataclass(frozen=True, slots=True)
class DotExpr(Expr):
    """(. obj slot) or (. obj slot arg...)
    - No args:  read field or call zero-arg method
    - One arg + slot is a field:  write field
    - Args + slot is a method:  call method
    """
    obj: Expr
    slot: str
    args: tuple[Expr, ...]

@dataclass(frozen=True, slots=True)
class SuperExpr(Expr):
    """(super methodName args...)"""
    method: str
    args: tuple[Expr, ...]


# ── Statement nodes ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ExpressionStmt(Stmt):
    expression: Expr

@dataclass(frozen=True, slots=True)
class VarStmt(Stmt):
    name: str
    initializer: Expr | None = None

@dataclass(frozen=True, slots=True)
class SetStmt(Stmt):
    target: str
    value: Expr

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


# ── Class-related nodes ───────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class MethodDef:
    """Method definition inside a class body. Not a Stmt — contained by ClassStmt."""
    name: str
    params: tuple[str, ...]
    body: tuple[Stmt, ...]
    location: SourceLocation | None = None

@dataclass(frozen=True, slots=True)
class ClassStmt(Stmt):
    """(class Name [Parent] (field ...) ... (method ...) ...)"""
    name: str
    parent: str | None
    fields: tuple[str, ...]
    methods: tuple[MethodDef, ...]


# ── Program root ──────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class FuncDefStmt(Stmt):
    name: str
    params: tuple[str, ...]
    body: Stmt


@dataclass(frozen=True, slots=True)
class ReturnStmt(Stmt):
    value: Expr | None = None


@dataclass(frozen=True, slots=True)
class Program:
    statements: tuple[Stmt, ...]


# ── Error hierarchy ───────────────────────────────────────────────────────────

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
    "ArrayExpr",
    "ArrayIndexExpr",
    "AssembleError",
    "BUILTIN_OPS",
    "BlockStmt",
    "CheckError",
    "ClassStmt",
    "DotExpr",
    "ExecuteError",
    "Expr",
    "ExpressionStmt",
    "ForStmt",
    "FuncDefStmt",
    "IdentifierExpr",
    "IfStmt",
    "KEYWORDS",
    "LanguageError",
    "ListExpr",
    "LiteralExpr",
    "LiteralValue",
    "MethodDef",
    "NewExpr",
    "Node",
    "PrintStmt",
    "Program",
    "ReturnStmt",
    "RuntimeValue",
    "SetStmt",
    "SINGLE_CHAR_TOKENS",
    "SINGLE_INVALID_CHAR_TOKENS",
    "SourceLocation",
    "Stmt",
    "SuperExpr",
    "Token",
    "TokenType",
    "TokenizeError",
    "VarStmt",
]
