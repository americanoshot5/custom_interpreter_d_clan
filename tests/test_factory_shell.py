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


def test_debug_command_parser_returns_command_objects():
    parser = factory_shell.DebugCommandParser()

    cases = [
        ("step", factory_shell.StepDebugCommand),
        ("next", factory_shell.StepDebugCommand),
        ("continue", factory_shell.ContinueDebugCommand),
        ("breakpoints", factory_shell.ListBreakpointsDebugCommand),
        ("watches", factory_shell.ListWatchesDebugCommand),
        ("inspect", factory_shell.InspectDebugCommand),
        ("break 3", factory_shell.AddBreakpointDebugCommand),
        ("remove 3", factory_shell.RemoveBreakpointDebugCommand),
        ("watch total", factory_shell.WatchDebugCommand),
        ("unwatch total", factory_shell.UnwatchDebugCommand),
    ]

    for text, command_type in cases:
        command = parser.parse(text)

        assert isinstance(command, command_type)
        assert hasattr(command, "execute")


def test_debug_command_parser_returns_unknown_command_object():
    parser = factory_shell.DebugCommandParser()

    command = parser.parse("rewind")

    assert isinstance(command, factory_shell.UnknownDebugCommand)


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


def test_debug_mode_continue_executes_through_breakpoint_line():
    source = """
    (var total 0)
    (set! total (+ total 1))
    (print total)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["break 3", "continue", "inspect"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "total = 1.0" in outputs


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


def test_debug_watch_prints_value_at_each_stop():
    source = """
    (var total 0)
    (set! total (+ total 1))
    (set! total (+ total 2))
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["watch total", "step", "step", "step"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "Watch total: <undefined>" in outputs
    assert "Watch total: 0.0" in outputs
    assert "Watch total: 1.0" in outputs
    assert "Watch total: 3.0" in outputs


def test_debug_watches_command_lists_current_watch_values():
    source = """
    (var total 0)
    (set! total 5)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["watch total", "step", "step", "watches"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs[-1] == "Watch total: 5.0"


def test_debug_unwatch_removes_variable_from_watch_list():
    source = """
    (var total 0)
    (set! total 1)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["watch total", "step", "unwatch total", "step"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "Watch total: 0.0" in outputs
    assert "Watch total: 1.0" not in outputs
    assert "Stopped watching total" in outputs


def test_debug_watches_reports_empty_watch_list():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=["watches"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs[-1] == "Watches: none"


def test_debug_inspect_prints_current_scope_variables():
    source = """
    (var left 1)
    (var right 2)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["step", "step", "inspect"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "left = 1.0" in outputs
    assert "right = 2.0" in outputs


def test_debug_inspect_reports_empty_scope():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=["inspect"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs[-1] == "Scope: empty"


def test_debug_watch_tracks_multiple_variables_at_same_stop():
    source = """
    (var left 1)
    (var right 2)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["watch left", "watch right", "step", "step"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "Watch left: 1.0" in outputs
    assert "Watch right: <undefined>" in outputs
    assert "Watch right: 2.0" in outputs


def test_debug_watch_does_not_duplicate_same_variable():
    source = """
    (var total 0)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["watch total", "watch total", "step"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs.count("Watch total: 0.0") == 1


def test_debug_watch_command_requires_variable_name():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=["watch"],
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert outputs[-1] == "Usage: watch <variable>"


def test_debug_unwatch_command_requires_variable_name():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=["unwatch"],
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert outputs[-1] == "Usage: unwatch <variable>"


def test_debug_unwatch_unknown_variable_is_noop():
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        "(print 1)",
        commands=["unwatch missing", "step"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert "Stopped watching missing" in outputs
    assert all(not line.startswith("Watch missing:") for line in outputs)


def test_debug_inspect_prints_scope_variables_in_name_order():
    source = """
    (var zeta 1)
    (var alpha 2)
    """
    outputs: list[str] = []

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["step", "step", "inspect"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs.index("alpha = 2.0") < outputs.index("zeta = 1.0")


def test_run_prompt_mode_preserves_session_state_across_submissions():
    outputs: list[str] = []

    exit_code = factory_shell.run_prompt_mode(
        read_line=iter(
            ["(var total 1)", "", "(set! total (+ total 2))", "", "(print total)", "", "exit"]
        ).__next__,
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs[-1] == "3.0"


def test_run_prompt_mode_reports_language_errors():
    outputs: list[str] = []

    exit_code = factory_shell.run_prompt_mode(
        read_line=iter(["(print unknown)", "", "exit"]).__next__,
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("Error:" in line for line in outputs)


def test_run_prompt_mode_accepts_bare_statement_without_outer_parens(capsys):
    outputs: list[str] = []

    exit_code = factory_shell.run_prompt_mode(
        read_line=iter(["var a 1", "", "print a", "", "exit"]).__next__,
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert capsys.readouterr().out == "1.0\n"


def test_run_prompt_mode_shows_continuation_prompt_while_buffering():
    prompts: list[str] = []

    exit_code = factory_shell.run_prompt_mode(
        read_line=iter(["(var x", "10)", "", "exit"]).__next__,
        write_output=lambda line: None,
        on_prompt=prompts.append,
    )

    assert exit_code == 0
    assert prompts == [">>> ", "... ", "... ", ">>> "]


def test_main_run_subcommand_dispatches_to_file_mode(mocker):
    fake_run_file_mode = mocker.patch.object(factory_shell, "run_file_mode", return_value=0)

    exit_code = factory_shell.main(["run", "program.cf"])

    assert exit_code == 0
    fake_run_file_mode.assert_called_once_with("program.cf")


def test_main_debug_subcommand_dispatches_to_interactive_debug_mode(mocker):
    fake_run_debug = mocker.patch.object(
        factory_shell, "run_interactive_debug_mode", return_value=0
    )

    exit_code = factory_shell.main(["debug", "program.cf"])

    assert exit_code == 0
    fake_run_debug.assert_called_once_with("program.cf")


def test_main_prompt_subcommand_dispatches_to_prompt_mode(mocker):
    fake_run_prompt = mocker.patch.object(factory_shell, "run_prompt_mode", return_value=0)

    exit_code = factory_shell.main(["prompt"])

    assert exit_code == 0
    fake_run_prompt.assert_called_once()


def test_main_bare_path_falls_back_to_file_mode_for_backward_compat(mocker):
    fake_run_file_mode = mocker.patch.object(factory_shell, "run_file_mode", return_value=0)

    exit_code = factory_shell.main(["program.cf"])

    assert exit_code == 0
    fake_run_file_mode.assert_called_once_with("program.cf")


def test_main_with_no_args_prints_usage_and_returns_error():
    exit_code = factory_shell.main([])

    assert exit_code == 2


def test_main_with_unknown_subcommand_and_extra_args_prints_usage():
    exit_code = factory_shell.main(["bogus", "extra", "args"])

    assert exit_code == 2
