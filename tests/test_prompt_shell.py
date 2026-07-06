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
