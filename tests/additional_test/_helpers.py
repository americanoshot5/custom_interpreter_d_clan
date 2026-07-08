"""
3일차 기능 추가 미션을 S-expression 문법으로 옮긴 통합 테스트에서 공용으로 쓰는 헬퍼.

PDF의 C-style 예시는 이 프로젝트의 기존 문법에 맞춰 다음 원칙으로 번역한다.
- 함수 선언: (func name (params...) body)
- 함수 호출: (name args...)
- 클래스 선언: (class Name { ... })
- 필드 접근: dotted name 또는 helper form (get-field/set-field!)
- 정적 배열: (Array size), (index array i), (set-index! array i value)
- import: (import "path" alias name), imported call as (alias.member args...)

이 폴더의 파일명은 의도적으로 pytest 기본 수집 패턴(test_*.py / *_test.py)을
피해서 짓는다 — 아직 구현되지 않은 기능(function/class/array/optimizer/import)
테스트라서, CI에서 자동 실행되어 실패하지 않도록 하기 위함이다.
"""

from __future__ import annotations

from Assembler import assemble
from Checker import check
from Executor import execute
from Tokenizer import tokenize


def run(source):
    tokens = tokenize(source)
    program = assemble(tokens)
    check(program)
    return execute(program)
