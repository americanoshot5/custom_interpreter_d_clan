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
