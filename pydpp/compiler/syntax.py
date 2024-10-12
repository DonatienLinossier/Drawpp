from enum import Enum
from typing import Optional, Iterable

from pydpp.compiler import FileSpan
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

    __slots__ = ("pos", "is_fake")

    def __init__(self, pos: Optional[FileSpan] = None):
        self.pos = pos
        "The position of the node in the source code."

        self.is_fake = pos is not None and pos.start == pos.end
        """
        True when this is a 'fake node'.
        
        A fake node is a node that doesn't exist in the code, but is created artificially
        to "fix up" a broken node: like a missing operand, missing identifier...
        
        To create a fake node, its position must be of length 0.
        """

    @property
    def children(self) -> Iterable["Node"]:
        """
        Returns all children nodes of this node, from left to right order.
        Can return no nodes if the node has no children, which means it's a leaf node.

        This is a property! Just do ``node.children`` to get all children nodes.

        :return: all children nodes
        """
        return self._children()

    def _children(self) -> Iterable["Node"]:
        """
        Returns all children nodes of this node.

        This function should be overridden by all node classes that have children,
        so we can access them using the children property.

        :return: all children nodes
        """
        return []

    @property
    def is_leaf(self):
        """
        Returns True when this node is a leaf node, meaning it has no children.
        :return: True when it's a leaf node, False otherwise.
        """
        return next(iter(self.children), None) is None

    def __repr__(self):
        return f"{type(self).__name__}()"

    def __str__(self):
        return self.pretty_print()

    def pretty_print(self, indent: int =0):
        """
        Prints the node as a tree in a nice and indented way. Used in str(node).
        Nodes can have their own printing logic by creating a pretty_print(indent) function.
        :return: a string with the Node and its children
        """

        props = type(self).__slots__

        # If we have no properties, print out the name and go away
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
            append_indent(f"{p} = ")
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
# Nodes that don't fit into statements or expressions
# ----------

