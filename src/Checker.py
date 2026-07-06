from __future__ import annotations

from common import CheckError, Program
from interfaces import Checker


class StaticChecker(Checker):
    def check(self, program: Program) -> None:
        raise CheckError("Checker implementation is not ready yet.")


DefaultChecker = StaticChecker


def check(program: Program) -> None:
    StaticChecker().check(program)


__all__ = ["DefaultChecker", "StaticChecker", "check"]

