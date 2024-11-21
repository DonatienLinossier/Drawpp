from pydpp.compiler.syntax import Program


# ======================================================
# semantic.py: The semantic analyser
# ======================================================
# This is also where built-in functions and types are defined.

class ProgramSemanticInfo:
    """
    Contains all symbolic information about a program: its declared functions, global variables, etc.
    Could maybe contain built-in functions too!
    """

    def __init__(self):
        # TODO! Peut-être mettre "self.functions = {...}" pour stocker les fonctions de base ?
        pass

def analyse(program: Program) -> ProgramSemanticInfo:
    """
    Runs semantic analysis on a program. Will make sure that all types are correct, that variables are
    valid, and will list all functions and instructions to run when transpiling.

    :param program: The root node of the AST
    :param ps: The problem set to report any errors during semantic analysis
    :return: The semantic information of the program, to be given to the transpiler
    """

    # TODO! À faire :
    #   - Récupérer toutes les variables et leurs types.
    #   - Bien vérifier que les expressions de variables (VariableExpression) ne font pas
    #     référence à des variables qui n'existent pas (du moins pas encore).
    #   - Calculer et stocker les types de toutes les expressions dans l'attribut "semantic_info".
    #     Utiliser le type ERROR si une expression n'a pas de sens, et signaler une erreur.
    #   - Vérifier les appels de fonction : la fonction doit exister, tous les arguments
    #     doivent être donnés et les types doivent correspondre
    #     ...
    #     ...
    #     En gros, faut juste vérifier que le programme en entier a un sens, et stocker toutes
    #     les informations nécessaires (types, déclarations) pour pouvoir générer le code C après !
    #     Ces informations devront être stockées dans le "struct" ProgramSemanticInfo, que le générateur
    #     va récupérer (transpiler.py)
    raise NotImplementedError("Not done yet... :(")