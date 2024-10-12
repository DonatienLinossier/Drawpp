# All compiler functionality available to use within the IDE module.
# Import the pydpp.compiler module to use it!

# ======================
# PUBLIC IMPORTS
# ======================
# Import all useful types that the IDE module will take usage of.
#
# This means that the IDE module will be able to import those types easily, for example this works:
#   from pydpp.compiler import ProblemSet, FileSpan
from .problem import ProblemSet, Problem, ProblemSeverity
from .position import FileCoordinates, FileSpan

# ======================
# PRIVATE IMPORTS
# ======================
# Import modules with an underscore prefix to avoid importing pipeline elements (tokenizer, parser)
# when importing pydpp.compiler.
from . import tokenizer as _tokenizer


# ======================
# PUBLIC FUNCTIONS
# ======================
# Functions that the IDE module will be able to use to do various stuff with code.

# Draft version of the compilation pipeline
def compile_code(code):
    # Create a problem set to contain all errors during the compilation pipeline
    ps = ProblemSet()
    # Tokenize the code, and get a list of tokens
    tokens = _tokenizer.tokenize(code, ps)
    # And then...?
    raise NotImplementedError("To be continued...!")
