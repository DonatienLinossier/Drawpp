import typing
from enum import Enum
from typing import Optional, Iterable, TypeVar, Any, Union, Generic, Literal
import sys

from pydpp.compiler import ProblemSeverity
from pydpp.compiler.position import TextSpan

if sys.version_info[1] <= 10:
    # Run pip install typing-extensions for running on PyPy 3.10
    from typing_extensions import Self
else:
    from typing import Self

from pydpp.compiler.tokenizer import Token, TokenKind, IdentifierToken, AuxiliaryText
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
    __slots__ = tuple()
    attr: str
    "The attribute name in the node containing the raw slot data (node or list of nodes)"
    multi: bool
    name: str
    token: bool
    el_type: typing.Type[E]
    tok_kind: typing.Optional[TokenKind] = None
    check_func: typing.Callable[[E], bool] | None = None

    def __init__(self, attr_: str, el_type: typing.Type[E] | typing.Optional[TokenKind],
                 check_func: typing.Callable[[E], bool] | None = None):
        self.attr = attr_
        self.name = attr_.lstrip('_')
        self.token = el_type == Token or isinstance(el_type, TokenKind)
        self.el_type = Token if isinstance(el_type, TokenKind) else el_type
        self.tok_kind = el_type if isinstance(el_type, TokenKind) else None
        self.check_func = check_func

    def accepts(self, el: Element):
        return isinstance(el, self.el_type) \
            and ((not self.token) or self.tok_kind is None or el.kind == self.tok_kind) \
            and (self.check_func is None or self.check_func(el))

    def __repr__(self):
        return f"{type(self).__name__}({self.attr!r})"


class SingleNodeSlot(NodeSlot[P, E]):
    multi: Literal[False] = False


class MultiNodeSlot(NodeSlot[P, E]):
    multi: Literal[True] = True


T = TypeVar("T")


class AnnotationKey(Generic[T]):
    """
    A key that identifies a kind of annotation data attached to a node.
    Can react to various events happening to the node.

    Use the metaclass AnnotationKeyMeta to get a neat __str__ function for the class.
    """
    name: str

    @classmethod
    def child_change(cls, node: "Node", v: T):
        pass

    @classmethod
    def attached(cls, node: "Node", v: T):
        pass

    @classmethod
    def detached(cls, node: "Node", v: T):
        pass


