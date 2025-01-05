#! /usr/bin/env python3

import shutil
import subprocess
import os

# The directory of this script.
script_dir = os.path.dirname(os.path.realpath(__file__))

# The path to the sdlEncapsulation project.
sdl_encap_dir = os.path.join(script_dir, "sdlEncapsulation")

# The build directory for the project.
build_dir = os.path.join(sdl_encap_dir, "build")

# Create the build_dir if it doesn't exist
if not os.path.exists(build_dir):
    os.makedirs(build_dir)

# Check if SDL2 is installed for Linux systems. On Windows we bundled it.
if os.name == "posix":
    # sdl2-config is a nice heuristic to know if SDL2 is there, but it might not be precise
    # if you're using some weird distro/config... So let's not stop the script there.
    if shutil.which("sdl2-config") is None:
        print("Warning: Couldn't find SDL2 (sdl2-config) installed.")
        print("On a Debian/Ubuntu system, try installing it with:")
        print("    sudo apt-get install libsdl2-dev")

if os.name == "posix" and os.getenv("FORCE_CMAKE") != "1":
    # On linux: Try calling the C compiler directly, so we don't need to install CMake.
    #           Produces a static library.

    cc = shutil.which("cc")
    ar = shutil.which("ar")

    if not cc:
        print("C compiler not found!")
        exit(1)

    print("Building sdlEncapsulation directly using the C compiler (" + cc + ")...")

    # Run the C compiler to compile the source file.
    res1 = subprocess.run([cc,
                           "-c",  # Don't do linking
                           f"{sdl_encap_dir}/src/sdlEncapsulation.c",  # Compile the sdlEncapsulation.c file
                           f"-I{sdl_encap_dir}/include",  # Add the include directory to the search path
                           "-o", f"{build_dir}/sdlEncapsulation.o",  # Output an object file
                           '-lSDL2', '-lm']  # Link against SDL2 and the math library
                          )
    if res1.returncode != 0:
        print("Failed to compile sdlEncapsulation.c")
        exit(1)

    # Create the static library from the only object file produced.
    # (Honestly I don't even know if that's necessary)
    res2 = subprocess.run(
        [ar, "rcs", f"{sdl_encap_dir}/bin/libsdlEncapsulation.a", f"{build_dir}/sdlEncapsulation.o"])
    if res2.returncode != 0:
        print("Failed to create static library")
        exit(1)
else:
    # On Windows/Linux forced: Use CMake to build the project.

    # Find the CMake executable.
    cmake = shutil.which("cmake")
    if not cmake:
        print("CMake is not installed!")
        exit(1)

    # Initialise CMake cache in the build dir
    subprocess.run([cmake, ".."], cwd=build_dir)
    # Build the project
    subprocess.run([cmake, "--build", "."], cwd=build_dir)
