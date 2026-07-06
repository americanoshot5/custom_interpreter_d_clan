from __future__ import annotations

from collections.abc import Callable, Sequence

from common import LanguageError, Program, RuntimeValue, Token


def is_balanced(text: str) -> bool:
    depth = 0
    in_string = False
    for char in text:
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
    return depth <= 0


def run_shell(
    read_line: Callable[[str], str],
    write_output: Callable[[str], None],
    tokenize: Callable[[str], Sequence[Token]],
    assemble: Callable[[Sequence[Token]], Program],
    check: Callable[[Program], None],
    execute: Callable[[Program], RuntimeValue],
    prompt: str = ">>> ",
    continuation_prompt: str = "... ",
) -> None:
    while True:
        try:
            line = read_line(prompt)
        except EOFError:
            return

        if line.strip().lower() in {"exit", "quit"}:
            return
        if line.strip() == "":
            continue

        try:
            tokens = tokenize(line)
            program = assemble(tokens)
            check(program)
            result = execute(program)
        except LanguageError as error:
            write_output(f"Error: {error}")
        else:
            write_output(str(result))
