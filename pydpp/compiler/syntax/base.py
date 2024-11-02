import typing
from enum import Enum
from typing import Optional, Iterable, TypeVar, Any, Union, Generic, Literal
import sys

from pydpp.compiler.problem import ProblemSeverity
from pydpp.compiler.position import TextSpan

if sys.version_info[1] <= 10:
    # Run pip install typing-extensions for running on PyPy 3.10
    from typing_extensions import Self
else:
    from typing import Self

from pydpp.compiler.tokenizer import Token, TokenKind, AuxiliaryText
from pydpp.compiler.types import BuiltInTypeKind

# ===========================================
# syntax.py: Syntax Tree for the language
# ===========================================
# Notes & stuff to improve
# - Being able to edit the node tree and provide suggestions/refactorings
#   Currently trees don't store token info so we can't edit a tree to edit a file.
#   We could edit the children function to return both tokens and children
#   So we can have _children(nodes=True, tokens=False) and have many properties
#            - child_nodes = _children(nodes=True, tokens=False)
#            - child_tokens = _children(nodes=False, tokens=True)
#            - children = _children(nodes=True, tokens=True)
#
# - Add "parent" attributes to nodes, which is much more practical for navigating the tree.
#   That's tricky to implement if we like our nodes to be immutable, or we could settle with mutability...
#   Nothing's impossible though! Check how Roslyn does it: https://ericlippert.com/2012/06/08/red-green-trees/
#   We can also get inspiration from JavaScript's DOM API, this one's mutable and easy to use.

Element = Union["Node", Token]
E = TypeVar("E", bound="Element")
P = TypeVar("P", bound="Node")


class NodeSlot(Generic[P, E]):
    """
    Describes a slot containing children elements (nodes or tokens) in a node.

    Slots come in two variants: Single ([0; 1]) and Multi ([0; N]).
    """
    __slots__ = ("attr", "name", "token", "el_type", "check_func", "optional")
    multi: bool

    def __init__(self, attr_: str, el_type: typing.Type[E],
                 check_func: typing.Callable[[E], bool] | None = None,
                 optional: bool = True):
        # TODO: Optional support
        self.attr = attr_
        "The attribute name in the node containing the raw slot data (node or list of nodes)"
        self.name = attr_.lstrip('_')
        self.token = el_type == Token
        self.el_type = el_type
        self.check_func = check_func
        self.optional = optional

    def accepts(self, el: Element):
        return isinstance(el, self.el_type) and (self.check_func is None or self.check_func(el))

    def __repr__(self):
        return f"{type(self).__name__}({self.attr!r})"


class SingleNodeSlot(NodeSlot[P, E]):
    multi: Literal[False] = False


class MultiNodeSlot(NodeSlot[P, E]):
    multi: Literal[True] = True


T = TypeVar("T")

class NodeProblem:
    """
    An issue related to a node during parsing, or semantic analysis.
    """
    __slots__ = ("message", "severity", "slot")

    def __init__(self, message: str,
                 severity: ProblemSeverity = ProblemSeverity.ERROR,
                 slot: NodeSlot["Node", Element] | None = None):
        self.message = message
        self.severity = severity
        self.slot = slot
        """
        On which slot the problem is located. 
        If the slot is specified, the problem spans the text of the slot.
        If not slot is specified, the problem spans the entire node.
        If the slot is empty, the problems spans a 0-length node on the left of the slot.
        """

    def compute_span(self, node: "Node") -> TextSpan:
        # TODO: Optimize with a span cache

        if self.slot is None:
            return node.span

        assert hasattr(node, self.slot.attr)

        node_start = node.full_span_start
        inner_start = 0
        for s in node.element_slots:
            if s == self.slot:
                break
            if s.multi:
                inner_start += sum(len(x.full_text) for x in getattr(node, s.attr))
            else:
                el = getattr(node, s.attr)
                if el is not None:
                    inner_start += len(el.full_text)

        slot_value = node.get(self.slot)
        first_child = (slot_value[0] if slot_value else None) if self.slot.multi else slot_value
        inner_end = inner_start + (len(first_child.full_text) if first_child is not None else 0)

        return TextSpan(node_start + inner_start, node_start + inner_end)

    def __repr__(self):
        return f"NodeProblem({self.message!r}, {self.severity!r})"


