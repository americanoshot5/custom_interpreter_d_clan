# 데모 실행 가이드

이 폴더의 데모들은 인터프리터의 주요 기능을 실제로 실행해서 확인할 수 있도록
작성됐습니다. 별도 패키지 설치 없이 `python3`만 있으면 됩니다.

## 실행 방법

**반드시 저장소 루트 디렉터리에서** 실행하세요 (`import` 문의 경로가
현재 실행 위치 기준 상대 경로이기 때문입니다).

```bash
python3 src/factory_shell.py demo/demo1_basics.cf
python3 src/factory_shell.py demo/demo2_functions.cf
python3 src/factory_shell.py demo/demo3_classes_and_modules.cf
python3 demo/demo4_debugging.py
```

## 데모 목록

| 파일 | 다루는 기능 |
|---|---|
| `demo1_basics.cf` | 변수, 산술/비교 연산자, 조건문(`if`), 반복문(`for`), 블록 스코프, 배열 |
| `demo2_functions.cf` | 함수 정의/호출, 재귀(팩토리얼·피보나치), 클로저 |
| `demo3_classes_and_modules.cf` | 클래스, 상속(`Super`), `instanceof`, 모듈 `import` (같은 폴더의 `demo3_module_utils.cf`를 불러와 사용) |
| `demo4_debugging.py` + `demo4_debug_target.cf` | 디버그 모드(`run_debug_mode`) — 브레이크포인트, 한 줄씩 실행(step), 변수 watch, 현재 스코프 inspect |

`demo3_module_utils.cf`는 `demo3_classes_and_modules.cf`가 `import`로 불러오는
보조 모듈 파일이라 직접 실행할 필요는 없습니다.

`demo4_debugging.py`는 `factory_shell.run_debug_mode`를 직접 호출하는 파이썬
드라이버 스크립트입니다. 디버그 모드는 사람이 콘솔에 한 줄씩 명령을 입력하는
대화형 인터페이스라, 스크립트 안의 `COMMANDS` 리스트가 `break 6` → `watch total`
→ `continue` → `step` → `step` → `inspect` → `continue` 순서로 실제 입력을
대신 재현하고, 각 단계에서 `total` 값이 어떻게 바뀌는지 로그로 보여줍니다.
`COMMANDS` 리스트의 값을 바꿔서 직접 다른 시나리오로 실험해봐도 됩니다.

## 프롬프트 모드로 직접 입력해보기

파일 없이 대화형으로 한 줄씩 입력해보고 싶다면:

```bash
python3 src/prompt_shell.py
```

데모 `.cf` 파일 내용을 그대로 복사해서 프롬프트 모드에 붙여넣어도 정상
동작합니다 (변수·함수·클래스 정의가 세션 동안 유지됩니다). 다만 파일에
있는 빈 줄마다 그때까지 입력한 내용이 실행되므로, 각 구간의 출력이
한 번에 몰아서 나오지 않고 조금씩 끊어서 출력됩니다. 전체 결과를 한
번에 깔끔하게 보고 싶다면 `factory_shell.py` 파일 모드 실행을 사용하세요.

언어 문법 전체 설명은 저장소 루트의 `README.md`를 참고하세요.
