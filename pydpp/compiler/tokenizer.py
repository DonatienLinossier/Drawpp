from collections import namedtuple
from enum import Enum, auto
from typing import Optional, final
from pydpp.compiler.position import FileCoordinates, FileSpan
from pydpp.compiler.problem import ProblemSet, ProblemSeverity
import re


class TokenKind(Enum):
    KW_IF = auto()
    "The if keyword: if"
    KW_ELSE = auto()
    "The else keyword: else"
    KW_WHILE = auto()
    "Keyword for while loops: while"
    KW_INT = auto()
    "Keyword for integer type: int"
    KW_FLOAT = auto()
    "Keyword for float type: float"
    KW_BOOL = auto()
    "Keyword for boolean type: bool"
    KW_STRING = auto()
    "Keyword for string type: string"
    KW_FCT = auto()
    "Keyword for function: fct"
    KW_NOT = auto()
    "Keyword for logical negation: not"
    KW_AND = auto()
    "Keyword for logical and: and"
    KW_OR = auto()
    "Keyword for logical or: or"
    SYM_EQ = auto()
    "Symbol for equality: =="
    SYM_NEQ = auto()
    "Symbol for inequality: !="
    SYM_LT = auto()
    "Symbol for less than: <"
    SYM_LEQ = auto()
    "Symbol for less than or equal to: <="
    SYM_GT = auto()
    "Symbol for greater than: >"
    SYM_GEQ = auto()
    "Symbol for greater than or equal to: >="
    SYM_PLUS = auto()
    "Symbol for addition: +"
    SYM_MINUS = auto()
    "Symbol for subtraction: -"
    SYM_STAR = auto()
    "Symbol for multiplication: *"
    SYM_SLASH = auto()
    "Symbol for division: /"
    SYM_LPAREN = auto()
    "Symbol for left parenthesis: ("
    SYM_RPAREN = auto()
    "Symbol for right parenthesis: )"
    SYM_LBRACE = auto()
    "Symbol for left brace: {"
    SYM_RBRACE = auto()
    "Symbol for right brace: }"
    SYM_SEMICOLON = auto()
    "Symbol for semicolon: ;"
    SYM_ASSIGN = auto()
    "Symbol for assignment: ="
    LITERAL_NUM = auto()
    """A number literal, an integer or decimal value: 4, 4.92, 0.2, 880
    It uses the NumberLiteralToken class.
    That class contains the integer_val and decimal_part attributes."""
    LITERAL_BOOL = auto()
    """A boolean literal: true or false
    It uses the BoolLiteralToken class.
    That class contains the value attribute."""
    LITERAL_STRING = auto()
    """A string literal: "hello", "world", "hello world"
    It uses the StringLiteralToken class.
    That class contains the value attribute.
    """
    IDENTIFIER = auto()
    """An identifier: a name that represents a variable, function, class, etc.
    It uses the IdentifierToken class.
    That class contains the name attribute."""


class Token:
    """
    A token is "fragment" of code, contained inside a sequence of tokens that make up the entire program.
    They make some sort of "alphabet" for the parser to read, available in multiple kinds: keywords (if, else),
    operators (==, !=), literals...

    Example: if x < 4 { print("hello"); }
    => [KW_IF, IDENTIFIER, SYM_LT, LITERAL_NUM, SYM_LBRACE, IDENTIFIER, SYM_SEMICOLON, SYM_RBRACE]

    Most tokens only consist of their "kind" (see TokenKind), which is a simple enum value.
    Some tokens of some particular kinds may have additional information, which are stored as supplementary attributes.
    Check the various subclasses of Token for more information (like NumberLiteralToken).

    Tokens can also track where they come from in the file, with the pos attribute, which contains
    the coordinates of the starting and ending character in the file.
    """

    __slots__ = ("kind", "pos")
    """Register slots for Token objects to save lots of memory, since we'll have thousands of them.
    Subclasses should also register their own slots!"""

    def __init__(self, kind: TokenKind, pos: Optional[FileSpan] = None):
        self.kind = kind
        """The kind of the token. See the TokenKind enum for all possible values.
        Tokens of some particular kinds may have additional information, which are stored as supplementary attributes.
        Check the various subclasses of Token for more information (like NumberLiteralToken)."""

        self.pos = pos
        """The position of the token in the file. May be null if we're not in a file."""

    def __repr__(self):
        return f"{self.kind.name}"


