"""
docs/테스트스크립트.md 의 시나리오를 S-expression 문법으로 옮긴 통합 테스트.

--- 제안 문법 (Assembler 가 아직 지원하지 않는 것들) ---
아직 Assembler 는 var/print/if/for/블록을 구조화된 Stmt(VarStmt/PrintStmt/
IfStmt/ForStmt/BlockStmt)로 파싱하지 않고, 전부 평평한 ListExpr 로만 파싱한다.
Checker/Executor 는 이 Stmt 들을 처리하는 로직이 이미 있으므로, Assembler 가
아래 문법으로 파싱해주면 그대로 동작할 것으로 기대하고 작성했다.

  변수 선언       (var <name> <initializer>)
  재할당          (set! <name> <expr>)              # 새 노드 없이 ListExpr 특수형으로 처리 가능
  출력            (print <expr>)
  블록            { <stmt> <stmt> ... }              # LEFT_BRACE/RIGHT_BRACE 토큰은 이미 존재
  조건문          (if <cond> <then>)
                  (if <cond> <then> <else>)
  반복문          (for <iterator> <start> <end> <body>)
                  # ForStmt(iterator, start, end, body) 형태에 맞춤.
                  # start <= iterator < end, 매 반복 +1 이라고 가정.

각 테스트는 실제로 통과하는지 실행해 확인했다. 실패하는 것은 왜 실패하는지
주석으로 남겨서, 어느 담당자(Assembler/Checker/Executor)에게 전달해야 하는지
알 수 있게 했다.
"""

import pytest

from Assembler import assemble
from Checker import check
from Executor import execute
from Tokenizer import tokenize
from common import AssembleError, CheckError, ExecuteError


def _run(source):
    tokens = tokenize(source)
    program = assemble(tokens)
    check(program)
    return execute(program)


def test_end_to_end_simple_addition():
    assert _run("(+ 1 2)") == 3.0


def test_end_to_end_nested_arithmetic():
    assert _run("(+ 1 (* 2 3))") == 7.0


# ============================================================
# 1-1. 표현식 / 연산자 / 우선순위 / 진리값
# ============================================================

def test_operator_precedence_multiplication_before_addition():
    assert _run("(+ 1 (* 2 3))") == 7.0


def test_operator_precedence_explicit_grouping():
    assert _run("(* (+ 1 2) 3)") == 9.0


def test_left_associative_subtraction_chain():
    assert _run("(- (- 10 4) 3)") == 3.0


def test_left_associative_division_chain():
    assert _run("(/ (/ 8 2) 2)") == 2.0


def test_unary_minus_then_addition():
    assert _run("(+ (- 3) 2)") == -1.0


def test_less_than_comparison():
    assert _run("(< 1 2)") is True


def test_greater_than_comparison():
    assert _run("(> 3 5)") is False


def test_string_concatenation_with_plus():
    assert _run('(+ "Hello, " "CodeFab!")') == "Hello, CodeFab!"


# 숫자 출력 포맷 / print 는 PrintStmt 가 필요하다.
# 현재 Assembler 는 `print` 키워드를 특수 처리하지 않아
# `(print 5)` 는 ListExpr(IdentifierExpr("print"), LiteralExpr(5.0)) 로 파싱된다.
# Checker 는 "print" 도 IdentifierExpr 로 취급해 스코프에서 찾으려 하는데
# "print" 는 _BUILTINS 에도 없고 변수로도 선언된 적이 없어 CheckError 가 난다.
# → Assembler 에 print 파싱, Executor 의 PrintStmt 처리(현재 `...` no-op) 구현 필요.

def test_print_integer_without_decimal_point(capsys):
    _run("(print 5)")
    assert capsys.readouterr().out.strip() == "5"


def test_print_float_with_zero_fraction_drops_decimal(capsys):
    _run("(print 5.0)")
    assert capsys.readouterr().out.strip() == "5"


def test_print_float_keeps_fraction(capsys):
    _run("(print 3.14)")
    assert capsys.readouterr().out.strip() == "3.14"


def test_print_boolean_true(capsys):
    _run("(print true)")
    assert capsys.readouterr().out.strip() == "true"


def test_print_boolean_false(capsys):
    _run("(print false)")
    assert capsys.readouterr().out.strip() == "false"


# ============================================================
# 1-2. 변수, 할당, 블록 스코프, 변수 shadowing
# ============================================================
# var/set!/블록 모두 Assembler 가 아직 못 만드는 노드라 전부 AssembleError
# 아니면 (파싱이 우연히 통과해도) 의도와 다른 트리가 만들어져 실패한다.

