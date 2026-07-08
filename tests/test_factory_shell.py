from __future__ import annotations

import factory_shell


def test_file_mode_executes_source_file(tmp_path):
    source_file = tmp_path / "program.txt"
    source_file.write_text("(print (+ 1 2))", encoding="utf-8")
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code == 0
    assert outputs == ["3.0"]


def test_file_mode_reports_missing_file(tmp_path):
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(
        str(tmp_path / "missing.txt"),
        write_output=outputs.append,
    )

    assert exit_code != 0
    assert any("not found" in line.lower() or "없" in line for line in outputs)


def test_file_mode_reports_runtime_error_line_and_stops(tmp_path):
    source_file = tmp_path / "program.txt"
    source_file.write_text(
        """
        (print 1)
        (var arr (Array 1))
        (print (index arr 2))
        (print 3)
        """,
        encoding="utf-8",
    )
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code != 0
    assert outputs[0] == "1.0"
    assert any("line" in line.lower() and "4" in line for line in outputs)
    assert all("3.0" not in line for line in outputs)


def test_debug_mode_steps_top_level_statements():
    source = """
    (var total 0)
    (set! total (+ total 1))
    (print total)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["step", "step", "step"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("stopped" in line.lower() and "3" in line for line in outputs)
    assert "1.0" in outputs
    assert any("finished" in line.lower() for line in outputs)


def test_debug_mode_reports_initial_stop_before_running_any_statement():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=[],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs == ["Stopped at line 1"]


def test_debug_mode_next_executes_one_top_level_statement():
    source = """
    (print 1)
    (print 2)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["next"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "1.0" in outputs
    assert "2.0" not in outputs
    assert any("stopped" in line.lower() and "3" in line for line in outputs)


def test_debug_mode_continue_without_breakpoint_finishes_program():
    source = """
    (print 1)
    (print 2)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["continue"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "1.0" in outputs
    assert "2.0" in outputs
    assert outputs[-1] == "Program finished"


def test_debug_mode_continue_stops_before_breakpoint():
    source = """
    (var total 0)
    (set! total (+ total 1))
    (print total)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["break 4", "continue", "step"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    stop_index = next(
        index for index, line in enumerate(outputs)
        if "stopped" in line.lower() and "4" in line
    )
    assert "1.0" not in outputs[:stop_index]
    assert "1.0" in outputs[stop_index + 1:]


def test_debug_mode_manages_breakpoint_list():
    source = "(print 1)"
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["break 1", "breakpoints", "remove 1", "breakpoints", "continue"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("breakpoints" in line.lower() and "1" in line for line in outputs)
    assert any("breakpoints" in line.lower() and "none" in line.lower() for line in outputs)


def test_debug_mode_unknown_command_returns_error():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=["rewind"],
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert outputs[-1] == "Unknown debug command: rewind"


def test_debug_mode_invalid_breakpoint_line_returns_error():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=["break not-a-number"],
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert outputs[-1] == "Invalid line number: not-a-number"


def test_debug_mode_reports_runtime_error_line_and_stops():
    source = """
    (var arr (Array 1))
    (print (index arr 2))
    (print 3)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["step", "step", "continue"],
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert any("runtime error" in line.lower() and "3" in line for line in outputs)
    assert "3.0" not in outputs
