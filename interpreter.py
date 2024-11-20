from typing import Any, Dict, List
from parser import Expression, Binary, Grouping, Literal, Unary, Variable, VarDeclaration, Assignment, Program, Print, If, Block, While, Function, Return, Call, Array, ArrayAccess, ArrayAssign, StringLength, StringFind, StringReplace
from lexer import Token, TokenType

class RuntimeError(Exception):
    def __init__(self, token: Token, message: str):
        self.token = token
        self.message = message
        super().__init__(self.message)

class Environment:
    def __init__(self, enclosing=None):
        self.values: Dict[str, Any] = {}
        self.enclosing = enclosing

    def define(self, name: str, value: Any):
        self.values[name] = value

    def get(self, name: Token) -> Any:
        if name.lexeme in self.values:
            return self.values[name.lexeme]

        if self.enclosing is not None:
            return self.enclosing.get(name)

        raise RuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def assign(self, name: Token, value: Any):
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return

        raise RuntimeError(name, f"Undefined variable '{name.lexeme}'.")

class AetherFunction:
    def __init__(self, declaration: Function, closure: Environment):
        self.declaration = declaration
        self.closure = closure

    def call(self, interpreter, arguments: List[Any]) -> Any:
        environment = Environment(self.closure)
        for i in range(len(self.declaration.params)):
            environment.define(self.declaration.params[i].lexeme, arguments[i])
            
        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnValue as return_value:
            return return_value.value
            
        return None

    def arity(self) -> int:
        return len(self.declaration.params)

class ReturnValue(Exception):
    def __init__(self, value: Any):
        self.value = value
        super().__init__()

