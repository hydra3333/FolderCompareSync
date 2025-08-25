# FolderCompareSync_Global_Imports.py
# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
#from FolderCompareSync_Global_Imports import *

# import out global constants first ...
# HERE WE ASSUME that none of the global constants depend on imports :)
#from FolderCompareSync_Global_Constants import *

# import our flushed_logging before other modules
#from flushed_logging import *   # includes LoggerManager
#from flushed_logging import log_and_flush, get_log_level, LoggerManager

# ============================================================================
# GLOBAL IMPORTS
# ============================================================================
# These imports control various aspects of the application behavior and UI.
# Add or Remove these imports to customize the application without hunting through code.

# ----- snapshot BEFORE imports so we can detect what gets added -----
_BASE_NAMES = set(globals().keys())

# --- PUT IMPORTS HERE ONLY - stdlib imports you always want available ---
import platform
import os
import sys
import importlib
import threading
import queue
import hashlib
import re
import time
import stat
import fnmatch
import argparse
import tempfile
import shutil
import uuid
import ctypes
from ctypes import wintypes, Structure, c_char_p, c_int, c_void_p, POINTER, byref
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Any, Union
from typing import Final # If configured, Final can tell type checkers (like mypy, VS Code) that a name is meant to be constant (i.e. not reassigned, not overridden in subclasses). It does nothing at runtime.
from enum import Enum
# import tkinter safely, see below
#import tkinter as tk
#from tkinter import ttk, filedialog, messagebox
#import tkinter.font as tkfont
import threading
import logging
import traceback
import gc # for python garbage collection of unused structures etc
import ast
import inspect
import json
import locale
import math
from types import ModuleType
# Import these 2 for Memory mapping support:
import mmap
import msvcrt

# BLAKE3_AVAILABLE is declared as GLOBAL and reset below
BLAKE3_AVAILABLE = False

# ---------- helpers for late/optional imports & exporting ----------

def _export_name(name: str) -> None:
    """Add a name to __all__ if not already present."""
    lst = globals().setdefault("__all__", [])
    if name not in lst:
        lst.append(name)

def ensure_global_import(module_name: str, alias: str | None = None) -> ModuleType | None:
    """
    OPTIONAL/LATE IMPORTS ONLY.
    Import a module at runtime and export it via __all__.
    Usage:
        from FolderCompareSync_Global_Imports import ensure_global_import, bind_latest
        pd = ensure_global_import("pandas", alias="pd")
        if pd:
            print("Pandas is available:", pd.__version__)
            # re-import, to see 'pd' in your local namespace:
            # Instead of 'from ... import *' inside a function (illegal), do:
            bind_latest(globals())  # now 'pd' is available in the caller module's globals
    Or:
        from FolderCompareSync_Global_Imports import ensure_global_import, bind_latest
        ensure_global_import("importlib")
        # Instead of 'from ... import *' inside a function (illegal), do:
        bind_latest(globals())  # now 'pd' is available in the caller module's globals
    """
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return None
    name = alias or module_name.rsplit(".", 1)[-1]
    globals()[name] = mod
    _export_name(name)
    return mod

def ensure_global_import_from(module_name: str, *names: str) -> bool:
    """
    OPTIONAL/LATE IMPORTS ONLY.
    Import one or more names from a module at runtime and export them via __all__.
    Usage:
        from FolderCompareSync_Global_Imports import ensure_global_import_from, bind_latest
        ok = ensure_global_import_from("math", "isclose", "dist")
        if ok:
            bind_latest(globals())  # brings 'isclose' and 'dist' into your module's globals
    """
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return False
    ok = True
    for n in names:
        try:
            obj = getattr(mod, n)
        except AttributeError:
            ok = False
            continue
        globals()[n] = obj
        _export_name(n)
    return ok

def bind_latest(target_globals: dict) -> None:
    """
    Copy the current exported names from THIS MODULE into the caller's globals().
    Use this instead of 'from ... import *' inside functions (which is illegal).

    Example:
        from FolderCompareSync_Global_Imports import ensure_global_import, bind_latest
        if ensure_global_import("pandas", alias="pd"):
            bind_latest(globals())  # now 'pd' is bound in the caller's module
    """
    # Only copy names intended for export
    for name in __all__:
        target_globals[name] = globals()[name]

# ---------- check core third-party deps are pip installed and available, then do NORMAL imports ----------

# Add this near _check_dependencies
_OPTIONAL_INSTALL_HINTS = {
    # key by import name (right-hand side of your tuple)
    "tkinter": (
        "Tk/tkinter isn't usually installed via pip.\n"
        "Windows: re-run the official Python installer and select 'tcl/tk'.\n"
        # Add more OS hints if you wish:
        # "Debian/Ubuntu:  sudo apt-get install python3-tk\n"
        # "Fedora:         sudo dnf install python3-tkinter\n"
        # "Arch:           sudo pacman -S tk\n"
    ),
}

