"""
S-expression 인터프리터의 클래스(OOP) 기능 테스트

지원 문법:
  (class Name [Parent] (field f) ... (method (name p...) body...) ...)
  (new ClassName args...)
  (. obj slot)          → 필드 읽기 or 인자 없는 메서드 호출
  (. obj slot val)      → 필드 쓰기 or 1-arg 메서드 호출
  (. obj method a b)    → 메서드 호출
  self                  → 메서드 내부에서 현재 인스턴스
  (super method args)   → 부모 메서드 호출
"""
import pytest

from Tokenizer import tokenize
from Assembler import assemble
from Checker import check
from Executor import execute
from common import AssembleError, CheckError, ExecuteError


def _run(source: str):
    tokens = tokenize(source)
    program = assemble(tokens)
    check(program)
    return execute(program)


# ── 1. 기본 정의와 인스턴스 생성 ─────────────────────────────────────────────

def test_empty_class_instantiation():
    """빈 클래스를 정의하고 인스턴스화할 수 있다."""
    _run("(class Empty) (var e (new Empty))")


def test_class_with_fields_instantiation():
    """필드를 가진 클래스를 정의하고 인스턴스화할 수 있다."""
    _run("""
    (class Point (field x) (field y))
    (var p (new Point))
    """)


def test_new_returns_non_none():
    """new 는 None 이 아닌 인스턴스를 반환한다."""
    result = _run("(class Foo) (var f (new Foo)) f")
    assert result is not None


# ── 2. 필드 읽기/쓰기 ────────────────────────────────────────────────────────

def test_field_default_is_none():
    """초기화하지 않은 필드는 None 이다."""
    result = _run("""
    (class Box (field value))
    (var b (new Box))
    (. b value)
    """)
    assert result is None


def test_field_write_then_read():
    """(. obj field val) 로 쓰고 (. obj field) 로 읽는다."""
    result = _run("""
    (class Box (field value))
    (var b (new Box))
    (. b value 42)
    (. b value)
    """)
    assert result == 42.0


def test_init_method_sets_fields():
    """new 에 전달된 인수가 init 메서드를 통해 필드에 저장된다."""
    result = _run("""
    (class Point
      (field x)
      (field y)
      (method (init px py)
        (. self x px)
        (. self y py)))
    (var p (new Point 3 4))
    (. p x)
    """)
    assert result == 3.0


def test_init_sets_second_field():
    result = _run("""
    (class Point
      (field x)
      (field y)
      (method (init px py)
        (. self x px)
        (. self y py)))
    (var p (new Point 10 20))
    (. p y)
    """)
    assert result == 20.0


def test_multiple_instances_have_independent_fields():
    """두 인스턴스의 필드는 서로 독립적이다."""
    result = _run("""
    (class Box (field value))
    (var a (new Box))
    (var b (new Box))
    (. a value 1)
    (. b value 2)
    (. a value)
    """)
    assert result == 1.0


# ── 3. 메서드 ──────────────────────────────────────────────────────────────

def test_zero_arg_method_returns_value():
    result = _run("""
    (class Counter
      (field count)
      (method (init) (. self count 0))
      (method (value) (. self count)))
    (var c (new Counter))
    (. c value)
    """)
    assert result == 0.0


def test_method_with_params():
    result = _run("""
    (class Adder
      (method (add a b) (+ a b)))
    (var a (new Adder))
    (. a add 3 4)
    """)
    assert result == 7.0


def test_method_reads_self_field():
    result = _run("""
    (class Box
      (field value)
      (method (init v) (. self value v))
      (method (doubled) (* (. self value) 2)))
    (var b (new Box 5))
    (. b doubled)
    """)
    assert result == 10.0


def test_method_modifies_field():
    result = _run("""
    (class Counter
      (field n)
      (method (init) (. self n 0))
      (method (inc) (. self n (+ (. self n) 1)))
      (method (get) (. self n)))
    (var c (new Counter))
    (. c inc)
    (. c inc)
    (. c get)
    """)
    assert result == 2.0


def test_method_prints(capsys):
    _run("""
    (class Greeter
      (field name)
      (method (init n) (. self name n))
      (method (greet) (print (. self name))))
    (var g (new Greeter "World"))
    (. g greet)
    """)
    assert capsys.readouterr().out.strip() == "World"


def test_method_returns_string():
    result = _run("""
    (class Dog
      (method (sound) "Woof"))
    (var d (new Dog))
    (. d sound)
    """)
    assert result == "Woof"


# ── 4. 상속 ───────────────────────────────────────────────────────────────