class AnnotationKeyMeta(type):
    def __str__(cls: type[AnnotationKey]):
        return cls.name

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
        assert hasattr(node, self.slot.attr)

        # TODO: Optimize with a span cache

        if self.slot is None:
            return node.span

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

    __slots__ = ("semantic_info", "_cached_text", "parent", "parent_slot", "annotations")

    # Filled later on at the end of the file.
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

        self.annotations: dict[type[AnnotationKey], Any] = dict()
        "The dictionary of all annotations attached to this node."

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

    def _children_updated(self):
        """
        Called when a child or more have been attached or detached.
        """
        self._cached_text = None
        n = self.parent
        while n is not None and (n._cached_text is not None):
            n._cached_text = None
            n = n.parent

        for k, v in self.annotations.items():
            k.child_change(self, v)

    def _detached(self):
        """
        Called when this node has been detached from its parent.
        """
        for k, v in self.annotations.items():
            k.detached(self, v)

    def _attached(self):
        """
        Called when this node has been attached to a parent.
        """
        for k, v in self.annotations.items():
            k.attached(self, v)

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

        self._children_updated()

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

        self._children_updated()

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
        self._attached()

    def _register_detachment(self):
        """
        Called when this node has been detached from its parent, and resets the parent/parent slots accordingly.
        """
        self.parent = None
        self.parent_slot = None
        self._detached()

    # =========================
    # SLOT MANAGEMENT
    # =========================

    def _init_single_slot(self, el: E, slot: SingleNodeSlot[Self, Element]) -> E | None:
        assert el is None or slot.accepts(el), f"Slot {slot} cannot accept the node {el!r}"

        if not slot.token and el is not None:
            n: Node = el
            n._register_attachment(self, slot)

        return el

    def _init_multi_slot(self, el_list: Iterable[E], slot: MultiNodeSlot[Self, Element]) -> list[E]:
        if not slot.token:
            for node in el_list:
                assert slot.accepts(node), f"Slot {slot} cannot accept the node {node!r}"
                node._register_attachment(self, slot)
        else:
            for el in el_list:
                assert slot.accepts(el), f"Slot {slot} cannot accept the token {el!r}"

        return list(el_list)

    @staticmethod
    def single_slot(attr_name_: str, enforced_type: typing.Type[Element] | TokenKind,
                    check_func: typing.Callable[[Element], bool] | None = None):
        return SingleNodeSlot(attr_name_, enforced_type, check_func)

    @staticmethod
    def multi_slot(attr_name_: str, enforced_type: typing.Type[Element] | TokenKind,
                   check_func: typing.Callable[[Element], bool] | None = None):
        return MultiNodeSlot(attr_name_, enforced_type, check_func)

    @staticmethod
    def single_slot_prop(slot: SingleNodeSlot["Node", E]):
        return property(
            fget=lambda self: getattr(self, slot.attr),
            fset=lambda self, value: self.attach_child(slot, value)
        )

    @staticmethod
    def multi_slot_prop(slot: MultiNodeSlot["Node", E]):
        return property(
            fget=lambda self: getattr(self, slot.attr),
        )

    def __repr__(self):
        return f"{type(self).__name__}()"

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
# Nodes that don't fit into statements or expressions
# ----------

class BuiltInType(Node):
    """
    A built-in type specified using a keyword like int, bool...
    """

    __slots__ = ("_kind_token",)

    kind_token_slot: SingleNodeSlot["BuiltInType", Token] \
        = Node.single_slot("_kind_token", Token,
                           check_func=lambda t: t.kind in {TokenKind.KW_INT, TokenKind.KW_FLOAT, TokenKind.KW_BOOL,
                                                           TokenKind.KW_STRING})

    def __init__(self, kind_token: Token):
        super().__init__()

        self._kind_token = self._init_single_slot(kind_token, self.kind_token_slot)

    kind_token: Token | None = Node.single_slot_prop(kind_token_slot)
    "The token representing the built-in type: int, bool, etc."

    @property
    def kind(self) -> BuiltInTypeKind | None:
        if not self.kind_token:
            return None

        match self.kind_token.kind:
            case TokenKind.KW_INT:
                return BuiltInTypeKind.INT
            case TokenKind.KW_FLOAT:
                return BuiltInTypeKind.FLOAT
            case TokenKind.KW_BOOL:
                return BuiltInTypeKind.BOOL
            case TokenKind.KW_STRING:
                return BuiltInTypeKind.STRING
            case _:
                return None

    def __repr__(self):
        return f"{type(self).__name__}({self.kind!r})"


class Argument(Node):
    __slots__ = ("_expr", "_comma_token")

    expr_slot: SingleNodeSlot["Argument", Expression] = Node.single_slot("_expr", Expression)
    comma_token_slot: SingleNodeSlot["Argument", Token] = Node.single_slot("_comma_token", TokenKind.SYM_COMMA)

    def __init__(self, expr: Expression | None, comma_token: Token | None):
        super().__init__()
        self._expr = self._init_single_slot(expr, self.expr_slot)
        self._comma_token = self._init_single_slot(comma_token, self.comma_token_slot)

    expr: Expression | None = Node.single_slot_prop(expr_slot)
    comma_token: Token | None = Node.single_slot_prop(comma_token_slot)

    def __repr__(self):
        return f"{type(self).__name__}(expr={self._expr!r})"