class Identifier(Node):
    """
    An identifier node, representing a name in the program, such as a variable name or a function name.

    Identifiers are composed of UTF-8 letters (belonging in the Unicode categories Ll, Lu, Lt, Lo, Lm,
    see ``string.isalpha``), underscores, and digits. An identifier cannot start with a digit.

    The identifier's name can be accessed using the ``name`` attribute, or by calling ``str(identifier_node)``.

    Identifiers may have an empty string to indicate that they are missing.
    """

    __slots__ = ("name",)

    def __init__(self, name: str, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.name = name
        "The name of the identifier. Contains UTF-8 letters, underscores and digits. Cannot start with a digit."

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"

    def __str__(self):
        return self.name

    def pretty_print(self, indent: int = 0):
        return f"Identifier({self.name!r})"


class BuiltInType(Node):
    """
    A built-in type specified using a keyword like int, bool...
    """

    __slots__ = ("kind",)

    def __init__(self, kind: BuiltInTypeKind, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.kind = kind
        "What built-in type it actually is: int, string, etc."

    def __repr__(self):
        return f"{type(self).__name__}({self.kind!r})"


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

    __slots__ = ("statements",)

    def __init__(self, statements: Iterable[Statement], pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.statements = list(statements)
        "A list of all statements to run when executing the program: variable/function declarations and instructions."

    def _children(self) -> Iterable[Node]:
        return self.statements

    def __repr__(self):
        return f"{type(self).__name__}(statements={self.statements!r})"


# ----------
# Statements
# ----------

class VariableDeclarationStmt(Node):
    """
    A variable declaration, with a type, identifier, and optional value.
    """

    __slots__ = ("type", "name", "value")

    def __init__(self, var_type: BuiltInType, name: Identifier, value: Optional[Expression],
                 pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.type = var_type
        "The type of the variable. (Currently built-in types only)"
        self.name = name
        "The name of the variable, as an Identifier."
        self.value = value
        "The value of the variable, can be None."

    @property
    def name_str(self) -> str:
        """
        Returns the name of the variable as a string, instead of using the identifier.
        :return: the string name of the variable
        """
        return self.name.name

    def _children(self) -> Iterable[Node]:
        return [self.type, self.name, self.value] if self.value is not None else [self.type, self.name]

    def __repr__(self):
        return f"{type(self).__name__}(type={self.type!r}, name={self.name!r}, value={self.value!r})"


class BlockStmt(Statement):
    """
    A block statement, which is a sequence of statements enclosed in curly braces.
    """

    __slots__ = ("statements",)

    def __init__(self, statements: Iterable[Statement], pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.statements = list(statements)
        "The list of statements in the block."

    def _children(self) -> Iterable[Node]:
        return self.statements

    def __repr__(self):
        return f"{type(self).__name__}(statements={self.statements!r})"


# Function declaration will be implemented later

class IfStmt(Statement):
    """
    An if statement, with [0..N] else/else-if blocks.
    """

    # Should we create an "ElseStmt" or keep it this way...?
    # Having a separate Else statement would make error reporting easier,
    # but the tree would be a bit weirder to manipulate.

    __slots__ = ("condition", "then_block", "else_statements")

    def __init__(self,
                 condition: Expression,
                 then_block: BlockStmt,
                 else_statements: Optional[Iterable["ElseStmt"]] = None,
                 pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.condition = condition
        "The condition to check for the if block."
        self.then_block = then_block
        "The block to run if the condition is true."
        self.else_statements = list(else_statements) if else_statements is not None else []
        """
        The list of else if and else blocks. The else block should be located last.
        An erroneous if statement might contain misplaced else/else-if blocks.
        """

    def _children(self) -> Iterable[Node]:
        yield self.condition
        yield self.then_block
        yield from self.else_statements

    def __repr__(self):
        return f"{type(self).__name__}(condition={self.condition!r}, then_block={self.then_block!r}, else_statements={self.else_statements!r})"

class ElseStmt(Statement):
    """
    An "else" or "else if" statement. Should be located inside an IfStmt.
    If located somewhere else, it's an error.
    """

    __slots__ = ("condition", "block")

    def __init__(self, condition: Optional[Expression], block: BlockStmt, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.condition = condition
        "If this is an 'else if' blocks, this is the condition to check. Else, if it's just an 'else' block, it's None."
        self.block = block
        "The block of statements to run when reaching this block."

    def _children(self) -> Iterable[Node]:
        return [self.condition, self.block] if self.condition is not None else [self.block]

    def __repr__(self):
        return f"{type(self).__name__}(condition={self.condition!r}, block={self.block!r})"

class WhileStmt(Statement):
    """
    A while loop, with a condition and a block of statements to run while the condition is true.
    """

    __slots__ = ("condition", "block")

    def __init__(self, condition: Expression, block: BlockStmt, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.condition = condition
        "The condition to check before running the block."
        self.block = block
        "The block of statements to run while the condition is true."

    def _children(self) -> Iterable[Node]:
        return [self.condition, self.block]

    def __repr__(self):
        return f"{type(self).__name__}(condition={self.condition!r}, block={self.block!r})"


class FunctionCallStmt(Statement):
    """
    A function call statement, which just contains a function call expression, and discards the
    return value of the function.
    """

    __slots__ = ("expr",)

    def __init__(self, expr: "FunctionExpr", pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.expr = expr
        "The function call expression to execute."

    def _children(self) -> Iterable[Node]:
        return [self.expr]

    def __repr__(self):
        return f"{type(self).__name__}(expr={self.expr!r})"


class AssignStmt(Statement):
    """
    A variable assignment statement, which assigns a value to an existing variable.
    """

    __slots__ = ("name", "value")

    def __init__(self, name: Identifier, value: Expression, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.name = name
        "The name of the variable to assign to."
        self.value = value
        "The value to assign to the variable."

    def _children(self) -> Iterable[Node]:
        return [self.name, self.value]

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r}, value={self.value!r})"

# ----------
# Expressions
# ----------

class NumberLiteralExpr(Expression):
    """
    A number literal expression, a number in the code with two parts: integer and decimal part.
    Examples: 4, 8.2, 0.99
    """

    __slots__ = ("int_part", "dec_part")

    def __init__(self, int_part: int, dec_part: Optional[int], pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.int_part = int_part
        "The integer part of the number.  Example: in 5.25, it's 5."
        self.dec_part = dec_part
        "The decimal part of the number, can be None if the number is purely an integer. Example: in 5.25, it's 25."

    def __repr__(self):
        return f"{type(self).__name__}(int_part={self.int_part!r}, dec_part={self.dec_part!r})"

    def pretty_print(self, indent: int = 0):
        if self.dec_part:
            return f"NumberLiteralExpr({self.int_part!r}.{self.dec_part!r})"
        else:
            return f"NumberLiteralExpr({self.int_part!r})"


class StringLiteralExpr(Expression):
    """
    A string literal expression, a sequence of characters enclosed in double quotes.
    """

    __slots__ = ("value",)

    def __init__(self, value: str, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.value = value
        "The string value inside the double quotes. Escaped characters are unescaped."

    def __repr__(self):
        return f"{type(self).__name__}(value={self.value!r})\n"

    def pretty_print(self, indent: int = 0):
        return f"StringLiteralExpr({self.value!r})"


class BoolLiteralExpr(Expression):
    """
    A boolean literal expression, either true or false.
    """

    __slots__ = ("value",)

    def __init__(self, value: bool, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.value = value
        "The boolean value, either True or False."

    def __repr__(self):
        return f"{type(self).__name__}(value={self.value!r})"

    def pretty_print(self, indent: int = 0):
        return f"BoolLiteralExpr({self.value!r})"


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

    __slots__ = ("left", "operator", "right")

    def __init__(self, left: Expression, operator: BinaryOperator, right: Expression, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.left = left
        "The left operand of the binary operation."
        self.operator = operator
        "The operator of the binary operation."
        self.right = right
        "The right operand of the binary operation."

    def _children(self):
        return [self.left, self.right]

    def __repr__(self):
        return f"{type(self).__name__}(left={self.left!r}, operator={self.operator!r}, right={self.right!r})"

class ParenthesizedExpr(Expression):
    """
    An expression enclosed in parentheses.
    """

    __slots__ = ("expr",)

    def __init__(self, expr: Expression, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.expr = expr
        "The expression enclosed in parentheses."

    def _children(self):
        return [self.expr]

    def __repr__(self):
        return f"{type(self).__name__}(expr={self.expr!r})"

class NotExpr(Expression):
    """
    A logical NOT expression, which negates the value of another expression.
    Example: NOT true
    """

    __slots__ = ("expr",)

    def __init__(self, expr: Expression, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.expr = expr
        "The expression to negate."

    def _children(self):
        return [self.expr]

    def __repr__(self):
        return f"{type(self).__name__}(expr={self.expr!r})"

class NegativeExpr(Expression):
    """
    An arithmetic negation expression, which flips the sign of the expression: -expr.
    Example: -(8+3)
    """

    __slots__ = ("expr",)

    def __init__(self, expr: Expression, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.expr = expr
        "The expression to negate."

    def _children(self):
        return [self.expr]

    def __repr__(self):
        return f"{type(self).__name__}(expr={self.expr!r})"

class FunctionExpr(Expression):
    """
    A function call expression, which calls a function with a list of arguments, and gives
    the return value of the function.
    """

    __slots__ = ("name", "arguments")

    def __init__(self, name: Identifier, arguments: Iterable[Expression], pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.name = name
        "The name of the function to call."
        self.arguments = list(arguments)
        "The list of arguments to pass to the function. Can be empty."

    def name_str(self) -> str:
        """
        Returns the name of the function as a string, instead of using the identifier.
        :return: the string name of the function
        """
        return self.name.name

    def _children(self) -> Iterable[Node]:
        return [self.name] + self.arguments

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r}, arguments={self.arguments!r})"

class VariableExpr(Expression):
    """
    A variable expression, returning the value of a variable.
    """

    __slots__ = ("name",)

    def __init__(self, name: Identifier, pos: Optional[FileSpan] = None):
        super().__init__(pos)
        self.name = name
        "The name of the variable, as an Identifier."

    @property
    def name_str(self) -> str:
        """
        Returns the name of the variable as a string, instead of using the identifier.
        :return: the string name of the variable
        """
        return self.name.name

    def _children(self) -> Iterable[Node]:
        return [self.name]

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r})"

    def pretty_print(self, indent: int = 0):
        return f"VariableExpr({self.name!r})"

class ErrorExpr(Expression):
    """
    An invalid/unrecognized expression. Prevents compilation. Has unknown type.
    """
    __slots__ = tuple()
    pass # No particular data