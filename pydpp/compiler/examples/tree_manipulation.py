from pydpp.compiler import tokenize, parse, ProblemSet
from pydpp.compiler.syntax import *

# Mon code qui sera utilisé tout le long de la doc
# Oui la première ligne est erronée c'est normal
code = """
  print("salut")
int x = 5;

if x > 4.5 {
    test(x+y+f(x));
    print("oh", 789);
}
bool machin = true;
"""[1:]

# Les tokens
tokens = tokenize(code)
# L'arbre de syntaxe (sera donnée dans les fonctions que sur lesquelles tu travailleras)
tree = parse(tokens)

# ========================================
# DÉMONSTRATIONS GÉNÉRALES POUR MANIPULER LES ARBRES
# ========================================

def info_node():
    """
    Informations utiles sur un nœud (interne et feuille)
    """

    # On prend un nœud au pif (la première instruction)
    node = tree.statements[0]

    # On print plein d'infos
    print("Type du nœud", type(node).__name__)
    print("Valeur textuelle du nœud (espaces compris) :", node.full_text)
    print("Valeur textuelle du nœud (sans espaces) :", node.text)
    print("Position du nœud dans le code (espaces compris) (index début, index fin) :", node.full_span)
    print("Est-ce que le nœud (ou ses enfants) a des problèmes ?", node.has_problems)
    print("Problèmes du nœud :", node.problems)
    print("Structure du nœud (pour débug) :", str(node))

    print("Structure du nœud (plus joli) :")
    node.print_fancy()

    print("Structure du nœud (plus joli, sans tokens) :")
    node.print_fancy(include_tokens=False)

def statements_and_expressions():
    """
    Présentation des nœuds de types Statement (instructions) et Expression (expressions/valeurs)
    """

    # Dans Draw++ il y a deux types principaux de nœuds : Statement et Expression.

    # Un nœud de type Statement représente une instruction du programme :
    # déclaration de variable, appel de fonction, assignation, bloc 'if', etc.

    # On va lister toutes les instructions du programme (voir la fonction node_children pour plus de détails)
    print("[tree.descendants(Statement)] Toutes les instructions du programme :")
    for d in tree.descendants(Statement):
        print("- de type", type(d).__name__, ":", d.text)

    print("---")

    # Un nœud de type Expression est essentiellement une "valeur" que le programme peut évaluer.
    # Ça peut être une valeur numérique, une chaîne de caractères, peu importe !
    # Globalement, si on peut le mettre dans une fonction ou une variable, c'est une Expression.
    # 5, c'est une expression. "pouet" aussi. f(a+b) aussi... Mais if(true){} non !

    # Chaque expression doit avoir, par définition, un type. Ce type devra être évalué
    # dans l'étape "analyse sémantique" du compilateur.

    # On va justement lister toutes les expressions du programme (voir la fonction node_children pour plus de détails)
    print("[tree.descendants(Expression)] Toutes les expressions du programme :")
    for d in tree.descendants(Expression):
        print("- de type", type(d).__name__, ":", d.text)

def node_children():
    """
    Parcours des enfants d'un nœud (récursif et non-récursif)
    """

    # Prenons un nœud qui a des enfants : le "if"

    # On prend le nœud "if" (3e instruction du code)
    # Tu peux changer cette variable pour parcourir le nœud de ton choix
    node = tree.statements[2]

    print("On regarde ce nœud :", node.text, "\n")

    # PROPRIÉTÉ node.children
    # -----------------------
    # On print tous les enfants de ce if.
    # node.children renvoie TOUS les nœuds enfants : les internes et les feuilles (tokens)
    print("[node.children] Tous les nœuds enfants du 'if', internes et feuilles :")
    for d in node.children:
        print("- de type", type(d).__name__, ":", d.text)

    print("---")

    # PROPRIÉTÉ node.child_inner_nodes
    # --------------------------------
    # node.child_inner_nodes renvoie UNIQUEMENT les nœuds internes (pas les tokens)
    print("[node.children_inner_nodes] Tous les nœuds enfants du 'if', internes uniquement :")
    for d in node.child_inner_nodes:
        print("- de type", type(d).__name__, ":", d.text)

    print("---")

    # FONCTION node.descendants(filter)
    # filter : le type de nœud à chercher, peut être None pour avoir tout
    # ---------------------------------
    # Je peux aussi utiliser la fonction "descendants" pour parcourir l'intégralité des enfants de manière récursive,
    # en allant jusqu'aux feuilles. En gros on ne s'arrête pas au "niveau 1" de profondeur, mais jusqu'à la fin.
    # Par exemple, on va récupérer tous les nœuds descendants de type Expression.
    print("[node.descendants(Expression)] Tous les nœuds descendants du 'if', de type Expression :")
    for d in node.descendants(Expression):
        print("- de type", type(d).__name__, ":", d.text)

    print("---")

    # C'est aussi possible de s'arrêter aux nœuds rencontrés lors de la recherche de descendants.
    # Par exemple, si on cherche des Expressions et qu'on tombe sur x+y, on ne va pas recracher "x" et "y".
    print("[node.descendants(Expression, stop=True)] Tous les nœuds descendants du 'if', de type Expression, en arrêtant le parcours si trouvé :")
    for d in node.descendants(Expression, stop=True):
        print("- de type", type(d).__name__, ":", d.text)

