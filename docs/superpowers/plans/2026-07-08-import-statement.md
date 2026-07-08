# Import 문 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `(import "path/to/file.cf" alias name)` 문을 언어에 추가해서, 다른 소스 파일을 독립된 네임스페이스로 불러와 `name.member` 형태로 값/함수에 접근할 수 있게 한다.

**Architecture:** 기존 4단계 파이프라인(Tokenizer → Assembler → Checker → Executor) 패턴을 그대로 따른다. `ImportStmt`라는 새 AST 노드 하나를 추가하고, 각 단계의 기존 dispatch 테이블(`_SPECIAL_FORMS`, `_STMT_DISPATCH`)에 한 줄씩 등록한다. Checker가 임포트 대상 파일을 재귀적으로 `tokenize→assemble→check`해서 정적 오류(순환, 중복, 없는 파일 등)를 전부 `CheckError`로 잡아내고, Executor는 같은 파일을 독립된 `Environment`에서 실제로 실행해 그 결과를 `Module` 런타임 값으로 감싼다.

**Tech Stack:** Python 3.13, pytest, pytest-mock. 새 외부 의존성 없음 (표준 라이브러리 `pathlib`만 추가로 사용).

## Global Constraints

- 이 저장소의 pytest 설정(`pyproject.toml`)은 `pythonpath = ["src"]`, `testpaths = ["tests"]` — 모든 `src/*.py` 모듈은 서로 `from Assembler import ...`처럼 **`src.` 프리픽스 없이** 임포트한다. 새로 추가하는 import 문에서도 이 컨벤션을 반드시 지킨다.
- AST 노드는 전부 `@dataclass(frozen=True, slots=True)`. `Expr`/`Stmt` 베이스는 `kw_only=True`라 하위 클래스에서 `location`은 항상 키워드 인자로만 넘긴다.
- 각 파이프라인 단계(Assembler/Checker/Executor)는 "새 기능 추가 시 dispatch 테이블에 한 줄 + 메서드 하나"라는 기존 패턴을 그대로 따른다 — 새로운 if/elif 체인을 만들지 않는다.
- 에러는 전부 `common.py`의 `LanguageError` 계층(`AssembleError`/`CheckError`/`ExecuteError`) 중 하나를 사용한다.
- 커밋 메시지는 한국어로 작성하고, 끝에 `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`를 붙인다 (이 저장소 관례).

## 선행 조건 (필독)

이 계획은 **Function Call**(`feature/executor/add-function`)과 **Class**(`feature/add_class_feature`) 두 PR이 이미 `master`에 머지되어 있다는 것을 전제로 한다 (`FuncDefStmt`, `ReturnStmt`, `_ReturnSignal`, `Function`, `ClassStmt`, `ClassDef`, `DotExpr`, `NewExpr`, `SuperExpr`가 이미 `common.py`/`Assembler.py`/`Checker.py`/`Executor.py`에 있어야 한다).

Task 1에서 이 전제를 확인하고, 만약 아직 머지가 안 됐다면 로컬에서 두 브랜치를 직접 머지해서 진행한다 (정확한 충돌 해결 방법을 Task 1에 그대로 적어뒀다 — 이미 한 번 검증된 해결법이다).

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `src/common.py` | `ImportStmt` AST 노드, `TokenType.IMPORT`, `KEYWORDS["import"]` 추가 |
| `src/Assembler.py` | `_parse_import_stmt` (import 문 파싱), bare `DOTIDENTIFIER` 원자를 `DotExpr`로 만드는 fix |
| `src/Checker.py` | `_check_import_stmt` (경로/파일존재/순환/중복/for문제한 검사), `_ScopeStack`에 임포트 경로 추적 추가 |
| `src/Executor.py` | `Module` 런타임 값, `_execute_importstmt`, `_execute_dot_expr`의 `Module` 분기 |
| `tests/test_assembler.py` | import 파싱 + dotted-atom fix 유닛 테스트 |
| `tests/test_checker.py` | `_check_import_stmt`의 각 검사 항목 유닛 테스트 |
| `tests/test_executor.py` | `Module` 생성 + dot-expr 실행 유닛 테스트 |
| `tests/additional_test/additional_import_integration.py` | 정상/예외 통합 테스트 2건 추가 |

---

### Task 1: 선행 조건 확인 및 베이스라인 검증

**Files:**
- (읽기 전용 — 코드 변경 없음)

**Interfaces:**
- Consumes: 없음
- Produces: 검증된 베이스라인 (이후 모든 Task가 이 상태 위에서 진행됨)

- [ ] **Step 1: 현재 브랜치와 master 상태 확인**

```bash
git fetch origin
git log --oneline master -5
```

`FuncDefStmt`, `ClassStmt`가 `master`의 `src/common.py`에 있는지 확인:

```bash
git show master:src/common.py | grep -E "FuncDefStmt|ClassStmt"
```

두 클래스 이름이 모두 출력되면 선행 조건이 이미 충족된 것 — Step 2로 건너뛰고 `feature/executor/add-import` 브랜치를 `master`에서 새로 만들어 진행한다.

```bash
git checkout master && git pull --ff-only origin master
git checkout -b feature/executor/add-import
```

- [ ] **Step 2 (선행 조건이 아직 안 갖춰졌을 때만): 두 브랜치를 로컬에서 머지**

```bash
git checkout -b feature/executor/add-import master
git merge --no-edit origin/feature/executor/add-function
```

`src/Executor.py`의 import 줄에서만 충돌이 난다. 아래처럼 양쪽을 다 합친다:

```python
from common import *
from common import (
    ArrayExpr,
    ArrayIndexExpr,
    BUILTIN_OPS,
    FuncDefStmt,
    ReturnStmt,
    SetStmt,
    VarStmt,
)
from interfaces import *
```

```bash
git add src/Executor.py
git commit --no-edit
git merge --no-edit origin/feature/add_class_feature
```

