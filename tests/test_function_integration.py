"""
3-1. function: declaration, call, return, recursion, errors

번역 규칙은 _helpers.py 참고.
"""

from __future__ import annotations

import pytest

from common import CheckError, ExecuteError

from _helpers import run as _run


def test_function_declaration_call_and_return_value(capsys):
    source = """
    (func add (a b)
      { (return (+ a b)) })
    (var ret (add 3 7))
    (print ret)
    """
    _run(source)
    assert capsys.readouterr().out.strip() == "10.0"


def test_recursive_function_factorial(capsys):
    source = """
    (func fact (n)
      { (if (< n 2)
          (return 1)
          (return (* n (fact (- n 1))))) })
    (print (fact 5))
    """
    _run(source)
    assert capsys.readouterr().out.strip() == "120.0"


def test_return_outside_function_raises_check_error():
    with pytest.raises(CheckError, match="return.*outside function"):
        _run("(return 5)")


def test_function_duplicate_parameter_name_raises_check_error():
    source = """
    (func bad (a a)
      { (return a) })
    """
    with pytest.raises(CheckError, match="parameter|duplicate|already declared"):
        _run(source)


def test_calling_non_function_value_raises_execute_error():
    source = """
    (var x "hello")
    (x)
    """
    with pytest.raises(ExecuteError, match="not callable|function|call"):
        _run(source)


def test_return_without_value_returns_null(capsys):
    source = """
    (func noop ()
      { (return) })
    (print (noop))
    """
    _run(source)
    assert capsys.readouterr().out.strip() == "None"


def test_function_call_argument_count_mismatch_raises_execute_error():
    source = """
    (func add3 (a b c)
      { (return (+ (+ a b) c)) })
    (add3 1 2)
    """
    with pytest.raises(ExecuteError, match="argument|arity|parameter"):
        _run(source)
