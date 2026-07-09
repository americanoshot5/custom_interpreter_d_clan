from __future__ import annotations

from collections.abc import Callable, Sequence

from Assembler import assemble
from Checker import StaticChecker
from common import LanguageError, Program, RuntimeValue, Token
from Executor import SExpressionExecutor
from Tokenizer import tokenize


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
    checkpoint: Callable[[], object] | None = None,
    restore: Callable[[object], None] | None = None,
) -> None:
    buffer: list[str] = []

    while True:
        current_prompt = continuation_prompt if buffer else prompt
        try:
            line = read_line(current_prompt)
        except EOFError:
            return

        if not buffer:
            stripped = line.strip()
            if stripped.lower() in {"exit", "quit"}:
                return
            if stripped == "":
                continue

        if line.strip() == "":
            text = "\n".join(buffer)
            saved = checkpoint() if checkpoint is not None else None
            try:
                tokens = tokenize(text)
                program = assemble(tokens)
                check(program)
                result = execute(program)
            except LanguageError as error:
                if saved is not None and restore is not None:
                    restore(saved)
                write_output(f"Error: {error}")
            else:
                if result is not None:
                    write_output(str(result))

            buffer = []
            continue

        buffer.append(line)


def main() -> None:
    checker = StaticChecker()
    executor = SExpressionExecutor()
    run_shell(
        read_line=input,
        write_output=print,
        tokenize=tokenize,
        assemble=assemble,
        check=checker.check,
        execute=executor.execute,
        checkpoint=checker.checkpoint,
        restore=checker.restore,
    )


if __name__ == "__main__":
    main()
