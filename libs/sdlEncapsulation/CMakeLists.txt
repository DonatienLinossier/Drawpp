cmake_minimum_required(VERSION 3.10)

project(sdlEncapsulation C)

# Set the source directory
set(SRC_DIR src)
set(sdlEncapsulation_include_dir "include")

# Specify the path to the SDL2 installation (adjust path if necessary)
if(WIN32)
    if (CMAKE_C_COMPILER_ID MATCHES "MSVC")
        # We have a MSVC compiler, use the VC version of SDL2

        # PROJECT_SOURCE_DIR uses the folder containing this CMakeLists.txt file,
        # instead of CMAKE_SOURCE_DIR which uses the folder containing the root CMakeLists
        set(SDL_DIR "${PROJECT_SOURCE_DIR}/../SDL2-devel-2.30.11-VC")
    else()
        set(SDL_DIR "${PROJECT_SOURCE_DIR}/../SDL2-devel-2.30.11-mingw/x86_64-w64-mingw32")
    endif()

    set(CMAKE_PREFIX_PATH ${SDL_DIR})
endif()

# Find SDL2 package
# Required package on Ubuntu: libsdl2-dev
find_package(SDL2 REQUIRED)
if(NOT SDL2_FOUND)
    message(FATAL_ERROR "SDL2 not found. Please install SDL2.")
    if (UNIX)
        message(FATAL_ERROR "You can install it by running the following command on Debian/Ubuntu:\n"
                            "    sudo apt-get install libsdl2-dev")
    endif()
endif()

# Include directories
include_directories(${sdlEncapsulation_include_dir})
include_directories(${SDL2_INCLUDE_DIRS})

# Specify the source files for the shared library
set(SDL_ENCAPSULATION_SRC
        ${SRC_DIR}/sdlEncapsulation.c
)

# Create the static library (LIB) for SDL encapsulation
# It's much more practical than a shared library when we're going to link to it manually
# in Python.
add_library(sdlEncapsulation STATIC ${SDL_ENCAPSULATION_SRC})

# Link SDL2 libraries to your shared library
target_link_libraries(sdlEncapsulation ${SDL2_LIBRARIES})

# Set the output name for the DLL
set_target_properties(sdlEncapsulation PROPERTIES OUTPUT_NAME "sdlEncapsulation")

set_target_properties(sdlEncapsulation PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin"  # Path to the /bin directory
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin"  # Path to the /bin directory
        # Actually, only this path is used since we're building a static lib.
        # Using the $<1:xxx> syntax to avoid debug/release directories on MSVC.
        # https://stackoverflow.com/questions/47175912/using-cmake-how-to-stop-the-debug-and-release-subdirectories
        ARCHIVE_OUTPUT_DIRECTORY $<1:${CMAKE_CURRENT_SOURCE_DIR}/bin>  # Path to the /bin directory
)

# For handiness, let's copy all the SDL2 DLLs to the /bin directory.
# This will allow us to copy all necessary DLLs in one command later on.
if(WIN32)
    if (CMAKE_C_COMPILER_ID MATCHES "MSVC")
        add_custom_command(TARGET sdlEncapsulation POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy
            "${SDL_DIR}/lib/x64/SDL2.dll"
            $<TARGET_FILE_DIR:sdlEncapsulation>/SDL2.dll
            COMMAND ${CMAKE_COMMAND} -E copy
            "${SDL_DIR}/lib/x64/SDL2.lib"
            $<TARGET_FILE_DIR:sdlEncapsulation>/SDL2.lib
            COMMAND ${CMAKE_COMMAND} -E copy
            "${SDL_DIR}/lib/x64/SDL2main.lib"
            $<TARGET_FILE_DIR:sdlEncapsulation>/SDL2main.lib
            )
    else()
        add_custom_command(TARGET sdlEncapsulation POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy
            "${SDL_DIR}/lib/libSDL2.a"
            $<TARGET_FILE_DIR:sdlEncapsulation>/libSDL2.a
            COMMAND ${CMAKE_COMMAND} -E copy
            "${SDL_DIR}/lib/x64/libSDL2main.a"
            $<TARGET_FILE_DIR:sdlEncapsulation>/libSDL2main.a
            COMMAND ${CMAKE_COMMAND} -E copy
            "${SDL_DIR}/bin/SDL2.dll"
            $<TARGET_FILE_DIR:sdlEncapsulation>/SDL2.dll
        )
    endif()
endif()