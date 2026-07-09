"""
3-3. static array: fixed size, indexing, runtime errors

번역 규칙은 _helpers.py 참고.
"""

from __future__ import annotations

import pytest

from common import ExecuteError

from _helpers import run as _run


def test_static_array_create_write_read_with_expression_index(capsys):
    source = """
    (var arr (Array 3))
    (set-index! arr 0 10)
    (set-index! arr 1 20)
    (set-index! arr 2 30)
    (var i 2)
    (set-index! arr (- i 1) 7)
    (print (index arr 0))
    (print (index arr 1))
    (print (index arr 2))
    """
    _run(source)
    assert capsys.readouterr().out.splitlines() == ["10.0", "7.0", "30.0"]


def test_static_array_out_of_bounds_raises_execute_error():
    source = """
    (var arr (Array 3))
    (print (index arr 5))
    """
    with pytest.raises(ExecuteError, match="index|bounds|range"):
        _run(source)


def test_static_array_non_numeric_size_raises_execute_error():
    with pytest.raises(ExecuteError, match="size|number"):
        _run('(var arr (Array "hi"))')


def test_static_array_defaults_to_null(capsys):
    source = """
    (var arr (Array 2))
    (print (index arr 0))
    (print (index arr 1))
    """
    _run(source)
    assert capsys.readouterr().out.splitlines() == ["None", "None"]


def test_static_array_non_numeric_index_raises_execute_error():
    source = """
    (var arr (Array 3))
    (print (index arr "hello"))
    """
    with pytest.raises(ExecuteError, match="index.*number|numeric index"):
        _run(source)


def test_static_array_write_out_of_bounds_raises_execute_error():
    source = """
    (var arr (Array 3))
    (set-index! arr 3 10)
    """
    with pytest.raises(ExecuteError, match="index|bounds|range"):
        _run(source)


def test_static_array_index_on_non_array_raises_execute_error():
    source = """
    (var x 10)
    (print (index x 0))
    """
    with pytest.raises(ExecuteError, match="array|index"):
        _run(source)
