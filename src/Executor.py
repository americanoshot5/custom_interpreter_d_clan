from __future__ import annotations

import operator as _op
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from common import *
from interfaces import *
from Tokenizer import tokenize
from Assembler import assemble
from Checker import check

# ── 연산자 테이블 ─────────────────────────────────────────────────────────────
#
# 새로운 연산자 추가 시: _UNARY 또는 _BINARY에 한 줄만 추가하면 됩니다.
# Checker의 BUILTIN_OPS(common.py)도 함께 업데이트하는 것을 잊지 마세요.

_UNARY: dict[str, Callable[[RuntimeValue], RuntimeValue]] = {
    "+":   lambda a: a,
    "-":   _op.neg,
    "not": _op.not_,
    "!":   _op.not_,
}

_BINARY: dict[str, Callable[[RuntimeValue, RuntimeValue], RuntimeValue]] = {
    "+":   _op.add,
    "-":   _op.sub,
    "*":   _op.mul,
    "/":   _op.truediv,  # ZeroDivisionError 는 자연스럽게 전파됩니다
    "<":   _op.lt,
    ">":   _op.gt,
    "=":   _op.eq,
    "and": lambda a, b: a and b,
    "or":  lambda a, b: a or b,
}

_ARRAY_OPS: frozenset[str] = frozenset({"Array", "index", "set-index!"})
_ALL_OPS: frozenset[str] = frozenset(_UNARY) | frozenset(_BINARY) | _ARRAY_OPS | {"instanceof"}

# ── 함수 런타임 값 / 반환 시그널 ──────────────────────────────────────────────

@dataclass
class Function:
    params: tuple[str, ...]
    body: "Stmt"
    closure: "Environment"


class _ReturnSignal(Exception):
    def __init__(self, value: "RuntimeValue") -> None:
        self.value = value


@dataclass
class Module:
    name: str
    environment: "Environment"
# ── 런타임 객체 ───────────────────────────────────────────────────────────────

@dataclass
class ClassDef:
    """실행 시간에 클래스를 나타내는 객체."""
    name: str
    parent: ClassDef | None
    field_names: tuple[str, ...]
    methods: dict[str, MethodDef]

    def get_all_field_names(self) -> list[str]:
        """상속 계층을 포함한 모든 필드 이름 (부모 → 자식 순서)."""
        parent_fields = self.parent.get_all_field_names() if self.parent else []
        own = [f for f in self.field_names if f not in parent_fields]
        return parent_fields + own

    def lookup_method(self, name: str) -> tuple[MethodDef, ClassDef] | None:
        """메서드 이름으로 (메서드 정의, 정의된 클래스) 를 반환한다. 없으면 None."""
        if name in self.methods:
            return self.methods[name], self
        if self.parent is not None:
            return self.parent.lookup_method(name)
        return None


@dataclass
class ClassInstance:
    """클래스의 인스턴스."""
    class_def: ClassDef
    fields: dict[str, RuntimeValue] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<{self.class_def.name} instance>"

# ── 환경(스코프) ──────────────────────────────────────────────────────────────

