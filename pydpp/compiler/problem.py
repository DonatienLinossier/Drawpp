from enum import Enum
from typing import Optional

from pydpp.compiler.position import FileSpan


class ProblemSeverity(Enum):
    """
    The importance and relevance of a problem.
    Ordered from least to most severe: Notice, Warning, Error.
    """
    NOTICE = "notice"
    "A message to the user that doesn't pinpoint any issue in the code, but might require their attention nonetheless."

    WARNING = "warning"
    "An issue that might cause some problems during execution, but doesn't prevent compilation."

    ERROR = "error"
    "A critical issue that prevents the code from being compiled."


class Problem:
    """
    Represents a problem during the entire compilation pipeline.
    Consists of a message, a severity and an optional position value: where the problem occurred.
    """

    __slots__ = ("message", "severity", "pos")

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
        return f"{self.severity.value.capitalize()}: {self.message} (à {self.pos})"


class ProblemSet:
    """
    Basically a list of problems, which can grow in size while processing code in the pipeline.

    This object is meant to be passed to each step of the pipeline, so we can aggregate all problems
    each step finds, even if there are errors during the process! For example, the tokenizer might find an error,
    but that doesn't prevent the parser from finding more of them.

    At the end of the pipeline, this will contain all problems found during the compilation process,
    which should all be displayed to the user on the IDE. The IDE will be able to use this class to do so.

    Contains lists of problem for each severity (``ProblemSeverity``) in the ``grouped`` attribute, which can be
    useful to get all warnings, all errors...

    Can be used as if it was a list of problems! You can use for/len/in etc. on it.
    For example, the following code works: ::

        ps = ProblemSet()
        add_tons_of_errors(ps)
        for problem in ps:
            print(problem)
    """

    __slots__ = ("problems", "grouped")

    def __init__(self):
        self.problems = []
        "The list of problems. (Don't append to it directly, use the append function!)"

        self.grouped = {e: [] for e in ProblemSeverity}
        "All problems grouped by their severity. (Don't edit it directly, use the append function!)"

    def append(self,
               problem: Problem | str,
               severity: ProblemSeverity = ProblemSeverity.ERROR,
               pos: Optional[FileSpan] = None):
        """
        Adds a problem to the list. Each problem has a message, a severity, and a position.

        This function can be called in two ways:

        - append(Problem(...)): adds the problem directly.
        - append("message", severity, pos): adds a problem with the given message, severity, and position
                                            (severity is ERROR by default, and pos is None by default).
        """

        # When we're given a string inside the first argument, we need to construct a new Problem.
        if isinstance(problem, str):
            problem = Problem(problem, severity, pos)

        # Add the problem to the list and to the grouped dictionary.
        self.problems.append(problem)
        self.grouped[problem.severity].append(problem)

    def __iter__(self):
        return iter(self.problems)

    def __len__(self):
        return len(self.problems)

    def __contains__(self, item):
        return item in self.problems

    def __str__(self):
        # Print a simple summary of all problems in the set.
        print("Summary:", " | ".join([f"{k.name}: {len(v)}" for k, v in self.grouped.items()]))
        return "\n".join([str(x) for x in self.problems])

    def __repr__(self):
        return repr(self.problems)