이번엔 `common.py`(KEYWORDS 딕셔너리 한 줄), `Assembler.py`, `Checker.py`, `Executor.py` 네 곳에서 충돌이 난다. 각 충돌은 "한쪽엔 func/return 관련 코드, 다른 쪽엔 class 관련 코드"라서 **양쪽 다 살리면** 된다 (겹치는 로직 없음). 단, 아래 두 곳은 단순 병합이 아니라 실제로 고쳐야 한다:

1. `Checker.py`의 `_check_exprstmt` — class 브랜치가 "함수 기능 나오기 전 임시"로 넣어둔, `ListExpr` 안에서 `return` 문자열을 찾는 코드가 있다. 이건 이제 죽은 코드다 (func 브랜치가 `return`을 진짜 `ReturnStmt`로 파싱하므로). 삭제하고 아래로 교체:

```python
def _check_exprstmt(self, stmt: ExpressionStmt, scopes: _ScopeStack) -> None:
    self._check_expr(stmt.expression, scopes)
```

그리고 `_check_return_stmt`를 아래로 교체 (함수/메서드 양쪽 컨텍스트를 인식하도록):

```python
def _check_return_stmt(self, stmt: ReturnStmt, scopes: _ScopeStack) -> None:
    in_function = getattr(self, "_in_function", 0) > 0
    in_method = bool(self._method_stack)
    if not in_function and not in_method:
        raise CheckError("'return' is used outside function")
    if stmt.value is not None:
        self._check_expr(stmt.value, scopes)
        if in_method and self._method_stack[-1]["is_init"]:
            raise CheckError("'init' method cannot use 'return' with a value")
```

2. `Executor.py`의 `_call_method` — 메서드 안에서 `return`을 쓰면 `_ReturnSignal` 예외가 새어나가 크래시가 난다 (class 브랜치가 이 예외를 잡는 코드를 안 만들었기 때문). `_call_method`의 try 블록을 아래로 교체:

```python
        try:
            result: RuntimeValue = None
            try:
                for stmt in method_def.body:
                    result = self._execute_stmt(stmt)
            except _ReturnSignal as sig:
                result = sig.value
            return result
        finally:
            self._environment = previous
```

또한 `Executor.py`의 `_execute_list_expr`에서 class 브랜치가 넣어둔 "return: 현재는 값을 그대로 반환 (함수 기능 구현 전 임시)" 특수 처리 블록(`if op == "return": ...`)을 삭제한다 — 이제 필요 없다. 그리고 `_ALL_OPS` 정의에서 `"return"`을 제거한다:

```python
_ALL_OPS: frozenset[str] = frozenset(_UNARY) | frozenset(_BINARY) | _ARRAY_OPS | {"instanceof"}
```

나머지 충돌은 양쪽 블록을 순서대로 이어붙이면 된다 (마커만 지우고 내용은 그대로 유지).

```bash
git add src/common.py src/Assembler.py src/Checker.py src/Executor.py
git commit --no-edit
```

- [ ] **Step 3: 전체 테스트 스위트로 베이스라인 확인**

```bash
python3 -m venv .venv  # 이미 있으면 생략
.venv/bin/pip install -q -r requirements-dev.txt
.venv/bin/pytest -q
```

Expected: 기존 테스트 전부 통과 (244개 안팎, 정확한 숫자는 환경에 따라 다를 수 있음 — **실패가 0건**이어야 한다).

```bash
.venv/bin/pytest tests/additional_test/additional_function_integration.py tests/additional_test/additional_class_integration.py tests/additional_test/additional_static_array_integration.py -q
```

Expected: 25 passed (function 7 + class 11 + array 7).

이 두 명령이 전부 통과해야 Task 2로 넘어간다. 실패하면 머지 충돌 해결이 잘못된 것이니 위 Step 2를 다시 확인한다.

---

### Task 2: common.py — ImportStmt AST 노드 + 토큰 추가

**Files:**
- Modify: `src/common.py`
- Test: `tests/test_assembler.py` (Task 3에서 이 노드를 사용하는 첫 테스트 작성)

**Interfaces:**
- Produces: `ImportStmt(path: Expr, alias: str, location=...)` — `path`는 임의의 `Expr`(리터럴 여부는 Checker가 검증), `alias`는 평문 문자열.
- Produces: `TokenType.IMPORT`, `KEYWORDS["import"]`

- [ ] **Step 1: TokenType에 IMPORT 추가**

`src/common.py`의 `TokenType` enum에서 `PRINT = "print"` 아래에 추가:

```python
    PRINT = "print"
    IMPORT = "import"
```

- [ ] **Step 2: KEYWORDS 딕셔너리에 등록**

`KEYWORDS` 딕셔너리에서 `"print": TokenType.PRINT,` 아래에 추가:

```python
    "print": TokenType.PRINT,
    "import": TokenType.IMPORT,
```

- [ ] **Step 3: ImportStmt 노드 정의**

"Statement nodes" 섹션의 `ForStmt` 클래스 바로 아래에 추가:

```python
@dataclass(frozen=True, slots=True)
class ImportStmt(Stmt):
    path: Expr
    alias: str
```

- [ ] **Step 4: `__all__`에 추가**

`__all__` 리스트에 알파벳 순서를 지켜서 추가 (`IfStmt` 다음, `IdentifierExpr` 다음 등 — 기존 정렬 방식에 맞춰 `"ImportStmt",`를 `"IfStmt",` 바로 다음 줄에 삽입):

```python
    "IfStmt",
    "ImportStmt",
    "KEYWORDS",
```

- [ ] **Step 5: 문법 오류 없는지 확인**

```bash
.venv/bin/python -c "
import sys
sys.path.insert(0, 'src')
from common import ImportStmt, TokenType
print(TokenType.IMPORT)
print(ImportStmt)
"
```

Expected: 에러 없이 `TokenType.IMPORT`와 `<class 'common.ImportStmt'>`가 출력됨.

- [ ] **Step 6: 커밋**

