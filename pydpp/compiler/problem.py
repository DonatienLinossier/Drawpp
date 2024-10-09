from enum import Enum
from typing import Optional

from pydpp.compiler.position import FileSpan

class ProblemSeverity(Enum):
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"

class Problem:
    """
    Represents a problem during the entire compilation pipeline.
    Consists of a message, a severity and an optional position value: where the problem occurred.
    """
    def __init__(self, message: str, severity: ProblemSeverity, pos: Optional[FileSpan] = None):
        self.message = message
        "The message of the problem, localized to the user's language."
        self.severity = severity
        "The severity of the problem."
        self.pos = pos
        "Where exactly the problem occurred in the file, can be null (preferably not though)."

    def __repr__(self):
        return f"Problem({self.message!r}, {self.severity!r}, {self.pos!r})"

    def __str__(self):
        return f"{self.severity.value.capitalize()}: {self.message}"

class ProblemSet:
    """
    Basically a list of problems, which can grow during the pipeline.
    Can be used as if it was a list of problems! You can use for/len/in etc. on it.
    """
    def __init__(self):
        self.problems = []
        "The list of problems."
        self.grouped = { e:[] for e in ProblemSeverity }
        "True when the problem set has at least one error."

    def append(self, problem: Problem | str, severity: ProblemSeverity = ProblemSeverity.ERROR, pos: Optional[FileSpan] = None):
        """
        Adds a problem to the list. Can be called in two ways:

        - append(Problem(...)): adds the problem directly.
        - append("message", severity, pos): creates a problem with the given parameters and adds it, ERROR by default.
        """

        if isinstance(problem, str):
            problem = Problem(problem, severity, pos)

        self.problems.append(problem)
        self.grouped[problem.severity].append(problem)

    def __iter__(self):
        return iter(self.problems)

    def __len__(self):
        return len(self.problems)

    def __contains__(self, item):
        return item in self.problems

    def __str__(self):
        print("Summary:", " | ".join([ f"{k.name}: {len(v)}" for k,v  in self.grouped.items() ]))
        return "\n".join([str(x) for x in self.problems])

    def __repr__(self):
        return repr(self.problems)