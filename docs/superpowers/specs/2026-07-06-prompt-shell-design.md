# prompt_shell.py 설계

## 배경

S-Expression 인터프리터 학습용 팀 프로젝트에서, 사용자가 파이썬 인터프리터처럼 S-Expression
프로그램을 실시간으로 입력할 수 있는 REPL(`prompt_shell.py`)이 필요하다. TDD로 개발하고,
완료 후 동료들의 GitHub PR 리뷰를 받을 예정이다. 이 작업은 별도 브랜치
(`feature/prompt-shell`)에서 진행한다.

현재 `Tokenizer`/`Assembler`/`Checker`는 스텁(각자 "implementation is not ready yet."
에러를 raise) 상태이고 `Executor`도 원래부터 스텁 상태다. 이 REPL은 파이프라인의
실제 구현 여부와 무관하게 동작을 검증할 수 있어야 한다.

## 아키텍처

`src/prompt_shell.py`에 두 개의 함수를 둔다.

### `is_balanced(text: str) -> bool`

순수 함수. `text`에서 `(`/`)` 개수를 세어 깊이(depth = 열린 괄호 수 - 닫힌 괄호 수)를
계산한다. 단, `"..."` 문자열 리터럴 안에 있는 괄호는 세지 않는다 (같은 줄 안의 여는
따옴표와 닫는 따옴표 사이 구간만 건너뛴다 — 여러 줄에 걸친 문자열 리터럴은 이 함수의
관심사가 아니며, 그런 경우는 파이프라인의 `Tokenizer`가 `TokenizeError`로 처리한다).
`depth <= 0`이면 `True`(완결됨), 아니면 `False`.

### `run_shell(read_line, write_output, tokenize, assemble, check, execute, prompt=">>> ", continuation_prompt="... ") -> None`

REPL 본체. 파이프라인 4단계(`tokenize`, `assemble`, `check`, `execute`)와 입출력
(`read_line`, `write_output`)을 모두 함수로 주입받는다. 이 덕분에 파이프라인이 스텁이든
실제 구현이든, 그리고 실제 표준입출력이 아니어도 REPL 자체 로직(프롬프트 전환, 여러 줄
누적, 에러 처리, 종료)을 독립적으로 테스트할 수 있다.

- `read_line: Callable[[], str]` — 한 줄을 읽어 반환. 입력이 끝나면 `EOFError`를
  raise한다 (내장 `input()`과 동일한 계약).
- `write_output: Callable[[str], None]` — 한 줄을 출력 (내장 `print`와 동일한 계약).
- `tokenize: Callable[[str], Sequence[Token]]`, `assemble: Callable[[Sequence[Token]], Program]`,
  `check: Callable[[Program], None]`, `execute: Callable[[Program], RuntimeValue]` — 각
  모듈의 기존 모듈 레벨 함수와 동일한 시그니처.

## 루프 동작

1. 버퍼(줄 리스트)가 비어 있으면 `prompt`를, 아니면 `continuation_prompt`를 사용해
   `read_line()`으로 한 줄을 읽는다.
2. `read_line()`이 `EOFError`를 raise하면 루프를 종료한다.
3. 버퍼가 비어 있고 읽은 줄을 `strip().lower()`한 값이 `"exit"` 또는 `"quit"`이면 루프를
   종료한다.
4. 버퍼가 비어 있고 읽은 줄이 공백뿐이면(strip 결과가 빈 문자열) 아무것도 하지 않고 1번으로
   돌아간다.
5. 읽은 줄을 버퍼에 추가하고, 버퍼를 개행으로 합친 텍스트에 대해 `is_balanced()`를 확인한다.
   `False`면 1번으로 돌아가 계속 입력을 받는다 (이때부터는 `continuation_prompt` 사용).
6. `True`면 완결된 것으로 보고 파이프라인을 실행한다: `tokenize` → `assemble` → `check` →
   `execute`. 이 중 하나가 `TokenizeError`/`AssembleError`/`CheckError`/`ExecuteError`를
   raise하면 `write_output(f"Error: {예외 메시지}")`를 호출하고, 성공하면
   `write_output(str(execute 결과))`를 호출한다. 어느 쪽이든 버퍼를 비우고 1번으로
   돌아간다.

## 진입점

`src/prompt_shell.py` 파일 하단에 `if __name__ == "__main__":` 블록을 두고, `run_shell`을
다음으로 연결한다:
- `read_line=input`, `write_output=print`
- `tokenize=Tokenizer.tokenize`, `assemble=Assembler.assemble`, `check=Checker.check`,
  `execute=Executor.execute` (각 모듈에 이미 존재하는 모듈 레벨 함수)

파이프라인 4개 모듈이 현재 스텁이므로, 이 상태로 실제로 실행하면 매번 에러가 출력된다.
이는 이 모듈의 결함이 아니라 프로젝트의 현재 진행 상태를 반영하는 정상 동작이다.

## 테스트 (TDD)

`tests/test_prompt_shell.py`에 7개:

1. `is_balanced`: 괄호 안 맞음/맞음 기본 케이스
2. `is_balanced`: 문자열 리터럴 안의 괄호는 무시됨
3. 한 줄 입력이 파이프라인을 통과해 즉시 결과가 출력됨
4. 괄호가 여러 줄에 걸쳐 있는 입력이 완결될 때까지 누적된 뒤 한 번에 실행됨
5. 파이프라인 단계에서 에러가 발생하면 `"Error: ..."`로 출력되고, 셸이 종료되지 않고 다음
   입력을 계속 받음
6. `"exit"` 입력 시 루프가 종료됨
7. `read_line`이 `EOFError`를 raise하면 루프가 종료됨

(테스트는 전부 `tokenize`/`assemble`/`check`/`execute` 자리에 원하는 값을 반환하거나
예외를 raise하는 가짜 함수를 주입해 작성한다. 실제 `Tokenizer`/`Assembler`/`Checker`/
`Executor` 모듈을 임포트하거나 호출하지 않는다.)

## 범위 밖

- 실제 파이프라인 4개 모듈의 구현 (각각 별도 팀원이 다른 브랜치에서 진행 중)
- 입력 히스토리(방향키로 이전 입력 불러오기), 자동완성 등 셸 편의 기능
- 변수/환경 상태를 REPL 세션 내에서 유지하는 기능 (현재 `Executor` 인터페이스가
  `execute(program) -> RuntimeValue`로 상태를 갖지 않으므로, 이 REPL도 상태를 유지하지 않음)