```bash
git add src/common.py
git commit -m "$(cat <<'EOF'
feat: ImportStmt AST 노드와 import 키워드 추가

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Assembler — bare DOTIDENTIFIER 원자를 DotExpr로 파싱 (기존 버그 수정)

지금 `(sum.add 1 2)`처럼 **호출 위치**의 `DOTIDENTIFIER`는 `DotExpr`로 정확히
분해되지만, `(print sum.answer)`처럼 **값만 읽는 위치**에서는 그냥
`IdentifierExpr("sum.answer")`(점 포함 문자열 그대로)가 되어버린다. import
기능이 모듈 멤버를 제대로 읽으려면 이 gap을 먼저 고쳐야 한다.

**Files:**
- Modify: `src/Assembler.py`
- Test: `tests/test_assembler.py`

**Interfaces:**
- Consumes: `common.DotExpr(obj: Expr, slot: str, args: tuple[Expr, ...])` (이미 존재)
- Produces: bare `DOTIDENTIFIER` 원자 → `DotExpr(obj=IdentifierExpr(앞부분), slot=뒷부분, args=())`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_assembler.py`에서 `unwrap` 헬퍼가 정의된 섹션 근처(예: "3. 단일 atom" 섹션) 아무 곳에 추가:

```python
def test_dotidentifier_atom_becomes_dot_expr():
    """호출 위치가 아닌 곳의 obj.slot 도 DotExpr 로 분해되어야 한다."""
    from common import DotExpr

    expr = unwrap(
        [tok(TokenType.DOTIDENTIFIER, "sum.answer", literal="sum.answer"), eof()]
    )
    assert isinstance(expr, DotExpr)
    assert isinstance(expr.obj, IdentifierExpr)
    assert expr.obj.name == "sum"
    assert expr.slot == "answer"
    assert expr.args == ()
```

`DotExpr`를 파일 상단 `from common import (...)` 블록에도 추가한다 (알파벳 순서 유지, `DotExpr,`를 `Expr,` 앞에 삽입).

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/test_assembler.py::test_dotidentifier_atom_becomes_dot_expr -v
```

Expected: FAIL — `assert isinstance(expr, DotExpr)` 에서 `AssertionError` (지금은 `IdentifierExpr`가 나오므로).

- [ ] **Step 3: `_parse_atom`에 DOTIDENTIFIER 분기 추가**

`src/Assembler.py`의 `_parse_atom` 메서드를 아래로 교체:

```python
    def _parse_atom(self, token: Token) -> Expr:
        if token.type is TokenType.RIGHT_PAREN:
            raise AssembleError(f"Unexpected ')' at {token.location.line}:{token.location.column}")
        if token.type is TokenType.RIGHT_BRACKET:
            raise AssembleError(f"Unexpected ']' at {token.location.line}:{token.location.column}")
        if token.type in {TokenType.NUMBER, TokenType.STRING, TokenType.TRUE, TokenType.FALSE}:
            return LiteralExpr(token.literal, location=token.location)
        if token.type is TokenType.DOTIDENTIFIER:
            obj_name, slot_name = self._split_dot_identifier(token.lexeme)
            return DotExpr(
                obj=IdentifierExpr(obj_name, location=token.location),
                slot=slot_name,
                args=(),
                location=token.location,
            )
        return IdentifierExpr(token.lexeme, location=token.location)

    @staticmethod
    def _split_dot_identifier(lexeme: str) -> tuple[str, str]:
        dot_pos = lexeme.index(".")
        return lexeme[:dot_pos], lexeme[dot_pos + 1:]
```

그리고 기존 `_parse_dotidentifier_expr`(호출 위치용) 안의 직접 분리 로직을 이 헬퍼를 쓰도록 바꿔서 중복을 없앤다. 아래 두 줄:

```python
        lexeme = tok.lexeme
        dot_pos = lexeme.index(".")
        obj_name = lexeme[:dot_pos]
        method_name = lexeme[dot_pos + 1:]
```

을 이렇게 교체:

```python
        lexeme = tok.lexeme
        obj_name, method_name = self._split_dot_identifier(lexeme)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/test_assembler.py::test_dotidentifier_atom_becomes_dot_expr -v
```

Expected: PASS

- [ ] **Step 5: 전체 test_assembler.py 회귀 확인 (호출 위치 dotted 파싱이 안 깨졌는지)**

```bash
.venv/bin/pytest tests/test_assembler.py -q
```

Expected: 전부 통과 (신규 1개 포함).

- [ ] **Step 6: 커밋**

```bash
git add src/Assembler.py tests/test_assembler.py
git commit -m "$(cat <<'EOF'
fix: 호출 위치가 아닌 obj.slot 원자도 DotExpr 로 파싱

(print sum.answer) 처럼 dotted 식별자를 값만 읽는 위치에서 쓰면 지금까지
IdentifierExpr("sum.answer")(점 포함 문자열 그대로)가 되어 모듈 멤버
읽기가 동작하지 않았다. 호출 위치(_parse_dotidentifier_expr)와 동일한
분해 로직을 공유해서 원자 위치에서도 DotExpr 로 만들도록 수정.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Assembler — import 문 파싱

**Files:**
- Modify: `src/Assembler.py`
- Test: `tests/test_assembler.py`

**Interfaces:**
- Consumes: `common.ImportStmt` (Task 2), `TokenType.IMPORT` (Task 2)
- Produces: `SExpressionAssembler`가 `(import "path" alias name)`을 `ImportStmt(path=LiteralExpr("path"), alias="name")`으로 파싱

- [ ] **Step 1: 실패하는 테스트 작성 (정상 케이스)**

`tests/test_assembler.py`에 추가:

```python
def test_import_stmt_parses_path_and_alias():
    from common import ImportStmt

    tokens = [
        lparen(),
        tok(TokenType.IMPORT, "import"),
        string("lib.cf"),
        ident("alias"),
        ident("sum"),
        rparen(),
        eof(),
    ]
    prog = SExpressionAssembler(tokens).assemble()
    stmt = prog.statements[0]
    assert isinstance(stmt, ImportStmt)
    assert isinstance(stmt.path, LiteralExpr)
    assert stmt.path.value == "lib.cf"
    assert stmt.alias == "sum"


def test_import_stmt_missing_alias_keyword_raises():
    tokens = [
        lparen(),
        tok(TokenType.IMPORT, "import"),
        string("lib.cf"),
        ident("sum"),  # 'alias' 키워드 없이 바로 이름
        rparen(),
        eof(),
    ]
    with pytest.raises(AssembleError):
        SExpressionAssembler(tokens).assemble()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/test_assembler.py::test_import_stmt_parses_path_and_alias -v
```

