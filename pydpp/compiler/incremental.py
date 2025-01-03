# =============================================================================
# incremental.py: Handful functions for incremental parsing logic
# =============================================================================
import typing
from typing import NamedTuple

from pydpp.compiler import tokenize, ProblemSet, Problem
from pydpp.compiler.parser import _Parser
from pydpp.compiler.position import TextSpan
from pydpp.compiler.syntax import Program, Node, LeafNode, Statement, InnerNode, BlockStmt
from pydpp.compiler.tokenizer import Token, TokenKind


class IncrementalTokenization(NamedTuple):
    """
    The result of an incremental tokenization operation.
    """
    replacement_span: TextSpan
    replacement_indices: tuple[int, int]
    "Inclusive interval of token indices that were replaced in the list."
    tokens: list[Token]

    def __repr__(self):
        nicely_formatted = '[\n        ' + ",\n        ".join([str(t) for t in self.tokens]) + '\n    ]'
        return f"IncrementalTokenization(\n    replacement_span={self.replacement_span},\n    replacement_indices={self.replacement_indices},\n    tokens={nicely_formatted}\n)"

class IncrementalTokenization2(NamedTuple):
    """
    The result of an incremental tokenization operation (2nd edition).
    """
    node_to_replace: Node
    tokens: list[Token]

    def __repr__(self):
        nicely_formatted = '[\n        ' + ",\n        ".join([str(t) for t in self.tokens]) + '\n    ]'
        return f"IncrementalTokenization2(\n    node_to_replace={self.node_to_replace!r},\n    tokens={nicely_formatted}\n)"

def _collect_tokens(n: Node, l: list[Token]):
    if isinstance(n, LeafNode):
        l.append(n.token)
    else:
        for c in n.children:
            _collect_tokens(c, l)

    return l

def tokenize_incremental_list(token_src: list[Token],
                              delete_interval: TextSpan,
                              replacement: str) -> IncrementalTokenization | None:
    # Handling "greedy" tokens (strings and comments) will induce a lot of complexity,
    # so we'll give up on them for now.
    if '"' in replacement or '//' in replacement:
        return None  # panic?

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
    elif ((start_tkn.kind == TokenKind.LITERAL_STRING and start_tkn_max_char < len(start_tkn.full_text) + 1) or
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

    # print("Text to reparse:", text_to_reparse.strip())
    # print("Start token idx:", rescan_start_tkn_idx)
    # print("End token idx:", rescan_end_tkn_idx)

    tkns = tokenize(text_to_reparse)
    if end_tkn_idx != len(token_src) - 1:
        # The last token is the EOF token produced by the tokenizer, we need to get rid of it.
        tkns.pop()

    # print("Tokens to rescan:", tokens_to_rescan)
    # print("Text to reparse:", text_to_reparse)
    return IncrementalTokenization(
        replacement_span=TextSpan(rescan_start_text_idx, rescan_end_text_idx),
        replacement_indices=(rescan_start_tkn_idx, rescan_end_tkn_idx),
        tokens=tkns
    )


def tokenize_incremental_tree(token_src: Program,
                              delete_interval: TextSpan,
                              replacement: str) -> IncrementalTokenization2 | None:
    # Handling "greedy" tokens (strings and comments) will induce a lot of complexity,
    # so we'll give up on them for now.
    if '"' in replacement or '//' in replacement:
        return None  # panic?

    # if last := token_src.statements[-1]:
    #     _ = last.full_span_start

    def binary_search(inner_nodes: list[InnerNode]):
        prev_i = -1
        i = len(inner_nodes) // 2
        start = 0
        end = len(inner_nodes) - 1
        while prev_i != i:
            if c := find_containing(inner_nodes[i]):
                return c
            elif inner_nodes[i].full_span_start > delete_interval.start:
                # We're too far ahead, go back
                end = i
            else:  # nodes[i].full_span_start < delete_interval.start
                # We're too far behind, go forward
                start = i

            prev_i = i
            i = (start + end) // 2
        return None

    def find_containing(n: Node):
        if delete_interval in n.full_span:
            cin = n.child_inner_nodes
            if isinstance(cin, list) and len(cin) >= 16:
                if cont := binary_search(cin):
                    return cont
            else:
                for c in cin:
                    if cont := find_containing(c):
                        return cont

            return n
        else:
            return None

    def first_token(n: Node):
        if isinstance(n, LeafNode):
            return n
        else:
            return first_token(next(iter(n.children)))

    def last_token(n: Node):
        if isinstance(n, LeafNode):
            return n
        else:
            return last_token(next(iter(n.children_reverse)))

    container = find_containing(token_src)
    if container is None or container is token_src:
        return None

    while (container.parent is not None and
           (first_token(container).full_span.intersection(delete_interval) is not None
            or last_token(container).full_span.intersection(delete_interval) is not None)):
        container = container.parent

    tokens = _collect_tokens(container, [])
    new_interval = TextSpan(delete_interval.start - container.full_span_start, delete_interval.end - container.full_span_start)
    inc = tokenize_incremental_list(tokens, new_interval, replacement)
    tokens[inc.replacement_indices[0]: inc.replacement_indices[1] + 1] = inc.tokens
    return IncrementalTokenization2(container, tokens)

def parse_incremental(tree: Program, tokenization: IncrementalTokenization2) -> bool:
    stmt = tokenization.node_to_replace

    while (not isinstance(stmt, Statement)
           and stmt.parent is not None
           and not stmt.parent_slot.multi):
        stmt = stmt.parent

    if stmt is tree:
        return False

    stmt = typing.cast(Statement, stmt)

    stmt_par = stmt.parent
    stmt_slot = stmt.parent_slot
    stmt_list = typing.cast(list[Statement], stmt.parent.get(stmt.parent_slot))
    idx = stmt_list.index(stmt)

    min_idx = idx

    while min_idx > 0 and stmt_list[min_idx - 1].has_problems:
        min_idx -= 1

    tokens = []
    for i in range(min_idx, idx):
        tokens.extend(_collect_tokens(stmt_list[i], []))

    tokens.extend(tokenization.tokens)
    tokens.append(Token(TokenKind.EOF, ""))

    p = _Parser(tokens)

    new_statements = []
    while s := p.parse_statement():
        new_statements.append(s)

    if not p.eof:
        return False

    old_statements = stmt_list[min_idx:idx+1]
    for s in old_statements:
        s.detach_self()

    for s in new_statements:
        stmt_par.attach_child(stmt_slot, s, idx)

    return True

