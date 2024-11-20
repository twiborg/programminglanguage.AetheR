from dataclasses import dataclass
from typing import List, Any
from lexer import Token, TokenType

class ParseError(Exception):
    def __init__(self, line, where, message):
        self.line = line
        self.where = where
        self.message = message
        super().__init__(f"[line {line}] Error at '{where}': {message}")

@dataclass
class Expression:
    pass

@dataclass
class Binary(Expression):
    left: Expression
    operator: Token
    right: Expression

@dataclass
class Grouping(Expression):
    expression: Expression

@dataclass
class Literal(Expression):
    value: Any

@dataclass
class Unary(Expression):
    operator: Token
    right: Expression

@dataclass
class Variable(Expression):
    name: Token

@dataclass
class VarDeclaration(Expression):
    name: Token
    initializer: Expression

@dataclass
class Assignment(Expression):
    name: Token
    value: Expression

@dataclass
class Print(Expression):
    expression: Expression

@dataclass
class If(Expression):
    condition: Expression
    then_branch: Expression
    else_branch: Expression = None

@dataclass
class While(Expression):
    condition: Expression
    body: Expression

@dataclass
class For(Expression):
    initializer: Expression
    condition: Expression
    increment: Expression
    body: Expression

@dataclass
class Block(Expression):
    statements: List[Expression]

@dataclass
class Program:
    statements: List[Expression]

@dataclass
class Function(Expression):
    name: Token
    params: List[Token]
    body: Block

@dataclass
class Return(Expression):
    keyword: Token
    value: Expression

@dataclass
class Call(Expression):
    callee: Expression
    paren: Token
    arguments: List[Expression]

@dataclass
class Array(Expression):
    elements: List[Expression]

@dataclass
class ArrayAccess(Expression):
    array: Expression
    bracket: Token
    index: Expression

@dataclass
class ArrayAssign(Expression):
    array: Expression
    bracket: Token
    index: Expression
    value: Expression

@dataclass
class StringLength(Expression):
    string: Expression

@dataclass
class StringFind(Expression):
    string: Expression
    substring: Expression

