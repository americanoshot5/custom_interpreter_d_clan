from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from common import (
    ArrayExpr,
    ArrayIndexExpr,
    AssembleError,
    BlockStmt,
    ClassStmt,
    DotExpr,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDefStmt,
    IdentifierExpr,
    IfStmt,
    ListExpr,
    LiteralExpr,
    MethodDef,
    NewExpr,
    PrintStmt,
    Program,
    ReturnStmt,
    SetStmt,
    SourceLocation,
    Stmt,
    SuperExpr,
    Token,
    TokenType,
    VarStmt,
)
from interfaces import Assembler


class SExpressionAssembler(Assembler):

    # 새로운 special form(문) 추가 시: 이 테이블에 한 줄 + 파서 메서드 하나만 추가하면 됩니다.
    _SPECIAL_FORMS: ClassVar[dict[TokenType, str]] = {
        TokenType.VAR:    "_parse_var_stmt",
        TokenType.SET:    "_parse_set_stmt",
        TokenType.PRINT:  "_parse_print_stmt",
        TokenType.IF:     "_parse_if_stmt",
        TokenType.FOR:    "_parse_for_stmt",
        TokenType.FUNC:   "_parse_func_stmt",
        TokenType.RETURN: "_parse_return_stmt",
        TokenType.CLASS: "_parse_class_stmt",
    }

    # 새로운 expression special form 추가 시: 이 테이블에 한 줄 + 파서 메서드 하나만 추가하면 됩니다.
    _EXPR_FORMS: ClassVar[dict[TokenType, str]] = {
        TokenType.NEW:           "_parse_new_expr",
        TokenType.DOT:           "_parse_dot_expr",
        TokenType.SUPER:         "_parse_super_expr",
        TokenType.DOTIDENTIFIER: "_parse_dotidentifier_expr",
    }

    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = list(tokens)
        self._current = 0

    def assemble(self) -> Program:
        statements: list[Stmt] = []
        while not self._is_at_end():
            statements.append(self._statement())
        return Program(tuple(statements))

    # ── Statement parsers ────────────────────────────────────────────────────

    def _statement(self) -> Stmt:
        if self._check(TokenType.LEFT_BRACE):
            return self._parse_block()
        if self._check(TokenType.LEFT_PAREN):
            return self._parse_list_stmt()
        expr = self._expression()
        self._assert_expr(expr)
        return ExpressionStmt(expr)

    def _parse_block(self) -> BlockStmt:
        open_brace = self._advance()  # consume '{'
        stmts: list[Stmt] = []
        while not self._check(TokenType.RIGHT_BRACE):
            if self._is_at_end():
                raise AssembleError(
                    f"Missing '}}' for block opened at "
                    f"{open_brace.location.line}:{open_brace.location.column}"
                )
            stmts.append(self._statement())
        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after block")
        return BlockStmt(tuple(stmts), location=open_brace.location)

    def _parse_list_stmt(self) -> Stmt:
        open_paren = self._advance()  # consume '('
        stmt_method = self._SPECIAL_FORMS.get(self._peek().type)
        if stmt_method:
            return getattr(self, stmt_method)(open_paren)
        # 나머지는 표현식으로 파싱 (_EXPR_FORMS 포함)
        expr = self._parse_list(open_paren)
        return ExpressionStmt(expr)

    def _parse_set_stmt(self, open_paren: Token) -> SetStmt:
        self._advance()  # consume 'set!'
        target_token = self._peek()
        if target_token.type is not TokenType.IDENTIFIER:
            raise AssembleError(
                f"Invalid assignment target at "
                f"{target_token.location.line}:{target_token.location.column}: "
                f"assignment target must be a variable name"
            )
        self._advance()
        value = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close set! statement")
        return SetStmt(target=target_token.lexeme, value=value, location=open_paren.location)

    def _parse_var_stmt(self, open_paren: Token) -> VarStmt:
        self._advance()  # consume 'var'
        name_token = self._consume(TokenType.IDENTIFIER, "Expected variable name after 'var'")
        initializer = None
        if not self._check(TokenType.RIGHT_PAREN):
            initializer = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close var statement")
        return VarStmt(name=name_token.lexeme, initializer=initializer, location=open_paren.location)

    def _parse_print_stmt(self, open_paren: Token) -> PrintStmt:
        self._advance()  # consume 'print'
        expr = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close print statement")
        return PrintStmt(expression=expr, location=open_paren.location)

    def _parse_if_stmt(self, open_paren: Token) -> IfStmt:
        self._advance()  # consume 'if'
        condition = self._expression()
        then_branch = self._statement()
        else_branch = None
        if not self._check(TokenType.RIGHT_PAREN):
            else_branch = self._statement()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close if statement")
        return IfStmt(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            location=open_paren.location,
        )

    def _parse_for_stmt(self, open_paren: Token) -> ForStmt:
        self._advance()  # consume 'for'
        iter_token = self._consume(TokenType.IDENTIFIER, "Expected iterator name after 'for'")
        start = self._expression()
        end = self._expression()
        body = self._statement()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close for statement")
        return ForStmt(
            iterator=iter_token.lexeme,
            start=start,
            end=end,
            body=body,
            location=open_paren.location,
        )

    def _parse_func_stmt(self, open_paren: Token) -> FuncDefStmt:
        self._advance()  # consume 'func'
        name_token = self._consume(TokenType.IDENTIFIER, "Expected function name after 'func'")
        self._consume(TokenType.LEFT_PAREN, "Expected '(' for parameter list in func")
        params: list[str] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError("Unclosed parameter list in func declaration")
            param_token = self._consume(TokenType.IDENTIFIER, "Expected parameter name in func")
            params.append(param_token.lexeme)
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close parameter list in func")
        body = self._statement()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close func declaration")
        return FuncDefStmt(
            name=name_token.lexeme,
            params=tuple(params),
            body=body,
            location=open_paren.location,
        )

    def _parse_return_stmt(self, open_paren: Token) -> ReturnStmt:
        self._advance()  # consume 'return'
        if self._check(TokenType.RIGHT_PAREN):
            self._advance()  # consume ')'
            return ReturnStmt(value=None, location=open_paren.location)
        value = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close return statement")
        return ReturnStmt(value=value, location=open_paren.location)

    def _parse_class_stmt(self, open_paren: Token) -> ClassStmt:
        self._advance()  # consume 'class'
        name_token = self._advance()
        if name_token.type is TokenType.RIGHT_PAREN or name_token.type is TokenType.EOF:
            raise AssembleError(
                f"Expected class name at {name_token.location.line}:{name_token.location.column}"
            )
        class_name = name_token.lexeme

        # 새 문법 감지: '{' 또는 ':' 가 뒤따르면 새 문법 (braces + colon 상속)
        if (self._peek().type is TokenType.LEFT_BRACE or
                self._peek().lexeme == ":"):
            return self._parse_new_class_body(open_paren, class_name)

        # ── 구 문법 ──────────────────────────────────────────────────────────
        # 선택적 부모 클래스: 다음 토큰이 IDENTIFIER 이면 부모 이름
        parent_name: str | None = None
        if self._peek().type is TokenType.IDENTIFIER:
            parent_name = self._advance().lexeme

        fields: list[str] = []
        methods: list[MethodDef] = []

        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError(
                    f"Missing ')' for class '{class_name}' opened at "
                    f"{open_paren.location.line}:{open_paren.location.column}"
                )
            if not self._check(TokenType.LEFT_PAREN):
                tok = self._peek()
                raise AssembleError(
                    f"Expected '(' in class body at {tok.location.line}:{tok.location.column}"
                )
            self._advance()  # consume '('

            member_type = self._peek().type
            if member_type is TokenType.FIELD:
                self._advance()  # consume 'field'
                fname = self._advance()
                fields.append(fname.lexeme)
                self._consume(TokenType.RIGHT_PAREN, "Expected ')' after field name")
            elif member_type is TokenType.METHOD:
                methods.append(self._parse_method_def())
            else:
                tok = self._peek()
                raise AssembleError(
                    f"Expected 'field' or 'method' in class body at "
                    f"{tok.location.line}:{tok.location.column}"
                )

        self._consume(TokenType.RIGHT_PAREN, f"Expected ')' to close class '{class_name}'")
        return ClassStmt(
            name=class_name,
            parent=parent_name,
            fields=tuple(fields),
            methods=tuple(methods),
            location=open_paren.location,
        )

    def _parse_new_class_body(self, open_paren: Token, class_name: str) -> ClassStmt:
        """새 문법 클래스 본문: (class Name { ... }) 또는 (class Name : Parent { ... })"""
        parent_name: str | None = None
        if self._peek().lexeme == ":":
            self._advance()  # consume ':'
            parent_tok = self._advance()
            parent_name = parent_tok.lexeme

        self._consume(TokenType.LEFT_BRACE, f"Expected '{{' for class '{class_name}' body")

        methods: list[MethodDef] = []
        while not self._check(TokenType.RIGHT_BRACE):
            if self._is_at_end():
                raise AssembleError(f"Missing '}}' for class '{class_name}'")
            self._consume(TokenType.LEFT_PAREN, "Expected '(' for method definition")
            if self._peek().type is not TokenType.METHOD:
                tok = self._peek()
                raise AssembleError(
                    f"Expected 'method' at {tok.location.line}:{tok.location.column}"
                )
            methods.append(self._parse_new_method_def())

        self._consume(TokenType.RIGHT_BRACE, f"Expected '}}' to close class '{class_name}'")
        self._consume(TokenType.RIGHT_PAREN, f"Expected ')' to close class '{class_name}'")
        return ClassStmt(
            name=class_name,
            parent=parent_name,
            fields=(),
            methods=tuple(methods),
            location=open_paren.location,
        )

    def _parse_new_method_def(self) -> MethodDef:
        """새 문법 메서드: (method name (params...) { body... })"""
        method_kw = self._advance()  # consume 'method'
        loc = method_kw.location
        name_tok = self._advance()
        method_name = name_tok.lexeme

        self._consume(TokenType.LEFT_PAREN, "Expected '(' for method parameters")
        params: list[str] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError(f"Missing ')' in method '{method_name}' parameters")
            params.append(self._advance().lexeme)
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close method parameters")

        self._consume(TokenType.LEFT_BRACE, f"Expected '{{' for method '{method_name}' body")
        body: list[Stmt] = []
        while not self._check(TokenType.RIGHT_BRACE):
            if self._is_at_end():
                raise AssembleError(f"Missing '}}' for method '{method_name}'")
            body.append(self._statement())
        self._consume(TokenType.RIGHT_BRACE, f"Expected '}}' to close method '{method_name}'")

        self._consume(TokenType.RIGHT_PAREN, f"Expected ')' to close method '{method_name}'")
        return MethodDef(
            name=method_name,
            params=tuple(params),
            body=tuple(body),
            location=loc,
        )

    def _parse_get_field_expr(self, open_paren: Token) -> DotExpr:
        """(get-field obj fieldName) → DotExpr(obj, fieldName, ())"""
        self._advance()  # consume 'get-field'
        obj = self._expression()
        field_tok = self._advance()  # field name treated as literal symbol
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close get-field")
        return DotExpr(obj=obj, slot=field_tok.lexeme, args=(), location=open_paren.location)

    def _parse_set_field_expr(self, open_paren: Token) -> DotExpr:
        """(set-field! obj fieldName value) → DotExpr(obj, fieldName, (value,))"""
        self._advance()  # consume 'set-field!'
        obj = self._expression()
        field_tok = self._advance()  # field name treated as literal symbol
        value = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close set-field!")
        return DotExpr(obj=obj, slot=field_tok.lexeme, args=(value,), location=open_paren.location)

    def _parse_dotidentifier_expr(self, open_paren: Token) -> Expr:
        """(obj.method args...) or (Super.method args...) from DOTIDENTIFIER token"""
        tok = self._advance()  # consume DOTIDENTIFIER
        lexeme = tok.lexeme
        obj_name, method_name = self._split_dot_identifier(lexeme)

        args: list[Expr] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError(f"Missing ')' in '{lexeme}' call")
            args.append(self._expression())
        self._consume(TokenType.RIGHT_PAREN, f"Expected ')' to close '{lexeme}' call")

        if obj_name == "Super":
            return SuperExpr(method=method_name, args=tuple(args), location=open_paren.location)
        return DotExpr(
            obj=IdentifierExpr(obj_name, location=tok.location),
            slot=method_name,
            args=tuple(args),
            location=open_paren.location,
        )

    def _parse_method_def(self) -> MethodDef:
        method_kw = self._advance()  # consume 'method'
        loc = method_kw.location

        # 메서드 시그니처: (methodName param1 param2 ...)
        self._consume(TokenType.LEFT_PAREN, "Expected '(' for method signature")
        name_tok = self._advance()
        method_name = name_tok.lexeme

        params: list[str] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError("Missing ')' in method signature")
            params.append(self._advance().lexeme)
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close method signature")

        # 메서드 본문: 문(Stmt) 목록
        body: list[Stmt] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError(f"Missing ')' to close method '{method_name}'")
            body.append(self._statement())
        self._consume(TokenType.RIGHT_PAREN, f"Expected ')' to close method '{method_name}'")

        return MethodDef(
            name=method_name,
            params=tuple(params),
            body=tuple(body),
            location=loc,
        )

    # ── Expression parsers ───────────────────────────────────────────────────

    def _expression(self) -> Expr:
        token = self._advance()
        if token.type is TokenType.LEFT_PAREN:
            expr = self._parse_list(token)
        elif token.type is TokenType.LEFT_BRACKET:
            expr = self._parse_array(token)
        else:
            expr = self._parse_atom(token)

        while self._check(TokenType.LEFT_BRACKET):
            bracket = self._advance()
            index = self._expression()
            self._consume(TokenType.RIGHT_BRACKET, "Expected ']' to close array index")
            expr = ArrayIndexExpr(array=expr, index=index, location=bracket.location)

        return expr

    def _parse_array(self, open_bracket: Token) -> ArrayExpr:
        size = self._expression()
        self._consume(TokenType.RIGHT_BRACKET, "Expected ']' to close array literal")
        return ArrayExpr(size=size, location=open_bracket.location)

    def _parse_list(self, open_paren: Token) -> Expr:
        # expression-level special forms (new / . / super / dotidentifier)
        expr_method = self._EXPR_FORMS.get(self._peek().type)
        if expr_method:
            return getattr(self, expr_method)(open_paren)

        # lexeme 기반 special form: get-field / set-field!
        if self._peek().type is TokenType.IDENTIFIER:
            lex = self._peek().lexeme
            if lex == "get-field":
                return self._parse_get_field_expr(open_paren)
            if lex == "set-field!":
                return self._parse_set_field_expr(open_paren)

        # 일반 ListExpr
        elements: list[Expr] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError(
                    f"Missing ')' for list opened at "
                    f"{open_paren.location.line}:{open_paren.location.column}"
                )
            child = self._expression()
            self._assert_expr(child)
            elements.append(child)
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after S-expression")
        return ListExpr(tuple(elements), location=open_paren.location)

    def _parse_new_expr(self, open_paren: Token) -> NewExpr:
        self._advance()  # consume 'new'
        name_tok = self._advance()
        class_name = name_tok.lexeme
        args: list[Expr] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError("Missing ')' in new expression")
            args.append(self._expression())
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close new expression")
        return NewExpr(class_name=class_name, args=tuple(args), location=open_paren.location)

    def _parse_dot_expr(self, open_paren: Token) -> DotExpr:
        self._advance()  # consume '.'
        obj = self._expression()
        # 슬롯 이름: 키워드도 허용 (예: method named 'init')
        slot_tok = self._advance()
        if slot_tok.type in {TokenType.RIGHT_PAREN, TokenType.EOF}:
            raise AssembleError(
                f"Expected slot name in dot expression at "
                f"{slot_tok.location.line}:{slot_tok.location.column}"
            )
        slot = slot_tok.lexeme
        args: list[Expr] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError("Missing ')' in dot expression")
            args.append(self._expression())
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close dot expression")
        return DotExpr(obj=obj, slot=slot, args=tuple(args), location=open_paren.location)

    def _parse_super_expr(self, open_paren: Token) -> SuperExpr:
        self._advance()  # consume 'super'
        method_tok = self._advance()
        method_name = method_tok.lexeme
        args: list[Expr] = []
        while not self._check(TokenType.RIGHT_PAREN):
            if self._is_at_end():
                raise AssembleError("Missing ')' in super expression")
            args.append(self._expression())
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' to close super expression")
        return SuperExpr(method=method_name, args=tuple(args), location=open_paren.location)

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

    def _assert_expr(self, node: Expr) -> None:
        if isinstance(node, Stmt):
            loc = node.location
            loc_str = f"{loc.line}:{loc.column}" if loc is not None else "unknown"
            raise AssembleError(f"Statement cannot be used as expression at {loc_str}")

    # ── Token navigation ─────────────────────────────────────────────────────

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        raise AssembleError(f"{message} at {token.location.line}:{token.location.column}")

    def _check(self, token_type: TokenType) -> bool:
        return not self._is_at_end() and self._peek().type is token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self._current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type is TokenType.EOF

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]


DefaultAssembler = SExpressionAssembler


def assemble(tokens: Sequence[Token]) -> Program:
    return SExpressionAssembler(tokens).assemble()


__all__ = ["DefaultAssembler", "SExpressionAssembler", "assemble"]
