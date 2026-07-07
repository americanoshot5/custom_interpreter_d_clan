from prompt_shell import is_balanced, run_shell
from common import TokenizeError


def _scripted_read_line(lines):
    remaining = iter(lines)

    def read_line(prompt):
        try:
            return next(remaining)
        except StopIteration:
            raise EOFError

    return read_line


def _unreachable(*args, **kwargs):
    raise AssertionError("pipeline function should not be called")


def test_is_balanced_basic_depth_counting():
    assert is_balanced("(+ 1 2)") is True
    assert is_balanced("(+ 1 (* 2 3)") is False


def test_is_balanced_ignores_parens_inside_string_literals():
    assert is_balanced('(print "(")') is True


def test_exit_command_terminates_loop():
    outputs = []
    run_shell(
        read_line=_scripted_read_line(["exit"]),
        write_output=outputs.append,
        tokenize=_unreachable,
        assemble=_unreachable,
        check=_unreachable,
        execute=_unreachable,
    )
    assert outputs == []


def test_eof_terminates_loop():
    outputs = []
    run_shell(
        read_line=_scripted_read_line([]),
        write_output=outputs.append,
        tokenize=_unreachable,
        assemble=_unreachable,
        check=_unreachable,
        execute=_unreachable,
    )
    assert outputs == []


def test_single_line_success_prints_result(mocker):
    fake_tokenize = mocker.Mock(return_value=["TOKENS"])
    fake_assemble = mocker.Mock(return_value="PROGRAM")
    fake_check = mocker.Mock(return_value=None)
    fake_execute = mocker.Mock(return_value=3.0)

    outputs = []
    run_shell(
        read_line=_scripted_read_line(["(+ 1 2)", "", "exit"]),
        write_output=outputs.append,
        tokenize=fake_tokenize,
        assemble=fake_assemble,
        check=fake_check,
        execute=fake_execute,
    )
    assert outputs == ["3.0"]
    fake_tokenize.assert_called_once_with("(+ 1 2)")
    fake_assemble.assert_called_once_with(["TOKENS"])
    fake_check.assert_called_once_with("PROGRAM")
    fake_execute.assert_called_once_with("PROGRAM")


def test_pipeline_error_is_reported_and_loop_continues(mocker):
    fake_tokenize = mocker.Mock(side_effect=TokenizeError("boom"))

    outputs = []
    run_shell(
        read_line=_scripted_read_line(["bad input", "", "exit"]),
        write_output=outputs.append,
        tokenize=fake_tokenize,
        assemble=_unreachable,
        check=_unreachable,
        execute=_unreachable,
    )
    assert outputs == ["Error: boom"]


def test_blank_line_is_skipped_without_pipeline_call():
    outputs = []
    run_shell(
        read_line=_scripted_read_line(["", "exit"]),
        write_output=outputs.append,
        tokenize=_unreachable,
        assemble=_unreachable,
        check=_unreachable,
        execute=_unreachable,
    )
    assert outputs == []


def test_balanced_expression_waits_for_blank_line_before_dispatch(mocker):
    fake_tokenize = mocker.Mock(return_value=["TOKENS"])

    outputs = []
    run_shell(
        read_line=_scripted_read_line(["(+ 1 2)", "exit"]),
        write_output=outputs.append,
        tokenize=fake_tokenize,
        assemble=mocker.Mock(return_value="PROGRAM"),
        check=mocker.Mock(return_value=None),
        execute=mocker.Mock(return_value=3.0),
    )
    assert outputs == []
    fake_tokenize.assert_not_called()


def test_multiline_expression_submits_on_blank_line(mocker):
    fake_tokenize = mocker.Mock(return_value=["TOKENS"])
    fake_assemble = mocker.Mock(return_value="PROGRAM")
    fake_check = mocker.Mock(return_value=None)
    fake_execute = mocker.Mock(return_value=7.0)

    outputs = []
    run_shell(
        read_line=_scripted_read_line(["(+ 1", "(* 2 3))", "", "exit"]),
        write_output=outputs.append,
        tokenize=fake_tokenize,
        assemble=fake_assemble,
        check=fake_check,
        execute=fake_execute,
    )
    assert outputs == ["7.0"]
    fake_tokenize.assert_called_once_with("(+ 1\n(* 2 3))")


def test_multiple_top_level_expressions_submit_together_on_blank_line(mocker):
    fake_tokenize = mocker.Mock(return_value=["TOKENS"])

    outputs = []
    run_shell(
        read_line=_scripted_read_line(['(print "hello")', "(+ 1 2)", "", "exit"]),
        write_output=outputs.append,
        tokenize=fake_tokenize,
        assemble=mocker.Mock(return_value="PROGRAM"),
        check=mocker.Mock(return_value=None),
        execute=mocker.Mock(return_value=3.0),
    )
    assert outputs == ["3.0"]
    fake_tokenize.assert_called_once_with('(print "hello")\n(+ 1 2)')


def test_main_wires_run_shell_with_real_pipeline_functions(mocker):
    import prompt_shell
    from Assembler import assemble
    from Checker import check
    from Executor import execute
    from Tokenizer import tokenize

    fake_run_shell = mocker.patch.object(prompt_shell, "run_shell")
    prompt_shell.main()

    captured = fake_run_shell.call_args.kwargs
    assert captured["read_line"] is input
    assert captured["write_output"] is print
    assert captured["tokenize"] is tokenize
    assert captured["assemble"] is assemble
    assert captured["check"] is check
    assert captured["execute"] is execute
