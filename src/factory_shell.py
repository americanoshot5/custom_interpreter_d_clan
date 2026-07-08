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


class DebugSession:
    def __init__(
        self,
        program: Program,
        write_output: Callable[[str], None],
    ) -> None:
        self._program = program
        self._write_output = write_output
        self._executor = FileModeExecutor()
        self._cursor = 0
        self._breakpoints: set[int] = set()

    def run(self, commands: Sequence[str]) -> int:
        self._report_position()
        try:
            for command in commands:
                if not self._handle_command(command.strip()):
                    return 1
        except RuntimeExecutionError as error:
            line = str(error.line) if error.line is not None else "unknown"
            self._write_output(f"Runtime error at line {line}: {error.error}")
            return 1
        return 0

    def _handle_command(self, command: str) -> bool:
        if command in {"step", "next"}:
            self._step()
            return True
        if command == "continue":
            self._continue()
            return True
        if command == "breakpoints":
            self._list_breakpoints()
            return True
        if command.startswith("break "):
            return self._add_breakpoint(command)
        if command.startswith("remove "):
            return self._remove_breakpoint(command)
        self._write_output(f"Unknown debug command: {command}")
        return False

    def _add_breakpoint(self, command: str) -> bool:
        line = self._parse_line_arg(command, "break")
        if line is None:
            return False
        self._breakpoints.add(line)
        self._write_output(f"Breakpoint set at line {line}")
        return True

    def _remove_breakpoint(self, command: str) -> bool:
        line = self._parse_line_arg(command, "remove")
        if line is None:
            return False
        self._breakpoints.discard(line)
        self._write_output(f"Breakpoint removed at line {line}")
        return True

    def _parse_line_arg(self, command: str, name: str) -> int | None:
        parts = command.split()
        if len(parts) != 2:
            self._write_output(f"Usage: {name} <line>")
            return None
        try:
            return int(parts[1])
        except ValueError:
            self._write_output(f"Invalid line number: {parts[1]}")
            return None

    def _list_breakpoints(self) -> None:
        if not self._breakpoints:
            self._write_output("Breakpoints: none")
            return
        points = ", ".join(str(line) for line in sorted(self._breakpoints))
        self._write_output(f"Breakpoints: {points}")

    def _continue(self) -> None:
        while not self._is_finished():
            if self._current_line() in self._breakpoints:
                self._report_position()
                return
            self._execute_current_statement()
            self._cursor += 1
        self._report_position()

    def _step(self) -> None:
        if self._is_finished():
            self._report_position()
            return
        self._execute_current_statement()
        self._cursor += 1
        self._report_position()

    def _execute_current_statement(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self._executor._execute_stmt(self._program.statements[self._cursor])
        _emit_captured_stdout(stdout.getvalue(), self._write_output)

    def _report_position(self) -> None:
        if self._is_finished():
            self._write_output("Program finished")
            return
        self._write_output(f"Stopped at line {self._current_line()}")

    def _current_line(self) -> int | None:
        stmt = self._program.statements[self._cursor]
        return stmt.location.line if stmt.location is not None else None

    def _is_finished(self) -> bool:
        return self._cursor >= len(self._program.statements)


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


def run_debug_mode(
    source: str,
    commands: Sequence[str],
    write_output: Callable[[str], None] = print,
) -> int:
    try:
        program = _run_pipeline(source)
    except LanguageError as error:
        write_output(f"Error: {error}")
        return 1

    return DebugSession(program, write_output).run(commands)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: factory_shell.py <source-file>")
        return 2
    return run_file_mode(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
