from Assembler import assemble
from Checker import check
from Executor import execute
from Tokenizer import tokenize


def _run(source):
    tokens = tokenize(source)
    program = assemble(tokens)
    check(program)
    return execute(program)


def test_end_to_end_simple_addition():
    assert _run("(+ 1 2)") == 3.0


def test_end_to_end_nested_arithmetic():
    assert _run("(+ 1 (* 2 3))") == 7.0
