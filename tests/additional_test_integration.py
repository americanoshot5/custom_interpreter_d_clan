"""
3일차 기능 추가 미션을 S-expression 문법으로 옮긴 통합 테스트.

PDF의 C-style 예시는 이 프로젝트의 기존 문법에 맞춰 다음 원칙으로 번역한다.
- 함수 선언: (func name (params...) body)
- 함수 호출: (name args...)
- 클래스 선언: (class Name { ... })
- 필드 접근: dotted name 또는 helper form (get-field/set-field!)
- 정적 배열: (Array size), (index array i), (set-index! array i value)
- import: (import "path" alias name), imported call as (alias.member args...)
"""

from __future__ import annotations

import importlib

import pytest

from Assembler import assemble
from Checker import check
from Executor import execute
from Tokenizer import tokenize
from common import CheckError, ExecuteError


def _run(source):
    tokens = tokenize(source)
    program = assemble(tokens)
    check(program)
    return execute(program)


# ============================================================
# 3-1. function: declaration, call, return, recursion, errors
# ============================================================


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


# ============================================================
# 3-2. class: instance, fields, methods, init, inheritance
# ============================================================


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


# ============================================================
# 3-3. static array: fixed size, indexing, runtime errors
# ============================================================


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


# ============================================================
# 3-4. pre-execution optimization
# ============================================================


def test_optimizer_preserves_result_for_static_binding_and_constant_folding(capsys):
    optimizer = importlib.import_module("Optimizer")
    source = """
    (var total 0)
    {
      (var a 5)
      { { { (for i 0 4
              (set! total (+ total (+ a (- (* 2 3) (/ 8 4)))))) } } }
    }
    (print total)
    """
    program = assemble(tokenize(source))
    check(program)
    optimized = optimizer.optimize(program)
    check(optimized)
    execute(optimized)
    assert capsys.readouterr().out.strip() == "36.0"


def test_optimizer_records_static_binding_distances():
    optimizer = importlib.import_module("Optimizer")
    source = """
    (var a 1)
    { { { (print a) } } }
    """
    program = assemble(tokenize(source))
    check(program)

    bindings = optimizer.resolve_bindings(program)

    assert bindings.lookup("a").distance == 3


def test_optimizer_constant_folds_literal_expression_without_runtime_calculation():
    optimizer = importlib.import_module("Optimizer")
    source = "(+ 1 (* 2 3))"
    program = assemble(tokenize(source))

    optimized = optimizer.fold_constants(program)

    assert execute(optimized) == 7.0
    assert optimizer.optimization_stats(optimized)["folded_expressions"] >= 1


# ============================================================
# 3-5. import: alias, scope, duplicate/cycle errors
# ============================================================


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


# ============================================================
# 3-6. factory control shell: file mode and debug mode
# ============================================================


def test_factory_shell_file_mode_executes_source_file(tmp_path):
    factory_shell = importlib.import_module("factory_shell")
    source_file = tmp_path / "program.cf"
    source_file.write_text("(print (+ 1 2))", encoding="utf-8")
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code == 0
    assert outputs == ["3.0"]


def test_factory_shell_file_mode_reports_missing_file(tmp_path):
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(
        str(tmp_path / "missing.cf"),
        write_output=outputs.append,
    )

    assert exit_code != 0
    assert any("not found" in line.lower() or "없" in line for line in outputs)


def test_factory_shell_prompt_mode_preserves_session_state():
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []

    exit_code = factory_shell.run_prompt_mode(
        read_line=iter(
            ["(var total 1)", "", "(set! total (+ total 2))", "", "(print total)", "", "exit"]
        ).__next__,
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert outputs[-1] == "3.0"


def test_factory_shell_file_mode_reports_runtime_error_line_and_stops(tmp_path):
    factory_shell = importlib.import_module("factory_shell")
    source_file = tmp_path / "program.cf"
    source_file.write_text(
        """
        (print 1)
        (print notDefined)
        (print 3)
        """,
        encoding="utf-8",
    )
    outputs: list[str] = []

    exit_code = factory_shell.run_file_mode(str(source_file), write_output=outputs.append)

    assert exit_code != 0
    assert any("line" in line.lower() and "3" in line for line in outputs)
    assert all("3.0" not in line for line in outputs)


def test_factory_shell_debug_mode_supports_watch_and_step():
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []
    source = """
    (var total 0)
    (set! total (+ total 1))
    (set! total (+ total 2))
    """

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["watch total", "step", "step", "watches", "continue"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("total" in line and "3.0" in line for line in outputs)


def test_factory_shell_debug_mode_supports_breakpoint_continue_and_inspect():
    factory_shell = importlib.import_module("factory_shell")
    outputs: list[str] = []
    source = """
    (var total 0)
    (set! total (+ total 1))
    (set! total (+ total 2))
    """

    exit_code = factory_shell.run_debug_mode(
        source,
        commands=["break 3", "continue", "inspect", "remove 3", "breakpoints", "continue"],
        write_output=outputs.append,
    )

    assert exit_code == 0
    assert any("total" in line and "1.0" in line for line in outputs)
    assert any("breakpoints" in line.lower() and "3" not in line for line in outputs)
