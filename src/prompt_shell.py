from __future__ import annotations

from collections.abc import Callable, Sequence

from Assembler import assemble
from Checker import StaticChecker
from common import LanguageError, Program, RuntimeValue, Token, TokenType
from Executor import SExpressionExecutor
from Tokenizer import tokenize

# var/set!/print/if/for/func/return/class/import 처럼 "(키워드 ...)" 형태로
# 감싸야 하는 최상위 특수 형태 키워드들. wrap_bare_statement 가 이 목록을
# 보고 바깥 괄호 생략 여부를 판단한다.
_BARE_STATEMENT_KEYWORDS = frozenset({
    TokenType.VAR,
    TokenType.SET,
    TokenType.PRINT,
    TokenType.IF,
    TokenType.FOR,
    TokenType.FUNC,
    TokenType.RETURN,
    TokenType.CLASS,
    TokenType.IMPORT,
})


def wrap_bare_statement(
    text: str,
    tokenize: Callable[[str], Sequence[Token]],
    assemble: Callable[[Sequence[Token]], Program],
) -> str:
    """REPL 편의 기능: `var a 1` 처럼 단순한 한 줄짜리 문장이면 바깥 괄호를
    생략해도 `(var a 1)`로 감싸서 실행한다. 중첩된 하위 식은 여전히 자기
    괄호가 필요하다 (예: `var a (+ 1 2)`는 그대로 두고 바깥만 감싼다).

    이미 괄호로 시작하거나, 첫 토큰이 특수 형태 키워드가 아니거나, 감싼
    결과가 문장 하나로 깔끔하게 조립되지 않으면 원본 텍스트를 그대로
    반환한다 (기존 동작/에러 메시지를 그대로 유지하기 위함)."""
    stripped = text.strip()
    if not stripped or stripped.startswith("("):
        return text
    try:
        tokens = tokenize(stripped)
    except LanguageError:
        return text
    if not tokens or tokens[0].type not in _BARE_STATEMENT_KEYWORDS:
        return text

    wrapped = f"({stripped})"
    try:
        program = assemble(tokenize(wrapped))
    except LanguageError:
        return text
    if len(program.statements) != 1:
        return text
    return wrapped


def is_balanced(text: str) -> bool:
    depth = 0
    in_string = False
    for char in text:
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
    return depth <= 0


def run_shell(
    read_line: Callable[[str], str],
    write_output: Callable[[str], None],
    tokenize: Callable[[str], Sequence[Token]],
    assemble: Callable[[Sequence[Token]], Program],
    check: Callable[[Program], None],
    execute: Callable[[Program], RuntimeValue],
    prompt: str = ">>> ",
    continuation_prompt: str = "... ",
    checkpoint: Callable[[], object] | None = None,
    restore: Callable[[object], None] | None = None,
) -> None:
    buffer: list[str] = []

    while True:
        current_prompt = continuation_prompt if buffer else prompt
        try:
            line = read_line(current_prompt)
        except EOFError:
            return

        if not buffer:
            stripped = line.strip()
            if stripped.lower() in {"exit", "quit"}:
                return
            if stripped == "":
                continue

        if line.strip() == "":
            text = wrap_bare_statement("\n".join(buffer), tokenize, assemble)
            saved = checkpoint() if checkpoint is not None else None
            try:
                tokens = tokenize(text)
                program = assemble(tokens)
                check(program)
                result = execute(program)
            except LanguageError as error:
                if saved is not None and restore is not None:
                    restore(saved)
                write_output(f"Error: {error}")
            else:
                if result is not None:
                    write_output(str(result))

            buffer = []
            continue

        buffer.append(line)


def main() -> None:
    checker = StaticChecker()
    executor = SExpressionExecutor()
    run_shell(
        read_line=input,
        write_output=print,
        tokenize=tokenize,
        assemble=assemble,
        check=checker.check,
        execute=executor.execute,
        checkpoint=checker.checkpoint,
        restore=checker.restore,
    )


if __name__ == "__main__":
    main()
