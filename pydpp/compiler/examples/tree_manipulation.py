from pydpp.compiler import tokenize, parse, ProblemSet
from pydpp.compiler.syntax import *

# Mon code
code = """
  print("salut")
int x = 5;

if x > 4 {
    test(x);
}
"""[1:]

ps = ProblemSet()
# Les tokens
tokens = tokenize(code, ps)

# L'arbre de syntaxe
tree = parse(tokens, ps)

# --- Petit catalogue des fonctions ---

def info_node():
    # Informations utiles sur un nœud (interne et feuille)

    # On prend un nœud au pif (la première instruction)
    node = tree.statements[0]

    print("Type du nœud", type(node).__name__)
    print("Valeur textuelle du nœud (espaces compris) :", node.full_text)
    print("Valeur textuelle du nœud (sans espaces) :", node.text)
    print("Position du nœud dans le code (espaces compris) (index début, index fin) :", node.full_span)
    print("Est-ce que le nœud (ou ses enfants) a des problèmes ?", node.has_problems)
    print("Problèmes du nœud :", node.problems)
    print("Structure du nœud (pour débug) :", str(node))



def all_expressions():
    # Avoir toutes les expressions de l'arbre « tree », y compris dans les enfants des enfants
    expr = tree.descendants(Expression)
    for e in expr:
        print(e)

info_node()
