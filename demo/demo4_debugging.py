"""디버그 모드(run_debug_mode) 데모: 브레이크포인트 / 스텝 / watch / inspect.

실행:
    python3 demo/demo4_debugging.py

디버깅 대상 소스는 demo4_debug_target.cf 이며, 아래 commands 리스트가
사람이 콘솔에 직접 입력하는 디버그 명령을 대신 재현한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from factory_shell import run_debug_mode  # noqa: E402

TARGET_PATH = Path(__file__).resolve().parent / "demo4_debug_target.cf"

COMMANDS = [
    "break 6",   # 두 번째 set! (total += step2) 실행 직후 멈추도록 브레이크포인트 설정
    "watch total",
    "continue",  # 브레이크포인트까지 실행 -> total = 30.0
    "step",      # (var step3 30) 실행
    "step",      # 세 번째 set! (total += step3) 실행 -> total = 60.0
    "inspect",   # 현재 스코프의 모든 변수 값 확인
    "continue",  # 나머지 출력문까지 실행하고 종료
]


def main() -> int:
    source = TARGET_PATH.read_text(encoding="utf-8")

    def write_output(line: str) -> None:
        print(f"[debug] {line}")

    print("--- 디버그 명령 시퀀스 ---")
    for command in COMMANDS:
        print(f"> {command}")
    print("--- 실행 로그 ---")

    return run_debug_mode(source, COMMANDS, write_output=write_output)


if __name__ == "__main__":
    raise SystemExit(main())