def node_parent():
    """
    Présentation du parent d'un nœud (et de tous ces ancêtres sur 9 générations)
    """

    # C'est aussi possible d'avoir le nœud parent d'un nœud, ce qui permet de remonter dans l'arbre.

    # PROPRIÉTÉ node.parent
    # --------------------------------
    # Voilà un petit exemple pour trouver tous les parents des litéraux du code.
    # Cette fois-ci on cherche tous les LiteralExpr car c'est l'expression litérale qui contient le token litéral.
    # Pour rappel : LiteralExpr contient un LeafNode (nœud feuille) du token litéral ("salut", 789, true)
    print("Parents des litéraux du code")
    print("------")
    for lit in tree.descendants(LiteralExpr):
        expr_txt = lit.text
        ancestor_txt = lit.parent.text
        print("- litéral       :", expr_txt.ljust(30), f"({type(lit).__name__})")
        print("  son parent    :", ancestor_txt.ljust(30), f"({type(lit.parent).__name__})")
        print()
    print()
    print()

    # FONCTION node.ancestor(filter)
    # filter : le type de nœud à chercher
    # ---------------------------------
    # On peut aussi chercher un « ancêtre » étant d'un type particulier de nœud.
    # Un ancêtre est un parent de n'importe quel degré, aussi éloigné que l'on veut,
    # c'est-à-dire, on recherche un parent, un grand-parent, un arrière-grand-parent, etc. jusqu'à la racine
    # Puis, on s'arrête si le parent est du type voulu.

    # Ici, on va chercher toutes les expressions, puis voir celles qui sont contenues dans un appel de fonction.
    print("Ancêtres de type FunctionExpr des expressions")
    print("------")
    for e in tree.descendants(Expression):
        # On cherche le premier ancêtre de type FunctionExpr : un appel de fonction
        ancestor = e.ancestor(FunctionExpr)
        if ancestor is None:
            # Cette expression n'est pas dans un appel de fonction, on l'ignore.
            continue

        expr_txt = e.text
        ancestor_txt = ancestor.text
        print("- expression    :", expr_txt.ljust(30), f"({type(e).__name__})")
        print("  son ancêtre   :", ancestor_txt)
        print()





def leaf_tokens():
    """
    Présentation des nœuds feuilles, les tokens.
    """

    # Les nœuds sont classifiés en deux types : les nœuds internes et les nœuds feuilles.

    # Les nœuds internes (type InnerNode) sont des nœuds qui ne sont pas des feuilles (wow !).
    # Ils contiennent forcément des enfants, qui peuvent être soit des nœuds internes, soit des feuilles.
    # En théorie des language : symbole non-terminal

    # Les feuilles n'ont pas d'enfants (normal c'est des feuilles tu me diras).
    # Ils ont en revanche un token, qui représente le "symbole" lu du code, avec sa représentation textuelle.
    # En rassemblant toutes les feuilles de l'arbre, on arrive à reconstruire le code source complet.
    # En théorie des language : symbole terminal

    # Chaque Token est composé de plusieurs parties :
    # - kind : le type de token (TokenKind)
    # - text : le texte du token, sans les espaces (exemple : si kind = KW_IF, text = "if")
    # - pre_auxiliary : le texte auxiliaire présent derrière ce token (espaces, commentaires, erreurs)
    # - full_text : le texte complet du token, avec le texte auxiliaire précédent
    # - value : la valeur du token, si c'est un litéral (nombre, chaîne de caractères, booléen)

    # Montrons les nœuds feuilles de la 2e instruction, l'assignation
    node = tree.statements[1]

    print(f"Tous les nœuds feuilles enfants de {node.text}")
    for c in node.children:
        # C'est une feuille ?
        if isinstance(c, LeafNode):
            # Le "type" du token.
            kind = c.kind
            # La valeur du c, si c'est un litéral
            # Si c'est pas un litéral, c'est None (NULL en C).
            value = c.value

            print(f"- trouvé : {str(c).ljust(16)} | {c.text} (value={value!r})")
            print(f"  kind={kind!r}, pre_auxiliary={c.pre_auxiliary!r}, full_text={c.full_text!r}")
            print()
    print()

    # Remarque : on a utilisé "children" donc on n'a pas le 5 !
    #            Car le nœud feuille 5 est contenu dans un nœud interne de type LiteralExpr.
    #
    # On peut utiliser la fonction "descendants" pour l'obtenir, et avoir absolument tous les tokens à l'intérieur :

    print(f"\nTous les nœuds feuilles descendants de {node.text}")
    for c in node.descendants(LeafNode):
        # Le "type" du token.
        kind = c.kind
        # La valeur du c, si c'est un litéral
        # Si c'est pas un litéral, c'est None (NULL en C).
        value = c.value

        print(f"- c trouvé : {str(c).ljust(16)} | {c.text} (value={value!r})")
        print(f"  kind={kind!r}, pre_auxiliary={c.pre_auxiliary!r}, full_text={c.full_text!r}")
        print()

