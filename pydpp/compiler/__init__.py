# All compiler functionality available to use within the IDE module.
# Import the pydpp.compiler module to use it!

# Don't import anything when we're running the codegen module,
# as this all those imports break the code if it isn't generated!
# noinspection PyCompatibility
import __main__

if __main__ is None or not hasattr(__main__, "__file__") or not __main__.__file__.endswith("codegen.py"):
    # ======================
    # IMPORTS
    # ======================
    # Import all useful types that the IDE module will take usage of.
    #
    # This means that the IDE module will be able to import those types easily, for example this works:
    #   from pydpp.compiler import ProblemSet, FileSpan
    from .problem import ProblemSet, Problem, ProblemSeverity
    from .position import FileCoordinates, FileSpan
    from .tokenizer import tokenize
    from .parser import parse
    from .semantic import analyse
    from .transpiler import transpile

    # Make all submodules available when importing the compiler module
    from . import problem, position, tokenizer, semantic, syntax, transpiler, types, transpiler, CTranslater


    # ======================
    # FUNCTIONS
    # ======================
    # Functions that the IDE module will be able to use to do various stuff with code.

    # Draft version of the compilation pipeline, returns the path to the exe, or None if there was an error
    def compile_code(code) -> tuple[str | None, ProblemSet]:
        # Create a problem set to contain all errors during the compilation pipeline
        ps = ProblemSet()
        # Tokenize the code, and get a list of tokens
        tokens = tokenize(code, ps)
        # Take that list of tokens, and parse it to make a syntax tree
        program = parse(tokens, ps)
        # Do some semantic analysis on the tree, to check/compute types and references
        semantic_info = analyse(program, ps)

        # If we have an error, we can't transpile and compile, so return no path
        if len(ps.grouped[ProblemSeverity.ERROR]) > 0:
            return None, ps

        # Generate the C code that will run the program's instructions
        c_code = transpile(program, semantic_info, ps)

        # And then...? We need to compile an EXE, and call CMake/gcc whatever!
        raise NotImplementedError("To be continued...!")