class Interpreter:
    def __init__(self):
        self.environment = Environment()
        self.globals = self.environment
        self.output_function = print

    def set_output_function(self, output_function):
        self.output_function = output_function

    def interpret(self, program):
        try:
            if isinstance(program, Program):
                for statement in program.statements:
                    self.evaluate(statement)
            else:
                self.evaluate(program)
        except RuntimeError as error:
            self.runtime_error(error)

    def evaluate(self, expr: Expression) -> Any:
        if isinstance(expr, Literal):
            if isinstance(expr.value, str):
                print(f"Debug - Raw string: {repr(expr.value)}")  
                # Обрабатываем escape-последовательности
                i = 0
                result = []
                while i < len(expr.value):
                    if expr.value[i] == '\\' and i + 1 < len(expr.value):
                        next_char = expr.value[i + 1]
                        if next_char == 'n':
                            result.append('\n')
                            print(f"Debug - Found \\n at position {i}")
                        elif next_char == 't':
                            result.append('\t')
                            print(f"Debug - Found \\t at position {i}")
                        elif next_char == 'r':
                            result.append('\r')
                            print(f"Debug - Found \\r at position {i}")
                        elif next_char == '"':
                            result.append('"')
                            print(f"Debug - Found quote at position {i}")
                        elif next_char == '\\':
                            result.append('\\')
                            print(f"Debug - Found backslash at position {i}")
                        else:
                            result.append('\\' + next_char)
                            print(f"Debug - Found unknown escape sequence \\{next_char} at position {i}")
                        i += 2
                    else:
                        result.append(expr.value[i])
                        i += 1
                final_result = ''.join(result)
                print(f"Debug - Processed string: {repr(final_result)}")  
                return final_result
            return expr.value
        elif isinstance(expr, Grouping):
            return self.evaluate(expr.expression)
        elif isinstance(expr, Unary):
            right = self.evaluate(expr.right)
            
            if expr.operator.type == TokenType.MINUS:
                self.check_number_operand(expr.operator, right)
                return -float(right)
            elif expr.operator.type == TokenType.BANG:
                return not self.is_truthy(right)

        elif isinstance(expr, Binary):
            left = self.evaluate(expr.left)
            right = self.evaluate(expr.right)
            
            if expr.operator.type == TokenType.MINUS:
                self.check_number_operands(expr.operator, left, right)
                return float(left) - float(right)
            elif expr.operator.type == TokenType.PLUS:
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                self.check_number_operands(expr.operator, left, right)
                return float(left) + float(right)
            elif expr.operator.type == TokenType.SLASH:
                self.check_number_operands(expr.operator, left, right)
                if right == 0:
                    raise RuntimeError(expr.operator, "Division by zero.")
                return float(left) / float(right)
            elif expr.operator.type == TokenType.STAR:
                self.check_number_operands(expr.operator, left, right)
                return float(left) * float(right)
            elif expr.operator.type == TokenType.GREATER:
                self.check_number_operands(expr.operator, left, right)
                return float(left) > float(right)
            elif expr.operator.type == TokenType.GREATER_EQUAL:
                self.check_number_operands(expr.operator, left, right)
                return float(left) >= float(right)
            elif expr.operator.type == TokenType.LESS:
                self.check_number_operands(expr.operator, left, right)
                return float(left) < float(right)
            elif expr.operator.type == TokenType.LESS_EQUAL:
                self.check_number_operands(expr.operator, left, right)
                return float(left) <= float(right)
            elif expr.operator.type == TokenType.EQUAL_EQUAL:
                return self.is_equal(left, right)
            elif expr.operator.type == TokenType.BANG_EQUAL:
                return not self.is_equal(left, right)
            elif expr.operator.type == TokenType.AND:
                return self.is_truthy(left) and self.is_truthy(right)
            elif expr.operator.type == TokenType.OR:
                return self.is_truthy(left) or self.is_truthy(right)
            elif expr.operator.type == TokenType.PERCENT:
                self.check_number_operands(expr.operator, left, right)
                if right == 0:
                    raise RuntimeError(expr.operator, "Division by zero.")
                return float(left) % float(right)
                
        elif isinstance(expr, Variable):
            return self.environment.get(expr.name)
            
        elif isinstance(expr, Assignment):
            value = self.evaluate(expr.value)
            self.environment.assign(expr.name, value)
            return value
            
        elif isinstance(expr, VarDeclaration):
            value = None
            if expr.initializer is not None:
                value = self.evaluate(expr.initializer)
            self.environment.define(expr.name.lexeme, value)
            
        elif isinstance(expr, Print):
            value = self.evaluate(expr.expression)
            self.output_function(str(value))
            return None
            
        elif isinstance(expr, Block):
            return self.execute_block(expr, Environment(self.environment))
                
        elif isinstance(expr, If):
            if self.is_truthy(self.evaluate(expr.condition)):
                self.evaluate(expr.then_branch)
            elif expr.else_branch is not None:
                self.evaluate(expr.else_branch)
                
        elif isinstance(expr, While):
            while self.is_truthy(self.evaluate(expr.condition)):
                self.evaluate(expr.body)

        elif isinstance(expr, Function):
            function = AetherFunction(expr, self.environment)
            self.environment.define(expr.name.lexeme, function)
            
        elif isinstance(expr, Call):
            callee = self.evaluate(expr.callee)
            
            arguments = []
            for argument in expr.arguments:
                arguments.append(self.evaluate(argument))
                
            if not isinstance(callee, AetherFunction):
                raise RuntimeError(expr.paren, "Can only call functions.")
                
            if len(arguments) != callee.arity():
                raise RuntimeError(expr.paren, f"Expected {callee.arity()} arguments but got {len(arguments)}.")
                
            return callee.call(self, arguments)
            
        elif isinstance(expr, Return):
            value = None
            if expr.value is not None:
                value = self.evaluate(expr.value)
                
            raise ReturnValue(value)

        elif isinstance(expr, Array):
            return self.visit_array_expr(expr)

        elif isinstance(expr, ArrayAccess):
            return self.visit_array_access_expr(expr)

        elif isinstance(expr, ArrayAssign):
            return self.visit_array_assign_expr(expr)

        elif isinstance(expr, StringLength):
            return self.visit_string_length_expr(expr)

        elif isinstance(expr, StringFind):
            return self.visit_string_find_expr(expr)

        elif isinstance(expr, StringReplace):
            return self.visit_string_replace_expr(expr)

    def visit_array_expr(self, expr: Array) -> Any:
        elements = [self.evaluate(element) for element in expr.elements]
        return elements

    def visit_array_access_expr(self, expr: ArrayAccess) -> Any:
        array = self.evaluate(expr.array)
        index = self.evaluate(expr.index)
        
        if not isinstance(array, list):
            raise RuntimeError(expr.bracket, "Индексация возможна только для массивов.")
        if not isinstance(index, (int, float)):
            raise RuntimeError(expr.bracket, "Индекс должен быть числом.")
        
        index = int(index)
        if index < 0 or index >= len(array):
            raise RuntimeError(expr.bracket, f"Индекс {index} выходит за границы массива.")
            
        return array[index]

    def visit_array_assign_expr(self, expr: ArrayAssign) -> Any:
        array = self.evaluate(expr.array)
        index = self.evaluate(expr.index)
        value = self.evaluate(expr.value)
        
        if not isinstance(array, list):
            raise RuntimeError(expr.bracket, "Индексация возможна только для массивов.")
        if not isinstance(index, (int, float)):
            raise RuntimeError(expr.bracket, "Индекс должен быть числом.")
            
        index = int(index)
        if index < 0 or index >= len(array):
            raise RuntimeError(expr.bracket, f"Индекс {index} выходит за границы массива.")
            
        array[index] = value
        return value

    def visit_string_length_expr(self, expr: StringLength) -> Any:
        string = self.evaluate(expr.string)
        if not isinstance(string, str):
            raise RuntimeError(expr.length, f"Операция length ожидает строку, получено {type(string)}")
        return len(string)

    def visit_string_find_expr(self, expr: StringFind) -> Any:
        string = self.evaluate(expr.string)
        substring = self.evaluate(expr.substring)
        
        if not isinstance(string, str):
            raise RuntimeError(expr.find, f"Первый аргумент find должен быть строкой, получено {type(string)}")
        if not isinstance(substring, str):
            raise RuntimeError(expr.find, f"Второй аргумент find должен быть строкой, получено {type(substring)}")
            
        return string.find(substring)

    def visit_string_replace_expr(self, expr: StringReplace) -> Any:
        string = self.evaluate(expr.string)
        old_str = self.evaluate(expr.old_str)
        new_str = self.evaluate(expr.new_str)
        
        if not isinstance(string, str):
            raise RuntimeError(expr.replace, f"Первый аргумент replace должен быть строкой, получено {type(string)}")
        if not isinstance(old_str, str):
            raise RuntimeError(expr.replace, f"Второй аргумент replace должен быть строкой, получено {type(old_str)}")
        if not isinstance(new_str, str):
            raise RuntimeError(expr.replace, f"Третий аргумент replace должен быть строкой, получено {type(new_str)}")
            
        return string.replace(old_str, new_str)

    def execute_block(self, statements: Block, environment: Environment) -> None:
        previous = self.environment
        try:
            self.environment = environment
            for statement in statements.statements:
                self.evaluate(statement)
        finally:
            self.environment = previous

    def visit_binary_expr(self, expr: Binary) -> Any:
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)

        if expr.operator.type == TokenType.MINUS:
            self.check_number_operands(expr.operator, left, right)
            return float(left) - float(right)
        elif expr.operator.type == TokenType.SLASH:
            self.check_number_operands(expr.operator, left, right)
            if right == 0:
                raise RuntimeError(expr.operator, "Division by zero.")
            return float(left) / float(right)
        elif expr.operator.type == TokenType.STAR:
            self.check_number_operands(expr.operator, left, right)
            return float(left) * float(right)
        elif expr.operator.type == TokenType.PLUS:
            if isinstance(left, float) and isinstance(right, float):
                return float(left) + float(right)
            elif isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            raise RuntimeError(expr.operator, "Operands must be two numbers or two strings.")
        elif expr.operator.type == TokenType.GREATER:
            self.check_number_operands(expr.operator, left, right)
            return float(left) > float(right)
        elif expr.operator.type == TokenType.GREATER_EQUAL:
            self.check_number_operands(expr.operator, left, right)
            return float(left) >= float(right)
        elif expr.operator.type == TokenType.LESS:
            self.check_number_operands(expr.operator, left, right)
            return float(left) < float(right)
        elif expr.operator.type == TokenType.LESS_EQUAL:
            self.check_number_operands(expr.operator, left, right)
            return float(left) <= float(right)
        elif expr.operator.type == TokenType.BANG_EQUAL:
            return not self.is_equal(left, right)
        elif expr.operator.type == TokenType.EQUAL_EQUAL:
            return self.is_equal(left, right)
        elif expr.operator.type == TokenType.PERCENT:
            self.check_number_operands(expr.operator, left, right)
            if right == 0:
                raise RuntimeError(expr.operator, "Division by zero.")
            return float(left) % float(right)

        return None

    def visit_grouping_expr(self, expr: Grouping) -> Any:
        return self.evaluate(expr.expression)

    def visit_literal_expr(self, expr: Literal) -> Any:
        return expr.value

    def visit_unary_expr(self, expr: Unary) -> Any:
        right = self.evaluate(expr.right)

        if expr.operator.type == TokenType.MINUS:
            self.check_number_operand(expr.operator, right)
            return -float(right)
        elif expr.operator.type == TokenType.BANG:
            return not self.is_truthy(right)

        return None

    def visit_variable_expr(self, expr: Variable) -> Any:
        return self.environment.get(expr.name)

    def visit_var_declaration(self, expr: VarDeclaration) -> Any:
        value = None
        if expr.initializer is not None:
            value = self.evaluate(expr.initializer)
        
        self.environment.define(expr.name.lexeme, value)
        return value

    def visit_assignment(self, expr: Assignment) -> Any:
        value = self.evaluate(expr.value)
        self.environment.assign(expr.name, value)
        return value

    def visit_if(self, expr: If):
        if self.is_truthy(self.evaluate(expr.condition)):
            return self.evaluate(expr.then_branch)
        elif expr.else_branch is not None:
            return self.evaluate(expr.else_branch)
        return None

    def visit_block(self, expr: Block):
        for statement in expr.statements:
            self.evaluate(statement)
        return None

    def check_number_operand(self, operator: Token, operand: Any):
        if isinstance(operand, float):
            return
        raise RuntimeError(operator, "Operand must be a number.")

    def check_number_operands(self, operator: Token, left: Any, right: Any):
        if isinstance(left, float) and isinstance(right, float):
            return
        raise RuntimeError(operator, "Operands must be numbers.")

    def is_truthy(self, obj: Any) -> bool:
        if obj is None:
            return False
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, (int, float)):
            return obj != 0
        if isinstance(obj, str):
            return len(obj) > 0
        return True

    def is_equal(self, a: Any, b: Any) -> bool:
        if a is None and b is None:
            return True
        if a is None:
            return False
        return a == b

    def stringify(self, obj: Any) -> str:
        if obj is None:
            return "nil"
        
        if isinstance(obj, float):
            text = str(obj)
            if text.endswith(".0"):
                text = text[:-2]
            return text
            
        if isinstance(obj, bool):
            return str(obj).lower()
            
        if isinstance(obj, list):
            elements = [self.stringify(elem) for elem in obj]
            return "[" + ", ".join(elements) + "]"
            
        return str(obj)

    def runtime_error(self, error: RuntimeError):
        self.output_function(f"{error.message}\n[line {error.token.line}]")
