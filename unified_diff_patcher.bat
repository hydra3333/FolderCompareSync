@echo off
@setlocal ENABLEDELAYEDEXPANSION
@setlocal enableextensions
REM Apply a unified diff using Python patcher script
REM Usage: Drag and drop .diff file OR run from cmd:
REM   ApplyPatch.bat changes.diff [--dry-run] [--verbose] [--base-dir path]

set SCRIPT=unified_diff_patcher.py

if "%~1"=="" (
    echo Usage: %~nx0 patchfile.diff [--dry-run] [--verbose] [--base-dir path]
    exit /b 1
)

REM Call Python with all arguments passed to this batch file
python "%~dp0%SCRIPT%" %*
pause
