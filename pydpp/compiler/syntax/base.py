import typing
from typing import Optional, Iterable, TypeVar, Any, Generic, Literal
import sys

from pydpp.compiler.problem import ProblemSeverity, ProblemCode
from pydpp.compiler.position import TextSpan

if sys.version_info[1] <= 10:
    # Run pip install typing-extensions for running on PyPy 3.10
    from typing_extensions import Self
else:
    from typing import Self

from pydpp.compiler.tokenizer import Token, TokenKind, AuxiliaryText, TokenProblem

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

P = TypeVar("P", bound="InnerNode")
N = TypeVar("N", bound="Node")


class NodeSlot(Generic[P, N]):
    """
    Describes a slot containing children elements (nodes or tokens) in a node.

    Slots come in two variants: Single ([0; 1]) and Multi ([0; N]).
    """
    __slots__ = ("attr", "name", "el_type", "check_func", "optional")
    multi: bool

    def __init__(self, attr_: str, el_type: typing.Type[N],
                 check_func: typing.Callable[[N], bool] | None = None,
                 optional: bool = True):
        # TODO: Optional support
        self.attr = attr_
        "The attribute name in the node containing the raw slot data (node or list of nodes)"
        self.name = attr_.lstrip('_')
        self.el_type = el_type
        self.check_func = check_func
        self.optional = optional

    def accepts(self, el: "Node"):
        return isinstance(el, self.el_type) and (self.check_func is None or self.check_func(el))

    def __repr__(self):
        return f"{type(self).__name__}({self.name}, {self.el_type.__name__})"


class SingleNodeSlot(NodeSlot[P, N]):
    multi: Literal[False] = False


class MultiNodeSlot(NodeSlot[P, N]):
    multi: Literal[True] = True


T = TypeVar("T")

class InnerNodeProblem:
    """
    An issue related to an inner node during parsing.
    """
    __slots__ = ("message", "severity", "slot", "code")

    def __init__(self, message: str,
                 severity: ProblemSeverity = ProblemSeverity.ERROR,
                 slot: NodeSlot["InnerNode", "Node"] | None = None,
                 code: ProblemCode = ProblemCode.OTHER):
        self.message = message
        self.severity = severity
        self.slot = slot
        """
        On which slot the problem is located. 
        If the slot is specified, the problem spans the text of the slot.
        If not slot is specified, the problem spans the entire node.
        If the slot is empty, the problems spans a 0-length node on the left of the slot.
        """

        self.code = code
        "The error code of the problem."

    def compute_span(self, node: "InnerNode") -> TextSpan:
        # TODO: Optimize with a span cache

        if self.slot is None:
            return node.span

        assert hasattr(node, self.slot.attr)

        # Increase the number of preceding characters (inner_start) until we reach our slot.
        node_start = node.full_span_start
        inner_start = 0
        for s in node.element_slots:
            if s == self.slot:
                break
            if s.multi:
                # Many nodes: sum their length
                inner_start += sum(len(x.full_text) for x in getattr(node, s.attr))
            else:
                # Zero or one node: add its length
                el = getattr(node, s.attr)
                if el is not None:
                    inner_start += len(el.full_text)

        # Find the node in the slot. It's very likely that the node just doesn't exist, because
        # that's why we have slot support in the first place.
        slot_value = node.get(self.slot)
        # Find the first element of the slot, or None if it's empty.
        first_child = (slot_value[0] if slot_value else None) if self.slot.multi else slot_value

        if first_child is not None:
            # We already have a child. Just use its span.
            return first_child.span
        else:
            # We don't have a child. Take the closest location we can find.
            return TextSpan(node_start + inner_start, node_start + inner_start)

    def __repr__(self):
        return f"NodeProblem({self.message!r}, {self.severity!r})"

