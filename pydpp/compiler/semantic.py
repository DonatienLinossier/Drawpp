import typing
from enum import Enum
from math import trunc

from pydpp.compiler.syntax import *


# ======================================================
# semantic.py: The semantic analyser
# ======================================================
# This is also where built-in functions and types are defined.
#
# The semantic analyser reads the entire program tree to look for node references (variables, functions...),
# and does type inference + checking to make sure types are correct (e.g. boolean in an if statement).
#
# Some nodes have semantic information attached to them, called Symbols.
# These Symbols are semantic informations (not syntaxic) of a variable, a function, ...
# A Symbol returns generally its name and its stype (and other informations).
# Multiple Symbol types exist, following the [Node]Sym pattern:
#     - FunctionSym: for function declarations
#     - ParameterSym: for function parameters
#     - VariableSym: for variable declarations
#     - ExpressionSym: for expressions
#     - AssignStmtSym: for assignation statements
#
# Each symbol contains the AST node it is linked to, in the "node" attribute.
#
# These symbols can be accessed by using the _to_sym maps (function_to_sym, variable_to_sym, etc.), stored
# in the final ProgramSemanticInfo. (Except for ParameterSym which can only be accessed from a function.)

class SemanticType(Enum):   # Enum : class allowing to structure groups of constants linked together
    """
    A built-in type in the language.
    """
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    CURSOR = "cursor"
    NOTHING = "nothing"  # like void in C? but a little bit more original?
    ERROR = "error"

    def __str__(self):
        return self.value  
        # this method allows to get the real type
        # ex :  1. without def __str__ :
        #           print(SemanticType.INT)    ->  return 'SemanticType.INT'
        #       2. with def __str__ :
        #           print(SemanticType.INT)    ->  return 'int'


class VariableSym:
    """
    Semantic information for a declared variable (global or local).
    Contains its type information.
    Supports built-in variables with constant values.
    """

    def __init__(self, name: str, type: SemanticType, node: VariableDeclarationStmt | None, builtin_val=None):
        # VariableDeclarationStmt : is the entire node (ex : int x = 5;, not only x or 5)
        self.name = name
        "The name of the variable."
        self.type = type
        "The type of the variable."
        self.node = node
        "The AST node this symbol is attached to. Can be None for built-in variables."
        self.built_in_val = builtin_val
        "The built-in value of the variable, if it's a constant. Can be None."

    def __str__(self):
        return f"VariableSym({self.name}, {self.type})"
        # return name and type of the var

class ParameterSym:
    """
    Semantic information for a function parameter.
    Contains its type information.
    """

    def __init__(self, name: str, type: SemanticType, node: FunctionParameter | None):
        self.name = name
        "The name of the parameter."
        self.type = type
        "The type of the parameter."
        self.node = node
        "The AST node this symbol is attached to."

    def __str__(self):
        return f"ParameterSym({self.name}, {self.type})"
        # return name and type of the function

class FunctionSym:
    """
    Semantic information for a function.
    Includes type information for parameters and return values. Supports built-in functions.
    """

    def __init__(self, name: str, return_type: SemanticType, parameters: list["ParameterSym"],
                 node: FunctionDeclarationStmt | None, c_func_name: str = None, doc: str | None = None):
        self.name = name
        "The name of the function."
        self.return_type = return_type
        "The return type of the function. Can be set to NOTHING if this function doesn't return anything."
        self.parameters = parameters
        "All parameters of this function, in order, as a list of ParameterSym."
        self.node = node
        "The AST node this symbol is attached to. Can be None for built-in functions."
        self.c_func_name = c_func_name 
        # ??
        "For built-in functions only: the name of the C/CTranslater function/instruction to call."
        self.doc = doc
        "Some documentation to guide users to use this function properly."

    def find_param(self, name: str) -> typing.Optional["ParameterSym"]:
        # This method can return :
        #   - a "ParameterSym" object
        #   - or None
        # typing.Optional is an alias provided by the typing module to express that a value can be of given type or None.
        # /!\ typing.Optional["ParameterSym"] is equivalent to Union["ParameterSym", None]
        """
        Finds a parameter symbol with the given name. Uses linear search in O(n).
        :param name: the name of the parameter
        :return: the parameter symbol
        """
        for p in self.parameters:
            if p.name == name:
                return p
        return None

    def __str__(self):
        params = ", ".join(str(p.type) + " " + p.name for p in self.parameters) # ", ".join(...) : combine all parameters strings separated them with ", "
        return f"FunctionSym({self.name}, {self.return_type}, [{params}])"
        # return name, type and parameters of the function