class ArgumentList(Node):
    __slots__ = ("_arguments", "_lparen_token", "_rparen_token")

    lparen_token_slot: SingleNodeSlot["ArgumentList", Token] = Node.single_slot("_lparen_token", TokenKind.SYM_LPAREN)
    arguments_slot: MultiNodeSlot["ArgumentList", Argument] = Node.multi_slot("_arguments", Argument)
    rparen_token_slot: SingleNodeSlot["ArgumentList", Token] = Node.single_slot("_rparen_token", TokenKind.SYM_RPAREN)

    def __init__(self, lparen_token: Token, arguments: Iterable[Argument], rparen_token: Token):
        super().__init__()
        self._lparen_token = self._init_single_slot(lparen_token, self.lparen_token_slot)
        self._arguments = self._init_multi_slot(arguments, self.arguments_slot)
        self._rparen_token = self._init_single_slot(rparen_token, self.rparen_token_slot)

    lparen_token: Token | None = Node.single_slot_prop(lparen_token_slot)
    arguments: list[Argument] = Node.multi_slot_prop(arguments_slot)
    rparen_token: Token | None = Node.single_slot_prop(rparen_token_slot)

    def __repr__(self):
        return f"{type(self).__name__}(arguments={self._arguments!r})"


# ----------
# The root node: Program
# ----------

class Program(Node):
    """
    The root node of the syntax tree, representing the entire program, containing all statements to
    be run when executing the program.
    """

    __slots__ = ("_statements", "_eof")

    statements_slot: MultiNodeSlot["Program", Statement] = Node.multi_slot("_statements", Statement)
    eof_slot: SingleNodeSlot["Program", Token] = Node.single_slot("_eof", TokenKind.EOF,
                                                                  check_func=lambda t: t is not None)

    def __init__(self, statements: Iterable[Statement], eof: Token):
        super().__init__()
        self._statements = self._init_multi_slot(statements, self.statements_slot)
        self._eof = self._init_single_slot(eof, self.eof_slot)

    statements = Node.multi_slot_prop(statements_slot)
    "A list of all statements to run when executing the program: variable/function declarations and instructions."
    eof = Node.single_slot_prop(eof_slot)
    "The end-of-file token."

    @property
    def children(self) -> Iterable[Element]:
        yield from self.statements
        yield self.eof

    @property
    def child_nodes(self) -> Iterable["Node"]:
        return self._statements

    def __repr__(self):
        return f"{type(self).__name__}(statements={self._statements!r})"


# ----------
# Statements
# ----------

class VariableDeclarationStmt(Statement):
    """
    A variable declaration, with a type, identifier, and optional value.
    """

    __slots__ = ("_type", "_name_token", "_assign_token", "_value", "_semi_colon")

    type_slot: SingleNodeSlot[Self, BuiltInType] = Node.single_slot("_type", BuiltInType)
    name_token_slot: SingleNodeSlot[Self, IdentifierToken] = Node.single_slot("_name_token", TokenKind.IDENTIFIER)
    assign_token_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_assign_token", TokenKind.SYM_ASSIGN)
    value_slot: SingleNodeSlot[Self, Expression] = Node.single_slot("_value", Expression)
    semi_colon_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_semi_colon", TokenKind.SYM_SEMICOLON)

    def __init__(self,
                 var_type: BuiltInType | None,
                 name_token: Token | None,
                 assign_token: Token | None,
                 value: Expression | None,
                 semi_colon: Token | None):
        super().__init__()
        self._type = self._init_single_slot(var_type, self.type_slot)
        self._name_token = self._init_single_slot(name_token, self.name_token_slot)
        self._assign_token = self._init_single_slot(assign_token, self.assign_token_slot)
        self._value = self._init_single_slot(value, self.value_slot)
        self._semi_colon = self._init_single_slot(semi_colon, self.semi_colon_slot)

    type: BuiltInType | None = Node.single_slot_prop(type_slot)
    "The type of the variable. (Currently built-in types only)"
    name: IdentifierToken | None = Node.single_slot_prop(name_token_slot)
    "The name of the variable, as an Identifier."
    equal_token: Token | None = Node.single_slot_prop(assign_token_slot)
    "The equal token, before the default value."
    value: Expression | None = Node.single_slot_prop(value_slot)
    "The value of the variable, can be None."
    semi_colon: Token | None = Node.single_slot_prop(semi_colon_slot)
    "The semicolon token at the end of the statement."

    def __repr__(self):
        return f"{type(self).__name__}(type={self._type!r}, name={self._name_token!r}, value={self._value!r})"