class Node:
    """
    A node in the syntax tree, which can be either:
    - An inner node (InnerNode), with children
    - A leaf node (LeafNode), with no children
    """
    __slots__ = ("parent", "parent_slot", "_cached_fss")
    parent: Optional["InnerNode"]
    parent_slot: Optional[NodeSlot["InnerNode", "Node"]]
    has_problems: bool
    _cached_fss: int | None

    # =========================
    # CHILDREN ATTACHMENT/DETACHMENT
    # =========================

    def register_attachment(self, other: "InnerNode", slot: NodeSlot["InnerNode", Self]):
        """
        Called when this node has been attached to another one, and sets the parent/parent slots accordingly.
        """
        assert self.parent is None

        self.parent = other
        self.parent_slot = slot

    def register_detachment(self):
        """
        Called when this node has been detached from its parent, and resets the parent/parent slots accordingly.
        """
        self.parent = None
        self.parent_slot = None

    def detach_self(self) -> tuple["InnerNode", NodeSlot["InnerNode", "Node"], int] | None:
        if self.parent is not None:
            parent, slot, idx = self.parent, self.parent_slot, self.parent_slot_idx
            if slot.multi:
                parent.detach_child(slot, idx)
            else:
                parent.detach_child(slot)
            return parent, slot, idx
        else:
            return None


    @property
    def parent_slot_idx(self) -> int | None:
        if self.parent_slot is None or not self.parent_slot.multi:
            return None
        else:
            return self.parent.get(self.parent_slot).index(self)

    # =========================
    # POSITION & TEXT
    # =========================

    @property
    def full_span_start(self) -> int:
        """
        Returns the index of the first character of this node, including auxiliary text.
        """

        if self._cached_fss is None:
            # We need to initialize the cached value of the FSS (Full Span Start).
            # To do so, we need to calculate the FSS of
            # - all left siblings of this node
            # - the parent chain of this node (until we reach the root node)
            #
            # We calculate first the parent's FSS, so we get the start position for our nodes.
            # Using that information, we can easily calculate the FSS of all our siblings on the left,
            # since that value is just equal to FSS(parent) + Σ full_text_length(left_sibling).

            par = self.parent

            if par is None:
                # We're root, our FSS is zero.
                self._cached_fss = 0
                return 0

            offset = 0
            parent_fss = par.full_span_start
            for c in par.children:
                c._cached_fss = parent_fss + offset
                if c is self:
                    # My cached FSS is set. Let's stop there.
                    break
                offset += len(c.full_text)

        return self._cached_fss

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
        s = self.span_start
        return TextSpan(s, s + len(self.text))

    @property
    def full_span(self) -> TextSpan:
        """
        Returns the full span of characters covered by this node, including auxiliary text.
        Cost of this property ramps up the deeper the node is, so be mindful!
        """
        s = self.full_span_start
        return TextSpan(s, s + len(self.full_text))

    @property
    def full_text(self) -> str:
        raise NotImplementedError()
    
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
    def pre_auxiliary(self) -> tuple[AuxiliaryText, ...]:
        raise NotImplementedError()

    def _pre_auxiliary_length(self):
        # Calculate the length of all auxiliary text of the first token in this node and its descendants.
        return sum(len(a.text) for a in self.pre_auxiliary)

    # =========================
    # CHILDREN PROPERTIES
    # =========================

    @property
    def children(self) -> Iterable["Node"]:
        raise NotImplementedError()

    @property
    def children_reverse(self) -> Iterable["Node"]:
        raise NotImplementedError()

    @property
    def child_inner_nodes(self) -> Iterable["InnerNode"]:
        raise NotImplementedError()

    def child_at(self, idx: int, inner_nodes=False):
        """
        Returns the child node at the given index.
        :param idx: the index of the child node
        :param inner_nodes: whether to return only inner nodes
        :return: the child node
        """
        for i, n in enumerate(self.children if not inner_nodes else self.child_inner_nodes):
            if i == idx:
                return n
        return None

    def descendants(self, filter: typing.Callable[["Node"], bool] | type[N] = None, stop=False) -> Iterable[N]:
        """
        Returns all descendants of this node: the childrens AND all their childrens, recursively.
        Use the filter parameter to specify which nodes should be returned, which can be either:
            -> a function: applied on each descendant
            -> a type: only descendants of that type will be returned

        Examples: node.descendants() -> all descendants
                  node.descendants(Expression) -> all descendants of type Expression
                  node.descendants(lambda x: x.has_problems) -> all descendants with problems

        :param filter: a filter function/type to apply to each node
        :param stop: whether to stop scanning children nodes when a node matches the filter
        :return: all descendants
        """

        if isinstance(filter, type):
            func = lambda n: isinstance(n, filter)
        else:
            func = filter

        for c in self.children:
            if func is None or func(c):
                yield c
                if stop:
                    continue
            yield from c.descendants(filter)

    def ancestor(self, filter: typing.Callable[[N], bool] | type[N], include_self=False) -> N | None:
        """
        Returns the first ancestor of this node that matches the filter.
        Goes up parent to parent until one is found.

        :param filter: a filter function/type to apply to each node
        :param include_self: whether to include the current node in the search
        :return: the ancestor node
        """

        if isinstance(filter, type):
            func = lambda n: isinstance(n, filter)
        else:
            func = filter

        n = self if include_self else self.parent
        while n is not None:
            if func(n):
                return n
            n = n.parent

        return None

    def find(self, filter: typing.Callable[[N], bool] | type[N], span: TextSpan) -> N | None:
        """
        Finds the smallest node that covers this span, with the given filter applied.
        :param filter: the filter to use while searching
        :param span: the span to search for
        :return: a node. or not. who knows?
        """

        # Convert the filter to a function
        if isinstance(filter, type):
            func = lambda n: isinstance(n, filter)
        else:
            func = filter

        # If we're in the span and fulfilling the filter, we can be a good candidate.
        last_good = self if func(self) and span in self.full_span else None

        # We could do a binary search but I'm lazy
        for c in self.children:
            if span in c.full_span:
                # Do some recursive search.
                if deeper := c.find(filter, span):
                    return deeper
                else:
                    return last_good

        # No child matches the span. It's game over.
        return last_good

    def replace_with(self, other):
        """
        Replaces this node with another one. The other node is attached to the parent of this node.
        """
        assert self.parent is not None  # Obviously if we're the root we can replace ourselves

        parent = self.parent
        slot = self.parent_slot
        idx = self.parent_slot_idx or 0

        self.detach_self()

        parent.attach_child(slot, other, idx)

    # =========================
    # PROBLEM PROPERTIES
    # =========================

    @property
    def problems(self) -> tuple[InnerNodeProblem | TokenProblem, ...]:
        raise NotImplementedError()

    @property
    def has_problems(self) -> bool:
        raise NotImplementedError()

    # =========================
    # COOL PRINTING FUNCS
    # =========================

    def pretty_str(self, indent: int = 0):
        """
        Prints the node as a tree in a nice and indented way. Used in str(node).
        Nodes can have their own printing logic by creating a pretty_print(indent) function.
        :return: a string with the Node and its children
        """

        if isinstance(self, LeafNode):
            return repr(self)

        assert isinstance(self, InnerNode)
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

            if isinstance(value, InnerNode):
                # It's a node ==> call pretty_print recursively
                append(value.pretty_str(indent))
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
                        append(v.pretty_str(indent))

                        # Add a comma if necessary
                        if idx2 != len(value) - 1:
                            append(",")
                        append("\n")

                    indent -= 1
                    append_indent("]")
                else:
                    append("[]")
            else:
                # It's something else or a LeafNode ==> print it using repr()
                append(repr(value))

            # Add a newline after each property
            append("\n")

        # Decrease the indent to write the closing parenthesis
        indent -= 1
        append_indent(")")

        return result

    def print_fancy(self, include_tokens=True):
        """
        Prints the node and its children in a fancy tree-like representation.
        Requires an ANSI-compatible terminal for C O L O R S!
        """
        _print_fancy_tree(self, include_tokens, 0, "", True)