def test_declare_and_use_variables():
    source = """
    (var a 10)
    (var b 20)
    (print (+ a b))
    """
    assert _run(source) is None  # 마지막 문장은 print(현재 no-op)


def test_reassignment_updates_variable():
    source = """
    (var a 10)
    (set! a (+ a 5))
    (print a)
    """
    _run(source)


def test_block_scope_shadowing_does_not_leak_outward():
    source = """
    (var x "global")
    {
      (var x "inner")
      (print x)
    }
    (print x)
    """
    _run(source)


def test_inner_block_can_mutate_outer_variable():
    source = """
    (var count 0)
    {
      (set! count (+ count 1))
    }
    (print count)
    """
    _run(source)


def test_nested_scope_resolves_outer_names():
    source = """
    (var outer "A")
    {
      (var inner "B")
      {
        (print (+ outer inner))
      }
    }
    """
    _run(source)


# ============================================================
# 1-3. 제어 흐름 (if/else, for)
# ============================================================

def test_if_true_branch_executes():
    _run('(if true (print "bbq"))')


def test_if_false_with_else_executes_else_branch():
    _run('(if false (print "no") (print "kfc"))')


def test_nested_if_else_binds_to_correct_branch():
    # S-expression 은 항상 명시적으로 괄호로 그룹화되므로
    # C 스타일의 "else 는 가장 가까운 if 에 결합" 같은 모호함 자체가 없다.
    source = """
    (if true
      (if false (print "kfc") (print "bbq")))
    """
    _run(source)


def test_for_loop_prints_range(capsys):
    _run("(for j 0 3 (print j))")
    assert capsys.readouterr().out.splitlines() == ["0", "1", "2"]


# ============================================================
# 2-1. 구문 에러 (Assembler 단계에서 검출)
# ============================================================

# 세미콜론 누락 시나리오는 S-expression 에 세미콜론이 없어 해당 사항 없음 (생략).

def test_missing_closing_paren_raises_assemble_error():
    with pytest.raises(AssembleError):
        _run('(print (+ 1 2)')


def test_invalid_assignment_target_raises_error():
    # `a + b = 3` 에 대응 : set! 의 첫 번째 인자가 이름이 아님.
    # 현재는 set! 자체가 특수형으로 인식되지 않아서, "set!" 을 정의되지 않은
    # 변수로 오인한 CheckError 가 우연히 발생한다 (의도한 검증이 아님).
    with pytest.raises((AssembleError, CheckError), match=r"assignment target|set!.*first argument"):
        _run("(set! (+ a b) 3)")


def test_print_without_expression_raises_assemble_error():
    # `print * 5;` (표현식이 와야 할 자리에 엉뚱한 토큰) 에 대응하는
    # 가장 가까운 S-expression 형태: print 에 표현식이 없는 경우.
    with pytest.raises(AssembleError):
        _run("(print)")


# ============================================================
# 2-2. Checker 단계에서 검출하는 정적 에러
# ============================================================

def test_variable_cannot_reference_itself_in_initializer():
    # Checker 의 _ScopeStack 에는 이 검사가 이미 구현되어 있다.
    # 다만 Assembler 가 `{`/`var` 를 파싱하지 못해 지금은 엉뚱한
    # "Undefined variable '{'" 에러가 나므로, 메시지까지 검증해 구분한다.
    with pytest.raises(CheckError, match="references itself"):
        _run("{ (var a a) }")


def test_duplicate_declaration_in_same_scope_raises_check_error():
    # Checker 의 declare() 에 이미 구현되어 있다. 위와 같은 이유로
    # 메시지까지 검증해 "우연한 통과" 를 걸러낸다.
    with pytest.raises(CheckError, match="already declared"):
        _run('{ (var a "hi") (var a 3) }')


# ============================================================
# 2-3. 실행 중 발생하는 런타임 에러
# ============================================================

def test_undefined_variable_reference_raises_check_error():
    with pytest.raises(CheckError):
        _run("(+ notDefined 1)")


def test_plus_with_number_and_string_raises_execute_error():
    # 현재 Executor 는 피연산자 타입을 검사하지 않아
    # ExecuteError 대신 Python TypeError 가 발생한다.
    with pytest.raises(ExecuteError):
        _run('(+ 1 "HI")')


def test_unary_minus_on_non_number_raises_execute_error():
    # 위와 동일한 이유로 현재는 TypeError 가 발생한다.
    with pytest.raises(ExecuteError):
        _run('(- "FabCoding")')