Expected: FAIL — `TokenType.IMPORT`가 `_SPECIAL_FORMS`에 없어서 `ImportStmt`가 아니라 `ExpressionStmt`가 나옴 (`isinstance(stmt, ImportStmt)`에서 실패).

- [ ] **Step 3: `_SPECIAL_FORMS`에 등록**

`src/Assembler.py`의 `_SPECIAL_FORMS` 딕셔너리에 한 줄 추가:

```python
    _SPECIAL_FORMS: ClassVar[dict[TokenType, str]] = {
        TokenType.VAR:    "_parse_var_stmt",
        TokenType.SET:    "_parse_set_stmt",
        TokenType.PRINT:  "_parse_print_stmt",
        TokenType.IF:     "_parse_if_stmt",
        TokenType.FOR:    "_parse_for_stmt",
        TokenType.FUNC:   "_parse_func_stmt",
        TokenType.RETURN: "_parse_return_stmt",
        TokenType.CLASS:  "_parse_class_stmt",
        TokenType.IMPORT: "_parse_import_stmt",
    }
```

- [ ] **Step 4: `_parse_import_stmt` 구현**

`_parse_for_stmt` 메서드 바로 아래에 추가 (import는 새 `ImportStmt`를 만들어야 하므로 파일 상단 `from common import (...)`에 `ImportStmt`도 추가한다):

```python
    def _parse_import_stmt(self, open_paren: Token) -> ImportStmt:
        self._advance()  # consume 'import'
        path_expr = self._expression()
        alias_kw = self._advance()
        if alias_kw.lexeme != "alias":
            raise AssembleError(
                f"Expected 'alias' after import path at "
                f"{alias_kw.location.line}:{alias_kw.location.column}"
            )
        alias_name_token = self._consume(
            TokenType.IDENTIFIER, "Expected alias name after 'alias'"
        )
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close import statement")
        return ImportStmt(
            path=path_expr,
            alias=alias_name_token.lexeme,
            location=open_paren.location,
        )
```

주의: `path_expr`는 여기서 문자열인지 검증하지 않는다 — `(import sum.cf alias sum)`처럼 따옴표 없는 경로도 일단 파싱은 되어야 하고 (dotted atom이면 Task 3 덕분에 `DotExpr`가 됨), "경로는 문자열 리터럴이어야 한다"는 검증은 **Checker**(Task 5)의 책임이다.

- [ ] **Step 5: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/test_assembler.py::test_import_stmt_parses_path_and_alias tests/test_assembler.py::test_import_stmt_missing_alias_keyword_raises -v
```

Expected: 둘 다 PASS

- [ ] **Step 6: 전체 test_assembler.py 회귀 확인**

```bash
.venv/bin/pytest tests/test_assembler.py -q
```

Expected: 전부 통과.

- [ ] **Step 7: 커밋**

```bash
git add src/Assembler.py tests/test_assembler.py
git commit -m "$(cat <<'EOF'
feat: import 문(경로 문자열, alias 이름) 파싱 추가

경로 표현식이 문자열 리터럴인지는 검증하지 않고 그대로 ImportStmt.path 에
담는다 — 그 검증은 Checker 단계에서 한다.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Checker — import 기본 검사 (경로 리터럴 / 파일 존재 / alias 등록)

**Files:**
- Modify: `src/Checker.py`
- Test: `tests/test_checker.py`

**Interfaces:**
- Consumes: `common.ImportStmt` (Task 2)
- Produces: `StaticChecker._check_import_stmt(stmt, scopes)` — 경로가 문자열 리터럴이 아니거나 파일이 없으면 `CheckError`. 통과하면 `scopes.declare(stmt.alias, ...)`로 alias를 현재 스코프에 등록 (이 한 줄 덕분에 alias 이름 충돌과 블록 스코프 밖 참조는 **기존 `_ScopeStack.declare`/`push`/`pop` 로직이 그대로 처리**한다 — 새 코드 불필요).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_checker.py` 상단 import 블록에 `ImportStmt`, `LiteralExpr`(이미 있을 수 있음) 추가하고, 헬퍼 섹션에 추가:

```python
def import_stmt(path_expr, alias: str, line: int = 1, col: int = 1) -> ImportStmt:
    return ImportStmt(path=path_expr, alias=alias, location=loc(line, col))
```

테스트 파일 아무 하단에 새 클래스로 추가:

```python
class TestImportStmt:
    def test_path_must_be_string_literal(self):
        program = prog(import_stmt(ident("sum"), alias="sum"))
        with pytest.raises(CheckError, match="string"):
            check(program)

    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "missing.cf"
        program = prog(import_stmt(lit(str(missing)), alias="m"))
        with pytest.raises(CheckError, match="not found"):
            check(program)

    def test_valid_import_declares_alias_in_scope(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            import_stmt(lit(str(lib)), alias="m"),
            print_stmt(ident("m")),
        )
        check(program)  # 예외 없이 통과해야 한다
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/test_checker.py::TestImportStmt -v
```

Expected: 3개 다 FAIL — `_check_import_stmt`가 아직 없어서 `_check_stmt`의 `method_name is None` 분기를 타고 `"Unsupported statement type: ImportStmt"`로 실패.

- [ ] **Step 3: `_STMT_DISPATCH`에 등록**

```python
    _STMT_DISPATCH: ClassVar[dict[type, str]] = {
        VarStmt:        "_check_var_stmt",
        SetStmt:        "_check_set_stmt",
        PrintStmt:      "_check_print_stmt",
        ExpressionStmt: "_check_exprstmt",
        BlockStmt:      "_check_block_stmt",
        IfStmt:         "_check_if_stmt",
        ForStmt:        "_check_for_stmt",
        FuncDefStmt:    "_check_func_stmt",
        ReturnStmt:     "_check_return_stmt",
        ClassStmt:      "_check_class_stmt",
        ImportStmt:     "_check_import_stmt",
    }