@dataclass
class StringReplace(Expression):
    string: Expression
    old_str: Expression
    new_str: Expression

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self):
        try:
            statements = []
            while not self.is_at_end():
                statements.append(self.declaration())
            return Program(statements)
        except ParseError:
            return None

    def declaration(self):
        if self.match(TokenType.FUN):
            return self.function("function")
        if self.match(TokenType.VAR):
            return self.var_declaration()
            
        return self.statement()

    def var_declaration(self):
        name = self.consume(TokenType.IDENTIFIER, "Expect variable name.")
        
        initializer = None
        if self.match(TokenType.EQUAL):
            initializer = self.expression()
            
        self.consume(TokenType.SEMICOLON, "Expect ';' after variable declaration.")
        return VarDeclaration(name, initializer)

    def function(self, kind: str):
        name = self.consume(TokenType.IDENTIFIER, f"Ожидается имя {kind}.")
        
        self.consume(TokenType.LEFT_PAREN, f"Ожидается '(' после имени {kind}.")
        parameters = []
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                if len(parameters) >= 255:
                    self.error(self.peek(), "Нельзя использовать больше 255 параметров.")
                
                parameters.append(
                    self.consume(TokenType.IDENTIFIER, "Ожидается имя параметра."))
                
                if not self.match(TokenType.COMMA):
                    break
                    
        self.consume(TokenType.RIGHT_PAREN, "Ожидается ')' после параметров.")
        
        self.consume(TokenType.LEFT_BRACE, f"Ожидается '{{' перед телом {kind}.")
        body = self.block()
        return Function(name, parameters, body)

    def statement(self):
        if self.match(TokenType.FOR):
            return self.for_statement()
        if self.match(TokenType.IF):
            return self.if_statement()
        if self.match(TokenType.PRINT):
            return self.print_statement()
        if self.match(TokenType.RETURN):
            return self.return_statement()
        if self.match(TokenType.WHILE):
            return self.while_statement()
        if self.match(TokenType.LEFT_BRACE):
            return self.block()
            
        return self.expression_statement()

    def return_statement(self):
        keyword = self.previous()
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()
            
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после return.")
        return Return(keyword, value)

    def expression_statement(self):
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after expression.")
        return expr

    def print_statement(self):
        value = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after value.")
        return Print(value)

    def if_statement(self):
        self.consume(TokenType.LEFT_PAREN, "Expect '(' after 'if'.")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expect ')' after if condition.")
        
        # Обработка then-ветки
        if self.match(TokenType.LEFT_BRACE):
            then_branch = self.block()
        else:
            then_branch = self.statement()
        
        # Обработка else-ветки (если есть)
        else_branch = None
        if self.match(TokenType.ELSE):
            if self.match(TokenType.LEFT_BRACE):
                else_branch = self.block()
            else:
                else_branch = self.statement()

        return If(condition, then_branch, else_branch)

    def while_statement(self):
        self.consume(TokenType.LEFT_PAREN, "Ожидается '(' после 'while'.")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Ожидается ')' после условия.")
        
        if self.match(TokenType.LEFT_BRACE):
            body = self.block()
        else:
            body = self.statement()
            
        return While(condition, body)

    def for_statement(self):
        self.consume(TokenType.LEFT_PAREN, "Ожидается '(' после 'for'")
        
        # Инициализация
        if self.match(TokenType.SEMICOLON):
            initializer = None
        elif self.match(TokenType.VAR):
            initializer = self.var_declaration()
        else:
            initializer = self.expression_statement()
            
        # Условие
        condition = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.expression()
        self.consume(TokenType.SEMICOLON, "Ожидается ';' после условия цикла")
        
        # Инкремент
        increment = None
        if not self.check(TokenType.RIGHT_PAREN):
            increment = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Ожидается ')' после условий цикла")
        
        # Тело цикла
        body = self.statement()
        
        # Если есть инкремент, добавляем его в конец тела
        if increment is not None:
            body = Block([body, increment])
            
        # Если условие не задано, используем true
        if condition is None:
            condition = Literal(True)
            
        # Преобразуем for в while
        body = While(condition, body)
        
        # Если есть инициализация, добавляем её перед циклом
        if initializer is not None:
            body = Block([initializer, body])
            
        return body

    def block(self):
        statements = []
        
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            statements.append(self.declaration())
            
        self.consume(TokenType.RIGHT_BRACE, "Expect '}' after block.")
        return Block(statements)

    def expression(self):
        return self.assignment()

    def assignment(self):
        expr = self.equality()
        
        if self.match(TokenType.EQUAL):
            equals = self.previous()
            value = self.assignment()
            
            if isinstance(expr, Variable):
                name = expr.name
                return Assignment(name, value)
            elif isinstance(expr, ArrayAccess):
                return ArrayAssign(expr.array, expr.bracket, expr.index, value)
                
            self.error(equals, "Invalid assignment target.")
            
        return expr

    def equality(self):
        expr = self.comparison()

        while self.match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator = self.previous()
            right = self.comparison()
            expr = Binary(expr, operator, right)

        return expr

    def comparison(self):
        expr = self.term()

        while self.match(TokenType.GREATER, TokenType.GREATER_EQUAL,
                        TokenType.LESS, TokenType.LESS_EQUAL):
            operator = self.previous()
            right = self.term()
            expr = Binary(expr, operator, right)

        return expr

    def term(self):
        expr = self.factor()

        while self.match(TokenType.MINUS, TokenType.PLUS):
            operator = self.previous()
            right = self.factor()
            expr = Binary(expr, operator, right)

        return expr

    def factor(self):
        expr = self.unary()

        while self.match(TokenType.SLASH, TokenType.STAR, TokenType.PERCENT):
            operator = self.previous()
            right = self.unary()
            expr = Binary(expr, operator, right)

        return expr

    def unary(self):
        if self.match(TokenType.BANG, TokenType.MINUS):
            operator = self.previous()
            right = self.unary()
            return Unary(operator, right)

        return self.call()

    def call(self):
        expr = self.primary()
        
        while True:
            if self.match(TokenType.LEFT_PAREN):
                expr = self.finish_call(expr)
            elif self.match(TokenType.LEFT_BRACKET):
                expr = self.finish_array_access(expr)
            else:
                break
                
        return expr

    def finish_call(self, callee):
        arguments = []
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                if len(arguments) >= 255:
                    self.error(self.peek(), "Нельзя передать больше 255 аргументов.")
                arguments.append(self.expression())
                if not self.match(TokenType.COMMA):
                    break
                    
        paren = self.consume(TokenType.RIGHT_PAREN, "Ожидается ')' после аргументов.")
        
        return Call(callee, paren, arguments)

    def finish_array_access(self, array):
        bracket = self.previous()
        index = self.expression()
        self.consume(TokenType.RIGHT_BRACKET, "Ожидается ']' после индекса массива.")
        return ArrayAccess(array, bracket, index)

    def primary(self):
        if self.match(TokenType.FALSE): 
            return Literal(False)
        if self.match(TokenType.TRUE): 
            return Literal(True)
        if self.match(TokenType.NIL): 
            return Literal(None)
        if self.match(TokenType.NUMBER, TokenType.STRING):
            return Literal(self.previous().literal)
        if self.match(TokenType.IDENTIFIER):
            return Variable(self.previous())
        if self.match(TokenType.LEFT_PAREN):
            expr = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expect ')' after expression.")
            return Grouping(expr)
        if self.match(TokenType.LEFT_BRACKET):
            elements = []
            if not self.check(TokenType.RIGHT_BRACKET):
                while True:
                    elements.append(self.expression())
                    if not self.match(TokenType.COMMA):
                        break
            self.consume(TokenType.RIGHT_BRACKET, "Ожидается ']' после элементов массива.")
            return Array(elements)
        if self.match(TokenType.LENGTH):
            self.consume(TokenType.LEFT_PAREN, "Ожидается '(' после 'length'.")
            string = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Ожидается ')' после аргумента.")
            return StringLength(string)
        if self.match(TokenType.FIND):
            self.consume(TokenType.LEFT_PAREN, "Ожидается '(' после 'find'.")
            string = self.expression()
            self.consume(TokenType.COMMA, "Ожидается ',' после первого аргумента.")
            substring = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Ожидается ')' после аргументов.")
            return StringFind(string, substring)
        if self.match(TokenType.REPLACE):
            self.consume(TokenType.LEFT_PAREN, "Ожидается '(' после 'replace'.")
            string = self.expression()
            self.consume(TokenType.COMMA, "Ожидается ',' после первого аргумента.")
            old_str = self.expression()
            self.consume(TokenType.COMMA, "Ожидается ',' после второго аргумента.")
            new_str = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Ожидается ')' после аргументов.")
            return StringReplace(string, old_str, new_str)
            
        raise self.error(self.peek(), "Expect expression.")

    def match(self, *types):
        for type in types:
            if self.check(type):
                self.advance()
                return True
        return False

    def check(self, type):
        if self.is_at_end():
            return False
        return self.peek().type == type

    def advance(self):
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def is_at_end(self):
        return self.peek().type == TokenType.EOF

    def peek(self):
        return self.tokens[self.current]

    def previous(self):
        return self.tokens[self.current - 1]

    def consume(self, type, message):
        if self.check(type):
            return self.advance()
        raise self.error(self.peek(), message)

    def error(self, token, message):
        if token.type == TokenType.EOF:
            where = "end"
        else:
            where = token.lexeme
        raise ParseError(token.line, where, message)

    def report(self, line, where, message):
        print(f"[line {line}] Error{where}: {message}")

    def synchronize(self):
        self.advance()

        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return

            if self.peek().type in [TokenType.CLASS, TokenType.FUN, TokenType.VAR, TokenType.FOR, TokenType.IF, TokenType.WHILE, TokenType.RETURN]:
                return

            self.advance()
