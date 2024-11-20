from enum import Enum
from dataclasses import dataclass

class TokenType(Enum):
    LEFT_PAREN = '('
    RIGHT_PAREN = ')'
    LEFT_BRACE = '{'
    RIGHT_BRACE = '}'
    LEFT_BRACKET = '['
    RIGHT_BRACKET = ']'
    COMMA = ','
    DOT = '.'
    MINUS = '-'
    PLUS = '+'
    SEMICOLON = ';'
    SLASH = '/'
    STAR = '*'
    PERCENT = '%'

    BANG = '!'
    BANG_EQUAL = '!='
    EQUAL = '='
    EQUAL_EQUAL = '=='
    GREATER = '>'
    GREATER_EQUAL = '>='
    LESS = '<'
    LESS_EQUAL = '<='

    IDENTIFIER = 'IDENTIFIER'
    STRING = 'STRING'
    NUMBER = 'NUMBER'

    AND = 'and'
    OR = 'or'
    IF = 'if'
    ELSE = 'else'
    TRUE = 'true'
    FALSE = 'false'
    FUN = 'fun'
    FOR = 'for'
    NIL = 'nil'
    PRINT = 'print'
    RETURN = 'return'
    VAR = 'var'
    WHILE = 'while'
    CLASS = 'class'
    SUPER = 'super'
    THIS = 'this'
    LENGTH = 'length'
    FIND = 'find'
    REPLACE = 'replace'

    EOF = 'EOF'

@dataclass
class Token:
    type: TokenType
    lexeme: str
    literal: object
    line: int

    def __str__(self):
        return f"{self.type} {self.lexeme} {self.literal}"

