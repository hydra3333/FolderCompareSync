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

# kernel32 is initialized by setup_windows_api_bindings().
# IMPORTANT: it must be explicitly exported at the end of setup_windows_api_bindings()
# using the module's globals() and _export_name(), so that star-importers can see it.
kernel32 = None

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
        ("tzdata",          "zoneinfo"),      # tzdata provides zoneinfo database
        ("python-dateutil", "dateutil.tz"),   # dateutil.tz for tzwinlocal on Windows
        ("tkinter",         "tkinter"),       # tkinter required
        ("blake3",          "blake3"),        # blake3 required
        ("pywin32",         "win32con"),      # pywin32: win32con - All Windows constants (FILE_ATTRIBUTE_, GENERIC_, etc.) 
        ("pywin32",         "win32api"),      # pywin32: win32api - Windows API functions
        ("pywin32",         "win32file"),     # pywin32: win32file - File operations
        ("pywin32",         "winerror"),      # pywin32: winerror - Windows error codes
        ("pywin32",         "winioctlcon"),   # pywin32: FSCTL_* / IOCTL_* (compression, sparse, allocated ranges)
        ("pywin32",         "win32security"), # pywin32: win32security - Security constants and functions
        ("pywin32",         "win32com.shell.shellcon"), # pywin32: Shell constants module
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
    import win32con
    import win32api
    import win32file
    import winerror
    import winioctlcon
    import win32security
    from win32com.shell import shellcon
    
    # promote all these new locals into module globals
    g = globals()
    for name, val in locals().items():
        if name not in ("_check_dependencies", "g"):  # skip helper local variables
            g[name] = val
    # Flag blake3 is available
    global BLAKE3_AVAILABLE
    BLAKE3_AVAILABLE    = True

# ============================================================================
# Add raw, unaliased constant resolver + error formatter
# Search these raw pywin32 modules (no aliases) for constants by name
# ============================================================================

MISSING_OBJECT = object()  # unique sentinel
PYWIN32_MODULES = (win32con, win32api, win32file, winerror, winioctlcon, win32security, shellcon)
def W(name: str, default: object = MISSING_OBJECT):
    """
    Resolve a Win32 constant by name across pywin32 modules.
    Example: W("FILE_FLAG_OPEN_REPARSE_POINT"), W("COPY_FILE_RESTARTABLE")
    If not found and `default` is provided, returns it; otherwise raises AttributeError.
    """
    for mod in PYWIN32_MODULES:
        val = getattr(mod, name, None)
        # IMPORTANT: 0 is a valid constant; only None means “not here”
        if val is not None:
            return val
    if default is MISSING_OBJECT:
        raise AttributeError(f"Constant not found: {name}")
    return default

def format_last_error(err: int | None = None) -> str:
    """Best-effort formatting of a Win32 error code (defaults to GetLastError)."""
    if err is None:
        err = ctypes.get_last_error()
    try:
        return (win32api.FormatMessage(err) or "").strip()
    except Exception:
        return f"ERROR: Windows Error: {err}"

# ============================================================================
# WINDOWS API BINDINGS AND STRUCTURES (M15) - COPY-RELATED ONLY
# ============================================================================

# Correct LARGE_INTEGER definition (it's a union in Windows)
class LARGE_INTEGER(ctypes.Union):
    class _STRUCT(ctypes.Structure):
        _fields_ = [
            ("LowPart", wintypes.DWORD),
            ("HighPart", ctypes.c_long),
        ]
    
    _anonymous_ = ("u",)
    _fields_ = [
        ("QuadPart", ctypes.c_longlong),
        ("u", _STRUCT),
    ]

# Correct ULARGE_INTEGER definition (it's a union in Windows)
class ULARGE_INTEGER(ctypes.Union):
    class _STRUCT(ctypes.Structure):
        _fields_ = [
            ("LowPart",  wintypes.DWORD),
            ("HighPart", wintypes.DWORD),
        ]
    _anonymous_ = ("u",)
    _fields_ = [
        ("QuadPart", ctypes.c_ulonglong),
        ("u", _STRUCT),
    ]