```

`ImportStmt`를 파일 상단 `from common import (...)` 블록에도 추가한다.

- [ ] **Step 4: `check()`에 import 관련 상태 초기화 추가**

`check()` 메서드를 아래로 교체 (기존 `_method_stack` 초기화 옆에 나란히 추가):

```python
    def check(self, program: Program) -> None:
        scopes = _ScopeStack()
        self._method_stack: list[dict] = []  # [{class_name, has_parent, is_init}]
        self._import_stack: list[str] = []  # 순환 임포트 감지용 (절대경로 스택)
        self._check_program(program, scopes)

    def _check_program(self, program: Program, scopes: _ScopeStack) -> None:
        for stmt in program.statements:
            self._check_stmt(stmt, scopes)
```

(`_check_program`을 분리해두는 이유는, 임포트한 파일을 재귀적으로 검사할 때
`_method_stack`/`_import_stack`은 그대로 유지한 채 새 `_ScopeStack`만 새로
써야 하기 때문 — Task 6에서 사용한다.)

- [ ] **Step 5: `_check_import_stmt` 최소 구현**

`_check_class_stmt` 메서드 바로 아래에 추가. 파일 상단에 `from pathlib import Path` 추가:

```python
    def _check_import_stmt(self, stmt: ImportStmt, scopes: _ScopeStack) -> None:
        loc = stmt.location
        loc_str = f" at {loc.line}:{loc.column}" if loc else ""

        if not isinstance(stmt.path, LiteralExpr) or not isinstance(stmt.path.value, str):
            raise CheckError(f"import path must be a string literal{loc_str}")

        path = stmt.path.value
        file_path = Path(path)
        if not file_path.exists():
            raise CheckError(f"Imported file not found: '{path}'{loc_str}")

        scopes.declare(stmt.alias, stmt.location)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/test_checker.py::TestImportStmt -v
```

Expected: 3개 다 PASS

- [ ] **Step 7: 전체 test_checker.py 회귀 확인**

```bash
.venv/bin/pytest tests/test_checker.py -q
```

Expected: 전부 통과.

- [ ] **Step 8: 커밋**

```bash
git add src/Checker.py tests/test_checker.py
git commit -m "$(cat <<'EOF'
feat: Checker에 import 기본 검사 추가 (경로 리터럴/파일존재/alias 등록)

alias 이름 충돌과 블록 스코프 이탈 검사는 새 로직 없이 기존
_ScopeStack.declare/push/pop 을 재사용한다.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Checker — 순환 참조 / 중복 임포트 / for문 제한 + 임포트 파일 재귀 검사

**Files:**
- Modify: `src/Checker.py`
- Test: `tests/test_checker.py`

**Interfaces:**
- Consumes: `Tokenizer.tokenize`, `Assembler.assemble` (임포트 대상 파일을 재귀적으로 검사하기 위해 처음으로 Checker가 이 두 모듈에 의존하게 된다)
- Produces: `_ScopeStack.mark_imported(abs_path: str) -> bool` (현재 스코프에서 처음 보는 경로면 등록하고 `True`, 이미 있으면 `False`), `_check_import_stmt`가 순환/중복/for문 제한을 전부 `CheckError`로 처리하고 임포트 대상 파일 자체도 재귀적으로 검사

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_checker.py`의 `TestImportStmt` 클래스에 추가:

```python
    def test_duplicate_import_same_scope_raises(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            import_stmt(lit(str(lib)), alias="a"),
            import_stmt(lit(str(lib)), alias="b"),
        )
        with pytest.raises(CheckError, match="already imported|duplicate"):
            check(program)

    def test_alias_collision_with_existing_variable_raises(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            var("sum", init=lit(0.0)),
            import_stmt(lit(str(lib)), alias="sum"),
        )
        with pytest.raises(CheckError, match="already declared"):
            check(program)

    def test_import_cycle_raises(self, tmp_path):
        a = tmp_path / "a.cf"
        b = tmp_path / "b.cf"
        a.write_text(f'(import "{b}" alias b)', encoding="utf-8")
        b.write_text(f'(import "{a}" alias a)', encoding="utf-8")
        program = prog(import_stmt(lit(str(a)), alias="a"))
        with pytest.raises(CheckError, match="circular|cycle|순환"):
            check(program)

    def test_import_inside_for_loop_raises(self, tmp_path):
        lib = tmp_path / "lib.cf"
        lib.write_text("(var answer 1)", encoding="utf-8")
        program = prog(
            for_stmt("i", lit(0.0), lit(1.0), import_stmt(lit(str(lib)), alias="m")),
        )
        with pytest.raises(CheckError, match="for|loop"):
            check(program)

    def test_imported_file_own_errors_propagate_as_check_error(self, tmp_path):
        lib = tmp_path / "broken.cf"
        lib.write_text("(print notDefined)", encoding="utf-8")
        program = prog(import_stmt(lit(str(lib)), alias="m"))
        with pytest.raises(CheckError, match="notDefined"):
            check(program)
```

`test_alias_collision_with_existing_variable_raises`는 이미 Task 5의 `_check_import_stmt` 최소 구현으로 통과할 수도 있다 (declare가 이미 있으므로) — 그래도 회귀 방지용으로 같이 추가해둔다.

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/test_checker.py::TestImportStmt -v
```

Expected: `test_duplicate_import_same_scope_raises`, `test_import_cycle_raises`, `test_import_inside_for_loop_raises`, `test_imported_file_own_errors_propagate_as_check_error`가 FAIL (순환/중복 감지와 파일 내용 검사가 아직 없음). `test_alias_collision_with_existing_variable_raises`는 이미 PASS일 수 있음.

- [ ] **Step 3: `_ScopeStack`에 임포트 경로 추적 추가**