class LexerError(Exception):
    def __init__(self, line, message):
        self.line = line
        self.message = message
        super().__init__(f"[line {line}] Error: {message}")

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        
        # Только те команды, которые реально реализованы
        self.KEYWORDS = {
            'and': TokenType.AND,
            'class': TokenType.CLASS,
            'else': TokenType.ELSE,
            'false': TokenType.FALSE,
            'for': TokenType.FOR,
            'fun': TokenType.FUN,
            'if': TokenType.IF,
            'nil': TokenType.NIL,
            'or': TokenType.OR,
            'print': TokenType.PRINT,
            'return': TokenType.RETURN,
            'super': TokenType.SUPER,
            'this': TokenType.THIS,
            'true': TokenType.TRUE,
            'var': TokenType.VAR,
            'while': TokenType.WHILE,
            'length': TokenType.LENGTH,
            'find': TokenType.FIND,
            'replace': TokenType.REPLACE
        }
        
        # Только реально работающие команды с их описанием
        self.COMMANDS = {
            'print': 'вывести значение на экран',
            'var': 'объявить переменную',
            'if': 'условный оператор',
            'else': 'иначе (для if)',
            'true': 'логическое значение истина',
            'false': 'логическое значение ложь',
            'and': 'логическое И',
            'or': 'логическое ИЛИ',
            'while': 'цикл с условием',
            'for': 'цикл for',
            'fun': 'объявление функции',
            'return': 'возврат значения из функции',
            'length': 'получить длину строки',
            'find': 'найти позицию подстроки',
            'replace': 'заменить подстроку'
        }
        
    def _find_similar_command(self, text):
        """Находит наиболее похожую команду используя расстояние Левенштейна"""
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]
        
        # Находим команду с минимальным расстоянием
        distances = {cmd: levenshtein_distance(text.lower(), cmd.lower()) 
                    for cmd in self.COMMANDS.keys()}
        closest = min(distances.items(), key=lambda x: x[1])
        
        # Возвращаем подсказку только если команды достаточно похожи
        if closest[1] <= 2:  # максимально допустимое расстояние
            return closest[0]
        return None

    def scan_tokens(self):
        while not self.is_at_end():
            self.start = self.current
            self.scan_token()

        self.tokens.append(Token(TokenType.EOF, "", None, self.line))
        return self.tokens

    def scan_token(self):
        c = self.advance()
        
        if c == '(':
            self.add_token(TokenType.LEFT_PAREN)
        elif c == ')':
            self.add_token(TokenType.RIGHT_PAREN)
        elif c == '{':
            self.add_token(TokenType.LEFT_BRACE)
        elif c == '}':
            self.add_token(TokenType.RIGHT_BRACE)
        elif c == '[':
            self.add_token(TokenType.LEFT_BRACKET)
        elif c == ']':
            self.add_token(TokenType.RIGHT_BRACKET)
        elif c == ',':
            self.add_token(TokenType.COMMA)
        elif c == '.':
            self.add_token(TokenType.DOT)
        elif c == '-':
            self.add_token(TokenType.MINUS)
        elif c == '+':
            self.add_token(TokenType.PLUS)
        elif c == ';':
            self.add_token(TokenType.SEMICOLON)
        elif c == '*':
            self.add_token(TokenType.STAR)
        elif c == '%':
            self.add_token(TokenType.PERCENT)
        elif c == '!':
            self.add_token(TokenType.BANG_EQUAL if self.match('=') else TokenType.BANG)
        elif c == '=':
            self.add_token(TokenType.EQUAL_EQUAL if self.match('=') else TokenType.EQUAL)
        elif c == '<':
            self.add_token(TokenType.LESS_EQUAL if self.match('=') else TokenType.LESS)
        elif c == '>':
            self.add_token(TokenType.GREATER_EQUAL if self.match('=') else TokenType.GREATER)
        elif c == '/':
            if self.match('/'):
                # Комментарий до конца строки
                while self.peek() != '\n' and not self.is_at_end():
                    self.advance()
            else:
                self.add_token(TokenType.SLASH)
        elif c in ' \r\t':
            # Игнорируем пробельные символы
            pass
        elif c == '\n':
            self.line += 1
        elif c == '"':
            self.string()
        elif c.isdigit():
            self.number()
        elif c.isalpha() or c == '_':
            self.identifier()
        elif c == '\\':
            # Разрешаем escape-последовательности внутри строк
            if self.is_in_string():
                self.advance()  # Пропускаем следующий символ
            else:
                raise LexerError(self.line, f"Unexpected character '{c}'")
        else:
            raise LexerError(self.line, f"Unexpected character '{c}'")

    def is_in_string(self):
        # Проверяем, находимся ли мы внутри строки
        # Подсчитываем количество кавычек до текущей позиции
        count = 0
        for i in range(self.start):
            if self.source[i] == '"' and (i == 0 or self.source[i-1] != '\\'):
                count += 1
        return count % 2 == 1

    def identifier(self):
        while self.is_alphanumeric(self.peek()):
            self.advance()

        text = self.source[self.start:self.current]
        
        # Сначала проверяем, является ли это ключевым словом
        type = self.KEYWORDS.get(text)
        if type is not None:
            self.add_token(type)
            return
            
        # Проверяем правила для пользовательских идентификаторов
        if not text[0].isalpha():
            raise LexerError(self.line, f"Identifier '{text}' must start with a letter")
            
        if not all(c.isalnum() or c == '_' for c in text):
            raise LexerError(self.line, f"Invalid identifier '{text}': can only contain letters, numbers and underscore")
            
        # Если все проверки пройдены, это валидный идентификатор
        self.add_token(TokenType.IDENTIFIER, text)

    def number(self):
        while self.is_digit(self.peek()):
            self.advance()

        if self.peek() == '.' and self.is_digit(self.peek_next()):
            self.advance()
            while self.is_digit(self.peek()):
                self.advance()

        self.add_token(TokenType.NUMBER, float(self.source[self.start:self.current]))

    def string(self):
        while self.peek() != '"' and not self.is_at_end():
            if self.peek() == '\\':
                # Обрабатываем escape-последовательности
                if not self.is_at_end() and self.peek_next() in ['"', 'n', 't', 'r', '\\']:
                    self.advance()  # Пропускаем '\'
                    self.advance()  # Пропускаем следующий символ
                else:
                    raise LexerError(self.line, "Invalid escape sequence")
            else:
                if self.peek() == '\n':
                    self.line += 1
                self.advance()

        if self.is_at_end():
            raise LexerError(self.line, "Unterminated string.")

        # Закрывающая кавычка
        self.advance()

        # Получаем значение строки без кавычек
        value = self.source[self.start + 1:self.current - 1]
        self.add_token(TokenType.STRING, value)

    def match(self, expected):
        if self.is_at_end():
            return False
        if self.source[self.current] != expected:
            return False

        self.current += 1
        return True

    def peek(self):
        if self.is_at_end():
            return '\0'
        return self.source[self.current]

    def peek_next(self):
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]

    def is_alpha(self, c):
        return ('a' <= c <= 'z') or ('A' <= c <= 'Z') or c == '_'

    def is_digit(self, c):
        return '0' <= c <= '9'

    def is_alphanumeric(self, c):
        return self.is_alpha(c) or self.is_digit(c)

    def is_at_end(self):
        return self.current >= len(self.source)

    def advance(self):
        self.current += 1
        return self.source[self.current - 1]

    def add_token(self, type, literal=None, line=None):
        text = self.source[self.start:self.current]
        if line is None:
            line = self.line
        self.tokens.append(Token(type, text, literal, line))
