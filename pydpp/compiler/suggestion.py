import copy
import typing
from collections.abc import Callable
from typing import TypeVar

from pydpp.compiler.problem import ProblemCode
from pydpp.compiler.syntax import Node, InnerNodeProblem, TokenProblem, leaf, InnerNode
from pydpp.compiler.tokenizer import Token, TokenKind

class SuggestionPreview(typing.NamedTuple):
    replacement: str
    start: int
    end: int
    includes_auxiliary: bool

    def __str__(self):
        s = self.replacement + "\n"
        for i in range(self.end):
            if i >= self.start:
                s += "^"
            else:
                s += " "
        return s

class Suggestion(typing.NamedTuple):
    title: str
    problem: InnerNodeProblem | TokenProblem
    func: Callable[[Node], bool]

    def preview(self, node: Node) -> SuggestionPreview | None:
        c = copy_node(node)
        if self.apply(c):
            return calc_preview(node, c)
        else:
            return None

    def apply(self, node: Node) -> bool:
        return self.func(node)

def gather_suggestions(root: Node) -> dict[Node, list[Suggestion]]:
    suggestions = {}

    def gather(n: Node):
        if n.has_problems:
            probs = []
            for p in n.problems:
                s = find_suggestion(n, p)
                if s is not None:
                    probs.append(s)

            if probs:
                suggestions[n] = probs

            for c in n.children:
                gather(c)

    gather(root)
    return suggestions

def find_suggestion(node: Node, problem: InnerNodeProblem | TokenProblem) -> Suggestion | None:
    match problem.code:
        case ProblemCode.MISSING_SEMICOLON:
            def apply(n: Node):
                assert isinstance(n, InnerNode)
                n.semi_colon = leaf(Token(TokenKind.SYM_SEMICOLON, ';'))
                n.with_problems(*filter(lambda p: p.code != ProblemCode.MISSING_SEMICOLON, n.problems))
                return True
            return Suggestion("Ajouter un point-virgule", problem, apply)

    return None

def calc_preview(prev_node: Node, fixed_node: Node) -> SuggestionPreview:
    # See if we have any whitespace/comments changes
    exclude_auxiliary = prev_node.pre_auxiliary == fixed_node.pre_auxiliary
    if exclude_auxiliary:
        # No whitespace changes, use the text
        prev_text = prev_node.text
        fixed_text = fixed_node.text
    else:
        # We have some comment/whitespace changes, include those too.
        prev_text = prev_node.full_text
        fixed_text = fixed_node.full_text

    prefix, suffix = prefix_suffix(prev_text, fixed_text)

    return SuggestionPreview(fixed_text, prefix, len(fixed_text) - suffix, not exclude_auxiliary)

T = TypeVar('T', bound=Node)
def copy_node(node: T) -> T:
    # Make a deep copy of a node and invalidate its parent-related caches (currently, the full_span_start)
    # Also detach it from its parent, it's the new root!
    copied = copy.deepcopy(node)
    copied._cached_fss = None
    copied.register_detachment()

    def invalidate_caches(n: Node):
        n._cached_fss = None
        for c in n.children:
            if c._cached_fss is None:
                break
            invalidate_caches(c)

    invalidate_caches(copied)

    return copied

def prefix_suffix(a, b):
    prefix = 0
    for i in range(min(len(a), len(b))):
        if a[i] == b[i]:
            prefix += 1

    suffix = 0
    for i in range(min(len(a), len(b))):
        if a[-i-1] == b[-i-1]:
            suffix += 1

    return prefix, suffix