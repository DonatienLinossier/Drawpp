#! /usr/bin/env python3

import shutil
import subprocess
import os
import sys

# The directory of this script.
script_dir = os.path.dirname(os.path.realpath(__file__))

# The path to the sdlEncapsulation project.
sdl_encap_dir = os.path.join(script_dir, "sdlEncapsulation")

# The build directory for the project.
build_dir = os.path.join(sdl_encap_dir, "build")

# Where binaries reside
bin_dir = os.path.join(sdl_encap_dir, "bin")

# Create the build_dir if it doesn't exist
if not os.path.exists(build_dir):
    os.makedirs(build_dir)

# Same for the bin/ folder
if not os.path.exists(bin_dir):
    os.makedirs(bin_dir)

# Check if SDL2 is installed for Linux systems. On Windows we bundled it.
if os.name == "posix":
    # sdl2-config is a nice heuristic to know if SDL2 is there, but it might not be precise
    # if you're using some weird distro/config... So let's not stop the script there.
    if shutil.which("sdl2-config") is None:
        print("Warning: Couldn't find SDL2 (sdl2-config) installed.", file=sys.stderr)
        print("On a Debian/Ubuntu system, try installing it with:", file=sys.stderr)
        print("    sudo apt-get install libsdl2-dev", file=sys.stderr)

if os.name == "posix" and os.getenv("FORCE_CMAKE") != "1":
    # On linux: Try calling the C compiler directly, so we don't need to install CMake.
    #           Produces a static library.

    cc = shutil.which("cc")
    ar = shutil.which("ar")

    if not cc:
        print("C compiler not found!", file=sys.stderr)
        exit(1)

    print("Building sdlEncapsulation directly using the C compiler (" + cc + ")...")

    # Run the C compiler to compile the source file.
    res1 = subprocess.run([cc,
                           "-c",  # Don't do linking
                           f"{sdl_encap_dir}/src/sdlEncapsulation.c",  # Compile the sdlEncapsulation.c file
                           f"-I{sdl_encap_dir}/include",  # Add the include directory to the search path
                           "-o", f"{build_dir}/sdlEncapsulation.o",  # Output an object file
                           '-lSDL2', '-lm'],  # Link against SDL2 and the math library
                          encoding="utf-8", capture_output=True)
    if res1.returncode != 0:
        print("Failed to compile sdlEncapsulation.c:\n" + res1.stderr, file=sys.stderr)
        exit(1)

    # Create the static library from the only object file produced.
    # (Honestly I don't even know if that's necessary)
    res2 = subprocess.run(
        [ar, "rcs", f"{bin_dir}/libsdlEncapsulation.a", f"{build_dir}/sdlEncapsulation.o"],
        encoding="utf-8", capture_output=True)
    if res2.returncode != 0:
        print("Failed to archive the static library:\n" + res2.stderr, file=sys.stderr)
        exit(1)
else:
    # On Windows/Linux forced: Use CMake to build the project.

    # Find the CMake executable.
    cmake = shutil.which("cmake")
    if not cmake:
        print("CMake is not installed! Install it on your system.\n"
              "Windows:        https://cmake.org/download/\n"
              "Debian/Ubuntu:  Run this command: sudo apt install cmake", file=sys.stderr)
        exit(1)

    # Initialise CMake cache in the build dir
    res3 = subprocess.run([cmake, ".."], cwd=build_dir, encoding="utf-8", capture_output=True)
    if res3.returncode != 0:
        print("Failed to initialise the CMake cache:\n" + res3.stderr, file=sys.stderr)
        exit(1)

    # Build the project
    res4 = subprocess.run([cmake, "--build", "."], cwd=build_dir, encoding="utf-8", capture_output=True)
    if res4.returncode != 0:
        print("Failed to build the project:\n" + res4.stderr, file=sys.stderr)
        exit(1)