@final
class NumberLiteralToken(Token):

    __slots__ = ("integer_val", "decimal_part")

    def __init__(self, integer_val: int, decimal_part: Optional[int], pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.LITERAL_NUM, pos)
        self.integer_val = integer_val
        "The integer part of the number. Example: in 5.25, it's 5."

        self.decimal_part = decimal_part
        "The decimal part of the number, which may be null if the number is an integer. Example: in 5.25, it's 25."

    def __repr__(self):
        if self.decimal_part:
            return f"{self.kind.name}({self.integer_val!r}.{self.decimal_part!r})"
        else:
            return f"{self.kind.name}({self.integer_val!r})"


@final
class BoolLiteralToken(Token):

    __slots__ = ("value",)

    def __init__(self, value: bool, pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.LITERAL_BOOL, pos)
        self.value = value
        "The boolean value of the token: true or false."

    def __repr__(self):
        return f"{self.kind.name}({self.value!r})"


@final
class StringLiteralToken(Token):

    __slots__ = ("value",)

    def __init__(self, value: str, pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.LITERAL_STRING, pos)
        self.value = value
        "The string value contained within the string literal."

    def __repr__(self):
        return f"{self.kind.name}({self.value!r})"


@final
class IdentifierToken(Token):

    __slots__ = ("name",)

    def __init__(self, name: str, pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.IDENTIFIER, pos)
        self.name = name
        "The name of the identifier."

    def __repr__(self):
        return f"{self.kind.name}({self.name!r})"


