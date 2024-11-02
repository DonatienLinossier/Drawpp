from typing import overload

from pydpp.compiler.syntax import *
from pydpp.compiler.tokenizer import *

# =============================================================================
# parser.py: The magic parser transforming tokens into a syntax tree
# =============================================================================

N = TypeVar("N", bound=InnerNode)

class _Parser:
    """
    Takes a list of tokens, and processes it to create a syntax tree from it.

    Handles errors by making up fake nodes ("error expressions").

    It has a similar structure as the tokenizer, with the same cursor system.
    """

    __slots__ = ("tokens", "tok_positions", "cursor", "eof", "eof_token", "eof_idx")

    def __init__(self, tokens: list[Token], problems: ProblemSet):
        if len(tokens) == 0 or tokens[-1].kind != TokenKind.EOF:
            raise ValueError("The last element of the token list should be an EOF token.")

        self.tokens = tokens
        "The list of tokens to parse."
        self.cursor = 0
        "The index of the next token to read. If it's equal to len(tokens), we've reached the end of the file."
        self.eof = len(tokens) == 1
        "Whether we've reached the end of the file."
        self.eof_token = tokens[-1]
        "The last token: the end-of-file token."
        self.eof_idx = len(tokens) - 1
        "The index of the EOF token."

    def parse(self):
        """
        Parses the list of tokens, and returns the root Program node.
        """
        if self.eof:
            # We have no tokens! Return an empty program.
            return Program([], leaf(self.eof_token))

        # The list of statements that make up the program.
        program_statements = []

        # Keep track of the sequence of tokens that don't make a valid statement.
        invalid_tokens = []

        def flush_invalid_tokens():
            if len(invalid_tokens) > 0:
                program_statements.append(self.make_error_stmt(invalid_tokens))
                invalid_tokens.clear()

        # Keep reading tokens until we're finished.
        while not self.eof:
            # Try reading a statement
            if stmt := self.parse_statement():
                # Got one! Get rid of the invalid tokens (non-statement) if we got some.
                flush_invalid_tokens()
                program_statements.append(stmt)
            else:
                # That token wasn't recognized as a statement, add it to the unrecognized pile.
                tkn = self.consume()
                if tkn:
                    invalid_tokens.append(tkn)

        # If we have some invalid tokens left, report them as an error.
        flush_invalid_tokens()

        # Make the Program node, and return it!
        return Program(program_statements, leaf(self.eof_token))

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
            return stmt.with_problems(InnerNodeProblem("Bloc « else » sans « if » correspondant."))
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
            if_problems = []

            # We got an if keyword, try looking for a condition.
            condition = self.parse_expression()
            if condition is None:
                # No condition, keep it null
                if_problems.append(InnerNodeProblem(message="Condition manquante après un « if ».",
                                                    slot=IfStmt.condition_slot))

            block = self.parse_block_statement()
            if block is None:
                # No block?? Keep it null
                if_problems.append(InnerNodeProblem(message="Bloc d'instructions manquant après un « if ».",
                                                    slot=IfStmt.then_block_slot))

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
                    prob = InnerNodeProblem(f"Bloc « {block_name} » situé après un « else » existant.")
                    else_stmt.with_problems(prob)
                else:
                    saw_final_else = else_stmt.condition is None

            return IfStmt(leaf(if_kw), condition, block, elses).with_problems(*if_problems)

    def parse_else_statement(self) -> Optional[ElseStmt]:
        """
        Parses the next incoming else statement.
        """

        if else_kw := self.consume_exact(TokenKind.KW_ELSE):
            problems = []

            # We got an else keyword, try looking for a condition if we need one
            condition = None
            if if_kw := self.consume_exact(TokenKind.KW_IF):
                condition = self.parse_expression()
                if condition is None:
                    # No condition found despite it being "else if"
                    problems.append(InnerNodeProblem(message="Condition manquante après un « else if ».",
                                                     severity=ProblemSeverity.ERROR,
                                                     slot=ElseStmt.condition_slot))

            block = self.parse_block_statement()
            if block is None:
                # No block?? Make none!
                name = "else if" if condition else "else"
                problems.append(InnerNodeProblem(message=f"Bloc d'instructions manquant après un « {name} ».",
                                                 severity=ProblemSeverity.ERROR,
                                                 slot=ElseStmt.block_slot))

            # Make the node and return it.
            return ElseStmt(leaf(else_kw), leaf(if_kw), condition, block).with_problems(*problems)

        return None

    def parse_block_statement(self) -> Optional[BlockStmt]:
        """
        Parses the next incoming block statement.
        """

        # Make sure we start the block with a left brace: {
        if (lbrace := self.consume_exact(TokenKind.SYM_LBRACE)) is None:
            return None

        statements: list[Statement] = []
        problems = []

        # Keep track of the sequence of tokens that don't make a valid statement.
        # (copied from parse)
        invalid_tokens = []

        def flush_invalid_tokens():
            if len(invalid_tokens) > 0:
                statements.append(self.make_error_stmt(invalid_tokens))
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

        rbrace = None
        if nxt:  # Then it must be a SYM_RBRACE if we stop there
            rbrace = self.consume()
        else:
            # EOF, no closing brace! Report an error
            problems.append(InnerNodeProblem("Bloc d'instructions non fermé."))

        flush_invalid_tokens()

        return BlockStmt(leaf(lbrace), statements, leaf(rbrace)).with_problems(*problems)

    def parse_function_call_statement(self):
        """
        Parses the next incoming function call statement.
        """

        if fc := self.parse_function_expression():
            problems = []
            sm = self.expect_semicolon_2(problems, FunctionCallStmt.semi_colon_slot)
            return FunctionCallStmt(fc, leaf(sm)).with_problems(*problems)
        else:
            return None

    def parse_variable_declaration_statement(self) -> Optional[VariableDeclarationStmt]:
        """
        Parses the next incoming variable declaration.
        """

        # If come across a type, it's a variable declaration beginning.
        if var_type := self.parse_built_in_type():
            problems = []

            # Then we need to find the identifier of the variable.
            if ident := self.consume_exact(TokenKind.IDENTIFIER):
                # Let's see if there's an assignment or not.
                value = None
                if assign := self.consume_exact(TokenKind.SYM_ASSIGN):
                    # We have an assignment operator, now we need to find the value.
                    value = self.parse_expression()
                    if value is None:
                        problems.append(InnerNodeProblem(message="Valeur manquante après l'assignation '='.",
                                                         severity=ProblemSeverity.ERROR,
                                                         slot=VariableDeclarationStmt.assign_token_slot))

                sm = self.expect_semicolon_2(problems, VariableDeclarationStmt.semi_colon_slot)
                return VariableDeclarationStmt(var_type, leaf(ident), leaf(assign), value, leaf(sm)).with_problems(*problems)
            else:
                # No identifier? Then it'll be None.
                problems.append(InnerNodeProblem(message="Identificateur manquant après le type de variable.",
                                                 severity=ProblemSeverity.ERROR,
                                                 slot=VariableDeclarationStmt.name_token_slot))

                sm = self.expect_semicolon_2(problems, VariableDeclarationStmt.semi_colon_slot)
                return VariableDeclarationStmt(var_type, None, None, None, leaf(sm)).with_problems(*problems)

    def parse_assign_statement(self):
        """
        Parses the next incoming assignment statement.
        """

        # First we need to make sure that we have an identifier and an assignment operator.
        if (ident := self.peek()) and (assign := self.peek(skip=1)):
            if ident.kind == TokenKind.IDENTIFIER and assign.kind == TokenKind.SYM_ASSIGN:
                # Consume both identifier and assignment tokens.
                self.consume()
                self.consume()

                problems = []
                if (val := self.parse_expression()) is None:
                    # No expression after the equal sign: keep it None and report an error.
                    problems.append(InnerNodeProblem(message="Valeur manquante après l'assignation '='.",
                                                     severity=ProblemSeverity.ERROR,
                                                     slot=AssignStmt.value_slot))

                sm = self.expect_semicolon_2(problems, AssignStmt.semi_colon_slot)
                return AssignStmt(leaf(ident), leaf(assign), val, leaf(sm)).with_problems(*problems)

        return None

    def parse_while_statement(self):
        """
        Parses the next incoming while statement.
        """

        if while_kw := self.consume_exact(TokenKind.KW_WHILE):
            problems = []

            # We got a while keyword, try looking for a condition.
            condition = self.parse_expression()
            if condition is None:
                problems.append(InnerNodeProblem(message="Condition manquante après un « while ».",
                                                 severity=ProblemSeverity.ERROR,
                                                 slot=WhileStmt.condition_slot))

            block = self.parse_block_statement()
            if block is None:
                problems.append(InnerNodeProblem(message="Bloc d'instructions manquant après un « while ».",
                                                 severity=ProblemSeverity.ERROR,
                                                 slot=WhileStmt.block_slot))

            return WhileStmt(leaf(while_kw), condition, block).with_problems(*problems)
        else:
            return None

    def expect_semicolon_2(self, problems: list[InnerNodeProblem], sm_slot: SingleNodeSlot[InnerNode, LeafNode]) -> Token | None:
        """
        Consumes the incoming semicolon token. Errors out if not present.
        """
        if tkn := self.consume_exact(TokenKind.SYM_SEMICOLON):
            # We have a semicolon, all good, return its position.
            return tkn
        else:
            # We don't! Report and error and given the position of the last parsed token.
            problems.append(InnerNodeProblem(message="Point-virgule manquant à la fin d'une instruction.",
                                             severity=ProblemSeverity.ERROR,
                                             slot=sm_slot))
            return None

    def parse_built_in_type(self):
        """
        Parses the next built-in type node (int, float, etc.).
        """
        if self.eof:
            return None

        # Try all possible matching type keywords.
        match self.peek().kind:
            case TokenKind.KW_INT | TokenKind.KW_FLOAT | TokenKind.KW_STRING | TokenKind.KW_BOOL:
                tkn = self.consume()
                return BuiltInType(leaf(tkn))
            case _:
                return None

    # Precedence of all binary operators, from lowest to highest.
    # Precedence is what tells which expression is evaluated first. As in a+b*c, b*c is evaluated first.
    # The higher the precedence, deeper it is present in the syntax tree.
    # Inversely, a low precedence means it's higher up in the tree.
    op_to_prec = {
        TokenKind.KW_OR: 0,
        TokenKind.KW_AND: 1,
        TokenKind.SYM_EQ: 2,
        TokenKind.SYM_NEQ: 2,
        TokenKind.SYM_LT: 2,
        TokenKind.SYM_LEQ: 2,
        TokenKind.SYM_GT: 2,
        TokenKind.SYM_GEQ: 2,
        TokenKind.SYM_PLUS: 3,
        TokenKind.SYM_MINUS: 3,
        TokenKind.SYM_STAR: 4,
        TokenKind.SYM_SLASH: 4
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
        def binary_op_left_assoc(lhs, min_prec: int = 0):
            prec = None

            # Continue reading operators until we find one of lower precedence, in that is the case,
            # the parent function call will take over reading expressions of lower precedence.
            while (operator := self.peek()) and (prec := _Parser.op_to_prec.get(operator.kind)) is not None and prec >= min_prec:
                # Consume the operator we've just read
                self.consume()

                # Read the RHS, and make one up if it's not there.
                rhs = non_binary_expr()
                if rhs is None:
                    # Unsure what to do here. Exceptionally using an empty ErrorExpr.
                    rhs = ErrorExpr([]).with_problems(InnerNodeProblem(
                        f"Opérande de droite manquante après l'opérateur « {operator} » "))

                # If the next operator is one of HIGHER precedence, then "pause" this function's execution,
                # and leave it to another call that will read all operators of higher precedence.
                prec2 = None
                if (op2 := self.peek()) and (prec2 := _Parser.op_to_prec.get(op2.kind)) and prec2 > prec:
                    # Make sure to give it the RHS we got as *its* LHS.
                    # For instance, we can be reading 5+6*, while being at the '*' operator, with '+' having RHS=6
                    # Then, the '*' expression should have an LHS of 6.
                    rhs = binary_op_left_assoc(rhs, prec2)

                # If we didn't enter the loop above, that means we've read an operator of same precedence,
                # or that we don't have operators anymore.

                # Associate the LHS with the RHS we've read.
                lhs = BinaryOperationExpr(lhs, leaf(operator), rhs)

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

            problem = None

            # Check if we have "-" or "and"
            op = self.peek()
            if op is None or op.kind != TokenKind.SYM_MINUS and op.kind != TokenKind.KW_NOT:
                return None

            # We got a '-' or 'not' prefix! Consume it and get the next incoming expression.
            self.consume()
            expression = non_binary_expr()
            if expression is None:
                # No expression following the prefix? Error out.
                problem = InnerNodeProblem(message=f"Expression manquante après « {op} » ",
                                           severity=ProblemSeverity.ERROR,
                                           slot=UnaryExpr.op_token_slot)

            # Create the according expression node.
            return UnaryExpr(leaf(op), expression).with_problems(problem)

        def parenthesized():
            """Recognizes parenthesized expressions, like (expr)."""

            # See if we have an opening parenthesis coming.
            # If so, we're going to start a parenthesized expression.
            if lparen := self.consume_exact(TokenKind.SYM_LPAREN):
                problems = []

                # Read the incoming expression (not just non_binary, all kinds!)
                expr = self.parse_expression()

                if not expr:
                    # We didn't find one? Make it none
                    problems.append(InnerNodeProblem(message="Expression manquante après une parenthèse ouvrante.",
                                                     severity=ProblemSeverity.ERROR,
                                                     slot=ParenthesizedExpr.expr_slot))

                # Find the closing parenthesis and we're done!
                if (rparen := self.consume_exact(TokenKind.SYM_RPAREN)) is None:
                    # Unfinished parenthesized expression! Make it None.
                    problems.append(InnerNodeProblem(
                        message="Parenthèse fermante manquante après une expression entre parenthèses.",
                        severity=ProblemSeverity.ERROR,
                        slot=ParenthesizedExpr.rparen_token_slot))

                return ParenthesizedExpr(leaf(lparen), expr, leaf(rparen)).with_problems(*problems)
            else:
                return None

        def variable():
            """Recognizes variable expressions, like myVar, cool_var."""
            # See if we have an identifier coming, and if so that's a variable expression.
            if ident := self.consume_exact(TokenKind.IDENTIFIER):
                return VariableExpr(leaf(ident))
            else:
                return None

        def literal():
            """Recognizes literal expressions, like 5, "hello", true."""
            # Try all kinds of literals we know. Order has no importance.
            tkn = self.peek()
            match tkn.kind:
                case TokenKind.LITERAL_NUM | TokenKind.LITERAL_STRING | TokenKind.LITERAL_BOOL:
                    self.consume()
                    return LiteralExpr(leaf(tkn))

        # Start reading the expression.
        l = non_binary_expr()
        if l:
            return binary_op_left_assoc(l)
        else:
            return None

    def parse_function_expression(self) -> Optional[FunctionExpr]:
        if (ident := self.peek()) and ident.kind == TokenKind.IDENTIFIER \
                and ((lparen := self.peek(skip=1)) and lparen.kind == TokenKind.SYM_LPAREN):
            ident = self.consume()
            arg_list = self.parse_arg_list()

            # TODO: Err if arg list empty

            return FunctionExpr(leaf(ident), arg_list)

    def parse_arg_list(self) -> Optional[ArgumentList]:
        # Find the (possibly) identifier token and opening parenthesis "(" token
        lparen = self.peek()  # (
        if lparen and lparen.kind == TokenKind.SYM_LPAREN:
            # Consume token (paren)
            self.consume()

            # All arguments we've found.
            args = []

            # Continue reading the argument list until we find a closing parenthesis or a semicolon.
            # NOTE: The semicolon check is a bit of a weird choice, we might just give up reading the list
            # instead of waiting for an end of statement.
            while (nxt := self.peek()) and nxt.kind != TokenKind.SYM_RPAREN and nxt.kind != TokenKind.SYM_SEMICOLON:
                # Then we must have an expression coming next. Try to read it.
                arg = self.parse_expression()
                if not arg:
                    # TODO: Err if no expression
                    erroneous = []
                    while ((nxt := self.peek())
                           and nxt.kind != TokenKind.SYM_RPAREN
                           and nxt.kind != TokenKind.SYM_SEMICOLON
                           and nxt.kind != TokenKind.SYM_COMMA):
                        erroneous.append(leaf(self.consume()))
                    arg = ErrorExpr(erroneous)

                # TODO: Err if comma missing
                n = self.consume_exact(TokenKind.SYM_COMMA)
                args.append(Argument(arg, leaf(n) if n else None))

            rparen = self.consume_exact(TokenKind.SYM_RPAREN)
            # TODO: Err if rparen missing
            return ArgumentList(leaf(lparen), args, leaf(rparen))

    def make_error_expr(self, tokens: list[Token]) -> ErrorExpr:
        """
        Makes an error expression from a list of tokens.
        """
        return ErrorExpr(leaf(t) for t in tokens).with_problems(InnerNodeProblem("Expression invalide."))

    def make_error_stmt(self, tokens: list[Token]) -> ErrorStmt:
        """
        Makes an error statement from a list of tokens.
        """
        return ErrorStmt(leaf(t) for t in tokens).with_problems(InnerNodeProblem("Instruction invalide."))

    def peek(self, skip=0):
        """
        Returns the next incoming token without consuming it.

        The ``skip`` parameter can be specified to skip N characters.

        Can return None if the next token is the EOF token.
        """
        if self.cursor + skip >= self.eof_idx:
            return None
        return self.tokens[self.cursor + skip]

    def consume(self):
        """
        Consumes the next incoming token, and advances the cursor by one.
        Returns the consumed token, or None if the next token is the EOF token.
        """
        if self.eof:  # <==> self.cursor == len(self.tokens) - 1
            return None

        # Store the token to return it and advance the cursor by one.
        tok = self.tokens[self.cursor]
        self.cursor += 1
        self.eof = self.cursor == self.eof_idx
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
        if to < 0 or to > self.eof_idx:
            raise ValueError(f"Attempted to move to an invalid index: {to} (max: {self.eof_idx})")

        # Update the cursor and EOF flag. Return the token.
        self.cursor = to
        self.eof = self.cursor == self.eof_idx
        return self.peek()


def parse(tokens: list[Token], problems: ProblemSet) -> Program:
    """
    Parses the given list of tokens and returns the root Program node.
    """
    return _Parser(tokens, problems).parse()
