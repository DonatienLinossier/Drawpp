# All compiler functionality available to use within the IDE module.
# Import the pydpp.compiler module to use it!

# Don't import anything when we're running the codegen module,
# as this all those imports break the code if it isn't generated!
# noinspection PyCompatibility
import __main__

from .position import TextSpan
from .syntax import InnerNodeProblem

if __main__ is None or not hasattr(__main__, "__file__") or not __main__.__file__.endswith("codegen.py"):
    # ======================
    # IMPORTS
    # ======================
    # Import all useful types that the IDE module will take usage of.
    #
    # This means that the IDE module will be able to import those types easily, for example this works:
    #   from pydpp.compiler import ProblemSet, FileSpan
    from .problem import Problem, ProblemSeverity, ProblemSet
    from .tokenizer import tokenize, TokenProblem
    from .parser import parse
    from .semantic import analyse
    from .transpiler import transpile
    from .syntax import Node

    # Make all submodules available when importing the compiler module
    from . import problem, position, tokenizer, semantic, syntax, transpiler, types, transpiler, CTranslater


    # ======================
    # FUNCTIONS
    # ======================
    # Functions that the IDE module will be able to use to do various stuff with code.

    # Draft version of the compilation pipeline, returns the path to the exe, or None if there was an error
    def compile_code(code) -> tuple[str | None, ProblemSet]:
        problems = ProblemSet()

        # Tokenize the code, and get a list of tokens
        tokens = tokenize(code)
        # Take that list of tokens, and parse it to make a syntax tree
        program = parse(tokens)

        # Gather all problems from the parsing stage, and the tokenization stage as well
        collect_errors(program, problems)

        # Do some semantic analysis on the tree, to check/compute types and references
        semantic_info = analyse(program)

        # If we have an error, we can't transpile and compile, so return no path
        if len(problems.grouped[ProblemSeverity.ERROR]) > 0:
            return None, problems

        # Generate the C code that will run the program's instructions
        c_code = transpile(program, semantic_info)

        # And then...? We need to compile an EXE, and call CMake/gcc whatever!
        raise NotImplementedError("To be continued...!")

    def collect_errors(tree: Node, problems: ProblemSet):
        """
        Collects all errors (node/tokens) from a given syntax tree, into a problem set.
        :param tree: the tree with errors
        :param problems: the problem set to add the errors to
        """
        if tree.has_problems:
            stack = [tree]
            while stack:
                node = stack.pop()

                for p in node.problems:
                    if isinstance(p, InnerNodeProblem):
                        # TODO: Be more precise with the span (slots)
                        span = node.span
                    elif isinstance(p, TokenProblem):
                        span = TextSpan(node.span.start + p.span.start, node.span.start + p.span.end)
                    else:
                        raise ValueError(f"Unknown problem type: {p}")

                    problems.append(p.message, p.severity, span)

                for c in node.children:
                    if c.has_problems:
                        stack.append(c)
