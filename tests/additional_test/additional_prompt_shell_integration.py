"""
3-6. factory control shell: file mode and debug mode

번역 규칙은 _helpers.py 참고.
"""

from __future__ import annotations

import importlib


def test_factory_shell_file_mode_executes_source_file(tmp_path):
    factory_shell = importlib.import_module("factory_shell")
    source_file = tmp_path / "program.cf"
    source_file.write_text("(print (+ 1 2))", encoding="utf-8")
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code == 0
    assert outputs == ["3.0"]


def test_factory_shell_file_mode_reports_missing_file(tmp_path):
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(
        str(tmp_path / "missing.cf"),
        write_output=outputs.append,
    )

    assert exit_code != 0
    assert any("not found" in line.lower() or "없" in line for line in outputs)


def test_factory_shell_prompt_mode_preserves_session_state():
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []

    exit_code = factory_shell.run_prompt_mode(
        read_line=iter(
            ["(var total 1)", "", "(set! total (+ total 2))", "", "(print total)", "", "exit"]
        ).__next__,
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs[-1] == "3.0"


def test_factory_shell_file_mode_reports_runtime_error_line_and_stops(tmp_path):
    factory_shell = importlib.import_module("factory_shell")
    source_file = tmp_path / "program.cf"
    source_file.write_text(
        """
        (print 1)
        (print notDefined)
        (print 3)
        """,
        encoding="utf-8",
    )
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code != 0
    assert any("line" in line.lower() and "3" in line for line in outputs)
    assert all("3.0" not in line for line in outputs)


def test_factory_shell_debug_mode_supports_watch_and_step():
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []
    source = """
    (var total 0)
    (set! total (+ total 1))
    (set! total (+ total 2))
    """

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["watch total", "step", "step", "watches", "continue"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("total" in line and "3.0" in line for line in outputs)


def test_factory_shell_debug_mode_supports_breakpoint_continue_and_inspect():
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []
    source = """
    (var total 0)
    (set! total (+ total 1))
    (set! total (+ total 2))
    """

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["break 3", "continue", "inspect", "remove 3", "breakpoints", "continue"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("total" in line and "1.0" in line for line in outputs)
    assert any("breakpoints" in line.lower() and "3" not in line for line in outputs)