`_ScopeStack.__init__`, `push`, `pop`을 아래로 교체 (기존 `_class_names_stack`과 나란히 `_imported_paths_stack` 추가):

```python
    def __init__(self) -> None:
        # 전역 스코프에 내장 연산자를 미리 등록한다
        self._stack: list[dict[str, SourceLocation | None]] = [
            {name: None for name in BUILTIN_OPS}
        ]
        self._class_names_stack: list[set[str]] = [set()]
        self._imported_paths_stack: list[set[str]] = [set()]
        self._declaring: str | None = None

    def push(self) -> None:
        self._stack.append({})
        self._class_names_stack.append(set())
        self._imported_paths_stack.append(set())

    def pop(self) -> None:
        self._stack.pop()
        self._class_names_stack.pop()
        self._imported_paths_stack.pop()
```

`is_class_name` 메서드 바로 아래에 추가:

```python
    def mark_imported(self, abs_path: str) -> bool:
        """현재(가장 안쪽) 스코프에 이 경로가 이미 임포트돼 있으면 False,
        아니면 등록하고 True 를 반환한다."""
        current = self._imported_paths_stack[-1]
        if abs_path in current:
            return False
        current.add(abs_path)
        return True
```

- [ ] **Step 4: for문 진입 카운터 추가**

`_check_for_stmt`를 아래로 교체:

```python
    def _check_for_stmt(self, stmt: ForStmt, scopes: _ScopeStack) -> None:
        # start / end 는 for 스코프 밖(현재 스코프)에서 평가된다
        self._check_expr(stmt.start, scopes)
        self._check_expr(stmt.end, scopes)

        # 반복자 변수는 for 전용 스코프에 선언한다
        scopes.push()
        scopes.declare(stmt.iterator, stmt.location)
        self._in_for = getattr(self, "_in_for", 0) + 1
        self._check_stmt(stmt.body, scopes)
        self._in_for -= 1
        scopes.pop()
```

- [ ] **Step 5: `_check_import_stmt`를 순환/중복/for문 검사 + 재귀 검사로 확장**

파일 상단에 `from Tokenizer import tokenize`, `from Assembler import assemble`를 추가한다 (Checker가 처음으로 이 두 모듈에 의존하게 된다 — import 문 자체가 대상 파일의 정적 정합성까지 검증해야 하므로 필요한 의존성이다).

`_check_import_stmt`를 아래로 교체:

```python
    def _check_import_stmt(self, stmt: ImportStmt, scopes: _ScopeStack) -> None:
        loc = stmt.location
        loc_str = f" at {loc.line}:{loc.column}" if loc else ""

        if getattr(self, "_in_for", 0) > 0:
            raise CheckError(f"'import' cannot be used inside a for loop{loc_str}")

        if not isinstance(stmt.path, LiteralExpr) or not isinstance(stmt.path.value, str):
            raise CheckError(f"import path must be a string literal{loc_str}")

        path = stmt.path.value
        file_path = Path(path)
        if not file_path.exists():
            raise CheckError(f"Imported file not found: '{path}'{loc_str}")

        abs_path = str(file_path.resolve())
        if abs_path in self._import_stack:
            raise CheckError(f"Circular import (순환 참조) detected: '{path}'{loc_str}")
        if not scopes.mark_imported(abs_path):
            raise CheckError(
                f"'{path}' is already imported in this scope (duplicate import){loc_str}"
            )

        source = file_path.read_text(encoding="utf-8")
        self._import_stack.append(abs_path)
        try:
            imported_program = assemble(tokenize(source))
            self._check_program(imported_program, _ScopeStack())
        finally:
            self._import_stack.pop()

        scopes.declare(stmt.alias, stmt.location)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/test_checker.py::TestImportStmt -v
```

Expected: 전부 PASS (7개).

- [ ] **Step 7: 전체 test_checker.py 회귀 확인**

```bash
.venv/bin/pytest tests/test_checker.py -q
```

Expected: 전부 통과.

- [ ] **Step 8: 커밋**

```bash
git add src/Checker.py tests/test_checker.py
git commit -m "$(cat <<'EOF'
feat: import 순환/중복/for문제한 검사 및 대상 파일 재귀 검사 추가

_ScopeStack 에 스코프별 임포트 경로 추적(mark_imported)을 추가하고,
Checker 가 처음으로 Tokenizer/Assembler 에 의존해 임포트 대상 파일도
재귀적으로 tokenize/assemble/check 한다.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Executor — Module 런타임 값과 import 실행

**Files:**
- Modify: `src/Executor.py`
- Test: `tests/test_executor.py`

**Interfaces:**
- Consumes: `common.ImportStmt` (Task 2), `Tokenizer.tokenize`, `Assembler.assemble`, `Checker.check`
- Produces: `Module(name: str, environment: Environment)` dataclass, `SExpressionExecutor._execute_importstmt(stmt) -> None` — 대상 파일을 독립된 `Environment`로 전부 실행한 뒤 그 `Environment`를 `Module`로 감싸 alias 이름으로 현재 `Environment`에 `define`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_executor.py`에 추가 (파일 상단이 `from common import *` / `from Executor import *`라 `ImportStmt`, `DotExpr`, `IdentifierExpr` 등은 이미 임포트되어 있다):

```python
def test_execute_import_defines_module_and_reads_variable(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(DotExpr(obj=IdentifierExpr("m"), slot="answer", args=())),
    ))
    assert execute(program) == 42.0


def test_execute_import_isolates_module_namespace(tmp_path):
    """임포트한 파일 안의 변수는 메인 프로그램 스코프로 새지 않는다."""
    lib = tmp_path / "lib.cf"
    lib.write_text("(var secret 1)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(IdentifierExpr("secret")),
    ))
    with pytest.raises(ExecuteError):
        execute(program)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/test_executor.py::test_execute_import_defines_module_and_reads_variable tests/test_executor.py::test_execute_import_isolates_module_namespace -v
```

Expected: 첫 번째 테스트는 `"Unsupported statement: ImportStmt"` `ExecuteError`로 FAIL. 두 번째 테스트는 이미 `ExecuteError`가 나긴 하지만(같은 이유로) — Step 3~4를 마친 뒤 "올바른 이유로" 실패하는지 다시 확인한다.

