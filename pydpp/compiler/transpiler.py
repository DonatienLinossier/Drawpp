from pydpp.compiler.semantic import *
from pydpp.compiler.syntax import *
from pydpp.compiler.CTranslater import CTranslater, VarCall


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
        raise RuntimeError("Cannot transpile a program with parsing errors.")
    elif semantic_info is None:
        raise RuntimeError("Cannot transpile a program without complete semantic analysis.")

    # Create the translator that serves as the basis for actually outputting C code :o
    ct = CTranslater(file_name)

    # Name guide:
    # - Intermediary variables: ${n}: $1, $2, $3, ...
    # - Function names: @{name}
    # - Variable names: %{name}

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
        itd = next_intermediate_var()
        ct.add_instruction(instr, *args)
        ct.add_instruction("storeReturnedValueFromFuncInVar", itd)
        return VarCall(itd)

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

        # # Upgrades a constant value to an intermediate variable. Returns the variable if it's already one.
        # def upgrade_to_temp(v: VarCall | int | float | str | bool) -> VarCall:
        #     if not isinstance(v, VarCall):
        #         intermediate = next_intermediate_var()
        #         ct.add_instruction("createVar", intermediate, v)
        #         return VarCall(intermediate)
        #     else:
        #         return v

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

            if sym.node is None:
                # Built-in function, run instructions based on the function name.
                match sym.c_func_name:
                    case "drawpp_circle":
                        ct.add_instruction("drawCircle", *args)
                        return None

                # TODO: More functions!
            else:
                # User function, run it, and store the result in an intermediate variable
                # (only if the return type isn't nothing).
                if sym.return_type == BuiltInTypeKind.NOTHING:
                    ct.add_instruction(func_sym_to_translater(sym), *args)
                    return None
                else:
                    return translater_store_temp(func_sym_to_translater(sym), *args)

    # Same as evaluate_expression, but also applies type conversion if necessary.
    def evaluate_expression_type_conv(expr: Expression, target_type: BuiltInTypeKind) \
        -> VarCall | int | float | str | bool | None:
        # Evaluate the expression and find its associated symbol
        val = evaluate_expression(expr)
        sym = semantic_info.expr_to_sym[expr]

        if sym.type == target_type:
            # Same type, nothing to convert
            return val
        else:
            # Not the same type! Apply the *only* type conversion we have in the language...
            if target_type == BuiltInTypeKind.FLOAT and sym.type == BuiltInTypeKind.INT:
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
    def default_value(t: BuiltInTypeKind) -> int | float | str | bool | None:
        match t:
            case BuiltInTypeKind.BOOL:
                return False
            case BuiltInTypeKind.INT:
                return 0
            case BuiltInTypeKind.FLOAT:
                return 0.0
            case BuiltInTypeKind.STRING:
                return ""

        return None

    # Transforms a statement into translater instructions, to output C code.
    def transpile_statement(s: Statement):
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

            if sym.type == BuiltInTypeKind.CURSOR:
                # Special handling for cursors: create a cursor using the createCursor instruction.
                # They can't have values assign to anyway.
                ct.add_instruction("createCursor", val_sym_to_translater(sym))
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

            # Create the function using the translater.
            ct.createFunc(func_sym_to_translater(sym), [val_sym_to_translater(p) for p in sym.parameters])

            # Transpile all statements inside the body.
            for st in s.body.statements:
                transpile_statement(st)

            # Exit the block.
            ct.endBlock()
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
        else:
            raise NotImplementedError(f"Transpiling of {s.__class__.__name__} statements is not implemented.")


    for statement in program.statements:
        transpile_statement(statement)

    ct.run()