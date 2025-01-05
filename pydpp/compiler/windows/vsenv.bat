@echo off
REM This script prints all environment variables necessary to compile Windows programs

REM Set the current encoding to UTF-8, so Python can read paths correctly.
chcp 65001 > nul

REM Get the directory of this script
set script_dir=%~dp0

REM Get the directory of Visual Studio
for /f "tokens=*" %%i in ('%script_dir%vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath') do set vs_dir=%%i

if not defined vs_dir (
    echo Couldn't find an installation of Visual Studio with Visual C++ tools.
    exit /b 1
)

REM Run the "vsdevcmd.bat" script to get environment variables
call "%vs_dir%\Common7\Tools\vsdevcmd.bat" -arch=x64 -host_arch=x64 -no_logo

REM Output all environment variables (Yup, you do this with "set" alone!)
set