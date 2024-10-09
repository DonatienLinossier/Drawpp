from collections import namedtuple


class FileCoordinates:
    """
    Represents a position in a file, with a line (y) and a column (x) number.
    """

    __slots__ = ("index", "line", "column")

    def __init__(self, index: int, line: int, column: int):
        self.index = index
        "The index of the character in the file, UTF-8 spanning more than one byte only use one index. Starts by 0."

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


class FileSpan(namedtuple("FileSpan", ["start", "end"])):
    """
        An inclusive interval of characters within a file. That's [start; end], but with chars.
    """
    __slots__ = ()
    def __str__(self):
        return f"[{self.start}; {self.end}]"