class BlockStmt(Statement):
    """
    A block statement, which is a sequence of statements enclosed in curly braces.
    """

    __slots__ = ("_statements", "_open_brace_token", "_close_brace_token")

    open_brace_token_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_open_brace_token", TokenKind.SYM_LBRACE)
    statements_slot: MultiNodeSlot[Self, Statement] = Node.multi_slot("_statements", Statement)
    close_brace_token_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_close_brace_token", TokenKind.SYM_RBRACE)

    def __init__(self,
                 open_brace_token: Token | None,
                 statements: Iterable[Statement],
                 close_brace_token: Token | None):
        super().__init__()
        self._open_brace_token = self._init_single_slot(open_brace_token, self.open_brace_token_slot)
        self._statements = self._init_multi_slot(statements, self.statements_slot)
        self._close_brace_token = self._init_single_slot(close_brace_token, self.close_brace_token_slot)

    open_brace_token: Token | None = Node.single_slot_prop(open_brace_token_slot)
    "The { token."
    statements: list[Statement] = Node.multi_slot_prop(statements_slot)
    "The list of statements inside the block."
    close_brace_token: Token | None = Node.single_slot_prop(close_brace_token_slot)
    "The } token."

    def __repr__(self):
        return f"{type(self).__name__}(statements={self._statements!r})"


# Function declaration will be implemented later

class IfStmt(Statement):
    """
    An if statement, with [0..N] else/else-if blocks.
    """

    # Should we create an "ElseStmt" or keep it this way...?
    # Having a separate Else statement would make error reporting easier,
    # but the tree would be a bit weirder to manipulate.

    __slots__ = ("_if_token", "_condition", "_then_block", "_else_statements")

    if_token_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_if_token", TokenKind.KW_IF)
    condition_slot: SingleNodeSlot[Self, Expression] = Node.single_slot("_condition", Expression)
    then_block_slot: SingleNodeSlot[Self, BlockStmt] = Node.single_slot("_then_block", BlockStmt)
    else_statements_slot: MultiNodeSlot[Self, "ElseStmt"] = Node.multi_slot("_else_statements", Node)

    def __init__(self,
                 if_token: Token | None,
                 condition: Expression | None,
                 then_block: BlockStmt | None,
                 else_statements: Optional[Iterable["ElseStmt"]] = None):
        super().__init__()
        self._if_token = self._init_single_slot(if_token, self.if_token_slot)
        self._condition = self._init_single_slot(condition, self.condition_slot)
        self._then_block = self._init_single_slot(then_block, self.then_block_slot)
        self._else_statements = self._init_multi_slot(list(else_statements) if else_statements is not None else [],
                                                      self.else_statements_slot)

    if_token: Token | None = Node.single_slot_prop(if_token_slot)
    "The 'if' token."
    condition: Expression | None = Node.single_slot_prop(condition_slot)
    "The condition to check for the if block."
    then_block: BlockStmt | None = Node.single_slot_prop(then_block_slot)
    "The block to run if the condition is true."
    else_statements: list["ElseStmt"] = Node.multi_slot_prop(else_statements_slot)
    """
    The list of else if and else blocks. The else block should be located last.
    An erroneous if statement might contain misplaced else/else-if blocks.
    """

    def __repr__(self):
        return f"{type(self).__name__}(condition={self.condition!r}, then_block={self.then_block!r}, else_statements={self.else_statements!r})"