class ExpressionSym:
    """
    Semantic information for an expression.
    Contains its inferred type, and the symbol it references (when referencing a variable/parameter).
    """

    def __init__(self, type: SemanticType, referenced_symbol: typing.Optional["Sym"] = None):
        self.type = type
        "The type of the expression. Can be ERROR if the expression is invalid."
        self.referenced_symbol = referenced_symbol
        """
        The symbol this expression references, if any.
        Current possible referenced symbols:
            - VariableSym: value of a variable, with a VariableExpr node.
            - ParameterSym: value of a function parameter, with a VariableExpr node.
            - FunctionSym: a function call, with a FunctionExpr node.
        """

    def __str__(self):
        if self.referenced_symbol is not None:
            return f"ExpressionSym({self.type} -> {self.referenced_symbol.name})"
        else:
            return f"ExpressionSym({self.type})"

class AssignSym:
    """
    Semantic information for an assignment statement.
    Contains symbol references to the variable and the expression being assigned.
    """

    def __init__(self, variable: VariableSym | None, value: ExpressionSym | None, node: AssignStmt):
        self.variable = variable
        "The variable symbol being assigned to. Can be None when not found (invalid node)."
        self.value = value
        "The expression symbol being assigned to the variable. Can be None when there's no expression (invalid node)."
        self.node = node
        "The assignation node this symbol describes."

# Declare useful union types.
ValueSym = ParameterSym | VariableSym  # A value symbol, for VariableExpr
Sym = ParameterSym | VariableSym | FunctionSym | ExpressionSym | AssignSym  # Any symbol

##  # Création des tokens nécessaires
##  type_token = "int"  # Peut être un objet ou une chaîne selon la définition
##  name_tokenA = Token(kind="IDENTIFIER", value="x", text="int")  # Exemple de token pour "x"
##  assign_tokenA = Token(kind="ASSIGN", value="=", text="eq")  # Exemple de token pour "="
##  semi_colonA = Token(kind="SEMICOLON", value=";", text="semicolon")  # Exemple de token pour ";"
##  
##  # Création du nœud de déclaration
##  noeud = VariableDeclarationStmt(
##      type= BuiltInType(kind_token=leaf(Token(TokenKind.KW_INT, text="int"))),
##      name_token=leaf(Token(TokenKind.IDENTIFIER, text="x")),
##      assign_token=leaf(Token(TokenKind.SYM_ASSIGN, text="=")),
##      value=LiteralExpr(leaf(Token(TokenKind.LITERAL_NUM, text="50", value=50))),
##      semi_colon=leaf(Token(TokenKind.SYM_SEMICOLON, text=";"))
##  )
##  
##  symbole = VariableSym(name="x", type=SemanticType.INT, node=noeud)
##  print(symbole)

## param_1 = FunctionParameter(
##     type= BuiltInType(kind_token=leaf(Token(TokenKind.KW_INT, text="int"))),
##     name_token=leaf(Token(TokenKind.IDENTIFIER, text="p")),
##     comma=leaf(Token(TokenKind.SYM_COMMA, text=","))
## )
## symbole = ParameterSym(name="p", type=SemanticType.INT, node=param_1)
## print(symbole)


class ProgramSemanticInfo:
    """
    Contains all symbolic information about a program:
        - all global functions and variables, even built-in ones
        - semantic information for all nodes in the "_to_sym" maps: function_to_sym, variable_to_sym, expr_to_sym.
    """

    def __init__(self,
                 global_functions: dict[str, FunctionSym],
                 global_variables: dict[str, VariableSym],
                 function_to_sym: dict[FunctionDeclarationStmt, FunctionSym],
                 variable_to_sym: dict[VariableDeclarationStmt, VariableSym],
                 expr_to_sym: dict[Expression, ExpressionSym],
                 assign_to_sym: dict[AssignStmt, AssignSym],
                 canvas_width: int | None,
                 canvas_height: int | None):
        self.global_functions = global_functions
        "All declared global functions, including built-in ones."
        self.global_variables = global_variables
        "All declared global variables, including built-in ones."
        self.function_to_sym = function_to_sym
        "Semantic information for function nodes: function AST node -> function symbol."
        self.variable_to_sym = variable_to_sym
        "Semantic information for variable nodes: variable AST node -> variable symbol."
        self.expr_to_sym = expr_to_sym
        "Semantic information for expression nodes: expression AST node -> expression symbol."
        self.assign_to_sym = assign_to_sym
        "Semantic information for assignation nodes: assignation AST node -> assignation symbol."
        self.canvas_width = canvas_width
        "The width of the canvas, as set with the 'canvas' statement. Can be None."
        self.canvas_height = canvas_height
        "The height of the canvas, as set with the 'canvas' statement. Can be None."

    def print_debug(self):
        """
        Prints debug info for all symbols and declared members.
        """
        print("Global functions:")
        for k, v in self.global_functions.items():  # k=key, v=value
            left = k.ljust(45)                      # The ljust() method formats the string k by left-justifying it in a space of 45 characters.
            print(f"  {left} -> {v}")
        print("")

        print("Global variables:")
        for k, v in self.global_variables.items():
            left = k.ljust(45)
            print(f"  {left} -> {v}")
        print("")

        print("Function symbols:")
        for k, v in self.function_to_sym.items():
            left = f" {repr(k.text[:25])[1:-1]} @ {k.span}".ljust(45)   # Shows the position range (span) of the AST node in the source text, useful for locating the declaration.
            print(f"  {left} -> {v}")
        print("")

        print("Variable symbols:")
        for k, v in self.variable_to_sym.items():
            left = f" {repr(k.text[:25])[1:-1]} @ {k.span}".ljust(45)
            print(f"  {left} -> {v}")
        print("")

        print("Expression symbols:")
        for k, v in self.expr_to_sym.items():
            left = f" {repr(k.text[:25])[1:-1]} @ {k.span}".ljust(45)
            print(f"  {left} -> {v}")
        print("")

        print("Assignation symbols:")
        for k, v in self.assign_to_sym.items():
            left = f" {repr(k.text[:25])[1:-1]} @ {k.span}".ljust(45)
            print(f"  {left} -> {v}")


