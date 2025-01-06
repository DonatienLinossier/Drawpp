# =============================================================================
# toolchain.py: Compiles transpiled C code to make an executable
# =============================================================================
import os
import re
import sys
import subprocess
import shutil

_script_path = os.path.join(os.path.dirname(__file__))  # Path to this script
_libs_path = os.path.abspath(os.path.join(_script_path, "..", "..", "libs"))  # libs/
_encap_path = os.path.join(_libs_path, "sdlEncapsulation")  # libs/sdlEncapsulation/
_encap_incl_path = os.path.join(_encap_path, "include")  # libs/sdlEncapsulation/include/
_encap_bin_path = os.path.join(_encap_path, "bin")  # libs/sdlEncapsulation/bin/

# OS-specific paths for the sdlEncapsulation library
_linux_encap_lib_path = os.path.join(_encap_bin_path, "libSdlEncapsulation.a")
_windows_encap_lib_path = os.path.join(_encap_bin_path, "sdlEncapsulation.lib")


def link(c_path: str, exe_path: str) -> tuple[bool, str]:
    # Compiles the sdlEncapsulation library if it's not already compiled.
    def init_encap_lib(path: str) -> tuple[bool, str]:
        if not os.path.exists(path):
            # We didn't find the library. Let's try to compile it with the libs/build_sdlEncapsulation.py script!
            res = subprocess.run([
                sys.executable,  # Path to the Python interpreter this script is running
                os.path.join(_libs_path, "build_sdlEncapsulation.py")  # The build_sdlEncapsulation.py script
            ], encoding="utf-8", capture_output=True)

            # Make sure it was an absolute success.
            if res.returncode != 0:
                return False, "Failed to compile the SDL Encapsulation library. Output:\n" + res.stderr
            elif not os.path.exists(path):
                return False, "The compilation script reportedly succeeded, but the library wasn't found!\n" + res.stderr
        return True, ""

    # Call the right method based on operating system.
    # But, before we do anything, make sure that the sdlEncapsulation library exists!
    match sys.platform:
        case "linux":
            # Compile libSdlEncapsulation.a if it doesn't exist
            ok, msg = init_encap_lib(_linux_encap_lib_path)
            if not ok: return False, msg
            # Run GCC and the like
            return _linux_link(c_path, exe_path)
        case "win32":
            # Compile sdlEncapsulation.lib if it doesn't exist
            ok, msg = init_encap_lib(_windows_encap_lib_path)
            if not ok: return False, msg
            # Do the Windows busywork to compile the code
            return _windows_link(c_path, exe_path)
        case _:
            raise NotImplementedError(f"Operating system '{sys.platform}' not supported")


def _linux_link(c_path: str, exe_path: str) -> tuple[bool, str]:
    # Find the C compiler
    cc = shutil.which("cc")
    if cc is None:
        return False, "No C compiler found"

    # Find the libSdlEncapsulation.a file.
    encap_a_lib_file = os.path.join(_encap_bin_path, "libSdlEncapsulation.a")
    if not os.path.exists(encap_a_lib_file):
        return False, "SDL Encapsulation library not found at path: " + encap_a_lib_file

    # Compile the C code to an executable
    result = subprocess.run([cc, c_path, encap_a_lib_file, "-o", exe_path, "-I", _encap_incl_path, "-lm", "-lSDL2"],
                            capture_output=True)

    # Check the result of that command and we're done! That was so simple!
    # (Now go read the function below for the TOTAL OPPOSITE!)
    return result.returncode == 0, "Compilation failed. Compiler output:\n" + result.stderr.decode("utf-8")


