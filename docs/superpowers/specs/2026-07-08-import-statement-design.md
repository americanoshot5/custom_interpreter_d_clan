# import 문 설계

## 목적

`tests/additional_test/additional_import_integration.py`에 정의된 8개 테스트
시나리오(파일 임포트, alias 호출, 순환/중복/충돌/스코프/경로 관련 에러)를
통과시키는 `import` 기능을 언어에 추가한다.

## 선행 조건

`import`로 가져온 파일 안의 함수(`func`)를 실제로 호출하려면 Function Call
기능이 먼저 있어야 한다. 이 문서를 쓰는 시점에 Function Call
(`feature/executor/add-function`)과 Class/상속(`feature/add_class_feature`)이
각각 별도 PR로 올라와 있고 아직 master에 머지되지 않았다. 두 브랜치는 같은
파일(`Executor.py` 등)을 건드리며 서로 겹치지 않는 부분이 대부분이지만,
`return` 처리 방식이 충돌한다 — class 브랜치는 함수 기능이 없던 시점에
"임시로" `return`을 일반 연산자처럼 처리해뒀는데, 이는 진짜 `ReturnStmt`/
`_ReturnSignal` 메커니즘으로 대체되어야 한다. 로컬 검증 브랜치
(`integration-test/import-feature`)에서 두 브랜치 + 정적배열(이미 master에
머지됨)을 합쳐서 충돌을 해결하고, 244(기존) + 25(function/class/array
additional) 테스트가 전부 통과하는 것까지 확인했다.

**따라서 import 기능 작업은 Function Call과 Class 두 PR이 master에 머지된
이후(또는 그 머지 결과를 반영한 브랜치 위)에 진행해야 한다.**

## 기존 구조에서 재사용하는 것

- `_SPECIAL_FORMS`(Assembler), `_STMT_DISPATCH`(Checker/Executor) 테이블 —
  새 문장 추가 시 한 줄 + 메서드 하나만 추가하는 기존 패턴을 그대로 따른다.
- `_ScopeStack.declare()`의 중복 선언 검출 — alias 이름 충돌에 별도 로직 없이
  재사용한다.
- `_ScopeStack.push()`/`pop()`의 블록 스코프 — import한 alias가 블록을 벗어나면
  자동으로 사라지는 데 별도 로직이 필요 없다.
- `_in_function`(Checker) 카운터 패턴 — for문 안 import 금지 검사에 동일한
  패턴(`_in_for`)을 사용한다.
- `ClassDef`/`Function`과 같은 급의 새 런타임 값 `Module`을 추가하는 방식 —
  기존 `Environment`/`Function`/`ClassDef` 설계와 동일한 결로 확장한다.

## 발견한 기존 버그 (이번 기회에 같이 고침)

`(sum.add 1 2)`처럼 **호출 위치**에서는 `DOTIDENTIFIER` 토큰이 `DotExpr`로
정확히 분해되지만, `(print sum.answer)`처럼 **값을 읽기만 하는 위치**에서는
`_parse_atom`이 이를 그냥 `IdentifierExpr("sum.answer")`(점 포함 문자열
그대로)로 만들어버린다. import 기능이 제대로 동작하려면 이 gap을 먼저
고쳐야 한다.

## 1. 문법 / AST

```
(import "path/to/file.cf" alias sum)
```

`common.py`에 `ImportStmt(path: Expr, alias: str)` 추가 (`Stmt`). `path`를
`Expr`로 받아 위치 정보를 유지하되, Checker 단계에서 "리터럴 문자열이어야
한다"를 검사한다.

`alias`라는 두 번째 키워드는 새 `TokenType`을 만들지 않는다 — 파서가
`_parse_import_stmt`에서 그 위치의 토큰 lexeme이 정확히 `"alias"`인지
직접 검증한다 (새 예약어를 하나 덜 늘리는 선택).

## 2. Assembler 변경

1. `_SPECIAL_FORMS`에 `TokenType.IMPORT: "_parse_import_stmt"` 한 줄 추가.
2. `_parse_import_stmt`: `import` 소비 → 문자열 리터럴(경로) 파싱 → 다음
   토큰이 `"alias"` lexeme인지 확인 → 그 다음 식별자를 alias 이름으로 저장 →
   `)` 소비.
3. **dotted 읽기 fix**: `_parse_atom`(또는 `_expression`)에서
   `token.type is TokenType.DOTIDENTIFIER`일 때, 지금처럼 통짜
   `IdentifierExpr`를 만들지 않고 `DotExpr(obj=IdentifierExpr(앞부분),
   slot=뒷부분, args=())`를 만든다. 호출 위치용 `_parse_dotidentifier_expr`가
   쓰는 것과 동일한 "점으로 분리" 로직을 헬퍼로 공유한다.

## 3. Checker 변경

`_check_import_stmt`를 추가한다. 아래 검사는 전부 기존 메커니즘을 그대로
재사용/확장한다.