- [ ] **Step 3: `Module` 런타임 값 정의 + `_STMT_DISPATCH` 등록**

파일 상단 `from common import (...)`에 `ImportStmt`를 추가하고, `from pathlib import Path`를 추가한다. `Function`/`_ReturnSignal` 정의 바로 아래에 추가:

```python
@dataclass
class Module:
    name: str
    environment: "Environment"
```

`_STMT_DISPATCH`에 한 줄 추가:

```python
    _STMT_DISPATCH: ClassVar[dict[type, str]] = {
        ExpressionStmt: "_execute_exprstmt",
        PrintStmt:      "_execute_printstmt",
        VarStmt:        "_execute_varstmt",
        SetStmt:        "_execute_setstmt",
        IfStmt:         "_execute_ifstmt",
        ForStmt:        "_execute_forstmt",
        BlockStmt:      "_execute_blockstmt",
        FuncDefStmt:    "_execute_funcdefstmt",
        ReturnStmt:     "_execute_returnstmt",
        ClassStmt:      "_execute_classstmt",
        ImportStmt:     "_execute_importstmt",
    }
```

- [ ] **Step 4: `_execute_importstmt` 구현**

`_execute_classstmt` 메서드 바로 아래에 추가. 파일 상단에 `from Tokenizer import tokenize`, `from Assembler import assemble`, `from Checker import check`도 추가한다 (Checker가 이미 대상 파일을 검증했지만, Executor는 독립적으로 자신의 파이프라인을 다시 돌린다 — 각 단계가 서로 독립적으로 동작하는 기존 설계와 일관된 선택):

```python
    def _execute_importstmt(self, stmt: ImportStmt) -> RuntimeValue:
        path = stmt.path.value  # Checker 가 이미 문자열 리터럴임을 검증했다
        source = Path(path).read_text(encoding="utf-8")
        imported_program = assemble(tokenize(source))
        check(imported_program)

        module_env = Environment()
        previous = self._environment
        self._environment = module_env
        try:
            for s in imported_program.statements:
                self._execute_stmt(s)
        finally:
            self._environment = previous

        self._environment.define(stmt.alias, Module(name=stmt.alias, environment=module_env))
        return None
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/test_executor.py::test_execute_import_defines_module_and_reads_variable tests/test_executor.py::test_execute_import_isolates_module_namespace -v
```

Expected: 첫 번째는 아직 FAIL — `_execute_dot_expr`이 `Module`을 모르므로 `"'.' operator requires an instance object"` `ExecuteError`가 남 (Task 8에서 해결). 두 번째는 이제 "올바른 이유"(`secret`이라는 이름이 메인 스코프에 없음)로 PASS.

- [ ] **Step 6: 커밋**

```bash
git add src/Executor.py tests/test_executor.py
git commit -m "$(cat <<'EOF'
feat: import 문 실행 시 대상 파일을 독립 Environment 에서 실행해 Module 값 생성

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Executor — DotExpr의 Module 분기 (멤버 읽기 / 함수 멤버 호출)

**Files:**
- Modify: `src/Executor.py`
- Test: `tests/test_executor.py`

**Interfaces:**
- Consumes: `Module` (Task 7), `Function`/`_call_function` (이미 존재)
- Produces: `_execute_dot_expr`가 `obj`가 `Module`일 때: 인자가 없으면 멤버 값을 그대로 반환, 인자가 있으면 그 멤버가 `Function`인지 확인 후 호출

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_executor.py`에 추가:

```python
def test_execute_dot_expr_calls_function_member_of_module(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text(
        "(func add (a b) { (return (+ a b)) })",
        encoding="utf-8",
    )
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(
            DotExpr(
                obj=IdentifierExpr("m"),
                slot="add",
                args=(LiteralExpr(1.0), LiteralExpr(2.0)),
            )
        ),
    ))
    assert execute(program) == 3.0


def test_execute_dot_expr_missing_module_member_raises(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(DotExpr(obj=IdentifierExpr("m"), slot="missing", args=())),
    ))
    with pytest.raises(ExecuteError):
        execute(program)


def test_execute_dot_expr_calling_non_function_member_raises(tmp_path):
    lib = tmp_path / "lib.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    program = Program((
        ImportStmt(path=LiteralExpr(str(lib)), alias="m"),
        ExpressionStmt(
            DotExpr(obj=IdentifierExpr("m"), slot="answer", args=(LiteralExpr(1.0),))
        ),
    ))
    with pytest.raises(ExecuteError):
        execute(program)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/test_executor.py::test_execute_dot_expr_calls_function_member_of_module tests/test_executor.py::test_execute_dot_expr_missing_module_member_raises tests/test_executor.py::test_execute_dot_expr_calling_non_function_member_raises -v
```

Expected: 세 개 다 FAIL — `_execute_dot_expr`가 `Module`을 `ClassInstance`가 아니라고 보고 `"'.' operator requires an instance object"`를 던짐 (두 번째, 세 번째 테스트는 이미 `ExecuteError`가 나긴 하지만 "잘못된 이유"로 나는 것 — 구현 후 "올바른 이유"로 나는지 Step 4에서 확인).

- [ ] **Step 3: `_execute_dot_expr`에 Module 분기 추가**

`_execute_dot_expr` 메서드 전체를 아래로 교체 (맨 앞에 `Module` 분기를 추가하고, 그 아래 기존 `ClassInstance` 처리 로직은 그대로 유지):

