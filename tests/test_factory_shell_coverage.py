"""
factory_shell.py 커버리지 보강 테스트

미싱 라인:
  30   FileModeExecutor._execute_stmt — RuntimeExecutionError 재-raise
  38   DebugCommand.execute — NotImplementedError
 178   _remove_breakpoint — 잘못된 인수 시 return False
 186-187 _parse_line_arg — ValueError (비정수 줄 번호)
 261-262 _step — 이미 완료된 프로그램에서 step
 310-312 run_file_mode — OSError
 316-318 run_file_mode — LanguageError (컴파일 에러)
 341-343 run_debug_mode — LanguageError
 353-381 run_interactive_debug_mode — 전체
 400-401 run_prompt_mode — EOFError
     408 run_prompt_mode — 빈 줄을 버퍼 비어있는 상태에서 continue
 439-502 run_game_mode — 전체
     521 main — 인수 없음
 525-528 main — debug/play 모드
     538 main — 하위 호환 fallback
"""
from __future__ import annotations

import pytest
from unittest import mock

from common import (
    BlockStmt,
    ExpressionStmt,
    IdentifierExpr,
    LiteralExpr,
    ListExpr,
    Program,
    SourceLocation,
)
import factory_shell
from factory_shell import (
    DebugCommand,
    DebugSession,
    FileModeExecutor,
    RuntimeExecutionError,
    run_debug_mode,
    run_file_mode,
    run_interactive_debug_mode,
    run_game_mode,
    run_prompt_mode,
    main,
    _run_pipeline,
)


# ── FileModeExecutor ────────────────────────────────────────────────────────

def test_file_mode_executor_reraises_inner_runtime_error():
    """BlockStmt 내부에서 발생한 RuntimeExecutionError는 재-raise된다 (이중 래핑 방지)."""
    executor = FileModeExecutor()
    # 내부 문: 0으로 나누기 → ZeroDivisionError → RuntimeExecutionError
    inner = ExpressionStmt(
        ListExpr((IdentifierExpr("/"), LiteralExpr(1.0), LiteralExpr(0.0))),
        location=SourceLocation(line=2),
    )
    block = BlockStmt((inner,), location=SourceLocation(line=1))
    with pytest.raises(RuntimeExecutionError) as exc_info:
        executor.execute(Program((block,)))
    assert exc_info.value.line == 2  # 내부에서 래핑된 줄 번호 보존


# ── DebugCommand 기본 클래스 ────────────────────────────────────────────────

def test_debug_command_base_raises_not_implemented():
    """DebugCommand.execute() 기본 구현은 NotImplementedError를 발생시킨다."""
    with pytest.raises(NotImplementedError):
        DebugCommand().execute(None)  # type: ignore[arg-type]


# ── DebugSession — 잘못된 명령 인수 ────────────────────────────────────────

def _make_session(source: str) -> tuple[DebugSession, list[str]]:
    program = _run_pipeline(source)
    outputs: list[str] = []
    return DebugSession(program, outputs.append), outputs


def test_debug_session_remove_breakpoint_wrong_arg_count():
    """'remove 1 2' (인수 두 개) → _parse_line_arg len != 2 → Usage 메시지 + run 이 1 반환."""
    session, outputs = _make_session("(var x 1)")
    result = session.run(["remove 1 2"])  # startswith("remove ") → RemoveBreakpointDebugCommand
    assert result == 1
    assert any("usage" in line.lower() for line in outputs)


def test_debug_session_break_non_integer_returns_error():
    """'break abc' → int() ValueError → 에러 메시지 출력 후 run 이 1 반환."""
    session, outputs = _make_session("(var x 1)")
    result = session.run(["break abc"])
    assert result == 1
    assert any("invalid" in line.lower() for line in outputs)


def test_debug_session_remove_non_integer_returns_error():
    """'remove xyz' → int() ValueError → 에러 메시지 출력 후 run 이 1 반환."""
    session, outputs = _make_session("(var x 1)")
    result = session.run(["remove xyz"])
    assert result == 1
    assert any("invalid" in line.lower() for line in outputs)


# ── DebugSession — _step 이미 완료된 경우 ───────────────────────────────────

