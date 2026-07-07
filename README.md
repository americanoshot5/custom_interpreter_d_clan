# 모듈별 유닛 테스트 및 스텁 되돌리기 설계

## 배경

S-Expression 언어 인터프리터를 만드는 학습용 팀 프로젝트다. 각 모듈(Tokenizer, Assembler,
Checker, Executor)을 팀원별로 나눠 구현하고 GitHub로 협업할 계획이었다. 그런데 준비 과정에서
Tokenizer, Assembler, Checker에 실제 구현이 들어가 버려, 원래 의도(각자 인터페이스만 보고
학습하며 구현)가 깨진 상태다. Executor만 원래 계획대로 스텁(`raise ExecuteError(...)`)으로
남아 있다.

이 스펙은 다음 두 가지를 다룬다:

1. Tokenizer / Assembler / Checker 구현부를 Executor와 동일한 패턴의 스텁으로 되돌린다.
2. `tests/` 하위 5개 빈 테스트 파일에 모듈별 유닛 테스트와 통합 테스트를 채운다.

테스트는 (되돌리기 전) 실제 구현이 보여준 동작을 스펙으로 삼아 작성한다. 스텁 상태에서는
모든 테스트가 실패(red)하는 게 정상이며, 담당자가 각자 브랜치에서 구현하며 테스트를 통과시켜
나가는 것이 목표다.

## 환경 설정

- 루트에 `pyproject.toml`을 추가하고 `[tool.pytest.ini_options]`에 `pythonpath = ["src"]`를
  설정한다. `src/` 모듈들이 `from common import ...`처럼 절대 임포트를 사용하므로, pytest가
  `src/`를 import 경로에 넣어줘야 별도 `conftest.py` 없이 테스트가 동작한다. (pytest 7+ 필요)
- `requirements-dev.txt`에 `pytest`를 추가한다.

## 스텁 되돌리기

`SExpressionTokenizer.tokenize`, `SExpressionAssembler.assemble`, `StaticChecker.check`의
본문을 각각 다음과 같이 되돌린다 (인터페이스 시그니처, `DefaultXxx` 별칭, 모듈 레벨 헬퍼
함수는 그대로 유지):

```python
class SExpressionTokenizer(Tokenizer):
    def tokenize(self, source: str) -> Sequence[Token]:
        raise TokenizeError("Tokenizer implementation is not ready yet.")
```

- Assembler → `AssembleError("Assembler implementation is not ready yet.")`
- Checker → `CheckError("Checker implementation is not ready yet.")`

사용하지 않게 되는 private 헬퍼 메서드(`_read_string`, `_check_expression` 등)는 함께
제거한다.

## 테스트 내용

각 파일은 모듈별 핵심 시나리오 3~5개로 제한한다 (참고 프로젝트 수준의 촘촘함은 목표하지
않음).

### tests/test_tokenizer.py

- 기본 S-표현식 토큰화: `"(+ 1 2)"` → `LEFT_PAREN, IDENTIFIER("+"), NUMBER(1.0), NUMBER(2.0), RIGHT_PAREN, EOF`
- 문자열 리터럴 토큰화: `'"hi"'` → `STRING` 토큰, literal 값 `"hi"`
- 키워드 리터럴 처리: `"true"` / `"false"` → 각각 `TokenType.TRUE` / `TokenType.FALSE`, literal이 `True`/`False`
- 잘못된 문자 → `TokenizeError` 발생

### tests/test_assembler.py

- 단일 리터럴: 토큰 `[NUMBER(42.0), EOF]` → `Program`의 statement가 `ExpressionStmt(LiteralExpr(42.0))`
- 리스트 표현식: `"(+ 1 2)"`를 토큰화한 결과를 assemble → `ExpressionStmt(ListExpr((IdentifierExpr("+"), LiteralExpr(1.0), LiteralExpr(2.0))))`
- 중첩 리스트: `"(+ 1 (* 2 3))"` → 중첩된 `ListExpr` 구조
- 에러: 닫는 괄호 누락 → `AssembleError`
- 에러: 여는 괄호 없이 `)` 등장 → `AssembleError`

### tests/test_checker.py

- 정상적인 `ExpressionStmt(ListExpr(...))`로 구성된 `Program`은 `check()` 호출 시 예외 없음
- 중첩된 `ListExpr` 내부까지 재귀적으로 문제 없이 통과
- 지원하지 않는 statement 타입(예: 더미 `Stmt` 서브클래스)이 포함된 `Program` → `CheckError`

### tests/test_executor.py

되돌린 구현이 아직 없으므로, Tokenizer/Assembler가 만들어내는 flat S-expression AST
(`ListExpr`/`LiteralExpr`/`IdentifierExpr`)를 그대로 평가하는 산술 계산기 수준의 동작을
스펙으로 정의한다 (참고 프로젝트 `mylang.py`의 최소 기능과 동일한 결) :

- 리터럴 단독 평가: `Program(ExpressionStmt(LiteralExpr(42.0)))` → `42.0`
- 기본 산술: `(+ 1 2)` 구조 실행 → `3.0`
- 중첩 산술: `(+ 1 (* 2 3))` 구조 실행 → `7.0`

### tests/test_integration.py

전체 파이프라인(`tokenize → assemble → check → execute`)을 실제 소스 문자열로 검증하는
end-to-end 시나리오 2~3개:

- `"(+ 1 2)"` → 최종 결과 `3.0`
- `"(+ 1 (* 2 3))"` → 최종 결과 `7.0`

## 범위 밖

- `common.py`에 정의된 `VarStmt`/`IfStmt`/`ForStmt`/`BlockStmt`/`PrintStmt` 등은 현재
  Assembler가 만들어내지 않으므로 이번 테스트 범위에 포함하지 않는다. 언어에 변수/조건문/
  반복문을 추가하는 것은 이후 별도 스펙에서 다룬다.
- CI 연동, pre-commit 등 협업 인프라는 이번 스펙에서 다루지 않는다.
