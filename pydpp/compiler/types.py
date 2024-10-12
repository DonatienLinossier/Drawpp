from enum import Enum

# ======================================================
# types.py: The Draw++ typesystem and type checking
# ======================================================

class BuiltInTypeKind(Enum):
    """
    A built-in type in the language. Currently: int, float, string and bool.
    """
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    NOTHING = "nothing" # like void in C? but a little bit more original?

class Type:
    """
    A type in the language: user-defined or built-in.
    Can also be an "error" type if an expression doesn't make sense.
    For example, what type would "pastèque" / 2 have? ERROR!
    """
    # TODO!
    pass

# Idea: A "type classification" enum? BUILT-IN/USER-DEFINED/ERROR?
# User-defined isn't on the table at the moment, we could add it later one.

# Yeah, currently there isn't much there, but later on we'll add functions to check types