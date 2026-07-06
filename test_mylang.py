"""
mylang 인터프리터 테스트 스위트 (pytest)

계층별 / 기능별로 구성:
  1. 토큰화 (tokenize)
  2. 파싱 (parse / parse_program)
  3. atom 변환
  4. 산술 / 비교 / 논리 연산
  5. 변수 (define)
  6. 조건문 (if)
  7. 반복문 (for)
  8. 함수 (lambda) 와 클로저
  9. 재귀
 10. begin / 스코프
 11. 문자열
 12. 통합 프로그램
 13. 에러 케이스

실행:  pytest test_mylang.py -v
"""

import pytest
from mylang import (
    tokenize, parse, parse_program, atom, run,
    make_global_env, eval_node, Str, Function, Env,
)


# 헬퍼: 소스 코드를 파싱 -> 평가하고 마지막 값을 돌려준다
def evaluate(src):
    return run(src)


# ---------------------------------------------------------------------------
# 1. 토큰화
# ---------------------------------------------------------------------------
class TestTokenize:
    def test_simple(self):
        assert tokenize("(+ 1 2)") == ["(", "+", "1", "2", ")"]

    def test_nested(self):
        assert tokenize("(+ 1 (* 2 3))") == \
            ["(", "+", "1", "(", "*", "2", "3", ")", ")"]

    def test_extra_whitespace(self):
        assert tokenize("(  +   1    2 )") == ["(", "+", "1", "2", ")"]

    def test_newlines_and_tabs(self):
        assert tokenize("(+\n\t1\n2)") == ["(", "+", "1", "2", ")"]

    def test_string_literal_kept_whole(self):
        assert tokenize('(print "hello world")') == \
            ["(", "print", '"hello world"', ")"]

    def test_string_with_parens_inside(self):
        # 문자열 안의 괄호는 분리되면 안 된다
        assert tokenize('(print "a(b)c")') == ["(", "print", '"a(b)c"', ")"]

    def test_empty(self):
        assert tokenize("") == []

    def test_atoms_touching_parens(self):
        assert tokenize("(f)(g)") == ["(", "f", ")", "(", "g", ")"]


# ---------------------------------------------------------------------------
# 2. 파싱
# ---------------------------------------------------------------------------
class TestParse:
    def test_flat(self):
        assert parse(tokenize("(+ 1 2)")) == ["+", 1, 2]

    def test_nested(self):
        assert parse(tokenize("(+ 1 (* 2 3))")) == ["+", 1, ["*", 2, 3]]

    def test_single_atom(self):
        assert parse(tokenize("42")) == 42

    def test_empty_list(self):
        assert parse(tokenize("()")) == []

    def test_deeply_nested(self):
        assert parse(tokenize("(a (b (c (d))))")) == \
            ["a", ["b", ["c", ["d"]]]]

    def test_program_multiple_exprs(self):
        exprs = parse_program("(define x 1) (define y 2)")
        assert exprs == [["define", "x", 1], ["define", "y", 2]]

    def test_unclosed_paren_raises(self):
        with pytest.raises(SyntaxError):
            parse(tokenize("(+ 1 2"))

    def test_unexpected_close_raises(self):
        with pytest.raises(SyntaxError):
            parse(tokenize(")"))

    def test_empty_input_raises(self):
        with pytest.raises(SyntaxError):
            parse([])


# ---------------------------------------------------------------------------
# 3. atom 변환
# ---------------------------------------------------------------------------
class TestAtom:
    def test_int(self):
        assert atom("42") == 42 and isinstance(atom("42"), int)

    def test_negative_int(self):
        assert atom("-5") == -5

    def test_float(self):
        assert atom("3.14") == 3.14 and isinstance(atom("3.14"), float)

    def test_symbol(self):
        assert atom("foo") == "foo"

    def test_operator_symbol(self):
        assert atom("+") == "+"

    def test_string_literal(self):
        result = atom('"hello"')
        assert result == "hello" and isinstance(result, Str)

    def test_string_and_symbol_differ_by_type(self):
        # 같은 글자라도 문자열 리터럴과 심볼은 타입으로 구분되어야 한다
        assert isinstance(atom('"x"'), Str)
        assert not isinstance(atom("x"), Str)


