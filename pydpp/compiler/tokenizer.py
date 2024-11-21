from enum import Enum, auto
from typing import Optional
from pydpp.compiler.position import TextSpan
from pydpp.compiler.problem import ProblemSeverity
import re


class AuxiliaryKind(Enum):
    """
    The kind of auxiliary text.
    """
    WHITESPACE = auto()
    "Whitespace: spaces, tabs, newlines, etc."
    SINGLE_LINE_COMMENT = auto()
    "A single line comment: a sequence of characters that are ignored by the parser."
    INVALID = auto()
    "Invalid text: text that couldn't form tokens."


class AuxiliaryText:
    """
    Auxiliary text is any "secondary" text that can be ignored by the parser:
        - whitespace (newlines, space)
        - comments (single-line comments & multi-line)
        - invalid text (text that couldn't form tokens)
    """
    __slots__ = ("kind", "text")

    def __init__(self, kind: AuxiliaryKind, text: str):
        self.kind = kind
        "The kind of auxiliary text."
        self.text = text
        "The text of the auxiliary text."

    @staticmethod
    def whitespace(text: str):
        return AuxiliaryText(AuxiliaryKind.WHITESPACE, text)

    @staticmethod
    def single_line_comment(text: str):
        return AuxiliaryText(AuxiliaryKind.SINGLE_LINE_COMMENT, text)

    @staticmethod
    def invalid(text: str):
        return AuxiliaryText(AuxiliaryKind.INVALID, text)

    def __repr__(self):
        return f"{self.kind.name}({self.text!r})"


