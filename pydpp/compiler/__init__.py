# All compiler functionality available to use within the IDE module.
# Import the pydpp.compiler module to use it!

# Don't import anything when we're running the codegen module,
# as this all those imports break the code if it isn't generated!
# noinspection PyCompatibility
import __main__

from .position import TextSpan
from .suggestion import find_suggestion
from .syntax import InnerNodeProblem
import tempfile
import os

from .toolchain import link

if __main__ is None or not hasattr(__main__, "__file__") or not __main__.__file__.endswith("codegen.py"):
    # ======================
    # IMPORTS
    # ======================
    # Import all useful types that the IDE module will take usage of.
    #
    # This means that the IDE module will be able to import those types easily, for example this works:
    #   from pydpp.compiler import ProblemSet, FileSpan
    from .problem import Problem, ProblemSeverity, ProblemSet, ProblemCode
    from .tokenizer import tokenize, TokenProblem
    from .parser import parse
    from .semantic import analyse
    from .transpiler import transpile
    from .syntax import Node

    # Make all submodules available when importing the compiler module
    from . import problem, position, tokenizer, semantic, syntax, transpiler, transpiler, CTranslater


    # ======================
    # FUNCTIONS
    # ======================
    # Functions that the IDE module will be able to use to do various stuff with code.

    # Draft version of the compilation pipeline, returns True when everything went fine, or False if not.
    # - out_exe_path must contain the path for the generated executable
    # - out_c_path can be filled to set where the temporary C file will be generated, by default, the
    #   system temp directory is used
    def compile_code(code: str, out_exe_path: str, out_c_path: str | None = None) -> tuple[bool, ProblemSet]:
        # Tokenize the code, and get a list of tokens
        tokens = tokenize(code)
        # Take that list of tokens, and parse it to make a syntax tree
        program = parse(tokens)
        # Do some semantic analysis on the tree, to check/compute types and references
        semantic_info = analyse(program)

        # Gather all problems from the parsing, tokenization and semantic stages.
        problems = collect_errors_2(program)

        # If we have an error, we can't transpile and compile, so return False
        if len(problems.grouped[ProblemSeverity.ERROR]) > 0:
            return False, problems

        if out_c_path is None:
            # No C path was given, use the system's temp directory
            c_file, out_c_path = tempfile.mkstemp(prefix="dpp", suffix=".c")
            # Close the file, the CTranslater will open it again.
            os.close(c_file)

        # Generate the C code that will run the program's instructions
        transpile(program, semantic_info, out_c_path)

        # Compile the C code to an executable
        success, err = link(out_c_path, out_exe_path)
        if success:
            return True, problems
        else:
            problems.append(err, ProblemSeverity.ERROR)
            return False, problems


    def collect_errors(tree: Node, problems: ProblemSet, enable_suggestions=False):
        """
        Collects all errors (node/tokens) from a given syntax tree, into a problem set.
        :param tree: the tree with errors
        :param problems: the problem set to add the errors to
        :param enable_suggestions: whether to enable suggestions, attached to the Problem's suggestions attribute
        """
        if tree.has_problems:
            # Traverse the tree using DFS with a stack. All nodes marked "has_problems" has at least
            # one descendant with a problem.
            stack = [tree]
            while stack:
                node = stack.pop()

                for p in node.problems:
                    if isinstance(p, InnerNodeProblem):
                        # The problem is located on an inner node: use the compute_span function
                        # to get the precise span (since we can specify the *slot* location of the problem)
                        span = p.compute_span(node)
                        code = p.code
                        if enable_suggestions:
                            sug = find_suggestion(node, p)
                        else:
                            sug = None
                    elif isinstance(p, TokenProblem):
                        # The problem is located on a token: use the token's span + the problem span.
                        span = TextSpan(node.full_span_start + p.span.start, node.full_span_start + p.span.end)
                        code = ProblemCode.OTHER
                        sug = None # TODO: Suggestion for token problems
                    else:
                        raise ValueError(f"Unknown problem type: {p}")

                    # Add the problem to the problem set.
                    problems.append(p.message, p.severity, span, code, node, sug)

                # Continue traversing the tree for nodes that are interesting to us
                # (by interesting I mean absolutely BROKEN.)
                # We traverse them in reverse so we get them stacked correctly (i.e. the first child is stacked last)
                for c in node.children_reverse:
                    if c.has_problems:
                        stack.append(c)


    def collect_errors_2(tree: Node, enable_suggestions=False) -> ProblemSet:
        """
        Collects all errors (node/tokens) from a given syntax tree, into a problem set.
        :param tree: the tree with errors
        :param problems: the problem set to add the errors to
        """

        ps = ProblemSet()
        collect_errors(tree, ps, enable_suggestions)
        return ps