class ElseStmt(Statement):
    """
    An "else" or "else if" statement. Should be located inside an IfStmt.
    If located somewhere else, it's an error.
    """

    __slots__ = ("_else_token", "_if_token", "_condition", "_block")

    else_token_slot: SingleNodeSlot["ElseStmt", Token] = Node.single_slot("_else_token", TokenKind.KW_ELSE)
    if_token_slot: SingleNodeSlot["ElseStmt", Token] = Node.single_slot("_if_token", TokenKind.KW_IF)
    condition_slot: SingleNodeSlot["ElseStmt", Expression] = Node.single_slot("_condition", Expression)
    block_slot: SingleNodeSlot["ElseStmt", BlockStmt] = Node.single_slot("_block", BlockStmt)

    def __init__(self, else_token: Token | None, if_token: Token | None, condition: Expression | None,
                 block: BlockStmt | None):
        super().__init__()
        self._else_token = self._init_single_slot(else_token, self.else_token_slot)
        self._if_token = self._init_single_slot(if_token, self.if_token_slot)
        self._condition = self._init_single_slot(condition, self.condition_slot)
        self._block = self._init_single_slot(block, self.block_slot)

    else_token: Token | None = Node.single_slot_prop(else_token_slot)
    if_token: Token | None = Node.single_slot_prop(if_token_slot)
    condition: Expression | None = Node.single_slot_prop(condition_slot)
    block: BlockStmt | None = Node.single_slot_prop(block_slot)

    def __repr__(self):
        return f"{type(self).__name__}(condition={self._condition!r}, block={self._block!r})"


IfStmt.else_statements_slot.el_type = ElseStmt


class WhileStmt(Statement):
    """
    A while loop, with a condition and a block of statements to run while the condition is true.
    """

    __slots__ = ("_while_token", "_condition", "_block")

    while_token_slot: SingleNodeSlot["WhileStmt", Token] = Node.single_slot("_while_token", TokenKind.KW_WHILE)
    condition_slot: SingleNodeSlot["WhileStmt", Expression] = Node.single_slot("_condition", Expression)
    block_slot: SingleNodeSlot["WhileStmt", BlockStmt] = Node.single_slot("_block", BlockStmt)

    def __init__(self, while_token: Token | None, condition: Expression | None, block: BlockStmt | None):
        super().__init__()
        self._while_token = self._init_single_slot(while_token, self.while_token_slot)
        self._condition = self._init_single_slot(condition, self.condition_slot)
        self._block = self._init_single_slot(block, self.block_slot)

    while_token: Token | None = Node.single_slot_prop(while_token_slot)
    "The 'while' token."
    condition: Expression | None = Node.single_slot_prop(condition_slot)
    "The condition to check before running the block."
    block: BlockStmt | None = Node.single_slot_prop(block_slot)
    "The block of statements to run while the condition is true."

    def __repr__(self):
        return f"{type(self).__name__}(condition={self.condition!r}, block={self.block!r})"


class FunctionCallStmt(Statement):
    """
    A function call statement, which just contains a function call expression, and discards the
    return value of the function.
    """

    __slots__ = ("_expr", "_semi_colon")

    expr_slot: SingleNodeSlot["FunctionCallStmt", "FunctionExpr"] = Node.single_slot("_expr", Node)
    semi_colon_slot: SingleNodeSlot["FunctionCallStmt", Token] = Node.single_slot("_semi_colon",
                                                                                  TokenKind.SYM_SEMICOLON)

    def __init__(self, expr: Optional["FunctionExpr"], semi_colon: Token | None):
        super().__init__()
        self._expr = self._init_single_slot(expr, self.expr_slot)
        self._semi_colon = self._init_single_slot(semi_colon, self.semi_colon_slot)

    expr: Optional["FunctionExpr"] = Node.single_slot_prop(expr_slot)
    semi_colon: Token | None = Node.single_slot_prop(semi_colon_slot)

    def __repr__(self):
        return f"{type(self).__name__}(expr={self.expr!r})"