def _check_dependencies(deps: list[tuple[str, str]]) -> None:
    """
    deps: list of (pip_pkg_name, import_name) to verify.
    On failure: print clear instructions and exit with status 1.
    """
    missing_pip: list[str] = []                      # ones we'll suggest 'pip install' for
    missing_custom_msgs: list[tuple[str, str]] = []  # (import_name, msg) pairs for special cases

    for pkg_name, import_name in deps:
        try:
            importlib.import_module(import_name)
        except ImportError:
            if import_name in _OPTIONAL_INSTALL_HINTS:
                missing_custom_msgs.append((import_name, _OPTIONAL_INSTALL_HINTS[import_name]))
            else:
                missing_pip.append(pkg_name)

    if missing_pip or missing_custom_msgs:
        lines = ["ERROR: Missing required Python packages/components:\n"]
        if missing_pip:
            lines.append("Install with:\n    pip install --upgrade " + " ".join(missing_pip) + "\n")
        for import_name, msg in missing_custom_msgs:
            lines.append(f"To install '{import_name}':\n{msg}\n")
        sys.stderr.write("".join(lines))
        raise SystemExit(1)

def check_and_import_core_deps() -> None:
    """
    Verify required external deps exist,
    then import them *normally* so they are always available to any module that star-imports this file.
    """
    
    # *** Place EXTERNAL (pip/installer) modules here to verify they are available
    _check_dependencies([
        ("tzdata",          "zoneinfo"),     # tzdata provides zoneinfo database
        ("python-dateutil", "dateutil.tz"),  # dateutil.tz for tzwinlocal on Windows
        ("tkinter",         "tkinter"),      # tkinter required
        ("blake3",          "blake3"),        # blake3 required
    ])

    # *** Passed checking
    # Now do NORMAL imports (not "ensure_*" calls). These then auto become part of this module's globals:
    import zoneinfo
    from zoneinfo import ZoneInfo
    from dateutil.tz import tzwinlocal
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import tkinter.font as tkfont
    import blake3
    # promote all these new locals into module globals
    g = globals()
    for name, val in locals().items():
        if name not in ("_check_dependencies", "g"):  # skip helper local variables
            g[name] = val
    # Flag blake3 is available
    global BLAKE3_AVAILABLE
    BLAKE3_AVAILABLE    = True

# ============================================================================
# WINDOWS API BINDINGS AND STRUCTURES (M15) - COPY-RELATED ONLY
# ============================================================================

