import typing
from typing import Union

class TextSpan(typing.NamedTuple):
    """
    A span of text, using a pair of indices.

    Example: (the string starts with the first letter "s", no whitespace) ::

            soirée-champagne
                   _________
                     span

            span = TextSpan(7, 16)
            str(span) -> [7; 16[
    """

    start: int
    "The start of the interval (inclusive!)."

    end: int
    "The end of the interval (exclusive!)."

    def intersection(self, other: "TextSpan") -> typing.Optional["TextSpan"]:
        """
        Returns the intersection of two spans. Returns None when spans are disjoint.
        """

        span = TextSpan(
            max(self.start, other.start),
            min(self.end, other.end)
        )

        if span.start < span.end:
            return span
        else:
            return None

    def __str__(self):
        return f"[{self.start}; {self.end}["

    def __repr__(self):
        return f"TextSpan({self.start}, {self.end})"

    def __contains__(self, item: Union["TextSpan", int]):
        if isinstance(item, TextSpan):
            return self.start <= item.start and item.end <= self.end
        else:
            assert isinstance(item, int), "Must be TextSpan or int"
            return self.start <= item < self.end

    def __eq__(self, other):
        assert isinstance(other, TextSpan)
        return self.start == other.start and self.end == other.end