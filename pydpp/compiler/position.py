import typing


class FileCoordinates:
    """
    Represents a position in a file: with an index value,
    and a pair of x/y coordinates: line (y) and column (x).

    The line and columns start by one, and use the newline character to count lines.
    Example:
        sacrilège           <- line 1 | index at column 1: index 0
        pouet               <- line 2 | index at column 1: index 10
        j'ai faim           <- line 3 | index at column 1: index 16
    """

    __slots__ = ("index", "line", "column")

    def __init__(self, index: int, line: int, column: int):
        self.index = index
        "The index of the character in the entire file, UTF-8 spanning more than one byte only use one index. Starts by 0."

        self.line = line
        "The line (y) number in the file. Starts by 1."

        self.column = column
        "The column (x) number in the file. Starts by 1. UTF-8 characters spanning more than one byte only use one column."

    def __eq__(self, other):
        return self.index == other.index and self.line == other.line and self.column == other.column

    def __repr__(self):
        return f"FileCoordinates({self.index}, {self.line}, {self.column})"

    def __str__(self):
        return f"{self.line}:{self.column}"


class FileSpan(typing.NamedTuple):
    """
        An interval of characters within a file. That's [start; end[, but with characters instead.
        Example: (the string starts with the first letter "s", no whitespace)
            soirée-champagne
                   _________
                     span

            span = FileSpan(
                start = FileCoordinates(7, 1, 8),
                end = FileCoordinates(16, 1, 17)
            )
            str(span) -> [1:8; 1:17]
    """
    start: FileCoordinates
    "The start of the interval (inclusive!)."

    end: FileCoordinates
    "The end of the interval (exclusive!)."

    def __str__(self):
        return f"[{self.start}; {self.end}]"

    def __repr__(self):
        return f"FileSpan({self.start}, {self.end})"
