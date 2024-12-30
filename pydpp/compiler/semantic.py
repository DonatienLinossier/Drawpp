import typing
from math import trunc

from pydpp.compiler.syntax import *
from pydpp.compiler.types import BuiltInTypeKind


# ======================================================
# semantic.py: The semantic analyser
# ======================================================
# This is also where built-in functions and types are defined.

class FunctionSym:
    def __init__(self, name: str, return_type: BuiltInTypeKind, parameters: list["ParameterSym"],
                 node: FunctionDeclarationStmt | None, c_func_name: str = None):
        self.name = name
        self.return_type = return_type
        self.parameters = parameters
        self.node = node
        self.c_func_name = c_func_name

    def find_param(self, n: str) -> typing.Optional["ParameterSym"]:
        for p in self.parameters:
            if p.name == n:
                return p
        return None

    def __str__(self):
        params = ", ".join(str(p.type) + " " + p.name for p in self.parameters)
        return f"FunctionSym({self.name}, {self.return_type}, [{params}])"

class VariableSym:
    def __init__(self, name: str, type: BuiltInTypeKind, node: VariableDeclarationStmt | None, builtin_val = None):
        self.name = name
        self.type = type
        self.node = node
        self.built_in_val = builtin_val

    def __str__(self):
        return f"VariableSym({self.name}, {self.type})"

class ParameterSym:
    def __init__(self, name: str, type: BuiltInTypeKind, node: FunctionParameter | None):
        self.name = name
        self.type = type
        self.node = node

    def __str__(self):
        return f"ParameterSym({self.name}, {self.type})"

class ExpressionSym:
    def __init__(self, type: BuiltInTypeKind, referenced_symbol: typing.Optional["Sym"] = None):
        self.type = type
        self.referenced_symbol = referenced_symbol

    def __str__(self):
        if self.referenced_symbol is not None:
            return f"ExpressionSym({self.type} -> {self.referenced_symbol.name})"
        else:
            return f"ExpressionSym({self.type})"

# Declare useful union types.
ValueSym = ParameterSym | VariableSym
Sym = ParameterSym | VariableSym | FunctionSym | ExpressionSym

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
                 expr_to_sym: dict[Expression, ExpressionSym]):

        self.global_functions = global_functions
        self.global_variables = global_variables
        self.function_to_sym = function_to_sym
        self.variable_to_sym = variable_to_sym
        self.expr_to_sym = expr_to_sym

    def print_debug(self):
        print("Global functions:")
        for k, v in self.global_functions.items():
            left = k.ljust(45)
            print(f"  {left} -> {v}")
        print("")

        print("Global variables:")
        for k, v in self.global_variables.items():
            left = k.ljust(45)
            print(f"  {left} -> {v}")
        print("")

        print("Function symbols:")
        for k, v in self.function_to_sym.items():
            left = f" {repr(k.text[:25])[1:-1]} @ {k.span}".ljust(45)
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


builtin_funcs = {
    "circle": FunctionSym(
        name="circle",
        return_type=BuiltInTypeKind.NOTHING,
        parameters=[
            ParameterSym("x", BuiltInTypeKind.FLOAT, None),
            ParameterSym("y", BuiltInTypeKind.FLOAT, None),
            ParameterSym("r", BuiltInTypeKind.FLOAT, None),
        ],
        c_func_name="drawpp_circle",
        node=None
    )
}

builtin_vars = {
    "PI": VariableSym("PI", BuiltInTypeKind.FLOAT, None, 3.14159265358979323846),
}