class AssignStmt(Statement):
    """
    A variable assignment statement, which assigns a value to an existing variable.
    """

    __slots__ = ("_name_token", "_assign_token", "_value", "_semi_colon")

    name_token_slot: SingleNodeSlot[Self, IdentifierToken] = Node.single_slot("_name_token", TokenKind.IDENTIFIER)
    assign_token_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_assign_token", TokenKind.SYM_ASSIGN)
    value_slot: SingleNodeSlot[Self, Expression] = Node.single_slot("_value", Expression)
    semi_colon_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_semi_colon", TokenKind.SYM_SEMICOLON)

    def __init__(self, name: IdentifierToken | None,
                 assign_token: Token | None,
                 value: Expression | None,
                 semi_colon: Token | None):
        super().__init__()
        self._name_token = self._init_single_slot(name, self.name_token_slot)
        self._assign_token = self._init_single_slot(assign_token, self.assign_token_slot)
        self._value = self._init_single_slot(value, self.value_slot)
        self._semi_colon = self._init_single_slot(semi_colon, self.semi_colon_slot)

    name_token: IdentifierToken | None = Node.single_slot_prop(name_token_slot)
    "The name of the variable to assign"
    assign_token: Token | None = Node.single_slot_prop(assign_token_slot)
    "The assignment token, before the value to assign"
    value: Expression | None = Node.single_slot_prop(value_slot)
    "The value to assign to the variable"
    semi_colon: Token | None = Node.single_slot_prop(semi_colon_slot)
    "The semicolon token at the end of the statement"

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name_token!r}, value={self.value!r})"


class ErrorStmt(Statement):
    """
    An invalid/unrecognized statement. Prevents compilation.
    """
    __slots__ = tuple("_tokens")

    tokens_slot: MultiNodeSlot[Self, Token] = Node.multi_slot("_tokens", Token)

    def __init__(self, tokens: Iterable[Token]):
        super().__init__()
        self._tokens = self._init_multi_slot(tokens, self.tokens_slot)

    tokens: list[Token] = Node.multi_slot_prop(tokens_slot)

    def __repr__(self):
        return f"{type(self).__name__}(tokens={self.tokens!r})"


# ----------
# Expressions
# ----------

class LiteralExpr(Expression):
    """
    A literal expression, which can be either:
        - a number literal (5, 3.14)
        - a string literal ("hello, world!")
        - a boolean literal (true, false)
    """

    __slots__ = ("_token",)

    token_slot: SingleNodeSlot[Self, Token] \
        = Node.single_slot("_token",
                           Token,
                           check_func=lambda t: t is not None and t.kind in {TokenKind.LITERAL_NUM,
                                                                             TokenKind.LITERAL_STRING,
                                                                             TokenKind.LITERAL_BOOL})

    def __init__(self, token: Token):
        super().__init__()
        self._token = self._init_single_slot(token, self.token_slot)

    token: Token = Node.single_slot_prop(token_slot)

    def __repr__(self):
        return f"{type(self).__name__}({self._token!r})"

    def pretty_print(self, indent: int = 0):
        return f"LiteralExpr({self._token!r})"


class BinaryOperator(Enum):
    """
    A binary operator, placed between two expressions and producing a value, like +, -, etc.
    """
    ADD = "+"
    "The addition operator."

    SUB = "-"
    "The subtraction operator."

    MUL = "*"
    "The multiplication operator."

    DIV = "/"
    "The division operator."

    AND = "and"
    "The AND boolean operator."

    OR = "or"
    "The OR boolean operator."

    EQ = "=="
    "The equality operator."

    NEQ = "!="
    "The inequality operator."

    LT = "<"
    "The less-than operator."

    LEQ = "<="
    "The less-than-or-equal operator."

    GT = ">"
    "The greater-than operator."

    GEQ = ">="
    "The greater-than-or-equal operator."