```python
    def _execute_dot_expr(self, expr: DotExpr) -> RuntimeValue:
        obj = self._execute_expr(expr.obj)

        if isinstance(obj, Module):
            value = obj.environment.lookup(expr.slot)
            args = [self._execute_expr(a) for a in expr.args]
            if not args:
                return value
            if not isinstance(value, Function):
                raise ExecuteError(
                    f"'{expr.slot}' is not callable in module '{obj.name}'"
                )
            return self._call_function(value, args)

        if not isinstance(obj, ClassInstance):
            raise ExecuteError(
                f"'.' operator requires an instance object, got {type(obj).__name__!r}"
            )

        args = [self._execute_expr(a) for a in expr.args]
        slot = expr.slot

        # 메서드 우선 탐색
        method_result = obj.class_def.lookup_method(slot)
        if method_result is not None:
            method_def, defining_class = method_result
            return self._call_method(obj, method_def, defining_class, args)

        # 필드 처리 — 구 문법은 pre-declared(obj.fields에 None으로 존재),
        # 새 문법은 set-field! 로 동적 생성
        if len(args) == 0:  # 읽기
            if slot in obj.fields:
                return obj.fields[slot]
            raise ExecuteError(
                f"'{obj.class_def.name}' has no field or method '{slot}'"
            )
        if len(args) == 1:  # 쓰기 (새 필드 동적 생성 포함)
            obj.fields[slot] = args[0]
            return args[0]
        raise ExecuteError(
            f"Field '{slot}' expects 0 (read) or 1 (write) argument(s), got {len(args)}"
        )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/pytest tests/test_executor.py::test_execute_dot_expr_calls_function_member_of_module tests/test_executor.py::test_execute_dot_expr_missing_module_member_raises tests/test_executor.py::test_execute_dot_expr_calling_non_function_member_raises tests/test_executor.py::test_execute_import_defines_module_and_reads_variable -v
```

Expected: 전부 PASS.

- [ ] **Step 5: 전체 test_executor.py 및 클래스 관련 회귀 확인**

```bash
.venv/bin/pytest tests/test_executor.py -q
.venv/bin/pytest tests/additional_test/additional_class_integration.py -q
```

Expected: 둘 다 전부 통과 (class 쪽 `DotExpr` 처리를 건드렸으므로 회귀 여부를 반드시 확인).

- [ ] **Step 6: 커밋**

```bash
git add src/Executor.py tests/test_executor.py
git commit -m "$(cat <<'EOF'
feat: DotExpr 실행에 Module 분기 추가 (멤버 읽기 / 함수 멤버 호출)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: 통합 테스트 — 기존 8개 확인 + 정상/예외 케이스 각 1개 추가

**Files:**
- Modify: `tests/additional_test/additional_import_integration.py`

**Interfaces:**
- Consumes: Task 2~8에서 만든 전체 import 파이프라인
- Produces: 없음 (테스트만 추가/검증)

- [ ] **Step 1: 기존 8개 통합 테스트가 전부 통과하는지 먼저 확인**

```bash
.venv/bin/pytest tests/additional_test/additional_import_integration.py -v
```

Expected: 8개 전부 PASS. 하나라도 실패하면 Task 2~8 중 어디가 스펙과 어긋났는지 먼저 잡고 넘어간다 (아래 Step을 진행하지 않는다).

- [ ] **Step 2: 정상 동작 케이스 추가 (모듈 변수를 직접 읽기 — Task 3의 dotted-atom fix를 직접 검증)**

파일 끝(`test_import_inside_for_loop_raises_check_error` 다음)에 추가:

```python
def test_import_read_variable_from_module_without_calling(tmp_path, capsys):
    lib = tmp_path / "constants.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    source = f"""
    (import "{lib}" alias constants)
    (print constants.answer)
    """
    _run(source)
    assert capsys.readouterr().out.strip() == "42.0"
```

- [ ] **Step 3: 예외 동작 케이스 추가 (기존 8개가 전부 CheckError였던 것과 달리, ExecuteError 계층 커버)**

```python
def test_import_calling_missing_member_raises_execute_error(tmp_path):
    lib = tmp_path / "sum.cf"
    lib.write_text("(var answer 42)", encoding="utf-8")
    source = f"""
    (import "{lib}" alias sum)
    (print (sum.add 1 2))
    """
    with pytest.raises(ExecuteError):
        _run(source)
```

이 파일 상단에 `ExecuteError`가 이미 `from common import CheckError, ExecuteError`로 임포트되어 있는지 확인 (없으면 추가).

- [ ] **Step 4: 10개 전부 통과 확인**

```bash
.venv/bin/pytest tests/additional_test/additional_import_integration.py -v
```

Expected: 10 passed.

- [ ] **Step 5: 커밋**

```bash
git add tests/additional_test/additional_import_integration.py
git commit -m "$(cat <<'EOF'
test: import 통합 테스트에 정상/예외 케이스 각 1건 추가

기존 8개는 전부 CheckError 시나리오였어서, ExecuteError 계층(존재하지
않는 모듈 멤버 호출)을 커버하는 예외 케이스와, dotted 원자 읽기 fix를
직접 검증하는 정상 케이스를 추가.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: 전체 회귀 테스트 및 마무리

**Files:**
- (읽기 전용 — 코드 변경 없음)

**Interfaces:**
- Consumes: Task 1~9의 전체 결과물
- Produces: 최종 검증된 브랜치

- [ ] **Step 1: 전체 테스트 스위트 실행**

```bash
.venv/bin/pytest -q
```

Expected: 기존 테스트 + 이번에 추가한 유닛 테스트 전부 통과, 실패 0건.

- [ ] **Step 2: additional_test 전체 실행 (function/class/array/import)**

```bash
.venv/bin/pytest tests/additional_test/additional_function_integration.py tests/additional_test/additional_class_integration.py tests/additional_test/additional_static_array_integration.py tests/additional_test/additional_import_integration.py -v
```

Expected: 7 + 11 + 7 + 10 = 35 passed.

- [ ] **Step 3: 브랜치 상태 확인**

```bash
git log --oneline master..HEAD
git status
```

Expected: Task 1~9에서 만든 커밋들이 순서대로 보이고, working tree는 깨끗해야 한다.

- [ ] **Step 4: 사용자에게 보고**

이 시점에서 구현이 끝났으니, PR을 올릴지(원격 push + PR 생성) 여부를 사용자에게 확인한다. 이 계획 문서는 push/PR 생성 여부를 자동으로 결정하지 않는다 — 항상 명시적으로 확인받는다.
