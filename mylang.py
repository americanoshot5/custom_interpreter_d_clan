"""
mylang - S-expression 기반 미니 언어 인터프리터
지원 기능: 변수(define), 함수(lambda), 조건문(if), 반복문(for),
          재귀, 여러 문장 묶기(begin), 산술/비교 연산, 출력(print)
"""

import sys

# ---------------------------------------------------------------------------
# 1) 토큰화 (Tokenizer)
#    괄호를 공백으로 분리한 뒤 공백 기준으로 나눈다.
# ---------------------------------------------------------------------------
def tokenize(src):
    tokens = []
    i = 0
    while i < len(src):
        c = src[i]
        if c in "()":
            tokens.append(c)
            i += 1
        elif c == '"':
            # 따옴표로 감싼 문자열을 하나의 토큰으로 읽는다
            j = i + 1
            while j < len(src) and src[j] != '"':
                j += 1
            tokens.append(src[i:j + 1])  # 따옴표 포함
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < len(src) and not src[j].isspace() and src[j] not in '()"':
                j += 1
            tokens.append(src[i:j])
            i = j
    return tokens


# ---------------------------------------------------------------------------
# 2) 파싱 (Parser) : 토큰 -> 트리(AST)
#    '(' 를 만나면 리스트를 시작하고 ')' 를 만나면 닫는다. 재귀 한 번이면 끝.
# ---------------------------------------------------------------------------
def parse(tokens):
    if not tokens:
        raise SyntaxError("입력이 비었습니다")
    tok = tokens.pop(0)
    if tok == "(":
        node = []
        while tokens and tokens[0] != ")":
            node.append(parse(tokens))
        if not tokens:
            raise SyntaxError("괄호가 닫히지 않았습니다")
        tokens.pop(0)  # ')' 제거
        return node
    elif tok == ")":
        raise SyntaxError("예상치 못한 )")
    else:
        return atom(tok)


class Str(str):
    """문자열 리터럴 (심볼과 구분하기 위한 래퍼)"""
    pass


def atom(tok):
    """문자열/숫자/심볼 변환"""
    if tok.startswith('"') and tok.endswith('"'):
        return Str(tok[1:-1])  # 문자열 값 (심볼과 구분됨)
    try:
        return int(tok)
    except ValueError:
        try:
            return float(tok)
        except ValueError:
            return tok  # 심볼 (변수명, 연산자, 키워드)


def parse_program(src):
    """여러 최상위 식을 순서대로 파싱"""
    tokens = tokenize(src)
    exprs = []
    while tokens:
        exprs.append(parse(tokens))
    return exprs


# ---------------------------------------------------------------------------
# 3) 환경 (Environment) : 변수/함수 이름 -> 값
#    부모 환경을 가리켜서 함수 안의 지역 변수를 지원(스코프 체인).
# ---------------------------------------------------------------------------
class Env(dict):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

    def find(self, name):
        if name in self:
            return self
        if self.parent is not None:
            return self.parent.find(name)
        raise NameError(f"정의되지 않은 이름: {name}")


# 사용자 정의 함수 표현
class Function:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env  # 정의된 시점의 환경(클로저)

    def __call__(self, *args):
        local = Env(self.env)
        for p, a in zip(self.params, args):
            local[p] = a
        return eval_node(self.body, local)


# ---------------------------------------------------------------------------
# 4) 평가기 (Evaluator) : 트리를 재귀적으로 실행
# ---------------------------------------------------------------------------
def eval_node(node, env):
    # atom 처리
    if isinstance(node, (int, float)):
        return node
    if isinstance(node, Str):
        return node  # 문자열 리터럴은 그대로 반환
    if isinstance(node, str):
        return env.find(node)[node]  # 변수 조회

    if len(node) == 0:
        return None

    head = node[0]

    # ---- 특수형(special form): 인자를 미리 계산하지 않고 규칙대로 처리 ----
    if head == "define":
        # (define 이름 값)
        _, name, expr = node
        env[name] = eval_node(expr, env)
        return env[name]

    if head == "lambda":
        # (lambda (인자...) 몸통)
        _, params, body = node
        return Function(params, body, env)

    if head == "if":
        # (if 조건 참 거짓)
        _, cond, then_branch, else_branch = node
        if eval_node(cond, env):
            return eval_node(then_branch, env)
        else:
            return eval_node(else_branch, env)

    if head == "for":
        # (for 변수 시작 끝 몸통)  -- 끝값 포함
        _, var, start, end, body = node
        s = eval_node(start, env)
        e = eval_node(end, env)
        result = None
        for i in range(s, e + 1):
            env[var] = i
            result = eval_node(body, env)
        return result

    if head == "begin":
        # (begin 식1 식2 ...)  -- 순서대로 실행, 마지막 값 반환
        result = None
        for expr in node[1:]:
            result = eval_node(expr, env)
        return result

    # ---- 일반 함수 호출: 인자를 모두 계산한 뒤 호출 ----
    func = eval_node(head, env)
    args = [eval_node(arg, env) for arg in node[1:]]
    return func(*args)


# ---------------------------------------------------------------------------
# 5) 기본 내장 함수/연산자
# ---------------------------------------------------------------------------
def make_global_env():
    env = Env()
    import operator as op
    env.update({
        "+": lambda *a: sum(a),
        "-": lambda a, b=None: -a if b is None else a - b,
        "*": lambda *a: _product(a),
        "/": op.truediv,
        "%": op.mod,
        ">": op.gt, "<": op.lt,
        ">=": op.ge, "<=": op.le,
        "=": op.eq, "!=": op.ne,
        "and": lambda a, b: a and b,
        "or": lambda a, b: a or b,
        "not": lambda a: not a,
        "print": _print,
        "true": True,
        "false": False,
    })
    return env


def _product(nums):
    result = 1
    for n in nums:
        result *= n
    return result


def _print(*args):
    print(*args)
    return args[-1] if args else None


# ---------------------------------------------------------------------------
# 6) 실행기
# ---------------------------------------------------------------------------
def run(src):
    env = make_global_env()
    result = None
    for expr in parse_program(src):
        result = eval_node(expr, env)
    return result


# ---------------------------------------------------------------------------
# 데모
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    program = """
    (define x 10)
    (print "x =" x)

    (define square (lambda (n) (* n n)))
    (print "square(5) =" (square 5))

    (print "if test:" (if (> x 5) 100 200))

    (print "for loop:")
    (for i 1 5 (print "  i =" i))

    (define fact
      (lambda (n)
        (if (<= n 1)
            1
            (* n (fact (- n 1))))))
    (print "fact(5) =" (fact 5))

    (define sum-to
      (lambda (n)
        (begin
          (define total 0)
          (for i 1 n (define total (+ total i)))
          total)))
    (print "sum 1..10 =" (sum-to 10))
    """
    run(program)
