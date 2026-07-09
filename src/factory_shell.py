from __future__ import annotations

import contextlib
import io
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from Assembler import assemble
from Checker import StaticChecker, check
from common import ExecuteError, LanguageError, Program, RuntimeValue, Stmt
from Executor import SExpressionExecutor
from prompt_shell import wrap_bare_statement
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


class DebugCommand:
    def execute(self, session: "DebugSession") -> bool:
        raise NotImplementedError


class StepDebugCommand(DebugCommand):
    def execute(self, session: "DebugSession") -> bool:
        session._step()
        return True


class ContinueDebugCommand(DebugCommand):
    def execute(self, session: "DebugSession") -> bool:
        session._continue()
        return True


class ListBreakpointsDebugCommand(DebugCommand):
    def execute(self, session: "DebugSession") -> bool:
        session._list_breakpoints()
        return True


class ListWatchesDebugCommand(DebugCommand):
    def execute(self, session: "DebugSession") -> bool:
        session._list_watches()
        return True


class InspectDebugCommand(DebugCommand):
    def execute(self, session: "DebugSession") -> bool:
        session._inspect_scope()
        return True


@dataclass(frozen=True)
class AddBreakpointDebugCommand(DebugCommand):
    command: str

    def execute(self, session: "DebugSession") -> bool:
        return session._add_breakpoint(self.command)


@dataclass(frozen=True)
class RemoveBreakpointDebugCommand(DebugCommand):
    command: str

    def execute(self, session: "DebugSession") -> bool:
        return session._remove_breakpoint(self.command)


@dataclass(frozen=True)
class WatchDebugCommand(DebugCommand):
    command: str

    def execute(self, session: "DebugSession") -> bool:
        return session._add_watch(self.command)


@dataclass(frozen=True)
class UnwatchDebugCommand(DebugCommand):
    command: str

    def execute(self, session: "DebugSession") -> bool:
        return session._remove_watch(self.command)


@dataclass(frozen=True)
class UnknownDebugCommand(DebugCommand):
    command: str

    def execute(self, session: "DebugSession") -> bool:
        session._write_output(f"Unknown debug command: {self.command}")
        return False


class DebugCommandParser:
    def parse(self, command: str) -> DebugCommand:
        if command in {"step", "next"}:
            return StepDebugCommand()
        if command == "continue":
            return ContinueDebugCommand()
        if command == "breakpoints":
            return ListBreakpointsDebugCommand()
        if command == "watches":
            return ListWatchesDebugCommand()
        if command == "inspect":
            return InspectDebugCommand()
        if command.startswith("break "):
            return AddBreakpointDebugCommand(command)
        if command.startswith("remove "):
            return RemoveBreakpointDebugCommand(command)
        if command == "watch" or command.startswith("watch "):
            return WatchDebugCommand(command)
        if command == "unwatch" or command.startswith("unwatch "):
            return UnwatchDebugCommand(command)
        return UnknownDebugCommand(command)


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
        self._watches: list[str] = []
        self._command_parser = DebugCommandParser()
        self._reported_initial = False

    def run(self, commands: Sequence[str]) -> int:
        if not self._reported_initial:
            self._report_position()
            self._reported_initial = True
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
        return self._command_parser.parse(command).execute(self)

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

    def _add_watch(self, command: str) -> bool:
        name = self._parse_name_arg(command, "watch")
        if name is None:
            return False
        if name not in self._watches:
            self._watches.append(name)
        self._write_output(f"Watching {name}")
        self._write_watch_value(name)
        return True

    def _remove_watch(self, command: str) -> bool:
        name = self._parse_name_arg(command, "unwatch")
        if name is None:
            return False
        if name in self._watches:
            self._watches.remove(name)
        self._write_output(f"Stopped watching {name}")
        return True

    def _parse_name_arg(self, command: str, name: str) -> str | None:
        parts = command.split()
        if len(parts) != 2:
            self._write_output(f"Usage: {name} <variable>")
            return None
        return parts[1]

    def _list_watches(self) -> None:
        if not self._watches:
            self._write_output("Watches: none")
            return
        for name in self._watches:
            self._write_watch_value(name)

    def _write_watch_value(self, name: str) -> None:
        try:
            value = self._executor.lookup_variable(name)
        except ExecuteError:
            value = "<undefined>"
        self._write_output(f"Watch {name}: {value}")

    def _inspect_scope(self) -> None:
        values = self._executor.current_scope_snapshot()
        if not values:
            self._write_output("Scope: empty")
            return
        for name in sorted(values):
            self._write_output(f"{name} = {values[name]}")

    def _continue(self) -> None:
        while not self._is_finished():
            current_line = self._current_line()
            self._execute_current_statement()
            self._cursor += 1
            if current_line in self._breakpoints:
                self._report_position()
                return
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
            if self._watches:
                self._list_watches()
            return
        self._write_output(f"Stopped at line {self._current_line()}")
        if self._watches:
            self._list_watches()

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


def run_interactive_debug_mode(
    path: str,
    read_line: Callable[[str], str] = input,
    write_output: Callable[[str], None] = print,
) -> int:
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

    session = DebugSession(program, write_output)
    while True:
        try:
            command = read_line("(debug) ").strip()
        except EOFError:
            return 0
        if command in {"exit", "quit"}:
            return 0
        if not command:
            continue
        exit_code = session.run([command])
        if exit_code != 0:
            return exit_code


def run_prompt_mode(
    read_line: Callable[[], str],
    write_output: Callable[[str], None] = print,
    on_prompt: Callable[[str], None] | None = None,
    prompt: str = ">>> ",
    continuation_prompt: str = "... ",
) -> int:
    checker = StaticChecker()
    executor = SExpressionExecutor()
    buffer: list[str] = []

    while True:
        if on_prompt is not None:
            on_prompt(continuation_prompt if buffer else prompt)
        try:
            line = read_line()
        except EOFError:
            return 0

        if not buffer:
            stripped = line.strip()
            if stripped.lower() in {"exit", "quit"}:
                return 0
            if stripped == "":
                continue

        if line.strip() == "":
            text = wrap_bare_statement("\n".join(buffer), tokenize, assemble)
            try:
                tokens = tokenize(text)
                program = assemble(tokens)
                checker.check(program)
                result = executor.execute(program)
            except LanguageError as error:
                write_output(f"Error: {error}")
            else:
                if result is not None:
                    write_output(str(result))
            buffer = []
            continue

        buffer.append(line)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    usage = "Usage: factory_shell.py <run|debug|prompt> [source-file]"

    if not args:
        print(usage)
        return 2

    mode, *rest = args

    if mode == "run" and len(rest) == 1:
        return run_file_mode(rest[0])
    if mode == "debug" and len(rest) == 1:
        return run_interactive_debug_mode(rest[0])
    if mode == "prompt" and not rest:
        def on_prompt(text: str) -> None:
            print(text, end="", flush=True)

        return run_prompt_mode(read_line=input, write_output=print, on_prompt=on_prompt)
    if mode not in {"run", "debug", "prompt"} and not rest:
        # 하위 호환: 서브커맨드 없이 파일 경로 하나만 주면 run 모드로 처리한다.
        return run_file_mode(mode)

    print(usage)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
