from pydpp.compiler.syntax.base import *
from pydpp.compiler.syntax.codegen import *
from pydpp.compiler.tokenizer import Token, TokenKind as TK


def definitions() -> list[type]:
    node_def, nodes = declare_definitions()

    # ----------
    # Nodes that don't fit into statements or expressions
    # ----------

    @node_def
    class BuiltInType(Statement):
        """
        A built-in type specified using a keyword like int, bool...
        """

        kind_token = single(Token, doc="The token representing the type.")

    @node_def
    class Argument(InnerNode):
        """
        An argument to a function call.
        """

        expr = single(Expression, doc="The expression representing the argument.")
        comma_token = single(TK.SYM_COMMA, doc="The ',' token.")

    @node_def
    class ArgumentList(InnerNode):
        """
        A list of arguments to a function call.
        """

        lparen_token = single(TK.SYM_LPAREN, doc="The '(' token.")
        arguments = multi(Argument, doc="The arguments to the function.")
        rparen_token = single(TK.SYM_RPAREN, doc="The ')' token.")

    # ----------
    # Expressions
    # ----------

    @node_def
    class LiteralExpr(Expression):
        """
        A literal expression, which can be either:
            - a number literal (5, 3.14)
            - a string literal ("hello, world!")
            - a boolean literal (true, false)

        The value of the literal is contained within the token: token.value
        """

        token = single(Token,
                       check=[TK.LITERAL_NUM, TK.LITERAL_STRING, TK.LITERAL_BOOL],
                       optional=False,
                       doc="The token representing the literal.")

    @node_def
    class BinaryOperationExpr(Expression):
        """
        A binary operation expression, following this pattern: left [operator] right.
        Where [operator] is a binary operator in the ``BinaryOperator`` enum.

        Examples:
            - 5 + 8 ; left = 5, operator = ADD, right = 8
            - 8 * 6 ; left = 8, operator = MUL, right = 6
        """

        left = single(Expression, doc="The left side of the operation.")
        operator_token = single(Token,
                                check=[TK.KW_OR, # OR: "or"
                                       TK.KW_AND, # AND: "and"
                                       TK.SYM_EQ, # EQ: "=="
                                       TK.SYM_NEQ, # NEQ: "!="
                                       TK.SYM_LT, # LT: "<"
                                       TK.SYM_LEQ, # LEQ: "<="
                                       TK.SYM_GT, # GT: ">"
                                       TK.SYM_GEQ, # GEQ: ">="
                                       TK.SYM_PLUS, # PLUS: "+"
                                       TK.SYM_MINUS, # MINUS: "-"
                                       TK.SYM_STAR, # STAR: "*"
                                       TK.SYM_SLASH], # SLASH: "/"
                                doc="The operator token.")
        right = single(Expression, doc="The right side of the operation.")

    @node_def
    class ParenthesizedExpr(Expression):
        """
        An expression enclosed in parentheses.
        """

        lparen_token = single(TK.SYM_LPAREN, doc="The '(' token.")
        expr = single(Expression, doc="The expression inside the parentheses.")
        rparen_token = single(TK.SYM_RPAREN, doc="The ')' token.")

    @node_def
    class UnaryExpr(Expression):
        """
        A unary expression, an expression with a NOT/- operator before it.
        Example: NOT true
        """

        op_token = single(Token,
                          check=[TK.KW_NOT, TK.SYM_MINUS],
                          doc="The operator preceding the expression: .")
        expr = single(Expression, doc="The expression to apply the operator to.")

    @node_def
    class FunctionExpr(Expression):
        """
        A function call expression, which calls a function with a list of arguments, and gives
        the return value of the function.
        """

        identifier_token = single(TK.IDENTIFIER, doc="The identifier of the function.")
        arg_list = single(ArgumentList, doc="The arguments to the function.")

    @node_def
    class VariableExpr(Expression):
        """
        A variable expression, returning the value of a variable.
        """

        name_token = single(TK.IDENTIFIER, optional=False, doc="The name of the variable.")

    @node_def
    class ErrorExpr(Expression):
        """
        An invalid/unrecognized expression. Prevents compilation. Has unknown type.
        """

        tokens = multi(Token, doc="All tokens that were ignored during parsing.")

    # ----------
    # Statements
    # ----------

    @node_def
    class BlockStmt(Statement):
        """
        A block statement, which is a sequence of statements enclosed in curly braces.
        """

        lbrace_token = single(TK.SYM_LBRACE, doc="The '{' token.")
        statements = multi(Statement, doc="The statements contained within the block.")
        rbrace_token = single(TK.SYM_RBRACE, doc="The '}' token.")

    @node_def
    class VariableDeclarationStmt(Statement):
        """
        A variable declaration, with a type, identifier, and optional value.
        """

        type = single(BuiltInType, doc="The type of the variable.")
        name_token = single(Token, doc="The name of the variable.")
        assign_token = single(TK.SYM_ASSIGN, doc="The '=' token.")
        value = single(Expression, doc="The value of the variable.")
        semi_colon = single(TK.SYM_SEMICOLON, doc="The ';' token.")

    @node_def
    class ElseStmt(Statement):
        """
        An "else" or "else if" statement. Should be located inside an IfStmt.
        If located somewhere else, it's an error.
        """

        else_token = single(Token, doc="The 'else' token.")
        if_token = single(Token, doc="The 'if' token.")
        condition = single(Expression, doc="The condition of the else if statement.")
        block = single(BlockStmt, doc="The block of the else if statement.")

    @node_def
    class IfStmt(Statement):
        """
        An if statement, with [0..N] else/else-if blocks.
        """

        if_token = single(Token, doc="The 'if' token.")
        condition = single(Expression, doc="The condition of the if statement.")
        then_block = single(BlockStmt, doc="The block of the if statement.")
        else_statements = multi(ElseStmt, doc="The else/else-if blocks of the if statement.")

    @node_def
    class WhileStmt(Statement):
        """
        A while loop, with a condition and a block of statements to run while the condition is true.
        """

        while_token = single(Token, doc="The 'while' token.")
        condition = single(Expression, doc="The condition to check before running the block.")
        block = single(BlockStmt, doc="The block of statements to run while the condition is true.")

    @node_def
    class FunctionCallStmt(Statement):
        """
        A function call statement, which just contains a function call expression, and discards the
        return value of the function.
        """

        expr = single(FunctionExpr, doc="The function call expression.")
        semi_colon = single(TK.SYM_SEMICOLON, doc="The ';' token.")

    @node_def
    class AssignStmt(Statement):
        """
        A variable assignment statement, which assigns a value to an existing variable.
        """

        name_token = single(TK.IDENTIFIER, doc="The name of the variable.")
        assign_token = single(TK.SYM_ASSIGN, doc="The '=' token.")
        value = single(Expression, doc="The value to assign to the variable.")
        semi_colon = single(TK.SYM_SEMICOLON, doc="The ';' token.")

    @node_def
    class ErrorStmt(Statement):
        """
        An invalid/unrecognized statement. Prevents compilation.
        """

        tokens = multi(Token, doc="All tokens that were ignored during parsing.")

    return nodes
