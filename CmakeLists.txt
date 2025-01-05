cmake_minimum_required(VERSION 3.10)

project(drawppCompiler C)

# Set the output directory for the compiled files
set(OUTPUT_DIR .drawppTmp)

# Add the submodule for sdlEncapsulation only if it hasn't been compiled yet
if(NOT TARGET sdlEncapsulation)
    add_subdirectory(libs/sdlEncapsulation)
endif()

include_directories(${CMAKE_SOURCE_DIR}/libs/sdlEncapsulation/include)

# Specify the main source file for the executable
set(MAIN_SRC ${OUTPUT_DIR}/tmp.c)

# Create the main executable
add_executable(${PROJECT_NAME} ${MAIN_SRC})

# Link the shared library from the submodule
target_link_libraries(${PROJECT_NAME} sdlEncapsulation)

# Copy sdl2.dll to the output directory if required
if(WIN32)
    if (CMAKE_C_COMPILER_ID MATCHES "MSVC")
        # We have a MSVC compiler, use the VC version of SDL2
        set(SDL2_DLL "${PROJECT_SOURCE_DIR}/libs/SDL2-devel-2.30.11-VC/lib/x64/SDL2.dll")
    else()
        # Else, use the MinGW version.
        set(SDL2_DLL "${PROJECT_SOURCE_DIR}/libs/SDL2-2.30.8-mingw/x86_64-w64-mingw32/bin/SDL2.dll")
    endif()
    if(EXISTS "${SDL2_DLL}")
        # Use add_custom_command to copy the file to the right output directory.
        add_custom_command(TARGET drawppCompiler POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
        ${SDL2_DLL}
        $<TARGET_FILE_DIR:drawppCompiler>/SDL2.dll)
    else()
        message(FATAL_ERROR "SDL2 DLL not found at ${SDL2_DLL}")
    endif()
endif()