def test_debug_session_step_on_finished_program():
    """프로그램이 끝난 후 step 명령 → 'Program finished' 메시지 + 정상 종료."""
    session, outputs = _make_session("(print 1)")
    result = session.run(["step", "step", "step"])
    assert result == 0
    finished_msgs = [line for line in outputs if "finished" in line.lower()]
    assert len(finished_msgs) >= 2  # 완료 후 step 때도 출력


# ── run_file_mode ───────────────────────────────────────────────────────────

def test_run_file_mode_oserror():
    """파일 읽기 OSError → 에러 메시지 출력 후 exit code 1."""
    outputs: list[str] = []
    mock_path = mock.MagicMock()
    mock_path.read_text.side_effect = OSError("disk error")

    with mock.patch("factory_shell.Path", return_value=mock_path):
        exit_code = run_file_mode("/fake/path.cf", write_output=outputs.append)

    assert exit_code == 1
    assert any("disk error" in line for line in outputs)


def test_run_file_mode_language_error(tmp_path):
    """구문 에러가 있는 파일 → LanguageError → 에러 메시지 + exit code 1."""
    source_file = tmp_path / "bad.cf"
    source_file.write_text("(var", encoding="utf-8")  # 닫히지 않은 괄호
    outputs: list[str] = []

    exit_code = run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code == 1
    assert any("error" in line.lower() for line in outputs)


# ── run_debug_mode ──────────────────────────────────────────────────────────

def test_run_debug_mode_language_error():
    """구문 에러가 있는 소스 → LanguageError → 에러 메시지 + exit code 1."""
    outputs: list[str] = []

    exit_code = run_debug_mode("(var", commands=["step"], write_output=outputs.append)

    assert exit_code == 1
    assert any("error" in line.lower() for line in outputs)


# ── run_interactive_debug_mode ──────────────────────────────────────────────

