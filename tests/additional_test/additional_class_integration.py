"""
3-2. class: instance, fields, methods, init, inheritance

번역 규칙은 _helpers.py 참고.
"""

from __future__ import annotations

import pytest

from common import CheckError, ExecuteError

from _helpers import run as _run


def test_class_init_fields_and_method_call(capsys):
    source = """
    (class Robot {
      (method init (name speed)
        { (set-field! This name name)
          (set-field! This speed speed)
          (set-field! This position 0) })
      (method move (dist)
        { (set-field! This position (+ (get-field This position) dist)) })
      (method report ()
        { (print (get-field This position)) })
    })
    (var r (Robot "AndOr" 10))
    (r.move 5)
    (r.report)
    """
    _run(source)
    assert capsys.readouterr().out.strip() == "5.0"


def test_class_inheritance_super_and_instanceof(capsys):
    source = """
    (class Robot {
      (method kind () { (return "robot") })
    })
    (class SpeedRobot : Robot {
      (method kind () { (return (+ (Super.kind) "-speed")) })
    })
    (var w (SpeedRobot))
    (print (w.kind))
    (print (instanceof w SpeedRobot))
    (print (instanceof w Robot))
    """
    _run(source)
    assert capsys.readouterr().out.splitlines() == ["robot-speed", "True", "True"]


def test_class_reading_missing_field_raises_execute_error():
    source = """
    (class Robot {})
    (var r (Robot))
    (print (get-field r power))
    """
    with pytest.raises(ExecuteError, match="field|property|power"):
        _run(source)


def test_this_outside_class_raises_check_error():
    with pytest.raises(CheckError, match="This.*outside class|this.*outside class"):
        _run("(print This)")


def test_init_return_value_raises_check_error():
    source = """
    (class Robot {
      (method init () { (return 5) })
    })
    """
    with pytest.raises(CheckError, match="init.*return"):
        _run(source)


def test_class_cannot_inherit_from_itself():
    with pytest.raises(CheckError, match="inherit.*itself|self inheritance"):
        _run("(class Robot : Robot {})")


def test_class_cannot_inherit_from_non_class():
    source = """
    (var x 10)
    (class Robot : x {})
    """
    with pytest.raises(CheckError, match="superclass|inherit.*class|not a class"):
        _run(source)


def test_super_outside_class_raises_check_error():
    with pytest.raises(CheckError, match="Super.*outside class|super.*outside class"):
        _run("(Super.move)")


def test_super_in_class_without_parent_raises_check_error():
    source = """
    (class Robot {
      (method move () { (Super.move) })
    })
    """
    with pytest.raises(CheckError, match="Super.*parent|superclass|without parent"):
        _run(source)


def test_field_access_on_non_instance_raises_execute_error():
    source = """
    (var x "hello")
    (set-field! x speed 10)
    """
    with pytest.raises(ExecuteError, match="instance|field|object"):
        _run(source)


def test_missing_method_call_raises_execute_error():
    source = """
    (class Robot {})
    (var r (Robot))
    (r.notExist)
    """
    with pytest.raises(ExecuteError, match="method|notExist|field"):
        _run(source)
