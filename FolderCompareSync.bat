@echo off
@setlocal ENABLEDELAYEDEXPANSION
@setlocal enableextensions

REM DEBUG PAUSING
REM set "do_pause="
set "do_pause=PAUSE"

REM Run python to get version string like "3.13.5"
for /f "delims=" %%v in ('python -c "import sys; print(sys.version.split()[0])"') do set "PY_VERSION=%%v"
REM Split at first two dots (major.minor.patch) then build variables To get major=3 and minor=13, patch=5 from "3.13.5"
for /f "tokens=1,2,3 delims=." %%a in ("%PY_VERSION%") do (
    set "PYTHON_VERSION_MAJOR=%%a"
    set "PYTHON_VERSION_MINOR=%%b"
    set "PYTHON_VERSION_PATCH=%%c"
    set "PYTHON_VERSION_MAJOR_MINOR=!PYTHON_VERSION_MAJOR!!PYTHON_VERSION_MINOR!"
    set "PYTHON_VERSION_MAJOR_MINOR_DOT=!PYTHON_VERSION_MAJOR!.!PYTHON_VERSION_MINOR!"
    set "PYTHON_VERSION=!PYTHON_VERSION_MAJOR!.!PYTHON_VERSION_MINOR!.!PYTHON_VERSION_PATCH!"
)
echo Detected Python version: '%PY_VERSION%'
echo Major version:           '%PYTHON_VERSION_MAJOR%'
echo Minor version:           '%PYTHON_VERSION_MINOR%'
echo Patch version:           '%PYTHON_VERSION_PATCH%'
echo Major/Minor version:     '%PYTHON_VERSION_MAJOR_MINOR%'
echo Major/Minor version dot: '%PYTHON_VERSION_MAJOR_MINOR_DOT%'
echo Full version:            '%PYTHON_VERSION%'

python FolderCompareSync.py

pause
goto :eof