def test_child_inherits_parent_method():
    result = _run("""
    (class Animal
      (field name)
      (method (init n) (. self name n))
      (method (get-name) (. self name)))
    (class Dog Animal)
    (var d (new Dog "Rex"))
    (. d get-name)
    """)
    assert result == "Rex"


def test_child_inherits_parent_field():
    result = _run("""
    (class Vehicle (field speed))
    (class Car Vehicle (field brand))
    (var c (new Car))
    (. c speed 100)
    (. c speed)
    """)
    assert result == 100.0


def test_child_has_own_methods():
    result = _run("""
    (class Animal
      (field name)
      (method (init n) (. self name n))
      (method (type) "animal"))
    (class Dog Animal
      (method (bark) "Woof"))
    (var d (new Dog "Rex"))
    (. d bark)
    """)
    assert result == "Woof"


def test_child_can_call_parent_method():
    result = _run("""
    (class Animal
      (field name)
      (method (init n) (. self name n))
      (method (type) "animal"))
    (class Dog Animal
      (method (bark) "Woof"))
    (var d (new Dog "Rex"))
    (. d type)
    """)
    assert result == "animal"


def test_multi_level_inheritance():
    """A → B → C 3단계 상속에서 A의 메서드를 C가 호출할 수 있다."""
    result = _run("""
    (class A (method (hello) "from A"))
    (class B A)
    (class C B)
    (var c (new C))
    (. c hello)
    """)
    assert result == "from A"


# ── 5. 메서드 오버라이드 ──────────────────────────────────────────────────

def test_child_overrides_parent_method():
    result = _run("""
    (class Shape (method (area) 0))
    (class Square Shape
      (field side)
      (method (init s) (. self side s))
      (method (area) (* (. self side) (. self side))))
    (var sq (new Square 4))
    (. sq area)
    """)
    assert result == 16.0


def test_override_uses_child_version():
    result = _run("""
    (class Base (method (greet) "from base"))
    (class Child Base (method (greet) "from child"))
    (var c (new Child))
    (. c greet)
    """)
    assert result == "from child"


def test_parent_instance_uses_parent_method():
    """부모 클래스 인스턴스는 부모 메서드를 사용한다."""
    result = _run("""
    (class Base (method (greet) "from base"))
    (class Child Base (method (greet) "from child"))
    (var b (new Base))
    (. b greet)
    """)
    assert result == "from base"


# ── 6. super ──────────────────────────────────────────────────────────────

def test_super_calls_parent_method():
    result = _run("""
    (class A (method (value) 1))
    (class B A (method (value) (+ (super value) 10)))
    (var b (new B))
    (. b value)
    """)
    assert result == 11.0


def test_super_init_sets_parent_field():
    result = _run("""
    (class Animal
      (field name)
      (method (init n) (. self name n)))
    (class Dog Animal
      (field breed)
      (method (init n b)
        (super init n)
        (. self breed b)))
    (var d (new Dog "Rex" "Lab"))
    (. d name)
    """)
    assert result == "Rex"


def test_super_init_child_field_still_set():
    result = _run("""
    (class Animal
      (field name)
      (method (init n) (. self name n)))
    (class Dog Animal
      (field breed)
      (method (init n b)
        (super init n)
        (. self breed b)))
    (var d (new Dog "Rex" "Lab"))
    (. d breed)
    """)
    assert result == "Lab"


def test_super_in_override_extends_parent():
    """자식 메서드가 부모 결과를 활용할 수 있다."""
    result = _run("""
    (class Shape
      (field color)
      (method (init c) (. self color c))
      (method (info) (. self color)))
    (class Circle Shape
      (field radius)
      (method (init c r)
        (super init c)
        (. self radius r))
      (method (area) (* (. self radius) (. self radius))))
    (var ci (new Circle "red" 5))
    (. ci color)
    """)
    assert result == "red"


# ── 7. 에러 케이스 ────────────────────────────────────────────────────────

def test_new_undefined_class_raises():
    with pytest.raises((CheckError, ExecuteError)):
        _run("(new Undefined)")


def test_dot_undefined_field_raises():
    with pytest.raises(ExecuteError):
        _run("""
        (class Box (field x))
        (var b (new Box))
        (. b y)
        """)


def test_dot_on_non_instance_raises():
    with pytest.raises(ExecuteError):
        _run("""
        (var x 5)
        (. x field)
        """)


def test_method_wrong_arg_count_raises():
    with pytest.raises(ExecuteError):
        _run("""
        (class Calc (method (add a b) (+ a b)))
        (var c (new Calc))
        (. c add 1)
        """)
