from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from  src.common import Program, RuntimeValue, Token


class Tokenizer(ABC):
    @abstractmethod
    def tokenize(self, source: str) -> Sequence[Token]:
        """Convert source text into tokens."""


class Assembler(ABC):
    @abstractmethod
    def assemble(self, tokens: Sequence[Token]) -> Program:
        """Convert tokens into the common AST representation."""


class Checker(ABC):
    @abstractmethod
    def check(self, program: Program) -> None:
        """Validate a program before execution."""


class Executor(ABC):
    @abstractmethod
    def execute(self, program: Program) -> RuntimeValue:
        """Run a checked program and return its last value."""


__all__ = ["Assembler", "Checker", "Executor", "Tokenizer"]

