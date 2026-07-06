from prompt_shell import is_balanced, run_shell


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


def test_single_line_success_prints_result():
    calls = {}

    def fake_tokenize(source):
        calls["tokenize"] = source
        return ["TOKENS"]

    def fake_assemble(tokens):
        calls["assemble"] = tokens
        return "PROGRAM"

    def fake_check(program):
        calls["check"] = program

    def fake_execute(program):
        calls["execute"] = program
        return 3.0

    outputs = []
    run_shell(
        read_line=_scripted_read_line(["(+ 1 2)", "exit"]),
        write_output=outputs.append,
        tokenize=fake_tokenize,
        assemble=fake_assemble,
        check=fake_check,
        execute=fake_execute,
    )
    assert outputs == ["3.0"]
    assert calls["tokenize"] == "(+ 1 2)"
    assert calls["assemble"] == ["TOKENS"]
    assert calls["check"] == "PROGRAM"
    assert calls["execute"] == "PROGRAM"


def test_pipeline_error_is_reported_and_loop_continues():
    from common import TokenizeError

    def fake_tokenize(source):
        raise TokenizeError("boom")

    outputs = []
    run_shell(
        read_line=_scripted_read_line(["bad input", "exit"]),
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


def test_multiline_expression_accumulates_until_balanced():
    calls = {}

    def fake_tokenize(source):
        calls["tokenize"] = source
        return ["TOKENS"]

    def fake_assemble(tokens):
        return "PROGRAM"

    def fake_check(program):
        pass

    def fake_execute(program):
        return 7.0

    outputs = []
    run_shell(
        read_line=_scripted_read_line(["(+ 1", "(* 2 3))", "exit"]),
        write_output=outputs.append,
        tokenize=fake_tokenize,
        assemble=fake_assemble,
        check=fake_check,
        execute=fake_execute,
    )
    assert outputs == ["7.0"]
    assert calls["tokenize"] == "(+ 1\n(* 2 3))"
