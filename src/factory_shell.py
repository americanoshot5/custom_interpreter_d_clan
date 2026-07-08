from __future__ import annotations

import contextlib
import io
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from Assembler import assemble
from Checker import check
from common import ExecuteError, LanguageError, Program, RuntimeValue, Stmt
from Executor import SExpressionExecutor
from Tokenizer import tokenize


class RuntimeExecutionError(ExecuteError):
    def __init__(self, line: int | None, error: BaseException) -> None:
        self.line = line
        self.error = error
        super().__init__(str(error))


class FileModeExecutor(SExpressionExecutor):
    def _execute_stmt(self, stmt: Stmt) -> RuntimeValue:
        try:
            return super()._execute_stmt(stmt)
        except RuntimeExecutionError:
            raise
        except (ExecuteError, ZeroDivisionError) as error:
            line = stmt.location.line if stmt.location is not None else None
            raise RuntimeExecutionError(line, error) from error


def _run_pipeline(source: str) -> Program:
    tokens = tokenize(source)
    program = assemble(tokens)
    check(program)
    return program


def _emit_captured_stdout(captured: str, write_output: Callable[[str], None]) -> None:
    for line in captured.splitlines():
        write_output(line)


def run_file_mode(path: str, write_output: Callable[[str], None] = print) -> int:
    source_path = Path(path)
    try:
        source = source_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        write_output(f"File not found: {source_path}")
        return 1
    except OSError as error:
        write_output(f"Could not read file '{source_path}': {error}")
        return 1

    try:
        program = _run_pipeline(source)
    except LanguageError as error:
        write_output(f"Error: {error}")
        return 1

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            FileModeExecutor().execute(program)
    except RuntimeExecutionError as error:
        _emit_captured_stdout(stdout.getvalue(), write_output)
        line = str(error.line) if error.line is not None else "unknown"
        write_output(f"Runtime error at line {line}: {error.error}")
        return 1

    _emit_captured_stdout(stdout.getvalue(), write_output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: factory_shell.py <source-file>")
        return 2
    return run_file_mode(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