| 검사 | 방법 | 실패 시 |
|---|---|---|
| path가 문자열 리터럴 | `isinstance(stmt.path, LiteralExpr)` 이고 값이 `str` | `CheckError` |
| 파일 존재 | `pathlib.Path(path).exists()` | `CheckError` |
| 순환 참조 | "현재 체크 중인 파일 경로" 스택 추가 (기존 `_declaring` 자기참조 패턴과 동일한 아이디어). 이미 스택에 있는 경로를 다시 임포트하려 하면 실패 | `CheckError` |
| 같은 파일 같은 스코프 중복 임포트 | 스코프별 "이미 임포트한 절대경로 집합"을 `_ScopeStack.push`/`pop`에 같이 얹어 추적 | `CheckError` |
| alias 이름 충돌 | 새 로직 없음 — 끝에서 `scopes.declare(alias, location)` 호출 시 기존 중복선언 검사가 처리 | `CheckError` |
| import는 블록 스코프에 한정 | 새 로직 없음 — `declare()`가 현재(가장 안쪽) 스코프에만 등록되므로 블록이 끝나면 자동 소멸 | `CheckError` (스코프 밖에서 alias 참조 시 "Undefined variable") |
| for문 안 import 금지 | `_check_for_stmt` 진입 시 `_in_for` 카운터 증가, `_check_import_stmt`에서 0보다 크면 실패 (`_in_function`과 동일 패턴) | `CheckError` |
| 임포트한 파일 자체의 정합성 | 그 파일을 재귀적으로 `tokenize → assemble → check` (새 `_ScopeStack`으로 독립 검사) | 내부 에러 그대로 `CheckError`로 전파 |

멤버(`sum.add`가 실제로 존재하는지)는 **check 시점에 정적으로 검증하지
않는다** — 기존 `ClassInstance`의 필드/메서드 접근과 동일하게, 실행 시점에
`ExecuteError`로 처리한다(아래 4번 참고). 이렇게 하면 Checker의 import
관련 로직이 "구조적으로 올바른가"만 보면 되어 단순해진다.

## 4. Executor 변경

- 새 런타임 값 `Module(name: str, environment: Environment)` — `ClassDef`/
  `Function`과 같은 급.
- `_execute_importstmt`: 대상 파일을 **독립된 빈 Environment**로
  `tokenize → assemble → check → execute` 전부 실행한 뒤, 그 결과
  Environment를 `Module`로 감싸 alias 이름으로 현재 Environment에 `define`.
  (Checker가 이미 같은 파일을 한 번 검사하므로 파싱/검사가 두 번 일어나는
  셈이지만, 각 파이프라인 단계가 서로 독립적으로 동작하는 기존 설계와
  일관되며, 이 프로젝트 규모에서 성능 문제가 되지 않는다.)
- `_execute_dot_expr`에 `Module` 분기 추가: `obj`가 `Module`이면
  `module.environment.lookup(slot)`으로 값을 가져온다. `args`가 있으면 그
  값이 `Function`인지 확인 후 `_call_function`으로 호출하고, 없으면 값을
  그대로 반환한다 (`sum.answer`처럼 단순 읽기).

## 5. 에러 계층 정리

| 시나리오 | 계층 |
|---|---|
| 경로가 문자열 아님 / 파일 없음 / 순환 / 같은 스코프 중복 임포트 / alias 충돌 / 스코프 밖 참조 / for문 안 import | `CheckError` |
| 위 검사를 통과했지만 실행 자체가 실패 (예: 존재하지 않는 멤버 호출) | `ExecuteError` |

## 6. 테스트 계획

**통합 테스트** (`tests/additional_test/additional_import_integration.py`,
기존 8개에 추가):
- 정상 동작 1개: 기존 것과 다른 형태(예: 임포트한 파일의 `var`를 직접 읽는
  케이스, 또는 같은 파일을 서로 다른 스코프에서 각각 임포트해도 문제없는
  케이스)
- 예외 동작 1개: 기존 8개가 다루지 않는 새로운 실패 시나리오 (예: 임포트한
  모듈에 없는 멤버를 호출 — `ExecuteError` 케이스, 지금 8개는 전부
  `CheckError`라 이 계층의 커버리지가 없음)

**유닛 테스트** (기존 파일에 추가, 새로 만들지 않음):
- `tests/test_assembler.py`: `(import "path" alias name)` 파싱 결과가
  `ImportStmt(path=LiteralExpr("path"), alias="name")`인지. 그리고 bare
  `DOTIDENTIFIER` 원자가 `DotExpr(obj=IdentifierExpr(...), slot=..., args=())`로
  분해되는지 (기존에 없던 커버리지 — 이번에 고친 버그의 회귀 방지).
- `tests/test_checker.py`: `_check_import_stmt`의 각 검사 항목(경로 리터럴,
  순환, 중복임포트, alias 충돌, for문 제한)을 `ImportStmt`를 직접 구성해
  단위 테스트. `_ScopeStack`에 추가되는 "임포트 경로 추적" 로직도 별도 검증.
- `tests/test_executor.py`: `Module` 런타임 값 생성, `_execute_dot_expr`의
  `Module` 분기(멤버 읽기 / 함수 멤버 호출) 단위 테스트.

## 비목표 (Out of scope)

- 상대 경로 해석(임포트하는 파일 기준 상대경로) — 테스트가 절대경로만
  사용하므로 이번 범위에서 제외. 필요해지면 별도로 다룬다.
- 멤버 정적 검증(존재하지 않는 멤버를 check 시점에 잡아내는 것) — 클래스
  필드/메서드와 동일하게 실행 시점 검증으로 충분하다고 판단.
- import한 모듈들 사이의 상호 참조(모듈 A가 모듈 B를 임포트하고, B도 A를
  일부만 참조하는 등의 복잡한 의존성 그래프) — 순환 감지만 구현하고, 그
  이상의 의존성 관리는 다루지 않는다.
