from enum import Enum, auto
from typing import Optional, final
from pydpp.compiler.position import FileCoordinates, FileSpan
from pydpp.compiler.problem import ProblemSet, ProblemSeverity
import re


class TokenKind(Enum):
    """
    A kind of token, that qualifies what a token *is* exactly. See the Token class below for more information.
    """
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
    SYM_COMMA = auto()
    "Symbol for comma: ,"
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

    def __eq__(self, other):
        """
        Two tokens are equal if they have the same kind (and same kind-specific attributes, if any).
        Subclasses must override this method to compare their own attributes.
        Position is ignored as it's just metadata.
        """
        return self.kind == other.kind


@final
class NumberLiteralToken(Token):
    """A number literal (LITERAL_NUMBER), which can have a decimal/integer part."""
    __slots__ = ("int_part", "dec_part")

    def __init__(self, int_part: int, dec_part: Optional[int], pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.LITERAL_NUM, pos)
        self.int_part = int_part
        "The integer part of the number. Example: in 5.25, it's 5."

        self.dec_part = dec_part
        "The decimal part of the number, which may be null if the number is an integer. Example: in 5.25, it's 25."

    def __repr__(self):
        if self.dec_part:
            return f"{self.kind.name}({self.int_part!r}.{self.dec_part!r})"
        else:
            return f"{self.kind.name}({self.int_part!r})"

    def __eq__(self, other):
        return isinstance(other, NumberLiteralToken) \
            and self.int_part == other.int_part \
            and self.dec_part == other.dec_part


@final
class BoolLiteralToken(Token):
    """A boolean literal (LITERAL_BOOL), which can be either true or false."""
    __slots__ = ("value",)

    def __init__(self, value: bool, pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.LITERAL_BOOL, pos)
        self.value = value
        "The boolean value of the token: true or false."

    def __repr__(self):
        return f"{self.kind.name}({self.value!r})"

    def __eq__(self, other):
        return isinstance(other, BoolLiteralToken) and self.value == other.value


@final
class StringLiteralToken(Token):
    """A string literal (LITERAL_STRING), having a string value."""
    __slots__ = ("value",)

    def __init__(self, value: str, pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.LITERAL_STRING, pos)
        self.value = value
        "The string value contained within the string literal."

    def __repr__(self):
        return f"{self.kind.name}({self.value!r})"

    def __eq__(self, other):
        return isinstance(other, StringLiteralToken) and self.value == other.value


@final
class IdentifierToken(Token):
    """An identifier (IDENTIFIER), which is a name representing a variable or function."""
    __slots__ = ("name",)

    def __init__(self, name: str, pos: Optional[FileSpan] = None):
        super().__init__(TokenKind.IDENTIFIER, pos)
        self.name = name
        "The name of the identifier."

    def __repr__(self):
        return f"{self.kind.name}({self.name!r})"

    def __eq__(self, other):
        return isinstance(other, IdentifierToken) and self.name == other.name


# Map of all known keywords and symbols to their token kind.
# Used in the recognize_kw_sym function.
_kw_sym_map = {
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
    "=": TokenKind.SYM_ASSIGN,
    ",": TokenKind.SYM_COMMA
}
# The length of the longest keyword/symbol
_kw_sym_longest = max(len(k) for k in _kw_sym_map.keys())
# A set of all characters that start a keyword/symbol
# Used to weed out non-keyword/symbol tokens from the get-go.
_kw_sym_first_chars = set(k[0] for k in _kw_sym_map.keys())