def test_interactive_debug_file_not_found(tmp_path):
    """존재하지 않는 파일 → 에러 메시지 + exit code 1."""
    outputs: list[str] = []

    exit_code = run_interactive_debug_mode(
        str(tmp_path / "missing.cf"),
        read_line=lambda _: "exit",
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert any("not found" in line.lower() for line in outputs)


def test_interactive_debug_language_error(tmp_path):
    """구문 에러 파일 → LanguageError → 에러 메시지 + exit code 1."""
    source_file = tmp_path / "bad.cf"
    source_file.write_text("(var", encoding="utf-8")
    outputs: list[str] = []

    exit_code = run_interactive_debug_mode(
        str(source_file),
        read_line=lambda _: "exit",
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert any("error" in line.lower() for line in outputs)


def test_interactive_debug_oserror():
    """파일 읽기 OSError → 에러 메시지 + exit code 1."""
    outputs: list[str] = []
    mock_path = mock.MagicMock()
    mock_path.read_text.side_effect = OSError("disk error")

    with mock.patch("factory_shell.Path", return_value=mock_path):
        exit_code = run_interactive_debug_mode(
            "/fake/path.cf",
            read_line=lambda _: "exit",
            write_output=outputs.append,
        )

    assert exit_code == 1
    assert any("disk error" in line for line in outputs)


def test_interactive_debug_eoferror(tmp_path):
    """read_line 에서 EOFError → 정상 종료 (exit code 0)."""
    source_file = tmp_path / "prog.cf"
    source_file.write_text("(print 1)", encoding="utf-8")
    outputs: list[str] = []

    def raise_eof(prompt: str) -> str:
        raise EOFError

    exit_code = run_interactive_debug_mode(
        str(source_file),
        read_line=raise_eof,
        write_output=outputs.append,
    )

    assert exit_code == 0


def test_interactive_debug_exit_command(tmp_path):
    """'exit' 명령어 → 정상 종료."""
    source_file = tmp_path / "prog.cf"
    source_file.write_text("(print 1)", encoding="utf-8")
    outputs: list[str] = []
    lines = iter(["exit"])

    exit_code = run_interactive_debug_mode(
        str(source_file),
        read_line=lambda _: next(lines),
        write_output=outputs.append,
    )

    assert exit_code == 0


def test_interactive_debug_quit_command(tmp_path):
    """'quit' 명령어 → 정상 종료."""
    source_file = tmp_path / "prog.cf"
    source_file.write_text("(var x 1)", encoding="utf-8")
    lines = iter(["quit"])

    exit_code = run_interactive_debug_mode(
        str(source_file),
        read_line=lambda _: next(lines),
        write_output=[].append,
    )

    assert exit_code == 0


def test_interactive_debug_empty_command_skipped(tmp_path):
    """빈 명령어는 무시하고 다음 명령어를 처리한다."""
    source_file = tmp_path / "prog.cf"
    source_file.write_text("(var x 1)", encoding="utf-8")
    lines = iter(["", "exit"])

    exit_code = run_interactive_debug_mode(
        str(source_file),
        read_line=lambda _: next(lines),
        write_output=[].append,
    )

    assert exit_code == 0


def test_interactive_debug_step_then_exit(tmp_path):
    """step 후 exit → 정상 실행."""
    source_file = tmp_path / "prog.cf"
    source_file.write_text("(var x 1)\n(var y 2)", encoding="utf-8")
    outputs: list[str] = []
    lines = iter(["step", "exit"])

    exit_code = run_interactive_debug_mode(
        str(source_file),
        read_line=lambda _: next(lines),
        write_output=outputs.append,
    )

    assert exit_code == 0


def test_interactive_debug_unknown_command_exits_nonzero(tmp_path):
    """알 수 없는 명령어 → run이 1 반환 → interactive loop 종료."""
    source_file = tmp_path / "prog.cf"
    source_file.write_text("(var x 1)", encoding="utf-8")
    lines = iter(["badcommand"])

    exit_code = run_interactive_debug_mode(
        str(source_file),
        read_line=lambda _: next(lines),
        write_output=[].append,
    )

    assert exit_code == 1


# ── run_prompt_mode ─────────────────────────────────────────────────────────

def test_run_prompt_mode_eoferror():
    """read_line 에서 EOFError → 정상 종료 (exit code 0)."""
    def raise_eof() -> str:
        raise EOFError

    exit_code = run_prompt_mode(read_line=raise_eof, write_output=[].append)

    assert exit_code == 0


def test_run_prompt_mode_empty_line_while_buffer_empty():
    """버퍼가 비어있을 때 빈 줄 → 무시하고 계속 진행."""
    outputs: list[str] = []
    lines = iter(["", "exit"])

    exit_code = run_prompt_mode(
        read_line=lambda: next(lines),
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs == []  # 아무것도 출력되지 않아야 한다


def test_run_prompt_mode_continuation_prompt():
    """첫 줄을 버퍼에 쌓은 후 두 번째 루프에서 continuation_prompt가 호출된다."""
    prompts: list[str] = []
    # "(var x" → buffer에 쌓임, 두 번째 루프에서 continuation_prompt
    # "" → buffer 실행, 세 번째 루프에서 다시 prompt
    # "exit" → 종료
    lines = iter(["(var x", "1)", "", "exit"])

    run_prompt_mode(
        read_line=lambda: next(lines),
        write_output=[].append,
        on_prompt=prompts.append,
        prompt=">>> ",
        continuation_prompt="... ",
    )

    assert "... " in prompts  # 버퍼가 찼을 때 continuation_prompt가 전달된다


# ── run_game_mode ───────────────────────────────────────────────────────────

def test_game_mode_file_not_found(tmp_path):
    """존재하지 않는 파일 → exit code 1."""
    outputs: list[str] = []

    exit_code = run_game_mode(
        str(tmp_path / "missing.cf"),
        read_line=lambda: "exit",
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert any("not found" in line.lower() for line in outputs)


def test_game_mode_oserror():
    """파일 읽기 OSError → exit code 1."""
    outputs: list[str] = []
    mock_path = mock.MagicMock()
    mock_path.read_text.side_effect = OSError("disk error")

    with mock.patch("factory_shell.Path", return_value=mock_path):
        exit_code = run_game_mode(
            "/fake/game.cf",
            read_line=lambda: "exit",
            write_output=outputs.append,
        )

    assert exit_code == 1
    assert any("disk error" in line for line in outputs)


def test_game_mode_language_error_in_preload(tmp_path):
    """프리로드 파일에 구문 에러 → exit code 1."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var", encoding="utf-8")
    outputs: list[str] = []

    exit_code = run_game_mode(
        str(source_file),
        read_line=lambda: "exit",
        write_output=outputs.append,
    )

    assert exit_code == 1
    assert any("error" in line.lower() for line in outputs)


def test_game_mode_exit_command(tmp_path):
    """'exit' 명령어 → 정상 종료."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var score 0)", encoding="utf-8")

    exit_code = run_game_mode(
        str(source_file),
        read_line=lambda: "exit",
        write_output=[].append,
    )

    assert exit_code == 0


def test_game_mode_eoferror(tmp_path):
    """read_line EOFError → 정상 종료."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var score 0)", encoding="utf-8")

    def raise_eof() -> str:
        raise EOFError

    exit_code = run_game_mode(
        str(source_file),
        read_line=raise_eof,
        write_output=[].append,
    )

    assert exit_code == 0


def test_game_mode_balanced_expr_executes_immediately(tmp_path):
    """균형 잡힌 단일 표현식은 빈 줄 없이 즉시 실행된다."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var score 0)", encoding="utf-8")
    outputs: list[str] = []
    lines = iter(["(+ 1 2)", "exit"])

    run_game_mode(
        str(source_file),
        read_line=lambda: next(lines),
        write_output=outputs.append,
    )

    assert "3.0" in outputs or any("3" in line for line in outputs)


def test_game_mode_empty_line_skipped_when_buffer_empty(tmp_path):
    """버퍼가 비어있을 때 빈 줄은 무시된다."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var x 1)", encoding="utf-8")
    outputs: list[str] = []
    lines = iter(["", "exit"])

    exit_code = run_game_mode(
        str(source_file),
        read_line=lambda: next(lines),
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs == []


def test_game_mode_multiline_input(tmp_path):
    """여러 줄 입력은 버퍼에 쌓인 후 빈 줄에 실행된다."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var total 0)", encoding="utf-8")
    outputs: list[str] = []
    lines = iter(["(set! total", "(+ total 5))", "", "exit"])

    run_game_mode(
        str(source_file),
        read_line=lambda: next(lines),
        write_output=outputs.append,
    )

    # set! returns 5.0 (the assigned value)
    assert any("5" in line for line in outputs)


def test_game_mode_run_language_error_restores_checker(tmp_path):
    """_run 중 LanguageError → checker 상태가 checkpoint로 복원된다."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var x 0)", encoding="utf-8")
    outputs: list[str] = []
    # undefined variable → CheckError (LanguageError)
    # (+ x 0) returns 0.0 → write_output("0.0") so we can assert
    lines = iter(["(print undefined_var)", "(+ x 0)", "exit"])

    exit_code = run_game_mode(
        str(source_file),
        read_line=lambda: next(lines),
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("error" in line.lower() for line in outputs)
    # checker가 복원되었으므로 x는 여전히 유효 → (+ x 0) = 0.0
    assert any("0" in line for line in outputs)


def test_game_mode_run_returns_non_none_result(tmp_path):
    """_run 결과가 None이 아니면 출력된다."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var n 10)", encoding="utf-8")
    outputs: list[str] = []
    lines = iter(["(+ n 5)", "exit"])

    run_game_mode(
        str(source_file),
        read_line=lambda: next(lines),
        write_output=outputs.append,
    )

    assert any("15" in line for line in outputs)


