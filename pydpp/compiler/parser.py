from typing import TypeVar, Optional, overload

from pydpp.compiler.position import extend_span, invisible_span
from pydpp.compiler.syntax import *
from pydpp.compiler.tokenizer import *
from pydpp.compiler.types import BuiltInTypeKind


# =============================================================================
# parser.py: The magic parser transforming tokens into a syntax tree
# =============================================================================

class Parser:
    """
    Takes a list of tokens, and processes it to create a syntax tree from it.

    Handles errors by making up fake nodes ("error expressions").

    It has a similar structure as the tokenizer, with the same cursor system.
    """

    __slots__ = ("tokens", "cursor", "eof", "program_statements", "problems")

    def __init__(self, tokens: list[Token], problems: ProblemSet):
        self.tokens = tokens
        "The list of tokens to parse."
        self.cursor = 0
        "The index of the next token to read. If it's equal to len(tokens), we've reached the end of the file."
        self.eof = len(tokens) == 0
        "Whether we've reached the end of the file."

        self.program_statements = []
        "The list of statements we've read so far, that will be put inside a Program node."
        self.problems = problems
        "The problem set to report errors to."

    def parse(self):
        """
        Parses the list of tokens, and returns the root Program node.
        """
        if self.eof:
            # We have no tokens! Return an empty program.
            return Program([], FileSpan(FileCoordinates(0, 1, 1), FileCoordinates(0, 1, 1)))

        # Keep track of the sequence of tokens that don't make a valid statement.
        invalid_tokens = []

        def flush_invalid_tokens():
            if len(invalid_tokens) > 0:
                self.problems.append(problem="Instruction non reconnue.",
                                     severity=ProblemSeverity.ERROR,
                                     pos=extend_span(invalid_tokens[0].pos, invalid_tokens[-1].pos))
                invalid_tokens.clear()

        # Keep reading tokens until we're finished.
        while not self.eof:
            # Try reading a statement
            if stmt := self.parse_statement():
                # Got one! Get rid of the invalid tokens (non-statement) if we got some.
                self.program_statements.append(stmt)
                flush_invalid_tokens()
            else:
                # That token wasn't recognized as a statement, add it to the unrecognized pile.
                tkn = self.consume()
                if tkn:
                    invalid_tokens.append(tkn)

        # If we have some invalid tokens left, report them as an error.
        flush_invalid_tokens()

        # Make the Program node, take the entire span of the file, and return it!
        pos = extend_span(self.tokens[0].pos, self.tokens[-1].pos)
        return Program(self.program_statements, pos)

    def parse_statement(self) -> Optional[Statement]:
        """
        Parses the next incoming statement.
        Returns the statement when a statement has been recognized OR when an erroneous statement
        has been created.
        Return None when no statement could be recognized.
        """

        # Try all kinds of statements we know. Order is important here (function call / assign)
        if stmt := self.parse_function_call_statement():
            return stmt
        elif stmt := self.parse_variable_declaration_statement():
            return stmt
        elif stmt := self.parse_if_statement():
            return stmt
        elif stmt := self.parse_else_statement():
            # todo: change this to move the logic down in if_statement that should check for else
            self.problems.append(problem="Bloc « else » sans « if » correspondant.",
                                 severity=ProblemSeverity.ERROR,
                                 pos=stmt.pos)
            return stmt
        elif stmt := self.parse_block_statement():
            return stmt
        elif stmt := self.parse_assign_statement():
            return stmt
        elif stmt := self.parse_while_statement():
            return stmt

        return None

    def parse_if_statement(self) -> Optional[IfStmt]:
        """
        Parses the next incoming if statement. May contain else statements.
        """

        if if_kw := self.consume_exact(TokenKind.KW_IF):
            # We got an if keyword, try looking for a condition.
            condition = self.parse_expression()
            if condition is None:
                # No condition, make one up and error out.
                condition = ErrorExpr(invisible_span(if_kw.pos))
                self.problems.append(problem="Condition manquante après un « if ».",
                                     severity=ProblemSeverity.ERROR,
                                     pos=if_kw.pos)

            block = self.parse_block_statement()
            if block is None:
                # No block?? Make one up!
                block = BlockStmt([], invisible_span(if_kw.pos))
                self.problems.append(problem="Bloc d'instructions manquant après un « if ».",
                                     severity=ProblemSeverity.ERROR,
                                     pos=if_kw.pos)

            # Read all "else" blocks after the if.
            elses = []
            # Set to True when we've seen an "else" block (not an "else if")
            # Used to report errors when we see another "else"/"else if" after an "else"
            saw_final_else = False
            while else_stmt := self.parse_else_statement():
                # Add the else statement.
                elses.append(else_stmt)

                # If we got another "else" block, report an error.
                if saw_final_else:
                    block_name = "else" if else_stmt.condition is None else "else if"
                    self.problems.append(problem=f"Bloc « {block_name} » situé après un « else » existant.",
                                         severity=ProblemSeverity.ERROR,
                                         pos=else_stmt.pos)
                else:
                    saw_final_else = else_stmt.condition is None

            return IfStmt(condition, block, elses, extend_span(if_kw.pos, block.pos))

    def parse_else_statement(self) -> Optional[ElseStmt]:
        """
        Parses the next incoming else statement.
        """

        if else_kw := self.consume_exact(TokenKind.KW_ELSE):
            # We got an else keyword, try looking for a condition if we need one
            condition = None
            if if_kw := self.consume_exact(TokenKind.KW_IF):
                condition = self.parse_expression()
                if condition is None:
                    # No condition found despite it being "else if"
                    condition = ErrorExpr(invisible_span(if_kw.pos))
                    self.problems.append(problem="Condition manquante après un « else if ».",
                                         severity=ProblemSeverity.ERROR,
                                         pos=if_kw.pos)

            block = self.parse_block_statement()
            if block is None:
                # No block?? Make one up!
                block = BlockStmt([], invisible_span(else_kw.pos))
                name = "else if" if condition else "else"
                self.problems.append(problem=f"Bloc d'instructions manquant après un « {name} ».",
                                     severity=ProblemSeverity.ERROR,
                                     pos=else_kw.pos)

            # Make the node and return it.
            return ElseStmt(condition, block, extend_span(else_kw.pos, block.pos))

        return None

    def parse_block_statement(self) -> Optional[BlockStmt]:
        """
        Parses the next incoming block statement.
        """

        # Make sure we start the block with a left brace: {
        if (lbrace := self.consume_exact(TokenKind.SYM_LBRACE)) is None:
            return None

        statements: list[Statement] = []

        # Keep track of the sequence of tokens that don't make a valid statement.
        # (copied from parse)
        invalid_tokens = []

        def flush_invalid_tokens():
            if len(invalid_tokens) > 0:
                self.problems.append(problem="Instruction non reconnue.",
                                     severity=ProblemSeverity.ERROR,
                                     pos=extend_span(invalid_tokens[0].pos, invalid_tokens[-1].pos))
                invalid_tokens.clear()

        # Keep reading statements until we stumble upon a right brace.
        while (nxt := self.peek()) and nxt.kind != TokenKind.SYM_RBRACE:
            if stmt := self.parse_statement():
                statements.append(stmt)
                flush_invalid_tokens()
            else:
                tkn = self.consume()
                if tkn:
                    invalid_tokens.append(tkn)

        if nxt: # Then it must be a SYM_RBRACE if we stop there
            self.consume()
        else:
            # EOF, no closing brace! Report an error
            self.problems.append(problem="Bloc d'instructions non fermé.",
                                 severity=ProblemSeverity.ERROR,
                                 pos=extend_span(lbrace.pos, self.peek(skip=-1).pos))

        flush_invalid_tokens()

        return BlockStmt(statements, extend_span(lbrace.pos, self.peek(skip=-1).pos))

    def parse_function_call_statement(self):
        """
        Parses the next incoming function call statement.
        """

        if fc := self.parse_function_expression():
            sm = self.expect_semicolon()
            return FunctionCallStmt(fc, extend_span(fc.pos, sm))
        else:
            return None

    def parse_variable_declaration_statement(self) -> Optional[VariableDeclarationStmt]:
        """
        Parses the next incoming variable declaration.
        """

        # If come across a type, it's a variable declaration beginning.
        if var_type := self.parse_built_in_type():
            # Then we need to find the identifier of the variable.
            if ident := self.parse_identifier():
                # Let's see if there's an assignment or not.
                value = None
                if assign := self.consume_exact(TokenKind.SYM_ASSIGN):
                    # We have an assignment operator, now we need to find the value.
                    value = self.parse_expression()
                    if value is None:
                        # Make one up again...
                        value = ErrorExpr(invisible_span(assign.pos))
                        self.problems.append(problem="Valeur manquante après l'assignation '='.",
                                             severity=ProblemSeverity.ERROR,
                                             pos=assign.pos)

                sm = self.expect_semicolon()
                return VariableDeclarationStmt(var_type, ident, value, extend_span(var_type.pos, sm))
            else:
                # No identifier? Make one up!
                ident = Identifier("", invisible_span(var_type.pos))
                self.problems.append(problem="Identificateur manquant après le type de variable.",
                                     severity=ProblemSeverity.ERROR,
                                     pos=var_type.pos)

                sm = self.expect_semicolon()
                return VariableDeclarationStmt(var_type, ident, None, extend_span(var_type.pos, sm))

    def parse_assign_statement(self):
        """
        Parses the next incoming assignment statement.
        """

        # First we need to make sure that we have an identifier and an assignment operator.
        if (ident := self.peek()) and (assign := self.peek(skip=1)):
            if isinstance(ident, IdentifierToken) and assign.kind == TokenKind.SYM_ASSIGN:
                # Consume both identifier and assignment tokens.
                self.consume()
                self.consume()

                if (val := self.parse_expression()) is None:
                    # No expression after the equal sign: make something up and report an error.
                    val = ErrorExpr(invisible_span(assign.pos))
                    self.problems.append(problem="Valeur manquante après l'assignation '='.",
                                         severity=ProblemSeverity.ERROR,
                                         pos=assign.pos)

                sm = self.expect_semicolon()
                return AssignStmt(Identifier(ident.name, ident.pos), val, extend_span(ident.pos, sm))

        return None

    def parse_while_statement(self):
        """
        Parses the next incoming while statement.
        """

        if while_kw := self.consume_exact(TokenKind.KW_WHILE):
            # We got a while keyword, try looking for a condition.
            condition = self.parse_expression()
            if condition is None:
                condition = ErrorExpr(invisible_span(while_kw.pos))
                self.problems.append(problem="Condition manquante après un « while ».",
                                     severity=ProblemSeverity.ERROR,
                                     pos=while_kw.pos)

            block = self.parse_block_statement()
            if block is None:
                # No block?? Make one up!
                block = BlockStmt([], invisible_span(while_kw.pos))
                self.problems.append(problem="Bloc d'instructions manquant après un « while ».",
                                     severity=ProblemSeverity.ERROR,
                                     pos=while_kw.pos)

            return WhileStmt(condition, block, extend_span(while_kw.pos, block.pos))
        else:
            return None

    def expect_semicolon(self) -> Optional[FileSpan]:
        """
        Consumes the incoming semicolon token. If it is not present, reports an error
        and returns a 0-length span to the last parsed token.

        May be None if no token was parsed or if the token doesn't have a span.
        """
        if tkn := self.consume_exact(TokenKind.SYM_SEMICOLON):
            # We have a semicolon, all good, return its position.
            return tkn.pos
        else:
            # We don't! Report and error and given the position of the last parsed token.
            self.problems.append(problem="Point-virgule manquant à la fin d'une instruction.",
                                 severity=ProblemSeverity.ERROR,
                                 pos=self.peek(skip=-1).pos)
            if self.cursor > 0:
                return extend_span(self.peek(skip=-1).pos, self.peek(skip=-1).pos)
            else:
                return None

    def parse_identifier(self):
        """
        Parses the next identifier node.
        """
        # Check if we have an incoming identifier token.
        if ident_token := self.consume_exact(IdentifierToken):
            return Identifier(ident_token.name, ident_token.pos)
        else:
            return None

    def parse_built_in_type(self):
        """
        Parses the next built-in type node (int, float, etc.).
        """
        if self.eof:
            return None

        # Try all possible matching type keywords.
        match self.peek().kind:
            case TokenKind.KW_INT:
                built_type = BuiltInTypeKind.INT
            case TokenKind.KW_FLOAT:
                built_type = BuiltInTypeKind.FLOAT
            case TokenKind.KW_STRING:
                built_type = BuiltInTypeKind.STRING
            case TokenKind.KW_BOOL:
                built_type = BuiltInTypeKind.BOOL
            case _:
                return None

        tkn = self.consume()
        return BuiltInType(built_type, tkn.pos)

    # Precedence of all binary operators, from lowest to highest.
    # Precedence is what tells which expression is evaluated first. As in a+b*c, b*c is evaluated first.
    # The higher the precedence, deeper it is present in the syntax tree.
    # Inversely, a low precedence means it's higher up in the tree.
    op_to_prec = {
        TokenKind.KW_OR: (0, BinaryOperator.OR),
        TokenKind.KW_AND: (1, BinaryOperator.AND),
        TokenKind.SYM_EQ: (2, BinaryOperator.EQ),
        TokenKind.SYM_NEQ: (2, BinaryOperator.NEQ),
        TokenKind.SYM_LT: (2, BinaryOperator.LT),
        TokenKind.SYM_LEQ: (2, BinaryOperator.LEQ),
        TokenKind.SYM_GT: (2, BinaryOperator.GT),
        TokenKind.SYM_GEQ: (2, BinaryOperator.GEQ),
        TokenKind.SYM_PLUS: (3, BinaryOperator.ADD),
        TokenKind.SYM_MINUS: (3, BinaryOperator.SUB),
        TokenKind.SYM_STAR: (4, BinaryOperator.MUL),
        TokenKind.SYM_SLASH: (4, BinaryOperator.DIV)
    }

    def parse_expression(self):
        """
        Parses the next expression.
        Returns an Expression node when an expression has been recognized,
        which may have ErrorExpressions as children if the expression wasn't written properly.

        Returns None when no expression could be recognized.
        """

        # ============================================
        # EXPRESSION PARSING
        # ============================================
        # To parse expressions, we have two "levels" of parsing:
        # 1. Binary operations: Using a precedence climbing parser to read all binary operations, while
        #    handling precedence correctly.
        # 2. Non-binary expressions: Using a usual recursive descent parser, we try each possible
        #    expression type in order (unary, function call, parenthesized, variable, literal).

        # ------
        # BINARY OPERATION PARSING
        # ------

        # The precedence climbing expression parser for binary operations.
        # set_idx is the index of the precedent set in precedent_sets.
        #
        # --------------------------------
        # The way it works is actually fairly straightforward, but difficult to grasp at first.
        #
        # Consider that binary operators have EBNF rules setup like this:
        #    prec0_expr = prec0_expr, "op0", prec1_expr | prec1_expr
        #    prec1_expr = prec1_expr, "op1", prec2_expr | prec2_expr
        #    ...
        #    precN_expr = precN_expr, "opN", non_binary_expr | non_binary_expr
        #    non_binary_expr = literal | variable | "(", prec0_expr, ")"
        #
        # Which can also be interpreted as
        #    prec0_expr = prec0_expr {"op0" prec1_expr} | prec1_expr
        #    prec1_expr = prec1_expr {"op1" prec2_expr} | prec2_expr
        #    ...
        #    precN_expr = precN_expr {"opN" non_binary_expr} | non_binary_expr
        #
        # The goal of these rules is to make sure that:
        #    - Operations of higher precedence are located "deeper" in the tree.
        #      For example, it makes it impossible to have a full prec0_expr within a prec1_expr.
        #    - Operations of the same precedence are left-associative.
        #      Since prec0_expr's RHS is necessarily a prec1_expr, the only way for
        #      a full prec0_expr (i.e. with an operator) to be itself present in a prec0_expr is to
        #      be to the left side.
        #
        # When we begin parsing an expression, we start with the lowest precedence (prec0_expr).
        #
        # We don't have any LHS (left hand side), so we parse using the prec1_rule.
        # This goes on until we read precN_expr, where N is the highest precedence.
        #
        # Since precN_expr is the last binary expression rule, it will start looking a non-binary expression
        # at the LHS so literals, variables, etc.
        #
        # Once precN_expr receives a valid LHS expression (and it should!), it's in fact the first expression
        # to "try" looking for its operator (opN) next to the LHS.
        # It has priority over all expressions of lower precedence to check for its operator!
        #
        # When the operators don't match, it bubbles up to the expression of previous precedence (N-1), which will
        # in turn try to match its own operators, up until precedence 0.
        #
        # When operators do match, it tries to find the RHS, which is inevitably of precedence N+1, as
        # per the EBNF grammar rules. If we searched for precedence N, we would get right-associativity!
        #
        # Speaking of associativity, once we find an RHS and have our, say, <prec0_expr "op0" prec1_expr> sorted
        # out (we'll refer to it as E), we need to know if there's another "op0" next this expression!
        #
        # Since E is itself a prec0_expr as per the EBNF rule, we need to check the same
        # <prec0_expr "op0" prec1_expr> production rule, where prec0_expr can be E.
        # If we don't, we would have no way to parse successive operators of the same precedence, such as 4 + 5 + 6!
        #
        # We do this using an interative approach. We start do regular left-associative building when the
        # operator is of the same precedence, but when we see a higher one, we give let another function
        # call treat them in the RHS.
        #
        # See https://en.wikipedia.org/wiki/Operator-precedence_parser
        def binary_op_left_assoc(lhs, min_prec: int=0):
            op = None

            # Continue reading operators until we find one of lower precedence, in that is the case,
            # the parent function call will take over reading expressions of lower precedence.
            while (nxt := self.peek()) and (op := Parser.op_to_prec.get(nxt.kind)) and op[0] >= min_prec:
                # Consume the read operator
                self.consume()

                # Read the RHS, and make one up if it's not there.
                rhs = non_binary_expr()
                if rhs is None:
                    rhs = ErrorExpr(invisible_span(nxt.pos))
                    self.problems.append(problem=f"Opérande de droite manquante après l'opérateur « {nxt} » ",
                                         severity=ProblemSeverity.ERROR,
                                         pos=extend_span(lhs.pos, nxt.pos))

                # If the next operator is one of HIGHER precedence, then "pause" this function's execution,
                # and leave it to another call that will read all operators of higher precedence.
                op2 = None
                if (nxt := self.peek()) and (op2 := Parser.op_to_prec.get(nxt.kind)) and op2[0] > op[0]:
                    # Make sure to give it the RHS we got as *its* LHS.
                    # For instance, we can be reading 5+6*, while being at the '*' operator, with '+' having RHS=6
                    # Then, the '*' expression should have an LHS of 6.
                    rhs = binary_op_left_assoc(rhs, op2[0])

                # If we didn't enter the loop above, that means we've read an operator of same precedence,
                # or that we don't have operators anymore.

                # Associate the LHS with the RHS we've read.
                lhs = BinaryOperationExpr(lhs, op[1], rhs, extend_span(lhs.pos, rhs.pos))

            return lhs

        def non_binary_expr() -> Optional[Expression]:
            """Recognizes non-binary expressions, expressions that don't involve binary operators."""

            # Try all non-binary expressions.
            # Order is important here (function expression needs to come before identifier).
            # Else it's just ordered by most likely to less likely.

            if expr := literal():
                return expr
            elif expr := unary():
                return expr
            elif expr := self.parse_function_expression():  # This one has its own function for direct parsing reasons.
                return expr
            elif expr := variable():
                return expr
            elif expr := parenthesized():
                return expr
            pass

        def unary():
            """Recognizes unary expressions, currently: '-expr', 'not expr'."""

            # Check if we have "-" or "and"
            nxt = self.peek()
            if nxt is None or nxt.kind != TokenKind.SYM_MINUS and nxt.kind != TokenKind.KW_NOT:
                return None

            # We got a '-' or 'not' prefix! Consume it and get the next incoming expression.
            self.consume()
            expression = non_binary_expr()
            if expression is None:
                # No expression following the prefix? Make a fake expression and error out.
                expression = ErrorExpr(invisible_span(nxt.pos))
                self.problems.append(problem=f"Expression manquante après « {nxt} » ",
                                     severity=ProblemSeverity.ERROR,
                                     pos=nxt.pos)

            # Create the according expression node.
            if nxt.kind == TokenKind.SYM_MINUS:
                return NegativeExpr(expression, nxt.pos)
            else:
                return NotExpr(expression, nxt.pos)

        def parenthesized():
            """Recognizes parenthesized expressions, like (expr)."""

            # See if we have an opening parenthesis coming.
            # If so, we're going to start a parenthesized expression.
            if lparen := self.consume_exact(TokenKind.SYM_LPAREN):
                # Read the incoming expression (not just non_binary, all kinds!)
                expr = self.parse_expression()

                if not expr:
                    # We didn't find one? Make a fake expression.
                    expr = ErrorExpr(invisible_span(lparen.pos))
                    self.problems.append(problem="Expression manquante après une parenthèse ouvrante.",
                                         severity=ProblemSeverity.ERROR,
                                         pos=lparen.pos)
                    return ParenthesizedExpr(expr, lparen.pos)

                # Find the closing parenthesis and we're done!
                if (rparen := self.consume_exact(TokenKind.SYM_RPAREN)) is None:
                    # Unfinished parenthesized expression! Act as if the parenthesis was closed.
                    self.problems.append(
                        problem="Parenthèse fermante manquante après une expression entre parenthèses.",
                        severity=ProblemSeverity.ERROR,
                        pos=extend_span(lparen.pos, expr.pos))
                    return ParenthesizedExpr(expr, extend_span(lparen.pos, expr.pos))

                return ParenthesizedExpr(expr, extend_span(lparen.pos, rparen.pos))
            else:
                return None

        def variable():
            """Recognizes variable expressions, like myVar, cool_var."""
            # See if we have an identifier coming, and if so that's a variable expression.
            if ident := self.parse_identifier():
                return VariableExpr(ident, ident.pos)
            else:
                return None

        def literal():
            """Recognizes literal expressions, like 5, "hello", true."""
            # Try all kinds of literals we know. Order has no importance.
            if str_lit := self.consume_exact(StringLiteralToken):
                return StringLiteralExpr(str_lit.value, str_lit.pos)
            elif num_lit := self.consume_exact(NumberLiteralToken):
                return NumberLiteralExpr(num_lit.int_part, num_lit.dec_part, num_lit.pos)
            elif bool_lit := self.consume_exact(BoolLiteralToken):
                return BoolLiteralExpr(bool_lit.value, bool_lit.pos)
            else:
                return None

        # Start reading the expression.
        l = non_binary_expr()
        if l:
            return binary_op_left_assoc(l)
        else:
            return None

    def parse_function_expression(self) -> Optional[FunctionExpr]:
        def flush_trash_tokens(tt: list[Token]):
            if len(tt) > 0:
                self.problems.append(problem="Argument de fonction invalide.",
                                     severity=ProblemSeverity.ERROR,
                                     pos=extend_span(tt[0].pos, tt[-1].pos))
                tt.clear()

        # Find the (possibly) identifier token and opening parenthesis "(" token
        ident = self.peek()  # identifier
        paren = self.peek(skip=1)  # (
        if ident and paren and isinstance(ident, IdentifierToken) and paren.kind == TokenKind.SYM_LPAREN:
            # Consume both tokens (ident and paren)
            self.consume()
            self.consume()

            # All arguments we've found.
            args = []
            # True when we were supposed to have an expression, up until we find a comma to delimit the invalid expr.
            expression_missing = False
            # The tokens of the invalid expression.
            trash_tokens = []

            # Continue reading the argument list until we find a closing parenthesis or a semicolon.
            # NOTE: The semicolon check is a bit of a weird choice, we might just give up reading the list
            # instead of waiting for an end of statement.
            while (nxt := self.peek()) and nxt.kind != TokenKind.SYM_RPAREN and nxt.kind != TokenKind.SYM_SEMICOLON:
                if expression_missing:
                    if nxt.kind == TokenKind.SYM_COMMA:
                        expression_missing = False
                        flush_trash_tokens(trash_tokens)
                        self.consume()
                    else:
                        trash_tokens.append(self.consume())
                        continue
                elif len(args) > 0:
                    # We already parsed one argument, a comma should comme next.
                    if not self.consume_exact(TokenKind.SYM_COMMA):
                        self.problems.append(problem="Virgule manquante entre deux arguments de fonction.",
                                             severity=ProblemSeverity.ERROR,
                                             pos=args[-1].pos)

                # Then we must have an expression coming next. Try to read it.
                arg = self.parse_expression()
                if arg:
                    args.append(arg)
                else:
                    expression_missing = True

            if expression_missing and len(trash_tokens) == 0:
                self.problems.append(problem="Argument attendu après une virgule",
                                     severity=ProblemSeverity.ERROR,
                                     pos=self.peek(skip=-1).pos)
            else:
                flush_trash_tokens(trash_tokens)

            if end := self.consume_exact(TokenKind.SYM_RPAREN):
                return FunctionExpr(Identifier(ident.name, ident.pos), args, extend_span(ident.pos, end.pos))
            else:
                self.problems.append(problem="L'appel de fonction n'a pas été proprement fermée.",
                                     severity=ProblemSeverity.ERROR,
                                     pos=extend_span(ident.pos, self.peek(skip=-1).pos))
                return FunctionExpr(Identifier(ident.name, ident.pos), args,
                                    extend_span(ident.pos, self.peek(skip=-1).pos))

    def peek(self, skip=0):
        """
        Returns the next incoming token without consuming it.

        The ``skip`` parameter can be specified to skip N characters.

        Can return None if we've reached the EOF.
        """
        if self.cursor + skip >= len(self.tokens):
            return None
        return self.tokens[self.cursor + skip]

    def consume(self):
        """
        Consumes the next incoming token, and advances the cursor by one.
        Returns the consumed token, or None if we've reached the EOF.
        """
        if self.eof:  # <==> self.cursor == len(self.tokens)
            return None

        # Store the token to return it and advance the cursor by one.
        tok = self.tokens[self.cursor]
        self.cursor += 1
        self.eof = self.cursor == len(self.tokens)
        return tok

    # Here goes some stuff so python understands how the consume_exact function works
    # depending on the argument we pass to it.

    # Kind k -> Token of kind k
    @overload
    def consume_exact(self, kind: TokenKind) -> Token:
        pass

    # Type t -> Token of type t
    T = TypeVar("T")

    @overload
    def consume_exact(self, kind: type[T]) -> T:
        pass

    def consume_exact(self, kind):
        """
        Consumes the next incoming token if it's of the specified kind OR type.
        The ``kind`` parameter can either be a ``TokenKind`` or a ``type`` of Token.

        Returns the consumed token if corresponding to the kind, or None otherwise.

        :param kind: either a ``TokenKind`` of token, or a ``type`` of token to match
        """

        if self.eof:
            return None

        next_tkn = self.peek()
        # True when kind is a TokenKind enum
        is_kind = isinstance(kind, TokenKind)
        # Check if it's of the same kind (when kind is TokenKind)
        # or of the same type (when kind is a type)
        if (is_kind and next_tkn.kind == kind) or (not is_kind and isinstance(next_tkn, kind)):
            return self.consume()
        else:
            return None

    def move(self, to: int):
        """
        Moves the cursor to the given index. Returns the token at that index, or None if EOF.
        Also updates the EOF flag.
        """

        # Make sure we aren't moving to some bizarre index (negative or too big).
        if to < 0 or to > len(self.tokens):
            raise ValueError(f"Attempted to move to an invalid index: {to} (max: {len(self.tokens)})")

        # Update the cursor and EOF flag. Return the token.
        self.cursor = to
        self.eof = self.cursor == len(self.tokens)
        return self.peek()


def parse(tokens: list[Token], problems: ProblemSet) -> Program:
    """
    Parses the given list of tokens and returns the root Program node.
    """
    return Parser(tokens, problems).parse()