@dataclass
class Environment:
    parent: Environment | None = None

    def __post_init__(self):
        self._values: dict[str, RuntimeValue] = {}

    def define(self, name: str, value: RuntimeValue) -> None:
        self._values[name] = value

    def lookup(self, name: str) -> RuntimeValue:
        if name in self._values:
            return self._values[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise ExecuteError(f"Undefined variable '{name}'")

    def assign(self, name: str, value: RuntimeValue) -> None:
        if name in self._values:
            self._values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise ExecuteError(f"Undefined variable '{name}'")

    def snapshot(self) -> dict[str, RuntimeValue]:
        """현재(가장 안쪽) 스코프 변수만 복사해 반환한다."""
        return dict(self._values)


# ── 실행기 ────────────────────────────────────────────────────────────────────

class SExpressionExecutor(Executor):

    # 새로운 Stmt 종류 추가 시: 이 테이블에 한 줄 + 실행 메서드 하나만 추가하면 됩니다.
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

    def __init__(self):
        self._environment = Environment()

    def execute(self, program: Program) -> RuntimeValue:
        result = None
        for stmt in program.statements:
            result = self._execute_stmt(stmt)
        return result

    # ── 디버거 공개 API ───────────────────────────────────────────────────────

    def lookup_variable(self, name: str) -> RuntimeValue:
        """현재 스코프 체인에서 변수를 조회한다. 없으면 ExecuteError."""
        return self._environment.lookup(name)

    def current_scope_snapshot(self) -> dict[str, RuntimeValue]:
        """현재(가장 안쪽) 스코프의 변수 이름→값 사전을 복사해 반환한다."""
        return self._environment.snapshot()

    # ── 문(Stmt) 실행 ─────────────────────────────────────────────────────────

    def _execute_stmt(self, stmt: Stmt) -> RuntimeValue:
        method_name = self._STMT_DISPATCH.get(type(stmt))
        if method_name is None:
            raise ExecuteError(f"Unsupported statement: {type(stmt).__name__}")
        return getattr(self, method_name)(stmt)

    def _execute_exprstmt(self, stmt: ExpressionStmt) -> RuntimeValue:
        return self._execute_expr(stmt.expression)

    def _execute_printstmt(self, stmt: PrintStmt) -> RuntimeValue:
        print(self._execute_expr(stmt.expression))
        return None

    def _execute_varstmt(self, stmt: VarStmt) -> Any | None:
        value = self._execute_expr(stmt.initializer) if stmt.initializer is not None else None
        self._environment.define(stmt.name, value)
        return None

    def _execute_setstmt(self, stmt: SetStmt) -> RuntimeValue:
        value = self._execute_expr(stmt.value)
        self._environment.assign(stmt.target, value)
        return value

    def _execute_ifstmt(self, stmt: IfStmt) -> RuntimeValue:
        if self._execute_expr(stmt.condition):
            return self._execute_stmt(stmt.then_branch)
        if stmt.else_branch is not None:
            return self._execute_stmt(stmt.else_branch)
        return None

    def _execute_forstmt(self, stmt: ForStmt) -> RuntimeValue:
        start = int(self._execute_expr(stmt.start))
        end   = int(self._execute_expr(stmt.end))
        previous = self._environment
        self._environment = Environment(parent=previous)
        try:
            result = None
            for i in range(start, end):
                self._environment.define(stmt.iterator, i)
                result = self._execute_stmt(stmt.body)
            return result
        finally:
            self._environment = previous

    def _execute_blockstmt(self, block: BlockStmt) -> RuntimeValue:
        previous = self._environment
        self._environment = Environment(parent=previous)
        try:
            result = None
            for stmt in block.statements:
                result = self._execute_stmt(stmt)
            return result
        finally:
            self._environment = previous

    def _execute_funcdefstmt(self, stmt: FuncDefStmt) -> RuntimeValue:
        func = Function(params=stmt.params, body=stmt.body, closure=self._environment)
        self._environment.define(stmt.name, func)
        return None

    def _execute_returnstmt(self, stmt: ReturnStmt) -> RuntimeValue:
        value = self._execute_expr(stmt.value) if stmt.value is not None else None
        raise _ReturnSignal(value)

    def _call_function(self, func: Function, args: list) -> RuntimeValue:
        if len(args) != len(func.params):
            raise ExecuteError(
                f"Function expects {len(func.params)} argument(s) but got {len(args)}"
            )
        call_env = Environment(parent=func.closure)
        for param, arg in zip(func.params, args):
            call_env.define(param, arg)
        previous = self._environment
        self._environment = call_env
        try:
            self._execute_stmt(func.body)
            return None
        except _ReturnSignal as sig:
            return sig.value
        finally:
            self._environment = previous

    def _execute_classstmt(self, stmt: ClassStmt) -> RuntimeValue:
        parent_def: ClassDef | None = None
        if stmt.parent is not None:
            parent_val = self._environment.lookup(stmt.parent)
            if not isinstance(parent_val, ClassDef):
                raise ExecuteError(f"'{stmt.parent}' is not a class")
            parent_def = parent_val

        class_def = ClassDef(
            name=stmt.name,
            parent=parent_def,
            field_names=stmt.fields,
            methods={m.name: m for m in stmt.methods},
        )
        self._environment.define(stmt.name, class_def)
        return None

    def _execute_importstmt(self, stmt: ImportStmt) -> RuntimeValue:
        path = stmt.path.value  # Checker 가 이미 문자열 리터럴임을 검증했다
        source = Path(path).read_text(encoding="utf-8-sig")
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

    # ── 식(Expr) 평가 ─────────────────────────────────────────────────────────

    def _execute_expr(self, expr: Expr) -> RuntimeValue:
        if isinstance(expr, LiteralExpr):
            return expr.value
        if isinstance(expr, IdentifierExpr):
            return expr.name if expr.name in _ALL_OPS else self._environment.lookup(expr.name)
        if isinstance(expr, ListExpr):
            return self._execute_list_expr(expr)
        if isinstance(expr, ArrayExpr):
            return self._execute_array_expr(expr)
        if isinstance(expr, ArrayIndexExpr):
            return self._execute_array_index_expr(expr)
        if isinstance(expr, NewExpr):
            return self._execute_new_expr(expr)
        if isinstance(expr, DotExpr):
            return self._execute_dot_expr(expr)
        if isinstance(expr, SuperExpr):
            return self._execute_super_expr(expr)
        raise ExecuteError(f"Unsupported expression: {type(expr).__name__}")

    def _execute_array_expr(self, expr: ArrayExpr) -> RuntimeValue:
        size = self._execute_expr(expr.size)
        if isinstance(size, bool) or not isinstance(size, (int, float)):
            raise ExecuteError(f"Array size must be a number, got {type(size).__name__}")
        size_int = int(size)
        if size_int < 0:
            raise ExecuteError(f"Array size must be non-negative, got {size_int}")
        return [None] * size_int

    def _execute_array_index_expr(self, expr: ArrayIndexExpr) -> RuntimeValue:
        array = self._execute_expr(expr.array)
        if not isinstance(array, list):
            raise ExecuteError(f"Cannot index non-array value")
        index = self._execute_expr(expr.index)
        if isinstance(index, bool) or not isinstance(index, (int, float)):
            raise ExecuteError(f"Array index must be a number, got {type(index).__name__}")
        idx = int(index)
        if idx < 0 or idx >= len(array):
            raise ExecuteError(f"Array index {idx} out of bounds for array of size {len(array)}")
        return array[idx]

    def _execute_list_expr(self, expr: ListExpr) -> RuntimeValue:
        if not expr.elements:
            raise ExecuteError("Empty s-expression")

        op = self._execute_expr(expr.elements[0])

        if isinstance(op, Function):
            args = [self._execute_expr(arg) for arg in expr.elements[1:]]
            return self._call_function(op, args)

        # 클래스명을 생성자로 직접 호출: (ClassName args...)
        if isinstance(op, ClassDef):
            args = [self._execute_expr(a) for a in expr.elements[1:]]
            return self._create_instance(op, args)

        if not isinstance(op, str):
            raise ExecuteError(f"'{op}' is not callable")

        # instanceof 특수 처리
        if op == "instanceof":
            if len(expr.elements) != 3:
                raise ExecuteError("'instanceof' requires exactly 2 arguments")
            obj_val = self._execute_expr(expr.elements[1])
            class_val = self._execute_expr(expr.elements[2])
            return self._do_instanceof(obj_val, class_val)

        if op not in _ALL_OPS:
            raise ExecuteError(f"'{op}' is not a callable operator")

        if op in _ARRAY_OPS:
            return self._execute_array_op(op, expr)

        args = [self._execute_expr(arg) for arg in expr.elements[1:]]
        n = len(args)

        try:
            if n == 1 and op in _UNARY:
                return _UNARY[op](args[0])
            if n == 2 and op in _BINARY:
                return _BINARY[op](args[0], args[1])
            raise ExecuteError(f"Operator '{op}' does not support {n} argument(s)")
        except ExecuteError:
            raise
        except TypeError as e:
            raise ExecuteError(str(e)) from e

    @staticmethod
    def _as_array_size(value: RuntimeValue) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ExecuteError(f"Array size must be a number, got {type(value).__name__}")
        size = int(value)
        if size < 0:
            raise ExecuteError(f"Array size must be non-negative, got {size}")
        return size

    @staticmethod
    def _as_array_index(array: list, value: RuntimeValue) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ExecuteError(f"Array index must be a number, got {type(value).__name__}")
        idx = int(value)
        if idx < 0 or idx >= len(array):
            raise ExecuteError(f"Array index {idx} out of bounds for array of size {len(array)}")
        return idx

    def _eval_array_arg(self, expr: ListExpr) -> list:
        array = self._execute_expr(expr.elements[1])
        if not isinstance(array, list):
            raise ExecuteError("Cannot index non-array value")
        return array

    def _execute_array_op(self, op: str, expr: ListExpr) -> RuntimeValue:
        if op == "Array":
            if len(expr.elements) != 2:
                raise ExecuteError("Array takes exactly 1 argument (size)")
            size = self._as_array_size(self._execute_expr(expr.elements[1]))
            return [None] * size

        if op == "index":
            if len(expr.elements) != 3:
                raise ExecuteError("index takes exactly 2 arguments (array, index)")
            array = self._eval_array_arg(expr)
            idx = self._as_array_index(array, self._execute_expr(expr.elements[2]))
            return array[idx]

        # op == "set-index!"
        if len(expr.elements) != 4:
            raise ExecuteError("set-index! takes exactly 3 arguments (array, index, value)")
        array = self._eval_array_arg(expr)
        idx = self._as_array_index(array, self._execute_expr(expr.elements[2]))
        value = self._execute_expr(expr.elements[3])
        array[idx] = value
        return value

    def _create_instance(self, class_def: ClassDef, args: list[RuntimeValue]) -> ClassInstance:
        instance = ClassInstance(
            class_def=class_def,
            fields={name: None for name in class_def.get_all_field_names()},
        )
        init_result = class_def.lookup_method("init")
        if init_result is not None:
            init_def, defining_class = init_result
            self._call_method(instance, init_def, defining_class, args)
        elif args:
            raise ExecuteError(
                f"Class '{class_def.name}' has no 'init' method "
                f"but {len(args)} argument(s) were provided"
            )
        return instance

    def _do_instanceof(self, obj: RuntimeValue, cls: RuntimeValue) -> bool:
        if not isinstance(cls, ClassDef):
            raise ExecuteError("'instanceof' second argument must be a class")
        if not isinstance(obj, ClassInstance):
            return False
        current = obj.class_def
        while current is not None:
            if current is cls or current.name == cls.name:
                return True
            current = current.parent
        return False

    # ── OOP 실행 ─────────────────────────────────────────────────────────────

    def _execute_new_expr(self, expr: NewExpr) -> RuntimeValue:
        class_val = self._environment.lookup(expr.class_name)
        if not isinstance(class_val, ClassDef):
            raise ExecuteError(f"'{expr.class_name}' is not a class")
        args = [self._execute_expr(a) for a in expr.args]
        return self._create_instance(class_val, args)

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

    def _execute_super_expr(self, expr: SuperExpr) -> RuntimeValue:
        # self 와 __class__ 는 메서드 실행 환경에 정의되어 있다
        try:
            instance = self._environment.lookup("self")
            current_class = self._environment.lookup("__class__")
        except ExecuteError:
            raise ExecuteError("'super' used outside of a method")

        if not isinstance(instance, ClassInstance):
            raise ExecuteError("'super' used outside of a method")

        parent = current_class.parent
        if parent is None:
            raise ExecuteError(f"Class '{current_class.name}' has no parent class")

        method_result = parent.lookup_method(expr.method)
        if method_result is None:
            raise ExecuteError(
                f"Method '{expr.method}' not found in parent class '{parent.name}'"
            )

        method_def, defining_class = method_result
        args = [self._execute_expr(a) for a in expr.args]
        return self._call_method(instance, method_def, defining_class, args)

    def _call_method(
        self,
        instance: ClassInstance,
        method_def: MethodDef,
        defining_class: ClassDef,
        args: list[RuntimeValue],
    ) -> RuntimeValue:
        if len(args) != len(method_def.params):
            raise ExecuteError(
                f"Method '{method_def.name}' expects {len(method_def.params)} "
                f"argument(s), got {len(args)}"
            )

        previous = self._environment
        self._environment = Environment(parent=previous)
        # self, __class__ (super 탐색용), 파라미터를 바인딩
        self._environment.define("self", instance)
        self._environment.define("This", instance)   # 새 문법 alias
        self._environment.define("__class__", defining_class)
        for param, val in zip(method_def.params, args):
            self._environment.define(param, val)

        try:
            result: RuntimeValue = None
            for stmt in method_def.body:
                result = self._execute_stmt(stmt)
            return result
        except _ReturnSignal as sig:
            return sig.value
        finally:
            self._environment = previous


DefaultExecutor = SExpressionExecutor


def execute(program: Program) -> RuntimeValue:
    return SExpressionExecutor().execute(program)


__all__ = ["DefaultExecutor", "SExpressionExecutor", "execute"]