class InnerNode(Node):
    """
    An inner node in the syntax tree.
    Represents a whole recognized element in the source code, which may have children nodes.

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

    __slots__ = ("_cached_text", "problems", "has_problems")

    element_slots: tuple[NodeSlot[Self, "Node"], ...] = ()
    inner_node_slots: tuple[NodeSlot[Self, "InnerNode"], ...] = ()

    def __init__(self):
        self._cached_text: str | None = None
        self._cached_fss: int | None = None

        self.parent: InnerNode | None = None
        "The parent node of this node. None if this node is the root node or not attached yet."
        self.parent_slot: NodeSlot[InnerNode, InnerNode] | None = None
        "The slot in the parent node where this node is attached. None if this node is the root node or not attached yet."

        self.problems: tuple[InnerNodeProblem, ...] = ()
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
    def children(self) -> Iterable["InnerNode"]:
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
    def children_reverse(self) -> Iterable["Node"]:
        """
        Returns all children elements of this node, in reverse order.
        """
        for s in reversed(self.element_slots):
            v = getattr(self, s.attr)
            if s.multi:
                yield from reversed(v)
            else:
                if v is not None:
                    yield v

    @property
    def child_inner_nodes(self) -> Iterable["InnerNode"]:
        """
        Returns all children nodes of this node. Only returns nodes, not tokens!
        """
        for s in self.inner_node_slots:
            v = getattr(self, s.attr)
            if s.multi:
                yield from v
            else:
                if v is not None:
                    yield v

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
            self._cached_text = "".join(x.full_text for x in self.children)

        return self._cached_text

    @property
    def pre_auxiliary(self) -> tuple[AuxiliaryText, ...]:
        """
        All auxiliary text preceding this node. Can be set to change the preceding auxiliary text.
        Returns an empty tuple if none found.
        """

        # Find the first token in the tree
        def first_tok(n: InnerNode) -> LeafNode | None:
            for x in n.children:
                if isinstance(x, LeafNode):
                    return x
                else:
                    return first_tok(x)

            # Nothing :(
            return None

        tok = first_tok(self)
        return tok.pre_auxiliary if tok is not None else ()

    @pre_auxiliary.setter
    def pre_auxiliary(self, value: tuple[AuxiliaryText, ...]):
        n = self._get_pre_auxiliary_node()

        # Normally this can't happen in any case, but we do have some very rare edge cases where
        # a node has no children at all.
        assert n is not None

        new_tok = Token(
            n.kind,
            n.text,
            value,
            n.problems
        )
        n.replace_with(leaf(new_tok))

    def _get_pre_auxiliary_node(self) -> Optional["LeafNode"]:
        """
        Returns the node containing this node's pre-auxiliary text: the first token.
        """

        # Find the first token in the tree
        def first_tok(n: InnerNode) -> LeafNode | None:
            for x in n.children:
                if isinstance(x, LeafNode):
                    return x
                else:
                    return first_tok(x)

            # Nothing :(
            return None

        tok = first_tok(self)
        return tok

    # =========================
    # CHILDREN ATTACHMENT/DETACHMENT
    # =========================

    def _children_updated(self,
                          slot: NodeSlot[Self, N],
                          elements: tuple[N] | list[N],
                          removed: bool,
                          removed_idx: int | None = None):
        """
        Called when a child or more have been attached or detached after initialization.
        """
        if self._cached_text is not None:
            self._cached_text = None
            n = self.parent
            while n is not None and (n._cached_text is not None):
                n._cached_text = None
                n = n.parent

        # Invalidate the cached file span start value. Try to:
        # - Find all right siblings of the node AND our parent chain (that includes ourselves)
        # - Invalidate all children of the siblings
        if self._cached_fss is not None:
            def invalidate_node(node: "Node"):
                node._cached_fss = None
                for child in node.children:
                    if child._cached_fss is not None:
                        invalidate_node(child)

            def child_at_idx(idx: int | None):
                if idx is None:
                    return next(iter(self.children), None)

                for i, node in enumerate(self.children):
                    if i == idx:
                        return node
                return None

            # Of course invalidate ourselves first!
            self._cached_fss = None

            par = self
            scan_start = elements[0] if not removed else child_at_idx(removed_idx)

            while par is not None:
                consider = False
                for c in par.children:
                    if consider:
                        if c._cached_fss is not None:
                            invalidate_node(c)
                        else:
                            # Stop scanning other children on the right, this one has no FSS,
                            # so must be all siblings on the right.
                            break
                    elif c == scan_start:
                        c._cached_fss = None
                        consider = True

                scan_start = par
                par = par.parent

        for x in elements:
            if x.has_problems:
                self._update_has_problems(x.has_problems and not removed)
                return

    def attach_child(self, slot: NodeSlot[Self, N], el: N, idx=None) -> N:
        a = slot.attr

        assert hasattr(self, a), f"Node {type(self).__name__} has no slot {a}"
        assert el is not None and slot.accepts(el), f"Slot {slot} cannot accept the node {el!r}"

        # If the newcomer is already attached to another parent, detach it first.
        if el.parent is not None:
            el.detach_self()

        if not slot.multi:
            if prev := getattr(self, a):
                prev.register_detachment()
            setattr(self, a, el)
        else:
            val = getattr(self, a)

            if idx is None:
                val.append(el)
            else:
                val.insert(idx, el)

        el.register_attachment(self, slot)

        self._children_updated(slot, (el, ), False)

        return el

    def detach_child(self, slot: NodeSlot[Self, N], idx=None) -> tuple[N, ...]:
        a = slot.attr

        assert hasattr(self, a), f"Node {type(self).__name__} has no slot {a}"
        assert slot.multi or idx is None, "Cannot a specific index node on a single slot."
        assert slot.optional, "Cannot detach a node from an non-optional slot."

        if slot.multi:
            el_list: list[N] = getattr(self, a)
            if idx is None:
                els = tuple(el_list)
                el_list.clear()
            else:
                els = (el_list.pop(idx),)
        else:
            el: InnerNode = getattr(self, a)
            els = (el,) if el else ()

        if len(els) == 0:
            return ()

        for el in els:
            el.register_detachment()

        self._children_updated(slot, els, True, idx)

        return els

    def get(self, slot: NodeSlot[Self, N]) -> list[N] | N | None:
        return getattr(self, slot.attr)

    # =========================
    # PROBLEMS MANAGEMENT
    # =========================

    def with_problems(self, *problems: InnerNodeProblem):
        l = len(self.problems)

        self.problems = problems

        if l != len(problems):
            self._update_has_problems()

        return self

    def add_problem(self, problem: InnerNodeProblem):
        assert problem is not None
        self.problems += (problem, )
        self._update_has_problems()

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

    def _init_single_slot(self, el: N, slot: SingleNodeSlot[Self, N]) -> N | None:
        assert (slot.optional and el is None) or slot.accepts(el), f"Slot {slot} cannot accept the node {el!r}"

        if el:
            setattr(self, slot.attr, el)
            el.register_attachment(self, slot)

            if el.has_problems: self._update_has_problems(True)

        return el

    def _init_multi_slot(self, el_list: Iterable[N], slot: MultiNodeSlot[Self, N]) -> list[N]:
        l = list(el_list)

        if l:
            for el in l:
                assert slot.accepts(el), f"Slot {slot} cannot accept the token {el!r}"
                el.register_attachment(self, slot)
                if el.has_problems: self._update_has_problems(True)

            self._children_updated(slot, l, False)

        setattr(self, slot.attr, l)

        return l

    def __str__(self):
        return self.pretty_str()


class LeafNode(Node):
    __slots__ = ("token", )

    def __init__(self, token: Token):
        assert token is not None
        self.token = token
        self.parent = None
        self.parent_slot = None
        self._cached_fss: int | None = None

    @property
    def full_text(self) -> str:
        return self.token.full_text

    @property
    def text(self) -> str:
        return self.token.text

    @property
    def pre_auxiliary(self) -> tuple[AuxiliaryText, ...]:
        return self.token.pre_auxiliary

    @property
    def kind(self) -> TokenKind:
        return self.token.kind

    @property
    def value(self) -> str | bool | int | float | None:
        """
        The value of the token. May be of three different types currently:
        - string: it's a string literal: "hello"
        - bool: it's a bool literal: true/false
        - int | float: it's a number. guess the type! it's either an int or float!
        """
        return self.token.value

    @property
    def children(self) -> Iterable["InnerNode"]:
        return []

    @property
    def children_reverse(self) -> Iterable["Node"]:
        return []

    @property
    def child_inner_nodes(self) -> Iterable["InnerNode"]:
        return []

    @property
    def child_nodes(self) -> Iterable["InnerNode"]:
        return []

    @property
    def has_problems(self) -> bool:
        return self.token.has_problems

    @property
    def problems(self) -> tuple[TokenProblem, ...]:
        return self.token.problems

    def __str__(self):
        return f"LeafNode({self.token})"

    def __repr__(self):
        return f"LeafNode({self.token!r})"


def leaf(t: Token | None):
    """
    Converts a token to a LeafNode. If the token is None, returns None.
    """
    return LeafNode(t) if t is not None else None

# ----------
# Base classes for statements and expressions
# ----------

class Statement(InnerNode):
    """
    A statement node, which can be an instruction or a declaration in the program.

    Examples:
        - variable declarations (int x = 5)
        - if/else blocks
        - while loops
    """
    pass


class Expression(InnerNode):
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

class Program(InnerNode):
    """
    The root node of the syntax tree, representing the entire program, containing all statements to
    be run when executing the program.
    """

    __slots__ = ("_statements", "_eof")

    statements_slot: MultiNodeSlot["Program", Statement] = MultiNodeSlot("_statements", Statement)
    eof_slot: SingleNodeSlot["Program", LeafNode] = SingleNodeSlot("_eof", LeafNode,
                                                                   check_func=lambda t: t.kind == TokenKind.EOF)

    def __init__(self, statements: Iterable[Statement], eof: LeafNode):
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
    def children(self) -> Iterable["InnerNode"]:
        yield from self.statements
        yield self.eof

    @property
    def child_inner_nodes(self) -> Iterable["InnerNode"]:
        return self._statements

Program.element_slots = (Program.statements_slot, Program.eof_slot)
Program.inner_node_slots = (Program.statements_slot, )

def _print_fancy_tree(n: Node, include_tokens=True, idt=0, idt_str="", is_last: bool = False):
    import re

    ascii_light_gray = "\033[37m"
    ascii_reset = "\033[0m"
    ascii_span_color = "\033[38;5;98m"
    ascii_inner_node_color = "\033[38;5;32m"
    ascii_leaf_node_color = "\033[38;5;35m"
    ascii_problem_color = "\033[38;5;166m"

    if idt == 0:
        branch = ""
    elif is_last:
        branch = "└── "
    else:
        branch = "├── "

    indentation = idt_str + branch

    color = ascii_inner_node_color if isinstance(n, InnerNode) else ascii_leaf_node_color
    header = color + (n.kind.name if isinstance(n, LeafNode) else type(n).__name__)
    if n.parent is not None:
        header += ascii_light_gray + f" ({n.parent_slot.name})"

    header += ascii_span_color + " " + str(n.span)
    header += ascii_reset

    line = indentation + header
    line_without_color = re.sub(r"\033\[[^m]*m", "", line)

    line += " " * (70 - len(line_without_color))
    line += n.text[:80].replace("\n", "\\n").replace("\t", "\\t")

    print(line)

    if idt == 0:
        child_indentation = idt_str
    elif not is_last:
        child_indentation = idt_str + "│   "
    else:
        child_indentation = idt_str + "    "

    if n.has_problems:
        print(child_indentation + ascii_problem_color + "Has problems: True" + ascii_reset)

    if n.problems:
        print(child_indentation + ascii_problem_color  + "Problems:", "".join(repr(x) for x in n.problems) + ascii_reset)

    children = list(n.children if include_tokens else n.child_inner_nodes)
    for i, c in enumerate(children):
        _print_fancy_tree(c, include_tokens, idt + 1, child_indentation, i == len(children) - 1)