# ---------------------------------------------------------------------------
# 4. 산술 / 비교 / 논리 연산
# ---------------------------------------------------------------------------
class TestArithmetic:
    def test_add(self):
        assert evaluate("(+ 1 2)") == 3

    def test_add_variadic(self):
        assert evaluate("(+ 1 2 3 4)") == 10

    def test_subtract(self):
        assert evaluate("(- 10 3)") == 7

    def test_negate(self):
        assert evaluate("(- 5)") == -5

    def test_multiply(self):
        assert evaluate("(* 4 5)") == 20

    def test_multiply_variadic(self):
        assert evaluate("(* 2 3 4)") == 24

    def test_divide(self):
        assert evaluate("(/ 10 4)") == 2.5

    def test_modulo(self):
        assert evaluate("(% 10 3)") == 1

    def test_nested_arithmetic(self):
        assert evaluate("(+ 3 (* 4 5))") == 23

    def test_precedence_via_nesting(self):
        assert evaluate("(* (+ 1 2) (+ 3 4))") == 21


class TestComparison:
    def test_gt_true(self):
        assert evaluate("(> 5 3)") is True

    def test_gt_false(self):
        assert evaluate("(> 3 5)") is False

    def test_lt(self):
        assert evaluate("(< 3 5)") is True

    def test_gte(self):
        assert evaluate("(>= 5 5)") is True

    def test_lte(self):
        assert evaluate("(<= 4 5)") is True

    def test_eq(self):
        assert evaluate("(= 3 3)") is True

    def test_neq(self):
        assert evaluate("(!= 3 4)") is True


class TestLogic:
    def test_and_true(self):
        assert evaluate("(and (> 5 1) (< 2 3))") is True

    def test_and_false(self):
        assert evaluate("(and (> 5 1) (< 3 2))") is False

    def test_or(self):
        assert evaluate("(or (< 3 2) (> 5 1))") is True

    def test_not(self):
        assert evaluate("(not (> 1 5))") is True


# ---------------------------------------------------------------------------
# 5. 변수 (define)
# ---------------------------------------------------------------------------
class TestDefine:
    def test_define_and_use(self):
        assert evaluate("(define x 10) (+ x 5)") == 15

    def test_define_returns_value(self):
        assert evaluate("(define x 10)") == 10

    def test_redefine(self):
        assert evaluate("(define x 1) (define x 2) x") == 2

    def test_define_from_expression(self):
        assert evaluate("(define x (+ 2 3)) x") == 5

    def test_undefined_variable_raises(self):
        with pytest.raises(NameError):
            evaluate("undefined_var")


# ---------------------------------------------------------------------------
# 6. 조건문 (if)
# ---------------------------------------------------------------------------
class TestIf:
    def test_true_branch(self):
        assert evaluate("(if (> 5 3) 100 200)") == 100

    def test_false_branch(self):
        assert evaluate("(if (< 5 3) 100 200)") == 200

    def test_nested_if(self):
        src = "(if (> 5 3) (if (> 2 1) 1 2) 3)"
        assert evaluate(src) == 1

    def test_if_does_not_eval_untaken_branch(self):
        # 거짓 분기는 실행되지 않아야 한다 (실행되면 NameError)
        assert evaluate("(if (> 5 3) 42 undefined_var)") == 42

    def test_if_with_expression_condition(self):
        assert evaluate("(define x 10) (if (= x 10) 1 0)") == 1


# ---------------------------------------------------------------------------
# 7. 반복문 (for)
# ---------------------------------------------------------------------------
class TestFor:
    def test_for_accumulates(self):
        src = """
        (define total 0)
        (for i 1 5 (define total (+ total i)))
        total
        """
        assert evaluate(src) == 15  # 1+2+3+4+5

    def test_for_inclusive_end(self):
        # 끝값 포함 여부 검증
        src = """
        (define count 0)
        (for i 1 3 (define count (+ count 1)))
        count
        """
        assert evaluate(src) == 3

    def test_for_single_iteration(self):
        src = """
        (define hit 0)
        (for i 5 5 (define hit (+ hit 1)))
        hit
        """
        assert evaluate(src) == 1

    def test_for_loop_variable_visible_after(self):
        src = "(for i 1 3 (+ i 0)) i"
        assert evaluate(src) == 3  # 마지막 i 값


