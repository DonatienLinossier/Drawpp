# Draw++ (c'est toujours pas terrible comme nom)

Un langage de programmation pour dessiner procéduralement des images, avec un IDE intégré.

## Prérequis

- Python 3.12
- Pipenv : `pip install --user pipenv` puis redémarrer le terminal
- CMake avec un toolchain pour du C (gcc, clang, ou Visual Studio sur Windows)

## Commencer à développer

Avant tout, n'oubliez pas de cloner le dépôt !!

### Compilateur & IDE

**Installation**
1. Se placer dans le dossier racine du projet
2. Créer le venv et installer les paquets nécessaires : `pipenv install`

**Utilisation**
 
Pour lancer un fichier Python, la manière la plus efficace, sur le terminal, est de :
- se mettre dans une session shell avec `pipenv shell`   
  (Remarque : Visual Studio Code peut le faire automatiquement, donc si ça émet une erreur on peut l'ignorer)
- utiliser `pipenv run python -m pydpp.xxxxx.yyyyy` avec `xxxxx`/`yyyyy` le chemin du fichier Python  
  **Exemple** : `pipenv run python -m pydpp.compiler.tokenizer` correspond à `pydpp/compiler/tokenizer.py`  
  **Exemple 2** : `pipenv run python -m pydpp.ide` correspond à `pydpp/ide/__main__.py`

C'est aussi possible d'utiliser l'IDE (Visual Studio Code et PyCharm), ce qui marche s'il trouve
pas le venv, sinon il faut trouver un moyen de l'indiquer (il est dans le dossier `.venv`)

Pour installer un paquet, là on utiliserait normalement `pip`, on utilise `pipenv`. Par exemple, `pipenv install customtkinter`.

### Moteur de dessin

Ah bah là j'en sais rien déso (indice : cmake + sdl)