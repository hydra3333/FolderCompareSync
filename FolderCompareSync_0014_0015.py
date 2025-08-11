#!/usr/bin/env python3
"""
FolderCompareSync - A Folder Comparison & Synchronization Tool

Version  v001.0016 - fix button and status message font scaling to use global constants consistently
         v001.0015 - add configurable tree row height control for compact folder display
         v001.0014 - add configurable font scaling system for improved UI text readability

Author: hydra3333
License: AGPL-3.0
GitHub: https://github.com/hydra3333/FolderCompareSync

LIMITS:
=======
- Maximum 200,000 files/folders supported with early abort protection
- 5,000 line status log history for comprehensive operation tracking
- Performance warnings displayed to users about large folder operation implications
- Early detection and handling of operations exceeding system limits

DEBUG & LOGGING:
================
This application uses Python's built-in __debug__ flag and logging for debugging:

1. __debug__ is a built-in Python constant and is:
   - True by default (debug mode) when "-O" on the python commandline is omitted  :  python FolderCompareSync.py
   - False when running with "-O" flag (python optimized mode) on the python commandline :  python -O FolderCompareSync.py
   - i.e. using "-O" turns off debugging via __debug__
   - Controls assert statements and debug-only code
2. Running the application:
   - Debug mode (verbose):            python FolderCompareSync.py
   - python Optimized mode (quiet):   python -O FolderCompareSync.py
3. Logging output:
   - File: foldercomparesync.log (always enabled, detailed log for troubleshooting)
   - Console: Real-time debug/info messages (only in debug mode when "-O" flag is omitted)
   - Copy Operations: Per-operation log files with timestamps and performance metrics for detailed analysis
   - DRY RUN: Full simulation logging without actual file operations for safe testing
4. Turn debug loglevel on/off within section of code within any Class Method:
    # debug some specific section of code
    self.set_debug_loglevel(True)  # Turn on debug logging
    ...
    self.set_debug_loglevel(False)  # Turn off debug logging

    # If you hit an error and want more detail:
    if some_error_condition:
        self.set_debug_loglevel(True)  # Turn on debug logging
        log_and_flush(logging.DEBUG, "Now getting detailed debug info...")
        ...
        self.set_debug_loglevel(False)  # Turn off debug logging
"""

import platform
import os
import sys
import importlib
import hashlib
import time
import stat
import fnmatch
import shutil
import uuid
import ctypes
import ctypes.wintypes
from ctypes import wintypes, Structure, c_char_p, c_int, c_void_p, POINTER, byref
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from enum import Enum
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import threading
import logging
import gc # for python garbage collection of unused structures etc

# ============================================================================
# GLOBAL CONFIGURATION CONSTANTS
# ============================================================================
# These constants control various aspects of the application behavior and UI.
# Modify these values to customize the application without hunting through code.

# Performance and file handling limits
MAX_FILES_FOLDERS = 100000         # Maximum number of files/folders supported for performance
STATUS_LOG_MAX_HISTORY = 5000      # Maximum lines to keep in status history (expanded from 500)

# Window sizing and layout constants
WINDOW_WIDTH_PERCENT = 0.98        # 98% of screen width
WINDOW_HEIGHT_PERCENT = 0.93       # 93% of screen height  
MIN_WINDOW_WIDTH = 800             # Minimum window width in pixels
MIN_WINDOW_HEIGHT = 600            # Minimum window height in pixels
WINDOW_TOP_OFFSET = 0              # Pixels from top of screen

# Progress dialog appearance and behavior
PROGRESS_DIALOG_WIDTH = 400        # Progress dialog width in pixels
PROGRESS_DIALOG_HEIGHT = 150       # Progress dialog height in pixels
PROGRESS_ANIMATION_SPEED = 10      # Animation speed for indeterminate progress
PROGRESS_UPDATE_FREQUENCY = 100    # Update progress every N items processed
PROGRESS_PERCENTAGE_FREQUENCY = 1  # Update percentage display every N%

# File processing limits and thresholds
SHA512_MAX_FILE_SIZE = (1000 * 1024 * 1024) * 25  # 25 GB filesize limit for hash computation
SHA512_STATUS_MESSAGE_THRESHOLD = 100 * 1024 * 1024  # 100 MB - Show status for files larger than this
COPY_PREVIEW_MAX_ITEMS = 10                       # Max items to show in copy preview dialog
SCAN_PROGRESS_UPDATE_INTERVAL = 50                # Update scanning progress every N items
COMPARISON_PROGRESS_BATCH = 100                   # Process comparison updates every N items

# Copy System Configuration
COPY_STRATEGY_THRESHOLD = (1024 * 1024) * 200    # 200MB threshold for copy strategy selection into STAGED (rename-based backup)
COPY_VERIFICATION_ENABLED = True                 # Enable post-copy simple verification
COPY_RETRY_COUNT = 3                             # Number of retries for failed operations
COPY_RETRY_DELAY = 1.0                           # Delay between retries in seconds
COPY_CHUNK_SIZE = 64 * 1024                      # 64KB chunks for large file copying
COPY_NETWORK_TIMEOUT = 30.0                      # Network operation timeout in seconds

# Performance and debug settings
DEBUG_LOG_FREQUENCY = 100           # Log debug info every N items (avoid spam in large operations)
TREE_UPDATE_BATCH_SIZE = 200000     # Process tree updates in batches of N items (used in sorting)
MEMORY_EFFICIENT_THRESHOLD = 10000  # Switch to memory-efficient mode above N items

# Tree column configuration (default widths) - for new columns
TREE_STRUCTURE_WIDTH = 350         # Default structure column width
TREE_STRUCTURE_MIN_WIDTH = 120     # Minimum structure column width
TREE_SIZE_WIDTH = 50               # Size column width
TREE_SIZE_MIN_WIDTH = 30           # Minimum size column width
TREE_DATE_CREATED_WIDTH = 140      # Date created column width # v001.0010 changed - increased width for full precision timestamps
TREE_DATE_CREATED_MIN_WIDTH = 120  # Minimum date created column width # v001.0010 changed - increased minimum width for full precision timestamps
TREE_DATE_MODIFIED_WIDTH = 140     # Date modified column width # v001.0010 changed - increased width for full precision timestamps
TREE_DATE_MODIFIED_MIN_WIDTH = 120 # Minimum date modified column width # v001.0010 changed - increased minimum width for full precision timestamps
TREE_SHA512_WIDTH = 100            # SHA512 column width (first 16 chars)
TREE_SHA512_MIN_WIDTH = 80         # Minimum SHA512 column width
TREE_STATUS_WIDTH = 100            # Status column width
TREE_STATUS_MIN_WIDTH = 80         # Minimum status column width

# Tree row height configuration # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_VERY_COMPACT = 18  # Very tight spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_COMPACT = 20       # Tight spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_NORMAL = 22        # Comfortable spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_DEFAULT = 24       # Tkinter default spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_LOOSE = 26         # Relaxed spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_VERY_LOOSE = 28    # Very relaxed spacing # v001.0015 added [tree row height control for compact display]

# Active tree row height setting - change this to switch spacing globally # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT = TREE_ROW_HEIGHT_NORMAL  # Start with 22px for good balance # v001.0015 added [tree row height control for compact display]

# Font scaling configuration # v001.0014 added [font scaling system for UI text size control]
UI_FONT_SCALE = 1                  # v001.0014 added [font scaling system for UI text size control]
                                   # Global font multiplier (can be Real number)- KEEP AT 1 for direct as-is font sizes
                                   # (1 = no scaling, 1.2 = 20% larger, etc.)
                                   # Font scaling infrastructure preserved for future use if needed

# Specific font sizes # v001.0014 added [font scaling system for UI text size control]
BUTTON_FONT_SIZE = 11               # Button text size (default ~9, so +2) # v001.0014 added [font scaling system for UI text size control]
LABEL_FONT_SIZE = 11                # Label text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
ENTRY_FONT_SIZE = 11                # Entry field text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
CHECKBOX_FONT_SIZE = 11             # Checkbox text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
DIALOG_FONT_SIZE = 11               # Dialog text size # v001.0014 added [font scaling system for UI text size control]
STATUS_MESSAGE_FONT_SIZE = 12       # Status message text size # v001.0014 added [font scaling system for UI text size control]
INSTRUCTION_FONT_SIZE = 11          # formerly INSTRUCTION_TEXT_SIZE Font size for instructional text
# pre-calculate scaled font sizes
SCALED_BUTTON_FONT_SIZE = ( BUTTON_FONT_SIZE * UI_FONT_SCALE )                 # Button text size (default ~9, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_LABEL_FONT_SIZE = ( LABEL_FONT_SIZE * UI_FONT_SCALE )                   # Label text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_ENTRY_FONT_SIZE = ( ENTRY_FONT_SIZE * UI_FONT_SCALE )                   # Entry field text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_CHECKBOX_FONT_SIZE = ( CHECKBOX_FONT_SIZE * UI_FONT_SCALE )             # Checkbox text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_DIALOG_FONT_SIZE = ( DIALOG_FONT_SIZE * UI_FONT_SCALE )                 # Dialog text size # v001.0014 added [font scaling system for UI text size control]
SCALED_STATUS_MESSAGE_FONT_SIZE = ( STATUS_MESSAGE_FONT_SIZE * UI_FONT_SCALE ) # Status message text size # v001.0014 added [font scaling system for UI text size control]
SCALED_INSTRUCTION_FONT_SIZE = ( INSTRUCTION_FONT_SIZE * UI_FONT_SCALE )       # Font size for instructional text

# Status log configuration
STATUS_LOG_VISIBLE_LINES = 6       # Visible lines in status log window, was 5
STATUS_LOG_FONT = ("Courier", SCALED_STATUS_MESSAGE_FONT_SIZE)   # v001.0016
STATUS_LOG_BG_COLOR = "#f8f8f8"    # Light background color
STATUS_LOG_FG_COLOR = "#333333"    # Dark text color

# Display colors and styling
MISSING_ITEM_COLOR = "gray"           # Color for missing items in tree
INSTRUCTION_TEXT_COLOR = "royalblue"  # Color for instructional text
FILTER_HIGHLIGHT_COLOR = "#ffffcc"    # Background color for filtered items

# Filtering and sorting configuration
MAX_FILTER_RESULTS = 200000       # Maximum items to show when filtering (performance)
                                                                         
# ============================================================================
# DELETE ORPHANS CONFIGURATION CONSTANTS
# ============================================================================
# Delete Orphans Dialog Configuration
DELETE_ORPHANS_DIALOG_WIDTH_PERCENT = 0.60    # 60% of main window width  # v001.0013 changed [reduced delete orphans dialog width from 85% to 60%]
DELETE_ORPHANS_DIALOG_HEIGHT_PERCENT = 1.0    # Full height               # v001.0012 added [delete orphans dialog sizing]
DELETE_ORPHANS_STATUS_LINES = 10               # Visible lines in status log  # v001.0012 added [delete orphans status area]
DELETE_ORPHANS_STATUS_MAX_HISTORY = 5000       # Maximum lines to keep     # v001.0012 added [delete orphans status area]

# Delete Orphans Memory Management Thresholds
DELETE_LARGE_FILE_LIST_THRESHOLD = 1000        # Clear if >1000 files      # v001.0012 added [delete orphans memory management]
DELETE_LARGE_TREE_DATA_THRESHOLD = 5000        # Clear if >5000 tree items # v001.0012 added [delete orphans memory management]
DELETE_LARGE_SELECTION_THRESHOLD = 500         # Clear if >500 selected items # v001.0012 added [delete orphans memory management]

# Delete Orphans Progress and UI Configuration
DELETE_ORPHANS_PROGRESS_UPDATE_FREQUENCY = 50  # Update progress every N files # v001.0012 added [delete orphans progress]
DELETE_ORPHANS_TREE_STRUCTURE_WIDTH = 400      # Tree structure column width   # v001.0012 added [delete orphans tree display]
DELETE_ORPHANS_TREE_SIZE_WIDTH = 80            # Size column width             # v001.0012 added [delete orphans tree display]
DELETE_ORPHANS_TREE_STATUS_WIDTH = 120         # Status column width           # v001.0012 added [delete orphans tree display]

# ============================
# WINDOWS SHELL API STRUCTURES
# ============================
# Windows Shell API constants

FO_DELETE = 0x0003                   # Delete operation
FOF_ALLOWUNDO = 0x0040               # Allow undo (moves to Recycle Bin)
FOF_NOCONFIRMATION = 0x0010          # No confirmation dialogs
FOF_SILENT = 0x0004                  # No progress dialog
FOF_NOERRORUI = 0x0400               # No error UI dialogs

class SHFILEOPSTRUCT(Structure):
    """
    Structure for SHFileOperation - Windows Shell file operations.
    Used for moving files to Recycle Bin with proper user feedback.
    """
    _fields_ = [
        ("hwnd", wintypes.HWND),          # Handle to parent window
        ("wFunc", wintypes.UINT),         # Operation type (delete, move, etc.)
        ("pFrom", c_char_p),              # Source file paths (null-terminated)
        ("pTo", c_char_p),                # Destination paths (null for delete)
        ("fFlags", wintypes.WORD),        # Operation flags
        ("fAnyOperationsAborted", wintypes.BOOL),  # Set if user cancelled
        ("hNameMappings", c_void_p),      # Handle to name mappings
        ("lpszProgressTitle", c_char_p),  # Progress dialog title
    ]


# ============================================================================
# LOGGING SETUP (MUST BE BEFORE FileTimestampManager)
# 2025.08.07 v0.3 replaced by updated version
# ============================================================================
# Setup logging loglevel based on __debug__ flag
# using "-O" on the python commandline turns __debug__ off:  python -O FolderCompareSync.py
if __debug__:
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
else:
    log_level = logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'

# Create handlers list with UTF-8 encoding support:
# Add a handler for file logging, since that is always enabled
handlers = [
    logging.FileHandler(
        os.path.join(os.path.dirname(__file__), 'foldercomparesync.log'), 
        mode='w', 
        encoding='utf-8'  # Ensure UTF-8 encoding for file output
    )
]
# When in debug mode, when __debug__ is True, add a handler for console logging, only 
#    ... i.e. when -O is missing from the python commandline
if __debug__:
    # Create console handler with UTF-8 encoding to handle Unicode filenames
    console_handler = logging.StreamHandler()
    console_handler.setStream(sys.stdout)  # Explicitly use stdout
    # Set UTF-8 encoding if possible (for Windows Unicode support)
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass  # If reconfigure fails, continue with default encoding
    handlers.append(console_handler)

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=handlers
)
logger = logging.getLogger(__name__)

def log_and_flush(level, msg, *args, **kwargs):
    # If you want to guarantee that a log line is on disk (or shown in the console) before the next line runs,
    # even if the program crashes, you can explicitly flush the handler(s) right after the log call.
    # Example Usage:
    #     log_and_flush(logging.INFO, "About to process file: %s", file_path)
    #
    logger.log(level, msg, *args, **kwargs)
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass  # Ignore handlers that don't support flush

# ************** At program startup **************
def check_dependencies(deps):
    missing = []
    for pkg_name, import_name in deps:
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pkg_name)
    if missing:
        missing_msg = (
            "ERROR: Missing required Python packages: "
            + ", ".join(missing)
            + "\nPlease install them with:\n"
            + "    pip install --upgrade "
            + " ".join(missing)
            + "\n"
        )
        # Print to stderr and to the logger, then exit
        sys.stderr.write(missing_msg)
        log_and_flush(logging.CRITICAL, missing_msg)
        sys.exit(1)
# Check the timezone dependencies are installed by pip
#     pip install --upgrade python-dateutil
#     pip install --upgrade tzdata
check_dependencies([
    ("tzdata",          "zoneinfo"),
    ("python-dateutil", "dateutil.tz"),
])
# If we get here, we can safely import:
from zoneinfo import ZoneInfo
import zoneinfo
from dateutil.tz import tzwinlocal
# ************** At program startup **************

# ============================================================================
# TOP-LEVEL UTILITY FUNCTION - Place this near the top of the program
# after imports but before the main classes
# ============================================================================

def format_timestamp(timestamp: Union[datetime, float, int, None], 
                    include_timezone: bool = False, 
                    include_microseconds: bool = True) -> str:
    """
    Universal timestamp formatting utility function.
    
    Purpose:
    --------
    Handles multiple timestamp input types and formatting options for consistent
    timestamp display throughout the application.
    
    Args:
    -----
    timestamp: Can be datetime object, float/int epoch time, or None
    include_timezone: Whether to include timezone info in output
    include_microseconds: Whether to include microsecond precision
    
    Returns:
    --------
    str: Formatted timestamp string or empty string if None
    
    Examples:
    ---------
    >>> format_timestamp(datetime.now())
    "2024-12-08 14:30:22.123456"
    
    >>> format_timestamp(1701234567.123456, include_microseconds=True)
    "2023-11-29 08:02:47.123456"
    
    >>> format_timestamp(None)
    ""
    
    >>> dt_with_tz = datetime.now(timezone.utc)
    >>> format_timestamp(dt_with_tz, include_timezone=True)
    "2024-12-08 14:30:22.123456 UTC"
    """
    if timestamp is None:
        return ""
    try:
        # Convert input to datetime object
        if isinstance(timestamp, datetime):
            dt = timestamp
        elif isinstance(timestamp, (int, float)):
            # Convert epoch timestamp to datetime in local timezone
            dt = datetime.fromtimestamp(timestamp)
        else:
            # Fallback for unexpected types
            return str(timestamp)
        
        # Build format string based on options
        if include_microseconds:
            base_format = "%Y-%m-%d %H:%M:%S.%f"
        else:
            base_format = "%Y-%m-%d %H:%M:%S"
        
        # Format the datetime
        formatted = dt.strftime(base_format)
        
        # Add timezone if requested and available
        if include_timezone and dt.tzinfo is not None:
            tz_name = dt.strftime("%Z")
            if tz_name:  # Only add if timezone name is available
                formatted += f" {tz_name}"
        
        return formatted
    except (ValueError, OSError, OverflowError) as e:
        # Handle invalid timestamps gracefully
        log_and_flush(logging.DEBUG, f"Invalid timestamp formatting: {timestamp} - {e}")
        return f"Invalid timestamp: {timestamp}"

def format_size(size_bytes):
    """
    Format file size in human readable format.
    
    Purpose:
    --------
    Converts byte values to human-readable format with appropriate
    units (B, KB, MB, GB, TB) for display in the UI.
    
    Args:
    -----
    size_bytes: Size in bytes
    
    Returns:
    --------
    str: Formatted size string
    """
    if size_bytes is None:
        return ""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


# ---------- Start of Common FileTimestampManager Code ----------
"""
A class to reliably manage file date-created and date-modified timestamps on Windows systems.

Purpose:
--------
    Handles both retrieval and setting of creation and modification times
    with proper timezone awareness for accurate file metadata preservation.
    Supports dry run mode to prevent actual filesystem modifications.

Features:
---------
    - Proper Windows FILETIME structure usage for maximum compatibility
    - Automatic timezone detection and conversion
    - Support for both files and directories
    - Dry run mode for testing
    - Fallback mechanism if primary method fails
    - Comprehensive error reporting

Usage:
------
    >>> timestamp_manager = FileTimestampManager()
    >>> 
    >>> # Get timestamps from a file
    >>> creation_time, mod_time = timestamp_manager.get_file_timestamps("source.txt")
    >>> 
    >>> # Set timestamps on another file
    >>> timestamp_manager.set_file_timestamps("target.txt", creation_time, mod_time)
    >>> 
    >>> # Copy timestamps directly
    >>> timestamp_manager.copy_timestamps("source.txt", "target.txt")
    >>> 
    >>> # Dry run mode (no actual changes)
    >>> dry_run_manager = FileTimestampManager(dry_run=True)

NOTES:
------
    Hybrid approach Generated by Claude AI.
    Robust FileTimestampManager class for Windows with proper type safety and fallback mechanisms.
    This hybrid approach combines the correctness of proper FILETIME structures with
    practical fallback options for maximum compatibility.
    Key improvements:
    - Proper FILETIME structure definition for type safety
    - Correct Windows API function signatures
    - Fallback mechanism if proper method fails
    - error handling and debugging
    - Clear documentation of Windows timestamp quirks
"""

import os
import sys
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone, timedelta
import time
import re
import argparse
import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Optional, Union

# ==========================================================================================================
# WINDOWS FILETIME STRUCTURE AND API SETUP
# ==========================================================================================================
# Windows FILETIME is a 64-bit value representing 100-nanosecond intervals since January 1, 1601 UTC.
# It's stored as two 32-bit DWORDs: dwLowDateTime (low 32 bits) and dwHighDateTime (high 32 bits).
# 
# While passing a c_ulonglong pointer often works (on little-endian systems), using the proper
# FILETIME structure is more correct and ensures compatibility across different scenarios.
# ==========================================================================================================

class FILETIME(ctypes.Structure):
    """
    Windows FILETIME structure.
    Represents time as 100-nanosecond intervals since 1601-01-01 00:00:00 UTC.
    """
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),   # Low 32 bits of the 64-bit time value
        ("dwHighDateTime", wintypes.DWORD),  # High 32 bits of the 64-bit time value
    ]

def _u64_to_FILETIME(u64: int) -> FILETIME:
    """
    Convert a 64-bit integer to a FILETIME structure.
    Args:
        u64: 64-bit integer representing 100-nanosecond intervals since 1601
    Returns:
        FILETIME structure with properly split low/high DWORDs
    """
    return FILETIME(
        dwLowDateTime=(u64 & 0xFFFFFFFF),        # Mask to get lower 32 bits
        dwHighDateTime=((u64 >> 32) & 0xFFFFFFFF) # Shift and mask to get upper 32 bits
    )

def _FILETIME_to_u64(ft: FILETIME) -> int:
    """
    Convert a FILETIME structure to a 64-bit integer.
    Args:
        ft: FILETIME structure
    Returns:
        64-bit integer representing 100-nanosecond intervals since 1601
    """
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


# ==========================================================================================================
# WINDOWS API FUNCTION BINDINGS WITH PROPER SIGNATURES
# ==========================================================================================================
# Setting argtypes and restype ensures:
# 1. Proper type conversion (especially important for HANDLEs on 64-bit Python)
# 2. Correct error handling (return values won't be truncated)
# 3. Better debugging (ctypes will raise errors for incorrect argument types)
# ==========================================================================================================

kernel32 = ctypes.windll.kernel32

# CreateFileW - Opens a file/directory handle
kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR,    # lpFileName (wide string path)
    wintypes.DWORD,      # dwDesiredAccess
    wintypes.DWORD,      # dwShareMode
    wintypes.LPVOID,     # lpSecurityAttributes (usually NULL)
    wintypes.DWORD,      # dwCreationDisposition
    wintypes.DWORD,      # dwFlagsAndAttributes
    wintypes.HANDLE      # hTemplateFile (usually NULL)
]
kernel32.CreateFileW.restype = wintypes.HANDLE

# SetFileTime - Sets file timestamps
kernel32.SetFileTime.argtypes = [
    wintypes.HANDLE,                 # hFile
    ctypes.POINTER(FILETIME),        # lpCreationTime (can be NULL)
    ctypes.POINTER(FILETIME),        # lpLastAccessTime (can be NULL)
    ctypes.POINTER(FILETIME)         # lpLastWriteTime (can be NULL)
]
kernel32.SetFileTime.restype = wintypes.BOOL

# CloseHandle - Closes an open handle
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

# GetLastError - Gets the last Windows error code
kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = wintypes.DWORD

# Windows constants
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
GENERIC_WRITE = 0x40000000
FILE_WRITE_ATTRIBUTES = 0x100  # More specific than GENERIC_WRITE for just changing attributes
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000  # Required for opening directories

# ==========================================================================================================
# MAIN TIMESTAMP MANAGER CLASS
# ==========================================================================================================

