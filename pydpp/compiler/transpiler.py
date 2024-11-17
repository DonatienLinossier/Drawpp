from pydpp.compiler import ProblemSet, ProblemSeverity
from pydpp.compiler.semantic import ProgramSemanticInfo
from pydpp.compiler.syntax import Program


# ======================================================
# transpiler.py: The transpiler producing C code
# ======================================================

def transpile(program: Program, semantic_info: ProgramSemanticInfo, ps: ProblemSet) -> str:
    """
    Produces working C code to run the program, which should have been
    successfully parsed and semantically analysed beforehand.

    There must have been no errors during the compilation pipeline. If there's one,
    the function will fail and raise an error.

    :param program: The root node of the AST
    :param semantic_info: The semantic information of the program
    :param ps: The problem set to report any errors during transpilation
    :return: The C code equivalent to the program
    """

    # Exit the function if we have any errors, or if we don't have semantic info
    if len(ps.grouped[ProblemSeverity.ERROR]) > 0:
        raise RuntimeError("Cannot transpile a program with errors.")
    elif semantic_info is None:
        raise RuntimeError("Cannot transpile a program without complete semantic analysis.")

    # TODO! À faire :
    #     - Utiliser le code de Donatien pour générer le code C avec les données de l'étape
    #       de l'analyse sémantique (ProgramSemanticInfo du fichier semantic.py).
    #     - Bien générer toutes les instructions, déclarations, etc.
    raise NotImplementedError("Not done yet... :(")