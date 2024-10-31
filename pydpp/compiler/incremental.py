# =============================================================================
# incremental.py: Handful functions for incremental parsing logic
# =============================================================================
from collections.abc import Callable
from lib2to3.btm_utils import tokens
from typing import NamedTuple

from pydpp.compiler import tokenize, ProblemSet, Problem
from pydpp.compiler.position import TextSpan
from pydpp.compiler.syntax import Program
from pydpp.compiler.tokenizer import Token, TokenKind


class IncrementalTokenization(NamedTuple):
    """
    The result of an incremental tokenization operation.
    """
    replacement_span: TextSpan
    replacement_indices: tuple[int, int]
    "Inclusive interval of token indices that were replaced in the list."
    tokens: list[Token]
    problems: list[Problem]

    def __repr__(self):
        nicely_formatted = '[\n        ' + ",\n        ".join([str(t) for t in self.tokens]) + '\n    ]'
        return f"IncrementalTokenization(\n    replacement_span={self.replacement_span},\n    replacement_indices={self.replacement_indices},\n    tokens={nicely_formatted},\n    problems={self.problems}\n)"

def tokenize_incremental(token_src: list[Token] | Program,
                         delete_interval: TextSpan,
                         replacement: str) -> IncrementalTokenization | None:
    if not isinstance(token_src, list):
        raise NotImplementedError("not yet!")

    # Handling "greedy" tokens (strings and comments) will induce a lot of complexity,
    # so we'll give up on them for now.
    if '"' in replacement or '//' in replacement:
        return None # panic?

    text_idx = 0
    start_tkn = None
    start_tkn_idx = None
    start_tkn_text_idx = None
    end_tkn = None
    end_tkn_idx = None
    end_tkn_text_idx = None

    for i in range(len(token_src)):
        start = text_idx
        l = len(token_src[i].full_text)
        end = start + l

        # Right now, text_idx refers to the index of the first char of the token (including auxiliary text).
        if end >= delete_interval.start and not start_tkn_idx:
            start_tkn = token_src[i]
            start_tkn_idx = i
            start_tkn_text_idx = start

        text_idx += l

        # Now, text_idx refers to the index of the LAST char of the token + 1 (as it is an exclusive bound).
        if end >= delete_interval.end:
            end_tkn = token_src[i]
            end_tkn_idx = i
            end_tkn_text_idx = start
            break

    if start_tkn_idx is None or end_tkn_idx is None:
        raise ValueError("Interval not found in token list.")

    # Example:
    # if my_var or true {}
    #      ----------
    #        del_ivl
    #
    # With replacement="hello", we should get:
    # if myhelloue {}
    #
    # First token: my_var
    # Last token: true
    #
    # We're going to process the spanned tokens and its surroundings, so:
    # tokens_to_rescan = [if, my_var, or, true, {]

    text_to_reparse = ""
    if start_tkn_idx > 0:
        text = token_src[start_tkn_idx - 1].full_text
        text_to_reparse += text
        rescan_start_text_idx = start_tkn_text_idx - len(text)
        rescan_start_tkn_idx = start_tkn_idx - 1
    else:
        rescan_start_text_idx = start_tkn_text_idx
        rescan_start_tkn_idx = start_tkn_idx

    start_tkn_max_char = delete_interval.start - start_tkn_text_idx
    end_tkn_min_char = delete_interval.end - end_tkn_text_idx

    # Give up if we're cutting through a string literal, making it incomplete.
    if start_tkn_idx == end_tkn_idx and start_tkn.kind == TokenKind.LITERAL_STRING:
        # Inside a string, maybe we're just inside its quotes?
        ws = sum(len(x.text) for x in start_tkn.pre_auxiliary)
        # ok if: start_tkn_max_char >= ws + 1 and end_tkn_min_char < len(start_tkn.full_text)
        if start_tkn_max_char < ws + 1 or end_tkn_min_char >= len(start_tkn.full_text):
            return None
    elif ((start_tkn.kind == TokenKind.LITERAL_STRING and start_tkn_max_char < len(start_tkn.full_text)+1) or
            (end_tkn.kind == TokenKind.LITERAL_STRING and end_tkn_min_char > 0)):
        return None

    text_to_reparse += start_tkn.full_text[:start_tkn_max_char]
    text_to_reparse += replacement
    text_to_reparse += end_tkn.full_text[end_tkn_min_char:]

    if end_tkn_idx < len(token_src) - 1:
        text = token_src[end_tkn_idx + 1].full_text
        text_to_reparse += text
        rescan_end_text_idx = end_tkn_text_idx + len(text)
        rescan_end_tkn_idx = end_tkn_idx + 1
    else:
        rescan_end_text_idx = end_tkn_text_idx
        rescan_end_tkn_idx = end_tkn_idx

    print("Text to reparse:", text_to_reparse.strip())
    print("Start token idx:", rescan_start_tkn_idx)
    print("End token idx:", rescan_end_tkn_idx)

    ps = ProblemSet()
    tkns = tokenize(text_to_reparse, ps)
    if end_tkn_idx != len(token_src) - 1:
        # The last token is the EOF token produced by the tokenizer, we need to get rid of it.
        tkns.pop()

    # print("Tokens to rescan:", tokens_to_rescan)
    # print("Text to reparse:", text_to_reparse)

    for p in ps.problems:
        p.pos = TextSpan(p.pos.start + rescan_start_text_idx, p.pos.end + rescan_start_text_idx)

    return IncrementalTokenization(
        replacement_span=TextSpan(rescan_start_text_idx, rescan_end_text_idx),
        replacement_indices=(rescan_start_tkn_idx, rescan_end_tkn_idx),
        tokens=tkns,
        problems=ps.problems
    )