from pydpp.compiler.semantic import *
from pydpp.compiler.syntax import *
# TODO: _Cursor seems to be internal, maybe rework this a little bit so I don't feel like an outright criminal?
from pydpp.compiler.CTranslater import CTranslater, VarCall, _Cursor


# ======================================================
# transpiler.py: The transpiler producing C code
# ======================================================

def transpile(program: Program, semantic_info: ProgramSemanticInfo, file_name: str):
    """
    Produces working C code to run the program, which should have been
    successfully parsed and semantically analysed beforehand.

    There must have been no errors during the compilation pipeline. If there's one,
    the function will fail and raise an error.

    :param program: The root node of the AST
    :param semantic_info: The semantic information of the program
    :param file_name: The name of the file to write the C code to
    """

    # Exit the function if we have any errors, or if we don't have semantic info
    if program.has_problems:
        raise RuntimeError("Cannot transpile a program with parsing or semantic errors.")
    elif semantic_info is None:
        raise RuntimeError("Cannot transpile a program without complete semantic analysis.")

    # Create the translator that serves as the basis for actually outputting C code :o
    ct = CTranslater(file_name)

    # Variable naming guide:
    # - Intermediary variables: ${n}: $1, $2, $3, ...
    # - Function names: @{name}
    # - Variable names: %{name}
    # - Internal names: !{name}

    # Create the default cursor, used when there's no active "wield" going on.
    default_cursor_var = "!default_cursor"
    ct.add_instruction("createCursor", default_cursor_var, 0, 0, 0, 0, 0, 0, 255)

    # The stack of all cursors. When we encounter a "wield" statement, we push the cursor it uses
    # (into an intermediate variable if necessary), and once it's done, we pop the stack.
    # Of course, this stack shouldn't be empty at any case!
    cursor_stack = [default_cursor_var]

    var_i = 0
    # Creates a brand-new intermediate variable name, by incrementing a counter.
    def next_intermediate_var():
        nonlocal var_i
        var_i += 1
        return f"${var_i}"

    # Converts a variable/parameter symbol to the interpreter/translater name.
    def val_sym_to_translater(sym: ValueSym) -> str:
        # Use a forbidden character to make sure conflicts won't happen!
        return "%" + sym.name

    # Converts a function symbol name to its interpreter/translater name.
    def func_sym_to_translater(sym: FunctionSym) -> str:
        # Use a forbidden character to make sure conflicts won't happen!
        return "@" + sym.name

    # Runs an instruction and stores its return value in a variable.
    def translater_store(target_var: str, instr: str, *args) -> VarCall:
        ct.add_instruction(instr, *args)
        ct.add_instruction("storeReturnedValueFromFuncInVar", target_var)
        return VarCall(target_var)

    # Runs an instruction and stores its return value in an intermediate variable.
    # Returns the newly made intermediate variable as a VarCall object.
    def translater_store_temp(instr: str, *args) -> VarCall:
        return translater_store(next_intermediate_var(), instr, *args)

    # Pushes a cursor onto the cursor stack. Can be either a temporary cursor or a variable.
    def push_cursor(cursor_expr: VarCall | _Cursor._Cursor) -> VarCall:
        if not isinstance(cursor_expr, VarCall):
            # In case we're using a temporary cursor, let's put it in a temporary variable.
            var = translater_store_temp("createVar", cursor_expr)
        else:
            # Just reuse the variable already present in the code.
            var = cursor_expr

        cursor_stack.append(var.name)
        return VarCall(var)

    # Pops a cursor from the cursor stack. Won't let you pop the default cursor.
    def pop_cursor():
        if len(cursor_stack) == 1:
            raise RuntimeError("Cannot pop the default cursor from the stack.")

        cursor_stack.pop()

    # Evaluates an expression, and emits all instructions necessary to compute it.
    # When the expression can be evaluated at compile-time, (like in "5+8", "not true") returns the constant result.
    #
    # This function gives either:
    # - a VarCall object:
    #       the expression *is* a variable OR needs to be stored in an intermediate variable
    # - anything else not-None (int, float, str, bool):
    #       the expression can be computed at compile-time.
    # - None:
    #       the expression is a function call returning nothing.
    def evaluate_expression(e: Expression) -> VarCall | int | float | str | bool | None:
        if isinstance(e, LiteralExpr):
            # Just a literal, return this constant value
            return e.token.value
        elif isinstance(e, VariableExpr):
            # Find the variable symbol from the expression.
            sym = semantic_info.expr_to_sym[e].referenced_symbol
            assert isinstance(sym, VariableSym) or isinstance(sym, ParameterSym)

            if isinstance(sym, VariableSym) and sym.built_in_val is not None:
                # Built-in variable, return its constant value.
                return sym.built_in_val

            # Return the VarCall to evaluate the variable/parameter.
            return VarCall(val_sym_to_translater(sym))
        elif isinstance(e, ParenthesizedExpr):
            # Return the expression within the parentheses.
            return evaluate_expression(e.expr)
        elif isinstance(e, UnaryExpr):
            value = evaluate_expression(e.expr)

            if isinstance(value, VarCall):
                # *NOT* a constant value, we need to output interpreter instructions
                if e.op_token.kind == TokenKind.KW_NOT:
                    return translater_store_temp("isNot", value)
                elif e.op_token.kind == TokenKind.SYM_MINUS:
                    return translater_store_temp("subtract", 0, value)
            else:
                # Constant value, can be computed at compile-time
                if e.op_token.kind == TokenKind.KW_NOT:
                    return not value
                elif e.op_token.kind == TokenKind.SYM_MINUS:
                    return -value
        elif isinstance(e, BinaryOperationExpr):
            # Evaluate both sides of the operation
            left = evaluate_expression(e.left)
            right = evaluate_expression(e.right)

            # See if at least one of them is a variable.
            if isinstance(left, VarCall) or isinstance(right, VarCall):
                # Not a constant, emit instructions to compute the result
                match e.operator_token.kind:
                    case TokenKind.KW_OR:
                        return translater_store_temp("or", left, right)
                    case TokenKind.KW_AND:
                        return translater_store_temp("and", left, right)
                    case TokenKind.SYM_EQ:
                        return translater_store_temp("equals", left, right)
                    case TokenKind.SYM_NEQ:
                        return translater_store_temp("notEquals", left, right)
                    case TokenKind.SYM_LT:
                        return translater_store_temp("lowerThan", left, right)
                    case TokenKind.SYM_LEQ:
                        return translater_store_temp("lowerThanOrEquals", left, right)
                    case TokenKind.SYM_GT:
                        return translater_store_temp("greaterThan", left, right)
                    case TokenKind.SYM_GEQ:
                        return translater_store_temp("greaterThanOrEquals", left, right)
                    case TokenKind.SYM_PLUS:
                        return translater_store_temp("add", left, right)
                    case TokenKind.SYM_MINUS:
                        return translater_store_temp("subtract", left, right)
                    case TokenKind.SYM_STAR:
                        return translater_store_temp("multiply", left, right)
                    case TokenKind.SYM_SLASH:
                        return translater_store_temp("divide", left, right)
            else:
                # Constant values, can be computed at compile-time
                match e.operator_token.kind:
                    case TokenKind.KW_OR:
                        return left or right
                    case TokenKind.KW_AND:
                        return left and right
                    case TokenKind.SYM_EQ:
                        return left == right
                    case TokenKind.SYM_NEQ:
                        return left != right
                    case TokenKind.SYM_LT:
                        return left < right
                    case TokenKind.SYM_LEQ:
                        return left <= right
                    case TokenKind.SYM_GT:
                        return left > right
                    case TokenKind.SYM_GEQ:
                        return left >= right
                    case TokenKind.SYM_PLUS:
                        return left + right
                    case TokenKind.SYM_MINUS:
                        return left - right
                    case TokenKind.SYM_STAR:
                        return left * right
                    case TokenKind.SYM_SLASH:
                        return left / right
        elif isinstance(e, FunctionExpr):
            # Find the associated function.
            sym = semantic_info.expr_to_sym[e].referenced_symbol
            assert isinstance(sym, FunctionSym)

            # Evaluate all the arguments.
            args = []
            ast_args = [a.expr for a in e.arg_list.arguments] # List of all expressions nodes
            for i in range(len(sym.parameters)):
                args.append(evaluate_expression_type_conv(ast_args[i], sym.parameters[i].type))

            # Find our current cursor for this function.
            if e.wielded_expr is not None:
                # We have a wield expression, let's use that given cursor.
                current_cursor = evaluate_expression(e.wielded_expr)
            else:
                # We don't have one, use the one on the top of the stack.
                current_cursor = VarCall(cursor_stack[-1])

            if sym.node is not None:
                # User defined functions: also add the current cursor as the function's default cursor.
                # The function runs under its own cursor stack, so there's no need to do anything about it.
                args.append(current_cursor)
            else:
                # That will depend on the built-in function. Some use cursors, some don't. See the
                # match case below.
                pass

            result = None
            if sym.node is None:
                # Built-in function, run instructions based on the function name.
                match sym.c_func_name:
                    case "cursorDrawCircle" | "cursorDrawFilledCircle" | "cursorJump" | "cursorChangeColor":
                        ct.add_instruction(sym.c_func_name, current_cursor, *args)
                        result = None

                # TODO: More functions!
            else:
                # User function, run it, and store the result in an intermediate variable
                # (only if the return type isn't nothing).
                if sym.return_type == SemanticType.NOTHING:
                    ct.add_instruction(func_sym_to_translater(sym), *args)
                    result = None
                else:
                    result = translater_store_temp(func_sym_to_translater(sym), *args)

            return result

    # Same as evaluate_expression, but also applies type conversion if necessary.
    def evaluate_expression_type_conv(expr: Expression, target_type: SemanticType) \
        -> VarCall | int | float | str | bool | None:
        # Evaluate the expression and find its associated symbol
        val = evaluate_expression(expr)
        sym = semantic_info.expr_to_sym[expr]

        if sym.type == target_type:
            # Same type, nothing to convert
            return val
        else:
            # Not the same type! Apply the *only* type conversion we have in the language...
            if target_type == SemanticType.FLOAT and sym.type == SemanticType.INT:
                # Convert an int to a float
                if isinstance(val, VarCall):
                    # This is very hacky, but due to the way it works in Python,
                    # adding a float will convert it to a float. Funny...
                    # TODO: NO THAT'S NOT VERY FUNNY! Find some cleaner way of doing that.
                    ct.add_instruction("addToVar", val.name, 0.0)
                    return val
                else:
                    return float(val)
            else:
                raise NotImplementedError(f"Type conversion from {sym.type} to {target_type} is not implemented.")

    # Returns the default value of the given type
    def default_value(t: SemanticType) -> int | float | str | bool | None:
        match t:
            case SemanticType.BOOL:
                return False
            case SemanticType.INT:
                return 0
            case SemanticType.FLOAT:
                return 0.0
            case SemanticType.STRING:
                return ""

        return None

    # Transforms a statement into translater instructions, to output C code.
    def transpile_statement(s: Statement):
        # Allow us to change the cursor stack entirely
        nonlocal cursor_stack

        if isinstance(s, AssignStmt):
            # Grab the symbol for this assignment
            sym = semantic_info.assign_to_sym[s]
            assert sym.variable is not None and sym.value is not None

            # Use the assignateValueToVar instruction to assign the value to the variable.
            ct.add_instruction("assignateValueToVar",
                               val_sym_to_translater(sym.variable),
                               evaluate_expression_type_conv(s.value, sym.variable.type))
        elif isinstance(s, VariableDeclarationStmt):
            sym = semantic_info.variable_to_sym[s]

            if sym.type == SemanticType.CURSOR:
                # Special handling for cursors: create a cursor using the createCursor instruction.
                # They can't have values assign to anyway.
                ct.add_instruction("createCursor", val_sym_to_translater(sym),
                                   0, 0, 0, 0, 0, 0, 1)
            else:
                # Find the value we should initialise the variable with.
                if s.value is not None:
                    # There's a value, evaluate it
                    val = evaluate_expression_type_conv(s.value, sym.type)
                else:
                    # Use the default value (usually zero).
                    val = default_value(sym.type)

                ct.add_instruction("createVar",
                                   val_sym_to_translater(sym),
                                   val)
        elif isinstance(s, FunctionCallStmt):
            # Just evaluate the function call, and ignore its return value.
            evaluate_expression(s.expr)
        elif isinstance(s, BlockStmt):
            # TODO: Actually have *real* block scope semantics. Right now we can only
            #       create scopes for functions and if/else/while blocks.
            #       This might cause issues with variable scoping.
            for st in s.statements:
                transpile_statement(st)
        elif isinstance(s, FunctionDeclarationStmt):
            # Fetch its associated symbol
            sym = semantic_info.function_to_sym[s]
            assert sym.node is not None

            # Configure the parameters to also have a "cursor" as an input.
            # The cursor will be called !default_cursor, so we can easily use the same variable name over and over,
            # and will be set to the current cursor when calling the function.
            params = [val_sym_to_translater(p) for p in sym.parameters]
            params.append(default_cursor_var)

            # Create the function using the translater.
            ct.createFunc(func_sym_to_translater(sym), params)

            # Now that we're inside another scope/block, we have a whole new cursor stack for this function.
            # So, let's replace the cursor stack with the "default" one.
            prev_stack = cursor_stack
            cursor_stack = [default_cursor_var]

            # Transpile all statements inside the body.
            for st in s.body.statements:
                transpile_statement(st)

            # Exit the block.
            ct.endBlock()

            # Restore the previous cursor stack.
            cursor_stack = prev_stack
        elif isinstance(s, IfStmt):
            # Let's create the if block. The translater expects us to write all branches (cond eval, if, else).

            # 1. Condition if(...)
            ct.createConditionalInstr()
            ct.add_instruction("functReturnStatement", evaluate_expression(s.condition))
            ct.endBlock()

            # 2. If block
            for st in s.then_block.statements:
                transpile_statement(st)
            ct.endBlock()

            # 3. Else block
            # Now that's where it gets tricky.

            # To make "chained" else-if statements, we need to decompose it into nested if/else blocks.
            # Example:
            # if a: doA                                if a: doA
            # elif b: doB         ------>              else:
            # elif c: doC                                  if b: doB
            # else: doD                                    else:
            #                                                  if c: doC
            #                                                  else: doD

            # This functions helps us do that to create a new block with:
            # - the condition filled in
            # - the "then" block filled in
            # - a missing else block.
            def make_partial_if(es: ElseStmt):
                # Create a partial if block for the else statement.
                ct.createConditionalInstr()
                ct.add_instruction("functReturnStatement", evaluate_expression(es.condition))
                ct.endBlock()

                # Transpile the statements inside the block.
                for st in es.block.statements:
                    transpile_statement(st)

                # End the block.
                ct.endBlock()

                # Then, we have the "else" block that will be filled later

            # Number of "else-if" blocks we've seen
            elif_blocks = 0
            for else_st in s.else_statements:
                if else_st.condition is not None:
                    # We'll need to make a new *partial* if block for this, we'll have:
                    # if (else_if_condition) {
                    #    else_if_statements
                    # } else {
                    #    ... (whatever comes up next)
                    # }
                    make_partial_if(else_st)

                    # The next statements (of an else/else-if block) will be located inside
                    # this "else" block. This might be the last else-if, which is okay, the else block will be empty.
                    # We'll have to call endBlock once more.
                    elif_blocks += 1
                else:
                    # No condition, it's the final else block. Since we're in an "else" transpiler block,
                    # add its statements.
                    for st in else_st.block.statements:
                        transpile_statement(st)

            # End the root else block, even if it's empty
            ct.endBlock()

            # End all transpiler "else" blocks we had to create for else-if statements.
            for i in range(elif_blocks):
                ct.endBlock()
        elif isinstance(s, WhileStmt):
            # Create a while loop block
            ct.createWhileLoop()

            # Set the condition
            ct.add_instruction("functReturnStatement", evaluate_expression(s.condition))
            ct.endBlock()

            # Transpile the statements inside the loop
            for st in s.block.statements:
                transpile_statement(st)

            # End the block
            ct.endBlock()
        elif isinstance(s, WieldStmt):
            # Push the cursor, run the statements, and pop it.
            push_cursor(evaluate_expression(s.expr))
            transpile_statement(s.block)
            pop_cursor()
        elif isinstance(s, CanvasStmt):
            # Nothing special to do, it's handled at the beginning of the transpilation since
            # the relevant data is in ProgramSemanticInfo anyway.
            pass
        else:
            raise NotImplementedError(f"Transpiling of {s.__class__.__name__} statements is not implemented.")

    # Use a "with" block to close the file when we're done.
    with ct:
        # Set the canvas width and height if we have some defined.
        if semantic_info.canvas_width is not None and semantic_info.canvas_height is not None:
            ct.configure_canvas(semantic_info.canvas_width, semantic_info.canvas_height)

        # Before transpiling anything, transpile all functions first.
        for statement in program.statements:
            if isinstance(statement, FunctionDeclarationStmt):
                transpile_statement(statement)

        # Transpile every statement of the program, except functions.
        # This function will also transpile children statements, so no need to worry.
        for statement in program.statements:
            if not isinstance(statement, FunctionDeclarationStmt):
                transpile_statement(statement)

        # Run the interpreter code we've emitted to write the final C file.
        ct.run()