builtin_funcs = {
    "circle": FunctionSym(
        name="circle",
        return_type=SemanticType.NOTHING,
        parameters=[
            ParameterSym("r", SemanticType.FLOAT, None),
        ],
        c_func_name="cursorDrawCircle",
        node=None,
        doc="Dessine un cercle creux de rayon r autour du curseur."
    ),
    "circleFill": FunctionSym(
        name="circleFill",
        return_type=SemanticType.NOTHING,
        parameters=[
            ParameterSym("r", SemanticType.FLOAT, None),
        ],
        c_func_name="cursorDrawFilledCircle",
        node=None,
        doc="Dessine un cercle plein de rayon r autour du curseur."
    ),
    "jump": FunctionSym(
        name="jump",
        return_type=SemanticType.NOTHING,
        parameters=[
            ParameterSym("x", SemanticType.FLOAT, None),
            ParameterSym("y", SemanticType.FLOAT, None),
        ],
        c_func_name="cursorJump",
        node=None,
        doc="Déplace le curseur aux coordonnées (x, y)."
    ),
    "changeColor": FunctionSym(
        name="changeColor",
        return_type=SemanticType.NOTHING,
        parameters=[
            ParameterSym("r", SemanticType.INT, None),
            ParameterSym("g", SemanticType.INT, None),
            ParameterSym("b", SemanticType.INT, None),
            ParameterSym("a", SemanticType.INT, None),
        ],
        c_func_name="cursorChangeColor",
        node=None,
        doc="Change la couleur du curseur en utilisant les valeurs RGBA.\n"
            "r, g, b et a sont des entiers allant de 0 à 255, pour le rouge, vert, bleu et l'opacité."
    )
}

builtin_vars = {
    "PI": VariableSym("PI", SemanticType.FLOAT, None, 3.14159265358979323846),
}