class BinaryOperationExpr(Expression):
    """
    A binary operation expression, following this pattern: left [operator] right.
    Where [operator] is a binary operator in the ``BinaryOperator`` enum.

    Examples:
        - 5 + 8 ; left = 5, operator = ADD, right = 8
        - 8 * 6 ; left = 8, operator = MUL, right = 6
    """

    __slots__ = ("_left", "_op_token", "_right")

    _compatible_operators = {
        TokenKind.KW_OR: BinaryOperator.OR,
        TokenKind.KW_AND: BinaryOperator.AND,
        TokenKind.SYM_EQ: BinaryOperator.EQ,
        TokenKind.SYM_NEQ: BinaryOperator.NEQ,
        TokenKind.SYM_LT: BinaryOperator.LT,
        TokenKind.SYM_LEQ: BinaryOperator.LEQ,
        TokenKind.SYM_GT: BinaryOperator.GT,
        TokenKind.SYM_GEQ: BinaryOperator.GEQ,
        TokenKind.SYM_PLUS: BinaryOperator.ADD,
        TokenKind.SYM_MINUS: BinaryOperator.SUB,
        TokenKind.SYM_STAR: BinaryOperator.MUL,
        TokenKind.SYM_SLASH: BinaryOperator.DIV,
    }

    left_slot: SingleNodeSlot[Self, Expression] = Node.single_slot("_left", Expression)
    op_token_slot: SingleNodeSlot[Self, Token] \
        = Node.single_slot("_op_token", Token,
                           check_func=lambda t: t is not None and t.kind in BinaryOperationExpr._compatible_operators)
    right_slot: SingleNodeSlot[Self, Expression] = Node.single_slot("_right", Expression)

    def __init__(self, left: Expression | None,
                 operator: Token | None,
                 right: Expression | None):
        super().__init__()
        self._left = self._init_single_slot(left, self.left_slot)
        self._op_token = self._init_single_slot(operator, self.op_token_slot)
        self._right = self._init_single_slot(right, self.right_slot)

    left: Expression | None = Node.single_slot_prop(left_slot)
    "The left operand of the binary operation."
    op_token: Token = Node.single_slot_prop(op_token_slot)
    "The operator of the binary operation."
    right: Expression | None = Node.single_slot_prop(right_slot)
    "The right operand of the binary operation."

    @property
    def operator(self) -> BinaryOperator | None:
        if self.op_token is None:
            return None
        return self._compatible_operators[self.op_token.kind]

    def __repr__(self):
        return f"{type(self).__name__}(left={self.left!r}, operator={self.operator!r}, right={self.right!r})"


class ParenthesizedExpr(Expression):
    """
    An expression enclosed in parentheses.
    """

    __slots__ = ("_lparen_token", "_expr", "_rparen_token")

    lparen_token_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_lparen_token", TokenKind.SYM_LPAREN)
    expr_slot: SingleNodeSlot[Self, Expression] = Node.single_slot("_expr", Expression)
    rparen_token_slot: SingleNodeSlot[Self, Token] = Node.single_slot("_rparen_token", TokenKind.SYM_RPAREN)

    def __init__(self, lparen_token: Token | None, expr: Expression | None, rparen_token: Token | None):
        super().__init__()
        self._lparen_token = self._init_single_slot(lparen_token, self.lparen_token_slot)
        self._expr = self._init_single_slot(expr, self.expr_slot)
        self._rparen_token = self._init_single_slot(rparen_token, self.rparen_token_slot)

    lparen_token: Token | None = Node.single_slot_prop(lparen_token_slot)
    expr: Expression | None = Node.single_slot_prop(expr_slot)
    rparen_token: Token | None = Node.single_slot_prop(rparen_token_slot)

    def __repr__(self):
        return f"{type(self).__name__}(expr={self.expr!r})"


