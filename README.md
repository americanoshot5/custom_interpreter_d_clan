# S-Expression 언어 사용 가이드

이 인터프리터가 실행하는 언어는 **S-expression** (괄호 기반) 문법을 사용합니다.  
모든 연산과 제어 흐름은 `(연산자 인자1 인자2 ...)` 형태로 표현됩니다.

---

## 목차

1. [구현 체크리스트](#1-구현-체크리스트)
2. [인터프리터 실행방법](#2-인터프리터-실행방법)
3. [언어의 기본적인 사용방법](#3-언어의-기본적인-사용방법)

## 1. 구현 체크리스트

| 완료 | 추가 기능 | 설명 |
|------|-----------|------|
| ☑ | Function | 함수 정의, 함수 호출, 재귀, return 처리 |
| ☑ | Class | 클래스 선언, 인스턴스 생성, 메서드, 상속, `Super` |
| ☑ | 정적배열 | 배열 생성, 인덱스 조회, 인덱스 값 변경 |
| ☑ | Import 문 | 외부 `.cf` 파일을 모듈 alias로 불러오기 |
| ☑ | 실행전 최적화 | 상수 접기와 최적화 통계 확인 |
| ☑ | 제어 쉘 제작 | Prompt mode, File mode, Debug mode, watch variable |

---

## 2. 인터프리터 실행방법

별도 패키지 설치 없이 `python3`만 있으면 실행할 수 있습니다.  
`import` 문의 상대 경로가 실행 위치 기준으로 해석되므로, 아래 명령은 **저장소 루트 디렉터리**에서 실행하세요.

### 프롬프트 모드

파일 없이 대화형으로 한 줄씩 입력해보고 싶을 때 사용합니다.

```bash
python3 src/factory_shell.py prompt
```

또는 동일하게 동작하는 기존 프롬프트 셸을 직접 실행할 수 있습니다.

```bash
python3 src/prompt_shell.py
```

실행하면 프롬프트가 나타납니다.

```
>>>
```

### 입력 방법

- **한 줄 입력**: 괄호가 닫힌 표현식을 입력하고 **Enter** → 즉시 실행됩니다.
- **여러 줄 입력**: 여러 줄에 걸쳐 입력하고 **빈 줄(Enter)** 을 입력하면 실행됩니다.

```
>>> (+ 1 2)
3.0

>>> (var x 10)
... (var y 20)
... (+ x y)
...
30.0
```

- `exit` 또는 `quit` 를 입력하면 종료됩니다.

### 파일 모드

`.cf` 파일을 한 번에 실행할 때 사용합니다.

```bash
python3 src/factory_shell.py run demo/demo1_basics.cf
```

하위 호환을 위해 서브커맨드 없이 파일 경로만 줘도 `run`과 동일하게 동작합니다.

```bash
python3 src/factory_shell.py demo/demo1_basics.cf
```

### 디버그 모드

소스 코드를 statement 단위로 멈추며 직접 확인할 때 사용합니다.

```bash
python3 src/factory_shell.py debug demo/demo4_debug_target.cf
```

`(debug)` 프롬프트가 뜨면 아래 명령을 입력할 수 있습니다.

| 명령 | 설명 |
|------|------|
| `break <줄번호>` / `remove <줄번호>` | 브레이크포인트 설정/해제 |
| `watch <변수명>` / `unwatch <변수명>` | 변수 감시 설정/해제 |
| `step` 또는 `next` | 한 줄 실행 |
| `continue` | 다음 브레이크포인트 또는 프로그램 끝까지 실행 |
| `breakpoints` / `watches` | 설정된 브레이크포인트/watch 목록 확인 |
| `inspect` | 현재 스코프의 모든 변수 값 확인 |
| `exit` | 종료 |

### 데모 실행

주요 기능을 바로 확인하려면 `demo/` 아래 예제를 실행하면 됩니다.

```bash
python3 src/factory_shell.py run demo/demo1_basics.cf
python3 src/factory_shell.py run demo/demo2_functions.cf
python3 src/factory_shell.py run demo/demo3_classes_and_modules.cf
python3 demo/demo4_debugging.py
```

| 파일 | 다루는 기능 |
|------|-------------|
| `demo/demo1_basics.cf` | 변수, 산술/비교 연산자, 조건문, 반복문, 블록 스코프, 배열 |
| `demo/demo2_functions.cf` | 함수 정의/호출, 재귀, 클로저 |
| `demo/demo3_classes_and_modules.cf` | 클래스, 상속(`Super`), `instanceof`, 모듈 `import` |
| `demo/demo4_debugging.py` + `demo/demo4_debug_target.cf` | 디버그 모드 자동 시나리오, break/step/watch/inspect |

`demo/demo3_module_utils.cf`는 `demo/demo3_classes_and_modules.cf`가 import로 불러오는 보조 모듈 파일이라 직접 실행할 필요는 없습니다.

---

## 3. 언어의 기본적인 사용방법

### 3.1 리터럴 값

| 종류 | 예시 | 설명 |
|------|------|------|
| 정수/실수 | `42`, `3.14`, `-7` | 모든 숫자는 실수로 처리됩니다 |
| 문자열 | `"hello"`, `"world"` | 큰따옴표로 감쌉니다 |
| 불리언 | `true`, `false` | 대소문자 구분 |
| null | `null` | 빈 값 |

```
>>> 42
42.0

>>> "hello"
hello

>>> true
True
```

---

### 3.2 변수

#### 변수 선언

```
(var 이름 초기값)
(var 이름)          ; 초기값 없이 선언 (null로 초기화)
```

```
>>> (var name "Alice")
>>> (var count 0)
>>> (var flag)      ; null
```

#### 변수 재할당

```
(set! 이름 새값)
```

```
>>> (var x 10)
>>> (set! x 99)
>>> x
99.0
```

> **주의**: `set!`은 이미 선언된 변수에만 사용 가능합니다. 새 변수 생성에는 `var`을 쓰세요.

---

### 3.3 연산자

모든 연산자는 `(연산자 인자...)` 형태로 사용합니다.

#### 산술 연산

```
(+ a b)   ; 덧셈 (문자열 이어붙이기도 가능)
(- a b)   ; 뺄셈
(* a b)   ; 곱셈
(/ a b)   ; 나눗셈
(- x)     ; 단항 음수
```

```
>>> (+ 3 4)
7.0

>>> (+ "hello" " world")
hello world

>>> (* 6 7)
42.0
```

#### 비교 연산

```
(< a b)   ; a < b
(> a b)   ; a > b
(= a b)   ; a == b
```

```
>>> (< 3 5)
True

>>> (= "hi" "hi")
True
```

#### 논리 연산

```
(and a b)   ; 논리 AND
(or  a b)   ; 논리 OR
(not x)     ; 논리 NOT
```

```
>>> (and true false)
False

>>> (not (< 10 5))
True
```

#### 중첩 표현식

```
>>> (* (+ 2 3) (- 10 4))
30.0
```

---

### 3.4 출력

```
(print 표현식)
```

```
>>> (print "Hello, World!")
Hello, World!

>>> (var name "Alice")
>>> (print (+ "Hi, " name))
Hi, Alice
```

---

### 3.5 조건문

```
(if 조건 then_문)
(if 조건 then_문 else_문)
```

```
>>> (var x 10)
>>> (if (> x 5)
...   (print "크다")
...   (print "작다"))
...
크다
```

여러 문장을 실행하려면 **블록** `{ ... }` 을 사용합니다.

```
>>> (var score 85)
>>> (if (>= score 90)
...   { (print "A") (print "우수") }
...   { (print "B") (print "보통") })
...
B
보통
```

> **팁**: `>=`, `<=` 연산자는 없습니다. `(not (< a b))` 처럼 조합해 쓰세요.

---

### 3.6 반복문

```
(for 변수 시작 끝 본문)
```

변수는 `시작`부터 `끝-1`까지 순회합니다 (`[시작, 끝)` 범위).

```
>>> (for i 0 5
...   (print i))
...
0
1
2
3
4
```

외부 변수 누적 예:

```
>>> (var sum 0)
>>> (for i 1 6
...   (set! sum (+ sum i)))
>>> sum
15.0
```

---

### 3.7 블록

중괄호 `{ }` 로 여러 문장을 하나의 단위로 묶습니다. 블록은 자체 스코프를 가집니다.

```
{
  (var temp 100)
  (print temp)
}
```

블록 안에서 선언된 변수는 블록 밖에서 접근할 수 없습니다.

```
>>> (var x 1)
>>> {
...   (var x 99)
...   (print x)
... }
...
99
>>> x
1.0        ; 바깥쪽 x는 그대로
```

---

### 3.8 함수

#### 함수 정의

```
(func 함수이름 (파라미터...) 본문)
```

```
>>> (func add (a b)
...   (return (+ a b)))
```

#### 함수 호출

```
(함수이름 인자...)
```

```
>>> (add 3 4)
7.0
```

#### return

```
(return 값)
(return)     ; 값 없이 반환 (null 반환)
```

#### 예제: 재귀 함수

```
(func factorial (n)
  (if (= n 0)
    (return 1)
    (return (* n (factorial (- n 1))))))

(factorial 5)   ; → 120.0
```

#### 클로저

함수는 정의된 시점의 스코프를 기억합니다.

```
(var base 10)
(func addBase (x)
  (return (+ base x)))

(addBase 5)   ; → 15.0
```

---

### 3.9 배열

#### 배열 생성

```
[크기]           ; 배열 리터럴 (모두 null로 초기화)
(Array 크기)     ; 동일
```

```
>>> (var arr [5])
>>> arr
[None, None, None, None, None]
```

#### 원소 읽기

```
배열[인덱스]       ; 인덱스 연산자 (0부터 시작)
(index 배열 인덱스)
```

```
>>> (var arr [3])
>>> (set-index! arr 0 "hello")
>>> arr[0]
hello
```

#### 원소 쓰기

```
(set-index! 배열 인덱스 값)
```

#### 배열 전체 예제

```
(var scores [4])
(set-index! scores 0 90)
(set-index! scores 1 85)
(set-index! scores 2 78)
(set-index! scores 3 92)

(var sum 0)
(for i 0 4
  (set! sum (+ sum scores[i])))

(print (/ sum 4))   ; 평균 → 86.25
```

> **주의**: 인덱스 범위를 벗어나면 에러가 발생합니다.

---

### 3.10 클래스

#### 클래스 정의

```
(class 클래스이름 {
  (method 메서드이름 (파라미터...) {
    본문...
  })
})
```

- `init` 메서드는 생성자입니다.
- 메서드 안에서 `This` 로 현재 인스턴스에 접근합니다.

```
(class Point {
  (method init (x y) {
    (set-field! This x x)
    (set-field! This y y)
  })
  (method describe () {
    (return (+ (+ "(" (get-field This x)) ")"))
  })
})
```

#### 인스턴스 생성

```
(클래스이름 인자...)
```

```
>>> (var p (Point 3 4))
```

#### 메서드 호출

```
(인스턴스.메서드이름 인자...)
```

```
>>> (p.describe)
(3.0)
```

#### 필드 읽기/쓰기

```
(get-field 인스턴스 필드이름)       ; 읽기
(set-field! 인스턴스 필드이름 값)   ; 쓰기
```

```
>>> (get-field p x)
3.0

>>> (set-field! p x 10)
>>> (get-field p x)
10.0
```

#### 상속

```
(class 자식클래스 : 부모클래스 {
  (method 메서드이름 (파라미터...) {
    본문...
  })
})
```

부모 메서드 호출:

```
(Super.메서드이름 인자...)
```

```
(class Animal {
  (method speak () {
    (return "...")
  })
})

(class Dog : Animal {
  (method speak () {
    (return (+ (Super.speak) " woof!"))
  })
})

(var d (Dog))
(d.speak)   ; → "... woof!"
```

#### instanceof

```
(instanceof 인스턴스 클래스)
```

부모 클래스에 대해서도 `true`를 반환합니다.

```
>>> (instanceof d Dog)
True

>>> (instanceof d Animal)
True

>>> (instanceof 42 Dog)
False
```

#### 클래스 전체 예제

```
(class BankAccount {
  (method init (owner balance) {
    (set-field! This owner owner)
    (set-field! This balance balance)
  })
  (method deposit (amount) {
    (set-field! This balance (+ (get-field This balance) amount))
  })
  (method withdraw (amount) {
    (if (< (get-field This balance) amount)
      (print "잔액 부족")
      { (set-field! This balance (- (get-field This balance) amount))
        (print "출금 완료") })
  })
  (method info () {
    (print (+ (get-field This owner) ": "))
    (print (get-field This balance))
  })
})

(var acc (BankAccount "Alice" 1000))
(acc.deposit 500)
(acc.withdraw 200)
(acc.info)
```

출력:
```
출금 완료
Alice:
1300.0
```

---

### 3.11 모듈 (import)

다른 파일의 코드를 불러와 사용할 수 있습니다.

#### 임포트

```
(import "파일경로" alias 별칭)
```

경로는 현재 실행 위치 기준 상대 경로 또는 절대 경로를 사용합니다.

#### 임포트된 모듈 사용

```
(별칭.함수이름 인자...)
```

**예시**  
`utils.sexp` 파일:
```
(func square (n)
  (return (* n n)))
```

메인 파일:
```
(import "utils.sexp" alias u)
(print (u.square 5))   ; → 25.0
```

> **제약**:
> - 임포트 경로는 반드시 문자열 리터럴이어야 합니다.
> - `for` 루프 안에서는 임포트할 수 없습니다.
> - 같은 스코프에서 동일 파일을 두 번 임포트할 수 없습니다.
> - 순환 임포트(A → B → A)는 금지됩니다.

---

### 3.12 에러 메시지 읽기

에러는 세 종류로 나뉩니다.

| 에러 종류 | 발생 시점 | 예시 |
|-----------|-----------|------|
| `TokenizeError` | 알 수 없는 문자 | `` ` `` 또는 `@` 입력 |
| `AssembleError` | 문법 오류 | 괄호 불일치, 잘못된 구조 |
| `CheckError` | 의미 오류 | 미선언 변수, 중복 선언, 잘못된 `return` 위치 |
| `ExecuteError` | 실행 오류 | 타입 불일치, 인덱스 초과, 없는 메서드 |

```
>>> (+ x 1)
Error: Undefined variable 'x'

>>> (var x 1)
>>> (var x 2)
Error: Variable 'x' is already declared in this scope
```

---

### 3.13 빠른 참조

```
; 변수
(var name value)
(set! name value)

; 출력
(print expr)

; 산술
(+ a b)  (- a b)  (* a b)  (/ a b)  (- x)

; 비교 / 논리
(< a b)  (> a b)  (= a b)
(and a b)  (or a b)  (not x)

; 제어 흐름
(if cond then [else])
(for i start end body)
{ stmt... }

; 함수
(func name (params...) body)
(return value)
(name args...)

; 배열
[size]  array[i]  (set-index! arr i val)

; 클래스
(class Name { (method name (params) { body }) })
(class Child : Parent { ... })
(ClassName args...)
(instance.method args...)
(get-field instance field)
(set-field! instance field value)
(instanceof instance Class)
(Super.method args...)

; 모듈
(import "path" alias name)
(name.func args...)
```