def analyse(program: Program) -> ProgramSemanticInfo:
    """
    Runs semantic analysis on a program. Will make sure that all types are correct, that value are
    valid, and will list all functions and instructions to run when transpiling.

    :param program: The root node of the AST
    :param ps: The problem set to report any errors during semantic analysis
    :return: The semantic information of the program, to be given to the transpiler


    
    ============
    EXAMPLE :
    ============
    If the code is :
            canvas(500, 500);
            int x = 42;
            float y = x + 3.14;
    
    The current function ("analyse") will return a ProgramSemanticInfo object with :
            global_funcs :      containing "circle", "circleFill", "jump", "changeColor", "draw"
            global_vars :       containing PI (float), x (int) and y (float)
            function_to_sym :   assocy draw with its symbol
            expr_to_sym :       assocy x + 3.14 to float type
            canvas_width :      500
            canvas_height :     500

            
    Details of the execution :

    1.  1st instruction : "canvas(500, 500);"
        -> analyse function detects that we have a CanvasStmt
        -> Verificaion that dimensions of drawing space are "None" at the begining (canvas_width and canvas_height)
        -> canvas_width and canvas_height updated

    2.  2nd instruction "int x = 42;"
        -> Use the fonction "analyse_node" :
            -> Detection of variable declaration (VariableDeclarationStmt)
            -> call "register_variable" function :
                - check variable name presence (in variable_to_sym) and if the name is valid
                - Creation of the symbol for x with its name and value :
                        symbole = VariableSym(name="x", type_=BuiltInTypeKind.INT, node=stmt, value=42)
                - check if the variable is global (parent node is a program) or local.
                - check if the variable name is yet used :
                    In global case :    it checks presence in global_vars.
                    In local case :     it checks if an argument (args) has the same name
                - call "register_expression" function :
                    aim : check coherence type between the var and its value
                    --
                - variable added to dictionnary "variable_to_sym"

    3.  3rd instruction "float y = x + 3.14;"
        -> Use the fonction "analyse_node" :
            -> Detection of variable declaration (VariableDeclarationStmt)
            -> call "register_variable" function :
                - check variable name presence (in variable_to_sym) and if the name is valid
                - Creation of the symbol for y with its name and value :
                        symbole = VariableSym(name="y", type_=BuiltInTypeKind.FLOAT, node=stmt, value=42)
                - check if the variable is global (parent node is a program) or local.
                - check if the variable name is yet used :
                    In global case :    it checks presence in global_vars.
                    In local case :     it checks if an argument (args) has the same name
                - call "register_expression" function :
                    aim : check coherence type between the var and its value
                    --
                - variable added to dictionnary "variable_to_sym"
    """

    # Includes the builtin functions and variables.
    global_funcs: dict[str, FunctionSym] = dict(builtin_funcs)
    global_vars: dict[str, VariableSym] = dict(builtin_vars)

    # All maps linking nodes (of different kinds) to their symbols
    function_to_sym: dict[FunctionDeclarationStmt, FunctionSym] = {}
    variable_to_sym: dict[VariableDeclarationStmt, VariableSym] = {}
    expr_to_sym: dict[Expression, ExpressionSym] = {}
    assign_to_sym: dict[AssignStmt, AssignSym] = {}

    # The canvas size, if set.
    canvas_width, canvas_height = None, None

    # Adds an error regarding the given node. (We may change error systems later)
    def register_error(node: InnerNode, message: str, slot=None):
        node.add_problem(InnerNodeProblem(message, slot=slot))

    # Returns all the visible value inside a Node N.
    # If multiple value have the same name, the oldest will be lost.
    # TODO: Cache this function's results.
    def visible_variables_within(n: Node) -> dict[str, VariableSym]:
        # THE RULE
        # ---------------
        # A variable declaration V is visible by a Statement S if:
        #     - V is higher than or on the same level as S: height(V) <= height(S)
        #       --> this prevents value inside a block from being visible outside
        #
        #     - V is declared before S:                     pos(V) < pos(S^)
        #                                                   |   where S^ is the ancestor of S such that
        #                                                   |   parent(S^) = parent(V)
        #       --> obviously, we don't want to use value which weren't declared yet!
        #           Even if we're inside a variable declaration, we can't use it inside the default value.
        #
        # The idea is that:                                              (visible_vars(None) = {})
        #     visible_vars(n) = visible_vars(parent of n) + variable declarations before n
        #
        # If the N isn't a Statement, we'll use its ancestor statement — the closest parent statement.
        n = n.ancestor(Statement, include_self=True)
            # A statement node, which can be an instruction or a declaration in the program.
            # Examples: - variable declarations (int x = 5)
            #           - if/else blocks
            #           - while loops
            #           - function block
        if n is None:
            return dict()

        # If this statement is a function, we can't see declared global variables, only local ones
        # and built-in variables. Stop there.
        if isinstance(n, FunctionDeclarationStmt):
            return builtin_vars

        # Else, if this statement is a "root" statement, use the global variables value,
        # it already contains all variables registered until now.
        if n.parent is program:
            return global_vars

        # List all the values there
        variables: dict[str, VariableSym] = {}      # empty dictionnary of variable : will collect all variables visible in the context of n

        # Add all the visible value of the parent. If the parent isn't a statement, we're
        # going to use statement ancestor anyway.
        variables |= visible_variables_within(n.parent)

        # Add all the variable declarations before this statement.
        # Don't do anything if we're the only child, of course.
        if n.parent_slot.multi:
            for i, c in enumerate(n.parent.get(n.parent_slot)):
                if n.parent_slot_idx == i:
                    break

                if isinstance(c, VariableDeclarationStmt):
                    variables[c.name_token_str] = variable_to_sym[c]

        return variables

    # Returns all the function arguments this node N can "see".
    # TODO: Cache this function's results.
    def visible_arguments_within(n: Node) -> dict[str, ParameterSym]:
        # Just get the closest parent function, and return its arguments. Easy.
        n = n.ancestor(FunctionDeclarationStmt, include_self=True)
        if n is None:
            return dict()

        return {p.name: p for p in function_to_sym[n].parameters}

    # Union of variables + arguments.
    # TODO: Cache this function's results.
    def visible_values_within(n: Node) -> dict[str, ValueSym]:
        # Arguments take precedence over variables.
        return visible_variables_within(n) | visible_arguments_within(n)
            # We return a fusion dictionnary containing arguments and variables accessible in the context of n

    # Finds a function with the given name. None if not found.
    def find_function(f: str | None) -> FunctionSym | None:
        return global_funcs.get(f, None)

    # Finds a visible variable of name v, from the node's point of view.
    def find_visible_variable(v: str | None, pov: Node) -> VariableSym | None:
        if v is None:
            return None

        visible_vars = visible_variables_within(pov)
        return visible_vars.get(v, None)

    # Finds a visible argument of name a, from the node's point of view.
    def find_visible_argument(a: str | None, pov: Node) -> ParameterSym | None:
        if a is None:
            return None

        visible_args = visible_arguments_within(pov)
        return visible_args.get(a, None)

    # Returns True when the type is INT or FLOAT.
    def is_numeric_type(k: SemanticType):
        return k == SemanticType.INT or k == SemanticType.FLOAT

    # Does type inference and checking for an expression — and its children — recursively.
    # Registers a symbol (ExpressionSym) for this expression, including its children, even if errored.
    def register_expression(e: Expression | None) -> ExpressionSym:
        """
            This function is used to analyse a node of the AST and :
                - Identify the expression type (int, float ...)
                - verify validity (variables and fonctioons used are defined,  types are compatibles)
                - assocy expresion  to a semantic symbol, it's to say an instance of ExpressionSym ( ... )
        """
        # Make up an error type for non-existing expressions.
        if e is None:
            return ExpressionSym(SemanticType.ERROR)

        # If we have already registered this expression, just return it. We avoid to do same thing.
        if e in expr_to_sym:
            return expr_to_sym[e]

        if isinstance(e, LiteralExpr):
            # The type of a literal is the type of the literal itself.
            expr_to_sym[e] = ExpressionSym(to_builtin_type(e.token))
                # e.token :                     is a LeafNode (with e a LiteralExpr)
                # to_builtin_type(e.token) :    returns the type of the node (int, float, char ... because LitteralExpr)
        elif isinstance(e, ErrorExpr):
            # An error expression, is well, of error type.
            expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
        elif isinstance(e, UnaryExpr):
            # A unary expression is an expression with a NOT/- operator before it.
            # Example: NOT true
            operand_sym = register_expression(e.expr)   #analyse the sub-expression without the operator before (- or NOT)

            # When our operand is an error, just give up.
            if operand_sym.type == SemanticType.ERROR:
                expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
                return expr_to_sym[e]

            match e.op_token.kind:
                case TokenKind.SYM_MINUS:
                    # Minus -> The operand must be numeric. If not, this will be of error type.
                    if is_numeric_type(operand_sym.type):
                        expr_to_sym[e] = ExpressionSym(operand_sym.type)
                    else:
                        register_error(e, "L'opérateur « − » ne peut être utilisé que sur des nombres (entiers ou décimaux).")
                        expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)

                case TokenKind.KW_NOT:
                    # Not -> Can only be a boolean.
                    if operand_sym.type == SemanticType.BOOL:
                        expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
                    else:
                        register_error(e, "L'opérateur « not » ne peut être utilisé que sur des booléens.")
                        # The type of not x is always boolean, so we don't need to error out here.
                        expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
        elif isinstance(e, ParenthesizedExpr):
            # A parenthesized one, just need to use the type of the child.
            # Will be an ERROR if e.expr is None
            expr_to_sym[e] = register_expression(e.expr)    # analyse the expression inside parentheses
                # e.expr : expression inside the parentheses
        elif isinstance(e, BinaryOperationExpr):
            # A binary operation expression, following this pattern: left [operator] right.
            # Where [operator] is a binary operator in the ``BinaryOperator`` enum.
            # Examples:     5 + 8 ; left = 5, operator = ADD, right = 8
            #               8 * 6 ; left = 8, operator = MUL, right = 6
            left_sym = register_expression(e.left)
            right_sym = register_expression(e.right)

            # If one of them is erroneous, I don't want to waste time on what might have
            # 90% chances of being a useless error message.
            if left_sym.type == SemanticType.ERROR or right_sym.type == SemanticType.ERROR:
                expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
                return expr_to_sym[e]

            match e.operator_token.kind:        # e.operator_token.kind : is the type of the operator token (e.operator_token is LeafNode)
                case TokenKind.KW_OR | TokenKind.KW_AND:
                    # OR and AND -> Both operands must be boolean.
                    if left_sym.type == SemanticType.BOOL and right_sym.type == SemanticType.BOOL:
                        expr_to_sym[e] = ExpressionSym(SemanticType.BOOL)
                    else:
                        register_error(e,
                                       "Les opérateurs « or » et « and » ne peuvent être utilisés que sur des booléens.")
                        expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
                case TokenKind.SYM_EQ | TokenKind.SYM_NEQ:
                    # EQ (==) and NEQ (!=) -> Both operands must be the same type
                    #               OR they're both numeric, in which case we're going to convert to float.
                    if left_sym.type == right_sym.type or (
                            is_numeric_type(left_sym.type) and is_numeric_type(right_sym.type)):
                        expr_to_sym[e] = ExpressionSym(SemanticType.BOOL)
                    else:
                        op_name = "==" if e.operator_token.kind == TokenKind.SYM_EQ else "!="
                        register_error(e,
                                       f"Impossible d'utiliser l'opérateur « {op_name} » avec les types {left_sym.type} et {right_sym.type}.")
                        expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
                case TokenKind.SYM_LT | TokenKind.SYM_LEQ | TokenKind.SYM_GT | TokenKind.SYM_GEQ:
                    # Numerical comparison -> both numeric
                    if is_numeric_type(left_sym.type) and is_numeric_type(right_sym.type):
                        expr_to_sym[e] = ExpressionSym(SemanticType.BOOL)
                    else:
                        op_name = e.operator_token.text
                        register_error(e,
                                       f"Impossible d'utiliser l'opérateur « {op_name} » avec les types {left_sym.type} et {right_sym.type}.")
                        # Always a boolean, no need to put an error type here.
                        expr_to_sym[e] = ExpressionSym(SemanticType.BOOL)
                case TokenKind.SYM_PLUS | TokenKind.SYM_MINUS | TokenKind.SYM_STAR | TokenKind.SYM_SLASH:
                    # Arithmetic operation -> both numeric
                    if is_numeric_type(left_sym.type) and is_numeric_type(right_sym.type):
                        # If one of them is a float, the result will be a float.
                        if left_sym.type == SemanticType.FLOAT or right_sym.type == SemanticType.FLOAT:
                            expr_to_sym[e] = ExpressionSym(SemanticType.FLOAT)
                        else:
                            expr_to_sym[e] = ExpressionSym(SemanticType.INT)
                    else:
                        op_name = e.operator_token.text
                        register_error(e,
                                       f"Impossible d'utiliser l'opérateur « {op_name} » avec les types {left_sym.type} et {right_sym.type}.")
                        expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
        elif isinstance(e, VariableExpr):
            # Variable expression. Make sure the variable/value actually exists.
            value_syms = visible_values_within(e)
            if e.name_token_str not in value_syms:
                # It doesn't exist! Well, exactly, we can't *see* it.
                # Let's write a well-suited error message.
                if e.name_token_str not in global_vars or e.ancestor(FunctionDeclarationStmt) is None:
                    # We just can't see that variable. It likely doesn't exist yet.
                    register_error(e, f"La variable {e.name_token_str} n'est pas encore définie.")
                else:
                    # We're a child of a function declaration, and we're trying to access a global variable.
                    register_error(e, "Impossible d'utiliser une variable globale dans une fonction.")
                expr_to_sym[e] = ExpressionSym(SemanticType.ERROR)
            else:
                # Take the type of the variable!
                v = value_syms[e.name_token_str]
                expr_to_sym[e] = ExpressionSym(v.type, v)
        elif isinstance(e, FunctionExpr):
            # Function call expression. Does the function exist? Are its arguments correct? Let's see...
            func = find_function(e.identifier_token_str)
            if not func:
                register_error(e, f"La fonction {e.identifier_token_str} n'est pas définie.")
                expr_to_sym[e] = ExpressionSym(SemanticType.ERROR, func)
            else:
                # We obviously know the return type.
                expr_to_sym[e] = ExpressionSym(func.return_type, func)

                # Now, let's gather and check the arguments
                given_args = list(e.arg_list.arguments) # arguments given to the function
                params = func.parameters                # parameters of the function
                common = min(len(params), len(given_args))

                # Compare if there is too much or too few, complain!
                if len(params) > len(given_args):
                    register_error(e,
                                   f"Trop peu d'arguments ont été donnés à la fonction {func.name} : {len(given_args)} donnés, {len(params)} attendus.")
                elif len(params) < len(given_args):
                    register_error(e,
                                   f"Trop d'arguments ont été donnés à la fonction {func.name} : {len(given_args)} donnés, {len(params)} attendus.")

                # Register all the argument expressions, and register some errors if the types don't match.
                for i in range(0, len(given_args)):
                    arg = given_args[i]
                    if arg.expr is not None:
                        arg_sym = register_expression(arg.expr)
                        if i < common and arg_sym.type != SemanticType.ERROR and not is_subtype(arg_sym.type,
                                                                                                   params[i].type):
                            register_error(arg,
                                           f"L'argument {i + 1} de l'appel à « {func.name} » est du mauvais type : {arg_sym.type} donné, {params[i].type} attendu.")

                # See if the wield expression is correct. Expression missing is already taken care of by the parser.
                if e.wield_token is not None and e.wielded_expr is not None:
                    we_sym = register_expression(e.wielded_expr)
                    if we_sym.type != SemanticType.CURSOR and we_sym.type != SemanticType.ERROR:
                        register_error(e.wielded_expr,
                                       f"La valeur donnée à « wield » doit être un curseur ({we_sym.type} donné).")
        else:
            raise NotImplementedError(f"Expression type {type(e)} not implemented yet.")

        return expr_to_sym[e]

    # Transforms a literal/type token (bool, int, float, "hell", 81, etc.) into the SemanticType enum.
    # Returns the "default" arg if there's no token, or if it's invalid.
    def to_builtin_type(t: LeafNode | BuiltInType | None, default=SemanticType.ERROR) -> SemanticType:
        """
            This function returns the type of the LeafNode t in parameter.
        """
        if t is None:
            return default

        if isinstance(t, BuiltInType):
            t = t.kind_token
        # now t is necessary a LeafNode

        match t.kind:       #t.kind : kind of the token (cf TokenKind class in tokenizer.py)
            case TokenKind.KW_BOOL | TokenKind.LITERAL_BOOL:
                return SemanticType.BOOL
            case TokenKind.KW_INT:
                return SemanticType.INT
            case TokenKind.KW_FLOAT:
                return SemanticType.FLOAT
            case TokenKind.KW_STRING | TokenKind.LITERAL_STRING:
                return SemanticType.STRING
            case TokenKind.LITERAL_NUM:
                # Integer -> int
                # Float -> float
                if isinstance(t.value, int):
                    return SemanticType.INT
                else:
                    return SemanticType.FLOAT
            case TokenKind.KW_CURSOR:
                return SemanticType.CURSOR
            case _:
                return default

    # Returns True when a <: b, meaning that a is a subtype of b OR both are same type.
    # In other words, whenever this assignment is valid:
    #    b = a;
    #
    # Usage example: My variable of type T wants to know if it can accept a value of type V:
    #     => is_subtype(V, T)
    def is_subtype(a: SemanticType, b: SemanticType) -> bool:
        if a == b:
            return True
        if a == SemanticType.INT and b == SemanticType.FLOAT:
            # Currently, we have automatic float -> int conversion
            return True
        return False

    def register_variable(v: VariableDeclarationStmt):
        if v in variable_to_sym:
            # Already registered
            return

        if v.name_token is None or not v.name_token_str:
            # Invalid name, already reported by the parser
            return

        # Make the variable symbol, with the name and type.
        name = v.name_token_str
        ty = to_builtin_type(v.type)
        symbol = VariableSym(name, ty, v)

        # I wonder how that is possible...
        if ty == SemanticType.ERROR:
            register_error(v, "Type de variable inconnu.")

        if v.parent is program:
            # This is a global variable!
            if name in global_vars:
                register_error(v, f"La variable {name} est déjà définie.")

            global_vars[v.name_token_str] = symbol
        else:
            # It's a local variable. We allow variable redefinition (shadowing) there.
            # But we need to check that it doesn't have the same name as an argument!
            args = visible_arguments_within(v)
            if name in args:
                # TODO: Better err message
                register_error(v, f"La variable locale {name} est déjà définie en tant que paramètre de la fonction ... .")

        if v.value is not None and ty != SemanticType.ERROR:
            # If there's a default value, check that it's of the correct type.
            value_sym = register_expression(v.value)
            if not is_subtype(value_sym.type, ty) and value_sym.type != SemanticType.ERROR:
                # exple :
                #   int x = 5.3;
                # => x is int, 5.3 is float
                # => We have is_subtype(float, int) that returns FALSE because float is not a subtype of int (it is the contrary)
                register_error(v.value,
                               f"La valeur donnée pour la variable {name} est du mauvais type : {value_sym.type} donné, {ty} attendu.")

        # Cursor variables are special. They're always initialised with a cursor by default,
        # and they can't be changed afterward.
        if v.value is not None and ty == SemanticType.CURSOR:
            register_error(v, "Impossible d'initialiser un curseur avec une valeur : "
                              "les curseurs sont déjà initialisés lorsqu'ils sont déclarés.")

        variable_to_sym[v] = symbol

    def register_function(f: FunctionDeclarationStmt):
        name_valid = f.name_token is not None

        # Is the function yet declared ?
        pre_existing = find_function(f.name_token_str)
        if pre_existing:
            register_error(f, f"La fonction {f.name_token_str} est déjà définie.")

        params: list[ParameterSym] = []
        for p in f.parameters:
            if p.name_token is None:
                register_error(p, "Nom de paramètre invalide.")
                continue

            ty = to_builtin_type(p.type)    # This function returns the type of the parameter.
            if ty == SemanticType.ERROR:
                register_error(p, "Type de paramètre inconnu.")
                # Don't return, it's okay

            # Make sure the parameter name isn't already used before.
            if not any(1 for x in params if x.name == p.name_token_str):
                params.append(ParameterSym(p.name_token_str, ty, p))
            else:
                register_error(p, f"Le paramètre {p.name_token_str} est déjà défini.")

        function_to_sym[f] = FunctionSym(
            name=f.name_token_str,
            return_type=SemanticType.NOTHING,  # TODO: Consider adding support for return types?
            parameters=params,
            node=f
        )

        # Register it to the map of all functions if we got a valid name and no duplicates.
        if name_valid and pre_existing is None:
            global_funcs[f.name_token_str] = function_to_sym[f]

    def analyse_node(n: InnerNode):
        analyse_children = True

        if isinstance(n, VariableDeclarationStmt):
            # We have a variable decl: register it, and don't re-read children further down.
            register_variable(n)
            analyse_children = False
        elif isinstance(n, FunctionDeclarationStmt):
            # We have a function decl: functions are already declared at the beginning of the analysis,
            # so let's not read it again.
            # However, we will still analyse its children, as registering a function does NOT analyse its block.

            # Oh, and, if we're trying to declare a function within a function/if/while/etc., don't.
            if n.parent is not program:
                register_error(n, "Les fonctions ne peuvent être déclarées que globalement.")
        elif isinstance(n, IfStmt) or isinstance(n, WhileStmt) or isinstance(n, ElseStmt):
            # We have a branching statement (if/while/else/else if): make sure that the condition
            # is a boolean.
            # Condition might be None for else statements.
            if n.condition is not None:
                cond_sym = register_expression(n.condition)
                if cond_sym.type != SemanticType.BOOL and cond_sym.type != SemanticType.ERROR:
                    register_error(n.condition, "La condition doit être un booléen.")
        elif isinstance(n, AssignStmt):
            # We have an assignation statement: check that its variable exists, and that the assigned value
            # is of the right type. Also register a symbol for it.

            # Ensure that the variable (not a parameter!) exist.
            var_sym = find_visible_variable(n.name_token_str, n)
                # return a VariableSym if the node n is a visible variable (a variable defined),
                # else return None

            # It doesn't? Report it.
            if var_sym is None:
                register_error(n, f"La variable {n.name_token_str} n'est pas définie.",
                               slot=AssignStmt.name_token_slot)
            elif find_visible_argument(n.name_token_str, n) is not None:    # return a ParameterSym if the node n is a visible parameter (a parameter defined), else return None
                # It's a parameter. We don't allow assigning to parameters right now, so report it to the user!
                register_error(n, f"Impossible de modifier la valeur du paramètre {n.name_token_str}.",
                               slot=AssignStmt.name_token_slot)
            elif var_sym.built_in_val is not None:
                # It's a built-in variable, we can't change its value.
                register_error(n, f"Impossible de modifier la valeur de la constante {n.name_token_str}.",
                               slot=AssignStmt.name_token_slot)

            if n.value is not None:
                val_sym = register_expression(n.value)
                # Check that the assign value is of the correct type, only if we have a variable found.
                if var_sym and val_sym.type != SemanticType.ERROR and not is_subtype(val_sym.type, var_sym.type):
                    register_error(n.value,
                                   f"La valeur assignée à la variable {n.name_token_str} est du mauvais type : {val_sym.type} donné, {var_sym.type} attendu.")
            else:
                val_sym = None

            # Cursor variables are special. They're always initialised with a cursor by default,
            # and they can't be changed afterward.
            if var_sym is not None and var_sym.type == SemanticType.CURSOR:
                register_error(n, "Impossible d'assigner une valeur à un curseur.")

            # Register a symbol for this assignation. (var_sym & val_sym can be None)
            assign_to_sym[n] = AssignSym(var_sym, val_sym, n)

            # No need to analyse children, we've already done the work.
            analyse_children = False
        elif isinstance(n, WieldStmt):
            # Within a wield statement, we just need to check that the wielded value is in fact a cursor.
            if n.expr is not None:
                we_sym = register_expression(n.expr)
                if we_sym.type != SemanticType.CURSOR and we_sym.type != SemanticType.ERROR:
                    register_error(n.expr, f"La valeur d'un bloc « wield » doit être un curseur ({we_sym.type} donné).")

            # Do analyse other children though.
        elif isinstance(n, CanvasStmt):
            # The canvas statement is a bit special.
            # It must be at the very start of the program, and we can't have more than one.
            if n.parent is None or n.parent_slot_idx != 0:
                # But, do we have duplicate canvas statements? Let's see...
                is_duplicate = False
                for s in program.statements:
                    if s is n:
                        break
                    elif isinstance(s, CanvasStmt):
                        is_duplicate = True
                        break

                if is_duplicate:
                    register_error(n, "La directive « canvas » a déjà été déclarée précédemment.")
                else:
                    register_error(n, "La directive « canvas » doit être placé au début du programme.")
            else:
                # The parser already tells error messages if the width/height is invalid.
                # So we'll just change the variables accordingly
                nonlocal canvas_width, canvas_height

                # Only set the dimensions if they're valid.
                def evaluate(e: Expression):
                    return e.token.value if e is not None \
                                            and isinstance(e, LiteralExpr) \
                                            and isinstance(e.token.value, int) \
                                            and e.token.value > 0 else None

                canvas_width = evaluate(n.width)
                canvas_height = evaluate(n.height)
        elif isinstance(n, Expression):
            # We have an expression... Just register it. Although this part of the code might be called
            # rarely since expression are already registered by function calls/variable assignation, etc.
            register_expression(n)

            # No need to analyse children, register_expression does that for us.
            analyse_children = False

        # Traverse all children — if necessary — to in turn analyse them, in depth-first order.
        if analyse_children:
            for child in n.child_inner_nodes:
                analyse_node(child)

    # First register all functions so we can use them even before declaring them.
    for ch in program.child_inner_nodes:
        if isinstance(ch, FunctionDeclarationStmt):
            register_function(ch)

    # Register anything else step by step, in a depth-first fashion, so we don't get variables we shouldn't
    # have known about.
    for ch in program.child_inner_nodes:
        analyse_node(ch)

    # Make up the final semantic info structure with all the symbols we've gathered!
    return ProgramSemanticInfo(
        global_functions=global_funcs,
        global_variables=global_vars,
        function_to_sym=function_to_sym,
        variable_to_sym=variable_to_sym,
        expr_to_sym=expr_to_sym,
        assign_to_sym=assign_to_sym,
        canvas_width=canvas_width,
        canvas_height=canvas_height
    )