class _Tokenizer:
    """
    The tokenizer is responsible for converting a string of code into a sequence of tokens.
    It is the first step of the compilation process.

    This class is used internally for convenience of storing all relevant values in one place.
    The other files should just use the "tokenize" function :)
    """

    def __init__(self, code: str, problems: ProblemSet):
        self.code = code
        "The code to tokenize."

        self.eof = len(code) == 0
        "Whether we've reached the end of the file."

        self.problems = problems
        "The problem set so we can report errors during tokenization."

        self.tokens: list[Token] = []
        """
        The list of tokens we have created so far.
        """

        self.cursor = 0
        """
        The currently read index of the cursor in the code.
        When this is N, the call to peek(1) will yield the N'th character of the code and cursor will be N+1.
        When the cursor is equal to len(code), we have reached the end of the file and eof will be True.
        """

        self.err_start: Optional[FileCoordinates] = None
        """
        The starting position of the current "error", which is set when a character is not recognized at all.
        Set to None once we get a valid character (i.e. consumed by self.consume normally).

        This allows us to raise an error message for a sequence of invalid characters, instead of 
        spitting out an error message *per* invalid character.
        """

        self.pos: FileCoordinates = FileCoordinates(0, 1, 1)
        """
        The current position of the cursor in file coordinates.
        The tuple is (index, line, column), and is immutable, so you can use it freely without copying it.
        """

    def tokenize(self) -> list[Token]:
        """
        Tokenizes the code into a sequence of tokens.
        Returns a list of Token objects.
        """

        # First consume any whitespace or comments before checking for end-of-file.
        self.consume_auxiliary()
        while not self.eof:
            # Try to recognize various kinds of tokens.
            # Identifiers come last since they cover any sequence of letters.
            if self.recognize_kw_sym():  # Recognize a keyword/symbol
                pass
            elif self.recognize_literal():  # Recognize a literal (number, string, bool)
                pass
            elif self.recognize_identifier():  # Recognize an identifier (var/func name)
                pass
            elif not self.eof:  # Check for eof since recognize functions can consume whitespace
                # We have an unrecognized character! It wasn't recognized by any function!
                # What do we do with this character? Consume it, mark it as an erroneous character, and move on.
                self.consume(1, err=True)  # Consume the character and mark it as an error.

        # If still have unrecognized error characters left, don't forget to report the error for those!
        self.flush_unrecognized_error()
        return self.tokens

    def recognize_kw_sym(self) -> bool:
        """
        Recognizes a keyword (KW_XXX) or a symbol (SYM_XXX) in the code.
        If a keyword or a symbol is found, the corresponding token is added to the list of tokens.
        Returns true if a keyword or a symbol was recognized, false otherwise.
        """

        # First skip any unwanted whitespace
        self.consume_auxiliary()

        # Make sure that there is at least one keyword/symbol starting with the next character.
        # If not, well, that's surely not a keyword or symbol. This saves up some time.
        nxt = self.peek()
        if nxt not in _kw_sym_first_chars:
            return False

        # Store the starting position of the Token position.
        start_pos = self.pos

        # Try out all substrings of length [1..k] with k the length of the longest keyword/symbol,
        # in the reverse order. We need to do as not doing this will recognize ">=" as ">" only.
        # For example: if we see "if (ab", we'll try "if (ab", "if (a", "if (", "if", "i", in that order.
        for i in range(_kw_sym_longest, 0, -1):
            # Take the substring of length i
            w = self.peek(i)
            # See if it matches a keyword/symbol
            m = _kw_sym_map.get(w)
            if m is not None:
                # The substring matches! Consume it and add a token.
                self.consume(i)
                self.tokens.append(Token(m, FileSpan(start_pos, self.pos)))
                return True

        return False

    digits_regex = re.compile(r"\d+")
    """The regex used to match a sequence of digits (from 0 to 9)."""

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

                # First, let's read the "integer" part.
                # We know that this integer conversion will succeed as the first character is a digit.
                integer = int(self.consume_regex(self.digits_regex))
                decimal = None  # Initialise the decimal part to none, making it an integer

                # Do we have a decimal separator next (the dot)?
                if self.consume_exact("."):
                    # We do! Let's read the digits after the dot, now that we've consumed it.
                    decimal_str = self.consume_regex(self.digits_regex)  # May be empty
                    if not decimal_str:  # Is it empty?
                        # That's a problem! We have a number missing its decimal digits, like "5."
                        # Instead of ignoring it though, we'll still consider it a "valid" number,
                        # just with a null decimal.
                        self.problems.append(problem="Partie décimale attendue après un point (« . »).",
                                             severity=ProblemSeverity.ERROR,
                                             pos=FileSpan(start_pos, self.pos))
                    else:
                        # We recognized the decimal part, convert it to an integer.
                        decimal = int(decimal_str)

                # Finally add the token to the list.
                self.tokens.append(NumberLiteralToken(integer, decimal, FileSpan(start_pos, self.pos)))
                return True
            else:
                return False

        def bool_literal() -> bool:
            "Boolean literal recognition: true & false"

            start_pos = self.pos
            # If it's true, then create a true token, else if it's false, create a false token. Simple enough!
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
            # Check if we have a quote next, if so, begin reading the string character by character.
            if self.consume_exact("\""):
                # The final "real" value of the string, with escape sequences resolved and all.
                val = ""
                # The current character we're reading
                character = self.consume(1)
                # Whether we're in an escape sequence (currently: \n, \\, \")
                escape = False

                # Read all following characters until:
                # - we hit the end of file (then character will be empty)
                # - we hit a non-escaped quote
                while character != "" and (escape or character != "\""):
                    # Check if we're starting a new escape sequence (while not already escaping of course)
                    if character == '\\' and not escape:
                        # Begin escape mode: don't add the backslash to the val
                        escape = True
                    else:
                        # We're not beginning a new escape sequence. We may be in escape mode though.
                        # Let's check if we're simply adding the character or escaping it.
                        if not escape or character == "\"":
                            # We aren't escaping OR escaping a quote (\"), add the character to the val.
                            val += character
                        elif escape and character == "n":
                            # If we're escaping a newline (\n), add a newline character to the val.
                            val += "\n"
                        else:  # escape and character != "t" and character != "\""
                            # Unknown escape sequence! Weird right?
                            self.problems.append(problem=f"Caractère d'échappement inconnu : « \\{character} ».",
                                                 severity=ProblemSeverity.ERROR,
                                                 pos=FileSpan(start_pos, self.pos))
                            # Ignore character
                        escape = False
                    # Onto the next character.
                    character = self.consume(1)

                if character == "":
                    # Then it's EOF! The string hasn't been closed properly. Report an error.
                    # TODO: Prevent this in some cases when detecting a newline after an escape character?
                    self.problems.append(problem="Chaîne de caractères non terminée.",
                                         severity=ProblemSeverity.ERROR,
                                         pos=FileSpan(start_pos, self.pos))

                # Add the string token to the list.
                self.tokens.append(StringLiteralToken(val, FileSpan(start_pos, self.pos)))
                return True
            else:
                return False

        # Skip any unwanted whitespace
        self.consume_auxiliary()

        # Try each literal type. Order doesn't matter here, it's random.
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

        self.consume_auxiliary()
        start_pos = self.pos

        # Scan all characters until we find an ineligible character.
        # Note that i is exclusive: the valid char range is [self.cursor; i[
        i = self.cursor
        while i < len(self.code) and (
                self.code[i].isalpha()
                or (i != self.cursor and self.code[i].isdigit())
                or self.code[i] == "_"
        ):
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
        Consumes the next n characters of the code: increments the cursor by n.

        Returns the n characters if there are more characters to consume, or an empty string else.

        If err is true, registers the current position to err_start if not already done;
        else, flushes the existing error.
        """

        # First, handle errors state switches correctly (i.e. err=False to err=True and vice-versa)
        if err and self.err_start is None:
            # We got an erroneous character!
            # Add an "error marker" here, we'll get rid of it on the next non-error consumption.
            self.err_start = self.pos
        elif not err and self.err_start is not None:
            # We're consuming a valid character! Get rid of the error marker.
            self.flush_unrecognized_error()

        # Note: this algorithm could be faster if we used smart search algorithms
        #       but this is python and most calls have small n so it doesn't make sense.

        # Store the substring to return, and the line/col coordinates to edit while scrubbing through the string.
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

            # Onto the next character!
            self.cursor += 1
            n -= 1

        # Update the position and eof flags respectively.
        # pos isn't mutated, so previous references to it are left untouched.
        self.pos = FileCoordinates(self.cursor, line, col)
        self.eof = self.cursor >= len(self.code)

        # Return the consumed substring, may be less than n characters if eof is reached.
        return substr

    def consume_exact(self, s: str) -> bool:
        """
        Consumes the next characters of the code if they match the given string.
        Returns true if the string was consumed, false otherwise.
        """

        # Peek the next characters and see if it's the exact same string as s.
        if self.peek(len(s)) == s:
            self.consume(len(s))
            return True
        else:
            return False

    def consume_auxiliary(self):
        """
        Consumes all the whitespace characters until the next non-whitespace character,
        and comments (single-line only).
        """
        i = self.cursor  # i is exclusive

        # Continue extending the interval as long as we find a space or a slash.
        slash = False # True when we have may have a comment starting
        while i < len(self.code) and (self.code[i].isspace() or (slash := self.code[i] == '/')):
            # Is this is a comment start?
            if slash and self.code[i:i+2] == "//":
                # We're in a comment! Consume all characters until the end of the line.
                while i < len(self.code) and self.code[i] != "\n":
                    i += 1
                slash = False
            else:
                # It's a space, consume it and go to the next character
                i += 1

        if i != self.cursor:
            self.consume(i - self.cursor)

    def consume_regex(self, regex: re.Pattern[str]) -> str:
        """
        Consumes the next characters in the code that match the regex.
        Returns the matching string if the regex matched, an empty string otherwise.
        """

        # Does the regex match the string beginning from the cursor?
        m = regex.match(self.code, self.cursor)
        if m is None:
            # No, return empty
            return ""
        else:
            # Yes! Consume the matched string and return it.
            return self.consume(len(m.group()))

    def peek(self, n: int = 1) -> str:
        """
        Peeks the next character in the code, without consuming it.
        Characters beyond the end of file are ignored, so the string might be shorter than n characters.
        """
        return self.code[self.cursor:self.cursor + n]

    def peek_until_whitespace(self):
        """
        Peeks the next "word" in the code, until we reach a whitespace character or the EOF.
        Doesn't consume the word.
        """
        i = self.cursor  # i is exclusive
        # Is the current character valid (not a space)?
        while i < len(self.code) and not self.code[i].isspace():
            i += 1  # This character is okay, onto the next!
        return self.code[self.cursor:i]  # Ranges are [a; b[ (exclusive end)

    def peek_regex(self, regex: re.Pattern[str]) -> str:
        """
        Peeks the next characters that match the given regex, without consuming them.
        Returns the characters that match the regex; with no match, returns an empty string.
        """

        # Match the given regex starting from the cursor.
        m = regex.match(self.code, self.cursor)
        if m is None:
            # No match, return an empty string
            return ""
        else:
            # We have a match! Return the matching characters.
            return m.group()

    def flush_unrecognized_error(self):
        """
        Flushes the current error to the problem set, if any.
        """
        if self.err_start is not None:
            chars = self.code[self.err_start.index:self.cursor]
            self.problems.append(problem=f"Séquence de caractères non reconnue : « {chars} ».",
                                 severity=ProblemSeverity.ERROR,
                                 pos=FileSpan(self.err_start, self.pos))
            self.err_start = None


def tokenize(code: str, problems: ProblemSet) -> list[Token]:
    """
    Tokenizes the given code into a sequence of tokens.
    Requires a ProblemSet to report any errors happening during tokenization.
    :param code: The code to tokenize.
    :param problems: The problem set which may contain errors afterward.
    :return: A list of tokens.
    """
    return _Tokenizer(code, problems).tokenize()