def analyse(program: Program) -> ProgramSemanticInfo:
    """
    Runs semantic analysis on a program. Will make sure that all types are correct, that value are
    valid, and will list all functions and instructions to run when transpiling.

    :param program: The root node of the AST
    :param ps: The problem set to report any errors during semantic analysis
    :return: The semantic information of the program, to be given to the transpiler
    """

    # Includes the builtin functions and variables.
    global_funcs: dict[str, FunctionSym] = dict(builtin_funcs)
    global_vars: dict[str, VariableSym] = dict(builtin_vars)

    # All functions node to their symbols
    function_to_sym: dict[FunctionDeclarationStmt, FunctionSym] = {}
    variable_to_sym: dict[VariableDeclarationStmt, VariableSym] = {}
    expr_to_sym: dict[Expression, ExpressionSym] = {}

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
        if n is None:
            return dict()

        # If this statement is a "root" statement, use the global value
        if n.parent is program:
            return global_vars

        # List all the values there
        variables: dict[str, VariableSym] = {}

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

    def find_function(f: str | None) -> FunctionSym | None:
        if f is None:
            return None

        if f in global_funcs:
            return global_funcs[f]
        elif f in builtin_funcs:
            return builtin_funcs[f]

    def find_visible_variable(v: str | None, pov: Node) -> VariableSym | None:
        if v is None:
            return None

        visible_vars = visible_values_within(pov)
        return visible_vars.get(v, None)

    def is_numeric_type(k: BuiltInTypeKind):
        return k == BuiltInTypeKind.INT or k == BuiltInTypeKind.FLOAT

    def register_expression(e: Expression) -> ExpressionSym:
        # If we have already registered this expression, just return it.
        if e in expr_to_sym:
            return expr_to_sym[e]

        if isinstance(e, LiteralExpr):
            # The type of a literal is the type of the literal itself.
            expr_to_sym[e] = ExpressionSym(to_builtin_type(e.token))
        elif isinstance(e, ErrorExpr):
            # An error expression, is well, of error type.
            expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
        elif isinstance(e, UnaryExpr):
            # We have either a +EXPR or not EXPR.
            operand_sym = register_expression(e)

            # When our operand is an error, just give up.
            if operand_sym.type == BuiltInTypeKind.ERROR:
                expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
                return expr_to_sym[e]

            match e.op_token.kind:
                case TokenKind.SYM_MINUS:
                    # Minus -> The operand must be numeric. If not, this will be of error type.
                    if operand_sym.type == BuiltInTypeKind.INT or operand_sym.type == BuiltInTypeKind.FLOAT:
                        expr_to_sym[e] = ExpressionSym(operand_sym.type)
                    else:
                        register_error(e, "L'opérateur « − » ne peut être utilisé que sur des nombres.")
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)

                case TokenKind.KW_NOT:
                    # Not -> Can only be a boolean.
                    if operand_sym.type == BuiltInTypeKind.BOOL:
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
                    else:
                        register_error(e, "L'opérateur « not » ne peut être utilisé que sur des booléens.")
                        # The type of not x is always boolean, so we don't need to error out here.
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
        elif isinstance(e, ParenthesizedExpr):
            # A parenthesized one, just need to use the type of the child.
            expr_to_sym[e] = register_expression(e.expr)
        elif isinstance(e, BinaryOperationExpr):
            # Binary operation. Oh boy. Lots of stuff to cover!
            left_sym = register_expression(e.left)
            right_sym = register_expression(e.right)

            # If one of them is erroneous, I don't want to waste time on what might have
            # 90% chances of being a useless error message.
            if left_sym.type == BuiltInTypeKind.ERROR or right_sym.type == BuiltInTypeKind.ERROR:
                expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
                return expr_to_sym[e]

            match e.operator_token.kind:
                case TokenKind.KW_OR | TokenKind.KW_AND:
                    # OR and AND -> Both operands must be boolean.
                    if left_sym.type == BuiltInTypeKind.BOOL and right_sym.type == BuiltInTypeKind.BOOL:
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.BOOL)
                    else:
                        register_error(e, "Les opérateurs « or » et « and » ne peuvent être utilisés que sur des booléens.")
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
                case TokenKind.SYM_EQ | TokenKind.SYM_NEQ:
                    # EQ and NEQ -> Both operands must be the same type
                    #               OR they're both numeric, in which case we're going to convert to float.
                    if left_sym.type == right_sym.type or (is_numeric_type(left_sym.type) and is_numeric_type(right_sym.type)):
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.BOOL)
                    else:
                        op_name = "==" if e.operator_token.kind == TokenKind.SYM_EQ else "!="
                        register_error(e, f"Impossible d'utiliser l'opérateur « {op_name} » avec les types {left_sym.type} et {right_sym.type}.")
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
                case TokenKind.SYM_LT | TokenKind.SYM_LEQ | TokenKind.SYM_GT | TokenKind.SYM_GEQ:
                    # Numerical comparison -> both numeric
                    if is_numeric_type(left_sym.type) and is_numeric_type(right_sym.type):
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.BOOL)
                    else:
                        op_name = e.operator_token.text
                        register_error(e,
                                       f"Impossible d'utiliser l'opérateur « {op_name} » avec les types {left_sym.type} et {right_sym.type}.")
                        # Always a boolean, no need to put an error type here.
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.BOOL)
                case TokenKind.SYM_PLUS | TokenKind.SYM_MINUS | TokenKind.SYM_STAR | TokenKind.SYM_SLASH:
                    # Arithmetic operation -> both numeric
                    if is_numeric_type(left_sym.type) and is_numeric_type(right_sym.type):
                        # If one of them is a float, the result will be a float.
                        if left_sym.type == BuiltInTypeKind.FLOAT or right_sym.type == BuiltInTypeKind.FLOAT:
                            expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.FLOAT)
                        else:
                            expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.INT)
                    else:
                        op_name = e.operator_token.text
                        register_error(e,
                                       f"Impossible d'utiliser l'opérateur « {op_name} » avec les types {left_sym.type} et {right_sym.type}.")
                        expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
        elif isinstance(e, VariableExpr):
            # Variable expression. Make sure the variable/value actually exists.

            value_syms = visible_values_within(e)
            if e.name_token_str not in value_syms:
                register_error(e, f"La variable {e.name_token_str} n'est pas encore définie.")
                expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR)
            else:
                # Take the type of the variable!
                v = value_syms[e.name_token_str]
                expr_to_sym[e] = ExpressionSym(v.type, v)
        elif isinstance(e, FunctionExpr):
            # Function call expression. Does the function exist? Are its arguments correct? Let's see...
            func = find_function(e.identifier_token_str)
            if not func:
                register_error(e, f"La fonction {e.identifier_token_str} n'est pas définie.")
                expr_to_sym[e] = ExpressionSym(BuiltInTypeKind.ERROR, func)
            else:
                # We obviously know the return type.
                expr_to_sym[e] = ExpressionSym(func.return_type, func)

                # Now, let's gather and check the arguments
                given_args = list(e.arg_list.arguments)
                params = func.parameters
                common = min(len(params), len(given_args))

                # If we have too much or too few, complain!
                if len(params) > len(given_args):
                    register_error(e, f"Trop peu d'arguments ont été donnés à la fonction {func.name} : {len(given_args)} donnés, {len(params)} attendus.")
                elif len(params) < len(given_args):
                    register_error(e, f"Trop d'arguments ont été donnés à la fonction {func.name} : {len(given_args)} donnés, {len(params)} attendus.")

                # Register all the argument expressions, and register some errors if the types don't match.
                for i in range(0, len(given_args)):
                    arg = given_args[i]
                    if arg.expr is not None:
                        arg_sym = register_expression(arg.expr)
                        if i < common and arg_sym.type != BuiltInTypeKind.ERROR and arg_sym.type != params[i].type:
                            register_error(e, f"L'argument {i + 1} de l'appel à « {func.name} » est du mauvais type : {arg_sym.type} donné, {params[i].type} attendu.")
        else:
            raise NotImplementedError(f"Expression type {type(e)} not implemented yet.")

        return expr_to_sym[e]


    # Transforms a literal/type token (bool, int, float, "hell", 81, etc.) into the BuiltInTypeKind enum.
    # Returns the "default" arg if there's no token, or if it's invalid.
    def to_builtin_type(t: LeafNode | BuiltInType | None, default=BuiltInTypeKind.ERROR) -> BuiltInTypeKind:
        if t is None:
            return default

        if isinstance(t, BuiltInType):
            t = t.kind_token

        match t.kind:
            case TokenKind.KW_BOOL | TokenKind.LITERAL_BOOL:
                return BuiltInTypeKind.BOOL
            case TokenKind.KW_INT:
                return BuiltInTypeKind.INT
            case TokenKind.KW_FLOAT:
                return BuiltInTypeKind.FLOAT
            case TokenKind.KW_STRING | TokenKind.LITERAL_STRING:
                return BuiltInTypeKind.STRING
            case TokenKind.LITERAL_NUM:
                # Integer -> int
                # Float -> float
                if trunc(t.value) == t.value:
                    return BuiltInTypeKind.INT
                else:
                    return BuiltInTypeKind.FLOAT
            case _:
                return default


    def register_variable(v: VariableDeclarationStmt):
        if v in variable_to_sym:
            # Already registered
            return

        if v.name_token is None or not v.name_token_str:
            # Invalid name, already reported by the parser
            return

        # Make the variable symbol.
        name = v.name_token_str
        ty = to_builtin_type(v.type)
        symbol = VariableSym(name, ty, v)

        if ty == BuiltInTypeKind.ERROR:
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
                register_error(v, f"La variable {name} est déjà définie comme paramètre.")
            pass

        if v.value is not None and ty != BuiltInTypeKind.ERROR:
            # If there's a default value, check that it's of the correct type.
            value_sym = register_expression(v.value)
            if value_sym.type != ty and value_sym != BuiltInTypeKind.ERROR:
                register_error(v.value, f"La valeur donnée pour la variable {name} est du mauvais type : {value_sym.type} donné, {ty} attendu.")

        variable_to_sym[v] = symbol

    def register_function(f: FunctionDeclarationStmt):
        if f.name_token is None or not f.name_token_str:
            # Invalid name, already reported by the parser
            return

        pre_existing = find_function(f.name_token_str)
        if pre_existing:
            register_error(f, f"La fonction {f.name_token_str} est déjà définie.")
            return

        params: list[ParameterSym] = []
        for p in f.parameters:
            if p.name_token is None:
                register_error(p, "Nom de paramètre invalide.")
                continue

            ty = to_builtin_type(p.type)
            if ty == BuiltInTypeKind.ERROR:
                register_error(p, "Type de paramètre inconnu.")
                # Don't return, it's okay

            # Make sure the parameter name isn't already used before.
            if not any(1 for x in params if x.name == p.name_token_str):
                params.append(ParameterSym(p.name_token_str, ty, p))
            else:
                register_error(p, f"Le paramètre {p.name_token_str} est déjà défini.")

        global_funcs[f.name_token_str] = FunctionSym(
            name=f.name_token_str,
            return_type=BuiltInTypeKind.NOTHING, # TODO: Consider adding support for return types?
            parameters=params,
            node=f
        )
        function_to_sym[f] = global_funcs[f.name_token_str]

    def analyse_node(n: InnerNode):
        analyse_children = True

        if isinstance(n, VariableDeclarationStmt):
            register_variable(n)
            analyse_children = False
        elif isinstance(n, FunctionDeclarationStmt):
            # Functions are already declared at the beginning of the analysis.
            if n.parent is not program:
                register_error(n, "Les fonctions ne peuvent être déclarées que globalement.")
        elif isinstance(n, IfStmt) or isinstance(n, WhileStmt) or isinstance(n, ElseStmt):
            cond_type = register_expression(n.condition)
            if cond_type != BuiltInTypeKind.BOOL and cond_type != BuiltInTypeKind.ERROR:
                register_error(n.condition, "La condition doit être un booléen.")
        elif isinstance(n, AssignStmt):
            # Ensure that the variable (not a parameter!) exist.
            var = find_visible_variable(n.name_token_str, n)

            # It doesn't? Report it.
            if var is None:
                register_error(n, f"La variable {n.name_token_str} n'est pas définie.",
                               slot=AssignStmt.name_token_slot)

            if n.value is not None:
                val_sym = register_expression(n.value)
                # Check that the assign value is of the correct type, only if we have a variable found.
                if var and val_sym.type != BuiltInTypeKind.ERROR and val_sym.type != var.type:
                    register_error(n.value, f"La valeur assignée à la variable {n.name_token_str} est du mauvais type : {val_sym.type} donné, {var.type} attendu.")

            analyse_children = False
        elif isinstance(n, Expression):
            register_expression(n)
            analyse_children = False

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

    return ProgramSemanticInfo(
        global_functions=global_funcs,
        global_variables=global_vars,
        function_to_sym=function_to_sym,
        variable_to_sym=variable_to_sym,
        expr_to_sym=expr_to_sym
    )
    # raise NotImplementedError("Not done yet... :(")
