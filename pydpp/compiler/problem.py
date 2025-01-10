from enum import Enum
from typing import Optional, TYPE_CHECKING

from pydpp.compiler.position import TextSpan

if TYPE_CHECKING:
    from pydpp.compiler.suggestion import Suggestion
    from pydpp.compiler.suggestion import Node

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


class ProblemCode(Enum):
    """
    A code associated with a particular type of problem.

    Not all problems have their own error code, it would be very annoying.
    Instead, they're used to mark up common error that can be fixed by an automated
    algorithm, or at least give some suggestions down the line.
    """

    MISSING_SEMICOLON = "missing_semicolon"
    "A semicolon is missing at the end of a statement."

    MISSING_LPAREN = "missing_lparen"
    "The left parenthesis is missing. (function def args)"

    MISSING_RPAREN = "missing_rparen"
    "The right parenthesis is missing. (parenthesized expr, function def args, function expr...)"

    MISSING_COMMA = "missing_comma"
    "A comma is missing between two arguments in a function expression, or between two parameters in a func def."

    MISSING_BLOCK = "missing_block"
    "A statement block is missing."

    MISSING_RBRACE = "missing_rbrace"
    "The right brace is missing on a statement block."

    UNDEFINED_VARIABLE = "undefined_variable"
    "Trying to use a variable that was not yet defined. (fetch/assign)"

    CANNOT_MUTATE_PARAMETER = "cannot_mutate_parameter"
    "Trying to change the value of a function parameter (which are immutable)."

    VAR_INIT_TYPE_MISMATCH = "var_init_type_mismatch"
    "The variable was initialized with a value of the wrong type."

    OTHER = "other"
    "A generic error code, used when no other code fits the problem."


class Problem:
    """
    Represents a problem during the entire compilation pipeline.
    Consists of a message, a severity, an error code, and an optional position value: where the problem occurred.
    Also registers the node and some suggestion to fix it.
    """

    __slots__ = ("message", "severity", "pos", "code", "node", "suggestion")

    def __init__(self, message: str,
                 severity: ProblemSeverity,
                 pos: Optional[TextSpan] = None,
                 code: ProblemCode = ProblemCode.OTHER,
                 node: Optional["Node"]=None,
                 suggestion: Optional["Suggestion"] = None):
        self.message = message
        "The message of the problem, localized to the user's language."
        self.severity = severity
        "The severity of the problem."
        self.pos = pos
        "Where exactly the problem occurred in the file, can be null (preferably not though)."
        self.code = code
        "The code associated with the problem."
        self.node = node
        "The AST node where the problem occurred, if any."
        self.suggestion = suggestion
        "A suggestion to fix the problem, if any."

    def __repr__(self):
        return f"Problem({self.message!r}, {self.severity!r}, {self.pos!r}, {self.code!r})"

    def __str__(self):
        title = f"{self.severity.value.capitalize()}: {self.message} (à {self.pos})"
        if self.suggestion is not None:
            assert self.node is not None
            preview = self.suggestion.preview(self.node)
            if preview is not None:
                title += f"\nSuggestion : {self.suggestion.title}\n{preview}"
        return title


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
        self.problems: list[Problem] = []
        "The list of problems. (Don't append to it directly, use the append function!)"

        self.grouped = {e: [] for e in ProblemSeverity}
        "All problems grouped by their severity. (Don't edit it directly, use the append function!)"

    def append(self,
               problem: Problem | str,
               severity: ProblemSeverity = ProblemSeverity.ERROR,
               pos: Optional[TextSpan] = None,
               code: ProblemCode = ProblemCode.OTHER,
               node: Optional["Node"] = None,
               suggestion: Optional["Suggestion"] = None):
        """
        Adds a problem to the list. Each problem has a message, a severity, and a position.

        This function can be called in two ways:

        - append(Problem(...)): adds the problem directly.
        - append("message", severity, pos): adds a problem with the given message, severity, and position
                                            (severity is ERROR by default, and pos is None by default).
        """

        # When we're given a string inside the first argument, we need to construct a new Problem.
        if isinstance(problem, str):
            problem = Problem(problem, severity, pos, code, node, suggestion)

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
        # print("Summary:", " | ".join([f"{k.name}: {len(v)}" for k, v in self.grouped.items()]))
        return "\n".join([str(x) for x in self.problems])

    def __repr__(self):
        return repr(self.problems)
