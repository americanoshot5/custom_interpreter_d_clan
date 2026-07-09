"""
3-4. pre-execution optimization

번역 규칙은 _helpers.py 참고.
"""

from __future__ import annotations

import importlib

from Assembler import assemble
from Checker import check
from Executor import execute
from Tokenizer import tokenize


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
