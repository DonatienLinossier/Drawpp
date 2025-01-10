import copy
from collections.abc import Callable

from pydpp.compiler.semantic import ProgramSemanticInfo, SemanticType
from pydpp.compiler.syntax import *
from pydpp.compiler.tokenizer import Token, TokenKind, AuxiliaryKind


# ======================================================
# semantic.py: The suggestion engine
# ======================================================

class Suggestion(typing.NamedTuple):
    title: str
    problem: InnerNodeProblem | TokenProblem
    func: Callable[[Node], bool]

    def apply(self, node: Node) -> bool:
        return self.func(node)


def find_suggestion(node: Node, semantic_info: ProgramSemanticInfo,
                    problem: InnerNodeProblem | TokenProblem) -> Suggestion | None:
    """
    Finds a suggestion to fix a problem on the given node.
    :param node: the node having a problem
    :param semantic_info: the semantic info
    :param problem: the problem
    :return: a suggestion, if it can provide any...
    """
    match problem.code:
        case ProblemCode.MISSING_SEMICOLON:
            def apply(n: Node):
                assert isinstance(n, Statement)
                n.semi_colon = leaf(Token(TokenKind.SYM_SEMICOLON, ';'))
                return True

            return Suggestion("Ajouter un point-virgule", problem, apply)

        case ProblemCode.MISSING_LPAREN:
            def apply(n: Node):
                assert isinstance(n, FunctionDeclarationStmt)
                n.lparen_token = leaf(Token(TokenKind.SYM_LPAREN, '('))
                return True

            return Suggestion("Ajouter une parenthèse ouvrante", problem, apply)

        case ProblemCode.MISSING_RPAREN:
            def apply(n: Node):
                assert isinstance(n, (ParenthesizedExpr, ArgumentList, FunctionDeclarationStmt))
                n.rparen_token = leaf(Token(TokenKind.SYM_RPAREN, ')'))
                return True

            return Suggestion("Ajouter une parenthèse fermante", problem, apply)

        case ProblemCode.MISSING_COMMA:
            def apply(n: Node):
                assert isinstance(n, (Argument, FunctionParameter))
                n.comma_token = leaf(Token(TokenKind.SYM_COMMA, ','))
                return True

            return Suggestion("Ajouter une virgule", problem, apply)

        case ProblemCode.MISSING_BLOCK:
            def apply(n: Node):
                assert isinstance(n, (IfStmt, WhileStmt, FunctionDeclarationStmt, ElseStmt, WieldStmt))
                # Make a new block statement, with some whitespace between and before the braces.
                bl = BlockStmt(
                    lbrace_token=leaf(Token(TokenKind.SYM_LBRACE, '{', _whitespace())),
                    statements=[],
                    rbrace_token=leaf(Token(TokenKind.SYM_RBRACE, '}', _whitespace()))
                )
                # The if statement is a bit special, its block slot is named "then_block".
                if not isinstance(n, IfStmt):
                    n.block = bl
                else:
                    n.then_block = bl
                return True

            return Suggestion("Ajouter un bloc d'instructions", problem, apply)

        case ProblemCode.MISSING_RBRACE:
            def apply(n: Node):
                assert isinstance(n, BlockStmt)
                n.rbrace_token = leaf(Token(TokenKind.SYM_RBRACE, '}'))
                return True

            return Suggestion("Ajouter une accolade fermante", problem, apply)

        case ProblemCode.UNDEFINED_VARIABLE:
            def apply(n: Node):
                assert isinstance(n, (AssignStmt, VariableExpr))

                if isinstance(n, AssignStmt):
                    # Transform this assignment statement into a variable declaration

                    # Find out the type of the value.
                    if n.value is not None:
                        expr_type = semantic_info.expr_to_sym[n.value].type
                        # Make sure to detach the value node, we're going to re-use it.
                        n.value.detach_self()
                    else:
                        expr_type = SemanticType.ERROR

                    # When we have an unknown type, just use FLOAT.
                    type_node = _builtin_type_to_node(expr_type) or _builtin_type_to_node(SemanticType.FLOAT)

                    if n.name_token_str:
                        var_name = n.name_token_str
                    else:
                        # Not sure if that's even possible
                        var_name = "var1"

                    # Build the variable declaration statement
                    var_decl = VariableDeclarationStmt(
                        type=BuiltInType(type_node),
                        name_token=leaf(Token(TokenKind.IDENTIFIER, var_name, _whitespace())),
                        assign_token=leaf(Token(TokenKind.SYM_ASSIGN, '=', _whitespace())),
                        value=n.value,
                        semi_colon=leaf(Token(TokenKind.SYM_SEMICOLON, ';'))
                    )
                    var_decl.pre_auxiliary = _only_last_whitespace(n.pre_auxiliary)
                    n.replace_with(var_decl)

                    return True
                elif isinstance(n, VariableExpr):
                    # We have some variable expression, "my_super_var_42" or whatever,
                    # which does NOT exist and thus we have no idea what its type might be.

                    # So, let's create a variable definition with a FLOAT type before the statement
                    # containing it.
                    stmt = n.ancestor(Statement)

                    # Try to guess the type. We can only be certain of it when it's an argument
                    # of something which wants a specific type of value, so stuff like "wield",
                    # func arguments, assignments, etc.
                    # We'll only implement cursor stuff for now.
                    var_type = SemanticType.FLOAT
                    if isinstance(n.parent, WieldStmt) or isinstance(n.parent, FunctionExpr):
                        var_type = SemanticType.CURSOR

                    # Make the node!
                    var_decl = VariableDeclarationStmt(
                        type=BuiltInType(_builtin_type_to_node(var_type)),
                        name_token=leaf(Token(TokenKind.IDENTIFIER, n.name_token_str, _whitespace())),
                        assign_token=None,
                        value=None,
                        semi_colon=leaf(Token(TokenKind.SYM_SEMICOLON, ';'))
                    )

                    # Here we're going to "transfer" the statement's auxiliary
                    # to our new statement (since it's now preceding it).
                    stmt_aux = stmt.pre_auxiliary
                    var_decl.pre_auxiliary = stmt_aux

                    # Both statements are now "glued" to each other. Add some whitespace
                    # so they're both on separate lines AND indented correctly.
                    stmt.pre_auxiliary = _whitespace("\n" + _find_indentation(stmt_aux))

                    stmt.parent.attach_child(stmt.parent_slot, var_decl, stmt.parent_slot_idx)

                    return True
                else:
                    return False

            return Suggestion(f"Déclarer la variable", problem, apply)

    return None