class UnaryExpr(Expression):
    """
    A unary expression, an expression with a NOT/- operator before it.
    Example: NOT true
    """

    __slots__ = ("_op_token", "_expr")

    _compatible_operators = {TokenKind.KW_NOT, TokenKind.SYM_MINUS}

    op_token_slot: SingleNodeSlot[Self, Token] \
        = Node.single_slot("_op_token", Token,
                           check_func=lambda t: t is not None and t.kind in UnaryExpr._compatible_operators)
    _expr_slot: SingleNodeSlot[Self, Expression] = Node.single_slot("_expr", Expression)

    def __init__(self, op_token: Token, expr: Expression | None):
        super().__init__()
        self._op_token = self._init_single_slot(op_token, self.op_token_slot)
        self._expr = self._init_single_slot(expr, self._expr_slot)

    op_token: Token = Node.single_slot_prop(op_token_slot)
    expr: Expression | None = Node.single_slot_prop(_expr_slot)

    def __repr__(self):
        return f"{type(self).__name__}(expr={self.expr!r})"


class FunctionExpr(Expression):
    """
    A function call expression, which calls a function with a list of arguments, and gives
    the return value of the function.
    """

    __slots__ = ("_identifier_token", "_arg_list")

    identifier_token_slot: SingleNodeSlot[Self, IdentifierToken] = Node.single_slot("_identifier_token",
                                                                                    TokenKind.IDENTIFIER)
    arg_list_slot: SingleNodeSlot[Self, ArgumentList] = Node.single_slot("_arg_list", ArgumentList)

    def __init__(self, name: Token, arguments: ArgumentList):
        super().__init__()
        self._identifier_token = self._init_single_slot(name, self.identifier_token_slot)
        self._arg_list = self._init_single_slot(arguments, self.arg_list_slot)

    name: IdentifierToken = Node.single_slot_prop(identifier_token_slot)
    "The name of the function to call."

    arguments: ArgumentList = Node.single_slot_prop(arg_list_slot)
    "The list of arguments to pass to the function. Can be empty."

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r}, arguments={self.arguments!r})"


class VariableExpr(Expression):
    """
    A variable expression, returning the value of a variable.
    """

    __slots__ = ("_name_token",)

    name_token_slot: SingleNodeSlot[Self, IdentifierToken] = Node.single_slot("_name_token", TokenKind.IDENTIFIER,
                                                                              check_func=lambda t: t is not None)

    def __init__(self, name_token: Token):
        super().__init__()
        self._name_token = self._init_single_slot(name_token, self.name_token_slot)

    name_token = Node.single_slot_prop(name_token_slot)
    "The token with the name of the variable."

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name_token!r})"

    def pretty_print(self, indent: int = 0):
        return f"VariableExpr({self.name_token!r})"


class ErrorExpr(Expression):
    """
    An invalid/unrecognized expression. Prevents compilation. Has unknown type.
    """
    __slots__ = ("_tokens",)

    tokens_slot: MultiNodeSlot[Self, Token] = Node.multi_slot("_tokens", Token)

    def __init__(self, tokens: Iterable[Token]):
        super().__init__()
        self._tokens = self._init_multi_slot(tokens, self.tokens_slot)

    tokens: list[Token] = Node.multi_slot_prop(tokens_slot)

    def __repr__(self):
        return f"{type(self).__name__}(tokens={self.tokens!r})"


FunctionCallStmt.expr_slot.el_type = FunctionExpr

# Iterate through all Node class declared in this file,
# and add all declared class attributes of type "NodeSlot" into the element_slots class attribute
import inspect

for cls in tuple(globals().values()):
    if inspect.isclass(cls) and issubclass(cls, Node):
        slots = []
        for attr_name, attr in cls.__dict__.items():
            if isinstance(attr, NodeSlot):
                slots.append(attr)
        cls.element_slots = slots
        cls.node_slots = tuple(filter(lambda x: not x.token, slots))
