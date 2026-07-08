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
```

## 데모 목록

| 파일 | 다루는 기능 |
|---|---|
| `demo1_basics.cf` | 변수, 산술/비교 연산자, 조건문(`if`), 반복문(`for`), 블록 스코프, 배열 |
| `demo2_functions.cf` | 함수 정의/호출, 재귀(팩토리얼·피보나치), 클로저 |
| `demo3_classes_and_modules.cf` | 클래스, 상속(`Super`), `instanceof`, 모듈 `import` (같은 폴더의 `demo3_module_utils.cf`를 불러와 사용) |

`demo3_module_utils.cf`는 `demo3_classes_and_modules.cf`가 `import`로 불러오는
보조 모듈 파일이라 직접 실행할 필요는 없습니다.

## 프롬프트 모드로 직접 입력해보기

파일 없이 대화형으로 한 줄씩 입력해보고 싶다면:

```bash
python3 src/prompt_shell.py
```

언어 문법 전체 설명은 저장소 루트의 `README.md`를 참고하세요.