def test_game_mode_on_prompt_continuation(tmp_path):
    """버퍼가 찼을 때 on_prompt에 continuation prompt("...  ")가 전달된다."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var x 0)", encoding="utf-8")
    prompts: list[str] = []
    lines = iter(["(set! x", "1)", "", "exit"])

    run_game_mode(
        str(source_file),
        read_line=lambda: next(lines),
        write_output=[].append,
        on_prompt=prompts.append,
    )

    assert "...  " in prompts  # 버퍼가 찼을 때의 continuation prompt


# ── main ────────────────────────────────────────────────────────────────────

def test_main_no_args(capsys):
    """인수 없음 → usage 출력 + exit code 2."""
    exit_code = main([])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_main_prompt_mode_on_prompt_called():
    """main(['prompt']) → run_prompt_mode 호출, on_prompt 내부 print 실행 (line 521)."""
    with mock.patch("builtins.input", side_effect=EOFError), \
         mock.patch("builtins.print"):
        exit_code = main(["prompt"])
    assert exit_code == 0


def test_main_debug_mode_file_not_found(tmp_path):
    """main(['debug', 'missing.cf']) → run_interactive_debug_mode 호출 → exit code 1."""
    exit_code = main(["debug", str(tmp_path / "missing.cf")])

    assert exit_code == 1


def test_main_play_mode_file_not_found(tmp_path):
    """main(['play', 'missing.cf']) → run_game_mode 호출 → exit code 1."""
    exit_code = main(["play", str(tmp_path / "missing.cf")])

    assert exit_code == 1


def test_main_play_mode_on_prompt_called(tmp_path):
    """main(['play', existing_file]) → on_prompt_play 함수가 실제 호출된다 (line 526)."""
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var score 0)", encoding="utf-8")
    with mock.patch("builtins.input", return_value="exit"), \
         mock.patch("builtins.print") as mock_print:
        exit_code = main(["play", str(source_file)])
    assert exit_code == 0
    mock_print.assert_any_call("game> ", end="", flush=True)


def test_main_fallback_run_file_not_found(tmp_path):
    """main(['missing.cf']) → 하위 호환 fallback으로 run_file_mode 호출 → exit code 1."""
    exit_code = main([str(tmp_path / "missing.cf")])

    assert exit_code == 1


def test_main_invalid_mode(capsys):
    """알 수 없는 모드 + 파일 인수 → usage 출력 + exit code 2."""
    exit_code = main(["badmode", "somefile.cf"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


# ── Optimizer 파이프라인 통합 ────────────────────────────────────────────────
# Optimizer.optimize()가 구현만 되고 실제 실행 경로(run_file_mode 등)에
# 연결이 안 되어 있던 회귀를 방지하기 위한 테스트. 각 실행 경로에서
# optimize()가 실제로 호출되는지, 그리고 상수 접기 결과가 정상적으로
# 실행에 반영되는지를 확인한다.

def test_run_file_mode_calls_optimize(tmp_path):
    source_file = tmp_path / "program.cf"
    source_file.write_text("(print (+ 1 (* 2 3)))", encoding="utf-8")
    outputs: list[str] = []

    with mock.patch("factory_shell.optimize", wraps=factory_shell.optimize) as spy:
        exit_code = run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code == 0
    assert outputs == ["7.0"]
    spy.assert_called_once()


def test_run_debug_mode_calls_optimize():
    outputs: list[str] = []

    with mock.patch("factory_shell.optimize", wraps=factory_shell.optimize) as spy:
        exit_code = run_debug_mode(
            "(print (+ 1 (* 2 3)))",
            commands=["continue"],
            write_output=outputs.append,
        )

    assert exit_code == 0
    spy.assert_called_once()


def test_run_prompt_mode_calls_optimize():
    outputs: list[str] = []
    lines = iter(["(+ 1 (* 2 3))", "", "exit"])

    with mock.patch("factory_shell.optimize", wraps=factory_shell.optimize) as spy:
        exit_code = run_prompt_mode(read_line=lambda: next(lines), write_output=outputs.append)

    assert exit_code == 0
    assert outputs == ["7.0"]
    spy.assert_called_once()


def test_run_game_mode_calls_optimize_for_preload_and_each_command(tmp_path):
    source_file = tmp_path / "game.cf"
    source_file.write_text("(var total 0)", encoding="utf-8")
    outputs: list[str] = []
    lines = iter(["(+ 1 (* 2 3))", "", "exit"])

    with mock.patch("factory_shell.optimize", wraps=factory_shell.optimize) as spy:
        exit_code = run_game_mode(
            str(source_file),
            read_line=lambda: next(lines),
            write_output=outputs.append,
        )

    assert exit_code == 0
    assert outputs == ["7.0"]
    # 1회: 프리로드, 1회: REPL에서 입력한 식
    assert spy.call_count == 2