def _windows_link(c_path: str, exe_path: str) -> tuple[bool, str]:
    # Runs the vsenv.bat file, and caches its result in %TEMP%/drawpp_env_vars.txt
    def _env_data():
        temp_loc = os.path.join(os.getenv("TEMP"), "drawpp_env_vars.txt")
        if os.path.exists(temp_loc):
            # We have a cache! Use it instead of running that slow script...
            with open(temp_loc, "r") as f:
                return f.read()
        else:
            # Run the vsenv.bat file, which is going to output all the environment variables int KEY=VALUE format.
            vs_env_path = os.path.join(_script_path, "windows", "vsenv.bat")
            vs_env_res = subprocess.run([vs_env_path], capture_output=True, shell=True, encoding="utf-8")

            # Make sure the script succeeded
            if vs_env_res.returncode != 0:
                return None

            # Write it into the cache.
            try:
                with open(temp_loc, "w") as f:
                    f.write(vs_env_res.stdout)
            except Exception as e:
                # That's weird. But that won't stop us from compiling the code.
                print("Warning: failed to write the Visual Studio environment variables to cache: " + str(e))

            return vs_env_res.stdout

    # Let's find visual studio! This will be fun, trust me!

    # The batch script outputs environment variables in KEY=VALUE format. Let's parse that.
    # We're starting by using our "vsenv.bat" script that will output all environment variables we need.
    env_data = _env_data()
    if env_data is None:
        return False, ("Visual Studio environment not found. Please install Visual Studio with the desktop development "
                       "workload (make sure to install it with C/C++ compilation support).")

    # We have a raw file, so split it into lines and get the KEY=VALUE pairs
    env_lines = env_data.split("\n")
    env_regex = re.compile("^(.+)=(.*)$")
    env_map = {
        m.group(1): m.group(2) for m
        in [env_regex.match(l) for l in env_lines if l]
        if m is not None
    }

    # Next, let's find the PATH environment variable so we can find where the C compiler is located.
    # We can't "just" use access the map by doing map["PATH"] since "PATH" can come in many cased forms:
    # path, Path... That's annoying but that's how it is!
    path_env = None
    for k, v in env_map.items():
        if k.lower() == "path":
            path_env = v
            break

    assert path_env, "The PATH should not be empty. WHAT HAPPENED?!"

    # Find the path of the C compiler.
    cl = shutil.which("cl", path=path_env)
    if cl is None:
        return False, "Visual Studio C compiler not found in the PATH given by vsenv.bat: " + path_env

    # Define some paths for the C compiler beforehand. Mainly just paths to SDL2 and encapsulation libraries.
    sdl_include_path = os.path.join(_libs_path, "SDL2-devel-2.30.11-VC", "include")
    sdl2_dll_path = os.path.join(_encap_bin_path, "SDL2.dll")
    sdl2_lib_path = os.path.join(_encap_bin_path, "SDL2.lib")
    sdl2_main_lib_path = os.path.join(_encap_bin_path, "SDL2main.lib")
    encap_lib_path = os.path.join(_encap_bin_path, "sdlEncapsulation.lib")

    # Make sure that each file/folder exists:
    for p in (sdl_include_path, sdl2_dll_path, sdl2_lib_path, sdl2_main_lib_path, encap_lib_path):
        if not os.path.exists(p):
            return False, f"Required library does not exist: {p}. Did you forget to compile sdlEncapsulation?"

    # Convert our C and executable paths to absolute paths to avoid any surprises.
    c_path, exe_path = os.path.abspath(c_path), os.path.abspath(exe_path)

    # Run the C compiler with two tons of arguments.
    cr = subprocess.run([cl,
                         "-I", _encap_incl_path,  # sdlEncapsulation include path
                         "-I", sdl_include_path,  # SDL2 include path
                         c_path,  # Compile our C file
                         encap_lib_path,  # Statically link to the SDL Encapsulation library
                         sdl2_lib_path, sdl2_main_lib_path,  # Statically link to SDL libraries
                         "shell32.lib",  # Statically link to Shell32 cause for some reason SDL needs that?
                         "/MDd",  # Use the Universal CRT library in debug mode
                         "/link",  # Run the linker
                         f"/out:{exe_path}",  # Produce the executable in the wanted path
                         "/MACHINE:X64",  # 64-bit supremacy
                         "/SUBSYSTEM:CONSOLE",  # Console application (and not a WIN32/GUI application)
                         ], env=env_map, capture_output=True)
    if cr.returncode != 0:
        return False, "Compilation failed. Compiler output:\n" + cr.stderr.decode("utf-8")

    # Compilation was successful! Now let's just copy our SDL2.dll next to the executable.
    try:
        shutil.copy(sdl2_dll_path, os.path.dirname(exe_path))
    except Exception as e:
        return False, "Failed to copy SDL2.dll to the executable directory: " + str(e)

    return True, ""