# ---------------------------------------------------------------------------
# 8. 함수 (lambda) 와 클로저
# ---------------------------------------------------------------------------
class TestLambda:
    def test_simple_function(self):
        assert evaluate("(define sq (lambda (n) (* n n))) (sq 5)") == 25

    def test_lambda_returns_function_object(self):
        env = make_global_env()
        result = eval_node(parse(tokenize("(lambda (x) x)")), env)
        assert isinstance(result, Function)

    def test_multiple_params(self):
        src = "(define add (lambda (a b) (+ a b))) (add 3 4)"
        assert evaluate(src) == 7

    def test_zero_params(self):
        src = "(define answer (lambda () 42)) (answer)"
        assert evaluate(src) == 42

    def test_immediately_invoked(self):
        assert evaluate("((lambda (x) (* x 2)) 21)") == 42

    def test_closure_captures_env(self):
        # make-adder 가 반환한 함수가 정의 시점의 n 을 기억해야 한다
        src = """
        (define make-adder (lambda (n) (lambda (x) (+ x n))))
        (define add10 (make-adder 10))
        (add10 5)
        """
        assert evaluate(src) == 15

    def test_local_does_not_leak_arg(self):
        # 함수 인자는 지역이므로 밖에서 보이면 안 된다
        with pytest.raises(NameError):
            evaluate("(define f (lambda (secret) secret)) (f 1) secret")


# ---------------------------------------------------------------------------
# 9. 재귀
# ---------------------------------------------------------------------------
class TestRecursion:
    def test_factorial(self):
        src = """
        (define fact
          (lambda (n)
            (if (<= n 1) 1 (* n (fact (- n 1))))))
        (fact 5)
        """
        assert evaluate(src) == 120

    def test_factorial_base_case(self):
        src = """
        (define fact
          (lambda (n)
            (if (<= n 1) 1 (* n (fact (- n 1))))))
        (fact 1)
        """
        assert evaluate(src) == 1

    def test_fibonacci(self):
        src = """
        (define fib
          (lambda (n)
            (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2))))))
        (fib 10)
        """
        assert evaluate(src) == 55

    def test_countdown_sum(self):
        src = """
        (define sum-down
          (lambda (n)
            (if (= n 0) 0 (+ n (sum-down (- n 1))))))
        (sum-down 100)
        """
        assert evaluate(src) == 5050


# ---------------------------------------------------------------------------
# 10. begin / 스코프
# ---------------------------------------------------------------------------
class TestBegin:
    def test_begin_returns_last(self):
        assert evaluate("(begin 1 2 3)") == 3

    def test_begin_executes_all(self):
        src = """
        (define x 0)
        (begin (define x 1) (define x 2) (define x 3))
        x
        """
        assert evaluate(src) == 3

    def test_begin_inside_lambda(self):
        src = """
        (define f
          (lambda (n)
            (begin
              (define doubled (* n 2))
              (+ doubled 1))))
        (f 10)
        """
        assert evaluate(src) == 21


# ---------------------------------------------------------------------------
# 11. 문자열
# ---------------------------------------------------------------------------
class TestString:
    def test_string_literal_value(self):
        assert evaluate('"hello"') == "hello"

    def test_string_in_define(self):
        assert evaluate('(define greeting "hi") greeting') == "hi"

    def test_string_not_treated_as_symbol(self):
        # 문자열 "x" 는 변수 x 를 찾으려 하면 안 된다
        assert evaluate('"x"') == "x"


# ---------------------------------------------------------------------------
# 12. 통합 프로그램
# ---------------------------------------------------------------------------
class TestIntegration:
    def test_sum_to_n(self):
        src = """
        (define sum-to
          (lambda (n)
            (begin
              (define total 0)
              (for i 1 n (define total (+ total i)))
              total)))
        (sum-to 10)
        """
        assert evaluate(src) == 55

    def test_compose_functions(self):
        src = """
        (define inc (lambda (x) (+ x 1)))
        (define double (lambda (x) (* x 2)))
        (double (inc 4))
        """
        assert evaluate(src) == 10

    def test_conditional_recursion_mix(self):
        src = """
        (define is-even
          (lambda (n) (if (= n 0) true (is-odd (- n 1)))))
        (define is-odd
          (lambda (n) (if (= n 0) false (is-even (- n 1)))))
        (is-even 10)
        """
        assert evaluate(src) is True


# ---------------------------------------------------------------------------
# 13. 에러 케이스
# ---------------------------------------------------------------------------
class TestErrors:
    def test_unclosed_paren(self):
        with pytest.raises(SyntaxError):
            evaluate("(+ 1 2")

    def test_undefined_function(self):
        with pytest.raises(NameError):
            evaluate("(nonexistent 1 2)")

    def test_undefined_variable(self):
        with pytest.raises(NameError):
            evaluate("(+ x 1)")

    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            evaluate("(/ 1 0)")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