def setup_windows_api_bindings():
    """
    Setup Windows API function bindings with proper signatures for enhanced file copy system.
    
    NOTE: Timestamp-related API bindings have been moved to FileTimestampManager_class.py
    This function now only handles copy-related Windows API bindings.
    
    This function configures Windows API calls needed for:
    - CopyFileExW with progress callbacks
    - Drive type detection 
    - File attribute handling
    - Path resolution and symbolic link handling
    - Comprehensive error handling
    """
    
    # Get kernel32 handle
    kernel32 = ctypes.windll.kernel32
    
    # ============================================================================
    # PROGRESS CALLBACK FUNCTION TYPE
    # ============================================================================
    
    PROGRESS_ROUTINE = ctypes.WINFUNCTYPE(
        wintypes.DWORD,              # Return type
        wintypes.LARGE_INTEGER,      # TotalFileSize
        wintypes.LARGE_INTEGER,      # TotalBytesTransferred  
        wintypes.LARGE_INTEGER,      # StreamSize
        wintypes.LARGE_INTEGER,      # StreamBytesTransferred
        wintypes.DWORD,              # StreamNumber
        wintypes.DWORD,              # CallbackReason
        wintypes.HANDLE,             # SourceFile
        wintypes.HANDLE,             # DestinationFile
        wintypes.LPVOID              # Data
    )
    
    # ============================================================================
    # WINDOWS API FUNCTION SIGNATURES - COPY-RELATED ONLY
    # ============================================================================
    
    # CopyFileExW - Enhanced file copy with progress callbacks
    kernel32.CopyFileExW.argtypes = [
        wintypes.LPCWSTR,            # lpExistingFileName
        wintypes.LPCWSTR,            # lpNewFileName
        PROGRESS_ROUTINE,            # lpProgressRoutine
        wintypes.LPVOID,             # lpData
        wintypes.LPBOOL,             # pbCancel
        wintypes.DWORD               # dwCopyFlags
    ]
    kernel32.CopyFileExW.restype = wintypes.BOOL

    # >>> CHANGE START: expose SetFilePointerEx / SetEndOfFile signatures for all modules
    # BOOL SetFilePointerEx(HANDLE hFile, LARGE_INTEGER liDistanceToMove, PLARGE_INTEGER lpNewFilePointer, DWORD dwMoveMethod)
    kernel32.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
    kernel32.SetFilePointerEx.restype  = wintypes.BOOL
    # BOOL SetEndOfFile(HANDLE hFile)
    kernel32.SetEndOfFile.argtypes = [wintypes.HANDLE]
    kernel32.SetEndOfFile.restype  = wintypes.BOOL
    # Common move-method constants (FILE_BEGIN/FILE_CURRENT/FILE_END)
    FILE_BEGIN   = 0
    FILE_CURRENT = 1
    FILE_END     = 2
    __export('FILE_BEGIN'); __export('FILE_CURRENT'); __export('FILE_END')
    # <<< CHANGE END

    # GetDiskFreeSpaceExW - Disk space checking
    kernel32.GetDiskFreeSpaceExW.argtypes = [
        wintypes.LPCWSTR,                           # lpDirectoryName
        ctypes.POINTER(wintypes.ULARGE_INTEGER),    # lpFreeBytesAvailable
        ctypes.POINTER(wintypes.ULARGE_INTEGER),    # lpTotalNumberOfBytes
        ctypes.POINTER(wintypes.ULARGE_INTEGER)     # lpTotalNumberOfFreeBytes
    ]
    kernel32.GetDiskFreeSpaceExW.restype = wintypes.BOOL

    # GetDriveTypeW - Drive type detection for strategy selection
    kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetDriveTypeW.restype = wintypes.UINT

    # GetFileAttributesW - File attribute checking
    kernel32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetFileAttributesW.restype = wintypes.DWORD

    # Enhanced path resolution APIs
    kernel32.GetFullPathNameW.argtypes = [
        wintypes.LPCWSTR,                    # lpFileName
        wintypes.DWORD,                      # nBufferLength
        wintypes.LPWSTR,                     # lpBuffer
        ctypes.POINTER(wintypes.LPWSTR)      # lpFilePart
    ]
    kernel32.GetFullPathNameW.restype = wintypes.DWORD

    kernel32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,                     # hFile
        wintypes.LPWSTR,                     # lpszFilePath
        wintypes.DWORD,                      # cchFilePath
        wintypes.DWORD                       # dwFlags
    ]
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD

    # GetLastError - Error code retrieval (still needed for copy operations)
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD
    
    # Expose these to the global namespace
    g = globals()
    g['kernel32'] = kernel32
    g['PROGRESS_ROUTINE'] = PROGRESS_ROUTINE
    _export_name('kernel32')
    _export_name('PROGRESS_ROUTINE')

# ---------- function to auto-build __all__ from what changed during imports ----------

def _auto_build_all() -> list[str]:
    """
    Export everything newly introduced by this module's imports,
    excluding private names and our internal helper symbols.
    """
    new_names = {k for k in globals().keys() if k not in _BASE_NAMES}
    exclude = {
        "__all__", "_BASE_NAMES",
        # exclude helpers from star-export (they can still be imported explicitly)
        "_export_name",
        "ensure_global_import", "ensure_global_import_from", "bind_latest",
        "_check_dependencies", "check_and_import_core_deps", "_auto_build_all",
        "setup_windows_api_bindings",
    }
    return sorted(
        n for n in new_names
        if not n.startswith("_") and n not in exclude
    )

# ---------- Actually build the list of imports to be exported for all to see ----------

# Setup Windows API bindings
setup_windows_api_bindings()

# Run the dependency check + imports at module import time
check_and_import_core_deps()

# Build the list of exports (names available via 'from ... import *')
__all__ = _auto_build_all()

#####################################################################################
# HOW TO USE THIS MODULE TO PERFORM GLOBAL IMPORTS WITHIN EACH MODULE
#
# In every file (main program and submodules but not global_constants), import like:
#     from FolderCompareSync_Global_Imports import *
#
# To add an import dependency later at runtime (e.g. pandas):
#     from FolderCompareSync_Global_Imports import ensure_global_import, ensure_global_import_from, bind_latest
#     # like: import pandas as pd
#     pd = ensure_global_import("pandas", alias="pd")
#     if pd:
#         print("pandas available:", pd.__version__)
#         # re-import all so that 'pd' is now visible in your local namespace
#         bind_latest(globals())   # instead of 'from ... import *' inside a function (illegal)
#
# To add an import of specific functions/classes later at runtime :
#     from FolderCompareSync_Global_Imports import ensure_global_import_from, bind_latest # for access to function to add global imports
#     # like: from math import isclose, dist
#     ensure_global_import_from("math", "isclose", "dist")
#     # re-import so they bind locally:
#     bind_latest(globals())      # 'isclose' and 'dist' are now bound in your module
#     print(isclose(0.1 + 0.2, 0.3))  # True
#
# Remember:
# - Later additions update THIS module's globals and __all__ but not for any other modules
# - Other modules do NOT automatically see new names; if you add at runtime, call bind_latest(globals()).
#####################################################################################