# S-Expression 언어 사용 가이드

## 추가 기능 구현 현황

| 완료 | 추가 기능 | 설명 |
|------|-----------|------|
| ☑ | Function | 함수 정의, 함수 호출, 재귀, return 처리 |
| ☑ | Class | 클래스 선언, 인스턴스 생성, 메서드, 상속, `Super` |
| ☑ | 정적배열 | 배열 생성, 인덱스 조회, 인덱스 값 변경 |
| ☑ | Import 문 | 외부 `.cf` 파일을 모듈 alias로 불러오기 |
| ☑ | 실행전 최적화 | 상수 접기와 최적화 통계 확인 |
| ☑ | 제어 쉘 제작 | Prompt mode, File mode, Debug mode, watch variable |

---

이 인터프리터가 실행하는 언어는 **S-expression** (괄호 기반) 문법을 사용합니다.  
모든 연산과 제어 흐름은 `(연산자 인자1 인자2 ...)` 형태로 표현됩니다.

---

## 목차

1. [인터프리터 실행하기](#1-인터프리터-실행하기)
2. [리터럴 값](#2-리터럴-값)
3. [변수](#3-변수)
4. [연산자](#4-연산자)
5. [출력](#5-출력)
6. [조건문](#6-조건문)
7. [반복문](#7-반복문)
8. [블록](#8-블록)
9. [함수](#9-함수)
10. [배열](#10-배열)
11. [클래스](#11-클래스)
12. [모듈 (import)](#12-모듈-import)
13. [에러 메시지 읽기](#13-에러-메시지-읽기)

## 1. 인터프리터 실행하기

```
python src/prompt_shell.py
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

---

## 2. 리터럴 값

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

## 3. 변수

### 변수 선언

```
(var 이름 초기값)
(var 이름)          ; 초기값 없이 선언 (null로 초기화)
```

```
>>> (var name "Alice")
>>> (var count 0)
>>> (var flag)      ; null
```

### 변수 재할당

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

## 4. 연산자

모든 연산자는 `(연산자 인자...)` 형태로 사용합니다.

### 산술 연산

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

### 비교 연산

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

### 논리 연산

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

### 중첩 표현식

```
>>> (* (+ 2 3) (- 10 4))
30.0
```

---

## 5. 출력

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

## 6. 조건문

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

## 7. 반복문

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

## 8. 블록

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

## 9. 함수

### 함수 정의

```
(func 함수이름 (파라미터...) 본문)
```

```
>>> (func add (a b)
...   (return (+ a b)))
```

### 함수 호출

```
(함수이름 인자...)
```

```
>>> (add 3 4)
7.0
```

### return

```
(return 값)
(return)     ; 값 없이 반환 (null 반환)
```

### 예제: 재귀 함수

```
(func factorial (n)
  (if (= n 0)
    (return 1)
    (return (* n (factorial (- n 1))))))

(factorial 5)   ; → 120.0
```

### 클로저

함수는 정의된 시점의 스코프를 기억합니다.

```
(var base 10)
(func addBase (x)
  (return (+ base x)))

(addBase 5)   ; → 15.0
```

---

## 10. 배열

### 배열 생성

```
[크기]           ; 배열 리터럴 (모두 null로 초기화)
(Array 크기)     ; 동일
```

```
>>> (var arr [5])
>>> arr
[None, None, None, None, None]
```

### 원소 읽기

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

### 원소 쓰기

```
(set-index! 배열 인덱스 값)
```

### 배열 전체 예제

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

## 11. 클래스

### 클래스 정의

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

### 인스턴스 생성

```
(클래스이름 인자...)
```

```
>>> (var p (Point 3 4))
```

### 메서드 호출

```
(인스턴스.메서드이름 인자...)
```

```
>>> (p.describe)
(3.0)
```

### 필드 읽기/쓰기

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

### 상속

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

### instanceof

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

### 클래스 전체 예제

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

## 12. 모듈 (import)

다른 파일의 코드를 불러와 사용할 수 있습니다.

### 임포트

```
(import "파일경로" alias 별칭)
```

경로는 현재 실행 위치 기준 상대 경로 또는 절대 경로를 사용합니다.

### 임포트된 모듈 사용

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

## 13. 에러 메시지 읽기

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

## 빠른 참조

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