def _builtin_type_to_node(t: SemanticType):
    match t:
        case SemanticType.INT:
            return leaf(Token(TokenKind.KW_INT, "int"))
        case SemanticType.FLOAT:
            return leaf(Token(TokenKind.KW_FLOAT, "float"))
        case SemanticType.BOOL:
            return leaf(Token(TokenKind.KW_BOOL, "bool"))
        case SemanticType.STRING:
            return leaf(Token(TokenKind.KW_STRING, "string"))
        case SemanticType.CURSOR:
            return leaf(Token(TokenKind.KW_CURSOR, "cursor"))
        case _:
            return None


# Makes some whitespace auxiliary text tuple
def _whitespace(s: str = " "):
    return (AuxiliaryText(AuxiliaryKind.WHITESPACE, s),)

# Takes a tuple of auxiliary texts, and gives ONLY the last whitespace element, if it's
# the last auxiliary text.
def _only_last_whitespace(a: tuple[AuxiliaryText, ...]):
    if len(a) == 0 or a[-1].kind != AuxiliaryKind.WHITESPACE:
        return ()
    else:
        return (a[-1], )

# Takes a tuple of auxiliary text, and returns only the last whitespace element's indentation,
# as a string
def _find_indentation(a: tuple[AuxiliaryText, ...]) -> str:
    ws = _only_last_whitespace(a)
    if len(ws) == 0:
        return ""

    text = ws[0].text

    last_nl = text.rfind("\n")
    if last_nl == -1:
        return text
    else:
        return text[last_nl + 1:]