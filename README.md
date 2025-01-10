# Draw++ (c'est toujours pas terrible comme nom)

Un langage de programmation pour dessiner procéduralement des images, avec un IDE intégré.

## Prérequis

**Windows & Linux**
- Python 3.12
- Pipenv : `pip install --user pipenv` ou `sudo apt install pipenv` sur Debian/Ubuntu
  **Sur Windows :** Si l'installation émet un avertissement car `pipenv.exe` est inaccessible depuis le PATH, ajoutez le long chemin contenu dans le message d'erreur (qui commence par `C:\Users\[user]\AppData\Local\Packages\`) dans votre PATH (voir [cet article](https://lecrabeinfo.net/modifier-le-path-de-windows-ajouter-un-dossier-au-path.html)), sinon pipenv ne sera pas accessible depuis le terminal

**Windows**
- CMake
- Visual Studio 2022 avec les modules de développement C/C++

**Linux**
- Compilateur C (gcc ou clang)
- SDL2 (bibliothèque de développement)

Sur Debian/Ubuntu, cette commande suffit pour installer tous les prérequis :
```bash
sudo apt install python3 pipenv build-essential libsdl2-dev
```

## Commencer à développer

Avant tout, n'oubliez pas de cloner le dépôt !!

### Compilateur & IDE

**Installation**
1. Se placer dans le dossier racine du projet
2. Créer le venv et installer les paquets nécessaires : `pipenv sync --dev`

**Utilisation**
 
Pour lancer un fichier Python, la manière la plus efficace, sur le terminal, est de :
- se mettre dans une session shell avec `pipenv shell`   
  (Remarque : Visual Studio Code peut le faire automatiquement, donc si ça émet une erreur on peut l'ignorer)
- utiliser `pipenv run python -m pydpp.xxxxx.yyyyy` avec `xxxxx`/`yyyyy` le chemin du fichier Python  
  **Exemple** : `pipenv run python -m pydpp.compiler.tokenizer` correspond à `pydpp/compiler/tokenizer.py`  
  **Exemple 2** : `pipenv run python -m pydpp.ide` correspond à `pydpp/ide/__main__.py`

C'est aussi possible d'utiliser l'IDE (Visual Studio Code et PyCharm), ce qui marche s'il trouve
le venv, sinon il faut trouver un moyen de l'indiquer (il est dans le dossier `.venv`)

Pour installer un paquet, là on utiliserait normalement `pip`, on utilise `pipenv`. Par exemple, `pipenv install customtkinter`.

### Moteur de dessin

Ah bah là j'en sais rien déso (indice : cmake + sdl)