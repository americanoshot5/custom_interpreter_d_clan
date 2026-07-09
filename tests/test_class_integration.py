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


# ── 추가 테스트 ───────────────────────────────────────────────────────────────

def test_empty_class_instantiation():
    """빈 클래스(메서드/필드 없음)도 인스턴스를 생성할 수 있다."""
    source = """
    (class Empty {})
    (var e (Empty))
    (instanceof e Empty)
    """
    assert _run(source) is True


def test_field_overwrite_updates_value():
    """필드를 set-field! 로 덮어쓰면 get-field 는 새 값을 반환한다."""
    source = """
    (class Box {
      (method init (v) {
        (set-field! This val v)
      })
      (method set (v) {
        (set-field! This val v)
      })
      (method get () {
        (return (get-field This val))
      })
    })
    (var b (Box 10))
    (b.set 20)
    (b.get)
    """
    assert _run(source) == 20.0


def test_two_instances_have_independent_fields():
    """두 인스턴스의 필드 상태는 서로 독립적이다."""
    source = """
    (class Counter {
      (method init (n) {
        (set-field! This count n)
      })
      (method inc () {
        (set-field! This count (+ (get-field This count) 1))
      })
      (method get () {
        (return (get-field This count))
      })
    })
    (var a (Counter 0))
    (var b (Counter 0))
    (a.inc)
    (a.inc)
    (a.inc)
    (b.get)
    """
    assert _run(source) == 0.0


def test_this_method_call_inside_method():
    """메서드 내부에서 (This.other) 구문으로 같은 인스턴스의 다른 메서드를 호출할 수 있다."""
    source = """
    (class Greeter {
      (method init (name) {
        (set-field! This name name)
      })
      (method get-name () {
        (return (get-field This name))
      })
      (method greet () {
        (return (+ "Hello " (This.get-name)))
      })
    })
    (var g (Greeter "World"))
    (g.greet)
    """
    assert _run(source) == "Hello World"


def test_instanceof_with_primitive_first_arg():
    """instanceof 의 첫 번째 인자가 primitive 값이면 False 를 반환한다."""
    source = """
    (class Robot {})
    (instanceof 42 Robot)
    """
    assert _run(source) is False


def test_instanceof_with_non_class_second_arg_raises():
    """instanceof 의 두 번째 인자가 클래스가 아니면 ExecuteError 를 발생시킨다."""
    source = """
    (class Robot {})
    (var r (Robot))
    (instanceof r 42)
    """
    with pytest.raises(ExecuteError, match="second argument must be a class"):
        _run(source)


def test_instanceof_multi_level_chain():
    """다단계 상속에서 instanceof 는 체인 상의 모든 조상 클래스에 대해 True 를 반환한다."""
    source = """
    (class A {})
    (class B : A {})
    (class C : B {})
    (var c (C))
    (instanceof c A)
    """
    assert _run(source) is True


def test_multi_level_inheritance_method_lookup():
    """3단계 상속에서 최상위 클래스에만 정의된 메서드를 손자 인스턴스로 호출할 수 있다."""
    source = """
    (class A {
      (method greet () {
        (return "hello from A")
      })
    })
    (class B : A {})
    (class C : B {})
    (var c (C))
    (c.greet)
    """
    assert _run(source) == "hello from A"


def test_super_with_multiple_args():
    """Super.method 호출 시 여러 인자를 올바르게 전달하고 반환값을 받는다."""
    source = """
    (class Animal {
      (method describe (adj noun) {
        (return (+ (+ "I am" adj) noun))
      })
    })
    (class Dog : Animal {
      (method speak () {
        (return (Super.describe " a " "dog"))
      })
    })
    (var d (Dog))
    (d.speak)
    """
    assert _run(source) == "I am a dog"


def test_duplicate_class_name_raises_check_error():
    """같은 스코프에서 클래스 이름을 중복 선언하면 CheckError 를 발생시킨다."""
    source = """
    (class Foo {})
    (class Foo {})
    """
    with pytest.raises(CheckError, match="already declared"):
        _run(source)


def test_method_returns_computed_value_from_multiple_fields():
    """여러 필드를 읽어 계산한 값을 반환하는 메서드가 올바르게 동작한다."""
    source = """
    (class Rectangle {
      (method init (w h) {
        (set-field! This width w)
        (set-field! This height h)
      })
      (method area () {
        (return (* (get-field This width) (get-field This height)))
      })
    })
    (var r (Rectangle 6 7))
    (r.area)
    """
    assert _run(source) == 42.0