class Node:
    """
    A node in the syntax tree. Represents a whole recognized element in the source code, which may
    have children nodes.

    Nodes usually fall into either of these categories:
        - statements  (variable declarations, if/else blocks, while loops, etc.)
        - expressions (number/string literals, arithmetic and logic operations, variables, function calls, etc.)

    Few nodes don't fit into either of them, such as:
        - built-in types (int, float, string, bool)
        - identifiers (function names, variable names)
        - the root node (Program, covering the entire file)

    Children nodes can be queried by using the ``children`` property: just do ``node.children``.

    Each node knows its position in the source code, crucial for error reporting!

    =========================
    A PRIMER TO SYNTAX TREES
    =========================

    What do we mean exactly by "syntax tree"?

    Simply put, the entire program is represented by a **hierarchy** of Nodes: the statements (the instructions
    and definitions) contain expressions, values evaluated to produce an output, which may in turn
    contain expressions! For instance, 5+7 is an expression containing two expressions (5 and 7).

    Since **Nodes can contain other Nodes**, and we have a **root Node (the Program)** we consider this
    to be a **syntax tree**.

    Here's a simple example. Consider the following program in Draw++: ::

        int a = 25 + 75;
        int b = a * 2;

    How would that program be represented as a syntax tree? Let's take a look using Python's object syntax. ::

        Program(
            statements = [
                VariableDeclaration(
                    type  = IntType,
                    name  = Identifier('a'),
                    value = AddExpression(
                        left = NumberLiteral(25),
                        right = NumberLiteral(75)
                    )
                ),
                VariableDeclaration(
                    type  = IntType,
                    name  = Identifier('b'),
                    value = MultiplyExpression(
                        left = VariableExpression('a'),
                        right = NumberLiteral(2)
                    )
                )
            ]
        )

    Here, the root node is Program, with **two children**:
        - the first variable declaration (``int a = 25 + 75;``)
        - the second variable declaration (``int b = a * 2;``)

    Each variable declaration has one child: their value (next to the =).

    For the first declaration, ``25 + 75`` is an AddExpression, with two children:
        - the number literal 25
        - the number literal 75

    Then, ``a * 2`` is a MultiplyExpression, with two children:
        - the variable expression 'a'
        - the number literal 2

    We can effectively visualize this as an (ASCII) tree: ::

        Program
        ├── VariableDeclaration (statements)
        │   ├── IntType (type)
        │   ├── Identifier('a') (identifier)
        │   └── AddExpression (value)
        │       ├── NumberLiteral(25) (left)
        │       └── NumberLiteral(75) (right)
        └── VariableDeclaration (statements)
            ├── IntType (type)
            └── MultiplyExpression (value)
                ├── VariableExpression('a') (left)
                └── NumberLiteral(2) (right)

    Notice how each children knows which "slot" it belongs to in the parent. That's why it's so
    different from your usual tree, which doesn't care about *why* children are there in the first place.
    """

    __slots__ = ("semantic_info", "_cached_text", "parent", "parent_slot", "problems", "has_problems")

    element_slots: tuple[NodeSlot[Self, Element], ...] = ()
    node_slots: tuple[NodeSlot[Self, "Node"], ...] = ()

    def __init__(self):
        self.semantic_info: Any = None
        """
        The semantic information of the node, mainly containing info about types.

        This attribute is None when the semantic analysis hasn't been done on this node, 
        or when this node doesn't need that.

        For now, it's can be anything, we haven't decided on what it should be yet.
        """

        self._cached_text: str | None = None

        self.parent: Node | None = None
        "The parent node of this node. None if this node is the root node or not attached yet."
        self.parent_slot: NodeSlot[Node, Node] | None = None
        "The slot in the parent node where this node is attached. None if this node is the root node or not attached yet."

        self.problems: tuple[NodeProblem, ...] = ()
        "A list of all problems related to this node."

        self.has_problems = False
        """
        Whether this node or any of its children have problems. 
        Defined by: len(self.problems) > 0 OR any(n for n in self.children if n.has_problems)
        """

    # =========================
    # CHILDREN QUERYING
    # =========================

    @property
    def children(self) -> Iterable[Element]:
        """
        Returns all children elements of this node: tokens and nodes.
        """
        for s in self.element_slots:
            v = getattr(self, s.attr)
            if s.multi:
                yield from v
            else:
                if v is not None:
                    yield v

    @property
    def child_nodes(self) -> Iterable["Node"]:
        """
        Returns all children nodes of this node. Only returns nodes, not tokens!
        """
        for s in self.node_slots:
            v = getattr(self, s.attr)
            if s.multi:
                yield from v
            else:
                if v is not None:
                    yield v

    @property
    def children_with_slots(self) -> Iterable[tuple[Element, NodeSlot["Node", Element]]]:
        """
        Returns all children elements of this node, along with their slots.
        """
        for s in self.element_slots:
            v = getattr(self, s.attr)
            if s.multi:
                for el in v:
                    yield el, s
            else:
                if v is not None:
                    yield v, s

    def child_node_at(self, idx: int):
        """
        Returns the child node at the given index.
        :param idx: the index of the child node
        :return: the child node
        """
        for i, n in enumerate(self.child_nodes):
            if i == idx:
                return n
        return None

    # =========================
    # COMPUTED PROPS (TEXT, POSITION, AUXILIARY)
    # =========================

    @property
    def full_text(self) -> str:
        """
        Returns the full text representation of this node, including preceding auxiliary text.
        """

        if self._cached_text is None:
            # Calculate recursively the full text of all children.
            # Tokens also have a full_text attribute, which is contains all text, including auxiliary text.
            self._cached_text = "".join(x.full_text for x in self.children if x is not None)

        return self._cached_text

    @property
    def text(self) -> str:
        """
        Returns the text representation of this node, without any auxiliary text.
        """

        # TODO: Maybe cache this in the future? It isn't very costly to calculate though...

        # Take the full text representation, and use the first token of the node
        # to remove the preceding auxiliary text
        ft = self.full_text
        return ft[self._pre_auxiliary_length():]

    @property
    def parent_slot_idx(self) -> int | None:
        if self.parent_slot is None or not self.parent_slot.multi:
            return None
        else:
            return self.parent.get(self.parent_slot).index(self)

    @property
    def full_span_start(self) -> int:
        """
        Returns the index of the first character of this node, including auxiliary text.
        """
        # The goal here is to find all left siblings of this node, and add all their length.
        pre_len = 0
        par = self.parent
        # The node which contains this node, which we need to "stop" at.
        excluded = self
        while par is not None:
            for c in par.children:
                if c is excluded:  # "is" so we don't get an error with token equality.
                    break
                pre_len += len(c.full_text)
            excluded = par
            par = par.parent

        return pre_len

    @property
    def span_start(self) -> int:
        """
        Returns the index of the first character of this node, excluding auxiliary text.
        """
        return self.full_span_start + self._pre_auxiliary_length()

    @property
    def span(self) -> TextSpan:
        """
        Returns the span of characters covered by this node, excluding auxiliary text.
        Cost of this property ramps up the deeper the node is, so be mindful!
        """
        s = self.full_span_start
        return TextSpan(s, s + len(self.full_text))

    @property
    def full_span(self) -> TextSpan:
        """
        Returns the full span of characters covered by this node, including auxiliary text.
        Cost of this property ramps up the deeper the node is, so be mindful!
        """
        s = self.span_start
        return TextSpan(s, s + len(self.full_text))

    @property
    def pre_auxiliary(self) -> tuple[AuxiliaryText, ...]:
        """
        All auxiliary text preceding this node. Can be set to change the preceding auxiliary text.
        Returns an empty tuple if none found.
        """

        # Calculate the length of all auxiliary text of the first token in this node and its descendants.
        def first_tok(n: Node) -> Token | None:
            for x in n.children:
                if isinstance(x, Token):
                    return x
                else:
                    return first_tok(x)

        tok = first_tok(self)
        return tok.pre_auxiliary if tok is not None else ()

    @pre_auxiliary.setter
    def pre_auxiliary(self, value: tuple[AuxiliaryText, ...]):
        raise NotImplementedError("TODO :D")

    def _pre_auxiliary_length(self):
        # Calculate the length of all auxiliary text of the first token in this node and its descendants.
        return sum(len(a.text) for a in self.pre_auxiliary)

    # =========================
    # CHILDREN ATTACHMENT/DETACHMENT
    # =========================

    def _children_updated(self, slot: NodeSlot[Self, Element], elements: Iterable[Element], removed: bool):
        """
        Called when a child or more have been attached or detached after initialization.
        """
        if self._cached_text is not None:
            self._cached_text = None
            n = self.parent
            while n is not None and (n._cached_text is not None):
                n._cached_text = None
                n = n.parent

        for x in elements:
            if x.has_problems:
                self._update_has_problems(x.has_problems and not removed)
                return

    def attach_child(self, slot: NodeSlot[Self, E], el: E, idx=None) -> E:
        a = slot.attr

        assert el.parent is None, "Cannot attach a node that's already attached somewhere else."
        assert hasattr(self, a), f"Node {type(self).__name__} has no slot {a}"
        assert slot.accepts(el), f"Slot {slot} cannot accept the node {el!r}"

        if not slot.multi:
            if not slot.token and (prev := getattr(self, a)):
                node: Node = prev
                node._register_detachment()
            setattr(self, a, el)
        else:
            val = getattr(self, a)

            if idx is None:
                val.append(el)
            else:
                val.insert(idx, el)

        if not slot.token:
            el._register_attachment(self, slot)

        self._children_updated(slot, (el, ), False)

        return el

    def detach_child(self, slot: NodeSlot[Self, E], idx=None) -> tuple[E, ...]:
        a = slot.attr

        assert hasattr(self, a), f"Node {type(self).__name__} has no slot {a}"
        assert slot.multi or idx is None, "Cannot a specific index node on a single slot."

        if slot.multi:
            el_list: list[E] = getattr(self, a)
            if idx is None:
                els = tuple(el_list)
                el_list.clear()
            else:
                els = (el_list.pop(idx),)
        else:
            el = getattr(self, a)
            els = (el,) if el else ()

        if len(els) == 0:
            return ()

        if not slot.token:
            for el in els:
                el._register_detachment()

        self._children_updated(slot, els, True)

        return els

    def detach_self(self) -> tuple["Node", NodeSlot["Node", "Node"], int] | None:
        if self.parent is not None:
            parent, slot, idx = self.parent, self.parent_slot, self.parent_slot_idx
            if slot.multi:
                parent.detach_child(slot, idx)
            else:
                parent.detach_child(slot)
            return parent, slot, idx
        else:
            return None

    def get(self, slot: NodeSlot[Self, E]) -> list[E] | E | None:
        return getattr(self, slot.attr)

    def _register_attachment(self, other: "Node", slot: NodeSlot["Node", Self]):
        """
        Called when this node has been attached to another one, and sets the parent/parent slots accordingly.
        """
        assert self.parent is None

        self.parent = other
        self.parent_slot = slot

    def _register_detachment(self):
        """
        Called when this node has been detached from its parent, and resets the parent/parent slots accordingly.
        """
        self.parent = None
        self.parent_slot = None

    # =========================
    # PROBLEMS MANAGEMENT
    # =========================

    def with_problems(self, *problems: NodeProblem):
        self.problems = problems

        if len(self.problems) != len(problems):
            self._update_has_problems()

        return self

    def _update_has_problems(self, problematic_child=False):
        prev = self.has_problems
        self.has_problems = len(self.problems) > 0 or problematic_child or any(n for n in self.children if n.has_problems)

        if prev != self.has_problems:
            if self.has_problems:
                # Our node is problematic! Let's propagate that up the tree.
                n = self.parent
                while n is not None:
                    n.has_problems = True
                    n = n.parent
            else:
                # We aren't problematic anymore. Call the parent to propagate a recheck upwards.
                if self.parent is not None:
                    self.parent._update_has_problems()

    # =========================
    # SLOT MANAGEMENT
    # =========================

    def _init_single_slot(self, el: E, slot: SingleNodeSlot[Self, Element]) -> E | None:
        assert el is None or slot.accepts(el), f"Slot {slot} cannot accept the node {el!r}"

        if el:
            setattr(self, slot.attr, el)
            if not slot.token:
                n: Node = el
                n._register_attachment(self, slot)

            if el.has_problems: self._update_has_problems(True)

        return el

    def _init_multi_slot(self, el_list: Iterable[E], slot: MultiNodeSlot[Self, Element]) -> list[E]:
        l = list(el_list)

        if l:
            if not slot.token:
                for node in l:
                    assert slot.accepts(node), f"Slot {slot} cannot accept the node {node!r}"
                    node._register_attachment(self, slot)
                    if node.has_problems: self._update_has_problems(True)
            else:
                for el in l:
                    assert slot.accepts(el), f"Slot {slot} cannot accept the token {el!r}"
                    if el.has_problems: self._update_has_problems(True)

            setattr(self, slot.attr, l)

            self._children_updated(slot, l, False)

        return l

    def __str__(self):
        return self.pretty_print()

    def pretty_print(self, indent: int = 0):
        """
        Prints the node as a tree in a nice and indented way. Used in str(node).
        Nodes can have their own printing logic by creating a pretty_print(indent) function.
        :return: a string with the Node and its children
        """

        props = [x.attr for x in type(self).element_slots]

        # If we have no slots, print out the name and go away
        if len(props) == 0:
            return type(self).__name__ + "()"

        result = ""

        def append_indent(s: str):
            nonlocal result
            result += "    " * indent + s

        def append(s: str):
            nonlocal result
            result += s

        # Begin writing down the node's name and properties.
        append(type(self).__name__ + "(\n")
        # Increment the indentation for properties that will follow.
        indent += 1

        # Go through all the properties and print them.
        for p in props:
            # Print the property name first
            append_indent(f"{p.lstrip('_')} = ")
            # Get the value of the property
            value = getattr(self, p)

            if isinstance(value, Node):
                # It's a node ==> call pretty_print recursively
                append(value.pretty_print(indent))
            elif isinstance(value, list):
                # It's a list ==> increase the indent level and print all elements on each line.
                if len(value) > 0:
                    append("[\n")
                    indent += 1

                    # Now it's a bit of a dirty/copy-paste we could clean that out with proper recursion,
                    # but I'm lazy
                    for idx2, v in enumerate(value):
                        # Put out the indent first
                        append_indent("")

                        # Print the value out
                        if isinstance(v, Node):
                            append(v.pretty_print(indent))
                        else:
                            append(repr(v))

                        # Add a comma if necessary
                        if idx2 != len(value) - 1:
                            append(",")
                        append("\n")

                    indent -= 1
                    append_indent("]")
                else:
                    append("[]")
            else:
                # It's something else ==> print it using repr()
                append(repr(value))

            # Add a newline after each property
            append("\n")

        # Decrease the indent to write the closing parenthesis
        indent -= 1
        append_indent(")")

        return result


