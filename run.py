#! /usr/bin/env python3
import os
import shutil
import subprocess
import sys
from importlib.util import find_spec

# run.py: Tries its best to run the Draw++ IDE by all means possible.

# The path to the python executable running this code.
python_exe = sys.executable
# The root dir of the project
project_path = os.path.dirname(os.path.realpath(__file__))
# Path to the sdlEncapsulation library
sdl_encap_dir = os.path.join(project_path, "libs", "sdlEncapsulation")
# Path to the sdlEncapsulation library file
sdl_encap_lib_path = os.path.join(sdl_encap_dir, "bin", "sdlEncapsulation.lib") if os.name == "nt" \
    else os.path.join(sdl_encap_dir, "bin", "libsdlEncapsulation.a")

# Path to the default venv
venv_path = os.path.join(project_path, ".venv")
# Path to the python executable of the venv
venv_python_path = os.path.join(venv_path, "Scripts", "python.exe") if os.name == "nt" \
    else os.path.join(venv_path, "bin", "python")

has_compiled_sdl_encap = os.path.exists(sdl_encap_lib_path)

# ---- FIRST STAGE: Checks ----
# Make sure that dependencies required by the compiler are installed.

warns = []
def warn_user(msg: str):
    warns.append(msg)

if os.name == "nt":
    # On Windows, we need to have CMake and Visual Studio tools.
    if shutil.which("cmake") is None:
        warn_user("CMake n'est pas installé.\n"
                  "  💡 Installez-le -> https://cmake.org/download/")

    # Checking for VS takes some time. Check only if sdlEncapsulation is not compiled.
    if not has_compiled_sdl_encap:
        res = subprocess.run(os.path.join(project_path, "pydpp", "compiler", "windows", "vsenv.bat"),
                             capture_output=True)
        if res.returncode != 0:
            # No VS!
            warn_user("Visual Studio n'est pas installé.\n"
                      "  💡 Installez-le -> https://visualstudio.microsoft.com/fr/downloads/")
else:
    # On Linux, we need: a C compiler, SDL2 libs
    if shutil.which("cc") is None:
        warn_user("Aucun compilateur C n'est installé (gcc ou clang).\n"
                  "  💡 Installez-en un -> sudo apt install build-essential")

    if shutil.which("sdl2-config") is None:
        warn_user("La bibliothèque SDL2 n'est pas installée.\n"
                  "  💡 Installez-la -> sudo apt install libsdl2-dev")

# Display the warnings if we have some, and kindly ask the user to proceed or not.
if len(warns) > 0:
    print("⚠️ Attention! Certaines dépendances requises sont introuvables :")
    for w in warns:
        print("-", w)
    print("❌ La compilation de programmes Draw++ risque de ne pas fonctionner.")
    print("Voulez-vous quand même tenter de lancer l'IDE ? [o/n]", end=" ")
    answer = input()
    if answer.lower() != "o" or answer.lower() != "y":
        sys.exit(1)

# ---- SECOND STAGE: Compile the SDL Encapsulation library ----

if not has_compiled_sdl_encap:
    # It's not compiled! Then let's compile obviously
    print("Compilation de SDL Encapsulation...")

    # Run the build_sdlEncapsulation.py script
    res = subprocess.run([python_exe, os.path.join(project_path, "libs", "build_sdlEncapsulation.py")])
    if res.returncode != 0:
        print("❌ La compilation de SDL Encapsulation a échoué. La compilation de programmes Draw++ sera indisponible.")
        print("Voulez-vous quand même tenter d'exécuter l'IDE? [o/n]", end=" ")
        answer = input()
        if answer.lower() != "o" or answer.lower() != "y":
            sys.exit(1)

# ---- THIRD STAGE: Run the IDE ----
# Well we're going to run the IDE here no surprise

if find_spec("customtkinter") is not None:
    # We are already in the venv, since we have customtkinter. Run the IDE.
    subprocess.run([python_exe, "-m", "pydpp.ide"])
elif find_spec("pipenv") is not None and (len(sys.argv) <= 1 or sys.argv[1] != "--no-pipenv"):
    # We have pipenv installed.

    # Do we have a venv we know? Use the Mario Kart Shortcut, else, just use pipenv (but it's so slow!)
    if os.path.exists(venv_python_path):
        print("Dossier .venv trouvé, C'est parti pour Draw++!")
        subprocess.run([venv_python_path, "-m", "pydpp.ide"])
    else:
        # Make sure the venv is synchronized before running the IDE.
        print("Pas de .venv, utilisation de pipenv pour mettre à jour le venv et lancer l'IDE.")
        subprocess.run([python_exe, "-m", "pipenv", "sync", "--dev"]).check_returncode()
        print("Dossier .venv préparé, c'est parti pour Draw++!")
        subprocess.run([python_exe, "-m", "pipenv", "run", "python", "-m", "pydpp.ide"]).check_returncode()
else:
    # We don't have pipenv! Offer the user the option of using an "experimental" workaround.

    print("Pipenv n'a pas été trouvé ! Installez-le pour pouvoir lancer l'IDE sans souci.")
    print("Vous pouvez essayer une alternative expérimentale pour exécuter Draw++ sans pipenv. Ça vous intéresse ? [o/n]", end=" ")
    answer = input()
    if answer.lower() == "y" or answer.lower() == "o":
        # Yes. Let's do it.
        import venv

        # Configure some new venv/venv_exe variables
        exp_venv_path = os.path.join(project_path, ".venv-exp")
        exp_venv_python_path = os.path.join(exp_venv_path, "Scripts", "python.exe") if os.name == "nt" \
            else os.path.join(exp_venv_path, "bin", "python")

        if not os.path.exists(exp_venv_python_path):
            # Create the virtual environment, and install customtkinter
            print("Création du venv...")
            venv.EnvBuilder(with_pip=True, system_site_packages=True, symlinks=os.name != "nt").create(exp_venv_path)
            print("Installation de customtkinter...")
            subprocess.run([exp_venv_python_path, "-m", "pip", "install", "customtkinter"]).check_returncode()

        # Run the pydpp.ide module, BUT we have to setup the PYTHONPATH to make sure it finds pydpp.
        print("Lancement en utilisant le venv :", exp_venv_path)
        env_vars = os.environ.copy()
        env_vars["PYTHONPATH"] = project_path
        subprocess.run([exp_venv_python_path, "-m", "pydpp.ide"], env=env_vars).check_returncode()
    else:
        # Coward!!
        print("Bonne chance alors...")