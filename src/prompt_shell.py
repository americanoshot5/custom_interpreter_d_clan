from __future__ import annotations


def is_balanced(text: str) -> bool:
    depth = 0
    in_string = False
    for char in text:
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
    return depth <= 0