def node_props():
    """
    Parcours des nœuds de différents types et usage de leurs propriétés
    """

    # On va lister tous les enfants du programme, et faire différentes opérations sur chaque type de nœud
    # On peut utiliser les propriétés pour avoir des nœuds enfants particuliers.
    # Les propriétés contenant des feuilles ont un nom qui se termine systématiquement par "_token".
    #
    # La liste des propriétés de chaque nœud est disponible dans le fichier syntax/nodedefs.py
    for c in tree.children:
        if isinstance(c, VariableDeclarationStmt):
            print("Déclaration de variable trouvée (VariableDeclarationStmt) :", c.text)

            # Schéma d'une déclaration : <type> <name> = <valeur>;
            # Je récupère le nœud dans l'emplacement "type".
            type_node = c.type
            # Je récupère le nœud dans l'emplacement "name".
            name = c.name_token
            # Je peux utiliser la propriété qui se termine par "_str" pour avoir directement le nom de l'identifiant.
            name_str = c.name_token_str
            # Je récupère le nœud dans l'emplacement "value".
            value_node = c.value

            print("Type de la variable :", type_node.text)
            print("Token du nom de la variable :", name)
            print("Nom de la variable :", name_str)
            print("Valeur de la variable :", value_node.text)
            print()
        elif isinstance(c, IfStmt):
            print("Bloc 'if' trouvé (IfStmt) :", c.text)

            # Schéma d'une déclaration : if <condition> <then_block> [<else_block>...]

            # Je récupère le nœud dans l'emplacement "condition".
            condition_node = c.condition
            # Je récupère le nœud dans l'emplacement "then_block".
            block_node = c.then_block

            print("Condition du 'if' :", condition_node.text)
            print("Bloc du 'if' :", block_node.text)
            print()

    # Maintenant, je vais chercher tous les litéraux du code : chaînes de caractères, nombres et booléen.
    # Je vais filtrer par "LeafNode" qui est le type des nœuds feuilles (les tokens)
    print("Recherche des litéraux du code")
    print("--------------")
    for leaf in tree.descendants(LeafNode):
        # Représentation textuelle sans espaces du token
        text = leaf.text
        # Valeur du token, si c'est un litéral
        value = leaf.value

        if leaf.kind == TokenKind.LITERAL_STRING:
            # C'est une chaîne de caractères !
            print("Chaîne de caractères trouvée :", text, f"(valeur : {value}, type : {type(value).__name__})")
        elif leaf.kind == TokenKind.LITERAL_NUM:
            # C'est un nombre !
            print("Nombre trouvé :", text, f"(valeur : {value}, type : {type(value).__name__})")
        elif leaf.kind == TokenKind.LITERAL_BOOL:
            # C'est un booléen !
            print("Booléen trouvé :", text, f"(valeur : {value}, type : {type(value).__name__})")


if __name__ == '__main__':
    fs = [info_node, statements_and_expressions, node_children, node_parent, leaf_tokens, node_props]
    while True:
        for i in range(len(fs)):
            print(f"{i+1} : {fs[i].__name__}")
        try:
            try:
                v = input("On lance quoi ? (q pour sortir) ").strip().lower()
                if v == "q" or v == "sortir" or v == "exit":
                    break
                n = int(v)
                if n < 1 or n > len(fs):
                    raise ValueError
            except ValueError:
                print("Pas bon !")
                continue

            print("")
            fs[n-1]()
            print("")
            input("Appuie sur entrée pour continuer...")
        except EOFError:
            break