class TokenKind(Enum):
    """
    A kind of token, that qualifies what a token *is* exactly. See the Token class below for more information.
    """
    EOF = auto()
    "The end-of-file, always at the end of the list."
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
    Its value is represented by a tuple: (int, int | None)"""
    LITERAL_BOOL = auto()
    """A boolean literal: true or false
    Its value is represented by a bool."""
    LITERAL_STRING = auto()
    """A string literal: "hello", "world", "hello world"
    Its value is represented by a string.
    """
    IDENTIFIER = auto()
    """An identifier: a name that represents a variable, function, class, etc.
    It uses the IdentifierToken class.
    That class contains the name attribute."""


class TokenProblem:
    """
    An issue about a token. Can specify a substring within the token text.
    """

    __slots__ = ("message", "severity", "span")

    def __init__(self,
                 message: str,
                 severity: ProblemSeverity,
                 span: TextSpan):
        self.message = message
        "The message of the problem."
        self.severity = severity
        "The severity of the problem."
        self.span = span
        "The span of the problem within the token's full text, including auxiliary text."

    def __repr__(self):
        return f"TokenProblem({self.message!r}, {self.severity!r}, {self.span!r})"


class _PendingTokenProblem:
    """
    A pending problem for a token. Used in Tokenizer to encode problems with the right coordinates
    (including or excluding auxiliary text).
    """

    __slots__ = ("message", "severity", "span", "text_space")

    def __init__(self,
                 message: str,
                 severity: ProblemSeverity = ProblemSeverity.ERROR,
                 span: TextSpan | None = None,
                 text_space: int | None = None):
        self.message = message
        "The message of the problem."
        self.severity = severity
        "The severity of the problem."

        self.span = span
        "The span of the problem within the text_space."

        self.text_space = text_space
        """
        The coordinate space indicating how the span should be calculated.
        
            - None  -> 'span' starts at the beginning of the token's text, excluding auxiliary text.
            - int n -> 'span' starts at the beginning of the auxiliary text at index n.
        """


class Token:
    """
    A token is "fragment" of code, contained inside a sequence of tokens that make up the entire program.
    They make some sort of "alphabet" for the parser to read, available in multiple kinds: keywords (if, else),
    operators (==, !=), literals...

    Example: if x < 4 { print("hello"); }
    => [KW_IF, IDENTIFIER, SYM_LT, LITERAL_NUM, SYM_LBRACE, IDENTIFIER, SYM_SEMICOLON, SYM_RBRACE]

    Most tokens only consist of their "kind" (see TokenKind), which is a simple enum value.
    Some tokens of some particular kinds may have additional information, which is stored inside the 'value' attribute.

    Applicable value attributes include:
        - TokenKind.LITERAL_NUM: a int or float value, if the number is integer or decimal respectively.
        - TokenKind.LITERAL_BOOL: a bool representing the boolean value.
        - TokenKind.LITERAL_STRING: a string representing the string value
    """

    __slots__ = ("kind", "text", "pre_auxiliary", "full_text", "value", "problems")
    """Register slots for Token objects to save lots of memory, since we'll have thousands of them.
    Subclasses should also register their own slots!"""

    def __init__(self, kind: TokenKind, text: str, pre_auxiliary: tuple[AuxiliaryText, ...] = (),
                 problems: tuple[TokenProblem, ...] = (),
                 value: str | bool | int | float | None = None):
        self.kind = kind
        """The kind of the token. See the TokenKind enum for all possible values.
        Tokens of some particular kinds may have additional information, which are stored as supplementary attributes.
        Check the various subclasses of Token for more information (like NumberLiteralToken)."""

        self.text = text
        """The text of the token, as written in code."""

        self.pre_auxiliary = pre_auxiliary
        """All auxiliary text preceding this token."""

        if len(pre_auxiliary) == 0:
            ft = text
        elif len(pre_auxiliary) == 1:
            ft = pre_auxiliary[0].text + text
        else:
            ft = "".join(a.text for a in pre_auxiliary) + text

        self.full_text = ft
        """The full text of the token, including auxiliary text."""

        self.value: str | bool | int | float | None = value
        "The value of this token, if it represents a literal."

        self.problems = problems
        "All problems related to this token."

    @property
    def has_problems(self) -> bool:
        return len(self.problems) != 0

    def __repr__(self):
        if self.value is not None:
            return f"{self.kind.name}({self.value!r})"
        elif self.kind == TokenKind.IDENTIFIER:
            return f"{self.kind.name}({self.text!r})"
        else:
            return f"{self.kind.name}"

    def with_pre_auxiliary(self, pre_auxiliary: tuple[AuxiliaryText, ...]) -> "Token":
        """
        Returns a new token with the given auxiliary text.
        """
        return Token(self.kind, self.text, pre_auxiliary)


# Map of all known keywords and symbols to their token kind.
# Used in the recognize_kw_sym function.
_kw_map = {
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
}
# Tuple of (kind, is_leaf). If is_leaf is false, we need to check the next character to determine the token.
_sym_map = {
    "==": (TokenKind.SYM_EQ, True),
    "!=": (TokenKind.SYM_NEQ, True),
    "<": (TokenKind.SYM_LT, False),
    "<=": (TokenKind.SYM_LEQ, True),
    ">": (TokenKind.SYM_GT, False),
    ">=": (TokenKind.SYM_GEQ, True),
    "+": (TokenKind.SYM_PLUS, True),
    "-": (TokenKind.SYM_MINUS, True),
    "*": (TokenKind.SYM_STAR, True),
    "/": (TokenKind.SYM_SLASH, True),
    "(": (TokenKind.SYM_LPAREN, True),
    ")": (TokenKind.SYM_RPAREN, True),
    "{": (TokenKind.SYM_LBRACE, True),
    "}": (TokenKind.SYM_RBRACE, True),
    ";": (TokenKind.SYM_SEMICOLON, True),
    "=": (TokenKind.SYM_ASSIGN, False),
    ",": (TokenKind.SYM_COMMA, True)
}
# The length of the longest symbol
_sym_longest = max(len(k) for k in _sym_map.keys())
# The length of the longest keyword
_kw_longest = max(len(k) for k in _kw_map.keys())


class _Tokenizer:
    """
    The tokenizer is responsible for converting a string of code into a sequence of tokens.
    It is the first step of the compilation process.

    This class is used internally for convenience of storing all relevant values in one place.
    The other files should just use the "tokenize" function :)
    """

    __slots__ = (
        "code",
        "eof",
        "tokens",
        "cursor",
        "err_start",
        "pending_auxiliary",
        "pending_problems",
        "no_pending_prob"
    )

    def __init__(self, code: str):
        self.code = code
        "The code to tokenize."

        self.eof = len(code) == 0
        "Whether we've reached the end of the file."

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

        self.err_start: Optional[int] = None
        """
        The starting position of the current "error", which is set when a character is not recognized at all.
        Set to None once we get a valid character (i.e. consumed by self.consume normally).

        This allows us to raise an error message for a sequence of invalid characters, instead of 
        spitting out an error message *per* invalid character.
        """

        self.pending_auxiliary: list[AuxiliaryText] = []
        """
        Auxiliary text that has been read, that will be put on the next pushed token.
        """

        self.pending_problems: list[_PendingTokenProblem] = []
        """
        Problems waiting to be added to the next token.
        """

        self.no_pending_prob = True
        """
        Whether pending_problems has zero elements.
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

        # If still have unrecognized error characters left, don't forget to report the error for those,
        # and add them to the auxiliary text of the last token.
        self.flush_unrecognized_error()
        self.push_token(TokenKind.EOF, "")
        return self.tokens

    def recognize_kw_sym(self) -> bool:
        """
        Recognizes a keyword (KW_XXX) or a symbol (SYM_XXX) in the code.
        If a keyword or a symbol is found, the corresponding token is added to the list of tokens.
        Returns true if a keyword or a symbol was recognized, false otherwise.
        """

        # First skip any unwanted whitespace
        self.consume_auxiliary()

        # Read a sequence of alphanumeric characters. Stop when we hit anything else (symbol/space)
        i = self.cursor
        l = 0
        while i < len(self.code) and self.code[i].isalnum():
            i += 1
            l += 1
            if l > _kw_longest:
                return False

        # Did we read at least one alphanumeric character?
        if i != self.cursor:
            w = self.code[self.cursor:i]
            # See if it matches a keyword
            m = _kw_map.get(w)
            if w in _kw_map:
                self.consume(l)
                self.push_token(m, w)
                return True
        else:
            # Not alphanumeric, perhaps it's a symbol?
            last_ok = None
            for i in range(1, _sym_longest):
                s = self.peek(i)
                m = _sym_map.get(s)
                if m:
                    kind, leaf = m
                    if leaf:
                        self.consume(i)
                        self.push_token(kind, s)
                        return True
                    else:
                        last_ok = kind, s

            if last_ok:
                kind, string_val = last_ok
                self.consume(len(string_val))
                self.push_token(kind, string_val)
                return True
            else:
                return False

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
                start_pos = self.cursor

                # First, let's read the "integer" part.
                integer_str = self.consume_regex(self.digits_regex)
                decimal_str = None

                # Tru to read the decimal part, if there is one.
                if self.consume_exact("."):
                    decimal_str = self.consume_regex(self.digits_regex)  # May be empty
                    if not decimal_str:  # Is it empty?
                        # That's a problem! We have a number missing its decimal digits, like "5."
                        # Instead of ignoring it though, we'll still consider it a "valid" number,
                        # just with a null decimal.
                        self.queue_problem(message="Partie décimale attendue après un point (« . »).",
                                           span=TextSpan(0, self.cursor - start_pos))
                        decimal_str = "0"

                # Make a number value: if it's an integer: int; if it's a decimal: float.
                val = int(integer_str) if decimal_str is None else float(f"{integer_str}.{decimal_str}")
                # Finally add the token to the list.
                self.push_token(TokenKind.LITERAL_NUM, self.code[start_pos:self.cursor], val)
                return True
            else:
                return False

        def bool_literal() -> bool:
            "Boolean literal recognition: true & false"

            # If it's true, then create a true token, else if it's false, create a false token. Simple enough!
            if self.consume_exact("true"):
                self.push_token(TokenKind.LITERAL_BOOL, "true", True)
                return True
            elif self.consume_exact("false"):
                self.push_token(TokenKind.LITERAL_BOOL, "false", False)
                return True
            else:
                return False

        def string_literal() -> bool:
            """String literal recognition:  "abc" """

            # Consume all characters into one "val" string until the next non-escaped quote
            start_pos = self.cursor
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
                            self.queue_problem(message=f"Caractère d'échappement inconnu : « \\{character} ».",
                                               span=TextSpan(self.cursor - start_pos - 2, self.cursor - start_pos))
                            # Ignore character
                        escape = False
                    # Onto the next character.
                    character = self.consume(1)

                if character == "":
                    # Then it's EOF! The string hasn't been closed properly. Report an error.
                    # TODO: Prevent this in some cases when detecting a newline after an escape character?
                    self.queue_problem(message="Chaîne de caractères non terminée.",
                                       span=TextSpan(self.cursor - start_pos - 1, self.cursor - start_pos))

                # Add the string token to the list.
                self.push_token(TokenKind.LITERAL_STRING, self.code[start_pos:self.cursor], val)
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
            self.push_token(TokenKind.IDENTIFIER, self.consume(n))
            return True
        else:
            return False

    def push_token(self, kind: TokenKind, text: str, value=None):
        """
        Pushes a token to the list of tokens.
        """
        if self.no_pending_prob:
            self.tokens.append(Token(kind, text, self.flush_auxiliary(), value=value))
        else:
            aux = self.flush_auxiliary()
            pb = self.flush_problems(aux)
            self.tokens.append(Token(kind, text, aux, pb, value))

    def flush_auxiliary(self):
        """
        Returns a tuple containing all pending auxiliary text, and clears the pending list.
        """
        t = tuple(self.pending_auxiliary)
        self.pending_auxiliary.clear()
        return t

    def flush_problems(self, auxiliary: tuple[AuxiliaryText, ...] = ()) -> tuple[TokenProblem, ...]:
        """
        Returns a tuple containing all pending problems, and clears the pending list.
        """
        problems = []
        for p in self.pending_problems:
            # Compute sums of all lengths before each auxiliary text
            auxiliary_start = [0]
            for a in auxiliary:
                auxiliary_start.append(auxiliary_start[-1] + len(a.text))

            # Calculate the span of the problem, by including auxiliary text.
            start = p.span.start if p.span else 0
            end = p.span.end if p.span else 0
            if p.text_space is None:
                span = TextSpan(auxiliary_start[len(auxiliary)] + start,
                                auxiliary_start[len(auxiliary)] + end)
            else:
                span = TextSpan(auxiliary_start[p.text_space] + start,
                                auxiliary_start[p.text_space] + end)
            problems.append(TokenProblem(p.message, p.severity, span))

        t = tuple(problems)
        self.pending_problems.clear()
        self.no_pending_prob = True
        return t

    def queue_problem(self, message: str, severity: ProblemSeverity = ProblemSeverity.ERROR,
                      span: TextSpan | None = None, text_space: int | None = None):
        """
        Queues a problem to be added to the next token.
        """
        self.pending_problems.append(_PendingTokenProblem(message, severity, span, text_space))
        self.no_pending_prob = False

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
            self.err_start = self.cursor
        elif not err and self.err_start is not None:
            # We're consuming a valid character! Get rid of the error marker.
            self.flush_unrecognized_error()

        # Store the substring to return; Update the cursor, and don't overshoot!
        substr = self.code[self.cursor:self.cursor + n]
        self.cursor = min(self.cursor + n, len(self.code))

        # Update the eof flag.
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

    until_nl_regex = re.compile(r"(.*)\n?")

    def consume_auxiliary(self):
        """
        Consumes all the whitespace characters until the next non-whitespace character,
        and comments (single-line only).

        Creates auxiliary text nodes for each whitespace/comment consumed.
        """
        i = self.cursor  # i is exclusive
        l = len(self.code)

        # Continue reading whitespace or comments until we read nothing.
        # Make sure the cursor isn't at the EOF.
        while i < l:
            very_start = i

            if self.code[i].isspace():
                # Consume all whitespace characters
                i += 1
                while i < l and self.code[i].isspace():
                    i += 1
                self.pending_auxiliary.append(AuxiliaryText(AuxiliaryKind.WHITESPACE, self.code[very_start:i]))

                if i < l and self.code[i] != "/":
                    break

            elif self.code[i:i + 2] == "//" and i < l:
                # We're in a comment! Consume all characters until the end of the line, including the newline.
                # We may have no newline at the end of file though.
                start = i
                i += 2
                m = self.until_nl_regex.match(self.code, i)
                i += len(m.group(0)) if m else 0
                self.pending_auxiliary.append(AuxiliaryText(AuxiliaryKind.SINGLE_LINE_COMMENT, self.code[start:i]))

            # If we've read nothing, exit the loop.
            if very_start == i:
                break

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
        Creates an auxiliary text node for the unrecognized characters.
        """
        if self.err_start is not None:
            chars = self.code[self.err_start:self.cursor]
            self.queue_problem(message=f"Séquence de caractères non reconnue : « {chars} ».",
                               text_space=len(self.pending_auxiliary),)
            self.pending_auxiliary.append(AuxiliaryText(AuxiliaryKind.INVALID, chars))
            self.err_start = None


def tokenize(code: str) -> list[Token]:
    """
    Tokenizes the given code into a sequence of tokens.
    Requires a ProblemSet to report any errors happening during tokenization.
    :param code: The code to tokenize.
    """
    return _Tokenizer(code).tokenize()