class _Tokenizer:
    """
    The tokenizer is responsible for converting a string of code into a sequence of tokens.
    It is the first step of the compilation process.

    This class is internal, the other files should just use the "tokenize" function :)
    """

    tokens: list[Token] = []
    """
    The list of tokens we have created so far.
    """
    cursor = 0
    """
    The currently read index of the cursor in the code.
    When this is N, the call to peek(1) will yield the N'th character of the code and cursor will be N+1.
    """
    err_start: Optional[FileCoordinates] = None
    """
    The starting position of the current "error", which is set when a character is not recognized at all.
    Set to None once we get a valid character (i.e. consumed by self.consume normally).
    """
    pos: FileCoordinates = FileCoordinates(0, 1, 1)
    """
    The current position of the cursor in file coordinates.
    The tuple is (index, line, column), and is immutable, so you can use it freely without copying it.
    """

    def __init__(self, code: str, problems: ProblemSet):
        self.code = code
        "The code to tokenize."
        self.eof = len(code) == 0
        "Whether we've reached the end of the file."
        self.problems = problems

    def tokenize(self) -> list[Token]:
        """
        Tokenizes the code into a sequence of tokens.
        Returns a list of Token objects.
        """

        # First consume any whitespace before checking for end-of-file.
        self.consume_whitespace()
        while not self.eof:
            # Try to recognize various kinds of tokens.
            # Identifiers come last since they cover any sequence of letters.
            if self.recognize_kw_sym():
                pass
            elif self.recognize_literal():
                pass
            elif self.recognize_identifier():
                pass
            elif not self.eof:  # Check for eof since recognize can consume whitespace
                # Unrecognized character! It wasn't recognized by any function!
                # What do we do with this character? Consume it and move on.
                self.consume(1, err=True)  # Consume the character and mark it as an error.

        # If still have unrecognized error characters left, flush them into an error message.
        self.flush_unrecognized_error()
        return self.tokens

    kw_sym_map = {
        "if": TokenKind.KW_IF,
        "else": TokenKind.KW_ELSE,
        "while": TokenKind.KW_WHILE,
        "int": TokenKind.KW_INT,
        "float": TokenKind.KW_FLOAT,
        "bool": TokenKind.KW_BOOL,
        "string": TokenKind.KW_STRING,
        "fct": TokenKind.KW_FCT,
        "not": TokenKind.KW_NOT,
        "and": TokenKind.KW_AND,
        "or": TokenKind.KW_OR,
        "==": TokenKind.SYM_EQ,
        "!=": TokenKind.SYM_NEQ,
        "<": TokenKind.SYM_LT,
        "<=": TokenKind.SYM_LEQ,
        ">": TokenKind.SYM_GT,
        ">=": TokenKind.SYM_GEQ,
        "+": TokenKind.SYM_PLUS,
        "-": TokenKind.SYM_MINUS,
        "*": TokenKind.SYM_STAR,
        "/": TokenKind.SYM_SLASH,
        "(": TokenKind.SYM_LPAREN,
        ")": TokenKind.SYM_RPAREN,
        "{": TokenKind.SYM_LBRACE,
        "}": TokenKind.SYM_RBRACE,
        ";": TokenKind.SYM_SEMICOLON,
        "=": TokenKind.SYM_ASSIGN
    }

    def recognize_kw_sym(self) -> bool:
        """
        Recognizes a keyword (KW_XXX) or a symbol (SYM_XXX) in the code.
        If a keyword or a symbol is found, the corresponding token is added to the list of tokens.
        Returns true if a keyword or a symbol was recognized, false otherwise.
        """

        self.consume_whitespace()

        start_pos = self.pos
        word = self.peek_until_whitespace()

        # Fast path: Keyword/symbol is separated by whitespace
        if word in self.kw_sym_map:
            self.consume(len(word))
            self.tokens.append(Token(self.kw_sym_map[word], FileSpan(start_pos, self.pos)))
            return True

        # We may have no whitespace: like in if{ or else{
        # TODO: Optimise? Prefix tree? Stop until symbol?
        for k, v in self.kw_sym_map.items():
            if self.consume_exact(k):
                self.tokens.append(Token(v, FileSpan(start_pos, self.pos)))
                return True

        return False

    digits_regex = re.compile(r"\d+")

    def recognize_literal(self) -> bool:
        """
        Recognizes a literal in the code: numbers (1, 56.25), booleans (true, false) and strings ("hello").
        If a literal is found, the corresponding token is added to the list of tokens.
        Returns true if a literal was recognized, false otherwise.
        """

        def number_literal() -> bool:
            "Number literal recognition: integer & decimal"

            # Are we starting with a digit? If so, that's a number we got here!
            if self.peek(1).isdigit():
                start_pos = self.pos

                # Cannot fail! We know that the first character is a digit.
                # First read the "integer" part
                integer = int(self.consume_regex(self.digits_regex))
                decimal = None  # Initialise the decimal part to none
                if self.peek(1) == ".":
                    # We have a decimal part! Read it.
                    self.consume(1)  # Consume the dot.
                    decimal_str = self.consume_regex(self.digits_regex)  # May be empty
                    if not decimal_str:  # Is it empty?
                        self.problems.append(problem="Partie décimale attendue après un point (« . »).",
                                             severity=ProblemSeverity.ERROR,
                                             pos=FileSpan(start_pos, self.pos))
                        # This is still a "valid" number, just with a null decimal.
                    else:
                        decimal = int(decimal_str)
                self.tokens.append(NumberLiteralToken(integer, decimal, FileSpan(start_pos, self.pos)))
                return True
            else:
                return False

        def bool_literal() -> bool:
            "Boolean literal recognition: true & false"

            start_pos = self.pos
            if self.consume_exact("true"):
                self.tokens.append(BoolLiteralToken(True, FileSpan(start_pos, self.pos)))
                return True
            elif self.consume_exact("false"):
                self.tokens.append(BoolLiteralToken(False, FileSpan(start_pos, self.pos)))
                return True
            else:
                return False

        def string_literal() -> bool:
            """String literal recognition:  "abc" """

            # Consume all characters into one "val" string until the next non-escaped quote
            start_pos = self.pos
            if self.consume_exact("\""):
                val = ""
                character = self.consume(1)
                escape = False
                while character != "" and (escape or character != "\""):
                    if character == '\\' and not escape:
                        # Begin escape sequence if we aren't already escaping
                        escape = True
                    else:
                        # We're not beginning a new escape sequence: read the character and likely add it
                        if not escape or character == "\"":
                            # Just add the character when not in escape mode OR escaping a quote
                            val += character
                        elif escape and character == "n":
                            # Add a newline character when escaped
                            val += "\n"
                        else:  # escape and character != "t" and character != "\""
                            self.problems.append(problem=f"Caractère d'échappement inconnu : « \\{character} ».",
                                                 severity=ProblemSeverity.ERROR,
                                                 pos=FileSpan(start_pos, self.pos))
                            # Ignore character
                        escape = False
                    character = self.consume(1)
                if character == "":
                    # Then it's EOF!
                    self.problems.append(problem="Chaîne de caractères non terminée.",
                                         severity=ProblemSeverity.ERROR,
                                         pos=FileSpan(start_pos, self.pos))
                self.tokens.append(StringLiteralToken(val, FileSpan(start_pos, self.pos)))
                return True
            else:
                return False

        self.consume_whitespace()
        if number_literal():
            return True
        elif bool_literal():
            return True
        elif string_literal():
            return True
        else:  # No literal found
            return False

    def recognize_identifier(self) -> bool:
        """
        Recognizes an identifier in the code.
        If an identifier is found, the corresponding token is added to the list of tokens.
        Returns true if an identifier was recognized, false otherwise.
        """

        self.consume_whitespace()
        start_pos = self.pos

        # Scan all characters until we find an ineligible character.
        # Note that i is exclusive: the valid char range is [self.cursor; i[
        i = self.cursor
        while i < len(self.code) and (self.code[i].isalpha() or self.code[i] == "_"):
            i += 1

        # Add a token if we have at least one character.
        n = i - self.cursor
        if n > 0:
            self.tokens.append(IdentifierToken(self.consume(n), FileSpan(start_pos, self.pos)))
            return True
        else:
            return False

    def consume(self, n: int, err=False) -> str:
        """
        Consumes the next n characters of the code.

        Returns the n characters if there are more characters to consume, or an empty string else.

        If err is true, registers the current position to err_start if not already done;
        else, flushes the existing error.
        """

        # First, handle errors correctly:
        if err and self.err_start is None:
            # Add an "error marker" here, we'll get rid of it on the next non-error consumption.
            self.err_start = self.pos
        elif not err and self.err_start is not None:
            # We're consuming a valid character! Get rid of the error marker.
            self.flush_unrecognized_error()

        # Note: this algorithm could be faster if we used smart search algorithms
        #       but this is python and most calls have small n so it doesn't make sense.
        substr = self.code[self.cursor:self.cursor + n]
        line = self.pos.line
        col = self.pos.column

        # Advance the cursor character by character so we can update the position accurately.
        while self.cursor < len(self.code) and n > 0:
            # Did we go through a new line? Update the position then!
            if self.code[self.cursor] == "\n":
                line += 1
                col = 1
            else:
                # Else, just add one to the column (x coordinate)
                col += 1

            self.cursor += 1
            n -= 1

        self.pos = FileCoordinates(self.cursor, line, col)
        self.eof = self.cursor >= len(self.code)

        return substr

    def consume_exact(self, s: str) -> bool:
        """
        Consumes the next characters of the code if they match the given string.
        Returns true if the string was consumed, false otherwise.
        """

        if self.peek(len(s)) == s:
            self.consume(len(s))
            return True
        else:
            return False

    def consume_whitespace(self):
        """
        Consumes all the whitespace characters until the next non-whitespace character.
        """
        i = self.cursor  # i is exclusive
        while i < len(self.code) and self.code[i].isspace():
            i += 1  # This character is okay, onto the next!
        self.consume(i - self.cursor)

    def consume_regex(self, regex: re.Pattern[str]) -> str:
        """
        Consumes the next characters in the code that match the regex.
        Returns the matching string if the regex matched, an empty string otherwise.
        """

        m = regex.match(self.code, self.cursor)
        if m is None:
            return ""
        else:
            return self.consume(len(m.group()))

    def peek(self, n: int = 1) -> str:
        """
        Peeks the next character in the code, without consuming it.
        Characters beyond the end of file are ignored
        """
        return self.code[self.cursor:self.cursor + n]

    def peek_until_whitespace(self):
        i = self.cursor  # i is exclusive
        while i < len(self.code) and not self.code[i].isspace():
            i += 1  # This character is okay, onto the next!
            return self.code[self.cursor:i]  # Ranges are [a; b[ (exclusive end)

    def peek_regex(self, regex: re.Pattern[str]) -> str:
        """
        Peeks the next characters in the code, without consuming them.
        Returns the characters that match the regex; with no match, returns an empty string.
        """

        m = regex.match(self.code, self.cursor)
        if m is None:
            return ""
        else:
            return m.group()

    def flush_unrecognized_error(self):
        """
        Flushes the current error, if any.
        """
        if self.err_start is not None:
            chars = self.code[self.err_start.index:self.cursor]
            self.problems.append(problem=f"Séquence de caractères non reconnue : « {chars} ».",
                                 severity=ProblemSeverity.ERROR,
                                 pos=FileSpan(self.err_start, self.pos))
            self.err_start = None


def tokenize(code: str, problems: ProblemSet) -> list[Token]:
    return _Tokenizer(code, problems).tokenize()