# ----------
# Base classes for statements and expressions
# ----------

class Statement(Node):
    """
    A statement node, which can be an instruction or a declaration in the program.

    Examples:
        - variable declarations (int x = 5)
        - if/else blocks
        - while loops
    """
    pass


class Expression(Node):
    """
    An expression node, which represents a value that can be evaluated to produce a result.

    Examples:
        - number literals (5, 3.14)
        - string literals ("hello, world!")
        - arithmetic operations (5 + 7)
    """
    pass

# ----------
# The root node: Program
# ----------

class Program(Node):
    """
    The root node of the syntax tree, representing the entire program, containing all statements to
    be run when executing the program.
    """

    __slots__ = ("_statements", "_eof")

    statements_slot: MultiNodeSlot["Program", Statement] = MultiNodeSlot("_statements", Statement)
    eof_slot: SingleNodeSlot["Program", Token] = SingleNodeSlot("_eof", Token,
                                                                  check_func=lambda t: t.kind == TokenKind.EOF)

    def __init__(self, statements: Iterable[Statement], eof: Token):
        super().__init__()
        self._init_multi_slot(statements, self.statements_slot)
        self._init_single_slot(eof, self.eof_slot)

    @property
    def statements(self) -> list[Statement]:
        "A list of all statements to run when executing the program: variable/function declarations and instructions."
        return self._statements

    @property
    def eof(self) -> Token:
        "The end-of-file token."
        return self._eof

    @property
    def children(self) -> Iterable[Element]:
        yield from self.statements
        yield self.eof

    @property
    def child_nodes(self) -> Iterable["Node"]:
        return self._statements

Program.element_slots = (Program.statements_slot, Program.eof_slot)
Program.node_slots = (Program.statements_slot, )