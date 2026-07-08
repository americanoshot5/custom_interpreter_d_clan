"""
3-5. import: alias, scope, duplicate/cycle errors

번역 규칙은 _helpers.py 참고.
"""

from __future__ import annotations

import pytest

from common import CheckError

from _helpers import run as _run


def test_import_file_alias_and_call_imported_function(tmp_path, capsys):
    lib = tmp_path / "sum.cf"
    lib.write_text(
        """
        (func add (a b)
          { (return (+ a b)) })
        """,
        encoding="utf-8",
    )
    source = f"""
    (import "{lib}" alias sum)
    (print (sum.add 1 2))
    """
    _run(source)
    assert capsys.readouterr().out.strip() == "3.0"


def test_import_cycle_raises_check_error(tmp_path):
    a = tmp_path / "a.cf"
    b = tmp_path / "b.cf"
    a.write_text(f'(import "{b}" alias b)', encoding="utf-8")
    b.write_text(f'(import "{a}" alias a)', encoding="utf-8")

    with pytest.raises(CheckError, match="cycle|circular|순환"):
        _run(f'(import "{a}" alias a)')


def test_import_path_must_be_string_literal():
    with pytest.raises(CheckError, match="import.*string|path.*literal"):
        _run("(import sum.cf alias sum)")


def test_import_missing_file_raises_check_error(tmp_path):
    missing = tmp_path / "missing.cf"
    with pytest.raises(CheckError, match="not found|missing|없"):
        _run(f'(import "{missing}" alias missing)')


def test_import_same_file_twice_in_same_scope_raises_check_error(tmp_path):
    lib = tmp_path / "sum.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    source = f"""
    (import "{lib}" alias sum)
    (import "{lib}" alias sumAgain)
    """
    with pytest.raises(CheckError, match="duplicate import|already imported"):
        _run(source)


def test_import_alias_collision_raises_check_error(tmp_path):
    lib = tmp_path / "sum.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    source = f"""
    (var sum 0)
    (import "{lib}" alias sum)
    """
    with pytest.raises(CheckError, match="alias|already declared|collision"):
        _run(source)


def test_imported_alias_is_scoped_to_import_block(tmp_path):
    lib = tmp_path / "sum.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    source = f"""
    {{
      (import "{lib}" alias sum)
      (print sum.answer)
    }}
    (print sum.answer)
    """
    with pytest.raises(CheckError, match="scope|alias.*sum|sum\\.answer"):
        _run(source)


def test_import_inside_for_loop_raises_check_error(tmp_path):
    lib = tmp_path / "sum.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    source = f"""
    (for i 0 1
      (import "{lib}" alias sum))
    """
    with pytest.raises(CheckError, match="import.*for|loop"):
        _run(source)