# Correct FILE_ALLOCATION_INFO structure
class FILE_ALLOCATION_INFO(ctypes.Structure):
    _fields_ = [("AllocationSize", LARGE_INTEGER)]

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

    # Get kernel32 handle (assigned to module-level variable name)
    global kernel32
    kernel32 = ctypes.windll.kernel32

    # ============================================================================
    # PROGRESS CALLBACK FUNCTION TYPE
    # ============================================================================
    
    PROGRESS_ROUTINE = ctypes.WINFUNCTYPE(
        wintypes.DWORD,              # Return type
        LARGE_INTEGER,               # TotalFileSize
        LARGE_INTEGER,               # TotalBytesTransferred  
        LARGE_INTEGER,               # StreamSize
        LARGE_INTEGER,               # StreamBytesTransferred
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

    #  expose SetFilePointerEx / SetEndOfFile / SetFileInformationByHandle + structs
    #kernel32.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
    kernel32.SetFilePointerEx.argtypes = [
        wintypes.HANDLE,
        LARGE_INTEGER,                       # liDistanceToMove (by value)
        ctypes.POINTER(LARGE_INTEGER),       # lpNewFilePointer (out)
        wintypes.DWORD                       # dwMoveMethod (win32con.FILE_BEGIN/CURRENT/END)
    ]
    kernel32.SetFilePointerEx.restype  = wintypes.BOOL
    # BOOL SetEndOfFile(HANDLE hFile)
    kernel32.SetEndOfFile.argtypes = [wintypes.HANDLE]
    kernel32.SetEndOfFile.restype  = wintypes.BOOL
    # BOOL SetFileInformationByHandle(HANDLE, FILE_INFO_BY_HANDLE_CLASS, LPVOID, DWORD)
    kernel32.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD]
    kernel32.SetFileInformationByHandle.restype  = wintypes.BOOL
    # Export commonly used constants (FILE_INFO_BY_HANDLE_CLASS ENUM)
    FILE_INFO_BY_HANDLE_FileAllocationInfo = 5    # OLD BAD: 19  # matches Win32 FILE_INFO_BY_HANDLE_CLASS::FileAllocationInfo
    FILE_INFO_BY_HANDLE_FileEndOfFileInfo  = 6    # OLD BAD: 20  # (not used here but handy)
    # Make these available to star-importers
    g = globals()
    g['FILE_ALLOCATION_INFO'] = FILE_ALLOCATION_INFO
    g['FILE_INFO_BY_HANDLE_FileAllocationInfo'] = FILE_INFO_BY_HANDLE_FileAllocationInfo
    g['FILE_INFO_BY_HANDLE_FileEndOfFileInfo']  = FILE_INFO_BY_HANDLE_FileEndOfFileInfo
    _export_name('FILE_ALLOCATION_INFO')
    _export_name('FILE_INFO_BY_HANDLE_FileAllocationInfo')
    _export_name('FILE_INFO_BY_HANDLE_FileEndOfFileInfo')

    # GetDiskFreeSpaceExW - Disk space checking
    kernel32.GetDiskFreeSpaceExW.argtypes = [
        wintypes.LPCWSTR,                  # lpDirectoryName
        ctypes.POINTER(ULARGE_INTEGER),    # lpFreeBytesAvailable
        ctypes.POINTER(ULARGE_INTEGER),    # lpTotalNumberOfBytes
        ctypes.POINTER(ULARGE_INTEGER)     # lpTotalNumberOfFreeBytes
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
    # Export kernel32 per module-level note so star-importers see it.
    g['kernel32'] = kernel32
    g['PROGRESS_ROUTINE'] = PROGRESS_ROUTINE
    _export_name('kernel32')
    _export_name('PROGRESS_ROUTINE')

# ================================================================================
# FILESYSTEM CAPABILITY HELPERS (non-destructive probes + simple attribute checks)
# only set these up AFTER calling setup_windows_api_bindings()
# --------------------------------------------------------------------------------
# Return convention for all helpers below:
#   (result: Optional[bool], err: Optional[int], message: Optional[str])
#   - result is True/False when known; None when unsupported/unknown or an error occurred
#   - err is a Win32 error code from GetLastError (or None when not applicable)
#   - message is a human-readable string (usually from format_last_error(err))
# ================================================================================

def setup_filesystem_capability_helpers() -> None:
    """
    Define and export non-destructive filesystem capability helpers.
    Relies on the module-level `kernel32` created by setup_windows_api_bindings().

    All public helpers return a tuple: (result: Optional[bool], err: Optional[int], message: Optional[str]),
    except the two setters which return (ok: bool, err: Optional[int], message: Optional[str]).
    Each helper includes short Examples in the docstring.
    """
    global kernel32

    # ---- internal: idempotent DeviceIoControl prototype binding -----------------
    def _ensure_deviceiocontrol_signature() -> None:
        global kernel32
        try:
            kernel32.DeviceIoControl.argtypes = [
                wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID
            ]
            kernel32.DeviceIoControl.restype = wintypes.BOOL
        except Exception:
            pass  # already bound or unavailable; fine

    # This is being called at the def setup_filesystem_capability_helpers() level, but kernel32 is at module level so all OK:
    # Eagerly bind once at setup time (the helpers which rely on it still re-bind defensively before IOCTL use).
    _ensure_deviceiocontrol_signature()

    # ---- public: get_file_attributes --------------------------------------------
    def get_file_attributes(path: str) -> tuple[int | None, int | None, str | None]:
        """
        Return raw attributes: (attrs or None, err, message) from GetFileAttributesW.

        Examples:
          get_file_attributes(r"C:\\file.txt")    -> (0x20, None, None)
          get_file_attributes(r"C:\\missing.txt") -> (None, 2, "The system cannot find the file specified.")
        """
        global kernel32
        attrs = kernel32.GetFileAttributesW(path)
        if attrs == W("INVALID_FILE_ATTRIBUTES", default=0xFFFFFFFF):
            err = kernel32.GetLastError()
            return None, err, format_last_error(err)
        return attrs, None, None

    # ---- public: read-only checks -----------------------------------------------
    def is_file_readonly(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Check FILE_ATTRIBUTE_READONLY on a file.

        Examples:
          is_file_readonly(r"C:\\readonly.txt") -> (True, None, None)
          is_file_readonly(r"C:\\writable.txt") -> (False, None, None)
          is_file_readonly(r"C:\\missing.txt")  -> (None, 2, "The system cannot find the file specified.")
        """
        global kernel32
        attrs, err, msg = get_file_attributes(path)
        if attrs is None:
            return None, err, msg
        return bool(attrs & win32con.FILE_ATTRIBUTE_READONLY), None, None

    def is_folder_readonly(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Check FILE_ATTRIBUTE_READONLY on a directory (mostly cosmetic on Windows).

        Examples:
          is_folder_readonly(r"C:\\dir")     -> (False, None, None)
          is_folder_readonly(r"C:\\missing") -> (None, 3, "The system cannot find the path specified.")
        """
        global kernel32
        attrs, err, msg = get_file_attributes(path)
        if attrs is None:
            return None, err, msg
        return bool(attrs & win32con.FILE_ATTRIBUTE_READONLY), None, None

    # ---- public: sparse bit -----------------------------------------------------
    def is_sparse_file(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Check FILE_ATTRIBUTE_SPARSE_FILE on a file.

        Examples:
          is_sparse_file(r"C:\\sparse.bin")  -> (True, None, None)
          is_sparse_file(r"C:\\normal.bin")  -> (False, None, None)
          is_sparse_file(r"C:\\missing.bin") -> (None, 2, "The system cannot find the file specified.")
        """
        global kernel32
        attrs, err, msg = get_file_attributes(path)
        if attrs is None:
            return None, err, msg
        return bool(attrs & win32con.FILE_ATTRIBUTE_SPARSE_FILE), None, None

    # ---- public: folder emptiness -----------------------------------------------
    def is_folder_empty(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Non-destructive quick test for emptiness.

        Examples:
          is_folder_empty(r"C:\\empty")     -> (True, None, None)
          is_folder_empty(r"C:\\nonempty")  -> (False, None, None)
          is_folder_empty(r"C:\\missing")   -> (None, 3, "The system cannot find the path specified.")
        """
        global kernel32
        try:
            with os.scandir(path) as it:
                for _ in it:
                    return False, None, None
            return True, None, None
        except FileNotFoundError:
            return None, W("ERROR_FILE_NOT_FOUND", default=2), "The system cannot find the file specified."
        except PermissionError:
            err = W("ERROR_ACCESS_DENIED", default=5)
            return None, err, format_last_error(err)
        except Exception:
            err = kernel32.GetLastError()
            return None, err, format_last_error(err) if err else ("Unexpected error")

    # ---- public: attribute-only open --------------------------------------------
    def open_for_attribute_write(path: str) -> wintypes.HANDLE:
        """
        Open a handle for attributes-only writes (timestamps, basic attrs).
        Non-destructive: uses OPEN_EXISTING; will NOT create/overwrite/delete.

        Examples:
          h = open_for_attribute_write(r"C:\\file.txt"); h != INVALID_HANDLE_VALUE -> usable
          h = open_for_attribute_write(r"C:\\missing.txt") -> INVALID_HANDLE_VALUE (check GetLastError)
        """
        global kernel32
        flags = win32con.FILE_ATTRIBUTE_NORMAL
        try:
            if os.path.isdir(path):
                flags |= win32con.FILE_FLAG_BACKUP_SEMANTICS
        except Exception:
            pass
        return kernel32.CreateFileW(
            path,
            win32con.FILE_WRITE_ATTRIBUTES,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | W("FILE_SHARE_DELETE", default=0x00000004),
            None,
            win32con.OPEN_EXISTING,
            flags,
            None
        )

    # ---- public: writability probes ---------------------------------------------
    def is_file_writable(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Non-destructive probe: can we write data to this file right now?

        Examples:
          is_file_writable(r"C:\\file.txt")     -> (True, None, None)
          is_file_writable(r"C:\\readonly.txt") -> (False, None, "read-only attribute set")
          is_file_writable(r"C:\\missing.txt")  -> (None or False, <err>, "<message>")
        """
        global kernel32
        ro, err, msg = is_file_readonly(path)
        if ro is True:
            return False, None, "read-only attribute set"
        desired = W("FILE_WRITE_DATA", default=0x0002)
        h = kernel32.CreateFileW(
            path, desired,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | W("FILE_SHARE_DELETE", default=0x00000004),
            None, win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL, None
        )
        if h == W("INVALID_HANDLE_VALUE", default=-1):
            e = kernel32.GetLastError()
            return False, e, format_last_error(e)
        kernel32.CloseHandle(h)
        return True, None, None

    def is_folder_writable(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Non-destructive probe: can we create a file in this directory?

        Examples:
          is_folder_writable(r"C:\\dir")     -> (True, None, None)
          is_folder_writable(r"C:\\missing") -> (None, 3, "The system cannot find the path specified.")
        """
        global kernel32
        desired = W("FILE_ADD_FILE", default=0x0002)
        flags = win32con.FILE_FLAG_BACKUP_SEMANTICS
        h = kernel32.CreateFileW(
            path, desired,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | W("FILE_SHARE_DELETE", default=0x00000004),
            None, win32con.OPEN_EXISTING,
            flags, None
        )
        if h == W("INVALID_HANDLE_VALUE", default=-1):
            e = kernel32.GetLastError()
            return False, e, format_last_error(e)
        kernel32.CloseHandle(h)
        return True, None, None

    # ---- public: deletable probes -----------------------------------------------
    def is_file_deletable(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Non-destructive probe: do we have DELETE rights for this file?
        (Does NOT delete; we only try to open with DELETE access.)

        Examples:
          is_file_deletable(r"C:\\file.txt")     -> (True, None, None)
          is_file_deletable(r"C:\\readonly.txt") -> (False, None, "read-only attribute set")
          is_file_deletable(r"C:\\missing.txt")  -> (None or False, <err>, "<message>")
        """
        global kernel32
        ro, err, msg = is_file_readonly(path)
        if ro is True:
            return False, None, "read-only attribute set"
        h = kernel32.CreateFileW(
            path, win32con.DELETE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | W("FILE_SHARE_DELETE", default=0x00000004),
            None, win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL, None
        )
        if h == W("INVALID_HANDLE_VALUE", default=-1):
            e = kernel32.GetLastError()
            return False, e, format_last_error(e)
        kernel32.CloseHandle(h)
        return True, None, None

    def is_folder_deletable(path: str, *, consider_emptiness: bool = False) -> tuple[bool | None, int | None, str | None]:
        """
        Non-destructive probe: do we have DELETE rights for this directory?
        (Does NOT delete; ignores emptiness unless consider_emptiness=True.)

        Examples:
          is_folder_deletable(r"C:\\dir")                          -> (True, None, None)
          is_folder_deletable(r"C:\\dir", consider_emptiness=True) -> (False, None, "directory not empty")
          is_folder_deletable(r"C:\\missing")                      -> (None, 3, "The system cannot find the path specified.")
        """
        global kernel32
        if consider_emptiness:
            empty, e, m = is_folder_empty(path)
            if empty is False:
                return False, None, "directory not empty"
            if empty is None:
                return None, e, m
        flags = win32con.FILE_FLAG_BACKUP_SEMANTICS
        h = kernel32.CreateFileW(
            path, win32con.DELETE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | W("FILE_SHARE_DELETE", default=0x00000004),
            None, win32con.OPEN_EXISTING,
            flags, None
        )
        if h == W("INVALID_HANDLE_VALUE", default=-1):
            e = kernel32.GetLastError()
            return False, e, format_last_error(e)
        kernel32.CloseHandle(h)
        return True, None, None

    # ---- internal: compression IOCTL helpers -----------------------------------
    def _fsctl_get_compression(path: str, dir_handle: bool) -> tuple[int | None, int | None, str | None]:
        """
        Return compression format (USHORT) or (None, err, msg).

        Examples:
          _fsctl_get_compression(r"C:\\file.txt", False) -> (0|1|..., None, None)
          _fsctl_get_compression(r"C:\\dir", True)       -> (0|1|..., None, None)
        """
        global kernel32
        _ensure_deviceiocontrol_signature()

        flags = win32con.FILE_ATTRIBUTE_NORMAL | (win32con.FILE_FLAG_BACKUP_SEMANTICS if dir_handle else 0)
        access = win32con.GENERIC_READ
        h = kernel32.CreateFileW(
            path, access,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None, win32con.OPEN_EXISTING,
            flags, None
        )
        if h == W("INVALID_HANDLE_VALUE", default=-1):
            e = kernel32.GetLastError()
            return None, e, format_last_error(e)
        try:
            out = ctypes.c_ushort(0)
            br = wintypes.DWORD(0)
            ok = kernel32.DeviceIoControl(
                h, winioctlcon.FSCTL_GET_COMPRESSION,
                None, 0,
                ctypes.byref(out), ctypes.sizeof(out),
                ctypes.byref(br), None
            )
            if not ok:
                e = kernel32.GetLastError()
                return None, e, format_last_error(e)
            return int(out.value), None, None
        finally:
            kernel32.CloseHandle(h)

    def _fsctl_set_compression(path: str, enable: bool, dir_handle: bool) -> tuple[bool, int | None, str | None]:
        """
        Set NTFS compression (file or dir default).

        Examples:
          _fsctl_set_compression(r"C:\\file.txt", True, False) -> (True, None, None)
        """
        global kernel32
        _ensure_deviceiocontrol_signature()

        flags = win32con.FILE_ATTRIBUTE_NORMAL | (win32con.FILE_FLAG_BACKUP_SEMANTICS if dir_handle else 0)
        access = win32con.GENERIC_READ | win32con.GENERIC_WRITE
        h = kernel32.CreateFileW(
            path, access,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None, win32con.OPEN_EXISTING,
            flags, None
        )
        if h == W("INVALID_HANDLE_VALUE", default=-1):
            e = kernel32.GetLastError()
            return False, e, format_last_error(e)
        try:
            fmt_val = W("COMPRESSION_FORMAT_DEFAULT", default=1) if enable else W("COMPRESSION_FORMAT_NONE", default=0)
            fmt = ctypes.c_ushort(fmt_val)
            br = wintypes.DWORD(0)
            ok = kernel32.DeviceIoControl(
                h, winioctlcon.FSCTL_SET_COMPRESSION,
                ctypes.byref(fmt), ctypes.sizeof(fmt),
                None, 0,
                ctypes.byref(br), None
            )
            if not ok:
                e = kernel32.GetLastError()
                return False, e, format_last_error(e)
            return True, None, None
        finally:
            kernel32.CloseHandle(h)

    # ---- public: compression checks/sets ---------------------------------------
    def is_file_compressed(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Prefer FSCTL_GET_COMPRESSION; fall back to attribute bit if unsupported.

        Examples:
          is_file_compressed(r"C:\\file.txt")    -> (True/False, None, None)
          is_file_compressed(r"C:\\missing.txt") -> (None, <err>, "<message>")
        """
        global kernel32
        fmt, err, msg = _fsctl_get_compression(path, dir_handle=False)
        if fmt is not None:
            return (fmt != W("COMPRESSION_FORMAT_NONE", default=0)), None, None
        attrs, aerr, amsg = get_file_attributes(path)
        if attrs is None:
            return None, err or aerr, msg or amsg
        return bool(attrs & win32con.FILE_ATTRIBUTE_COMPRESSED), None, None

    def is_folder_compression_default_on(path: str) -> tuple[bool | None, int | None, str | None]:
        """
        Directory default compression (affects new children).

        Examples:
          is_folder_compression_default_on(r"C:\\dir") -> (True/False, None, None)
        """
        global kernel32
        fmt, err, msg = _fsctl_get_compression(path, dir_handle=True)
        if fmt is not None:
            return (fmt != W("COMPRESSION_FORMAT_NONE", default=0)), None, None
        attrs, aerr, amsg = get_file_attributes(path)
        if attrs is None:
            return None, err or aerr, msg or amsg
        return bool(attrs & win32con.FILE_ATTRIBUTE_COMPRESSED), None, None

    def set_file_compression(path: str, enable: bool) -> tuple[bool, int | None, str | None]:
        """
        Enable/disable NTFS compression on a file.

        Examples:
          set_file_compression(r"C:\\file.txt", True)  -> (True, None, None)
          set_file_compression(r"C:\\file.txt", False) -> (True, None, None)
        """
        global kernel32
        return _fsctl_set_compression(path, enable, dir_handle=False)

    def set_folder_compression_default(path: str, enable: bool) -> tuple[bool, int | None, str | None]:
        """
        Enable/disable directory default compression (affects new children).

        Examples:
          set_folder_compression_default(r"C:\\dir", True) -> (True, None, None)
        """
        return _fsctl_set_compression(path, enable, dir_handle=True)

    # ---- export public helpers --------------------------------------------------
    g = globals()
    for name, obj in {
        "get_file_attributes": get_file_attributes,
        "is_file_readonly": is_file_readonly,
        "is_folder_readonly": is_folder_readonly,
        "is_sparse_file": is_sparse_file,
        "is_folder_empty": is_folder_empty,
        "open_for_attribute_write": open_for_attribute_write,
        "is_file_writable": is_file_writable,
        "is_folder_writable": is_folder_writable,
        "is_file_deletable": is_file_deletable,
        "is_folder_deletable": is_folder_deletable,
        "is_file_compressed": is_file_compressed,
        "is_folder_compression_default_on": is_folder_compression_default_on,
        "set_file_compression": set_file_compression,
        "set_folder_compression_default": set_folder_compression_default,
    }.items():
        g[name] = obj
        _export_name(name)

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
        "setup_windows_api_bindings", "setup_filesystem_capability_helpers",
    }
    return sorted(
        n for n in new_names
        if not n.startswith("_") and n not in exclude
    )

# ================================================================================

# ---------- Actually build the list of imports to be exported for all to see ----------

# Run the dependency check + imports at module import time
check_and_import_core_deps()

# Setup Windows API bindings
setup_windows_api_bindings()

# Initialize helpers ONLY AFTER WinAPI setup
# (kernel32 must exist via setup_windows_api_bindings)
setup_filesystem_capability_helpers()

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