class FileTimestampManager:
    """
    A robust class to manage file timestamps on Windows systems.
    """
    
    def __init__(self, dry_run=False):
        """
        Initialize the timestamp manager.
        
        Args:
            dry_run: If True, don't actually modify files (for testing)
            debug: If True, print detailed debug information
        """
        self._local_tz = self._get_local_timezone()
        self._windows_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        self._dry_run = dry_run
        log_and_flush(logging.DEBUG, f"FileTimestampManager initialized with timezone: {self.get_timezone_string()}")
        log_and_flush(logging.DEBUG, f"FileTimestampManager dry run mode: {self._dry_run}")

    def get_timezone_string(self) -> str:
        """
        Get a human-readable string representation of the detected timezone.
        
        Returns:
            String describing the timezone (e.g., "Australia/Adelaide" or "UTC+09:30")
        """
        if hasattr(self._local_tz, 'key'):
            # zoneinfo.ZoneInfo has a 'key' attribute with the IANA name
            return self._local_tz.key
        elif hasattr(self._local_tz, 'tzname'):
            # Some timezone objects have tzname method
            try:
                return self._local_tz.tzname(datetime.now())
            except:
                pass
        
        # For timezone objects created from offset, show the offset
        try:
            offset = self._local_tz.utcoffset(datetime.now())
            if offset:
                total_seconds = int(offset.total_seconds())
                hours, remainder = divmod(abs(total_seconds), 3600)
                minutes = remainder // 60
                sign = '+' if total_seconds >= 0 else '-'
                if minutes:
                    return f"UTC{sign}{hours:02d}:{minutes:02d}"
                else:
                    return f"UTC{sign}{hours:02d}:00"
        except:
            pass
        
        # Fallback
        return str(self._local_tz)

    def _get_local_timezone(self):
        """
        Get the system's local timezone with multiple fallback methods.
        
        Returns:
            timezone object representing the local timezone
        """
        # Method 0: Use dateutil.tz.tzwinlocal (Windows registry direct)
        log_and_flush(logging.DEBUG, "Attempting timezone detection using Method 0: dateutil.tz.tzwinlocal...")
        try:
            tz = tzwinlocal()
            if tz:
                # Get a human-readable description
                tz_name = tz.tzname(datetime.now())
                log_and_flush(logging.INFO, f"Timezone detected via Method 0: dateutil.tz.tzwinlocal: {tz_name}")
                return tz
        except Exception as e:
            log_and_flush(logging.DEBUG, f"tzwinlocal method failed: {e}")

        # Method 1: Try zoneinfo (Python 3.9+) with Windows timezone mapping
        log_and_flush(logging.DEBUG, "Attempting timezone detection using Method 1: zoneinfo method...")
        try:
            if hasattr(time, 'tzname') and time.tzname[0]:
                # Comprehensive Windows to IANA timezone mappings
                windows_to_iana = {
                    # Australian timezones
                    'Cen. Australia Standard Time': 'Australia/Adelaide',
                    'Cen. Australia Daylight Time': 'Australia/Adelaide',
                    'Central Standard Time (Australia)': 'Australia/Adelaide',
                    'Central Daylight Time (Australia)': 'Australia/Adelaide',
                    'AUS Central Standard Time': 'Australia/Darwin',  # No DST in NT
                    'E. Australia Standard Time': 'Australia/Brisbane',  # No DST in QLD
                    'AUS Eastern Standard Time': 'Australia/Sydney',
                    'AUS Eastern Daylight Time': 'Australia/Sydney',  # Sydney has DST
                    'W. Australia Standard Time': 'Australia/Perth',  # No DST in WA
                    'Tasmania Standard Time': 'Australia/Hobart',
                    'Tasmania Daylight Time': 'Australia/Hobart',  # Tasmania has DST
                    # US timezones
                    'Eastern Standard Time': 'America/New_York',
                    'Eastern Daylight Time': 'America/New_York',
                    'Central Standard Time': 'America/Chicago',
                    'Central Daylight Time': 'America/Chicago',
                    'Mountain Standard Time': 'America/Denver',
                    'Mountain Daylight Time': 'America/Denver',
                    'Pacific Standard Time': 'America/Los_Angeles',
                    'Pacific Daylight Time': 'America/Los_Angeles',
                    'Alaskan Standard Time': 'America/Anchorage',
                    'Alaskan Daylight Time': 'America/Anchorage',
                    'Hawaiian Standard Time': 'Pacific/Honolulu',  # Hawaii has no DST
                    # European timezones
                    'GMT Standard Time': 'Europe/London',
                    'GMT Daylight Time': 'Europe/London',
                    'British Summer Time': 'Europe/London',  # BST
                    'W. Europe Standard Time': 'Europe/Berlin',
                    'W. Europe Daylight Time': 'Europe/Berlin',
                    'Central Europe Standard Time': 'Europe/Paris',
                    'Central Europe Daylight Time': 'Europe/Paris',
                    'Central European Summer Time': 'Europe/Paris',  # CEST
                    'E. Europe Standard Time': 'Europe/Athens',
                    'E. Europe Daylight Time': 'Europe/Athens',
                    # Asian timezones (most don't observe DST)
                    'China Standard Time': 'Asia/Shanghai',
                    'Tokyo Standard Time': 'Asia/Tokyo',
                    'India Standard Time': 'Asia/Kolkata',
                    'Singapore Standard Time': 'Asia/Singapore',
                }
                # Try to map Windows timezone name to IANA
                win_tz_name = time.tzname[0]
                log_and_flush(logging.DEBUG, f"Windows timezone name detected: {win_tz_name}")
                
                if win_tz_name in windows_to_iana:
                    iana_name = windows_to_iana[win_tz_name]
                    tz = zoneinfo.ZoneInfo(iana_name)
                    log_and_flush(logging.INFO, f"Timezone detected via Method 1a: zoneinfo mapping: {iana_name} (from Windows: {win_tz_name})")
                    return tz
                    
                # Try the name directly (might work on some systems)
                try:
                    tz = zoneinfo.ZoneInfo(win_tz_name)
                    log_and_flush(logging.INFO, f"Timezone detected via Method 1b: zoneinfo direct: {win_tz_name}")
                    return tz
                except:
                    log_and_flush(logging.DEBUG, f"Could not use Windows timezone name directly: {win_tz_name}")
        except zoneinfo.ZoneInfoNotFoundError as e:
            log_and_flush(logging.WARNING, f"IANA lookup failed (no tzdata?): {e}")
        except ImportError as e:
            log_and_flush(logging.DEBUG, "zoneinfo module not available, {e},skipping Method 1")
        except (AttributeError, Exception) as e:
            log_and_flush(logging.DEBUG, f"Zoneinfo method failed: {e}")
        
        # Method 2: Use time module offset to create timezone
        log_and_flush(logging.DEBUG, "Attempting timezone detection using Method 2: time module offset method...")
        try:
            # We already have time imported at module level – do not do an inner import here!
            # Get the actual current offset by comparing local and UTC time
            local_time = time.localtime()
            utc_time   = time.gmtime()
            # Calculate integer offset in seconds
            local_timestamp = int(time.mktime(local_time))
            utc_timestamp   = int(time.mktime(utc_time)) + (local_time.tm_isdst * 3600)
            offset_seconds  = local_timestamp - utc_timestamp
            # Create timezone object with the calculated offset
            tz = timezone(timedelta(seconds=offset_seconds))
            # Log the offset details with integer formatting
            abs_off = abs(offset_seconds)
            hours = abs_off // 3600
            minutes = (abs_off % 3600) // 60
            sign = '+' if offset_seconds >= 0 else '-'
            offset_str = (
                f"UTC{sign}{hours:02d}:{minutes:02d}" if minutes else f"UTC{sign}{hours:02d}:00"
            )
            log_and_flush(logging.INFO, f"Timezone detected via Method 2: time module offset: {offset_str}")
            return tz
        except Exception as e:
            log_and_flush(logging.DEBUG, f"Time module offset method failed: {e}")
        
        # Method 3: Final fallback to UTC
        log_and_flush(logging.WARNING, "Could not determine local timezone, falling back to Method 3: UTC")
        return timezone.utc
    
    def get_file_timestamps(self, file_path: Union[str, Path]) -> Tuple[datetime, datetime]:
        """
        Get creation and modification timestamps from a file or directory.
        
        Args:
            file_path: Path to the file or directory
            
        Returns:
            Tuple of (creation_time, modification_time) as timezone-aware datetime objects
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            OSError: If there's an error accessing the file
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Get timestamps as seconds since Unix epoch (1970-01-01)
            creation_timestamp = os.path.getctime(file_path)
            modification_timestamp = os.path.getmtime(file_path)
            
            # Convert to timezone-aware datetime objects in local timezone
            creation_time = datetime.fromtimestamp(creation_timestamp, tz=self._local_tz)
            modification_time = datetime.fromtimestamp(modification_timestamp, tz=self._local_tz)
            
            log_and_flush(logging.DEBUG, f"Retrieved timestamps for {file_path}:")
            log_and_flush(logging.DEBUG, f"  Creation: {creation_time}")
            log_and_flush(logging.DEBUG, f"  Modified: {modification_time}")
            
            return creation_time, modification_time
        except OSError as e:
            raise OSError(f"Error accessing file timestamps for {file_path}: {e}")
    
    def set_file_timestamps(self, file_path: Union[str, Path], 
                          creation_time: Optional[datetime] = None,
                          modification_time: Optional[datetime] = None) -> bool:
        """
        Set creation and/or modification timestamps on a file or directory.
        
        Uses the proper FILETIME structure method first, with fallback to the
        simpler c_ulonglong method if needed.
        
        Args:
            file_path: Path to the file or directory
            creation_time: New creation time (optional)
            modification_time: New modification time (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If neither timestamp is provided
        """
        if self._dry_run:
            log_and_flush(logging.INFO, f"[DRY RUN] Would set timestamps for {file_path}")
            return True
            
        if creation_time is None and modification_time is None:
            raise ValueError("At least one timestamp must be provided")
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Convert datetime objects to Windows FILETIME format (as 64-bit integers)
            creation_filetime = None
            modification_filetime = None
            
            if creation_time is not None:
                creation_filetime = self._datetime_to_filetime(creation_time)
                dt_display = self._filetime_to_datetime(creation_filetime)
                log_and_flush(logging.DEBUG, f"Creation FILETIME: {creation_filetime}")
                log_and_flush(logging.DEBUG, f"        = {dt_display.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            if modification_time is not None:
                modification_filetime = self._datetime_to_filetime(modification_time)
                dt_display = self._filetime_to_datetime(modification_filetime)
                log_and_flush(logging.DEBUG, f"Modification FILETIME: {modification_filetime}")
                log_and_flush(logging.DEBUG, f"        = {dt_display.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Try the proper FILETIME structure method first
            success = self._set_file_times_windows_proper(
                str(file_path), creation_filetime, modification_filetime
            )
            
            # If that fails, try the fallback method
            if not success:
                log_and_flush(logging.DEBUG, "Primary method failed, trying fallback...")
                success = self._set_file_times_windows_fallback(
                    str(file_path), creation_filetime, modification_filetime
                )
            if success:
                log_and_flush(logging.DEBUG, f"Successfully set timestamps for {file_path}")
            else:
                log_and_flush(logging.ERROR, f"Failed to set timestamps for {file_path}")
            return success
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error setting timestamps for {file_path}: {e}")
            return False
    
    def _datetime_to_filetime(self, dt: datetime) -> int:
        """
        Convert a datetime object to Windows FILETIME format.
        
        FILETIME represents the number of 100-nanosecond intervals since
        January 1, 1601 00:00:00 UTC (Windows epoch).
        
        Args:
            dt: Datetime object (timezone-aware or naive)
            
        Returns:
            Windows FILETIME as integer (100-nanosecond intervals since 1601-01-01)
        """
        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            # Assume naive datetime is in local timezone
            dt = dt.replace(tzinfo=self._local_tz)
            log_and_flush(logging.DEBUG, f"Converting naive datetime to local timezone: {dt}")
        
        # Convert to UTC for consistent FILETIME calculation
        dt_utc = dt.astimezone(timezone.utc)
        
        # Calculate time difference from Windows epoch (1601-01-01)
        time_diff = dt_utc - self._windows_epoch
        
        # Convert to 100-nanosecond intervals
        # total_seconds() gives us seconds as a float
        # Multiply by 10,000,000 to get 100-nanosecond intervals
        filetime = int(time_diff.total_seconds() * 10_000_000)
        
        return filetime

    def _filetime_to_datetime(self, filetime: int) -> datetime:
        """Convert FILETIME integer back to datetime for display."""
        seconds_since_1601 = filetime / 10_000_000
        dt_utc = self._windows_epoch + timedelta(seconds=seconds_since_1601)
        return dt_utc.astimezone(self._local_tz)
    
    def _set_file_times_windows_proper(self, file_path: str, 
                                      creation_time: Optional[int] = None,
                                      modification_time: Optional[int] = None) -> bool:
        """
        Primary method: Use Windows API with proper FILETIME structures.
        
        This is the most correct way to set file times on Windows.
        
        Args:
            file_path: Path to the file or directory
            creation_time: Creation time in FILETIME format (optional)
            modification_time: Modification time in FILETIME format (optional)
            
        Returns:
            True if successful, False otherwise
        """
        handle = None
        try:
            # Determine if path is a directory
            is_directory = os.path.isdir(file_path)
            
            # Set appropriate flags
            flags = FILE_ATTRIBUTE_NORMAL
            if is_directory:
                # Must use FILE_FLAG_BACKUP_SEMANTICS to open directories
                flags = FILE_FLAG_BACKUP_SEMANTICS
            
            # Open file/directory handle
            # Using FILE_WRITE_ATTRIBUTES is more specific than GENERIC_WRITE
            handle = kernel32.CreateFileW(
                file_path,
                FILE_WRITE_ATTRIBUTES,  # Only need attribute write access
                FILE_SHARE_READ | FILE_SHARE_WRITE,  # Allow other processes to read/write
                None,  # Default security
                OPEN_EXISTING,  # File must exist
                flags,
                None  # No template file
            )
            
            if handle == INVALID_HANDLE_VALUE:
                error_code = kernel32.GetLastError()
                log_and_flush(logging.DEBUG, f"CreateFileW failed with error code: {error_code}")
                return False
            
            # Prepare FILETIME structures
            creation_ft_ptr = None
            modification_ft_ptr = None
            
            if creation_time is not None:
                creation_ft = _u64_to_FILETIME(creation_time)
                creation_ft_ptr = ctypes.pointer(creation_ft)
            
            if modification_time is not None:
                modification_ft = _u64_to_FILETIME(modification_time)
                modification_ft_ptr = ctypes.pointer(modification_ft)
            
            # Set file times
            # NULL for lpLastAccessTime means don't change access time
            result = kernel32.SetFileTime(
                handle,
                creation_ft_ptr,      # Creation time
                None,                 # Last access time (unchanged)
                modification_ft_ptr   # Modification time
            )
            
            if not result:
                error_code = kernel32.GetLastError()
                log_and_flush(logging.DEBUG, f"SetFileTime failed with error code: {error_code}")
            
            return bool(result)
            
        except Exception as e:
            log_and_flush(logging.DEBUG, f"Exception in proper method: {e}")
            return False
        finally:
            # Always close the handle if it was opened
            if handle and handle != INVALID_HANDLE_VALUE:
                kernel32.CloseHandle(handle)
    
    def _set_file_times_windows_fallback(self, file_path: str, 
                                        creation_time: Optional[int] = None,
                                        modification_time: Optional[int] = None) -> bool:
        """
        Fallback method: Use Windows API with c_ulonglong (simpler but less correct).
        
        This method works on most Windows systems due to little-endian memory layout,
        but is technically not the correct way to pass FILETIME structures.
        
        Args:
            file_path: Path to the file or directory
            creation_time: Creation time in FILETIME format (optional)
            modification_time: Modification time in FILETIME format (optional)
            
        Returns:
            True if successful, False otherwise
        """
        handle = None
        try:
            # Determine if path is a directory
            is_directory = os.path.isdir(file_path)
            
            # Set appropriate flags
            flags = FILE_ATTRIBUTE_NORMAL
            if is_directory:
                flags = FILE_FLAG_BACKUP_SEMANTICS
            
            # Open file/directory handle (using simpler approach without type hints)
            handle = ctypes.windll.kernel32.CreateFileW(
                file_path,
                wintypes.DWORD(GENERIC_WRITE),
                wintypes.DWORD(FILE_SHARE_READ | FILE_SHARE_WRITE),
                None,
                wintypes.DWORD(OPEN_EXISTING),
                wintypes.DWORD(flags),
                None
            )
            
            if handle == -1:  # Simple comparison for INVALID_HANDLE_VALUE
                return False
            
            # Prepare FILETIME as c_ulonglong (fallback method)
            creation_ft = None
            modification_ft = None
            
            if creation_time is not None:
                creation_ft = ctypes.byref(ctypes.c_ulonglong(creation_time))
            
            if modification_time is not None:
                modification_ft = ctypes.byref(ctypes.c_ulonglong(modification_time))
            
            # Set file times
            result = ctypes.windll.kernel32.SetFileTime(
                handle,
                creation_ft,
                None,
                modification_ft
            )
            
            return bool(result)
            
        except Exception as e:
            log_and_flush(logging.DEBUG, f"Exception in fallback method: {e}")
            return False
        finally:
            # Always close the handle if it was opened
            if handle and handle != -1:
                ctypes.windll.kernel32.CloseHandle(handle)
    
    def copy_timestamps(self, source_file: Union[str, Path], 
                       target_file: Union[str, Path]) -> bool:
        """
        Copy timestamps from source file to target file.
        
        This is a convenience method that combines get_file_timestamps
        and set_file_timestamps.
        
        Args:
            source_file: Source file path
            target_file: Target file path
            
        Returns:
            True if successful, False otherwise
        """
        if self._dry_run:
            log_and_flush(logging.INFO, f"[DRY RUN] Would copy timestamps from {source_file} to {target_file}")
            return True
            
        try:
            # Get timestamps from source
            creation_time, modification_time = self.get_file_timestamps(source_file)
            
            # Set timestamps on target
            success = self.set_file_timestamps(target_file, creation_time, modification_time)
            
            if success:
                log_and_flush(logging.DEBUG, f"Successfully copied timestamps from {source_file} to {target_file}")
            
            return success
            
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error copying timestamps: {e}")
            return False
    
    def verify_timestamps(self, file_path: Union[str, Path], 
                         expected_creation: Optional[datetime] = None,
                         expected_modification: Optional[datetime] = None,
                         tolerance_seconds: float = 1.0) -> bool:
        """
        Verify that a file has the expected timestamps (within tolerance).
        
        Useful for testing and validation.
        
        Args:
            file_path: Path to verify
            expected_creation: Expected creation time (optional)
            expected_modification: Expected modification time (optional)
            tolerance_seconds: Acceptable difference in seconds
            
        Returns:
            True if timestamps match within tolerance, False otherwise
        """
        try:
            actual_creation, actual_modification = self.get_file_timestamps(file_path)
            
            if expected_creation is not None:
                diff = abs((actual_creation - expected_creation).total_seconds())
                if diff > tolerance_seconds:
                    log_and_flush(logging.DEBUG, f"Creation time mismatch: {diff} seconds")
                    return False
            
            if expected_modification is not None:
                diff = abs((actual_modification - expected_modification).total_seconds())
                if diff > tolerance_seconds:
                    log_and_flush(logging.DEBUG, f"Modification time mismatch: {diff} seconds")
                    return False
            
            return True
            
        except Exception as e:
            log_and_flush(logging.DEBUG, f"Error verifying timestamps: {e}")
            return False

# ---------- End of Common FileTimestampManager Code ----------

# ============================================================================
# ERROR DIALOG WITH DETAILS
# ============================================================================

class ErrorDetailsDialog:
    """Custom error dialog with expandable details section."""
    
    def __init__(self, parent, title, summary, details):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x200")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # v001.0014 added [create scaled fonts for error dialog]
        # Create scaled fonts for this dialog
        default_font = tkfont.nametofont("TkDefaultFont") # v001.0014 added [create scaled fonts for error dialog]
        
        self.scaled_label_font = default_font.copy() # v001.0014 added [create scaled fonts for error dialog]
        self.scaled_label_font.configure(size=SCALED_LABEL_FONT_SIZE) # v001.0014 added [create scaled fonts for error dialog]
        # Create a bold version
        self.scaled_label_font_bold = self.scaled_label_font.copy()
        self.scaled_label_font_bold.configure(weight="bold")
        
        self.scaled_button_font = default_font.copy() # v001.0014 added [create scaled fonts for error dialog]
        self.scaled_button_font.configure(size=SCALED_BUTTON_FONT_SIZE) # v001.0014 added [create scaled fonts for error dialog]
        # Create a bold version
        self.scaled_button_font_bold = self.scaled_button_font.copy()
        self.scaled_button_font_bold.configure(weight="bold")
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=12) # v001.0014 changed [tightened padding from padding=15 to padding=12]
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Error icon and summary
        summary_frame = ttk.Frame(main_frame)
        summary_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        ttk.Label(summary_frame, text="❌", font=("TkDefaultFont", 16)).pack(side=tk.LEFT, padx=(0, 10))
        
        # Truncate summary if too long
        display_summary = summary[:200] + "..." if len(summary) > 200 else summary
        ttk.Label(summary_frame, text=display_summary, wraplength=400, font=self.scaled_label_font).pack(side=tk.LEFT, fill=tk.X, expand=True) # v001.0014 changed [use scaled label font instead of default]
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        self.details_shown = False
        self.details_button = ttk.Button(button_frame, text="Show Details ▼", command=self.toggle_details)
        self.details_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="OK", command=self.dialog.destroy).pack(side=tk.RIGHT)
        
        # Details frame (initially hidden)
        self.details_frame = ttk.LabelFrame(main_frame, text="Full Error Details", padding=5)
        
        # Details text with scrollbar
        self.details_text = tk.Text(self.details_frame, wrap=tk.WORD, height=10, width=60)
        details_scroll = ttk.Scrollbar(self.details_frame, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scroll.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.details_text.insert('1.0', details)
        self.details_text.config(state=tk.DISABLED)
        
        self.full_error = f"{summary}\n\nDetails:\n{details}"
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def toggle_details(self):
        if self.details_shown:
            self.details_frame.pack_forget()
            self.details_button.config(text="Show Details ▼")
            self.dialog.geometry("500x200")
        else:
            self.details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            self.details_button.config(text="Hide Details ▲")
            self.dialog.geometry("500x400")
        self.details_shown = not self.details_shown
        
    def copy_to_clipboard(self):
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(self.full_error)
        self.dialog.update()
        # Show temporary confirmation
        self.details_button.config(text="Copied! ✓")
        self.dialog.after(1500, lambda: self.details_button.config(
            text="Hide Details ▲" if self.details_shown else "Show Details ▼"
        ))

# ============================================================================
# COPY SYSTEM ENUMS AND CLASSES
# ============================================================================

class CopyStrategy(Enum):
    """
    Copy strategy enumeration for different file handling approaches.
    
    Purpose:
    --------
    Defines the available copy strategies for file operations
    based on file size, location, and drive type characteristics.
    """
    DIRECT = "direct"           # Strategy A: Direct copy for small files on local drives
    STAGED = "staged"           # Strategy B: Staged copy with rename-based backup for large files
    NETWORK = "network"         # Network-optimized copy with retry logic

class DriveType(Enum):
    """
    Drive type enumeration for path analysis and strategy selection.
    
    Purpose:
    --------
    Categorizes different drive types to enable optimal copy strategy
    selection based on the characteristics of source and destination drives.
    """
    LOCAL_FIXED = "local_fixed"
    LOCAL_REMOVABLE = "local_removable"
    NETWORK_MAPPED = "network_mapped"
    NETWORK_UNC = "network_unc"
    RELATIVE = "relative"
    UNKNOWN = "unknown"

@dataclass
class CopyOperationResult:
    """
    Result container for copy operation outcomes with detailed information.
    
    Purpose:
    --------
    Stores comprehensive information about copy operation results including
    success status, strategy used, performance metrics, and error details.
    
    Usage:
    ------
    Used by FileCopyManager to return detailed operation results
    for logging, error handling, and performance tracking purposes.
    """
    success: bool
    strategy_used: CopyStrategy
    source_path: str
    target_path: str
    file_size: int
    duration_seconds: float
    bytes_copied: int = 0
    error_message: str = ""
    verification_passed: bool = False
    retry_count: int = 0
    temp_path: str = ""
    backup_path: str = ""

# ============================================================================
# COPY SYSTEM UTILITIES
# ============================================================================

def get_drive_type(path: str) -> DriveType:
    """
    Determine the drive type for a given path using Windows API.
    
    Purpose:
    --------
    Analyzes the drive type to enable optimal copy strategy selection
    based on drive characteristics.
    
    Args:
    -----
    path: File or directory path to analyze
    
    Returns:
    --------
    DriveType: Enumerated drive type for strategy selection
    
    Usage:
    ------
    drive_type = get_drive_type("C:\\MyFiles\\file.txt")
    if drive_type == DriveType.NETWORK_MAPPED:
        # Use network-optimized copy strategy
    """
    if not path:
        return DriveType.RELATIVE
    
    # Handle UNC paths (\\server\share)
    if path.startswith('\\\\'):
        return DriveType.NETWORK_UNC
    
    # Extract drive letter
    drive = os.path.splitdrive(path)[0]
    if not drive:
        return DriveType.RELATIVE
    
    try:
        # Use Windows API to determine drive type
        drive_root = drive + '\\'
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive_root))
        
        # Map Windows drive types to our enum
        if drive_type == 2:  # DRIVE_REMOVABLE
            return DriveType.LOCAL_REMOVABLE
        elif drive_type == 3:  # DRIVE_FIXED
            return DriveType.LOCAL_FIXED
        elif drive_type == 4:  # DRIVE_REMOTE
            return DriveType.NETWORK_MAPPED
        elif drive_type == 5:  # DRIVE_CDROM
            return DriveType.LOCAL_REMOVABLE
        elif drive_type == 6:  # DRIVE_RAMDISK
            return DriveType.LOCAL_FIXED
        else:
            return DriveType.UNKNOWN
            
    except Exception as e:
        log_and_flush(logging.WARNING, f"Could not determine drive type for {path}: {e}")
        return DriveType.UNKNOWN

def determine_copy_strategy(source_path: str, target_path: str, file_size: int) -> CopyStrategy:
    """
    Determine the optimal copy strategy based on file size and drive types.
    
    Purpose:
    --------
    Analyzes file characteristics and drive types to select the most efficient
    copy strategy for optimal performance and reliability.
    
    Strategy Logic:
    ---------------
    - Network drives always use STAGED strategy (rename-based backup)
    - Files >= COPY_STRATEGY_THRESHOLD use STAGED strategy (rename-based backup)
    - Small files on local drives use DIRECT strategy
    
    Args:
    -----
    source_path: Source file path for analysis
    target_path: Target file path for analysis  
    file_size: File size in bytes for threshold comparison
    
    Returns:
    --------
    CopyStrategy: Optimal strategy for the given file and drive combination
    """
    source_drive_type = get_drive_type(source_path)
    target_drive_type = get_drive_type(target_path)
    
    # Network drives always use staged strategy (rename-based backup)
    if (source_drive_type in [DriveType.NETWORK_MAPPED, DriveType.NETWORK_UNC] or
        target_drive_type in [DriveType.NETWORK_MAPPED, DriveType.NETWORK_UNC]):
        return CopyStrategy.STAGED
    
    # Large files use staged strategy (rename-based backup)
    if file_size >= COPY_STRATEGY_THRESHOLD:
        return CopyStrategy.STAGED
    
    # Small files on local drives use direct strategy
    return CopyStrategy.DIRECT

def create_copy_operation_logger(operation_id: str) -> logging.Logger: # v000.0002 replaced by updated version
    """
    Create a dedicated logger for a copy operation with timestamped log file.
    
    Purpose:
    --------
    Establishes isolated logging for individual copy operations to enable
    detailed tracking, debugging, and performance analysis per operation.
    
    Args:
    -----
    operation_id: Unique identifier for the copy operation
    
    Returns:
    --------
    logging.Logger: Configured logger instance for the operation
    
    Usage:
    ------
    logger = create_copy_operation_logger("abc123def")
    log_and_flush(logging.INFO, "Copy operation starting...")
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"foldercomparesync_copy_{timestamp}_{operation_id}.log"
    log_filepath = os.path.join(os.path.dirname(__file__), log_filename)
    
    # Create a new logger instance for this operation
    operation_logger = logging.getLogger(f"copy_operation_{operation_id}")
    operation_logger.setLevel(logging.DEBUG)
    
    # Create file handler for this operation with UTF-8 encoding
    file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter for operation logs
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    operation_logger.addHandler(file_handler)
    operation_logger.propagate = False  # Don't propagate to root logger
    
    return operation_logger


@dataclass
class FileMetadata_class:
    """
    Container for file and folder metadata used in comparison operations.
    
    Purpose:
    --------
    Stores comprehensive metadata about files and folders including timestamps,
    size, hash values, and existence status for comparison and synchronization.
    
    Usage:
    ------
    metadata = FileMetadata_class.from_path("/path/to/file.txt", compute_hash=True)
    if metadata.exists and not metadata.is_folder:
        print(f"File size: {metadata.size} bytes")
    """
    path: str
    name: str
    is_folder: bool
    size: Optional[int] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    sha512: Optional[str] = None
    exists: bool = True
    
    @classmethod
    def from_path(cls, path: str, compute_hash: bool = False):
        """Create FileMetadata from a file system path with optional hash computation."""
        p = Path(path)
        if not p.exists():
            return cls(path=path, name=p.name, is_folder=False, exists=False)
        
        try:
            stat = p.stat()
            size = stat.st_size if p.is_file() else None
            date_created = datetime.fromtimestamp(stat.st_ctime)
            date_modified = datetime.fromtimestamp(stat.st_mtime)
            
            sha512 = None
            if compute_hash and p.is_file() and size and size < SHA512_MAX_FILE_SIZE:  # Use configurable limit
                try:
                    hasher = hashlib.sha512()
                    with open(path, 'rb') as f:
                        #sha512 = hashlib.sha512(f.read()).hexdigest()
                        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
                            hasher.update(chunk)
                    sha512 = hasher.hexdigest()
                except Exception:
                    pass  # Hash computation failed, leave as None
            
            return cls(
                path=path,
                name=p.name,
                is_folder=p.is_dir(),
                size=size,
                date_created=date_created,
                date_modified=date_modified,
                sha512=sha512,
                exists=True
            )
        except Exception:
            return cls(path=path, name=p.name, is_folder=False, exists=False)


@dataclass
class ComparisonResult_class:
    """
    Container for storing comparison results between left and right items.
    
    Purpose:
    --------
    Holds the comparison outcome between corresponding files/folders from
    left and right directories, including difference types and overall status.
    
    Usage:
    ------
    result = ComparisonResult_class(left_item, right_item, differences_set)
    if result.is_different:
        print(f"Found differences: {result.differences}")
    """
    left_item: Optional[FileMetadata_class]
    right_item: Optional[FileMetadata_class]
    differences: Set[str]  # Set of difference types: 'existence', 'size', 'date_created', 'date_modified', 'sha512'
    is_different: bool = False
    
    def __post_init__(self):
        self.is_different = len(self.differences) > 0


class ProgressDialog:
    """
    Progress dialog for long-running operations with configurable display options.
    
    Purpose:
    --------
    Provides user feedback during lengthy operations like scanning, comparison,
    and copy operations with both determinate and indeterminate progress modes.
    
    Usage:
    ------
    progress = ProgressDialog(parent, "Scanning", "Scanning files...", max_value=1000)
    progress.update_progress(500, "Processing file 500...")
    progress.close()
    """
    
    def __init__(self, parent, title, message, max_value=None):
        """
        Initialize progress dialog with configurable dimensions.
        
        Args:
        -----
        parent: Parent window for dialog positioning
        title: Dialog window title
        message: Initial progress message
        max_value: Maximum value for percentage (None for indeterminate)
        """
        log_and_flush(logging.DEBUG, f"Creating progress dialog: {title}")
        
        self.parent = parent
        self.max_value = max_value
        self.current_value = 0
        
        # Create dialog window using global constants
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{PROGRESS_DIALOG_WIDTH}x{PROGRESS_DIALOG_HEIGHT}")
        self.dialog.resizable(False, False)
        
        # Center the dialog on parent
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create progress frame
        progress_frame = ttk.Frame(self.dialog, padding=20)
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # Progress message label
        self.message_var = tk.StringVar(value=message)
        ttk.Label(progress_frame, textvariable=self.message_var, 
                 font=("TkDefaultFont", 10)).pack(pady=(0, 10))
        
        # Progress bar or counter display
        if max_value is not None:
            # Determinate progress bar for operations with known total
            self.progress_bar = ttk.Progressbar(
                progress_frame, mode='determinate', maximum=max_value, length=300
            )
            self.progress_bar.pack(pady=(0, 10))
            
            # Percentage label
            self.percent_var = tk.StringVar(value="0%")
            ttk.Label(progress_frame, textvariable=self.percent_var).pack()
        else:
            # Indeterminate progress for operations with unknown total (like file counting)
            self.progress_bar = ttk.Progressbar(
                progress_frame, mode='indeterminate', length=300
            )
            self.progress_bar.pack(pady=(0, 10))
            self.progress_bar.start(PROGRESS_ANIMATION_SPEED)  # Use configurable animation speed
            
            # Running counter display
            self.count_var = tk.StringVar(value="0 items")
            ttk.Label(progress_frame, textvariable=self.count_var, 
                     font=("TkDefaultFont", 9)).pack()
        
        # Update the display
        self.dialog.update_idletasks()
        
        # Center on parent window using configurable dialog dimensions
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (PROGRESS_DIALOG_WIDTH // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (PROGRESS_DIALOG_HEIGHT // 2)
        self.dialog.geometry(f"{PROGRESS_DIALOG_WIDTH}x{PROGRESS_DIALOG_HEIGHT}+{x}+{y}")
        
    def update_message(self, message):
        """Update the progress message display."""
        self.message_var.set(message)
        self.dialog.update_idletasks()
        
    def update_progress(self, value, message=None):
        """Update progress value and optionally message."""
        if self.max_value is not None:
            # Determinate progress
            self.current_value = value
            self.progress_bar['value'] = value
            percentage = int((value / self.max_value) * 100) if self.max_value > 0 else 0
            self.percent_var.set(f"{percentage}%")
        else:
            # Indeterminate progress - update counter
            self.count_var.set(f"{value:,} items")
            
        if message:
            self.message_var.set(message)
            
        self.dialog.update_idletasks()
        
    def close(self):
        """Close the progress dialog and clean up resources."""
        log_and_flush(logging.DEBUG, "Closing progress dialog")
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.stop()  # Stop any animation
            self.dialog.grab_release()
            self.dialog.destroy()
        except tk.TclError:
            pass  # Dialog already destroyed


class FileCopyManager:
    """
    file copy manager implementing Strategy A and Strategy B
    with rename-based backup , comprehensive error handling, and dry run capability.
    
    Purpose:
    --------
    Manages file copy operations using intelligent strategy selection based on file
    size and drive types, with support for both actual operations and dry run simulation.
    
    Key Features:
    -------------
    - Dual copy strategies (Direct and Staged) with automatic selection
    - Complete timestamp preservation with rollback capability
    - Dry run mode for safe operation testing without file modifications
    - Comprehensive logging and performance tracking
    - Atomic operations using Windows rename primitives
    
    Usage:
    ------
    copy_manager = FileCopyManager(status_callback=add_status_message)
    copy_manager.set_dry_run_mode(True)  # For testing
    operation_id = copy_manager.start_copy_operation("Test Copy")
    result = copy_manager.copy_file(source, target, overwrite=True)
    copy_manager.end_copy_operation(success_count, error_count, total_bytes)
    """
    
    def __init__(self, status_callback=None):
        """
        Initialize the copy manager with callback and supporting components.
        
        Args:
        -----
        status_callback: Function to call for status updates (optional)
        """
        self.status_callback = status_callback
        self.operation_id = None
        self.operation_logger = None
        self.timestamp_manager = FileTimestampManager()  # Single instance, will update in set_dry_run_mode
        self.dry_run_mode = False  # New: Dry run mode flag
        self.operation_sequence = 0  # New: Sequential numbering for operations
        
        # Log timezone information for the copy manager
        log_and_flush(logging.INFO, f"FileCopyManager initialized with timezone: {self.timestamp_manager.get_timezone_string()}")
    def set_dry_run_mode(self, enabled: bool):
        """
        Enable or disable dry run mode for safe operation testing.
        
        Purpose:
        --------
        When enabled, all copy operations are simulated without actual file I/O,
        providing full logging and strategy selection for testing purposes.
        
        Args:
        -----
        enabled: True to enable dry run mode, False for normal operations
        """
        self.dry_run_mode = enabled
        self.timestamp_manager = FileTimestampManager(dry_run=enabled)  # Update timestamp manager
        mode_text = "DRY RUN" if enabled else "NORMAL"
        self._log_status(f"Copy manager mode set to: {mode_text}")
        
    def _log_status(self, message: str):
        """Log status message to both operation logger and status callback."""
        if self.operation_logger:
            self.operation_log_and_flush(logging.INFO, message)
        if self.status_callback:
            self.status_callback(message)
        log_and_flush(logging.DEBUG, f"Copy operation status: {message}")
    
    def _verify_copy(self, source_path: str, target_path: str) -> bool:
        """
        Verify (simple method) that a copy operation was successful (or simulate Simple verification in dry run).
        
        Returns True if Simple verification passes, False otherwise
        """
        if not COPY_VERIFICATION_ENABLED:
            return True
        
        if self.dry_run_mode:
            self._log_status(f"DRY RUN: Would verify copy - {target_path}")
            return True  # Assume Simple verification would pass in dry run
            
        try:
            # Check file existence
            if not Path(target_path).exists():
                self._log_status(f"Simple verification failed: Target file does not exist: {target_path}")
                return False
            
            # Check file size
            source_size = Path(source_path).stat().st_size
            target_size = Path(target_path).stat().st_size
            
            if source_size != target_size:
                self._log_status(f"Simple verification failed: Size mismatch - Source: {source_size}, Target: {target_size}")
                return False
            
            self._log_status(f"Simple verification passed: {target_path} ({source_size} bytes)")
            return True
            
        except Exception as e:
            self._log_status(f"Simple verification error: {str(e)}")
            return False
    
    def _copy_direct_strategy(self, source_path: str, target_path: str) -> CopyOperationResult:
        """
        Strategy A: Direct copy for small files on local drives (with dry run support).
        Uses shutil.copy2 with error handling and Simple verification.
        """
        start_time = time.time()
        file_size = Path(source_path).stat().st_size
        
        dry_run_prefix = "DRY RUN: " if self.dry_run_mode else ""
        self._log_status(f"{dry_run_prefix}Using DIRECT strategy for {os.path.basename(source_path)} ({file_size} bytes)")
        
        result = CopyOperationResult(
            success=False,
            strategy_used=CopyStrategy.DIRECT,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0,
            bytes_copied=0
        )
        
        try:
            # Ensure target directory exists (or simulate in dry run)
            target_dir = Path(target_path).parent
            if target_dir and not target_dir.exists():
                if self.dry_run_mode:
                    self._log_status(f"DRY RUN: Would create target directory: {target_dir}")
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    self._log_status(f"Created target directory: {target_dir}")
            
            # Perform direct copy (or simulate in dry run)
            self._log_status(f"{dry_run_prefix}Copying: {source_path} -> {target_path}")
            
            if not self.dry_run_mode:
                shutil.copy2(source_path, target_path)
                result.bytes_copied = file_size
                
                # Copy timestamps from source to target for complete preservation
                self.timestamp_manager.copy_timestamps(source_path, target_path)
            else:
                # Simulate copy operation
                result.bytes_copied = file_size
                self._log_status(f"DRY RUN: Would copy timestamps from source to target")
            
            # Verify the copy (or simulate Simple verification in dry run)
            if self._verify_copy(source_path, target_path):
                result.success = True
                result.verification_passed = True
                self._log_status(f"{dry_run_prefix}DIRECT copy completed successfully")
            else:
                result.error_message = "Copy Simple verification failed"
                self._log_status(f"{dry_run_prefix}DIRECT copy failed Simple verification")
                
        except Exception as e:
            if not self.dry_run_mode:
                result.error_message = str(e)
                self._log_status(f"DIRECT copy failed: {str(e)}")
            else:
                # In dry run, we don't expect real exceptions
                result.success = True
                result.verification_passed = True
                self._log_status(f"DRY RUN: DIRECT copy simulation completed")
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def _copy_staged_strategy(self, source_path: str, target_path: str, overwrite: bool = True) -> CopyOperationResult:
        """
        Strategy B: staged copy using rename-based backup for large files or network drives (with dry run support).
        Implements 4-step process: save timestamps -> rename to backup -> copy source -> verify
        Uses atomic rename operations instead of expensive copy operations for backup.
        """
        start_time = time.time()
        file_size = Path(source_path).stat().st_size
        
        dry_run_prefix = "DRY RUN: " if self.dry_run_mode else ""
        self._log_status(f"{dry_run_prefix}Using STAGED strategy for {os.path.basename(source_path)} ({file_size} bytes)")
        
        result = CopyOperationResult(
            success=False,
            strategy_used=CopyStrategy.STAGED,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0,
            bytes_copied=0
        )
        
        # Generate unique identifier for backup file
        backup_uuid = uuid.uuid4().hex[:8]
        backup_path = f"{target_path}.backup_{backup_uuid}" if Path(target_path).exists() else None
        original_timestamps = None
        
        result.backup_path = backup_path
        
        try:
            # Ensure target directory exists (or simulate in dry run)
            target_dir = Path(target_path).parent
            if target_dir and not target_dir.exists():
                if self.dry_run_mode:
                    self._log_status(f"DRY RUN: Would create target directory: {target_dir}")
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    self._log_status(f"Created target directory: {target_dir}")
            
            # Step 1: Check overwrite permission and save original timestamps (or simulate in dry run)
            if Path(target_path).exists():
                if not overwrite:
                    result.error_message = "Target file exists and overwrite is disabled"
                    self._log_status(f"{dry_run_prefix}STAGED copy skipped: Target exists and overwrite disabled")
                    return result
                
                # Save original timestamps for potential rollback (or simulate in dry run)
                try:
                    if not self.dry_run_mode:
                        original_timestamps = self.timestamp_manager.get_file_timestamps(target_path)
                        self._log_status(f"Step 1: Saved original timestamps for potential rollback")
                    else:
                        self._log_status(f"DRY RUN: Step 1: Would save original timestamps for potential rollback")
                except Exception as e:
                    self._log_status(f"Warning: Could not save original timestamps: {e}")
                    # Continue anyway - this is not critical for copy operation
            
            # Step 2: Rename target to backup (atomic, fast operation) (or simulate in dry run)
            if Path(target_path).exists():
                try:
                    self._log_status(f"{dry_run_prefix}Step 2: Renaming target to backup: {target_path} -> {backup_path}")
                    if not self.dry_run_mode:
                        os.rename(target_path, backup_path)
                        self._log_status(f"Atomic rename completed successfully")
                    else:
                        self._log_status(f"DRY RUN: Atomic rename simulation completed")
                except OSError as e:
                    if not self.dry_run_mode:
                        # Critical failure - rename operation failed
                        result.error_message = f"CRITICAL: Rename operation failed - {str(e)}. This may indicate network drive issues or file locking. Operation aborted to prevent data loss."
                        self._log_status(f"CRITICAL FAILURE: Rename operation failed: {str(e)}")
                        self._log_status("RECOMMENDED ACTION: Check if target file is locked by another process, or if network drive has connectivity issues.")
                        return result
                    else:
                        # In dry run, simulate successful rename
                        self._log_status(f"DRY RUN: Rename simulation completed successfully")
            
            # Step 3: Copy source directly to target location (single copy operation) (or simulate in dry run)
            try:
                self._log_status(f"{dry_run_prefix}Step 3: Copying source to target: {source_path} -> {target_path}")
                
                if not self.dry_run_mode:
                    shutil.copy2(source_path, target_path)
                    result.bytes_copied = file_size
                    self._log_status(f"Copy operation completed")
                    
                    # Copy timestamps from source to target for complete preservation
                    self.timestamp_manager.copy_timestamps(source_path, target_path)
                    self._log_status(f"Timestamps copied from source to target")
                else:
                    # Simulate copy operation
                    result.bytes_copied = file_size
                    self._log_status(f"DRY RUN: Copy operation simulation completed")
                    self._log_status(f"DRY RUN: Would copy timestamps from source to target")
                
            except Exception as e:
                if not self.dry_run_mode:
                    # Copy failed - begin rollback procedure
                    result.error_message = f"Copy operation failed: {str(e)}"
                    self._log_status(f"Copy operation failed: {str(e)} - Beginning rollback")
                    raise  # Re-raise to trigger rollback in except block
                else:
                    # In dry run, simulate successful copy
                    result.bytes_copied = file_size
                    self._log_status(f"DRY RUN: Copy simulation completed successfully")
            
            # Step 4: Verify copy operation (or simulate in dry run)
            self._log_status(f"{dry_run_prefix}Step 4: Verifying copied file")
            if not self._verify_copy(source_path, target_path):
                if not self.dry_run_mode:
                    result.error_message = "Copy Simple verification failed"
                    self._log_status(f"STAGED copy failed: Simple verification failed - Beginning rollback")
                    raise Exception("Simple verification failed")  # Trigger rollback
                else:
                    self._log_status(f"DRY RUN: Simple verification simulation completed")
            
            # Step 5: Success - remove backup file (or simulate in dry run)
            if backup_path and (Path(backup_path).exists() or self.dry_run_mode):
                try:
                    if not self.dry_run_mode:
                        os.remove(backup_path)
                        self._log_status(f"Step 5: Removed backup file: {backup_path}")
                    else:
                        self._log_status(f"DRY RUN: Step 5: Would remove backup file: {backup_path}")
                except Exception as e:
                    # Non-critical - backup removal failed but copy succeeded
                    self._log_status(f"Warning: Could not remove backup file {backup_path}: {e}")
                    self._log_status("This is not critical - copy operation succeeded")
            
            result.success = True
            result.verification_passed = True
            self._log_status(f"{dry_run_prefix}STAGED copy completed successfully")
                
        except Exception as e:
            if not self.dry_run_mode:
                result.error_message = str(e) if not result.error_message else result.error_message
                self._log_status(f"STAGED copy failed: {result.error_message}")
                
                # ROLLBACK PROCEDURE: Restore original file and timestamps
                try:
                    self._log_status(f"Beginning rollback procedure for failed STAGED copy")
                    
                    # Remove any partial target file
                    if Path(target_path).exists():
                        try:
                            os.remove(target_path)
                            self._log_status(f"Removed partial target file: {target_path}")
                        except Exception as remove_error:
                            self._log_status(f"Warning: Could not remove partial target file: {remove_error}")
                    
                    # Restore backup file if it exists
                    if backup_path and Path(backup_path).exists():
                        try:
                            self._log_status(f"Restoring backup file: {backup_path} -> {target_path}")
                            os.rename(backup_path, target_path)
                            self._log_status(f"Backup file restored successfully")
                            
                            # Restore original timestamps if we saved them
                            if original_timestamps:
                                try:
                                    self.timestamp_manager.set_file_timestamps(target_path, *original_timestamps)
                                    self._log_status(f"Original timestamps restored successfully")
                                except Exception as timestamp_error:
                                    self._log_status(f"Warning: Could not restore original timestamps: {timestamp_error}")
                            
                        except Exception as restore_error:
                            # CRITICAL: Rollback failed
                            critical_error = f"CRITICAL ROLLBACK FAILURE: {str(restore_error)}"
                            self._log_status(critical_error)
                            self._log_status(f"CRITICAL: Original file may be lost. Backup is at: {backup_path}")
                            self._log_status("RECOMMENDED ACTION: Manually restore the backup file to recover your data.")
                            result.error_message += f" | {critical_error}"
                    else:
                        self._log_status("No backup file to restore (target file was new)")
                    
                    self._log_status(f"Rollback procedure completed")
                    
                except Exception as rollback_error:
                    rollback_failure = f"Rollback procedure failed: {str(rollback_error)}"
                    self._log_status(rollback_failure)
                    result.error_message += f" | {rollback_failure}"
            else:
                # In dry run mode, simulate successful operation
                result.success = True
                result.verification_passed = True
                self._log_status(f"DRY RUN: STAGED copy simulation completed successfully")
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def copy_file(self, source_path: str, target_path: str, overwrite: bool = True) -> CopyOperationResult:
        """
        Main copy method that automatically selects the appropriate strategy and supports dry run mode.
        
        Purpose:
        --------
        Orchestrates file copy operations using intelligent strategy selection based on
        file characteristics and drive types, with full dry run simulation capability.
        
        Args:
        -----
        source_path: Source file path
        target_path: Target file path  
        overwrite: Whether to overwrite existing files
        
        Returns:
        --------
        CopyOperationResult: Detailed result of the copy operation
        """
        # Increment sequence number for this operation
        self.operation_sequence += 1
        
        # Validate input paths
        if not Path(source_path).exists():
            return CopyOperationResult(
                success=False,
                strategy_used=CopyStrategy.DIRECT,
                source_path=source_path,
                target_path=target_path,
                file_size=0,
                duration_seconds=0,
                error_message="Source file does not exist"
            )
        
        if not Path(source_path).is_file():
            return CopyOperationResult(
                success=False,
                strategy_used=CopyStrategy.DIRECT,
                source_path=source_path,
                target_path=target_path,
                file_size=0,
                duration_seconds=0,
                error_message="Source path is not a file"
            )
        
        # Get file size for strategy determination
        file_size = Path(source_path).stat().st_size
        
        # Determine copy strategy
        strategy = determine_copy_strategy(source_path, target_path, file_size)
        
        # Log operation start with sequence number
        dry_run_prefix = "DRY RUN: " if self.dry_run_mode else ""
        sequence_info = f"[{self.operation_sequence}]"
        
        self._log_status(f"{dry_run_prefix}Starting copy operation {sequence_info}:")
        self._log_status(f"  Source: {source_path}")
        self._log_status(f"  Target: {target_path}")
        self._log_status(f"  Size: {file_size:,} bytes")
        self._log_status(f"  Strategy: {strategy.value}")
        self._log_status(f"  Overwrite: {overwrite}")
        if self.dry_run_mode:
            self._log_status(f"  Mode: DRY RUN SIMULATION")
        
        # Execute appropriate strategy
        if strategy == CopyStrategy.DIRECT:
            result = self._copy_direct_strategy(source_path, target_path)
        else:  # STAGED strategy with rename-based backup
            result = self._copy_staged_strategy(source_path, target_path, overwrite)
        
        # Log final result with sequence number
        if result.success:
            self._log_status(f"{dry_run_prefix}Copy operation {sequence_info} SUCCESSFUL - {result.bytes_copied:,} bytes in {result.duration_seconds:.2f}s")
        else:
            self._log_status(f"{dry_run_prefix}Copy operation {sequence_info} FAILED - {result.error_message}")
        
        return result
    
    def start_copy_operation(self, operation_name: str, dry_run: bool = False) -> str:
        """
        Start a new copy operation session with dedicated logging and dry run support.
        
        Args:
        -----
        operation_name: Descriptive name for the operation
        dry_run: Whether this is a dry run operation
        
        Returns:
        --------
        str: Operation ID for tracking
        """
        self.operation_id = uuid.uuid4().hex[:8]
        self.operation_logger = create_copy_operation_logger(self.operation_id)
        self.operation_sequence = 0  # Reset sequence counter for new operation
        self.set_dry_run_mode(dry_run)
        
        dry_run_text = " (DRY RUN SIMULATION)" if dry_run else ""
        
        self.operation_log_and_flush(logging.INFO, "=" * 80)
        self.operation_log_and_flush(logging.INFO, f"COPY OPERATION STARTED: {operation_name}{dry_run_text}")
        self.operation_log_and_flush(logging.INFO, f"Operation ID: {self.operation_id}")
        self.operation_log_and_flush(logging.INFO, f"Mode: {'DRY RUN SIMULATION' if dry_run else 'NORMAL OPERATION'}")
        self.operation_log_and_flush(logging.INFO, f"Timestamp: {datetime.now().isoformat()}")
        self.operation_log_and_flush(logging.INFO, "=" * 80)
        
        return self.operation_id
    
    def end_copy_operation(self, success_count: int, error_count: int, total_bytes: int):
        """
        End the current copy operation session with comprehensive summary.
        
        Args:
        -----
        success_count: Number of successfully processed files
        error_count: Number of files that failed
        total_bytes: Total bytes processed
        """
        if self.operation_logger:
            dry_run_text = " (DRY RUN SIMULATION)" if self.dry_run_mode else ""
            
            self.operation_log_and_flush(logging.INFO, "=" * 80)
            self.operation_log_and_flush(logging.INFO, f"COPY OPERATION COMPLETED{dry_run_text}")
            self.operation_log_and_flush(logging.INFO, f"Operation ID: {self.operation_id}")
            self.operation_log_and_flush(logging.INFO, f"Files processed successfully: {success_count}")
            self.operation_log_and_flush(logging.INFO, f"Files failed: {error_count}")
            self.operation_log_and_flush(logging.INFO, f"Total bytes processed: {total_bytes:,}")
            self.operation_log_and_flush(logging.INFO, f"Total operations: {self.operation_sequence}")
            if self.dry_run_mode:
                self.operation_log_and_flush(logging.INFO, "NOTE: This was a DRY RUN simulation - no actual files were modified")
            self.operation_log_and_flush(logging.INFO, f"Timestamp: {datetime.now().isoformat()}")
            self.operation_log_and_flush(logging.INFO, "=" * 80)
            
            # Close the operation logger
            for handler in self.operation_logger.handlers[:]:
                handler.close()
                self.operation_logger.removeHandler(handler)
        
        self.operation_id = None
        self.operation_logger = None
        self.operation_sequence = 0


class FolderCompareSync_class:
    """
    Main application class for folder comparison and synchronization with limits and dry run capability.
    
    Purpose:
    --------
    Provides the primary GUI interface for comparing two folder structures, identifying differences,
    and synchronizing files between them using a copy system with comprehensive safety features.
    
    Key Features:
    -------------
    - Dual-pane folder comparison with detailed metadata analysis
    - Configurable file/folder limits (100,000 max) with early abort protection
    - Dry run mode for safe operation testing without file modifications
    - Advanced filtering and selection capabilities
    - Status log export functionality for record keeping
    - Comprehensive error handling and user guidance
    
    Usage:
    ------
    app = FolderCompareSync_class()
    app.run()
    """
    
    def __init__(self):
        """Initialize the main application with all components and limits."""
        log_and_flush(logging.INFO, "Initializing FolderCompareSync application")
        global log_level
        if __debug__:
            if log_level == logging.DEBUG:
                log_and_flush(logging.DEBUG, "Debug mode enabled - Debug log_level active")
            else:
                log_and_flush(logging.DEBUG, "Debug mode enabled - non-Debug log_level active")
        
        self.root = tk.Tk()
        self.root.title("FolderCompareSync - Folder Comparison and Syncing Tool")
    
        # NEW style configs for the "Compare" "Copy" "Quit" buttons  button
        # 1) Get the existing default font and make a bold copy
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.bold_font = self.default_font.copy()
        self.bold_font.configure(weight="bold")
        
        # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        # Create scaled fonts based on configuration
        self.scaled_button_font = self.default_font.copy() # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        self.scaled_button_font.configure(size=SCALED_BUTTON_FONT_SIZE)
        # Create a bold version
        self.scaled_button_font_bold = self.scaled_button_font.copy()
        self.scaled_button_font_bold.configure(weight="bold")
        
        self.scaled_label_font = self.default_font.copy() # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        self.scaled_label_font.configure(size=SCALED_LABEL_FONT_SIZE) # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        
        self.scaled_entry_font = self.default_font.copy() # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        self.scaled_entry_font.configure(size=SCALED_ENTRY_FONT_SIZE) # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        
        self.scaled_checkbox_font = self.default_font.copy() # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        self.scaled_checkbox_font.configure(size=SCALED_CHECKBOX_FONT_SIZE) # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        
        self.scaled_dialog_font = self.default_font.copy() # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        self.scaled_dialog_font.configure(size=SCALED_DIALOG_FONT_SIZE) # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        
        self.scaled_status_font = self.default_font.copy() # v001.0016 added [scaled font for status messages using global SCALED_STATUS_MESSAGE_FONT_SIZE]
        self.scaled_status_font.configure(size=SCALED_STATUS_MESSAGE_FONT_SIZE) # v001.0016 added [scaled font for status messages using global SCALED_STATUS_MESSAGE_FONT_SIZE]
        
        self.style = ttk.Style(self.root)
        # 2) Create colour styles for some bolded_fonts
        self.style.configure("LimeGreenBold.TButton", foreground="limegreen",font=self.scaled_button_font_bold)
        self.style.configure("GreenBold.TButton", foreground="green",font=self.scaled_button_font_bold)
        self.style.configure("DarkGreenBold.TButton", foreground="darkgreen",font=self.scaled_button_font_bold)
        self.style.configure("RedBold.TButton", foreground="red",font=self.scaled_button_font_bold)
        self.style.configure("PurpleBold.TButton", foreground="purple",font=self.scaled_button_font_bold)
        self.style.configure("MediumPurpleBold.TButton", foreground="mediumpurple",font=self.scaled_button_font_bold)
        self.style.configure("IndigoBold.TButton", foreground="indigo",font=self.scaled_button_font_bold)
        self.style.configure("BlueBold.TButton", foreground="blue",font=self.scaled_button_font_bold)
        self.style.configure("GoldBold.TButton", foreground="gold",font=self.scaled_button_font_bold)
        self.style.configure("YellowBold.TButton", foreground="yellow",font=self.scaled_button_font_bold)

        # v001.0016 added [default button style for buttons without specific colors]
        self.style.configure("DefaultNormal.TButton", font=self.scaled_button_font, weight="normal") # v001.0016 added [default button style for buttons without specific colors]
        self.style.configure("DefaultBold.TButton.TButton", font=self.scaled_button_font_bold, weight="bold")     # v001.0016 added [default bold button style for buttons without specific colors]

        # v001.0014 added [create custom ttk styles for scaled fonts]
        # Create custom styles for ttk widgets that need scaled fonts
        self.style.configure("Scaled.TCheckbutton", font=self.scaled_checkbox_font)
        self.style.configure("Scaled.TLabel", font=self.scaled_label_font)
        self.style.configure("StatusMessage.TLabel", font=self.scaled_status_font) # v001.0016 added [status message label style using SCALED_STATUS_MESSAGE_FONT_SIZE]
        self.style.configure("Scaled.TEntry", font=self.scaled_entry_font)
    
        # Configure tree row height for all treeviews globally # v001.0015 added [tree row height control for compact display]
        self.style.configure("Treeview", rowheight=TREE_ROW_HEIGHT) # v001.0015 added [tree row height control for compact display]
    
        # Get screen dimensions for smart window sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Use configurable window sizing percentages
        window_width = int(screen_width * WINDOW_WIDTH_PERCENT)
        window_height = int(screen_height * WINDOW_HEIGHT_PERCENT)
        
        # Center horizontally, use configurable top offset for optimal taskbar clearance
        x = (screen_width - window_width) // 2
        y = WINDOW_TOP_OFFSET
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)  # Use configurable minimum size
        
        # Application state variables
        self.left_folder = tk.StringVar()
        self.right_folder = tk.StringVar()
        self.compare_existence = tk.BooleanVar(value=True)
        self.compare_size = tk.BooleanVar(value=True)
        self.compare_date_created = tk.BooleanVar(value=True)
        self.compare_date_modified = tk.BooleanVar(value=True)
        self.compare_sha512 = tk.BooleanVar(value=False)
        self.overwrite_mode = tk.BooleanVar(value=True)
        self.dry_run_mode = tk.BooleanVar(value=False)
        
        # Filtering state # v000.0002 changed - removed sorting
        self.filter_wildcard = tk.StringVar()

        self.filtered_results = {}  # Store filtered comparison results
        self.is_filtered = False
        
        # Data storage for comparison results and selection state
        self.comparison_results: Dict[str, ComparisonResult_class] = {}
        self.selected_left: Set[str] = set()
        self.selected_right: Set[str] = set()
        self.tree_structure: Dict[str, List[str]] = {'left': [], 'right': []}
        
        # Path mapping for proper status determination and tree navigation
        # Maps relative_path -> tree_item_id for efficient lookups
        self.path_to_item_left: Dict[str, str] = {}  # rel_path -> tree_item_id
        self.path_to_item_right: Dict[str, str] = {}  # rel_path -> tree_item_id
        
        # Store root item IDs for special handling in selection logic
        self.root_item_left: Optional[str] = None
        self.root_item_right: Optional[str] = None
        
        # Flag to prevent recursive display updates during tree operations
        self._updating_display = False
        
        # Status log management using configurable constants
        self.status_log_lines = []  # Store status messages
        self.max_status_lines = STATUS_LOG_MAX_HISTORY  # Use configurable maximum (5000)
        
        # File count tracking for limits
        self.file_count_left = 0
        self.file_count_right = 0
        self.total_file_count = 0
        self.limit_exceeded = False
        
        # UI References for widget interaction
        self.left_tree = None
        self.right_tree = None
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="Summary: No comparison performed")
        self.status_log_text = None  # Will be set in setup_ui
        
        # copy system with staged strategy and dry run support
        self.copy_manager = FileCopyManager(status_callback=self.add_status_message)
        
        if __debug__:
            log_and_flush(logging.DEBUG, "Application state initialized with dual copy system")
        
        self.setup_ui()
        
        # Add startup warnings about performance and limits
        self.add_status_message("Application initialized - dual copy system ready")
        self.add_status_message(f"WARNING: Large folder operations may be slow. Maximum {MAX_FILES_FOLDERS:,} files/folders supported.")
        self.add_status_message("Tip: Use filtering and dry run mode for testing with large datasets.")
        
        # Display detected timezone information
        timezone_str = self.copy_manager.timestamp_manager.get_timezone_string()
        self.add_status_message(f"Timezone detected: {timezone_str} - will be used for timestamp operations")
        log_and_flush(logging.INFO, "Application initialization complete ")

    def add_status_message(self, message):
        """
        Add a timestamped message to the status log using configurable history limit.
        
        Purpose:
        --------
        Maintains a comprehensive log of all application operations with timestamps
        for debugging, auditing, and user feedback purposes.
        
        Args:
        -----
        message: Message to add to status log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_line = f"{timestamp} - {message}"
        
        # Add to our internal list
        self.status_log_lines.append(status_line)
        
        # Trim to configurable maximum lines (5000)
        if len(self.status_log_lines) > self.max_status_lines:
            self.status_log_lines = self.status_log_lines[-self.max_status_lines:]
            
        # Update the text widget if it exists
        if self.status_log_text:
            self.status_log_text.config(state=tk.NORMAL)
            self.status_log_text.delete('1.0', tk.END)
            self.status_log_text.insert('1.0', '\n'.join(self.status_log_lines))
            self.status_log_text.config(state=tk.DISABLED)
            self.status_log_text.see(tk.END)  # Auto-scroll to bottom
            
        log_and_flush(logging.INFO, f"STATUS: {message}")

    def export_status_log(self):
        """
        Export the complete status log to clipboard and optionally to a file.
        
        Purpose:
        --------
        Provides users with the ability to save or share comprehensive operation
        logs for debugging, record keeping, or support purposes.
        """
        if not self.status_log_lines:
            messagebox.showinfo("Export Status Log", "No status log data to export.")
            return
        
        # Prepare export data
        export_text = "\n".join(self.status_log_lines)
        total_lines = len(self.status_log_lines)
        
        try:
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(export_text)
            self.root.update()  # Make sure clipboard is updated
            
            # Ask user if they want to save to file as well
            response = messagebox.askyesnocancel(
                "Export Status Log", 
                f"Status log ({total_lines:,} lines) copied to clipboard!\n\n"
                f"Would you also like to save to a file?\n\n"
                f"Yes = Save to file\n"
                f"No = Clipboard only\n"
                f"Cancel = Cancel export"
            )
            
            if response is True:  # Yes - save to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                default_filename = f"foldercomparesync_status_{timestamp}.log"
                
                file_path = filedialog.asksaveasfilename(
                    title="Save Status Log",
                    defaultextension=".log",
                    initialname=default_filename,
                    filetypes=[
                        ("Log files", "*.log"),
                        ("Text files", "*.txt"),
                        ("All files", "*.*")
                    ]
                )
                
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(export_text)
                    
                    self.add_status_message(f"Status log exported to: {file_path}")
                    messagebox.showinfo("Export Complete", f"Status log saved to:\n{file_path}")
                else:
                    self.add_status_message("Status log export to file cancelled")
            elif response is False:  # No - clipboard only
                self.add_status_message(f"Status log ({total_lines:,} lines) exported to clipboard")
            else:  # Cancel
                self.add_status_message("Status log export cancelled")
                
        except Exception as e:
            error_msg = f"Failed to export status log: {str(e)}"
            self.add_status_message(f"ERROR: {error_msg}")
            self.show_error(error_msg)

    def on_dry_run_changed(self):
        """
        Handle dry run mode checkbox changes.
        
        Purpose:
        --------
        Ensures proper interaction between dry run and overwrite modes,
        automatically disabling overwrite when dry run is enabled for safety.
        """
        if self.dry_run_mode.get():
            # When dry run is enabled, disable overwrite mode for safety
            self.overwrite_mode.set(False)
            self.add_status_message("DRY RUN mode enabled - Overwrite mode disabled for safety")
        else:
            self.add_status_message("DRY RUN mode disabled - Normal operations enabled")

    def set_debug_loglevel(self, enabled: bool):
        """
        Toggle debug loglevel in logging on/off during runtime.
        
        Purpose:
        --------
        Provides runtime control over logging verbosity for debugging
        and troubleshooting without restarting the application.
        
        Args:
        -----
        enabled: True to enable debug logging, False to disable
        
        Usage:
        ------
        app.set_debug_loglevel(True)   # Enable debug logging
        app.set_debug_loglevel(False)  # Disable debug logging
        """
        global log_level
        if enabled:
            log_level = logging.DEBUG
            log_and_flush(logging.INFO, "[DEBUG] Debug logging enabled - Debug output activated")
        else:
            log_level = logging.INFO
            log_and_flush(logging.INFO, "[INFO] Debug logging disabled - Info mode activated")
        logger.setLevel(log_level)
        # Update status to show updated current mode
        if hasattr(self, 'status_var'):
            current_status = self.status_var.get()
            mode = "DEBUG" if enabled else "NORMAL"
            self.status_var.set(f"{current_status} ({mode})")

    def delete_left_orphans(self): # v001.0012 added [delete left orphans button command]
        """Handle Delete LEFT-only Orphaned Files button.""" # v001.0012 added [delete left orphans button command]
        if self.limit_exceeded: # v001.0012 added [delete left orphans button command]
            messagebox.showwarning("Operation Disabled", "Delete operations are disabled when file limits are exceeded.") # v001.0012 added [delete left orphans button command]
            return # v001.0012 added [delete left orphans button command]
            
        if not self.comparison_results: # v001.0012 added [delete left orphans button command]
            self.add_status_message("No comparison data available - please run comparison first") # v001.0012 added [delete left orphans button command]
            messagebox.showinfo("No Data", "Please perform a folder comparison first.") # v001.0012 added [delete left orphans button command]
            return # v001.0012 added [delete left orphans button command]
            
        # Get current filter if active # v001.0012 added [delete left orphans button command]
        active_filter = self.filter_wildcard.get() if self.is_filtered else None # v001.0012 added [delete left orphans button command]
        
        # Detect orphaned files on left side # v001.0012 added [delete left orphans button command]
        orphaned_files = DeleteOrphansManager_class.detect_orphaned_files(self.comparison_results, 'left', active_filter) # v001.0012 changed [use DeleteOrphansManager_class class method]
        
        if not orphaned_files: # v001.0012 added [delete left orphans button command]
            filter_text = f" (with active filter: {active_filter})" if active_filter else "" # v001.0012 added [delete left orphans button command]
            self.add_status_message(f"No orphaned files found on LEFT side{filter_text}") # v001.0012 added [delete left orphans button command]
            messagebox.showinfo("No Orphans", f"No orphaned files found on LEFT side{filter_text}.") # v001.0012 added [delete left orphans button command]
            return # v001.0012 added [delete left orphans button command]
            
        self.add_status_message(f"Opening delete orphans dialog for LEFT side: {len(orphaned_files)} files") # v001.0012 added [delete left orphans button command]
        
        try: # v001.0012 added [delete left orphans button command]
            # Create and show delete orphans manager/dialog # v001.0012 added [delete left orphans button command]
            manager = DeleteOrphansManager_class ( # v001.0012 changed [use DeleteOrphansManager_class instead of DeleteOrphansDialog]
                parent=self.root, # v001.0012 added [delete left orphans button command]
                orphaned_files=orphaned_files, # v001.0012 added [delete left orphans button command]
                side='left', # v001.0012 added [delete left orphans button command]
                source_folder=self.left_folder.get(), # v001.0012 added [delete left orphans button command]
                dry_run_mode=self.dry_run_mode.get(), # v001.0012 added [delete left orphans button command]
                comparison_results=self.comparison_results, # v001.0012 added [delete left orphans button command]
                active_filter=active_filter # v001.0012 added [delete left orphans button command]
            ) # v001.0012 added [delete left orphans button command]
            
            # Wait for dialog to complete # v001.0012 added [delete left orphans button command]
            self.root.wait_window(manager.dialog) # v001.0012 changed [use manager.dialog instead of dialog.dialog]
            
            # Check if files were actually deleted (not dry run) # v001.0012 added [delete left orphans button command]
            if hasattr(manager, 'result') and manager.result == 'deleted' and not self.dry_run_mode.get(): # v001.0012 changed [use manager instead of dialog]
                self.add_status_message("Delete operation completed - refreshing folder comparison...") # v001.0012 added [delete left orphans button command]
                # Refresh comparison to show updated state # v001.0012 added [delete left orphans button command]
                self.refresh_after_copy_operation() # v001.0012 added [delete left orphans button command]
            else: # v001.0012 added [delete left orphans button command]
                self.add_status_message("Delete orphans dialog closed") # v001.0012 added [delete left orphans button command]
                
        except Exception as e: # v001.0012 added [delete left orphans button command]
            error_msg = f"Error opening delete orphans dialog: {str(e)}" # v001.0012 added [delete left orphans button command]
            self.add_status_message(f"ERROR: {error_msg}") # v001.0012 added [delete left orphans button command]
            self.show_error(error_msg) # v001.0012 added [delete left orphans button command]
        finally: # v001.0012 added [delete left orphans button command]
            # Cleanup memory after dialog operations # v001.0012 added [delete left orphans button command]
            gc.collect() # v001.0012 added [delete left orphans button command]

    def delete_right_orphans(self): # v001.0012 added [delete right orphans button command]
        """Handle Delete RIGHT-only Orphaned Files button.""" # v001.0012 added [delete right orphans button command]
        if self.limit_exceeded: # v001.0012 added [delete right orphans button command]
            messagebox.showwarning("Operation Disabled", "Delete operations are disabled when file limits are exceeded.") # v001.0012 added [delete right orphans button command]
            return # v001.0012 added [delete right orphans button command]
            
        if not self.comparison_results: # v001.0012 added [delete right orphans button command]
            self.add_status_message("No comparison data available - please run comparison first") # v001.0012 added [delete right orphans button command]
            messagebox.showinfo("No Data", "Please perform a folder comparison first.") # v001.0012 added [delete right orphans button command]
            return # v001.0012 added [delete right orphans button command]
            
        # Get current filter if active # v001.0012 added [delete right orphans button command]
        active_filter = self.filter_wildcard.get() if self.is_filtered else None # v001.0012 added [delete right orphans button command]
        
        # Detect orphaned files on right side # v001.0012 added [delete right orphans button command]
        orphaned_files = DeleteOrphansManager_class.detect_orphaned_files(self.comparison_results, 'right', active_filter) # v001.0012 changed [use DeleteOrphansManager_class class method]
        
        if not orphaned_files: # v001.0012 added [delete right orphans button command]
            filter_text = f" (with active filter: {active_filter})" if active_filter else "" # v001.0012 added [delete right orphans button command]
            self.add_status_message(f"No orphaned files found on RIGHT side{filter_text}") # v001.0012 added [delete right orphans button command]
            messagebox.showinfo("No Orphans", f"No orphaned files found on RIGHT side{filter_text}.") # v001.0012 added [delete right orphans button command]
            return # v001.0012 added [delete right orphans button command]
            
        self.add_status_message(f"Opening delete orphans dialog for RIGHT side: {len(orphaned_files)} files") # v001.0012 added [delete right orphans button command]
        
        try: # v001.0012 added [delete right orphans button command]
            # Create and show delete orphans manager/dialog # v001.0012 added [delete right orphans button command]
            manager = DeleteOrphansManager_class( # v001.0012 changed [use DeleteOrphansManager_class instead of DeleteOrphansDialog]
                parent=self.root, # v001.0012 added [delete right orphans button command]
                orphaned_files=orphaned_files, # v001.0012 added [delete right orphans button command]
                side='right', # v001.0012 added [delete right orphans button command]
                source_folder=self.right_folder.get(), # v001.0012 added [delete right orphans button command]
                dry_run_mode=self.dry_run_mode.get(), # v001.0012 added [delete right orphans button command]
                comparison_results=self.comparison_results, # v001.0012 added [delete right orphans button command]
                active_filter=active_filter # v001.0012 added [delete right orphans button command]
            ) # v001.0012 added [delete right orphans button command]
            
            # Wait for dialog to complete # v001.0012 added [delete right orphans button command]
            self.root.wait_window(manager.dialog) # v001.0012 changed [use manager.dialog instead of dialog.dialog]
            
            # Check if files were actually deleted (not dry run) # v001.0012 added [delete right orphans button command]
            if hasattr(manager, 'result') and manager.result == 'deleted' and not self.dry_run_mode.get(): # v001.0012 changed [use manager instead of dialog]
                self.add_status_message("Delete operation completed - refreshing folder comparison...") # v001.0012 added [delete right orphans button command]
                # Refresh comparison to show updated state # v001.0012 added [delete right orphans button command]
                self.refresh_after_copy_operation() # v001.0012 added [delete right orphans button command]
            else: # v001.0012 added [delete right orphans button command]
                self.add_status_message("Delete orphans dialog closed") # v001.0012 added [delete right orphans button command]
                
        except Exception as e: # v001.0012 added [delete right orphans button command]
            error_msg = f"Error opening delete orphans dialog: {str(e)}" # v001.0012 added [delete right orphans button command]
            self.add_status_message(f"ERROR: {error_msg}") # v001.0012 added [delete right orphans button command]
            self.show_error(error_msg) # v001.0012 added [delete right orphans button command]
        finally: # v001.0012 added [delete right orphans button command]
            # Cleanup memory after dialog operations # v001.0012 added [delete right orphans button command]
            gc.collect() # v001.0012 added [delete right orphans button command]

    def setup_ui(self):
        """
        Initialize the user interface with features including dry run and export capabilities.
        
        Purpose:
        --------
        Creates and configures all GUI components including the new dry run checkbox,
        export functionality, and limit warnings for the application interface.
        """
        log_and_flush(logging.DEBUG, "Setting up FolderCompareSync_class user interface with features")
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3) # v001.0014 changed [tightened padding from pady=5 to pady=3]
        
        # Performance warning frame at top
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        warning_label = ttk.Label(
            warning_frame, 
            text=(
                f"⚠ Performance Notice: Large folder operations may be slow. "
                f"Maximum {MAX_FILES_FOLDERS:,} files/folders supported. "
                f"SHA512 operations will take circa 2 seconds elapsed per GB of file read."
            ),
            foreground="royalblue",
            style="Scaled.TLabel" # v001.0014 changed [use scaled label style instead of font]
        )
    
        warning_label.pack(side=tk.LEFT)
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        folder_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
    
        # Left folder selection
        ttk.Label(folder_frame, text="Left Folder:", style="Scaled.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 5)) # v001.0014 changed [use scaled label style]
        ttk.Button(folder_frame, text="Browse", command=self.browse_left_folder, style="DefaultNormal.TButton").grid(row=0, column=1, padx=(0, 5)) # v001.0016 changed [use default button style]
        left_entry = ttk.Entry(folder_frame, textvariable=self.left_folder, width=60, style="Scaled.TEntry") # v001.0014 changed [use scaled entry style]
        left_entry.grid(row=0, column=2, sticky=tk.EW)
        
        # Right folder selection
        ttk.Label(folder_frame, text="Right Folder:", style="Scaled.TLabel").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(3, 0)) # v001.0014 changed [use scaled label style and tightened padding from pady=(5, 0) to pady=(3, 0)]
        ttk.Button(folder_frame, text="Browse", command=self.browse_right_folder, style="DefaultNormal.TButton").grid(row=1, column=1, padx=(0, 5), pady=(3, 0)) # v001.0016 changed [use default button style and tightened padding from pady=(5, 0) to pady=(3, 0)]
        right_entry = ttk.Entry(folder_frame, textvariable=self.right_folder, width=60, style="Scaled.TEntry") # v001.0014 changed [use scaled entry style]
        right_entry.grid(row=1, column=2, sticky=tk.EW, pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
    
        # Let column 2 (the entry) grow
        folder_frame.columnconfigure(2, weight=1)
       
        # Comparison options frame with instructional text
        options_frame = ttk.LabelFrame(main_frame, text="Comparison Options", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        options_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Comparison criteria checkboxes with instructional text
        criteria_frame = ttk.Frame(options_frame)
        criteria_frame.pack(fill=tk.X)
        
        # Add instructional text for better user guidance using configurable styling
        instruction_frame = ttk.Frame(criteria_frame)
        instruction_frame.pack(fill=tk.X)
        
        ttk.Label(instruction_frame, text="Compare Options:", style="Scaled.TLabel").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled label style]
        ttk.Checkbutton(instruction_frame, text="Existence", variable=self.compare_existence, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        ttk.Checkbutton(instruction_frame, text="Size", variable=self.compare_size, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        ttk.Checkbutton(instruction_frame, text="Date Created", variable=self.compare_date_created, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        ttk.Checkbutton(instruction_frame, text="Date Modified", variable=self.compare_date_modified, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        ttk.Checkbutton(instruction_frame, text="SHA512", variable=self.compare_sha512, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        
        # Add instructional text for workflow guidance using configurable colors and font size
        ttk.Label(instruction_frame, text="<- select options then click Compare", 
                 foreground=INSTRUCTION_TEXT_COLOR, 
                 font=("TkDefaultFont", SCALED_INSTRUCTION_FONT_SIZE, "italic")).pack(side=tk.LEFT, padx=(20, 0))
        
        # Control frame - reorganized for better layout
        control_frame = ttk.Frame(options_frame)
        control_frame.pack(fill=tk.X, pady=(8, 0)) # v001.0014 changed [tightened padding from pady=(10, 0) to pady=(8, 0)]
        
        # Top row of controls with dry run support
        top_controls = ttk.Frame(control_frame)
        top_controls.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Dry run checkbox next to overwrite mode
        dry_run_cb = ttk.Checkbutton(top_controls, text="DRY RUN Only", variable=self.dry_run_mode, command=self.on_dry_run_changed, style="Scaled.TCheckbutton") # v001.0014 changed [use scaled checkbox style]
        dry_run_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Checkbutton(top_controls, text="Overwrite Mode", variable=self.overwrite_mode, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 20)) # v001.0014 changed [use scaled checkbox style]
        ttk.Button(top_controls, text="Compare", command=self.start_comparison, style="LimeGreenBold.TButton").pack(side=tk.LEFT, padx=(0, 20))
    
        # selection controls with auto-clear and complete reset functionality
        # Left pane selection controls
        ttk.Button(top_controls, text="Select All Differences - Left", 
                  command=self.select_all_differences_left, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(top_controls, text="Clear All - Left", 
                  command=self.clear_all_left, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 15)) # v001.0016 changed [use default button style]
        
        # Right pane selection controls  
        ttk.Button(top_controls, text="Select All Differences - Right", 
                  command=self.select_all_differences_right, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(top_controls, text="Clear All - Right", 
                  command=self.clear_all_right, style="DefaultNormal.TButton").pack(side=tk.LEFT) # v001.0016 changed [use default button style]
    
        # Filter and tree control frame
        filter_tree_frame = ttk.Frame(control_frame)
        filter_tree_frame.pack(fill=tk.X, pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
        
        # Wildcard filter controls
        ttk.Label(filter_tree_frame, text="Filter Files by Wildcard:", style="Scaled.TLabel").pack(side=tk.LEFT, padx=(0, 5)) # v001.0014 changed [use scaled label style]
        filter_entry = ttk.Entry(filter_tree_frame, textvariable=self.filter_wildcard, width=20, style="Scaled.TEntry") # v001.0014 changed [use scaled entry style]
        filter_entry.pack(side=tk.LEFT, padx=(0, 5))
        filter_entry.bind('<Return>', lambda e: self.apply_filter())
        
        ttk.Button(filter_tree_frame, text="Apply Filter", command=self.apply_filter, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(filter_tree_frame, text="Clear Filter", command=self.clear_filter, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 20)) # v001.0016 changed [use default button style]
        
        # Tree expansion controls
        ttk.Button(filter_tree_frame, text="Expand All", command=self.expand_all_trees, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(filter_tree_frame, text="Collapse All", command=self.collapse_all_trees, style="DefaultNormal.TButton").pack(side=tk.LEFT) # v001.0016 changed [use default button style]
        
        # Tree comparison frame (adjusted height to make room for status log)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Left tree with columns
        left_frame = ttk.LabelFrame(tree_frame, text="LEFT", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.left_tree = ttk.Treeview(left_frame, show='tree headings', selectmode='none')
        self.left_tree.heading('#0', text='Structure', anchor=tk.W)
        self.left_tree.column('#0', width=TREE_STRUCTURE_WIDTH, minwidth=TREE_STRUCTURE_MIN_WIDTH)
        
        # Configure columns for metadata display
        self.setup_tree_columns(self.left_tree)
        
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.left_tree.yview)
        self.left_tree.configure(yscrollcommand=left_scroll.set)
        self.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right tree with columns
        right_frame = ttk.LabelFrame(tree_frame, text="RIGHT", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self.right_tree = ttk.Treeview(right_frame, show='tree headings', selectmode='none')
        self.right_tree.heading('#0', text='Structure', anchor=tk.W)
        self.right_tree.column('#0', width=TREE_STRUCTURE_WIDTH, minwidth=TREE_STRUCTURE_MIN_WIDTH)
        
        self.setup_tree_columns(self.right_tree)
        
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_tree.yview)
        self.right_tree.configure(yscrollcommand=right_scroll.set)
        self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Synchronize scrolling between panes
        self.setup_synchronized_scrolling()
        
        # Copy buttons frame
        copy_frame = ttk.Frame(main_frame)
        copy_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        ttk.Button(copy_frame, text="Copy LEFT to Right", command=self.copy_left_to_right, style="RedBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Copy RIGHT to Left", command=self.copy_right_to_left, style="LimeGreenBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        delete_frame = ttk.Frame(main_frame)
        delete_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        ttk.Button(delete_frame, text="Delete LEFT-only Orphaned Files", 
                      command=self.delete_left_orphans, style="PurpleBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(delete_frame, text="Delete RIGHT-only Orphaned Files", 
                      command=self.delete_right_orphans, style="DarkGreenBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Quit", command=self.root.quit, style="BlueBold.TButton").pack(side=tk.RIGHT)
    
        # status log frame at bottom with export functionality
        status_log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding=5)
        status_log_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Status log header with export button
        status_header = ttk.Frame(status_log_frame)
        status_header.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        ttk.Label(status_header, text=f"Operation History ({STATUS_LOG_MAX_HISTORY:,} lines max):", 
                 style="Scaled.TLabel").pack(side=tk.LEFT) # v001.0014 changed [use scaled label style]
        ttk.Button(status_header, text="Export Log", command=self.export_status_log, style="DefaultNormal.TButton").pack(side=tk.RIGHT) # v001.0016 changed [use default button style]
        
        # Create text widget with scrollbar for status log using configurable parameters
        status_log_container = ttk.Frame(status_log_frame)
        status_log_container.pack(fill=tk.X)
        
        self.status_log_text = tk.Text(
            status_log_container, 
            height=STATUS_LOG_VISIBLE_LINES,  # Use configurable visible lines
            wrap=tk.WORD,
            state=tk.DISABLED,  # Read-only
            font=STATUS_LOG_FONT,    # v001.0016 changed [now uses SCALED_STATUS_MESSAGE_FONT_SIZE]
            bg=STATUS_LOG_BG_COLOR,  # Use configurable background color
            fg=STATUS_LOG_FG_COLOR   # Use configurable text color
        )
        
        status_log_scroll = ttk.Scrollbar(status_log_container, orient=tk.VERTICAL, command=self.status_log_text.yview)
        self.status_log_text.configure(yscrollcommand=status_log_scroll.set)
        
        self.status_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status and summary frame (moved to bottom, below status log)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        
        ttk.Label(status_frame, textvariable=self.summary_var, style="StatusMessage.TLabel").pack(side=tk.LEFT) # v001.0016 changed [use status message style for summary]
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        ttk.Label(status_frame, text="Status:", style="StatusMessage.TLabel").pack(side=tk.RIGHT, padx=(0, 5)) # v001.0016 changed [use status message style for status label]
        ttk.Label(status_frame, textvariable=self.status_var, style="StatusMessage.TLabel").pack(side=tk.RIGHT) # v001.0016 changed [use status message style for status]
        
        # Configure tree event bindings for interaction
        self.setup_tree_events()
        
        log_and_flush(logging.DEBUG, "FolderCompareSync_class User interface setup complete with features")

    def setup_tree_columns(self, tree): # v000.0002 changed - column sorting disabled
        """
        Setup columns for metadata display in tree (sorting disabled).
        
        Purpose:
        --------
        Configures tree view columns with proper sizing and alignment
        for comprehensive file metadata display. Column sorting has been
        disabled to maintain mandatory folder structure compliance.
        
        Args:
        -----
        tree: Treeview widget to configure
        """
        # columns to show all metadata regardless of compare settings
        tree['columns'] = ('size', 'date_created', 'date_modified', 'sha512', 'status')
        
        # v000.0002 changed - removed column sorting command bindings to restore mandatory compliance
        tree.heading('size', text='Size', anchor=tk.E)
        tree.heading('date_created', text='Date Created', anchor=tk.CENTER)
        tree.heading('date_modified', text='Date Modified', anchor=tk.CENTER)
        tree.heading('sha512', text='SHA512', anchor=tk.CENTER)
        tree.heading('status', text='Status', anchor=tk.W)
        
        # Use configurable column widths
        tree.column('size', width=TREE_SIZE_WIDTH, minwidth=TREE_SIZE_MIN_WIDTH, anchor=tk.E)
        tree.column('date_created', width=TREE_DATE_CREATED_WIDTH, minwidth=TREE_DATE_CREATED_MIN_WIDTH, anchor=tk.CENTER)
        tree.column('date_modified', width=TREE_DATE_MODIFIED_WIDTH, minwidth=TREE_DATE_MODIFIED_MIN_WIDTH, anchor=tk.CENTER)
        tree.column('sha512', width=TREE_SHA512_WIDTH, minwidth=TREE_SHA512_MIN_WIDTH, anchor=tk.CENTER)
        tree.column('status', width=TREE_STATUS_WIDTH, minwidth=TREE_STATUS_MIN_WIDTH, anchor=tk.W)

    def check_file_limit_exceeded(self, file_count: int, operation_name: str) -> bool:
        """
        Check if file count exceeds the configured limit and handle appropriately.
        
        Purpose:
        --------
        Provides early detection of file count limits to prevent performance issues
        and provides clear user guidance when limits are exceeded.
        
        Args:
        -----
        file_count: Current number of files/folders found
        operation_name: Name of the operation being performed
        
        Returns:
        --------
        bool: True if limit exceeded, False if within limits
        """
        if file_count > MAX_FILES_FOLDERS:
            self.limit_exceeded = True
            
            # Clear trees and data structures
            self.clear_all_data_structures()
            
            # Create bold error message
            error_msg = f"LIMIT EXCEEDED: Found {file_count:,} files/folders in {operation_name}"
            limit_msg = f"Maximum supported: {MAX_FILES_FOLDERS:,} files/folders"
            
            self.add_status_message(f"ERROR: {error_msg}")
            self.add_status_message(f"ERROR: {limit_msg}")
            self.add_status_message("SOLUTION: Use filtering to reduce dataset size, or work with smaller folders")
            self.add_status_message("NOTE: This limit prevents performance issues with large datasets")
            
            # Update status display
            self.status_var.set("LIMIT EXCEEDED - Operation Aborted")
            self.summary_var.set(f"ERROR: {error_msg}")
            
            # Show user dialog with detailed error
            detailed_error = (
                f"{error_msg}\n\n"
                f"{limit_msg}\n\n"
                f"To resolve this issue:\n"
                f"• Use filtering to work with specific file types\n"
                f"• Work with smaller subdirectories\n"
                f"• Consider organizing large datasets into manageable chunks\n\n"
                f"This limit prevents performance issues with very large datasets."
            )
            ErrorDetailsDialog(self.root, "File Limit Exceeded", error_msg, detailed_error)
            
            return True
        
        return False

    def clear_all_data_structures(self):
        """
        Clear all trees and data structures when limits are exceeded.
        
        Purpose:
        --------
        Provides clean reset of all application state when file limits
        are exceeded to ensure consistent application behavior.
        """
        # Clear trees
        if self.left_tree:
            for item in self.left_tree.get_children():
                self.left_tree.delete(item)
        if self.right_tree:
            for item in self.right_tree.get_children():
                self.right_tree.delete(item)
        
        # Clear data structures
        self.comparison_results.clear()
        self.filtered_results.clear()
        self.selected_left.clear()
        self.selected_right.clear()
        self.path_to_item_left.clear()
        self.path_to_item_right.clear()
        
        # Reset state variables
        self.root_item_left = None
        self.root_item_right = None
        self.is_filtered = False
        self.file_count_left = 0
        self.file_count_right = 0
        self.total_file_count = 0

                                                                                           
                                                                                   
                                                                             
        
                               
                                                                                                              
                                                                        
                  
            
                                                                         
                                                                                                                                
        
                                                                          
                                              
                                                                                           
                                                                                           
             
                                             
                                           
                                                                                                         
        
                       
                                                                                      
                                                              
                                               
                                                       
        
                                 
                                                                                                 
                                                                                                                                           
        
                                
                                                                  
                                                                
                                                                
                  
        
                                                      
                                                                                                      
                                                             
        
            
                                                          
                              
                    
                                                                                
                                                                  
                                                                                              
                                      
                                                                                  
                                    
                                                                                                 
                                                                                                 
                        
                                                                        
                                                      
            
                                                                         
                                                                     
            
                              
                            
                                                                                    
                            
                                                                                          
                                                             
        
                                                                       

    
       
                                        
    
                                                                         
                                                                                                                
                                                                                                       
                                                                             
                                                                                       
                                                                  
                 
                    
                              
                                           
                                           
                                           
                           
                                        
                                        
                                    
                                                                                        
                                                                  
                                                                                                   
                                                                       

                  
                                              
                                                          
                                                                    
                                                     

                         
                         
    
                                           
                                            
                                                        
                                                                    
    
                                         
                                      
                                                               
                                                                   
    
                                     
                                     
                                                             
                                                                    
    
                              
                             
                                                    
                                                                            
    
                     
                    
    
                                    
                                          
                                            
                                              
                              
    
                                   
                                                
                               
                                 
    
                                        
                                               
                                               
    
                                           
                                                        
                                          
    
                                       
                                                   
                                            
    
                                                 
                            
                              
    
                                        
                                           
                                                      
                                            
    
                        
                       
                                                              
                                                      
                                                           
                                       
                                                        
                                                        
                                                  
    
                                                                                     
                                                                
   

                                                                         
           
                                                        
        
                
                
                                                                             
           
                            
        
                                             
                                                                   
                                                 
                                                                
                                                                 
            
                                    
                                       
                                                    
                                                   
                                                                                                
            
                              
                                                    
                                              
        
                               
                                             
                                              
        
                                                                                          
                              
    
                                                                                             
           
                                                       
        
             
             
                                                        
                                                                       
           
                                                            
                          
        
                                                 
                                                     
                                   
            
                                                 
                                                                 
            
                                           
                                                          
                                                       
                                   
                                                                                                          
            
                              
                                                    
                                                  
        
                                               
                                             
                                                  
        
                                                                                                      
    
                                                                                   
                                                                                                        
           
                                                                      
        
             
             
                                                               
                                                                 
                                                           
                                                             
           
                                                                            
        
            
                                      
                                                               
                                                                                          
            
                                           
                                                                     
                                                                                    
                                                                                      
            
                                                                                   
            
                              
                                                                              
                            
                                                                                           


                                                                                                      
                                                                                  
                                                                                                                      
        
                                          
                                                                    
                                                                             
        
                                                                    
        
                                                        
                                                                                               
                                                                                                                              
        
                              
                                                                                             
                                                              
                  
            
                                                                 
        
                                                      
                                                                  
                                                                              
                                                                                
                                                                                                                                         
            
                                                                               
        
                                                                              
            
                                                                                              
                                                                     
                                                                             
             
                                                                                     
            
                                                                     
            
                                                             
                                       
                                        
            
                                              
                                                                       
                            
                                                     
                    
                                               
                                                                        
                            
                                                      
            
                                                                                                                          
            
                                                                    
                                                       
            
                                        
                                
                                                      
                                                              
                 
                                                        
                                                                
            
                                                 
                                
                                                                      
                                                                  
                 
                                                             
                                                              
            
                                                                        
            
                                                                 
                                                                      
                                                           
                                                           
              
                                                             
            
                                                                                                                              
                                                                             
                                                 
            
                              
                                                                                 
                            
                                                                                  
                                                                                                      
        
                                                                   
                                                                             

                                                                                                 
           
                                                                         
        
                
                
                                                                      
                                                                                 
        
             
             
                                                              
                                                                
                                                                
                                                    
        
                
                
                                                                      
           
                                                       
                                                  
            
                                                
                                                                                    
            
                                                                       
                                           
                                                                                        
            
                                                           
                                           
                                                                                          
            
                                                                                
                              
                                                                               
            
                
                                    
                                                                     
                                              
                                                                                                           
                                                               
                                               
                                                                                                             
                                                               
                                        
                                                                        
                                        
                                                                           
                                                             
                     
                                             
                                                         
                                               
                                                     
        
                                                           
                         
        
                               
                            
                                                     
                                         
                        
                
                                              
                                                   
                                                  
                                                                    
        
                                       
                           
        
                                          
                              
                                                 
        
                                              
                                                           
                                                       
            
                                                      
                          
                                                
                                                                                           
                                                
                                               
                                                                 
            
                                                  
                                                        
                                             
                           
                                               
                                                  
                 
                
                                                            
                                                     
        
                             
    
                                                                                                                                      
                                                         
                                                                         
        
            
                                      
                                      
                                       
                                                                         
            
                                     
                             
                                                
                                                                       
                           
                                                   
                                      
                                                                                           
                     
                                                                                                     
            
                                        
                              
                                                 
                                                                        
                           
                                                    
                                       
                                                                                            
                     
                                                                                                      
            
                                                                                                                 
            
                            
                                                                    
                                           
                                                                              
            
                              
                                                                                                
                            
                                                                                               

    def apply_filter(self):
        """Apply wildcard filter to display only matching files with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Filtering is disabled when file limits are exceeded.")
            return
            
        wildcard = self.filter_wildcard.get().strip()
        
        if not wildcard:
            self.add_status_message("No wildcard pattern specified")
            return
        
        if not self.comparison_results:
            self.add_status_message("No comparison data to filter - please run comparison first")
            return
        
        log_and_flush(logging.DEBUG, f"Applying wildcard filter: {wildcard}")
        self.add_status_message(f"Applying filter: {wildcard}")
        
        # Create progress dialog for filtering
        progress = ProgressDialog(self.root, "Filtering Files", f"Applying filter: {wildcard}...", max_value=100)
        
        try:
            # Use thread for filtering to keep UI responsive
            def filter_thread():
                try:
                    self.perform_filtering(wildcard, progress)
                except Exception as e:
                    log_and_flush(logging.ERROR, f"Filter operation failed: {e}")
                    self.root.after(0, lambda: self.add_status_message(f"Filter failed: {str(e)}"))
                finally:
                    self.root.after(0, progress.close)
            
            threading.Thread(target=filter_thread, daemon=True).start()
            
        except Exception as e:
            progress.close()
            log_and_flush(logging.ERROR, f"Failed to start filter operation: {e}")
            self.add_status_message(f"Filter failed: {str(e)}")

    def perform_filtering(self, wildcard, progress):
        """Perform the actual filtering operation with performance tracking."""
        log_and_flush(logging.DEBUG, f"Performing filtering with pattern: {wildcard}")
        
        progress.update_progress(10, "Preparing filter...")
        
        # Filter comparison results based on wildcard (files only, not folders)
        self.filtered_results = {}
        matched_count = 0
        total_items = len(self.comparison_results)
        
        progress.update_progress(30, "Filtering files...")
        
        for rel_path, result in self.comparison_results.items():
            if rel_path:  # Skip empty paths
                filename = rel_path.split('/')[-1]  # Get just the filename
                
                # Only filter files, not folders
                is_file = ((result.left_item and not result.left_item.is_folder) or 
                          (result.right_item and not result.right_item.is_folder))
                
                if is_file and fnmatch.fnmatch(filename.lower(), wildcard.lower()):
                    self.filtered_results[rel_path] = result
                    matched_count += 1
                    
                    # Limit results for performance using configurable threshold
                    if matched_count >= MAX_FILTER_RESULTS:
                        log_and_flush(logging.WARNING, f"Filter results limited to {MAX_FILTER_RESULTS} items for performance")
                        break
        
        progress.update_progress(70, f"Found {matched_count} matches, updating display...")
        
        # Update tree display with filtered results
        self.is_filtered = True
        
        # Rebuild trees with filtered results
        self.root.after(0, lambda: self.update_comparison_ui_filtered())
        
        # Update status
        filter_summary = f"Filter applied: {matched_count:,} files match '{wildcard}'"
        if matched_count >= MAX_FILTER_RESULTS:
            filter_summary += f" (limited to {MAX_FILTER_RESULTS:,} for performance)"
        
        progress.update_progress(100, "Filter complete")
        self.root.after(0, lambda: self.add_status_message(filter_summary))

    def clear_filter(self):
        """Clear the wildcard filter and show all results with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Filter operations are disabled when file limits are exceeded.")
            return
            
        log_and_flush(logging.DEBUG, "Clearing wildcard filter")
        
        self.filter_wildcard.set("")
        self.filtered_results = {}
        self.is_filtered = False
        
        self.add_status_message("Filter cleared - showing all results")
        
        # Rebuild trees with all results
        if self.comparison_results:
            self.update_comparison_ui()

    def expand_all_trees(self):
        """Expand all items in both trees with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Tree operations are disabled when file limits are exceeded.")
            return
            
        log_and_flush(logging.DEBUG, "Expanding all tree items")
        self.add_status_message("Expanding all folders")
        
        def expand_all_recursive(tree, item=''):
            """Recursively expand all items"""
            children = tree.get_children(item)
            for child in children:
                tree.item(child, open=True)
                expand_all_recursive(tree, child)
        
        # Expand both trees
        expand_all_recursive(self.left_tree)
        expand_all_recursive(self.right_tree)
        
        self.add_status_message("All folders expanded")

    def collapse_all_trees(self):
        """Collapse all items in both trees with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Tree operations are disabled when file limits are exceeded.")
            return
            
        log_and_flush(logging.DEBUG, "Collapsing all tree items")
        self.add_status_message("Collapsing all folders")
        
        def collapse_all_recursive(tree, item=''):
            """Recursively collapse all items"""
            children = tree.get_children(item)
            for child in children:
                tree.item(child, open=False)
                collapse_all_recursive(tree, child)
        
        # Collapse both trees (but keep root expanded)
        for child in self.left_tree.get_children():
            self.left_tree.item(child, open=False)
            collapse_all_recursive(self.left_tree, child)
            
        for child in self.right_tree.get_children():
            self.right_tree.item(child, open=False)
            collapse_all_recursive(self.right_tree, child)
        
        self.add_status_message("All folders collapsed")

    def setup_synchronized_scrolling(self):
        """Setup synchronized scrolling between tree views."""
        def sync_yview(*args):
            self.left_tree.yview(*args)
            self.right_tree.yview(*args)
        
        # Create a shared scrollbar command for synchronized scrolling
        self.left_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.right_tree, *args))
        self.right_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.left_tree, *args))
        
    def sync_scrollbar(self, other_tree, *args):
        """Synchronize scrollbar between trees."""
        # Update both trees' scroll position for synchronized viewing
        self.left_tree.yview_moveto(args[0])
        self.right_tree.yview_moveto(args[0])
        
    def setup_tree_events(self):
        """
        Setup event bindings for tree interactions with limit checking.
        
        Purpose:
        --------
        Configures mouse and keyboard event handling for tree widgets
        while respecting file count limits for performance.
        """
        log_and_flush(logging.DEBUG, "Setting up tree event bindings")
        
        # Bind tree expansion/collapse events with state preservation
        self.left_tree.bind('<<TreeviewOpen>>', lambda e: self.handle_tree_expand_collapse(self.left_tree, self.right_tree, e, True))
        self.left_tree.bind('<<TreeviewClose>>', lambda e: self.handle_tree_expand_collapse(self.left_tree, self.right_tree, e, False))
        self.right_tree.bind('<<TreeviewOpen>>', lambda e: self.handle_tree_expand_collapse(self.right_tree, self.left_tree, e, True))
        self.right_tree.bind('<<TreeviewClose>>', lambda e: self.handle_tree_expand_collapse(self.right_tree, self.left_tree, e, False))
        
        # Bind checkbox-like behavior for item selection (with missing item exclusion)
        self.left_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.left_tree, 'left', e))
        self.right_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.right_tree, 'right', e))
        
    def handle_tree_expand_collapse(self, source_tree, target_tree, event, is_expand):
        """
        Handle tree expansion/collapse with proper state preservation and limit checking.
        
        Purpose:
        --------
        Ensures selection state is maintained during expand/collapse operations
        while respecting performance limits.
        """
        if self._updating_display or self.limit_exceeded:
            return  # Prevent recursive updates or operations when limits exceeded
            
        item = source_tree.selection()[0] if source_tree.selection() else source_tree.focus()
        if item:
            try:
                # Synchronize expand/collapse state with other tree
                target_tree.item(item, open=is_expand)
                
                if __debug__:
                    action = "expand" if is_expand else "collapse"
                    log_and_flush(logging.DEBUG, f"Synchronized tree {action} for item {item}")
                    
            except tk.TclError:
                pass  # Item doesn't exist in target tree
                
            # CRITICAL: Do NOT call update_tree_display() here as it interferes with selection state
            # Selection state should remain completely independent of expand/collapse operations
                
    def is_missing_item(self, tree, item_id):
        """
        Check if an item is a missing item (has [MISSING] in text or 'missing' tag).
        
        Purpose:
        --------
        Helper function to identify non-clickable missing items for proper
        user interaction handling and UI consistency.
        
        Args:
        -----
        tree: Tree widget containing the item
        item_id: ID of the item to check
        
        Returns:
        --------
        bool: True if item is missing, False otherwise
        """
        if not item_id:
            return False
            
        item_text = tree.item(item_id, 'text')
        item_tags = tree.item(item_id, 'tags')
        
        # Check if item is marked as missing
        is_missing = '[MISSING]' in item_text or 'missing' in item_tags
        
        if __debug__ and is_missing:
            log_and_flush(logging.DEBUG, f"Identified missing item: {item_id} with text: {item_text}")
            
        return is_missing
        
    def is_different_item(self, item_id, side):
        """
        Check if an item represents a different file/folder that needs syncing.
        
        Purpose:
        --------
        Used for smart folder selection logic to identify items that
        have differences and should be included in copy operations.
        
        Args:
        -----
        item_id: Tree item ID to check
        side: Which tree side ('left' or 'right')
        
        Returns:
        --------
        bool: True if item is different and exists, False otherwise
        """
        if not item_id:
            return False
            
        # Get the relative path for this item
        rel_path = self.get_item_relative_path(item_id, side)
        if not rel_path:
            return False
            
        # Check in appropriate results set (filtered or full)
        results = self.filtered_results if self.is_filtered else self.comparison_results
        result = results.get(rel_path)
        
        if result and result.is_different:
            # Also ensure the item exists on this side
            item_exists = False
            if side == 'left' and result.left_item and result.left_item.exists:
                item_exists = True
            elif side == 'right' and result.right_item and result.right_item.exists:
                item_exists = True
                
            if __debug__ and item_exists:
                log_and_flush(logging.DEBUG, f"Item {item_id} ({rel_path}) is different and exists on {side} side")
                
            return item_exists
            
        return False
        
    def get_item_relative_path(self, item_id, side):
        """
        Get the relative path for a tree item by looking it up in path mappings.
        
        Purpose:
        --------
        More efficient than reconstructing from tree hierarchy,
        provides fast lookup for tree item paths.
        
        Args:
        -----
        item_id: Tree item ID
        side: Which tree side ('left' or 'right')
        
        Returns:
        --------
        str: Relative path or None if not found
        """
        path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
        
        # Find the relative path by searching the mapping
        for rel_path, mapped_item_id in path_map.items():
            if mapped_item_id == item_id:
                return rel_path
                
        return None
                
    def handle_tree_click(self, tree, side, event):
        """
        Handle clicks on tree items (for checkbox behavior) with limit checking.
        
        Purpose:
        --------
        Processes user clicks on tree items to toggle selection state
        while ignoring clicks on missing items and respecting limits.
        """
        if self.limit_exceeded:
            return  # Don't process clicks when limits exceeded

        # Ignore clicks on the +/- indicator (expand/collapse control) and column headers/separators
        element = tree.identify('element', event.x, event.y)
        region  = tree.identify('region',  event.x, event.y)
        if element == 'Treeitem.indicator' or region in ('heading', 'separator'):
            return
            
        item = tree.identify('item', event.x, event.y)
        if item:
            # Check if item is missing and ignore clicks on missing items
            if self.is_missing_item(tree, item):
                if __debug__:
                    log_and_flush(logging.DEBUG, f"Ignoring click on missing item: {item}")
                return  # Don't process clicks on missing items
                
            # Toggle selection for this item if it's not missing
            self.toggle_item_selection(item, side)
            
    def toggle_item_selection(self, item_id, side):
        """Toggle selection state of an item and handle parent/child logic with root safety."""
        if self.limit_exceeded:
            return  # Don't process selections when limits exceeded
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Toggling selection for item {item_id} on {side} side")
            
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        was_selected = item_id in selected_set
        
        if item_id in selected_set:
            # Unticking - remove from selection and untick all parents and children
            selected_set.discard(item_id)
            # unticking with root safety check
            self.untick_parents_with_root_safety(item_id, side)
            self.untick_children(item_id, side)
        else:
            # Ticking - add to selection and tick all children (only different ones)
            selected_set.add(item_id)
            self.tick_children_smart(item_id, side)
            
        if __debug__:
            action = "unticked" if was_selected else "ticked"
            log_and_flush(logging.DEBUG, f"Item {action}, {side} selection count: {len(selected_set)}")
            
        # Log selection changes to status window
        total_selected = len(self.selected_left) + len(self.selected_right)
        action_word = "Deselected" if was_selected else "Selected"
        rel_path = self.get_item_relative_path(item_id, side) or "item"
        self.add_status_message(f"{action_word} {rel_path} ({side}) - Total selected: {total_selected}")
            
        self.update_tree_display_safe()
        self.update_summary()
        
    def tick_children_smart(self, item_id, side):
        """
        Smart tick children - only select different items underneath.
        
        Purpose:
        --------
        Implements intelligent folder selection logic that only selects
        child items that have actual differences requiring synchronization.
        """
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Smart ticking children for {item_id} - only selecting different items")
        
        different_count = 0
        total_count = 0
        
        def tick_recursive(item):
            nonlocal different_count, total_count
            total_count += 1
            
            # Only tick if item is not missing AND is different
            if not self.is_missing_item(tree, item) and self.is_different_item(item, side):
                selected_set.add(item)
                different_count += 1
                if __debug__:
                    rel_path = self.get_item_relative_path(item, side)
                    log_and_flush(logging.DEBUG, f"Smart-selected different item: {item} ({rel_path})")
                    
            # Recursively process children
            for child in tree.get_children(item):
                tick_recursive(child)
                
        # Process all children of the ticked item
        for child in tree.get_children(item_id):
            tick_recursive(child)
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Smart selection complete: {different_count}/{total_count} children selected (only different items)")
            
        # Log smart selection results
        if different_count > 0:
            folder_path = self.get_item_relative_path(item_id, side) or "folder"
            self.add_status_message(f"Smart-selected {different_count} different items in {folder_path} ({side})")
            
    def untick_children(self, item_id, side):
        """Untick all children of an item recursively."""
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        def untick_recursive(item):
            selected_set.discard(item)
            for child in tree.get_children(item):
                untick_recursive(child)
                
        for child in tree.get_children(item_id):
            untick_recursive(child)
            
    def untick_parents_with_root_safety(self, item_id, side):
        """
        Untick all parents of an item with safety check for root level.
        
        Purpose:
        --------
        Also prevent attempting to untick parents of root items
        which can cause errors and inconsistent selection state.
        """
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        root_item = self.root_item_left if side == 'left' else self.root_item_right
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Unticking parents for item {item_id}, root_item: {root_item}")
        
        parent = tree.parent(item_id)
        while parent:
            selected_set.discard(parent)
            if __debug__:
                log_and_flush(logging.DEBUG, f"Unticked parent: {parent}")
            
            # Safety check - if we've reached the root item, stop here
            # Don't try to untick the parent of the root item as it doesn't exist
            if parent == root_item:
                if __debug__:
                    log_and_flush(logging.DEBUG, f"Reached root item {root_item}, stopping parent unticking")
                break
                
            next_parent = tree.parent(parent)
            if not next_parent:  # Additional safety check for empty parent
                if __debug__:
                    log_and_flush(logging.DEBUG, f"No parent found for {parent}, stopping parent unticking")
                break
            parent = next_parent
            
    def update_tree_display_safe(self):
        """
        Safe tree display update that preserves selection state and respects limits.
        
        Purpose:
        --------
        Prevents recursive updates during expand/collapse operations
        and ensures consistent behavior when file limits are exceeded.
        """
        if self._updating_display or self.limit_exceeded:
            if __debug__:
                log_and_flush(logging.DEBUG, "Skipping tree display update - already updating or limits exceeded")
            return
            
        self._updating_display = True
        try:
            self.update_tree_display()
        finally:
            self._updating_display = False
            
    def update_tree_display(self):
        """Update tree display to show selection state (only for non-missing items)."""
        # Update left tree
        for item in self.left_tree.get_children():
            self.update_item_display(self.left_tree, item, 'left')
            
        # Update right tree  
        for item in self.right_tree.get_children():
            self.update_item_display(self.right_tree, item, 'right')
            
    def update_item_display(self, tree, item, side, recursive=True):
        """
        Update display of a single item and optionally its children.
        
        Purpose:
        --------
        Only updates checkbox display for non-missing items
        to maintain consistent visual representation of selectable items.
        """
        selected_set = self.selected_left if side == 'left' else self.selected_right
        
        # Get current text 
        current_text = tree.item(item, 'text')
        
        # Skip updating missing items (they shouldn't have checkboxes)
        if self.is_missing_item(tree, item):
            if recursive:
                for child in tree.get_children(item):
                    self.update_item_display(tree, child, side, True)
            return
        
        # Remove existing checkbox indicators for non-missing items
        if current_text.startswith('☑ ') or current_text.startswith('☐ '):
            current_text = current_text[2:]
            
        # Add checkbox indicator based on selection state
        if item in selected_set:
            new_text = '☑ ' + current_text
        else:
            new_text = '☐ ' + current_text
            
        tree.item(item, text=new_text)
        
        if recursive:
            for child in tree.get_children(item):
                self.update_item_display(tree, child, side, True)
                
    def browse_left_folder(self):
        """Browse for left folder with limit awareness."""
        log_and_flush(logging.DEBUG, "Opening left folder browser")
        folder = filedialog.askdirectory(title="Select Left Folder")
        if folder:
            self.left_folder.set(folder)
            self.add_status_message(f"Selected left folder: {folder}")
            log_and_flush(logging.INFO, f"Selected left folder: {folder}")
            
    def browse_right_folder(self):
        """Browse for right folder with limit awareness."""
        log_and_flush(logging.DEBUG, "Opening right folder browser")
        folder = filedialog.askdirectory(title="Select Right Folder")
        if folder:
            self.right_folder.set(folder)
            self.add_status_message(f"Selected right folder: {folder}")
            log_and_flush(logging.INFO, f"Selected right folder: {folder}")
            
    def start_comparison(self): # v000.0002 changed - removed sorting state reset
        """Start folder comparison in background thread with limit checking and complete reset."""
        log_and_flush(logging.INFO, "Starting folder comparison with complete reset")
        
        if not self.left_folder.get() or not self.right_folder.get():
            error_msg = "Both folders must be selected before comparison"
            log_and_flush(logging.ERROR, f"Comparison failed: {error_msg}")
            self.add_status_message(f"Error: {error_msg}")
            self.show_error("Please select both folders to compare")
            return
            
        if not Path(self.left_folder.get()).exists():
            error_msg = f"Left folder does not exist: {self.left_folder.get()}"
            log_and_flush(logging.ERROR, error_msg)
            self.add_status_message(f"Error: {error_msg}")
            self.show_error(error_msg)
            return
            
        if not Path(self.right_folder.get()).exists():
            error_msg = f"Right folder does not exist: {self.right_folder.get()}"
            log_and_flush(logging.ERROR, error_msg)
            self.add_status_message(f"Error: {error_msg}")
            self.show_error(error_msg)
            return
        
        # Reset application state for fresh comparison # v000.0002 changed - removed sorting
        self.limit_exceeded = False
                                                             
                                                             
        
        # Log the reset
        self.add_status_message("RESET: Clearing all data structures for fresh comparison") # v000.0002 changed - removed sorting
        log_and_flush(logging.INFO, "Complete application reset initiated - clearing all data") # v000.0002 changed - removed sorting
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Left folder: {self.left_folder.get()}")
            log_and_flush(logging.DEBUG, f"Right folder: {self.right_folder.get()}")
            log_and_flush(logging.DEBUG, f"Compare criteria: existence={self.compare_existence.get()}, "
                        f"size={self.compare_size.get()}, "
                        f"date_created={self.compare_date_created.get()}, "
                        f"date_modified={self.compare_date_modified.get()}, "
                        f"sha512={self.compare_sha512.get()}")
                                                                        
            
        # Start comparison in background thread
        self.status_var.set("Comparing folders...")
        self.add_status_message("Starting fresh folder comparison...") # v000.0002 changed - removed sorting
        log_and_flush(logging.INFO, "Starting background comparison thread with reset state")
        threading.Thread(target=self.perform_comparison, daemon=True).start()

    def perform_comparison(self):
        """
        Perform the actual folder comparison with progress tracking and limit checking.
        
        Purpose:
        --------
        Orchestrates the complete comparison process including scanning, comparison,
        and UI updates while enforcing file count limits for performance management.
        """
        start_time = time.time()
        log_and_flush(logging.INFO, "Beginning folder comparison operation")
        
        # Create progress dialog for the overall comparison process
        progress = ProgressDialog(
            self.root, 
            "Comparing Folders", 
            "Preparing comparison...",
            max_value=100  # We'll estimate progress as percentage
        )
        
        try:
            # Clear previous results and reset state
            self.comparison_results.clear()
            self.filtered_results.clear()
            self.is_filtered = False
            self.selected_left.clear()
            self.selected_right.clear()
            self.path_to_item_left.clear()
            self.path_to_item_right.clear()
            self.root_item_left = None
            self.root_item_right = None
            self.file_count_left = 0
            self.file_count_right = 0
            self.total_file_count = 0
            
            if __debug__:
                log_and_flush(logging.DEBUG, "Cleared previous comparison results and reset root items")
            
            # Step 1: Build file lists for both folders (40% of total work) with early limit checking
            progress.update_progress(5, "Scanning left folder...")
            self.root.after(0, lambda: self.add_status_message("Scanning left folder for files and folders..."))
            
            left_files = self.build_file_list_with_progress(self.left_folder.get(), progress, 5, 25)
            
            if left_files is None:  # Limit exceeded during left scan
                return
            
            file_count_left = len(left_files)
            self.file_count_left = file_count_left
            
            self.root.after(0, lambda: self.add_status_message(f"Left folder scan complete: {file_count_left:,} items found"))
            log_and_flush(logging.INFO, f"Found {file_count_left} items in left folder")
            
            progress.update_progress(30, "Scanning right folder...")
            self.root.after(0, lambda: self.add_status_message("Scanning right folder for files and folders..."))
            
            right_files = self.build_file_list_with_progress(self.right_folder.get(), progress, 30, 50)
            
            if right_files is None:  # Limit exceeded during right scan
                return
                
            file_count_right = len(right_files)
            self.file_count_right = file_count_right
            
            # Check combined file count limit
            self.total_file_count = file_count_left + file_count_right
            if self.check_file_limit_exceeded(self.total_file_count, "combined folders"):
                return
            
            self.root.after(0, lambda: self.add_status_message(f"Right folder scan complete: {file_count_right:,} items found"))
            log_and_flush(logging.INFO, f"Found {file_count_right} items in right folder")
            
            # Step 2: Compare files (50% of total work)
            progress.update_progress(50, "Comparing files and folders...")
            self.root.after(0, lambda: self.add_status_message("Comparing files and folders for differences..."))
            
            # Get all unique relative paths
            all_paths = set(left_files.keys()) | set(right_files.keys())
            total_paths = len(all_paths)
            log_and_flush(logging.INFO, f"Comparing {total_paths} unique paths")
            
            if __debug__:
                log_and_flush(logging.DEBUG, f"Left-only paths: {len(left_files.keys() - right_files.keys())}")
                log_and_flush(logging.DEBUG, f"Right-only paths: {len(right_files.keys() - left_files.keys())}")
                log_and_flush(logging.DEBUG, f"Common paths: {len(left_files.keys() & right_files.keys())}")
            
            # Compare each path with progress updates using configurable frequency
            differences_found = 0
            for i, rel_path in enumerate(all_paths):
                # Update progress using configurable frequency settings
                if i % max(1, total_paths // PROGRESS_PERCENTAGE_FREQUENCY) == 0 or i % COMPARISON_PROGRESS_BATCH == 0:
                    comparison_progress = 50 + int((i / total_paths) * 40)  # 40% of work for comparison
                    progress.update_progress(comparison_progress, f"Comparing... {i+1:,} of {total_paths:,}")
                
                left_item = left_files.get(rel_path)
                right_item = right_files.get(rel_path)
                
                differences = self.compare_items(left_item, right_item)
                
                self.comparison_results[rel_path] = ComparisonResult_class(
                    left_item=left_item,
                    right_item=right_item,
                    differences=differences
                )
                
                if differences:
                    differences_found += 1
                    if __debug__:
                        log_and_flush(logging.DEBUG, f"Difference found in '{rel_path}': {differences}")
            
            # Step 3: Update UI (10% of total work)
            progress.update_progress(90, "Building comparison trees...")
            self.root.after(0, lambda: self.add_status_message("Building comparison tree views..."))
            
            elapsed_time = time.time() - start_time
            log_and_flush(logging.INFO, f"Comparison completed in {elapsed_time:.2f} seconds")
            log_and_flush(logging.INFO, f"Found {differences_found} items with differences")
            
            # Update UI in main thread
            progress.update_progress(100, "Finalizing...")
            self.root.after(0, self.update_comparison_ui)
            
            # Add completion status message with file counts
            self.root.after(0, lambda: self.add_status_message(
                f"Comparison complete: {differences_found:,} differences found in {elapsed_time:.1f} seconds"
            ))
            self.root.after(0, lambda: self.add_status_message(
                f"Total files processed: {self.total_file_count:,} (Left: {self.file_count_left:,}, Right: {self.file_count_right:,})"
            ))
            
        except Exception as e:
            log_and_flush(logging.ERROR, f"Comparison failed with exception: {type(e).__name__}: {str(e)}")
            if __debug__:
                import traceback
                log_and_flush(logging.DEBUG, "Full exception traceback:")
                log_and_flush(logging.DEBUG, traceback.format_exc())
            
            error_msg = f"Comparison failed: {str(e)}"
            self.root.after(0, lambda: self.add_status_message(f"Error: {error_msg}"))
            self.root.after(0, lambda: self.show_error(error_msg))
        finally:
            # Always close the progress dialog
            progress.close()
            
    def build_file_list_with_progress(self, root_path: str, progress: ProgressDialog, 
                                    start_percent: int, end_percent: int) -> Optional[Dict[str, FileMetadata_class]]:
        """
        Build a dictionary of relative_path -> FileMetadata with progress tracking and early limit checking.
        
        Purpose:
        --------
        Scans directory structure while monitoring file count limits to prevent
        performance issues with very large datasets, providing early abort capability.
        
        Args:
        -----
        root_path: Root directory to scan
        progress: Progress dialog to update
        start_percent: Starting percentage for this operation
        end_percent: Ending percentage for this operation
        
        Returns:
        --------
        Dict[str, FileMetadata_class] or None: File metadata dict or None if limit exceeded
        """
        if __debug__:
            log_and_flush(logging.DEBUG, f"Building file list with progress for: {root_path}")
        
        assert Path(root_path).exists(), f"Root path must exist: {root_path}"
        
        files = {}
        root = Path(root_path)
        file_count = 0
        dir_count = 0
        error_count = 0
        items_processed = 0
        
        try:
            # Use memory-efficient processing for large folders
            total_items = 0
            if len(list(root.iterdir())) < MEMORY_EFFICIENT_THRESHOLD:
                # For smaller folders, count total items first for better progress tracking
                total_items = sum(1 for _ in root.rglob('*'))
            else:
                # For larger folders, use estimated progress
                total_items = MEMORY_EFFICIENT_THRESHOLD  # Use threshold as estimate
                
            # Include the root directory itself if it's empty
            if not any(root.iterdir()):
                if __debug__:
                    log_and_flush(logging.DEBUG, f"Root directory is empty: {root_path}")
                
            for path in root.rglob('*'):
                try:
                    items_processed += 1
                    
                    # Early limit checking during scanning
                    if items_processed > MAX_FILES_FOLDERS:
                        folder_name = os.path.basename(root_path)
                        if self.check_file_limit_exceeded(items_processed, f"'{folder_name}' folder"):
                            return None  # Return None to indicate limit exceeded
                    
                    # Update progress using configurable intervals for optimal performance
                    if items_processed % max(1, min(SCAN_PROGRESS_UPDATE_INTERVAL, total_items // 20)) == 0:
                        current_percent = start_percent + int(((items_processed / total_items) * (end_percent - start_percent)))
                        progress.update_progress(current_percent, f"Scanning... {items_processed:,} items found")
                    
                    rel_path = path.relative_to(root).as_posix()
                    
                    # v000.0004 added - handle SHA512 computation with progress at scanning level for better separation.
					#                   Yes that's a trade-off for a clean FileMetadata_class ... so be it.
                    #                   Even though all other metadata is calculated by "FileMetadata_class.from_path"
					#                   we remove the sha512 computation to here so as to be able to display progress here
					#                   since the FileMetadata_class must not interact with the UI.
					#                   Note that FileMetadata_class.from_path can still compute the hash if compute_hash=False,
					#                   however that does not update the UI with progress.
					#                   Put compute_sha512_with_progress() underneath this def at the same level
					#                   
                    sha512_hash = None
                    if self.compare_sha512.get() and path.is_file():
                        try:
                            size = path.stat().st_size
                            if size > SHA512_STATUS_MESSAGE_THRESHOLD:
                                # Large files: Use separate SHA512 computation utility function for progress tracking # v000.0004 added
                                log_and_flush(logging.DEBUG, f"Large file: Performing SHA512 computation via compute_sha512_with_progress() for {path}")
                                sha512_hash = self.compute_sha512_with_progress(str(path), progress)
                            else:
                                # Small files: compute directly without progress overhead # v000.0004 added
                                log_and_flush(logging.DEBUG, f"Small file: Performing SHA512 computation locally in build_file_list_with_progress() for {path}")
                                if size < SHA512_MAX_FILE_SIZE:
                                    hasher = hashlib.sha512()
                                    with open(str(path), 'rb') as f:
                                        hasher.update(f.read())
                                    sha512_hash = hasher.hexdigest()
                        except Exception as e:
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"SHA512 computation failed for {path}: {e}")
                    
                    # v000.0004 NOTE: Create metadata without SHA512 computation (since SHA512 computation already handled above) # v000.0004 changed
                    metadata = FileMetadata_class.from_path(str(path), compute_hash=False)
                    
                    # v000.0004 added - manually (re)set SHA512 if we computed it at scanning level
                    if sha512_hash:
                        metadata.sha512 = sha512_hash
                    
                    files[rel_path] = metadata
                    
                    if path.is_file():
                        file_count += 1
                    else:
                        dir_count += 1
                        
                except Exception as e:
                    error_count += 1
                    if __debug__:
                        log_and_flush(logging.DEBUG, f"Skipping file due to error: {path} - {e}")
                    continue  # Skip files we can't process
                    
            # Also scan for empty directories that might not be caught by rglob('*')
            for path in root.rglob(''):  # This gets all directories
                try:
                    if path.is_dir() and path != root:
                        rel_path = path.relative_to(root).as_posix()
                        if rel_path not in files:  # Only add if not already added
                            metadata = FileMetadata_class.from_path(str(path), compute_hash=False)  # Directories don't need SHA512
                            files[rel_path] = metadata
                            dir_count += 1
                            
                            # Check limit for directories too
                            if len(files) > MAX_FILES_FOLDERS:
                                folder_name = os.path.basename(root_path)
                                if self.check_file_limit_exceeded(len(files), f"'{folder_name}' folder"):
                                    return None
                                    
                except Exception as e:
                    error_count += 1
                    if __debug__:
                        log_and_flush(logging.DEBUG, f"Skipping directory due to error: {path} - {e}")
                    continue
                    
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error scanning directory {root_path}: {e}")
            if __debug__:
                import traceback
                log_and_flush(logging.DEBUG, traceback.format_exc())
            
        log_and_flush(logging.INFO, f"Scanned {root_path}: {file_count} files, {dir_count} directories, {error_count} errors")
        if __debug__:
            log_and_flush(logging.DEBUG, f"Total items found: {len(files)}")
            
        return files

    def compute_sha512_with_progress(self, file_path: str, progress_dialog: ProgressDialog) -> Optional[str]: # v000.0004 added - separated SHA512 computation with progress tracking
        """
        Compute SHA512 hash for a file with progress tracking in the UI every ~50MB.
        
        Purpose:
        --------
        Provides SHA512 computation with user progress feedback for large files,
        maintaining separation of UI updating concerns from the metadata creation only in class FileMetadata_class.
        
        Args:
        -----
        file_path: Path to the file to hash
        progress_dialog: Progress dialog for user feedback
        
        Returns:
        --------
        str: SHA512 hash as hexadecimal string, or None if computation failed
        
        Usage:
        ------
        hash_value = compute_sha512_with_progress("/path/to/large_file.dat", progress)
        """
        try:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                log_and_flush(logging.DEBUG, f"In compute_sha512_with_progress() ... returning None ... not path.exists() or not path.is_file() for {file_path}")
                return None
                
            size = path.stat().st_size
            if size >= SHA512_MAX_FILE_SIZE:  # v000.0004 respect configurable limit
                if __debug__:
                    log_and_flush(logging.DEBUG, f"In compute_sha512_with_progress() File too large for SHA512 computation: {size} bytes > {SHA512_MAX_FILE_SIZE} bytes")
                return None
            
            hasher = hashlib.sha512()
            
            # v000.0004 progress tracking variables
            bytes_processed = 0
            chunk_count = 0
            
            # v000.0004 Show initial progress message for large files
            if size > SHA512_STATUS_MESSAGE_THRESHOLD:
                size_mb = size / (1024 * 1024)
                progress_dialog.update_message(f"Computing SHA512 for {path.name} ({size_mb} MB)...\n(computed 0 MB of {size_mb} MB)")
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):  # v000.0004 8MB chunks
                    hasher.update(chunk)
                    bytes_processed += len(chunk) # v000.0004
                    chunk_count += 1 # v000.0004
                    
                    # v000.0004 update progress every ~6 chunks (48MB) for large files
                    if size > SHA512_STATUS_MESSAGE_THRESHOLD:
                        if chunk_count % 6 == 0 or bytes_processed >= size:  # Update every ~50MB
                            processed_mb = bytes_processed / (1024 * 1024)
                            total_mb = size / (1024 * 1024)
                            progress_dialog.update_message(f"Computing SHA512 for {path.name} ({total_mb:.1f} MB)...\n(computed {processed_mb} MB of {total_mb} MB)")
            
            return hasher.hexdigest() # v000.0004
            
        except Exception as e:
            if __debug__:
                log_and_flush(logging.DEBUG, f"In compute_sha512_with_progress() SHA512 computation failed for {file_path}: {e}")
            return None  # v000.0004 hash computation failed
        
    def compare_items(self, left_item: Optional[FileMetadata_class], 
                     right_item: Optional[FileMetadata_class]) -> Set[str]:
        """
        Compare two items and return set of differences.
        
        Purpose:
        --------
        Performs detailed comparison of file/folder metadata based on
        selected comparison criteria to identify synchronization needs.
        
        Args:
        -----
        left_item: Metadata for left side item (or None if missing)
        right_item: Metadata for right side item (or None if missing)
        
        Returns:
        --------
        Set[str]: Set of difference types found
        """
        differences = set()
        
        # Check existence
        if self.compare_existence.get():
            if (left_item is None) != (right_item is None):
                differences.add('existence')
            elif left_item and right_item and (not left_item.exists or not right_item.exists):
                differences.add('existence')
                
        # If both items exist, compare other attributes
        if left_item and right_item and left_item.exists and right_item.exists:
            if self.compare_size.get() and left_item.size != right_item.size:
                differences.add('size')
                
            if self.compare_date_created.get() and left_item.date_created != right_item.date_created:
                differences.add('date_created')
                # v001.0010 added [debug date created comparison with full microsecond precision]
                if __debug__:
                    left_display = format_timestamp(left_item.date_created, include_timezone=False) or "None" # v001.0011 changed [use centralized format_timestamp method]
                    right_display = format_timestamp(right_item.date_created, include_timezone=False) or "None" # v001.0011 changed [use centralized format_timestamp method]
                    left_raw = left_item.date_created.timestamp() if left_item.date_created else 0 # v001.0010 added [debug date created comparison with full microsecond precision]
                    right_raw = right_item.date_created.timestamp() if right_item.date_created else 0 # v001.0010 added [debug date created comparison with full microsecond precision]
                    diff_microseconds = abs(left_raw - right_raw) * 1_000_000 # v001.0010 added [debug date created comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"DATE CREATED DIFFERENCE found for {left_item.path}:") # v001.0010 added [debug date created comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Left display : {left_display}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Right display: {right_display}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Left raw     : {left_item.date_created}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Right raw    : {right_item.date_created}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Difference   : {diff_microseconds:.1f} microseconds") # v001.0010 added [debug date created comparison with full microsecond precision]
                
            if self.compare_date_modified.get() and left_item.date_modified != right_item.date_modified:
                differences.add('date_modified')
                # v001.0010 added [debug date modified comparison with full microsecond precision]
                if __debug__:
                    left_display = format_timestamp(left_item.date_modified, include_timezone=False) or "None" # v001.0011 changed [use centralized format_timestamp method]
                    right_display = format_timestamp(right_item.date_modified, include_timezone=False) or "None" # v001.0011 changed [use centralized format_timestamp method]
                    left_raw = left_item.date_modified.timestamp() if left_item.date_modified else 0 # v001.0010 added [debug date modified comparison with full microsecond precision]
                    right_raw = right_item.date_modified.timestamp() if right_item.date_modified else 0 # v001.0010 added [debug date modified comparison with full microsecond precision]
                    diff_microseconds = abs(left_raw - right_raw) * 1_000_000 # v001.0010 added [debug date modified comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"DATE MODIFIED DIFFERENCE found for {left_item.path}:") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Left display : {left_display}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Right display: {right_display}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Left raw     : {left_item.date_modified}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Right raw    : {right_item.date_modified}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    log_and_flush(logging.DEBUG, f"  Difference   : {diff_microseconds:.1f} microseconds") # v001.0010 added [debug date modified comparison with full microsecond precision]
                
            if (self.compare_sha512.get() and left_item.sha512 and right_item.sha512 
                and left_item.sha512 != right_item.sha512):
                differences.add('sha512')
                
        return differences
        
    def update_comparison_ui(self): # v000.0002 changed - removed sorting parameters 
        """Update UI with comparison results and limit checking (no sorting)."""
        if self.limit_exceeded:
            log_and_flush(logging.WARNING, "Skipping UI update due to file limit exceeded")
            return
            
        log_and_flush(logging.INFO, "Updating UI with comparison results")
        
        # Clear existing tree content
        left_items = len(self.left_tree.get_children())
        right_items = len(self.right_tree.get_children())
        
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Cleared {left_items} left tree items and {right_items} right tree items")
            
        # Build tree structure with root handling # v000.0002 changed - removed sorting
        self.build_trees_with_root_paths() # v000.0002 changed - (no sorting)
                                                 
                                              
         
        
        # Update status
        self.status_var.set("Ready")
        self.update_summary()
        log_and_flush(logging.INFO, "UI update completed")

    def update_comparison_ui_filtered(self): # v000.0002 changed - removed sorting parameters
        """Update UI with filtered comparison results and limit checking (no sorting)."""
        if self.limit_exceeded:
            log_and_flush(logging.WARNING, "Skipping filtered UI update due to file limit exceeded")
            return
            
        log_and_flush(logging.INFO, "Updating UI with filtered comparison results")
        
        # Clear existing tree content
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)
            
        # Build tree structure with filtered results # v000.0002 changed - removed sorting
        self.build_trees_with_filtered_results() # v000.0002 changed - removed sorting
        
        # Update status
        self.status_var.set("Ready (Filtered)")
        self.update_summary()
        log_and_flush(logging.INFO, "Filtered UI update completed")

    def build_trees_with_filtered_results(self):
        """Build tree structures from filtered comparison results with limit checking (no sorting)."""
        if self.limit_exceeded:
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Building trees from {len(self.filtered_results)} filtered results")
        
        # Use filtered results instead of full results
        results_to_use = self.filtered_results
        
        # Create root items with fully qualified paths and functional checkboxes
        left_root_path = self.left_folder.get()
        right_root_path = self.right_folder.get()
        
        # Insert root items as top-level entries with checkboxes
        left_root_text = f"☐ {left_root_path}"
        right_root_text = f"☐ {right_root_path}"
        
        self.root_item_left = self.left_tree.insert('', tk.END, text=left_root_text, open=True,
                                                   values=("", "", "", "", "Root"))
        self.root_item_right = self.right_tree.insert('', tk.END, text=right_root_text, open=True,
                                                     values=("", "", "", "", "Root"))
        
        # Store root path mappings for selection system
        self.path_to_item_left[''] = self.root_item_left  # Empty path represents root
        self.path_to_item_right[''] = self.root_item_right
        
        # For filtered results, show a flattened view under each root # v000.0002 changed - removed sorting
        for rel_path, result in results_to_use.items(): # v000.0002 changed - removed sorting
            if not rel_path:
                continue
                
            # Add left item if it exists
            if result.left_item and result.left_item.exists:
                # v000.0006 ---------- START CODE BLOCK - facilitate folder timestamp and smart status display
                # v000.0006 added - Handle folder vs file display with timestamps
                if result.left_item.is_folder:
                    # This is a folder - show timestamps and smart status
                    date_created_str = format_timestamp(result.left_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = format_timestamp(result.left_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = ""  # Folders never have SHA512
                    
                    # Determine smart status for folders
                    if result.is_different and result.differences:
                        # Check if folder is different ONLY due to timestamps
                        timestamp_only_differences = {'date_created', 'date_modified'}
                        if result.differences.issubset(timestamp_only_differences):
                            status = "Folder (timestamp)"
                        else:
                            status = "Folder"
                    else:
                        status = "Folder"
                    item_text = f"☐ {rel_path}/"  # Add folder indicator
                else:
                    # v000.0006 ---------- END CODE BLOCK - facilitate folder timestamp and smart status display
                    # This is a file - show all metadata as before
                    date_created_str = format_timestamp(result.left_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = format_timestamp(result.left_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = result.left_item.sha512[:16] + "..." if result.left_item.sha512 else ""
                    status = "Different" if result.is_different else "Same"
                    item_text = f"☐ {rel_path}"
                
                # v000.0004 changed - Use folder-aware display values
                size_str = format_size(result.left_item.size) if result.left_item.size else ""
                item_id = self.left_tree.insert(self.root_item_left, tk.END, text=item_text,
                                              values=(size_str, date_created_str, date_modified_str, sha512_str, status))
                self.path_to_item_left[rel_path] = item_id
                
            # Add right item if it exists
            if result.right_item and result.right_item.exists:
                # v000.0006 added - Handle folder vs file display with timestamps
                if result.right_item.is_folder:
                    # This is a folder - show timestamps and smart status
                    date_created_str = format_timestamp(result.right_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = format_timestamp(result.right_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = ""  # Folders never have SHA512
                    
                    # Determine smart status for folders
                    if result.is_different and result.differences:
                        # Check if folder is different ONLY due to timestamps
                        timestamp_only_differences = {'date_created', 'date_modified'}
                        if result.differences.issubset(timestamp_only_differences):
                            status = "Folder (timestamp)"
                        else:
                            status = "Folder"
                    else:
                        status = "Folder"
                    item_text = f"☐ {rel_path}/"  # Add folder indicator
                else:
                    # This is a file - show all metadata as before
                    # v000.0006 ---------- END CODE BLOCK - facilitate folder timestamp and smart status display
                    date_created_str = format_timestamp(result.right_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = format_timestamp(result.right_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = result.right_item.sha512[:16] + "..." if result.right_item.sha512 else ""
                    status = "Different" if result.is_different else "Same"
                    item_text = f"☐ {rel_path}"
                
                # v000.0006 changed - Use folder-aware display values
                size_str = format_size(result.right_item.size) if result.right_item.size else ""
                item_id = self.right_tree.insert(self.root_item_right, tk.END, text=item_text,
                                               values=(size_str, date_created_str, date_modified_str, sha512_str, status))
                self.path_to_item_right[rel_path] = item_id

    def build_trees_with_root_paths(self): # v000.0003 changed - fixed false conflict detection bug
        """
        Build tree structures from comparison results with fully qualified root paths # v000.0002 changed - removed sorting
        
        Purpose:
        --------
        Creates stable tree structure that maintains row correspondence and folder hierarchy
        without any sorting functionality to comply with mandatory features.
        """
        if self.limit_exceeded:
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Building trees with root paths from {len(self.comparison_results)} comparison results")
                                                                                    
        
        start_time = time.time()
        
        # Create root items with fully qualified paths and functional checkboxes
        left_root_path = self.left_folder.get()
        right_root_path = self.right_folder.get()
        
        # Insert root items as top-level entries with checkboxes
        left_root_text = f"☐ {left_root_path}"
        right_root_text = f"☐ {right_root_path}"
        
        self.root_item_left = self.left_tree.insert('', tk.END, text=left_root_text, open=True,
                                                   values=("", "", "", "", "Root"))
        self.root_item_right = self.right_tree.insert('', tk.END, text=right_root_text, open=True,
                                                     values=("", "", "", "", "Root"))
        
        # Store root path mappings for selection system
        self.path_to_item_left[''] = self.root_item_left  # Empty path represents root
        self.path_to_item_right[''] = self.root_item_right
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Created root items: left={self.root_item_left}, right={self.root_item_right}")
        
        # Create sentinel class for missing folders to distinguish from real empty folders
        class MissingFolder:
            def __init__(self):
                self.contents = {}
        
        # Organize paths into tree structure (same as before)
        left_structure = {}
        right_structure = {}
        
        # First pass: Build structure for existing items
        for rel_path, result in self.comparison_results.items():
            if not rel_path:  # Skip empty paths
                if __debug__:
                    log_and_flush(logging.DEBUG, "Skipping empty relative path")
                continue
                
            path_parts = rel_path.split('/')
            assert len(path_parts) > 0, f"Path parts should not be empty for: {rel_path}"
            
            # Build left structure
            if result.left_item is not None:
                current = left_structure
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = {}
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = {}
                        elif isinstance(current[part], MissingFolder):
                            current[part] = current[part].contents
                        current = current[part] if isinstance(current[part], dict) else current[part].contents
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    
                    # v000.0003 changed - fixed folder vs file handling to prevent false conflicts
                    if result.left_item.is_folder:
                        # This is a folder - ensure it exists as a dict structure
                        if final_name not in current:
                            current[final_name] = {}  # v000.0003 added - create folder dict structure
                        elif not isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: folder trying to replace a file (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add folder '{final_name}' - file exists with same name")
                        # v000.0003 changed - for folders, don't store metadata directly, just ensure dict exists
                    else:
                        # This is a file
                        if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: file trying to replace a folder (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add file '{final_name}' - folder exists with same name")
                        else:
                            current[final_name] = result.left_item  # v000.0003 changed - only store file metadata for files
            
            # Build right structure  
            if result.right_item is not None:
                current = right_structure
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = {}
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = {}
                        elif isinstance(current[part], MissingFolder):
                            current[part] = current[part].contents
                        current = current[part] if isinstance(current[part], dict) else current[part].contents
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    
                    # v000.0003 changed - fixed folder vs file handling to prevent false conflicts
                    if result.right_item.is_folder:
                        # This is a folder - ensure it exists as a dict structure
                        if final_name not in current:
                            current[final_name] = {}  # v000.0003 added - create folder dict structure
                        elif not isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: folder trying to replace a file (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add folder '{final_name}' - file exists with same name")
                        # v000.0003 changed - for folders, don't store metadata directly, just ensure dict exists
                    else:
                        # This is a file
                        if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: file trying to replace a folder (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add file '{final_name}' - folder exists with same name")
                        else:
                            current[final_name] = result.right_item  # v000.0003 changed - only store file metadata for files
                            
        # Second pass: Add missing items as placeholders
        missing_left = 0
        missing_right = 0
        for rel_path, result in self.comparison_results.items():
            if not rel_path:
                continue
                
            path_parts = rel_path.split('/')
            
            # Add missing left items
            if result.left_item is None and result.right_item is not None:
                missing_left += 1
                current = left_structure
                
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = MissingFolder()
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = MissingFolder()
                        current = current[part].contents if isinstance(current[part], MissingFolder) else current[part]
                        
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    if result.right_item and result.right_item.is_folder:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = MissingFolder()
                    else:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = None
                    
            # Add missing right items
            if result.right_item is None and result.left_item is not None:
                missing_right += 1
                current = right_structure
                
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = MissingFolder()
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = MissingFolder()
                        current = current[part].contents if isinstance(current[part], MissingFolder) else current[part]
                        
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    if result.left_item and result.left_item.is_folder:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = MissingFolder()
                    else:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = None
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Added {missing_left} missing left placeholders, {missing_right} missing right placeholders")
            
        # Populate trees under root items with stable alphabetical ordering # v000.0002 changed - removed sorting
        log_and_flush(logging.INFO, "Populating tree views under root paths with stable ordering...") # v000.0002 changed - removed sorting
        self.populate_tree(self.left_tree, left_structure, self.root_item_left, 'left', '') # v000.0002 changed - removed sorting
                                                                         
        self.populate_tree(self.right_tree, right_structure, self.root_item_right, 'right', '') # v000.0002 changed - removed sorting
                                                                         
        
        elapsed_time = time.time() - start_time
        if __debug__:
            log_and_flush(logging.DEBUG, f"Tree building with root paths completed in {elapsed_time:.3f} seconds")
            
    def populate_tree(self, tree, structure, parent_id, side, current_path):
        """
        Recursively populate tree with structure using stable alphabetical ordering.
        
        Purpose:
        --------
        Creates stable tree structure that maintains consistent ordering without
        any custom sorting to comply with mandatory features. Uses simple alphabetical
        ordering for predictable results.
        """
        if self.limit_exceeded:
            return
        
        # Use simple alphabetical sorting for stable, predictable ordering  # v000.0002 changed - removed sorting
        sorted_items = sorted(structure.items()) # v000.0002 changed - removed sorting
        
        # Import the MissingFolder class (defined in build_trees_with_root_paths)
        for name, content in sorted_items:
            # Build the full relative path for this item
            item_rel_path = current_path + ('/' if current_path else '') + name
            
            # Check if content is a MissingFolder (defined in the calling method)
            is_missing_folder = hasattr(content, 'contents')
            
            if isinstance(content, dict) or is_missing_folder:
                # This is a folder (either real or missing)
                if is_missing_folder:
                    # Missing folder - NO checkbox, just plain text with [MISSING]
                    item_text = f"{name}/ [MISSING]"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, open=False,
                                        values=("", "", "", "", "Missing"), tags=('missing',))
                    # Recursively populate children from the missing folder's contents
                    self.populate_tree(tree, content.contents, item_id, side, item_rel_path) # v000.0002 changed - removed sorting
                else:
                    # Real folder - has checkbox
                    item_text = f"☐ {name}/"
                    
                    # v000.0006 ---------- START CODE BLOCK - facilitate folder timestamp and smart status display
                    # v000.0006 added - Get folder metadata for timestamp display and smart status
                    result = self.comparison_results.get(item_rel_path)
                    folder_metadata = None
                    date_created_str = ""
                    date_modified_str = ""
                    status = "Folder"
                    
                    if result:
                        # Get the folder metadata from the appropriate side
                        if side == 'left' and result.left_item:
                            folder_metadata = result.left_item
                        elif side == 'right' and result.right_item:
                            folder_metadata = result.right_item
                        
                        # v000.0006 added - Format folder timestamps if available
                        if folder_metadata and folder_metadata.is_folder:
                            date_created_str = format_timestamp(folder_metadata.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                            date_modified_str = format_timestamp(folder_metadata.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                        
                        # v000.0006 added - Determine smart status for folders
                        if result.is_different and result.differences:
                            # Check if folder is different ONLY due to timestamps
                            timestamp_only_differences = {'date_created', 'date_modified'}
                            if result.differences.issubset(timestamp_only_differences):
                                status = "Folder (timestamp)"
                            elif result.differences:
                                # Other differences exist (existence, contents, etc.)
                                status = "Folder"
                    # v000.0006 ---------- END CODE BLOCK - facilitate folder timestamp and smart status display                 
                    # v000.0006 changed - Insert folder with timestamp data and smart status
                    item_id = tree.insert(parent_id, tk.END, text=item_text, open=False,
                                        values=("", date_created_str, date_modified_str, "", status))
                    # Recursively populate children
                    self.populate_tree(tree, content, item_id, side, item_rel_path) # v000.0002 changed - removed sorting
                                                                                    
                
                # Store path mapping for both real and missing folders
                path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
                path_map[item_rel_path] = item_id
                
            else:
                # This is a file
                if content is None:
                    # Missing file - NO checkbox, just plain text with [MISSING]
                    item_text = f"{name} [MISSING]"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, 
                                        values=("", "", "", "", "Missing"), tags=('missing',))
                else:
                    # Existing file - has checkbox and shows ALL metadata
                    size_str = format_size(content.size) if content.size else ""
                    date_created_str = format_timestamp(content.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = format_timestamp(content.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = content.sha512[:16] + "..." if content.sha512 else ""
                    
                    # Determine status using proper path lookup
                    result = self.comparison_results.get(item_rel_path)
                    status = "Different" if result and result.is_different else "Same"
                    
                    item_text = f"☐ {name}"
                    item_id = tree.insert(parent_id, tk.END, text=item_text,
                                        values=(size_str, date_created_str, date_modified_str, sha512_str, status))
                
                # Store path mapping for both missing and existing files
                path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
                path_map[item_rel_path] = item_id
                                        
        # Configure missing item styling using configurable color
        tree.tag_configure('missing', foreground=MISSING_ITEM_COLOR)

    def get_item_path(self, tree, item_id):
        """
        Get the full relative path for a tree item.
        
        Purpose:
        --------
        Reconstructs the relative path for a tree item by traversing
        the tree hierarchy up to the root item.
        
        Args:
        -----
        tree: Tree widget containing the item
        item_id: ID of the tree item
        
        Returns:
        --------
        str: Relative path of the item
        """
        if not item_id:
            return ""
        path_parts = []
        current = item_id
        while current:
            text = tree.item(current, 'text')
            # Remove checkbox and extract name
            if text.startswith('☑ ') or text.startswith('☐ '):
                text = text[2:]
            # Remove folder indicator
            if text.endswith('/'):
                text = text[:-1]
            # Remove [MISSING] indicator
            if text.endswith(' [MISSING]'):
                text = text[:-10]
            
            # Stop at root item (don't include the full path in relative path calculation)
            root_item = self.root_item_left if tree == self.left_tree else self.root_item_right
            if current == root_item:
                break
                
            path_parts.append(text)
            current = tree.parent(current)
        return '/'.join(reversed(path_parts))
        
    def find_tree_item_by_path(self, rel_path, side):
        """
        Find tree item ID by relative path using efficient path mapping.
        
        Purpose:
        --------
        Provides fast lookup of tree items by their relative paths
        using pre-built mapping dictionaries for optimal performance.
        
        Args:
        -----
        rel_path: Relative path to search for
        side: Which tree side ('left' or 'right')
        
        Returns:
        --------
        str: Tree item ID or None if not found
        """
        path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
        return path_map.get(rel_path)
        
    def select_all_differences_left(self):
        """
        Select all different items in left pane with auto-clear first and limit checking.
        
        Purpose:
        --------
        Automatically clears all selections before selecting for clean workflow.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Selection operations are disabled when file limits are exceeded.")
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, "Auto-clearing all selections before selecting differences in left pane")
            
        # First clear all selections for clean state
        self.clear_all_left()
        
        # Use appropriate results set (filtered or full)
        results_to_use = self.filtered_results if self.is_filtered else self.comparison_results
        
        count = 0
        for rel_path, result in results_to_use.items():
            if result.is_different and result.left_item and result.left_item.exists:
                item_id = self.find_tree_item_by_path(rel_path, 'left')
                if item_id:
                    self.selected_left.add(item_id)
                    count += 1
                    
        if __debug__:
            log_and_flush(logging.DEBUG, f"Selected {count} different items in left pane (after auto-clear)")
            
        filter_text = " (filtered)" if self.is_filtered else ""
        self.add_status_message(f"Selected all differences in left pane{filter_text}: {count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def select_all_differences_right(self):
        """
        Select all different items in right pane with auto-clear first and limit checking.
        
        Purpose:
        --------
        Automatically clears all selections before selecting for clean workflow.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Selection operations are disabled when file limits are exceeded.")
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, "Auto-clearing all selections before selecting differences in right pane")
            
        # First clear all selections for clean state
        self.clear_all_right()
        
        # Use appropriate results set (filtered or full)
        results_to_use = self.filtered_results if self.is_filtered else self.comparison_results
        
        count = 0
        for rel_path, result in results_to_use.items():
            if result.is_different and result.right_item and result.right_item.exists:
                item_id = self.find_tree_item_by_path(rel_path, 'right')
                if item_id:
                    self.selected_right.add(item_id)
                    count += 1
                    
        if __debug__:
            log_and_flush(logging.DEBUG, f"Selected {count} different items in right pane (after auto-clear)")
            
        filter_text = " (filtered)" if self.is_filtered else ""
        self.add_status_message(f"Selected all differences in right pane{filter_text}: {count:,} items")
        self.update_tree_display_safe() 
        self.update_summary()
        
    def clear_all_left(self):
        """
        Clear ALL selections in left pane (not just differences) with limit checking.
        
        Purpose:
        --------
        Provides complete reset functionality for workflow flexibility.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            # Allow clearing even when limits exceeded to help user reset
            pass
            
        cleared_count = len(self.selected_left)
        if __debug__:
            log_and_flush(logging.DEBUG, f"Clearing ALL {cleared_count} selections in left pane")
            
        self.selected_left.clear()
        if cleared_count > 0:
            self.add_status_message(f"Cleared all selections in left pane: {cleared_count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def clear_all_right(self):
        """
        Clear ALL selections in right pane (not just differences) with limit checking.
        
        Purpose:
        --------
        Provides complete reset functionality for workflow flexibility.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            # Allow clearing even when limits exceeded to help user reset
            pass
            
        cleared_count = len(self.selected_right)
        if __debug__:
            log_and_flush(logging.DEBUG, f"Clearing ALL {cleared_count} selections in right pane")
            
        self.selected_right.clear()
        if cleared_count > 0:
            self.add_status_message(f"Cleared all selections in right pane: {cleared_count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def copy_left_to_right(self):
        """Copy selected items from left to right with dry run support and limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Copy operations are disabled when file limits are exceeded.")
            return
            
        if not self.selected_left:
            self.add_status_message("No items selected for copying from left to right")
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # Get selected paths for copying
        selected_paths = []
        for item_id in self.selected_left:
            path = self.get_item_path(self.left_tree, item_id)
            if path:  # Only include non-empty paths
                selected_paths.append(path)
            
        if not selected_paths:
            self.add_status_message("No valid paths selected for copying")
            messagebox.showinfo("Info", "No valid paths selected for copying")
            return
        
        # Include dry run information in status message
        dry_run_text = " (DRY RUN)" if self.dry_run_mode.get() else ""
        self.add_status_message(f"Starting copy operation{dry_run_text}: {len(selected_paths):,} items from LEFT to RIGHT")
        
        # Show confirmation dialog with dry run information
        dry_run_notice = "\n\n*** DRY RUN MODE - No files will be modified ***" if self.dry_run_mode.get() else ""
        message = f"Copy {len(selected_paths)} items from LEFT to RIGHT?{dry_run_notice}\n\n"
        message += "\n".join(selected_paths[:COPY_PREVIEW_MAX_ITEMS])
        if len(selected_paths) > COPY_PREVIEW_MAX_ITEMS:
            message += f"\n... and {len(selected_paths) - COPY_PREVIEW_MAX_ITEMS} more items"
        
        if not messagebox.askyesno("Confirm Copy Operation", message):
            self.add_status_message("Copy operation cancelled by user")
            return
        
        # Start copy operation in background thread
        status_text = "Simulating copy..." if self.dry_run_mode.get() else "Copying files..."
        self.status_var.set(status_text)
        threading.Thread(target=self.perform_enhanced_copy_operation, args=('left_to_right', selected_paths), daemon=True).start()
        
    def copy_right_to_left(self):
        """Copy selected items from right to left with dry run support and limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Copy operations are disabled when file limits are exceeded.")
            return
            
        if not self.selected_right:
            self.add_status_message("No items selected for copying from right to left")
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # Get selected paths for copying
        selected_paths = []
        for item_id in self.selected_right:
            path = self.get_item_path(self.right_tree, item_id)
            if path:  # Only include non-empty paths
                selected_paths.append(path)
            
        if not selected_paths:
            self.add_status_message("No valid paths selected for copying")
            messagebox.showinfo("Info", "No valid paths selected for copying")
            return
        
        # Include dry run information in status message
        dry_run_text = " (DRY RUN)" if self.dry_run_mode.get() else ""
        self.add_status_message(f"Starting copy operation{dry_run_text}: {len(selected_paths):,} items from RIGHT to LEFT")
        
        # Show confirmation dialog with dry run information
        dry_run_notice = "\n\n*** DRY RUN MODE - No files will be modified ***" if self.dry_run_mode.get() else ""
        message = f"Copy {len(selected_paths)} items from RIGHT to LEFT?{dry_run_notice}\n\n"
        message += "\n".join(selected_paths[:COPY_PREVIEW_MAX_ITEMS])
        if len(selected_paths) > COPY_PREVIEW_MAX_ITEMS:
            message += f"\n... and {len(selected_paths) - COPY_PREVIEW_MAX_ITEMS} more items"
        
        if not messagebox.askyesno("Confirm Copy Operation", message):
            self.add_status_message("Copy operation cancelled by user")
            return
        
        # Start copy operation in background thread
        status_text = "Simulating copy..." if self.dry_run_mode.get() else "Copying files..."
        self.status_var.set(status_text)
        threading.Thread(target=self.perform_enhanced_copy_operation, args=('right_to_left', selected_paths), daemon=True).start()

    def perform_enhanced_copy_operation(self, direction, selected_paths): # changed for v000.0005
        """
        Perform file copy operations with comprehensive logging, dry run support, and tracking.
        
        Purpose:
        --------
        Orchestrates file copy operations using Strategy A/B with comprehensive logging,
        dry run simulation capability, sequential numbering, and automatic refresh after completion.
        
        Args:
        -----
        direction: Copy direction ('left_to_right' or 'right_to_left')
        selected_paths: List of relative paths to copy
        """
        start_time = time.time()
        is_dry_run = self.dry_run_mode.get()
        dry_run_text = " (DRY RUN)" if is_dry_run else ""
        
        log_and_flush(logging.INFO, f"Starting copy operation{dry_run_text}: {direction} with {len(selected_paths)} items")
        
        # Determine source and destination folders
        if direction == 'left_to_right':
            source_folder = self.left_folder.get()
            dest_folder = self.right_folder.get()
            direction_text = "LEFT to RIGHT"
        else:
            source_folder = self.right_folder.get()
            dest_folder = self.left_folder.get()
            direction_text = "RIGHT to LEFT"
        
        # Start copy operation session with dedicated logging and dry run support
        operation_name = f"Copy {len(selected_paths)} items from {direction_text}{dry_run_text}"
        operation_id = self.copy_manager.start_copy_operation(operation_name, dry_run=is_dry_run)
        
        # Create progress dialog for copy operation with dry run indication
        progress_title = f"{'Simulating' if is_dry_run else 'Copying'} Files"
        progress_message = f"{'Simulating' if is_dry_run else 'Copying'} files from {direction_text}..."
        progress = ProgressDialog(
            self.root,
            progress_title,
            progress_message,
            max_value=len(selected_paths)
        )
        
        copied_count = 0
        error_count = 0
        skipped_count = 0
        total_bytes_copied = 0
        critical_errors = []  # Track critical errors that require user attention
        
        # Track copy strategies used for summary
        direct_strategy_count = 0
        staged_strategy_count = 0
        
        try:
            for i, rel_path in enumerate(selected_paths):
                try:
                    # Update progress with dry run indication if required
                    source_path = str(Path(source_folder) / rel_path)
                    # Check if this file will use staged strategy for large file indication
                    base_progress_text = f"{'Simulating' if is_dry_run else 'Copying'} {i+1} of {len(selected_paths)}: {os.path.basename(rel_path)}"
                    if Path(source_path).exists() and Path(source_path).is_file():
                        file_size = Path(source_path).stat().st_size
                        strategy = determine_copy_strategy(source_path, str(Path(dest_folder) / rel_path), file_size)
                        if strategy == CopyStrategy.STAGED and file_size >= COPY_STRATEGY_THRESHOLD:
                            size_str = format_size(file_size)
                            progress_text = f"{base_progress_text}\n({size_str} file copy in progress ...not frozen, just busy)"
                        else:
                            progress_text = base_progress_text
                    else:
                        progress_text = base_progress_text
                    progress.update_progress(i+1, progress_text)
                                                       
                    dest_path = str(Path(dest_folder) / rel_path)
                    
                    # Skip if source doesn't exist
                    if not Path(source_path).exists():
                        skipped_count += 1
                        self.copy_manager._log_status(f"Source file not found, skipping: {source_path}")
                        continue
                    
                    # Handle directories separately (create them, don't copy as files) # v000.0005 changed - added folder timestamp copying
                    if Path(source_path).is_dir():
                        # Create destination directory if needed (or simulate in dry run)
                        if not Path(dest_path).exists():
                            if not is_dry_run:
                                Path(dest_path).mkdir(parents=True, exist_ok=True)
                                copied_count += 1
                                self.copy_manager._log_status(f"Created directory: {dest_path}")
                                
                                # v000.0005 added - Copy timestamps for newly created directories
                                try:                                                                                                     # v000.0005 added - Copy timestamps for newly created directories
                                    self.copy_manager.timestamp_manager.copy_timestamps(source_path, dest_path)                          # v000.0005 added - Copy timestamps for newly created directories
                                    self.copy_manager._log_status(f"Copied directory timestamps: {dest_path}")                           # v000.0005 added - Copy timestamps for newly created directories
                                except Exception as e:                                                                                   # v000.0005 added - Copy timestamps for newly created directories
                                    # Non-critical error - directory was created successfully                                            # v000.0005 added - Copy timestamps for newly created directories
                                    self.copy_manager._log_status(f"Warning: Could not copy directory timestamps for {dest_path}: {e}")  # v000.0005 added - Copy timestamps for newly created directories
                            else:
                                copied_count += 1
                                self.copy_manager._log_status(f"DRY RUN: Would create directory: {dest_path}")
                                self.copy_manager._log_status(f"DRY RUN: Would copy directory timestamps: {dest_path}")  # v000.0005 added
                        else:
                            # v000.0005 added - Directory already exists - still copy timestamps to sync metadata  
                            if not is_dry_run:                                                                                             # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                try:                                                                                                       # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    self.copy_manager.timestamp_manager.copy_timestamps(source_path, dest_path)                            # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    copied_count += 1  # Count as a successful operation                                                   # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    self.copy_manager._log_status(f"Updated directory timestamps: {dest_path}")                            # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                except Exception as e:                                                                                     # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    # Non-critical error - directory exists                                                                # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    self.copy_manager._log_status(f"Warning: Could not update directory timestamps for {dest_path}: {e}")  # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    skipped_count += 1                                                                                     # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                            else:                                                                                                          # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                copied_count += 1                                                                                          # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                self.copy_manager._log_status(f"DRY RUN: Would update directory timestamps: {dest_path}")                  # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                        continue
                    
                    # Copy individual file using copy manager with dry run support
                    result = self.copy_manager.copy_file(source_path, dest_path, self.overwrite_mode.get())
                    
                    # Track strategy usage for summary
                    if result.strategy_used == CopyStrategy.DIRECT:
                        direct_strategy_count += 1
                    elif result.strategy_used == CopyStrategy.STAGED:
                        staged_strategy_count += 1
                    
                    if result.success:
                        copied_count += 1
                        total_bytes_copied += result.bytes_copied
                        success_msg = f"Successfully {'simulated' if is_dry_run else 'copied'}: {rel_path} ({result.strategy_used.value} strategy)"
                        self.copy_manager._log_status(success_msg)
                    else:
                        error_count += 1
                        error_msg = f"Failed to {'simulate' if is_dry_run else 'copy'} {rel_path}: {result.error_message}"
                        self.copy_manager._log_status(error_msg)
                        self.root.after(0, lambda msg=error_msg: self.add_status_message(f"ERROR: {msg}"))
                        
                        # Check for critical errors that require immediate user attention (only in non-dry-run)
                        if not is_dry_run and ("CRITICAL" in result.error_message or "Rename operation failed" in result.error_message):
                            critical_errors.append((rel_path, result.error_message))
                    
                    # Update progress every few items using configurable frequency
                    if i % max(1, len(selected_paths) // 20) == 0:
                        status_msg = f"Progress: {copied_count} {'simulated' if is_dry_run else 'copied'}, {error_count} errors, {skipped_count} skipped"
                        self.root.after(0, lambda msg=status_msg: self.add_status_message(msg))
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error processing {rel_path}: {str(e)}"
                    log_and_flush(logging.ERROR, error_msg)
                    self.copy_manager._log_status(error_msg)
                    self.root.after(0, lambda msg=error_msg: self.add_status_message(f"ERROR: {msg}"))
                    continue
            
            # Final progress update
            final_progress_text = f"{'Simulation' if is_dry_run else 'Copy'} operation complete"
            progress.update_progress(len(selected_paths), final_progress_text)
            
            elapsed_time = time.time() - start_time
            
            # End copy operation session
            self.copy_manager.end_copy_operation(copied_count, error_count, total_bytes_copied)
            
            # summary message with strategy breakdown
            summary = f"Copy operation{dry_run_text} complete ({direction_text}): "
            summary += f"{copied_count} {'simulated' if is_dry_run else 'copied'}, {error_count} errors, "
            summary += f"{skipped_count} skipped, {total_bytes_copied:,} bytes in {elapsed_time:.1f}s"
            log_and_flush(logging.INFO, summary)
            self.root.after(0, lambda: self.add_status_message(summary))
            
            # strategy summary
            if direct_strategy_count > 0 or staged_strategy_count > 0:
                strategy_summary = f"Strategy usage: {direct_strategy_count} direct, {staged_strategy_count} staged"
                self.root.after(0, lambda: self.add_status_message(strategy_summary))
            
            # Show completion dialog with information including dry run status
            completion_msg = f"Copy operation{dry_run_text} completed!\n\n"
            completion_msg += f"Successfully {'simulated' if is_dry_run else 'copied'}: {copied_count} items\n"
            completion_msg += f"Total bytes {'simulated' if is_dry_run else 'copied'}: {total_bytes_copied:,}\n"
            completion_msg += f"Errors: {error_count}\n"
            completion_msg += f"Skipped: {skipped_count}\n"
            completion_msg += f"Time: {elapsed_time:.1f} seconds\n"
            completion_msg += f"Operation ID: {operation_id}\n"
            
            # Include strategy breakdown
            if direct_strategy_count > 0 or staged_strategy_count > 0:
                completion_msg += f"\nStrategy Usage:\n"
                completion_msg += f"• Direct strategy: {direct_strategy_count} files\n"
                completion_msg += f"• Staged strategy: {staged_strategy_count} files\n"
            
            if is_dry_run:
                completion_msg += f"\n*** DRY RUN SIMULATION ***\n"
                completion_msg += f"No actual files were modified. This was a test run.\n"
                completion_msg += f"Check the detailed log for complete operation simulation.\n"
            else:
                if critical_errors:
                    # Build error details separately
                    error_details = f"CRITICAL ERRORS ENCOUNTERED ({len(critical_errors)}):\n\n"
                    for i, (path, error) in enumerate(critical_errors):
                        error_details += f"{i+1}. {path}:\n   {error}\n\n"
                    error_details += "\nRECOMMENDED ACTION: Check the detailed log file for troubleshooting.\n"
                    error_details += "These errors may indicate network issues or file locking problems."
                    
                    # Add summary to main message
                    completion_msg += f"\n⚠️ {len(critical_errors)} CRITICAL ERRORS - Click 'Show Details' to view\n\n"
                
                completion_msg += "The folder trees will now be refreshed and selections cleared."
            
            # Use error dialog if there were critical errors, otherwise info dialog
            if critical_errors and not is_dry_run:
                self.root.after(0, lambda: ErrorDetailsDialog(
                    self.root, 
                    f"Copy Complete with Errors", 
                    completion_msg, 
                    error_details
                ))
            else:
                self.root.after(0, lambda: messagebox.showinfo(
                    f"{'Simulation' if is_dry_run else 'Copy'} Complete", 
                    completion_msg
                ))
            
            # IMPORTANT: Only refresh trees and clear selections for actual copy operations (not dry runs)
            if not is_dry_run:
                self.root.after(0, self.refresh_after_copy_operation)
            else:
                self.root.after(0, lambda: self.add_status_message("DRY RUN complete - no file system changes made"))
            
        except Exception as e:
            log_and_flush(logging.ERROR, f"Copy operation{dry_run_text} failed: {e}")
            error_msg = f"Copy operation{dry_run_text} failed: {str(e)}"
            self.copy_manager._log_status(error_msg)
            self.root.after(0, lambda: self.add_status_message(f"ERROR: {error_msg}"))
            self.root.after(0, lambda: self.show_error(error_msg))
        finally:
            progress.close()
            self.root.after(0, lambda: self.status_var.set("Ready"))

    def refresh_after_copy_operation(self):
        """
        Refresh folder trees and clear all selections after copy operation with limit checking.
        
        Purpose:
        --------
        This ensures the user sees the current state after copying,
        but only performs refresh for actual copy operations (not dry runs).
        """
        log_and_flush(logging.INFO, "Refreshing trees and clearing selections after copy operation")
        self.add_status_message("Refreshing folder trees after copy operation...")
        
        # Clear all selections first
        self.selected_left.clear()
        self.selected_right.clear()
        
        # Clear any active filter
        if self.is_filtered:
            self.clear_filter()
        
        # Reset limit state for refresh
        self.limit_exceeded = False
        
        # Restart comparison to refresh trees
        # This will re-scan both folders and rebuild the trees
        if self.left_folder.get() and self.right_folder.get():
            self.add_status_message("Re-scanning folders to show updated state...")
            threading.Thread(target=self.perform_comparison, daemon=True).start()
        else:
            self.add_status_message("Copy operation complete - ready for next operation")
        
    def update_summary(self):
        """Update summary information with filter status and limit checking."""
        # Use appropriate results set (filtered or full)
        results_to_use = self.filtered_results if self.is_filtered else self.comparison_results
        
        if self.limit_exceeded:
            self.summary_var.set("Summary: File limit exceeded - operations disabled")
            return
        
        if not results_to_use:
            if self.is_filtered:
                self.summary_var.set("Summary: No matching files in filter")
            else:
                self.summary_var.set("Summary: No comparison performed")
            return
            
        total_differences = sum(1 for r in results_to_use.values() if r.is_different)
        missing_left = sum(1 for r in results_to_use.values() 
                          if r.left_item is None or not r.left_item.exists)
        missing_right = sum(1 for r in results_to_use.values()
                           if r.right_item is None or not r.right_item.exists)
        selected_total = len(self.selected_left) + len(self.selected_right)
        
        filter_text = " (filtered)" if self.is_filtered else ""
        dry_run_text = " | DRY RUN MODE" if self.dry_run_mode.get() else ""
        summary = f"Summary{filter_text}: {total_differences} differences | {missing_left} missing left | {missing_right} missing right | {selected_total} marked{dry_run_text}"
        self.summary_var.set(summary)
        
    def show_error(self, message):
        """Show error message to user with context and details option."""
        log_and_flush(logging.ERROR, f"Displaying error to user: {message}")
        
        # Split message into summary and details if it's long
        if len(message) > 100 or '\n' in message or '|' in message:
            # Try to create meaningful summary
            if ':' in message:
                summary = message.split(':')[0] + " (see details)"
            else:
                summary = message[:100] + "..."
            ErrorDetailsDialog(self.root, "Error", summary, message)
        else:
            # Short message - use simple dialog
            messagebox.showerror("Error", message)
            
        self.status_var.set("Ready")
        
    def run(self):
        """
        Start the application GUI event loop
        
        Purpose:
        --------
        Main application entry point that starts the GUI event loop
        with comprehensive error handling and graceful shutdown.
        """
        log_and_flush(logging.INFO, "Starting FolderCompareSync GUI application.")
        try:
            self.root.mainloop()
        except Exception as e:
            log_and_flush(logging.ERROR, f"Application crashed: {type(e).__name__}: {str(e)}")
            if __debug__:
                import traceback
                log_and_flush(logging.DEBUG, "Crash traceback:")
                log_and_flush(logging.DEBUG, traceback.format_exc())
            raise
        finally:
            log_and_flush(logging.INFO, "Application shutdown")

# ============================================================================
# COMPREHENSIVE DELETE ORPHANS MANAGER CLASS
# ============================================================================

class DeleteOrphansManager_class:
    """
    Comprehensive manager for delete orphans functionality.
    
    Contains both utility functions (as static methods) and dialog interface (as instance methods).
    This keeps all delete orphans functionality organized in one place.
    
    Static Methods (Utilities):
    - File operations: delete_file_to_recycle_bin, delete_file_permanently
    - Permission checking: check_file_permissions, validate_orphan_file_access  
    - Orphan detection: detect_orphaned_files, create_orphan_metadata_dict
    - Data management: refresh_orphan_metadata_status, build_orphan_tree_structure, calculate_orphan_statistics
    
    Instance Methods (Dialog):
    - Dialog management: __init__, setup_dialog, close_dialog
    - UI setup: setup_ui, setup_header_section, etc.
    - Tree management: build_orphan_tree, handle_tree_click, etc.
    - Operations: apply_filter, delete_selected_files, perform_deletion, etc.
    """
    
    # ========================================================================
    # STATIC UTILITY METHODS - FILE OPERATIONS
    # ========================================================================
    
    @staticmethod
    def delete_file_to_recycle_bin(file_path: str, show_progress: bool = True) -> tuple[bool, str]:
        """
        Move a file to Windows Recycle Bin using SHFileOperation.
        
        Purpose:
        --------
        Safely moves files to Recycle Bin where they can be recovered.
        Uses Windows Shell API for proper integration with Windows Explorer.
        
        Args:
        -----
        file_path: Full path to file to move to Recycle Bin
        show_progress: Whether to show Windows progress dialog
        
        Returns:
        --------
        tuple[bool, str]: (success, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            
            # Prepare file path with double null termination required by SHFileOperation
            file_path_bytes = file_path.encode('utf-8') + b'\0\0'
            
            # Configure operation flags
            flags = FOF_ALLOWUNDO  # Enable Recycle Bin
            if not show_progress:
                flags |= FOF_SILENT | FOF_NOCONFIRMATION
            
            # Create operation structure
            file_op = SHFILEOPSTRUCT()
            file_op.hwnd = None                    # No parent window
            file_op.wFunc = FO_DELETE             # Delete operation
            file_op.pFrom = c_char_p(file_path_bytes)  # Source file
            file_op.pTo = None                    # No destination (delete)
            file_op.fFlags = flags                # Operation flags
            file_op.fAnyOperationsAborted = False
            file_op.hNameMappings = None
            file_op.lpszProgressTitle = c_char_p(b"Moving to Recycle Bin...")
            
            # Call Windows Shell API
            result = ctypes.windll.shell32.SHFileOperationA(byref(file_op))
            
            if result == 0 and not file_op.fAnyOperationsAborted:
                return True, ""
            elif file_op.fAnyOperationsAborted:
                return False, "Operation cancelled by user"
            else:
                # Map common error codes to user-friendly messages
                error_messages = {
                    0x71: "File is being used by another process",
                    0x72: "Access denied - insufficient permissions",
                    0x73: "File is read-only or system file",
                    0x74: "Path not found",
                    0x75: "Path too long",
                    0x76: "File name too long",
                    0x78: "Destination path invalid",
                    0x79: "Security error",
                    0x7A: "Source and destination are the same",
                    0x7C: "Path is invalid",
                    0x80: "File already exists",
                    0x81: "Folder is not empty",
                    0x82: "Operation not supported",
                    0x83: "Network path not found",
                    0x84: "Disk full"
                }
                error_msg = error_messages.get(result, f"Shell operation failed with error code: 0x{result:X}")
                return False, error_msg
                
        except Exception as e:
            return False, f"Exception during Recycle Bin operation: {str(e)}"

    @staticmethod
    def delete_file_permanently(file_path: str) -> tuple[bool, str]:
        """
        Permanently delete a file bypassing the Recycle Bin.
        
        Purpose:
        --------
        Immediately removes files from the file system without recovery option.
        Use with caution - files cannot be easily recovered after this operation.
        
        Args:
        -----
        file_path: Full path to file to permanently delete
        
        Returns:
        --------
        tuple[bool, str]: (success, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
                
            # Use Python's built-in os.remove for permanent deletion
            os.remove(file_path)
            return True, ""
            
        except PermissionError:
            return False, "Access denied - file may be read-only or in use by another process"
        except FileNotFoundError:
            return False, "File not found - may have been deleted by another process"
        except OSError as e:
            return False, f"System error during deletion: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error during permanent deletion: {str(e)}"

    @staticmethod
    def check_file_permissions(file_path: str) -> tuple[bool, str]:
        """
        Check if a file can be deleted by testing permissions and access.
        
        Purpose:
        --------
        Pre-validates file deletion capability to provide user feedback
        before attempting actual deletion operations.
        
        Args:
        -----
        file_path: Full path to file to check
        
        Returns:
        --------
        tuple[bool, str]: (can_delete, status_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, "Missing"
                
            # Check if file is accessible
            if not os.access(file_path, os.R_OK):
                return False, "No Read Access"
                
            # Check if file can be deleted
            if not os.access(file_path, os.W_OK):
                return False, "Read-Only"
                
            # Check if parent directory allows deletion
            parent_dir = os.path.dirname(file_path)
            if not os.access(parent_dir, os.W_OK):
                return False, "Directory Read-Only"
                
            # Additional Windows-specific checks using file attributes
            try:
                import stat
                file_stats = os.stat(file_path)
                
                # Check for system or hidden files that might be protected
                if hasattr(stat, 'FILE_ATTRIBUTE_SYSTEM'):
                    # Windows-specific attribute checking would go here
                    # For now, use basic permission checks
                    pass
                    
            except Exception:
                # If detailed checking fails, assume basic permissions are sufficient
                pass
                
            return True, "OK"
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    @staticmethod
    def validate_orphan_file_access(file_path: str) -> tuple[bool, str, dict]:
        """
        Comprehensive validation of orphan file for deletion readiness.
        
        Purpose:
        --------
        Performs detailed validation including existence, permissions, and metadata
        to provide complete status information for orphan file deletion.
        
        Args:
        -----
        file_path: Full path to orphan file to validate
        
        Returns:
        --------
        tuple[bool, str, dict]: (accessible, status_message, metadata_dict)
        """
        try:
            if not os.path.exists(file_path):
                return False, "File Missing", {}
                
            # Get file metadata
            stat_info = os.stat(file_path)
            metadata = {
                'size': stat_info.st_size,
                'modified': stat_info.st_mtime,
                'is_directory': os.path.isdir(file_path)
            }
            
            # Check permissions
            can_delete, permission_status = DeleteOrphansManager_class.check_file_permissions(file_path)
            
            if not can_delete:
                return False, permission_status, metadata
                
            # Check if file is currently in use (Windows-specific)
            try:
                # Try to open file in exclusive mode to check if it's in use
                if os.path.isfile(file_path):
                    with open(file_path, 'r+b'):
                        pass  # File is accessible
            except PermissionError:
                return False, "File In Use", metadata
            except Exception:
                # Other errors are not necessarily blocking
                pass
                
            return True, "OK", metadata
            
        except Exception as e:
            return False, f"Validation Error: {str(e)}", {}
    
    # ========================================================================
    # STATIC UTILITY METHODS - ORPHAN DETECTION AND DATA MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def detect_orphaned_files(comparison_results: Dict, side: str, 
                             active_filter: Optional[str] = None) -> List[str]:
        """
        Detect orphaned files from comparison results - files that exist on one side but are missing on the other.
        
        Purpose:
        --------
        Analyzes comparison results to identify files that exist only on the specified side,
        with optional filter support for consistent behavior with main application.
        
        Args:
        -----
        comparison_results: Dictionary of comparison results from main application
        side: 'left' or 'right' - which side to find orphans for
        active_filter: Optional wildcard filter to respect from main application
        
        Returns:
        --------
        List[str]: List of relative paths of orphaned files on the specified side
        """
        orphaned_paths = []
        
        if not comparison_results:
            log_and_flush(logging.DEBUG, f"No comparison results available for orphan detection on {side} side")
            return orphaned_paths
            
        log_and_flush(logging.DEBUG, f"Detecting orphaned files on {side} side from {len(comparison_results)} comparison results")
        
        for rel_path, result in comparison_results.items():
            if not rel_path:  # Skip empty paths
                continue
                
            # Determine if this item is orphaned on the specified side
            is_orphaned = False
            
            if side == 'left':
                # Left orphan: exists in left but missing in right
                is_orphaned = (result.left_item is not None and 
                              result.left_item.exists and
                              (result.right_item is None or not result.right_item.exists))
            elif side == 'right':
                # Right orphan: exists in right but missing in left  
                is_orphaned = (result.right_item is not None and
                              result.right_item.exists and
                              (result.left_item is None or not result.left_item.exists))
            
            if is_orphaned:
                # Apply filter if active (consistent with main application filtering)
                if active_filter:
                    filename = rel_path.split('/')[-1]  # Get just the filename
                    if not fnmatch.fnmatch(filename.lower(), active_filter.lower()):
                        continue  # Skip files that don't match the filter
                        
                orphaned_paths.append(rel_path)
                
        log_and_flush(logging.INFO, f"Found {len(orphaned_paths)} orphaned files on {side} side")
        if active_filter:
            log_and_flush(logging.INFO, f"Orphan detection used active filter: {active_filter}")
            
        return sorted(orphaned_paths)  # Return in stable alphabetical order

    @staticmethod
    def create_orphan_metadata_dict(comparison_results: Dict, orphaned_paths: List[str], 
                                   side: str, source_folder: str) -> Dict[str, Dict[str, Any]]:
        """
        Create metadata dictionary for orphaned files with validation status.
        
        Purpose:
        --------
        Builds comprehensive metadata for orphaned files including file information,
        validation status, and accessibility for the delete orphans dialog.
        
        Args:
        -----
        comparison_results: Dictionary of comparison results from main application
        orphaned_paths: List of relative paths of orphaned files
        side: 'left' or 'right' - which side the orphans are on
        source_folder: Full path to the source folder
        
        Returns:
        --------
        Dict[str, Dict]: Dictionary mapping rel_path -> metadata dict with validation
        """
        orphan_metadata = {}
        
        for rel_path in orphaned_paths:
            result = comparison_results.get(rel_path)
            if not result:
                continue
                
            # Get the metadata for the correct side
            if side == 'left' and result.left_item:
                file_metadata = result.left_item
            elif side == 'right' and result.right_item:
                file_metadata = result.right_item
            else:
                continue  # No metadata available
                
            # Get full file path
            full_path = str(Path(source_folder) / rel_path)
            
            # Validate file accessibility
            accessible, status_msg, validation_metadata = DeleteOrphansManager_class.validate_orphan_file_access(full_path)
            
            # Create comprehensive metadata entry
            metadata_entry = {
                'rel_path': rel_path,
                'full_path': full_path,
                'name': file_metadata.name,
                'is_folder': file_metadata.is_folder,
                'size': file_metadata.size,
                'date_created': file_metadata.date_created,
                'date_modified': file_metadata.date_modified,
                'sha512': file_metadata.sha512,
                'accessible': accessible,
                'status': status_msg,
                'validation_metadata': validation_metadata,
                'selected': True,  # Default to selected
            }
            
            orphan_metadata[rel_path] = metadata_entry
            
        log_and_flush(logging.DEBUG, f"Created metadata for {len(orphan_metadata)} orphaned files")
        return orphan_metadata

    @staticmethod
    def refresh_orphan_metadata_status(orphan_metadata: Dict[str, Dict[str, Any]]) -> Tuple[int, int]:
        """
        Refresh the validation status of orphaned files to detect external changes.
        
        Purpose:
        --------
        Re-validates accessibility and status of orphaned files to handle cases
        where files were deleted, moved, or permissions changed externally.
        
        Args:
        -----
        orphan_metadata: Dictionary of orphan metadata to refresh
        
        Returns:
        --------
        Tuple[int, int]: (still_accessible_count, changed_count)
        """
        still_accessible = 0
        changed_count = 0
        
        for rel_path, metadata in orphan_metadata.items():
            old_accessible = metadata['accessible']
            old_status = metadata['status']
            
            # Re-validate the file
            accessible, status_msg, validation_metadata = DeleteOrphansManager_class.validate_orphan_file_access(metadata['full_path'])
            
            # Update metadata with current status
            metadata['accessible'] = accessible
            metadata['status'] = status_msg
            metadata['validation_metadata'] = validation_metadata
            
            # Count changes
            if accessible:
                still_accessible += 1
                
            if old_accessible != accessible or old_status != status_msg:
                changed_count += 1
                log_and_flush(logging.DEBUG, f"Status changed for {rel_path}: {old_status} -> {status_msg}")
                
        log_and_flush(logging.INFO, f"Refresh complete: {still_accessible} accessible, {changed_count} status changes detected")
        return still_accessible, changed_count

    @staticmethod
    def build_orphan_tree_structure(orphan_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build hierarchical tree structure from orphaned file metadata.
        
        Purpose:
        --------
        Creates a nested dictionary structure representing the folder hierarchy
        of orphaned files for display in the delete orphans dialog tree.
        
        Args:
        -----
        orphan_metadata: Dictionary of orphan file metadata
        
        Returns:
        --------
        Dict: Nested dictionary representing folder structure
        """
        tree_structure = {}
        
        for rel_path, metadata in orphan_metadata.items():
            if not rel_path:
                continue
                
            path_parts = rel_path.split('/')
            current_level = tree_structure
            
            # Build nested structure
            for i, part in enumerate(path_parts):
                if part not in current_level:
                    # Determine if this is a file or folder
                    is_final_part = (i == len(path_parts) - 1)
                    
                    if is_final_part:
                        # This is the final part - store the metadata
                        current_level[part] = metadata
                    else:
                        # This is a folder - create nested dict
                        current_level[part] = {}
                        
                # Move to next level (only if it's a dict, not metadata)
                if isinstance(current_level[part], dict):
                    current_level = current_level[part]
                    
        log_and_flush(logging.DEBUG, f"Built tree structure with {len(orphan_metadata)} orphaned items")
        return tree_structure

    @staticmethod
    def calculate_orphan_statistics(orphan_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics for orphaned files including totals, sizes, and selection counts.
        
        Purpose:
        --------
        Provides comprehensive statistics for the delete orphans dialog header
        and status updates including size calculations and selection tracking.
        
        Args:
        -----
        orphan_metadata: Dictionary of orphan file metadata
        
        Returns:
        --------
        Dict: Statistics including total files, selected files, total size, selected size, etc.
        """
        stats = {
            'total_files': 0,
            'total_folders': 0,
            'selected_files': 0,
            'selected_folders': 0,
            'total_size': 0,
            'selected_size': 0,
            'accessible_files': 0,
            'inaccessible_files': 0,
            'size_warning_threshold': 1024 * 1024 * 1024,  # 1GB warning threshold
            'large_selection_warning': False
        }
        
        for metadata in orphan_metadata.values():
            # Count totals
            if metadata['is_folder']:
                stats['total_folders'] += 1
                if metadata['selected']:
                    stats['selected_folders'] += 1
            else:
                stats['total_files'] += 1
                if metadata['selected']:
                    stats['selected_files'] += 1
                    
            # Calculate sizes (only for files)
            if not metadata['is_folder'] and metadata['size']:
                stats['total_size'] += metadata['size']
                if metadata['selected']:
                    stats['selected_size'] += metadata['size']
                    
            # Count accessibility
            if metadata['accessible']:
                stats['accessible_files'] += 1
            else:
                stats['inaccessible_files'] += 1
                
        # Set warning flags
        if stats['selected_size'] > stats['size_warning_threshold']:
            stats['large_selection_warning'] = True
            
        return stats
    
    # ========================================================================
    # INSTANCE METHODS - DIALOG INITIALIZATION AND MANAGEMENT
    # ========================================================================
    
    def __init__(self, parent, orphaned_files, side, source_folder, dry_run_mode, 
                 comparison_results, active_filter=None):
        """
        Initialize the Delete Orphans Manager/Dialog.
        
        Args:
        -----
        parent: Parent window for modal dialog
        orphaned_files: List of relative paths of orphaned files
        side: 'left' or 'right' - which side orphans are on
        source_folder: Full path to source folder
        dry_run_mode: Whether main app is in dry run mode
        comparison_results: Main app comparison results for metadata
        active_filter: Current filter from main app (if any)
        """
        self.parent = parent
        self.orphaned_files = orphaned_files.copy()  # Create local copy
        self.side = side
        self.source_folder = source_folder
        self.dry_run_mode = dry_run_mode  # v001.0013 Keep original for reference only
        self.comparison_results = comparison_results
        self.active_filter = active_filter
        
        # Dialog state variables
        self.deletion_method = tk.StringVar(value="recycle_bin")  # Default to safer option
        self.local_dry_run_mode = tk.BooleanVar(value=dry_run_mode)  # v001.0013 added [local dry run mode for delete orphans dialog]
        self.dialog_filter = tk.StringVar()  # Dialog-specific filter
        self.result = None  # Result of dialog operation
        
        # Large data structures for memory management
        self.orphan_metadata = {}
        self.orphan_tree_data = {}
        self.selected_items = set()
        self.path_to_item_map = {}
        
        # UI References
        self.dialog = None
        self.tree = None
        self.statistics_var = tk.StringVar()
        self.status_log_text = None
        self.status_log_lines = []
        
        # Memory management thresholds (local constants)
        self.LARGE_FILE_LIST_THRESHOLD = DELETE_LARGE_FILE_LIST_THRESHOLD
        self.LARGE_TREE_DATA_THRESHOLD = DELETE_LARGE_TREE_DATA_THRESHOLD
        self.LARGE_SELECTION_THRESHOLD = DELETE_LARGE_SELECTION_THRESHOLD
        
        # Initialize dialog
        self.setup_dialog()
        
    def setup_dialog(self):
        """Create and configure the modal dialog window."""
        # Create modal dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Delete Orphaned Files - {self.side.upper()} Side")
        
        # Calculate dialog size based on parent
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        dialog_width = int(parent_width * DELETE_ORPHANS_DIALOG_WIDTH_PERCENT)
        dialog_height = int(parent_height * DELETE_ORPHANS_DIALOG_HEIGHT_PERCENT)
        
        # Position at top of screen like main window
        x = self.parent.winfo_x() + (parent_width - dialog_width) // 2
        y = 0  # Top of screen
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()  # Modal dialog
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)
        
        # Setup UI components
        self.setup_ui()
        
        # Initialize with orphan data
        self.initialize_orphan_data()
        
    def add_status_message(self, message):
        """Add timestamped message to dialog status log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_line = f"{timestamp} - {message}"
        
        self.status_log_lines.append(status_line)
        
        # Trim to maximum lines
        if len(self.status_log_lines) > DELETE_ORPHANS_STATUS_MAX_HISTORY:
            self.status_log_lines = self.status_log_lines[-DELETE_ORPHANS_STATUS_MAX_HISTORY:]
            
        # Update text widget
        if self.status_log_text:
            self.status_log_text.config(state=tk.NORMAL)
            self.status_log_text.delete('1.0', tk.END)
            self.status_log_text.insert('1.0', '\n'.join(self.status_log_lines))
            self.status_log_text.config(state=tk.DISABLED)
            self.status_log_text.see(tk.END)
            
        log_and_flush(logging.DEBUG, f"Delete Orphans Manager STATUS: {message}")
        
    def initialize_orphan_data(self):
        """Initialize orphan metadata and build tree structure."""
        if not self.orphaned_files:
            self.add_status_message("No orphaned files found")
            return
            
        self.add_status_message(f"Initializing {len(self.orphaned_files)} orphaned files...")
        
        # Show progress for large datasets
        if len(self.orphaned_files) > 1000:
            progress = ProgressDialog(
                self.dialog, 
                "Loading Orphan Files", 
                "Building orphan file tree...",
                max_value=100
            )
            threading.Thread(
                target=self._initialize_data_with_progress, 
                args=(progress,), 
                daemon=True
            ).start()
        else:
            # Small dataset - initialize directly
            self._initialize_data_direct()
            
    def _initialize_data_direct(self):
        """Initialize orphan data directly for small datasets."""
        # Create metadata with validation
        self.orphan_metadata = self.create_orphan_metadata_dict(
            self.comparison_results, 
            self.orphaned_files, 
            self.side, 
            self.source_folder
        )
        
        # Build tree structure
        self.orphan_tree_data = self.build_orphan_tree_structure(self.orphan_metadata)
        
        # Select all items by default
        self.selected_items = set(self.orphaned_files)
        
        # Log details about inaccessible files # v001.0013 added [detailed logging for inaccessible files]
        self.log_inaccessible_files() # v001.0013 added [detailed logging for inaccessible files]
        
        # Update UI
        self.build_orphan_tree()
        self.update_statistics()
        
        # Log initialization results
        accessible_count = sum(1 for m in self.orphan_metadata.values() if m['accessible'])
        self.add_status_message(f"Initialization complete: {accessible_count} accessible files")
        
    def _initialize_data_with_progress(self, progress):
        """Initialize orphan data with progress feedback for large datasets."""
        try:
            progress.update_progress(10, "Creating file metadata...")
            
            # Create metadata with validation
            self.orphan_metadata = self.create_orphan_metadata_dict(
                self.comparison_results, 
                self.orphaned_files, 
                self.side, 
                self.source_folder
            )
            
            progress.update_progress(50, "Building tree structure...")
            
            # Build tree structure
            self.orphan_tree_data = self.build_orphan_tree_structure(self.orphan_metadata)
            
            progress.update_progress(80, "Setting up selections...")
            
            # Select all items by default
            self.selected_items = set(self.orphaned_files)
            
            progress.update_progress(90, "Updating display...")
            
            # Update UI in main thread
            self.dialog.after(0, self._finalize_initialization)
            
            progress.update_progress(100, "Complete")
            
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error during orphan data initialization: {e}")
            self.dialog.after(0, lambda: self.add_status_message(f"Initialization error: {str(e)}"))
        finally:
            progress.close()
            
    def _finalize_initialization(self):
        """Finalize initialization in main thread."""
        # Log details about inaccessible files # v001.0013 added [detailed logging for inaccessible files in large datasets]
        self.log_inaccessible_files() # v001.0013 added [detailed logging for inaccessible files in large datasets]
        
        self.build_orphan_tree()
        self.update_statistics()
        
        # Log results
        accessible_count = sum(1 for m in self.orphan_metadata.values() if m['accessible'])
        self.add_status_message(f"Initialization complete: {accessible_count} accessible files")
        
    def _cleanup_large_data(self):
        """Clean up large data structures based on thresholds."""
        cleaned_items = []
        
        if len(self.orphaned_files) > self.LARGE_FILE_LIST_THRESHOLD:
            self.orphaned_files.clear()
            cleaned_items.append("file list")
            
        if len(self.orphan_tree_data) > self.LARGE_TREE_DATA_THRESHOLD:
            self.orphan_tree_data.clear()
            cleaned_items.append("tree data")
            
        if len(self.selected_items) > self.LARGE_SELECTION_THRESHOLD:
            self.selected_items.clear()
            cleaned_items.append("selections")
            
        if len(self.orphan_metadata) > self.LARGE_FILE_LIST_THRESHOLD:
            self.orphan_metadata.clear()
            cleaned_items.append("metadata")
            
        if len(self.path_to_item_map) > self.LARGE_TREE_DATA_THRESHOLD:
            self.path_to_item_map.clear()
            cleaned_items.append("path mappings")
            
        if cleaned_items:
            log_and_flush(logging.DEBUG, f"Cleaned up large data structures: {', '.join(cleaned_items)}")
            
    def close_dialog(self):
        """Close dialog with proper cleanup."""
        try:
            # Clean up large data structures
            self._cleanup_large_data()
            
            # Close dialog
            if self.dialog:
                self.dialog.grab_release()
                self.dialog.destroy()
                
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error during dialog cleanup: {e}")
        finally:
            # Ensure dialog is closed even if cleanup fails
            try:
                if self.dialog:
                    self.dialog.destroy()
            except:
                pass

    # ========================================================================
    # INSTANCE METHODS - UI SETUP AND CONFIGURATION
    # ========================================================================
    
    def setup_ui(self):
        """Setup all UI components for the delete orphans dialog."""
        # v001.0014 added [create scaled fonts for delete orphans dialog]
        # Create scaled fonts for this dialog
        log_and_flush(logging.DEBUG, "ENTERED DeleteOrphansManager_class.setup_ui")

        default_font = tkfont.nametofont("TkDefaultFont") # v001.0014 added [create scaled fonts for delete orphans dialog]
        
        self.scaled_label_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_label_font.configure(size=SCALED_LABEL_FONT_SIZE) # v001.0014 added [create scaled fonts for delete orphans dialog]
        # Create a bold version
        self.scaled_label_font_bold = self.scaled_label_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_label_font_bold.configure(weight="bold")
        
        self.scaled_entry_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_entry_font.configure(size=SCALED_ENTRY_FONT_SIZE) # v001.0014 added [create scaled fonts for delete orphans dialog]
        
        self.scaled_checkbox_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_checkbox_font.configure(size=SCALED_CHECKBOX_FONT_SIZE) # v001.0014 added [create scaled fonts for delete orphans dialog]
        # Create a bold version
        self.scaled_checkbox_font_bold = self.scaled_checkbox_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_checkbox_font_bold.configure(weight="bold")
        
        self.scaled_button_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_button_font.configure(size=SCALED_BUTTON_FONT_SIZE)
        # Create a bold version
        self.scaled_button_font_bold = self.scaled_button_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_button_font_bold.configure(weight="bold")
        
        # Configure tree row height for this dialog's treeviews # v001.0015 added [tree row height control for compact display]
        dialog_style = ttk.Style(self.dialog) # v001.0015 added [tree row height control for compact display]
        dialog_style.configure("Treeview", rowheight=TREE_ROW_HEIGHT) # v001.0015 added [tree row height control for compact display]
        
        # v001.0016 added [create button styles for delete orphans dialog]
        # Create button styles for this dialog
        dialog_style.configure("DeleteOrphansDefaultNormal.TButton", font=self.scaled_button_font) # v001.0016 added [create button styles for delete orphans dialog]
        dialog_style.configure("DeleteOrphansRedBold.TButton", foreground="red", font=self.scaled_button_font_bold) # v001.0014 added [create button style for delete orphans dialog with scaled font]
        dialog_style.configure("DeleteOrphansBlueBold.TButton", foreground="blue", font=self.scaled_button_font_bold) # v001.0014 added [create button style for delete orphans dialog with scaled font]

        dialog_style.configure("DeleteOrphansCheckbutton.TCheckbutton", font=self.scaled_checkbox_font)
        dialog_style.configure("DeleteOrphansLabel.TLabel", font=self.scaled_label_font)
        dialog_style.configure("DeleteOrphansSmallLabel.TLabel", font=(self.scaled_label_font.cget("family"), int(self.scaled_label_font.cget("size")) - 1))
        dialog_style.configure("DeleteOrphansLabelBold.TLabel", font=self.scaled_label_font_bold)
        dialog_style.configure("DeleteOrphansEntry.TEntry", font=self.scaled_entry_font)

        # Main container
        log_and_flush(logging.DEBUG, "BEFORE THE CREATE AND PACK main_frame")
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8) # v001.0014 changed [tightened padding from padx=10, pady=10 to padx=8, pady=8]
        log_and_flush(logging.DEBUG, "AFTER THE CREATE AND PACK main_frame")
        
        # Header section with explanation and statistics
        log_and_flush(logging.DEBUG, "BEFORE setup_header_section")
        self.setup_header_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_header_section")
        
        # Local dry run mode section # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "BEFORE setup_local_dry_run_section")
        self.setup_local_dry_run_section(main_frame) # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "AFTER setup_local_dry_run_section")
        
        # Deletion method selection
        log_and_flush(logging.DEBUG, "BEFORE setup_deletion_method_section")
        self.setup_deletion_method_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_deletion_method_section")
        
        # Filter controls
        log_and_flush(logging.DEBUG, "BEFORE setup_filter_section")
        self.setup_filter_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_filter_section")
        
        # Main tree area
        log_and_flush(logging.DEBUG, "BEFORE setup_tree_section")
        self.setup_tree_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_tree_section")
        
        # Status log area
        log_and_flush(logging.DEBUG, "BEFORE setup_status_section")
        self.setup_status_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_status_section")
        
        # Bottom buttons
        log_and_flush(logging.DEBUG, "BEFORE setup_button_section")
        self.setup_button_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_button_section")

        log_and_flush(logging.DEBUG, "EXITING DeleteOrphansManager_class.setup_ui")

    def setup_header_section(self, parent):
        """Setup header section with explanation and statistics."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Explanatory text
        side_text = self.side.upper()
        opposite_side = "RIGHT" if self.side == "left" else "LEFT"
        
        explanation = (
            f"The following orphaned files exist in {side_text} but are missing in {opposite_side}.\n"
            f"Select which files to delete, then click 'DELETE SELECTED ORPHANED FILES' to remove them permanently."
        )
        
        explanation_label = ttk.Label(
            header_frame, 
            text=explanation, 
            justify=tk.CENTER,
            style="DeleteOrphansLabel.TLabel"  # ✅ Use style instead of font parameter
        )
        explanation_label.pack(pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Statistics display
        self.statistics_var.set("Loading orphaned files...")
        statistics_label = ttk.Label(
            header_frame,
            textvariable=self.statistics_var,
            foreground="blue",
            style="DeleteOrphansLabelBold.TLabel"  # ✅ Use bold style
        )
        statistics_label.pack(pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]

    def setup_local_dry_run_section(self, parent): # v001.0013 added [local dry run mode section for delete orphans dialog]
        """Setup local dry run mode section with checkbox.""" # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "1. ENTERED DeleteOrphansManager_class.setup_local_dry_run_section")

        log_and_flush(logging.DEBUG, "2. BEFORE create and pack dry_run_frame")
        dry_run_frame = ttk.LabelFrame(parent, text="Local Operation Mode", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        dry_run_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        log_and_flush(logging.DEBUG, "3. AFTER create and pack dry_run_frame")
        
        # Checkbox for local dry run mode # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "4. BEFORE create and pack dry_run_cb checkbutton create")
        dry_run_cb = ttk.Checkbutton( # v001.0013 added [local dry run mode section for delete orphans dialog]
            dry_run_frame, # v001.0013 added [local dry run mode section for delete orphans dialog]
            text="DRY RUN Only (simulate deletion without actually removing files)", # v001.0013 added [local dry run mode section for delete orphans dialog]
            variable=self.local_dry_run_mode, # v001.0013 added [local dry run mode section for delete orphans dialog]
            command=self.on_local_dry_run_changed, # v001.0013 added [local dry run mode section for delete orphans dialog]
            style="DeleteOrphansCheckbutton.TCheckbutton" # v001.0014 changed [use scaled checkbox font instead of default]
        ) # v001.0013 added [local dry run mode section for delete orphans dialog]
        dry_run_cb.pack(side=tk.LEFT, padx=(0, 10)) # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "5. AFTER create and pack dry_run_cb checkbutton create")
        
        # Status indicator showing main app setting # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "6. BEFORE create and pack main_app_text create")
        main_app_text = f"(Main app DRY RUN mode: {'ON' if self.dry_run_mode else 'OFF'})" # v001.0013 added [local dry run mode section for delete orphans dialog]
        main_app_label = ttk.Label( # v001.0013 added [local dry run mode section for delete orphans dialog]
            dry_run_frame, # v001.0013 added [local dry run mode section for delete orphans dialog]
            text=main_app_text, # v001.0013 added [local dry run mode section for delete orphans dialog]
            foreground="gray", # v001.0013 added [local dry run mode section for delete orphans dialog]
            style="DeleteOrphansSmallLabel.TLabel"
        ) # v001.0013 added [local dry run mode section for delete orphans dialog]
        main_app_label.pack(side=tk.LEFT) # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "7. AFTER create and pack main_app_text create")
        
        # Explanation text # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "8. BEFORE create and pack explanation_label create")
        explanation_label = ttk.Label( # v001.0013 added [local dry run mode section for delete orphans dialog]
            dry_run_frame, # v001.0013 added [local dry run mode section for delete orphans dialog]
            text="This setting is local to this dialog and overrides the main app setting", # v001.0013 added [local dry run mode section for delete orphans dialog]
            foreground="blue", # v001.0013 added [local dry run mode section for delete orphans dialog]
            style="DeleteOrphansSmallLabel.TLabel"
        ) # v001.0013 added [local dry run mode section for delete orphans dialog]
        explanation_label.pack(pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
        log_and_flush(logging.DEBUG, "9. AFTER create and pack explanation_label create")
        log_and_flush(logging.DEBUG, "10. EXITING DeleteOrphansManager_class.setup_local_dry_run_section")

    def setup_deletion_method_section(self, parent):
        """Setup deletion method selection with radio buttons."""
        method_frame = ttk.LabelFrame(parent, text="Deletion Method", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        method_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Radio button frame
        radio_frame = ttk.Frame(method_frame)
        radio_frame.pack()
        
        # Recycle Bin option (default, safer)
        recycle_rb = ttk.Radiobutton(
            radio_frame,
            text="Move to Recycle Bin (recommended)",
            variable=self.deletion_method,
            value="recycle_bin",
            style="DeleteOrphansCheckbutton.TCheckbutton"  # ✅ Reuse checkbox style for radio buttons        
            recycle_rb.pack(side=tk.LEFT, padx=(0, 20))
        )
        recycle_rb.pack(side=tk.LEFT, padx=(0, 20))

        # Permanent deletion option
        permanent_rb = ttk.Radiobutton(
            radio_frame,
            text="Permanent Deletion (cannot be undone)",
            variable=self.deletion_method,
            value="permanent",
            style="DeleteOrphansCheckbutton.TCheckbutton"  # ✅ Reuse checkbox style for radio buttons
        )
        permanent_rb.pack(side=tk.LEFT)
        
        # Add warning text
        warning_label = ttk.Label(
            method_frame,
            text="⚠ Permanent deletion cannot be undone - files will be lost forever",
            foreground="red",
            style="DeleteOrphansSmallLabel.TLabel"  # ✅ Use style instead of font tuple
        )
        warning_label.pack(pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
        
    def setup_filter_section(self, parent):
        """Setup dialog-specific filter controls."""
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Filter label and entry
        ttk.Label(filter_frame, text="Filter Files:", style="DeleteOrphansLabel.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        filter_entry = ttk.Entry(filter_frame, textvariable=self.dialog_filter, width=20, style="DeleteOrphansEntry.TEntry")
        filter_entry.pack(side=tk.LEFT, padx=(0, 5))
        filter_entry.bind('<Return>', lambda e: self.apply_filter())
        
        # Filter buttons
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        ttk.Button(filter_frame, text="Clear Filter", command=self.clear_filter, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0016 changed [use delete orphans button style]
        
        # Filter status
        self.filter_status_var = tk.StringVar()
        if self.active_filter:
            self.filter_status_var.set(f"(Main app filter active: {self.active_filter})")
        else:
            self.filter_status_var.set("")
            
        filter_status_label = ttk.Label(filter_frame, textvariable=self.filter_status_var,
                                       foreground="gray", style="DeleteOrphansSmallLabel.TLabel")
        filter_status_label.pack(side=tk.LEFT)
        
    def setup_tree_section(self, parent):
        """Setup main tree display area."""
        tree_frame = ttk.LabelFrame(parent, text="Orphaned Files", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create tree with scrollbar
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_container, show='tree headings', selectmode='none')
        self.tree.heading('#0', text='File/Folder Structure', anchor=tk.W)
        self.tree.column('#0', width=DELETE_ORPHANS_TREE_STRUCTURE_WIDTH, minwidth=200)
        
        # Setup tree columns
        self.setup_tree_columns()
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind tree events
        self.tree.bind('<Button-1>', self.handle_tree_click)
        
    def setup_tree_columns(self):
        """Setup tree columns for metadata display."""
        self.tree['columns'] = ('size', 'date_created', 'date_modified', 'status')
        
        # Column headers
        self.tree.heading('size', text='Size', anchor=tk.E)
        self.tree.heading('date_created', text='Date Created', anchor=tk.CENTER)
        self.tree.heading('date_modified', text='Date Modified', anchor=tk.CENTER)
        self.tree.heading('status', text='Status', anchor=tk.W)
        
        # Column widths
        self.tree.column('size', width=DELETE_ORPHANS_TREE_SIZE_WIDTH, minwidth=60, anchor=tk.E)
        self.tree.column('date_created', width=150, minwidth=120, anchor=tk.CENTER)
        self.tree.column('date_modified', width=150, minwidth=120, anchor=tk.CENTER)
        self.tree.column('status', width=DELETE_ORPHANS_TREE_STATUS_WIDTH, minwidth=80, anchor=tk.W)
        
    def setup_status_section(self, parent):
        """Setup status log area."""
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding=5)
        status_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Status header with export button
        status_header = ttk.Frame(status_frame)
        status_header.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        ttk.Label(status_header, text=f"Operation History ({DELETE_ORPHANS_STATUS_MAX_HISTORY:,} lines max):", 
                 style="DeleteOrphansLabel.TLabel").pack(side=tk.LEFT)
        ttk.Button(status_header, text="Export Log", command=self.export_status_log, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.RIGHT)
        
        # Status log text area
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=tk.X)
        
        self.status_log_text = tk.Text(
            status_container,
            height=DELETE_ORPHANS_STATUS_LINES,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier", SCALED_STATUS_MESSAGE_FONT_SIZE),  # tk.Text supports font parameter
            bg="#f8f8f8",
            fg="#333333"
        )
        
        status_scroll = ttk.Scrollbar(status_container, orient=tk.VERTICAL, command=self.status_log_text.yview)
        self.status_log_text.configure(yscrollcommand=status_scroll.set)
        
        self.status_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_button_section(self, parent):
        """Setup bottom button section."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        # Left side utility buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="Select All", command=self.select_all_items, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        ttk.Button(left_buttons, text="Clear All", command=self.clear_all_items, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        ttk.Button(left_buttons, text="Refresh Orphans Tree", command=self.refresh_orphans_tree, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        
        # Right side action buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="Cancel", command=self.close_dialog, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.RIGHT, padx=(5, 0)) # v001.0016 changed [use delete orphans button style]
        
        # Delete button with conditional text based on local dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        delete_text = "SIMULATE DELETION" if is_local_dry_run else "DELETE SELECTED ORPHANED FILES" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        self.delete_button = ttk.Button( # v001.0013 changed [store button reference for dynamic updates]
            right_buttons, 
            text=delete_text, 
            command=self.delete_selected_files
        )
        self.delete_button.pack(side=tk.RIGHT, padx=(5, 0)) # v001.0013 changed [use stored button reference]
        
        # Style the delete button based on local dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            # Use blue style for simulation
            self.delete_button.configure(style="DeleteOrphansBlueBold.TButton") # v001.0014 changed [use local scaled button style instead of main app style]
        else:
            # Use red style for actual deletion
            self.delete_button.configure(style="DeleteOrphansRedBold.TButton") # v001.0014 changed [use local scaled button style instead of main app style]
                                                                                                          
    def export_status_log(self):
        """Export status log to clipboard and optionally to file."""
        if not self.status_log_lines:
            messagebox.showinfo("Export Status Log", "No status log data to export.")
            return
        
        try:
            # Copy to clipboard
            export_text = "\n".join(self.status_log_lines)
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(export_text)
            self.dialog.update()
            
            # Ask about saving to file
            response = messagebox.askyesnocancel(
                "Export Status Log",
                f"Status log ({len(self.status_log_lines):,} lines) copied to clipboard!\n\n"
                "Would you also like to save to a file?"
            )
            
            if response is True:  # Yes - save to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                default_filename = f"foldercomparesync_delete_{self.side}_{timestamp}.log"
                
                file_path = filedialog.asksaveasfilename(
                    title="Save Delete Orphans Log",
                    defaultextension=".log",
                    initialname=default_filename,
                    filetypes=[
                        ("Log files", "*.log"),
                        ("Text files", "*.txt"),
                        ("All files", "*.*")
                    ]
                )
                
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(export_text)
                    self.add_status_message(f"Status log exported to: {file_path}")
                    messagebox.showinfo("Export Complete", f"Status log saved to:\n{file_path}")
                    
        except Exception as e:
            error_msg = f"Failed to export status log: {str(e)}"
            self.add_status_message(f"ERROR: {error_msg}")
            messagebox.showerror("Export Error", error_msg)

    # ========================================================================
    # INSTANCE METHODS - TREE BUILDING AND INTERACTION
    # ========================================================================
    
    def build_orphan_tree(self):
        """Build the orphan file tree display."""
        if not self.tree:
            return
            
        # Clear existing tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.path_to_item_map.clear()
        
        if not self.orphan_tree_data:
            self.add_status_message("No orphan tree data to display")
            return
            
        # Build tree from structure
        self.add_status_message("Building orphan file tree...")
        
        # Use alphabetical ordering for stability
        self.populate_orphan_tree(self.tree, self.orphan_tree_data, '', '')
        
        # Expand all items by default
        self.expand_all_tree_items()
        
        # Update display with selections
        self.update_tree_display()
        
        self.add_status_message(f"Tree built with {len(self.orphan_metadata)} items")
        
    def populate_orphan_tree(self, tree, structure, parent_id, current_path):
        """Recursively populate tree with orphan file structure."""
        if not structure:
            return
            
        # Process items in alphabetical order for stability
        for name in sorted(structure.keys()):
            content = structure[name]
            
            # Build the relative path for this item
            item_rel_path = current_path + ('/' if current_path else '') + name
            
            if isinstance(content, dict) and 'rel_path' in content:
                # This is a file metadata entry
                metadata = content
                
                # Format file display
                size_str = format_size(metadata['size']) if metadata['size'] else ""
                date_created_str = format_timestamp(metadata['date_created'])
                date_modified_str = format_timestamp(metadata['date_modified'])
                status_str = metadata['status']
                
                # Create item text with checkbox
                if metadata['accessible']:
                    checkbox = "☑" if metadata['rel_path'] in self.selected_items else "☐"
                    item_text = f"{checkbox} {name}"
                    tags = ()
                else:
                    # Inaccessible files - no checkbox, grayed out
                    item_text = f"{name} (inaccessible)"
                    tags = ('inaccessible',)
                
                # Insert file item
                item_id = tree.insert(
                    parent_id, 
                    tk.END, 
                    text=item_text,
                    values=(size_str, date_created_str, date_modified_str, status_str),
                    tags=tags
                )
                
                # Store path mapping
                self.path_to_item_map[metadata['rel_path']] = item_id
                
            else:
                # This is a folder - create folder entry and recurse
                folder_checkbox = "☑" if self.is_folder_selected(item_rel_path) else "☐"
                folder_text = f"{folder_checkbox} {name}/"
                
                folder_id = tree.insert(
                    parent_id,
                    tk.END,
                    text=folder_text,
                    values=("", "", "", "Folder"),
                    open=True  # Expand by default
                )
                
                # Recursively populate children
                if isinstance(content, dict):
                    self.populate_orphan_tree(tree, content, folder_id, item_rel_path)
                    
    def is_folder_selected(self, folder_path):
        """Check if a folder should be considered selected based on its children."""
        # A folder is selected if any of its children are selected
        for rel_path in self.selected_items:
            if rel_path.startswith(folder_path + '/') or rel_path == folder_path:
                return True
        return False
        
    def expand_all_tree_items(self):
        """Expand all tree items by default."""
        def expand_recursive(item=''):
            children = self.tree.get_children(item)
            for child in children:
                self.tree.item(child, open=True)
                expand_recursive(child)
        
        expand_recursive()
        
    def handle_tree_click(self, event):
        """Handle clicks on tree items for selection toggle."""
        # Ignore clicks on column headers or separators
        element = self.tree.identify('element', event.x, event.y)
        region = self.tree.identify('region', event.x, event.y)
        
        if element == 'Treeitem.indicator' or region in ('heading', 'separator'):
            return
            
        item_id = self.tree.identify('item', event.x, event.y)
        if item_id:
            # Check if item is accessible (has checkbox)
            item_text = self.tree.item(item_id, 'text')
            if '(inaccessible)' in item_text:
                self.add_status_message("Cannot select inaccessible file")
                return
                
            # Find the relative path for this item
            rel_path = self.find_rel_path_for_item(item_id)
            
            if rel_path:
                self.toggle_item_selection(rel_path)
            else:
                # This might be a folder - handle folder selection
                self.handle_folder_selection(item_id)
                
    def find_rel_path_for_item(self, item_id):
        """Find relative path for a tree item."""
        for rel_path, mapped_item_id in self.path_to_item_map.items():
            if mapped_item_id == item_id:
                return rel_path
        return None
        
    def handle_folder_selection(self, folder_item_id):
        """Handle selection/deselection of folder items."""
        # Get all children of this folder
        folder_children = self.get_folder_children_paths(folder_item_id)
        
        if not folder_children:
            return
            
        # Check current selection state of children
        children_selected = [path for path in folder_children if path in self.selected_items]
        
        if len(children_selected) == len(folder_children):
            # All children selected - deselect all
            for path in folder_children:
                self.selected_items.discard(path)
            self.add_status_message(f"Deselected folder contents: {len(folder_children)} items")
        else:
            # Not all children selected - select all accessible ones
            accessible_children = [
                path for path in folder_children 
                if self.orphan_metadata.get(path, {}).get('accessible', False)
            ]
            self.selected_items.update(accessible_children)
            self.add_status_message(f"Selected folder contents: {len(accessible_children)} accessible items")
            
        # Update display and statistics
        self.update_tree_display()
        self.update_statistics()
        
    def get_folder_children_paths(self, folder_item_id):
        """Get all file paths that are children of a folder item."""
        children_paths = []
        
        def collect_children(item_id):
            for child_id in self.tree.get_children(item_id):
                # Check if this child is a file (has a path mapping)
                child_path = self.find_rel_path_for_item(child_id)
                if child_path:
                    children_paths.append(child_path)
                else:
                    # This is a subfolder - recurse
                    collect_children(child_id)
                    
        collect_children(folder_item_id)
        return children_paths
        
    def toggle_item_selection(self, rel_path):
        """Toggle selection state of a single item."""
        if not rel_path or rel_path not in self.orphan_metadata:
            return
            
        metadata = self.orphan_metadata[rel_path]
        if not metadata['accessible']:
            self.add_status_message(f"Cannot select inaccessible file: {rel_path}")
            return
            
        # Toggle selection
        if rel_path in self.selected_items:
            self.selected_items.discard(rel_path)
            action = "Deselected"
        else:
            self.selected_items.add(rel_path)
            action = "Selected"
            
        self.add_status_message(f"{action}: {rel_path}")
        
        # Update display and statistics
        self.update_tree_display()
        self.update_statistics()
        
    def update_tree_display(self):
        """Update tree display to show current selection state."""
        for rel_path, item_id in self.path_to_item_map.items():
            metadata = self.orphan_metadata.get(rel_path)
            if not metadata:
                continue
                
            current_text = self.tree.item(item_id, 'text')
            
            if metadata['accessible']:
                # Remove existing checkbox
                if current_text.startswith('☑ ') or current_text.startswith('☐ '):
                    name = current_text[2:]
                else:
                    name = current_text
                    
                # Add appropriate checkbox
                if rel_path in self.selected_items:
                    new_text = f"☑ {name}"
                else:
                    new_text = f"☐ {name}"
                    
                self.tree.item(item_id, text=new_text)
                
        # Update folder checkboxes
        self.update_folder_checkboxes()
        
    def update_folder_checkboxes(self):
        """Update folder checkbox states based on children."""
        def update_folder_recursive(item_id):
            children = self.tree.get_children(item_id)
            for child_id in children:
                child_text = self.tree.item(child_id, 'text')
                
                # If this is a folder (ends with /), update its checkbox
                if child_text.endswith('/') or '/' in child_text:
                    child_paths = self.get_folder_children_paths(child_id)
                    
                    if child_paths:
                        selected_children = [p for p in child_paths if p in self.selected_items]
                        
                        # Extract folder name
                        if child_text.startswith('☑ ') or child_text.startswith('☐ '):
                            folder_name = child_text[2:]
                        else:
                            folder_name = child_text
                            
                        # Update checkbox based on children selection
                        if len(selected_children) == len(child_paths) and len(child_paths) > 0:
                            new_text = f"☑ {folder_name}"
                        else:
                            new_text = f"☐ {folder_name}"
                            
                        self.tree.item(child_id, text=new_text)
                        
                # Recurse for subfolders
                update_folder_recursive(child_id)
                
        # Start from root
        update_folder_recursive('')
        
    def update_statistics(self):
        """Update statistics display based on current selections."""
        if not self.orphan_metadata:
            self.statistics_var.set("No orphaned files")
            return
            
        stats = self.calculate_orphan_statistics(self.orphan_metadata)
        
        # Update selection flags in metadata
        for rel_path, metadata in self.orphan_metadata.items():
            metadata['selected'] = rel_path in self.selected_items
            
        # Recalculate with updated selections
        stats = self.calculate_orphan_statistics(self.orphan_metadata)
        
        # Format statistics message
        total_items = stats['total_files'] + stats['total_folders']
        selected_items = stats['selected_files'] + stats['selected_folders']
        
        stats_text = f"{selected_items} of {total_items} orphaned items selected"
        
        if stats['selected_size'] > 0:
            size_text = format_size(stats['selected_size'])
            stats_text += f" ({size_text})"
            
        if stats['large_selection_warning']:
            stats_text += " - WARNING: Large files selected"
            
        if stats['inaccessible_files'] > 0:
            stats_text += f" - {stats['inaccessible_files']} inaccessible"
            
            # Add quick tip for users about inaccessible files # v001.0013 added [quick status message for inaccessible files]
            if hasattr(self, '_last_inaccessible_count'): # v001.0013 added [quick status message for inaccessible files]
                # Only show message if count changed or first time # v001.0013 added [quick status message for inaccessible files]
                if self._last_inaccessible_count != stats['inaccessible_files']: # v001.0013 added [quick status message for inaccessible files]
                    self.add_status_message(f"NOTE: {stats['inaccessible_files']} files are inaccessible and cannot be deleted (see detailed log above)") # v001.0013 added [quick status message for inaccessible files]
            else: # v001.0013 added [quick status message for inaccessible files]
                # First time showing inaccessible files # v001.0013 added [quick status message for inaccessible files]
                self.add_status_message(f"NOTE: {stats['inaccessible_files']} files are inaccessible and cannot be deleted (see detailed log above)") # v001.0013 added [quick status message for inaccessible files]
            
            self._last_inaccessible_count = stats['inaccessible_files'] # v001.0013 added [quick status message for inaccessible files]
            
        self.statistics_var.set(stats_text)

    # ========================================================================
    # INSTANCE METHODS - FILTER, SELECTION, AND DELETION OPERATIONS
    # ========================================================================
    
    def apply_filter(self):
        """Apply dialog-specific filter to orphan tree display."""
        filter_pattern = self.dialog_filter.get().strip()
        
        if not filter_pattern:
            self.add_status_message("No filter pattern specified")
            return
            
        if not self.orphan_metadata:
            self.add_status_message("No orphan data to filter")
            return
            
        self.add_status_message(f"Applying filter: {filter_pattern}")
        
        # Filter the metadata
        filtered_metadata = {}
        
        for rel_path, metadata in self.orphan_metadata.items():
            filename = rel_path.split('/')[-1]
            
            # Apply filter to files only, not folders
            if not metadata['is_folder']:
                if fnmatch.fnmatch(filename.lower(), filter_pattern.lower()):
                    filtered_metadata[rel_path] = metadata
            else:
                # Always include folders that contain matching files
                folder_has_matches = False
                for other_path in self.orphan_metadata:
                    if other_path.startswith(rel_path + '/'):
                        other_filename = other_path.split('/')[-1]
                        if fnmatch.fnmatch(other_filename.lower(), filter_pattern.lower()):
                            folder_has_matches = True
                            break
                            
                if folder_has_matches:
                    filtered_metadata[rel_path] = metadata
                    
        # Rebuild tree with filtered data
        original_count = len(self.orphan_metadata)
        self.orphan_metadata = filtered_metadata
        self.orphan_tree_data = self.build_orphan_tree_structure(self.orphan_metadata)
        
        # Update selected items to only include filtered items
        self.selected_items = self.selected_items.intersection(set(filtered_metadata.keys()))
        
        # Rebuild tree display
        self.build_orphan_tree()
        self.update_statistics()
        
        filtered_count = len(filtered_metadata)
        self.add_status_message(f"Filter applied: {filtered_count} of {original_count} items match '{filter_pattern}'")
        
    def clear_filter(self):
        """Clear dialog-specific filter and restore full orphan list."""
        self.dialog_filter.set("")
        
        if not self.orphaned_files:
            self.add_status_message("No original orphan data to restore")
            return
            
        self.add_status_message("Clearing filter - restoring full orphan list...")
        
        # Rebuild full metadata
        self.orphan_metadata = self.create_orphan_metadata_dict(
            self.comparison_results,
            self.orphaned_files,
            self.side,
            self.source_folder
        )
        
        # Rebuild tree structure
        self.orphan_tree_data = self.build_orphan_tree_structure(self.orphan_metadata)
        
        # Rebuild tree display
        self.build_orphan_tree()
        self.update_statistics()
        
        self.add_status_message(f"Filter cleared - showing all {len(self.orphan_metadata)} orphaned items")
        
    def select_all_items(self):
        """Select all accessible orphaned items."""
        if not self.orphan_metadata:
            self.add_status_message("No items to select")
            return
            
        # Select all accessible items
        accessible_items = [
            rel_path for rel_path, metadata in self.orphan_metadata.items()
            if metadata['accessible']
        ]
        
        self.selected_items = set(accessible_items)
        
        # Update display
        self.update_tree_display()
        self.update_statistics()
        
        self.add_status_message(f"Selected all accessible items: {len(accessible_items)} files")
        
    def clear_all_items(self):
        """Clear all selections."""
        selected_count = len(self.selected_items)
        self.selected_items.clear()
        
        # Update display
        self.update_tree_display()
        self.update_statistics()
        
        self.add_status_message(f"Cleared all selections: {selected_count} items deselected")
        
    def refresh_orphans_tree(self):
        """Refresh orphan tree to detect external changes."""
        if not self.orphaned_files:
            self.add_status_message("No orphan data to refresh")
            return
            
        self.add_status_message("Refreshing orphan file status...")
        
        # Re-validate all orphan metadata
        accessible_count, changed_count = self.refresh_orphan_metadata_status(self.orphan_metadata)
        
        # Log details about currently inaccessible files after refresh # v001.0013 added [detailed logging for inaccessible files after refresh]
        self.add_status_message("Post-refresh inaccessible file analysis:") # v001.0013 added [detailed logging for inaccessible files after refresh]
        self.log_inaccessible_files() # v001.0013 added [detailed logging for inaccessible files after refresh]
        
        # Update tree display with new status
        self.build_orphan_tree()
        self.update_statistics()
        
        # Report results
        total_count = len(self.orphan_metadata)
        inaccessible_count = total_count - accessible_count
        
        self.add_status_message(
            f"Refresh complete: {accessible_count} accessible, {inaccessible_count} inaccessible, "
            f"{changed_count} status changes detected"
        )
        
    def delete_selected_files(self):
        """Start the deletion process for selected files."""
        if not self.selected_items:
            self.add_status_message("No files selected for deletion")
            messagebox.showinfo("No Selection", "Please select files to delete first.")
            return
            
        # Get selected accessible files only
        selected_accessible = []
        for rel_path in self.selected_items:
            metadata = self.orphan_metadata.get(rel_path)
            if metadata and metadata['accessible']:
                selected_accessible.append(rel_path)
                
        if not selected_accessible:
            self.add_status_message("No accessible files selected for deletion")
            messagebox.showinfo("No Accessible Files", "All selected files are inaccessible and cannot be deleted.")
            return
            
        # Calculate statistics for confirmation
        total_size = sum(
            self.orphan_metadata[path].get('size', 0) or 0
            for path in selected_accessible
            if not self.orphan_metadata[path]['is_folder']
        )
        
        deletion_method = self.deletion_method.get()
        method_text = "Move to Recycle Bin" if deletion_method == "recycle_bin" else "Permanently Delete"
        
        # Use local dry run mode instead of main app dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        # Show confirmation dialog
        dry_run_text = " (DRY RUN SIMULATION)" if is_local_dry_run else "" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        confirmation_message = (
            f"Are you SURE you want to {method_text.lower()} the selected orphaned files{dry_run_text}?\n\n"
            f"Action: {method_text} {len(selected_accessible)} files ({format_size(total_size)}) "
            f"from {self.side.upper()} folder\n\n"
        )
        
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            confirmation_message += "*** DRY RUN MODE - No files will be actually deleted ***\n\n"
        elif deletion_method == "permanent":
            confirmation_message += "⚠ WARNING: Permanent deletion cannot be undone! ⚠\n\n"
        else:
            confirmation_message += "Files will be moved to Recycle Bin where they can be recovered.\n\n"
            
        # Show first 10 files
        preview_files = selected_accessible[:10]
        confirmation_message += "Files to delete:\n" + "\n".join(preview_files)
        
        if len(selected_accessible) > 10:
            confirmation_message += f"\n... and {len(selected_accessible) - 10} more files"
            
        # Create confirmation dialog with appropriate button styling
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            title = "Confirm Deletion Simulation"
            button_text = "Yes, SIMULATE DELETION"
        else:
            title = "Confirm Deletion"
            button_text = "Yes, DELETE FILES"
            
        result = messagebox.askyesno(title, confirmation_message)
        
        if not result:
            self.add_status_message("Deletion cancelled by user")
            return
            
        # Start deletion process
        self.add_status_message(f"Starting deletion process: {len(selected_accessible)} files")
        
        # Close dialog and start deletion in background
        deletion_method_final = deletion_method
        selected_files_final = selected_accessible.copy()
        
        # Start deletion process in background thread
        threading.Thread(
            target=self.perform_deletion,
            args=(selected_files_final, deletion_method_final),
            daemon=True
        ).start()
        
        # Set result and close dialog
        self.result = "deleted"
        self.close_dialog()
        
    def perform_deletion(self, selected_paths, deletion_method):
        """Perform the actual deletion operation with progress tracking."""
        operation_start_time = time.time()
        operation_id = uuid.uuid4().hex[:8]
        
        # Create dedicated logger for this operation
        deletion_logger = self.create_deletion_logger(operation_id)
        
        # Use local dry run mode instead of main app dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        # Log operation start
        dry_run_text = " (DRY RUN)" if is_local_dry_run else "" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        method_text = "Recycle Bin" if deletion_method == "recycle_bin" else "Permanent"
        
        log_and_flush(logging.INFO, "=" * 80)
        log_and_flush(logging.INFO, f"DELETE ORPHANS OPERATION STARTED{dry_run_text}")
        log_and_flush(logging.INFO, f"Operation ID: {operation_id}")
        log_and_flush(logging.INFO, f"Side: {self.side.upper()}")
        log_and_flush(logging.INFO, f"Source Folder: {self.source_folder}")
        log_and_flush(logging.INFO, f"Deletion Method: {method_text}")
        log_and_flush(logging.INFO, f"Files to delete: {len(selected_paths)}")
        log_and_flush(logging.INFO, f"Local Dry Run Mode: {is_local_dry_run}") # v001.0013 changed [log local dry run mode instead of main app dry run mode]
        log_and_flush(logging.INFO, "=" * 80)
        
        # Create progress dialog
        progress_title = f"{'Simulating' if is_local_dry_run else 'Deleting'} Orphaned Files" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        progress = ProgressDialog(
            self.parent,
            progress_title,
            f"{'Simulating' if is_local_dry_run else 'Processing'} orphaned files...", # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            max_value=len(selected_paths)
        )
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        total_bytes_processed = 0
        
        try:
            for i, rel_path in enumerate(selected_paths):
                try:
                    # Update progress
                    file_name = rel_path.split('/')[-1]
                    progress_text = f"{'Simulating' if is_local_dry_run else 'Processing'} {i+1} of {len(selected_paths)}: {file_name}" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
                    progress.update_progress(i+1, progress_text)
                    
                    # Get full path
                    full_path = str(Path(self.source_folder) / rel_path)
                    
                    # Skip if file doesn't exist
                    if not os.path.exists(full_path):
                        skipped_count += 1
                        log_and_flush(logging.WARNING, f"File not found, skipping: {full_path}")
                        continue
                        
                    # Get file size for statistics
                    try:
                        if os.path.isfile(full_path):
                            file_size = os.path.getsize(full_path)
                            total_bytes_processed += file_size
                    except:
                        file_size = 0
                        
                    # Perform deletion
                    if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
                        # Simulate deletion
                        log_and_flush(logging.INFO, f"DRY RUN: Would {method_text.lower()} delete: {full_path}")
                        success_count += 1
                    else:
                        # Actual deletion
                        if deletion_method == "recycle_bin":
                            success, error_msg = self.delete_file_to_recycle_bin(full_path, show_progress=False)
                        else:
                            success, error_msg = self.delete_file_permanently(full_path)
                            
                        if success:
                            success_count += 1
                            log_and_flush(logging.INFO, f"Successfully {method_text.lower()} deleted: {full_path}")
                        else:
                            error_count += 1
                            log_and_flush(logging.ERROR, f"Failed to delete {full_path}: {error_msg}")
                            
                except Exception as e:
                    error_count += 1
                    log_and_flush(logging.ERROR, f"Exception deleting {rel_path}: {str(e)}")
                    continue
                    
        except Exception as e:
            log_and_flush(logging.ERROR, f"Critical error during deletion operation: {str(e)}")
            
        finally:
            progress.close()
            
            # Log operation completion
            elapsed_time = time.time() - operation_start_time
            log_and_flush(logging.INFO, "=" * 80)
            log_and_flush(logging.INFO, f"DELETE ORPHANS OPERATION COMPLETED{dry_run_text}")
            log_and_flush(logging.INFO, f"Operation ID: {operation_id}")
            log_and_flush(logging.INFO, f"Files processed successfully: {success_count}")
            log_and_flush(logging.INFO, f"Files failed: {error_count}")
            log_and_flush(logging.INFO, f"Files skipped: {skipped_count}")
            log_and_flush(logging.INFO, f"Total bytes processed: {total_bytes_processed:,}")
            log_and_flush(logging.INFO, f"Duration: {elapsed_time:.2f} seconds")
            if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
                log_and_flush(logging.INFO, "NOTE: This was a DRY RUN simulation - no actual files were modified")
            log_and_flush(logging.INFO, "=" * 80)
            
            # Show completion dialog
            completion_message = self.format_completion_message(
                success_count, error_count, skipped_count, total_bytes_processed, 
                elapsed_time, method_text, operation_id
            )
            
            self.parent.after(0, lambda: messagebox.showinfo(
                f"{'Simulation' if is_local_dry_run else 'Deletion'} Complete", # v001.0013 changed [use local dry run mode instead of main app dry run mode]
                completion_message
            ))
            
            # Close logger
            for handler in deletion_logger.handlers[:]:
                handler.close()
                deletion_logger.removeHandler(handler)
                
    def create_deletion_logger(self, operation_id):
        """Create dedicated logger for deletion operation."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"foldercomparesync_delete_{self.side}_{timestamp}_{operation_id}.log"
        log_filepath = os.path.join(os.path.dirname(__file__), log_filename)
        
        operation_logger = logging.getLogger(f"delete_orphans_{operation_id}")
        operation_logger.setLevel(logging.DEBUG)
        
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        operation_logger.addHandler(file_handler)
        operation_logger.propagate = False
        
        return operation_logger
        
    def format_completion_message(self, success_count, error_count, skipped_count, 
                                total_bytes, elapsed_time, method_text, operation_id):
        """Format completion message for deletion operation."""
        # Use local dry run mode instead of main app dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        dry_run_text = " simulation" if is_local_dry_run else "" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        action_text = "simulated" if is_local_dry_run else method_text.lower() + " deleted" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        message = f"Deletion{dry_run_text} completed!\n\n"
        message += f"Successfully {action_text}: {success_count} files\n"
        
        if error_count > 0:
            message += f"Failed: {error_count} files\n"
        if skipped_count > 0:
            message += f"Skipped: {skipped_count} files (not found)\n"
            
        message += f"Total size processed: {format_size(total_bytes)}\n"
        message += f"Time elapsed: {elapsed_time:.1f} seconds\n"
        message += f"Operation ID: {operation_id}\n\n"
        
        # Log file reference
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"foldercomparesync_delete_{self.side}_{timestamp}_{operation_id}.log"
        message += f"Detailed log saved to:\n{log_filename}\n\n"
        
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            message += "*** DRY RUN SIMULATION ***\n"
            message += "No actual files were modified.\n\n"
        else:
            message += "The main window will now refresh to show the updated folder state.\n"
            
        return message

    def update_delete_button_appearance(self): # v001.0013 added [update delete button appearance based on local dry run mode]
        """Update delete button text and styling based on local dry run mode.""" # v001.0013 added [update delete button appearance based on local dry run mode]
        if not hasattr(self, 'delete_button'): # v001.0013 added [update delete button appearance based on local dry run mode]
            return  # Button not created yet # v001.0013 added [update delete button appearance based on local dry run mode]
        
        is_dry_run = self.local_dry_run_mode.get() # v001.0013 added [update delete button appearance based on local dry run mode]
        
        # Update button text based on local dry run mode # v001.0013 added [update delete button appearance based on local dry run mode]
        if is_dry_run: # v001.0013 added [update delete button appearance based on local dry run mode]
            button_text = "SIMULATE DELETION" # v001.0013 added [update delete button appearance based on local dry run mode]
            button_style = "DeleteOrphansBlueBold.TButton"  # Blue for simulation # v001.0014 changed [use local scaled button style instead of main app style]
        else: # v001.0013 added [update delete button appearance based on local dry run mode]
            button_text = "DELETE SELECTED ORPHANED FILES" # v001.0013 added [update delete button appearance based on local dry run mode]
            button_style = "DeleteOrphansRedBold.TButton"   # Red for actual deletion # v001.0014 changed [use local scaled button style instead of main app style]
        
        # Apply changes to button # v001.0013 added [update delete button appearance based on local dry run mode]
        self.delete_button.configure(text=button_text, style=button_style) # v001.0013 changed [use stored button reference]

    def on_local_dry_run_changed(self): # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        """Handle local dry run mode checkbox changes.""" # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        is_dry_run = self.local_dry_run_mode.get() # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        
        if is_dry_run: # v001.0013 added [local dry run mode change handler for delete orphans dialog]
            self.add_status_message("Local DRY RUN mode enabled - deletion will be simulated only") # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        else: # v001.0013 added [local dry run mode change handler for delete orphans dialog]
            self.add_status_message("Local DRY RUN mode disabled - actual deletion enabled") # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        
        # Update button text and styling to reflect current mode # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        self.update_delete_button_appearance() # v001.0013 added [local dry run mode change handler for delete orphans dialog]

    def log_inaccessible_files(self): # v001.0013 added [detailed logging for inaccessible files]
        """Log detailed information about inaccessible files with full paths and reasons.""" # v001.0013 added [detailed logging for inaccessible files]
        if not self.orphan_metadata: # v001.0013 added [detailed logging for inaccessible files]
            return # v001.0013 added [detailed logging for inaccessible files]
        
        # Find all inaccessible files # v001.0013 added [detailed logging for inaccessible files]
        inaccessible_files = [] # v001.0013 added [detailed logging for inaccessible files]
        
        for rel_path, metadata in self.orphan_metadata.items(): # v001.0013 added [detailed logging for inaccessible files]
            if not metadata['accessible']: # v001.0013 added [detailed logging for inaccessible files]
                inaccessible_files.append({ # v001.0013 added [detailed logging for inaccessible files]
                    'rel_path': rel_path, # v001.0013 added [detailed logging for inaccessible files]
                    'full_path': metadata['full_path'], # v001.0013 added [detailed logging for inaccessible files]
                    'reason': metadata['status'], # v001.0013 added [detailed logging for inaccessible files]
                    'is_folder': metadata['is_folder'] # v001.0013 added [detailed logging for inaccessible files]
                }) # v001.0013 added [detailed logging for inaccessible files]
        
        if not inaccessible_files: # v001.0013 added [detailed logging for inaccessible files]
            self.add_status_message("All orphaned files are accessible for deletion") # v001.0013 added [detailed logging for inaccessible files]
            log_and_flush(logging.INFO, f"All {len(self.orphan_metadata)} orphaned files on {self.side} side are accessible") # v001.0013 added [detailed logging for inaccessible files]
            return # v001.0013 added [detailed logging for inaccessible files]
        
        # Log summary # v001.0013 added [detailed logging for inaccessible files]
        total_count = len(self.orphan_metadata) # v001.0013 added [detailed logging for inaccessible files]
        inaccessible_count = len(inaccessible_files) # v001.0013 added [detailed logging for inaccessible files]
        accessible_count = total_count - inaccessible_count # v001.0013 added [detailed logging for inaccessible files]
        
        self.add_status_message(f"INACCESSIBLE FILES: {inaccessible_count} of {total_count} files cannot be deleted") # v001.0013 added [detailed logging for inaccessible files]
        log_and_flush(logging.WARNING, f"Found {inaccessible_count} inaccessible orphaned files on {self.side} side out of {total_count} total") # v001.0013 added [detailed logging for inaccessible files]
        
        # Group by reason for better reporting # v001.0013 added [detailed logging for inaccessible files]
        reasons = {} # v001.0013 added [detailed logging for inaccessible files]
        for file_info in inaccessible_files: # v001.0013 added [detailed logging for inaccessible files]
            reason = file_info['reason'] # v001.0013 added [detailed logging for inaccessible files]
            if reason not in reasons: # v001.0013 added [detailed logging for inaccessible files]
                reasons[reason] = [] # v001.0013 added [detailed logging for inaccessible files]
            reasons[reason].append(file_info) # v001.0013 added [detailed logging for inaccessible files]
        
        # Log details grouped by reason # v001.0013 added [detailed logging for inaccessible files]
        for reason, files_with_reason in reasons.items(): # v001.0013 added [detailed logging for inaccessible files]
            count = len(files_with_reason) # v001.0013 added [detailed logging for inaccessible files]
            self.add_status_message(f"  {reason}: {count} files") # v001.0013 added [detailed logging for inaccessible files]
            log_and_flush(logging.WARNING, f"Inaccessible files due to '{reason}': {count} files") # v001.0013 added [detailed logging for inaccessible files]
            
            # Log first few file paths for each reason (avoid spam) # v001.0013 added [detailed logging for inaccessible files]
            max_examples = 5  # Show max 5 examples per reason # v001.0013 added [detailed logging for inaccessible files]
            for i, file_info in enumerate(files_with_reason[:max_examples]): # v001.0013 added [detailed logging for inaccessible files]
                file_type = "folder" if file_info['is_folder'] else "file" # v001.0013 added [detailed logging for inaccessible files]
                self.add_status_message(f"    {file_type}: {file_info['full_path']}") # v001.0013 added [detailed logging for inaccessible files]
                log_and_flush(logging.WARNING, f"  Inaccessible {file_type}: {file_info['full_path']} (reason: {reason})") # v001.0013 added [detailed logging for inaccessible files]
            
            # If there are more files, show count # v001.0013 added [detailed logging for inaccessible files]
            if len(files_with_reason) > max_examples: # v001.0013 added [detailed logging for inaccessible files]
                remaining = len(files_with_reason) - max_examples # v001.0013 added [detailed logging for inaccessible files]
                self.add_status_message(f"    ... and {remaining} more files with same reason") # v001.0013 added [detailed logging for inaccessible files]
                log_and_flush(logging.WARNING, f"  ... and {remaining} more inaccessible files with reason '{reason}'") # v001.0013 added [detailed logging for inaccessible files]
        
        # Add helpful message about what to do # v001.0013 added [detailed logging for inaccessible files]
        self.add_status_message("TIP: Inaccessible files will be skipped during deletion") # v001.0013 added [detailed logging for inaccessible files]
        if any(reason in ["Read-Only", "No Read Access", "Directory Read-Only"] for reason in reasons.keys()): # v001.0013 added [detailed logging for inaccessible files]
            self.add_status_message("TIP: Try running as Administrator for permission-related issues") # v001.0013 added [detailed logging for inaccessible files]

def main():
    """
    Main entry point with system detection and configuration logging.
    
    Purpose:
    --------
    Application startup function that initializes logging, detects system
    configuration, and starts the main application with proper error handling.
    """
    log_and_flush(logging.INFO, "=== FolderCompareSync Startup ===")
    if __debug__:
        log_and_flush(logging.DEBUG, "Working directory : " + os.getcwd())
        log_and_flush(logging.DEBUG, "Python version    : " + sys.version)
        log_and_flush(logging.DEBUG, "Computer name     : " + platform.node())
        log_and_flush(logging.DEBUG, "Platform          : " + sys.platform)
        log_and_flush(logging.DEBUG, "Architecture      : " + platform.architecture()[0])
        log_and_flush(logging.DEBUG, "Machine           : " + platform.machine())
        log_and_flush(logging.DEBUG, "Processor         : " + platform.processor())

    # Detailed Windows information
    if sys.platform == "win32":
        try:
            win_ver = platform.win32_ver()
            log_and_flush(logging.DEBUG, f"Windows version   : {win_ver[0]}")
            log_and_flush(logging.DEBUG, f"Windows build     : {win_ver[1]}")
            if win_ver[2]:  # Service pack
                log_and_flush(logging.DEBUG, f"Service pack      : {win_ver[2]}")
            log_and_flush(logging.DEBUG, f"Windows type      : {win_ver[3]}")
            # Try to get Windows edition
            try:
                edition = platform.win32_edition()
                if edition:
                    log_and_flush(logging.DEBUG, f"Windows edition   : {edition}")
            except:
                pass
            # Extract build number from version string like "10.0.26100"
            version_parts = win_ver[1].split('.')
            if len(version_parts) >= 3:
                build_num = version_parts[2]  # Get "26100" from "10.0.26100"
            else:
                build_num = win_ver[1]  # Fallback to full string
                
            win_versions = {
                # Windows 11 versions
                "22000": "21H2 (Original release)",
                "22621": "22H2", 
                "22631": "23H2",
                "26100": "24H2",
                # Future Windows versions (anticipated)
                "27000": "25H1 (anticipated)",
                "27100": "25H2 (anticipated)"
            }
            if build_num in win_versions:
                log_and_flush(logging.DEBUG, f"Windows 11 version: {win_versions[build_num]} (build {build_num})")
            elif build_num.startswith("27") or build_num.startswith("28"):
                log_and_flush(logging.DEBUG, f"Windows version   : Future windows build {build_num}")
            elif build_num.startswith("26") or build_num.startswith("22"):
                log_and_flush(logging.DEBUG, f"Windows 11 version: Unknown windows build {build_num}")
            elif build_num.startswith("19"):
                log_and_flush(logging.DEBUG, f"Windows 10 build  : {build_num}")
            else:
                log_and_flush(logging.DEBUG, f"Windows version   : Unknown windows build {build_num}")
        except Exception as e:
            log_and_flush(logging.DEBUG, f"Error getting Windows details: {e}")

    # Log  configuration including new limits and features
    log_and_flush(logging.DEBUG, "FolderCompareSync Configuration:")
    log_and_flush(logging.DEBUG, f"  Max files/folders: {MAX_FILES_FOLDERS:,}")
    log_and_flush(logging.DEBUG, f"  Status log history: {STATUS_LOG_MAX_HISTORY:,} lines")
    log_and_flush(logging.DEBUG, f"  Copy strategy threshold: {COPY_STRATEGY_THRESHOLD / (1024*1024):.1f} MB")
    log_and_flush(logging.DEBUG, f"  SHA512 status threshold: {SHA512_STATUS_MESSAGE_THRESHOLD / (1024*1024):.1f} MB")
    log_and_flush(logging.DEBUG, f"  Simple verification enabled: {COPY_VERIFICATION_ENABLED}")
    log_and_flush(logging.DEBUG, f"  Retry count: {COPY_RETRY_COUNT}")
    log_and_flush(logging.DEBUG, f"  Network timeout: {COPY_NETWORK_TIMEOUT}s")
    log_and_flush(logging.DEBUG, f"  Dry run support: Enabled")
    log_and_flush(logging.DEBUG, f"  Status log export: Enabled")
    log_and_flush(logging.DEBUG, f"  Error details dialog: Enabled")
    log_and_flush(logging.DEBUG, f"  Path handling: Standardized on pathlib")
    
    try:
        FolderCompareSync_class_app = FolderCompareSync_class()
        # uncomment the next line to MANUALLY Enable debug mode logging for testing the application GUI event loop
        #FolderCompareSync_class_app.set_debug_loglevel(True)

        FolderCompareSync_class_app.run()    # start the application GUI event loop
    except Exception as e:
        log_and_flush(logging.ERROR, f"Fatal error: {type(e).__name__}: {str(e)}")
        if __debug__:
            import traceback
            log_and_flush(logging.DEBUG, "Fatal error traceback:")
            log_and_flush(logging.DEBUG, traceback.format_exc())
        raise
    finally:
        log_and_flush(logging.INFO, "=== FolderCompareSync Shutdown ===")


if __name__ == "__main__":
    main()
