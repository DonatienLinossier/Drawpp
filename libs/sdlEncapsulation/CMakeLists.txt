cmake_minimum_required(VERSION 3.10)

project(sdlEncapsulation C)

# Set the source directory
set(SRC_DIR src)
set(sdlEncapsulation_include_dir "include")

# Specify the path to the SDL2 installation (adjust path if necessary)
if(WIN32)
    set(CMAKE_PREFIX_PATH "${CMAKE_SOURCE_DIR}/libs/SDL2-2.30.8/x86_64-w64-mingw32")
endif()

# Find SDL2 package
find_package(SDL2 REQUIRED)
if(NOT SDL2_FOUND)
    message(FATAL_ERROR "SDL2 not found. Please install SDL2.")
endif()

# Include directories
include_directories(${sdlEncapsulation_include_dir})
include_directories(${SDL2_INCLUDE_DIRS})

# Specify the source files for the shared library
set(SDL_ENCAPSULATION_SRC
        ${SRC_DIR}/sdlEncapsulation.c
)

# Create the shared library (DLL) for SDL encapsulation
add_library(sdlEncapsulation SHARED ${SDL_ENCAPSULATION_SRC})

# Link SDL2 libraries to your shared library
target_link_libraries(sdlEncapsulation ${SDL2_LIBRARIES})

# Set the output name for the DLL
set_target_properties(sdlEncapsulation PROPERTIES OUTPUT_NAME "sdlEncapsulation")

set_target_properties(sdlEncapsulation PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin"  # Path to the /bin directory
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/bin"  # Path to the /bin directory
)