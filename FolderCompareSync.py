#!/usr/bin/env python3
"""
FolderCompareSync - A Professional Folder Comparison & Synchronization Tool

Version  v001.0010 - really, this time, show full precision timestamp displays

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
        logger.debug("Now getting detailed debug info...")
        ...
        self.set_debug_loglevel(False)  # Turn off debug logging
"""

import platform
import os
import sys
import importlib
import hashlib
import time
import fnmatch
import shutil
import uuid
import ctypes
import ctypes.wintypes
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import threading
import logging

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

# Status log configuration
STATUS_LOG_VISIBLE_LINES = 5       # Visible lines in status log window
STATUS_LOG_FONT = ("Courier", 9)   # Monospace font for better alignment
STATUS_LOG_BG_COLOR = "#f8f8f8"    # Light background color
STATUS_LOG_FG_COLOR = "#333333"    # Dark text color

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

# Display colors and styling
MISSING_ITEM_COLOR = "gray"       # Color for missing items in tree
INSTRUCTION_TEXT_COLOR = "royalblue"  # Color for instructional text
INSTRUCTION_TEXT_SIZE = 8         # Font size for instructional text
FILTER_HIGHLIGHT_COLOR = "#ffffcc"  # Background color for filtered items

# Filtering and sorting configuration
MAX_FILTER_RESULTS = 200000       # Maximum items to show when filtering (performance)
                                                                         

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
        logger.critical(missing_msg)
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
        logger.debug(f"FileTimestampManager initialized with timezone: {self.get_timezone_string()}")
        logger.debug(f"FileTimestampManager dry run mode: {self._dry_run}")

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
        logger.debug("Attempting timezone detection using Method 0: dateutil.tz.tzwinlocal...")
        try:
            tz = tzwinlocal()
            if tz:
                # Get a human-readable description
                tz_name = tz.tzname(datetime.now())
                logger.info(f"Timezone detected via Method 0: dateutil.tz.tzwinlocal: {tz_name}")
                return tz
        except Exception as e:
            logger.debug(f"tzwinlocal method failed: {e}")

        # Method 1: Try zoneinfo (Python 3.9+) with Windows timezone mapping
        logger.debug("Attempting timezone detection using Method 1: zoneinfo method...")
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
                logger.debug(f"Windows timezone name detected: {win_tz_name}")
                
                if win_tz_name in windows_to_iana:
                    iana_name = windows_to_iana[win_tz_name]
                    tz = zoneinfo.ZoneInfo(iana_name)
                    logger.info(f"Timezone detected via Method 1a: zoneinfo mapping: {iana_name} (from Windows: {win_tz_name})")
                    return tz
                    
                # Try the name directly (might work on some systems)
                try:
                    tz = zoneinfo.ZoneInfo(win_tz_name)
                    logger.info(f"Timezone detected via Method 1b: zoneinfo direct: {win_tz_name}")
                    return tz
                except:
                    logger.debug(f"Could not use Windows timezone name directly: {win_tz_name}")
        except zoneinfo.ZoneInfoNotFoundError as e:
            logger.warning(f"IANA lookup failed (no tzdata?): {e}")
        except ImportError as e:
            logger.debug("zoneinfo module not available, {e},skipping Method 1")
        except (AttributeError, Exception) as e:
            logger.debug(f"Zoneinfo method failed: {e}")
        
        # Method 2: Use time module offset to create timezone
        logger.debug("Attempting timezone detection using Method 2: time module offset method...")
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
            logger.info(f"Timezone detected via Method 2: time module offset: {offset_str}")
            return tz
        except Exception as e:
            logger.debug(f"Time module offset method failed: {e}")
        
        # Method 3: Final fallback to UTC
        logger.warning("Could not determine local timezone, falling back to Method 3: UTC")
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
            
            logger.debug(f"Retrieved timestamps for {file_path}:")
            logger.debug(f"  Creation: {creation_time}")
            logger.debug(f"  Modified: {modification_time}")
            
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
            logger.info(f"[DRY RUN] Would set timestamps for {file_path}")
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
                logger.debug(f"Creation FILETIME: {creation_filetime}")
                logger.debug(f"        = {dt_display.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            if modification_time is not None:
                modification_filetime = self._datetime_to_filetime(modification_time)
                dt_display = self._filetime_to_datetime(modification_filetime)
                logger.debug(f"Modification FILETIME: {modification_filetime}")
                logger.debug(f"        = {dt_display.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Try the proper FILETIME structure method first
            success = self._set_file_times_windows_proper(
                str(file_path), creation_filetime, modification_filetime
            )
            
            # If that fails, try the fallback method
            if not success:
                logger.debug("Primary method failed, trying fallback...")
                success = self._set_file_times_windows_fallback(
                    str(file_path), creation_filetime, modification_filetime
                )
            if success:
                logger.debug(f"Successfully set timestamps for {file_path}")
            else:
                logger.error(f"Failed to set timestamps for {file_path}")
            return success
        except Exception as e:
            logger.error(f"Error setting timestamps for {file_path}: {e}")
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
            logger.debug(f"Converting naive datetime to local timezone: {dt}")
        
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
                logger.debug(f"CreateFileW failed with error code: {error_code}")
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
                logger.debug(f"SetFileTime failed with error code: {error_code}")
            
            return bool(result)
            
        except Exception as e:
            logger.debug(f"Exception in proper method: {e}")
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
            logger.debug(f"Exception in fallback method: {e}")
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
            logger.info(f"[DRY RUN] Would copy timestamps from {source_file} to {target_file}")
            return True
            
        try:
            # Get timestamps from source
            creation_time, modification_time = self.get_file_timestamps(source_file)
            
            # Set timestamps on target
            success = self.set_file_timestamps(target_file, creation_time, modification_time)
            
            if success:
                logger.debug(f"Successfully copied timestamps from {source_file} to {target_file}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error copying timestamps: {e}")
            return False
    
    def format_timestamp(self, dt: datetime, include_timezone: bool = True) -> str:
        """
        Format a datetime object for display.
        
        Args:
            dt: Datetime object
            include_timezone: Whether to include timezone info in output
            
        Returns:
            Formatted datetime string
        """
        if include_timezone:
            return dt.strftime("%Y-%m-%d %H:%M:%S.%f %Z") # v001.0010 changed - full microsecond precision display
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S.%f") # v001.0010 changed - full microsecond precision display
    
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
                    logger.debug(f"Creation time mismatch: {diff} seconds")
                    return False
            
            if expected_modification is not None:
                diff = abs((actual_modification - expected_modification).total_seconds())
                if diff > tolerance_seconds:
                    logger.debug(f"Modification time mismatch: {diff} seconds")
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Error verifying timestamps: {e}")
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
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Error icon and summary
        summary_frame = ttk.Frame(main_frame)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(summary_frame, text="❌", font=("TkDefaultFont", 16)).pack(side=tk.LEFT, padx=(0, 10))
        
        # Truncate summary if too long
        display_summary = summary[:200] + "..." if len(summary) > 200 else summary
        ttk.Label(summary_frame, text=display_summary, wraplength=400).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
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
        logger.warning(f"Could not determine drive type for {path}: {e}")
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
    logger.info("Copy operation starting...")
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
        logger.debug(f"Creating progress dialog: {title}")
        
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
        logger.debug("Closing progress dialog")
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
        logger.info(f"FileCopyManager initialized with timezone: {self.timestamp_manager.get_timezone_string()}")
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
            self.operation_logger.info(message)
        if self.status_callback:
            self.status_callback(message)
        logger.debug(f"Copy operation status: {message}")
    
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
        
        self.operation_logger.info("=" * 80)
        self.operation_logger.info(f"COPY OPERATION STARTED: {operation_name}{dry_run_text}")
        self.operation_logger.info(f"Operation ID: {self.operation_id}")
        self.operation_logger.info(f"Mode: {'DRY RUN SIMULATION' if dry_run else 'NORMAL OPERATION'}")
        self.operation_logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.operation_logger.info("=" * 80)
        
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
            
            self.operation_logger.info("=" * 80)
            self.operation_logger.info(f"COPY OPERATION COMPLETED{dry_run_text}")
            self.operation_logger.info(f"Operation ID: {self.operation_id}")
            self.operation_logger.info(f"Files processed successfully: {success_count}")
            self.operation_logger.info(f"Files failed: {error_count}")
            self.operation_logger.info(f"Total bytes processed: {total_bytes:,}")
            self.operation_logger.info(f"Total operations: {self.operation_sequence}")
            if self.dry_run_mode:
                self.operation_logger.info("NOTE: This was a DRY RUN simulation - no actual files were modified")
            self.operation_logger.info(f"Timestamp: {datetime.now().isoformat()}")
            self.operation_logger.info("=" * 80)
            
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
        logger.info("Initializing FolderCompareSync application")
        global log_level
        if __debug__:
            if log_level == logging.DEBUG:
                logger.debug("Debug mode enabled - Debug log_level active")
            else:
                logger.debug("Debug mode enabled - non-Debug log_level active")
        
        self.root = tk.Tk()
        self.root.title("FolderCompareSync - Folder Comparison and Syncing Tool")

        # NEW style configs for the "Compare" "Copy" "Quit" buttons  button
        # 1) Get the existing default font and make a bold copy
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.bold_font = self.default_font.copy()
        self.bold_font.configure(weight="bold")
        self.style = ttk.Style(self.root)
        # 2) Create styles for the "Compare" "Copy" "Quit" buttons using that bold_font
        self.style.configure("LimeGreenBold.TButton", foreground="limegreen",font=self.bold_font,)
        self.style.configure("GreenBold.TButton", foreground="green",font=self.bold_font,)
        self.style.configure("RedBold.TButton", foreground="red",font=self.bold_font,)
        self.style.configure("PurpleBold.TButton", foreground="purple",font=self.bold_font,)
        self.style.configure("MediumPurpleBold.TButton", foreground="mediumpurple",font=self.bold_font,)
        self.style.configure("IndigoBold.TButton", foreground="indigo",font=self.bold_font,)
        self.style.configure("BlueBold.TButton", foreground="blue",font=self.bold_font,)
        self.style.configure("GoldBold.TButton", foreground="gold",font=self.bold_font,)
        self.style.configure("YellowBold.TButton", foreground="yellow",font=self.bold_font,)

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
            logger.debug("Application state initialized with dual copy system")
        
        self.setup_ui()
        
        # Add startup warnings about performance and limits
        self.add_status_message("Application initialized - dual copy system ready")
        self.add_status_message(f"WARNING: Large folder operations may be slow. Maximum {MAX_FILES_FOLDERS:,} files/folders supported.")
        self.add_status_message("Tip: Use filtering and dry run mode for testing with large datasets.")
        
        # Display detected timezone information
        timezone_str = self.copy_manager.timestamp_manager.get_timezone_string()
        self.add_status_message(f"Timezone detected: {timezone_str} - will be used for timestamp operations")
        logger.info("Application initialization complete ")

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
            
        logger.info(f"STATUS: {message}")

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
            logger.info("[DEBUG] Debug logging enabled - Debug output activated")
        else:
            log_level = logging.INFO
            logger.info("[INFO] Debug logging disabled - Info mode activated")
        logger.setLevel(log_level)
        # Update status to show updated current mode
        if hasattr(self, 'status_var'):
            current_status = self.status_var.get()
            mode = "DEBUG" if enabled else "NORMAL"
            self.status_var.set(f"{current_status} ({mode})")

    def setup_ui(self):
        """
        Initialize the user interface with features including dry run and export capabilities.
        
        Purpose:
        --------
        Creates and configures all GUI components including the new dry run checkbox,
        export functionality, and limit warnings for the application interface.
        """
        logger.debug("Setting up user interface with features")
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Performance warning frame at top
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 5))
        
        warning_label = ttk.Label(
            warning_frame, 
            text=(
                f"⚠ Performance Notice: Large folder operations may be slow. "
                f"Maximum {MAX_FILES_FOLDERS:,} files/folders supported. "
                f"SHA512 operations will take circa 2 seconds elapsed per GB of file read."
            ),
            foreground="royalblue",
            font=("TkDefaultFont", 9, "bold")
        )
                                                                                                                                        
                                    
        warning_label.pack(side=tk.LEFT)
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding=10)
        folder_frame.pack(fill=tk.X, pady=(0, 5))
        
               
                                
                                                                                                     
                                                                                      
                                                                    
                                                                                                       
                                 
                                                                                                                   
                                                                                        
                                                                                  
                                                                                                                     
                                                  

             
        # Left folder selection
        ttk.Label(folder_frame, text="Left Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_left_folder).grid(row=0, column=1, padx=(0, 5))
        left_entry = ttk.Entry(folder_frame, textvariable=self.left_folder, width=60)
        left_entry.grid(row=0, column=2, sticky=tk.EW)
        
        # Right folder selection
        ttk.Label(folder_frame, text="Right Folder:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Button(folder_frame, text="Browse", command=self.browse_right_folder).grid(row=1, column=1, padx=(0, 5), pady=(5, 0))
        right_entry = ttk.Entry(folder_frame, textvariable=self.right_folder, width=60)
        right_entry.grid(row=1, column=2, sticky=tk.EW, pady=(5, 0))

        # Let column 2 (the entry) grow
        folder_frame.columnconfigure(2, weight=1)

       
        # Comparison options frame with instructional text
        options_frame = ttk.LabelFrame(main_frame, text="Comparison Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Comparison criteria checkboxes with instructional text
        criteria_frame = ttk.Frame(options_frame)
        criteria_frame.pack(fill=tk.X)
        
        # Add instructional text for better user guidance using configurable styling
        instruction_frame = ttk.Frame(criteria_frame)
        instruction_frame.pack(fill=tk.X)
        
        ttk.Label(instruction_frame, text="Compare Options:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Existence", variable=self.compare_existence).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Size", variable=self.compare_size).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Date Created", variable=self.compare_date_created).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Date Modified", variable=self.compare_date_modified).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="SHA512", variable=self.compare_sha512).pack(side=tk.LEFT, padx=(0, 10))
        
        # Add instructional text for workflow guidance using configurable colors and font size
        ttk.Label(instruction_frame, text="<- select options then click Compare", 
                 foreground=INSTRUCTION_TEXT_COLOR, 
                 font=("TkDefaultFont", INSTRUCTION_TEXT_SIZE, "italic")).pack(side=tk.LEFT, padx=(20, 0))
        
        # Control frame - reorganized for better layout
        control_frame = ttk.Frame(options_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Top row of controls with dry run support
        top_controls = ttk.Frame(control_frame)
        top_controls.pack(fill=tk.X, pady=(0, 5))
        
        # Dry run checkbox next to overwrite mode
        dry_run_cb = ttk.Checkbutton(top_controls, text="DRY RUN Only", variable=self.dry_run_mode, command=self.on_dry_run_changed)
        dry_run_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Checkbutton(top_controls, text="Overwrite Mode", variable=self.overwrite_mode).pack(side=tk.LEFT, padx=(0, 20))

             
                                                                                                                 
             
        ttk.Button(top_controls, text="Compare", command=self.start_comparison, style="LimeGreenBold.TButton").pack(side=tk.LEFT, padx=(0, 20))

        # selection controls with auto-clear and complete reset functionality
        # Left pane selection controls
        ttk.Button(top_controls, text="Select All Differences - Left", 
                  command=self.select_all_differences_left).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(top_controls, text="Clear All - Left", 
                  command=self.clear_all_left).pack(side=tk.LEFT, padx=(0, 15))
        
        # Right pane selection controls  
        ttk.Button(top_controls, text="Select All Differences - Right", 
                  command=self.select_all_differences_right).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(top_controls, text="Clear All - Right", 
                  command=self.clear_all_right).pack(side=tk.LEFT)

        # Filter and tree control frame
        filter_tree_frame = ttk.Frame(control_frame)
        filter_tree_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Wildcard filter controls
        ttk.Label(filter_tree_frame, text="Filter Files by Wildcard:").pack(side=tk.LEFT, padx=(0, 5))
        filter_entry = ttk.Entry(filter_tree_frame, textvariable=self.filter_wildcard, width=20)
        filter_entry.pack(side=tk.LEFT, padx=(0, 5))
        filter_entry.bind('<Return>', lambda e: self.apply_filter())
        
        ttk.Button(filter_tree_frame, text="Apply Filter", command=self.apply_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_tree_frame, text="Clear Filter", command=self.clear_filter).pack(side=tk.LEFT, padx=(0, 20))
        
        # Tree expansion controls
        ttk.Button(filter_tree_frame, text="Expand All", command=self.expand_all_trees).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_tree_frame, text="Collapse All", command=self.collapse_all_trees).pack(side=tk.LEFT)
        
        # Tree comparison frame (adjusted height to make room for status log)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
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
        copy_frame.pack(fill=tk.X, pady=(0, 5))
        
             
                                                                                                                            
                                                                                                                            
                                                                                        
             
        ttk.Button(copy_frame, text="Copy LEFT to Right", command=self.copy_left_to_right, style="RedBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Copy RIGHT to Left", command=self.copy_right_to_left, style="GreenBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Quit", command=self.root.quit, style="BlueBold.TButton").pack(side=tk.RIGHT)

        # status log frame at bottom with export functionality
        status_log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding=5)
        status_log_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Status log header with export button
        status_header = ttk.Frame(status_log_frame)
        status_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(status_header, text=f"Operation History ({STATUS_LOG_MAX_HISTORY:,} lines max):", 
                 font=("TkDefaultFont", 9)).pack(side=tk.LEFT)
        ttk.Button(status_header, text="Export Log", command=self.export_status_log).pack(side=tk.RIGHT)
        
        # Create text widget with scrollbar for status log using configurable parameters
        status_log_container = ttk.Frame(status_log_frame)
        status_log_container.pack(fill=tk.X)
        
        self.status_log_text = tk.Text(
            status_log_container, 
            height=STATUS_LOG_VISIBLE_LINES,  # Use configurable visible lines
            wrap=tk.WORD,
            state=tk.DISABLED,  # Read-only
            font=STATUS_LOG_FONT,  # Use configurable font
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
        
        ttk.Label(status_frame, textvariable=self.summary_var).pack(side=tk.LEFT)
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        ttk.Label(status_frame, text="Status:").pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.RIGHT)
        
        # Configure tree event bindings for interaction
        self.setup_tree_events()
        
        logger.debug("User interface setup complete with features")
        
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
        
        logger.debug(f"Applying wildcard filter: {wildcard}")
        self.add_status_message(f"Applying filter: {wildcard}")
        
        # Create progress dialog for filtering
        progress = ProgressDialog(self.root, "Filtering Files", f"Applying filter: {wildcard}...", max_value=100)
        
        try:
            # Use thread for filtering to keep UI responsive
            def filter_thread():
                try:
                    self.perform_filtering(wildcard, progress)
                except Exception as e:
                    logger.error(f"Filter operation failed: {e}")
                    self.root.after(0, lambda: self.add_status_message(f"Filter failed: {str(e)}"))
                finally:
                    self.root.after(0, progress.close)
            
            threading.Thread(target=filter_thread, daemon=True).start()
            
        except Exception as e:
            progress.close()
            logger.error(f"Failed to start filter operation: {e}")
            self.add_status_message(f"Filter failed: {str(e)}")

    def perform_filtering(self, wildcard, progress):
        """Perform the actual filtering operation with performance tracking."""
        logger.debug(f"Performing filtering with pattern: {wildcard}")
        
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
                        logger.warning(f"Filter results limited to {MAX_FILTER_RESULTS} items for performance")
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
            
        logger.debug("Clearing wildcard filter")
        
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
            
        logger.debug("Expanding all tree items")
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
            
        logger.debug("Collapsing all tree items")
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
        logger.debug("Setting up tree event bindings")
        
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
                    logger.debug(f"Synchronized tree {action} for item {item}")
                    
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
            logger.debug(f"Identified missing item: {item_id} with text: {item_text}")
            
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
                logger.debug(f"Item {item_id} ({rel_path}) is different and exists on {side} side")
                
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
                    logger.debug(f"Ignoring click on missing item: {item}")
                return  # Don't process clicks on missing items
                
            # Toggle selection for this item if it's not missing
            self.toggle_item_selection(item, side)
            
    def toggle_item_selection(self, item_id, side):
        """Toggle selection state of an item and handle parent/child logic with root safety."""
        if self.limit_exceeded:
            return  # Don't process selections when limits exceeded
            
        if __debug__:
            logger.debug(f"Toggling selection for item {item_id} on {side} side")
            
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
            logger.debug(f"Item {action}, {side} selection count: {len(selected_set)}")
            
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
            logger.debug(f"Smart ticking children for {item_id} - only selecting different items")
        
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
                    logger.debug(f"Smart-selected different item: {item} ({rel_path})")
                    
            # Recursively process children
            for child in tree.get_children(item):
                tick_recursive(child)
                
        # Process all children of the ticked item
        for child in tree.get_children(item_id):
            tick_recursive(child)
            
        if __debug__:
            logger.debug(f"Smart selection complete: {different_count}/{total_count} children selected (only different items)")
            
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
            logger.debug(f"Unticking parents for item {item_id}, root_item: {root_item}")
        
        parent = tree.parent(item_id)
        while parent:
            selected_set.discard(parent)
            if __debug__:
                logger.debug(f"Unticked parent: {parent}")
            
            # Safety check - if we've reached the root item, stop here
            # Don't try to untick the parent of the root item as it doesn't exist
            if parent == root_item:
                if __debug__:
                    logger.debug(f"Reached root item {root_item}, stopping parent unticking")
                break
                
            next_parent = tree.parent(parent)
            if not next_parent:  # Additional safety check for empty parent
                if __debug__:
                    logger.debug(f"No parent found for {parent}, stopping parent unticking")
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
                logger.debug("Skipping tree display update - already updating or limits exceeded")
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
        logger.debug("Opening left folder browser")
        folder = filedialog.askdirectory(title="Select Left Folder")
        if folder:
            self.left_folder.set(folder)
            self.add_status_message(f"Selected left folder: {folder}")
            logger.info(f"Selected left folder: {folder}")
            
    def browse_right_folder(self):
        """Browse for right folder with limit awareness."""
        logger.debug("Opening right folder browser")
        folder = filedialog.askdirectory(title="Select Right Folder")
        if folder:
            self.right_folder.set(folder)
            self.add_status_message(f"Selected right folder: {folder}")
            logger.info(f"Selected right folder: {folder}")
            
    def start_comparison(self): # v000.0002 changed - removed sorting state reset
        """Start folder comparison in background thread with limit checking and complete reset."""
        logger.info("Starting folder comparison with complete reset")
        
        if not self.left_folder.get() or not self.right_folder.get():
            error_msg = "Both folders must be selected before comparison"
            logger.error(f"Comparison failed: {error_msg}")
            self.add_status_message(f"Error: {error_msg}")
            self.show_error("Please select both folders to compare")
            return
            
        if not Path(self.left_folder.get()).exists():
            error_msg = f"Left folder does not exist: {self.left_folder.get()}"
            logger.error(error_msg)
            self.add_status_message(f"Error: {error_msg}")
            self.show_error(error_msg)
            return
            
        if not Path(self.right_folder.get()).exists():
            error_msg = f"Right folder does not exist: {self.right_folder.get()}"
            logger.error(error_msg)
            self.add_status_message(f"Error: {error_msg}")
            self.show_error(error_msg)
            return
        
        # Reset application state for fresh comparison # v000.0002 changed - removed sorting
        self.limit_exceeded = False
                                                             
                                                             
        
        # Log the reset
        self.add_status_message("RESET: Clearing all data structures for fresh comparison") # v000.0002 changed - removed sorting
        logger.info("Complete application reset initiated - clearing all data") # v000.0002 changed - removed sorting
        
        if __debug__:
            logger.debug(f"Left folder: {self.left_folder.get()}")
            logger.debug(f"Right folder: {self.right_folder.get()}")
            logger.debug(f"Compare criteria: existence={self.compare_existence.get()}, "
                        f"size={self.compare_size.get()}, "
                        f"date_created={self.compare_date_created.get()}, "
                        f"date_modified={self.compare_date_modified.get()}, "
                        f"sha512={self.compare_sha512.get()}")
                                                                        
            
        # Start comparison in background thread
        self.status_var.set("Comparing folders...")
        self.add_status_message("Starting fresh folder comparison...") # v000.0002 changed - removed sorting
        logger.info("Starting background comparison thread with reset state")
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
        logger.info("Beginning folder comparison operation")
        
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
                logger.debug("Cleared previous comparison results and reset root items")
            
            # Step 1: Build file lists for both folders (40% of total work) with early limit checking
            progress.update_progress(5, "Scanning left folder...")
            self.root.after(0, lambda: self.add_status_message("Scanning left folder for files and folders..."))
            
            left_files = self.build_file_list_with_progress(self.left_folder.get(), progress, 5, 25)
            
            if left_files is None:  # Limit exceeded during left scan
                return
            
            file_count_left = len(left_files)
            self.file_count_left = file_count_left
            
            self.root.after(0, lambda: self.add_status_message(f"Left folder scan complete: {file_count_left:,} items found"))
            logger.info(f"Found {file_count_left} items in left folder")
            
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
            logger.info(f"Found {file_count_right} items in right folder")
            
            # Step 2: Compare files (50% of total work)
            progress.update_progress(50, "Comparing files and folders...")
            self.root.after(0, lambda: self.add_status_message("Comparing files and folders for differences..."))
            
            # Get all unique relative paths
            all_paths = set(left_files.keys()) | set(right_files.keys())
            total_paths = len(all_paths)
            logger.info(f"Comparing {total_paths} unique paths")
            
            if __debug__:
                logger.debug(f"Left-only paths: {len(left_files.keys() - right_files.keys())}")
                logger.debug(f"Right-only paths: {len(right_files.keys() - left_files.keys())}")
                logger.debug(f"Common paths: {len(left_files.keys() & right_files.keys())}")
            
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
                        logger.debug(f"Difference found in '{rel_path}': {differences}")
            
            # Step 3: Update UI (10% of total work)
            progress.update_progress(90, "Building comparison trees...")
            self.root.after(0, lambda: self.add_status_message("Building comparison tree views..."))
            
            elapsed_time = time.time() - start_time
            logger.info(f"Comparison completed in {elapsed_time:.2f} seconds")
            logger.info(f"Found {differences_found} items with differences")
            
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
            logger.error(f"Comparison failed with exception: {type(e).__name__}: {str(e)}")
            if __debug__:
                import traceback
                logger.debug("Full exception traceback:")
                logger.debug(traceback.format_exc())
            
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
            logger.debug(f"Building file list with progress for: {root_path}")
        
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
                    logger.debug(f"Root directory is empty: {root_path}")
                
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
                                logger.debug(f"Large file: Performing SHA512 computation via compute_sha512_with_progress() for {path}")
                                sha512_hash = self.compute_sha512_with_progress(str(path), progress)
                            else:
                                # Small files: compute directly without progress overhead # v000.0004 added
                                logger.debug(f"Small file: Performing SHA512 computation locally in build_file_list_with_progress() for {path}")
                                if size < SHA512_MAX_FILE_SIZE:
                                    hasher = hashlib.sha512()
                                    with open(str(path), 'rb') as f:
                                        hasher.update(f.read())
                                    sha512_hash = hasher.hexdigest()
                        except Exception as e:
                            if __debug__:
                                logger.debug(f"SHA512 computation failed for {path}: {e}")
                    
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
                        logger.debug(f"Skipping file due to error: {path} - {e}")
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
                        logger.debug(f"Skipping directory due to error: {path} - {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scanning directory {root_path}: {e}")
            if __debug__:
                import traceback
                logger.debug(traceback.format_exc())
            
        logger.info(f"Scanned {root_path}: {file_count} files, {dir_count} directories, {error_count} errors")
        if __debug__:
            logger.debug(f"Total items found: {len(files)}")
            
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
                logger.debug(f"In compute_sha512_with_progress() ... returning None ... not path.exists() or not path.is_file() for {file_path}")
                return None
                
            size = path.stat().st_size
            if size >= SHA512_MAX_FILE_SIZE:  # v000.0004 respect configurable limit
                if __debug__:
                    logger.debug(f"In compute_sha512_with_progress() File too large for SHA512 computation: {size} bytes > {SHA512_MAX_FILE_SIZE} bytes")
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
                logger.debug(f"In compute_sha512_with_progress() SHA512 computation failed for {file_path}: {e}")
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
                    left_display = left_item.date_created.strftime("%Y-%m-%d %H:%M:%S.%f") if left_item.date_created else "None" # v001.0010 changed - full microsecond precision debug display
                    right_display = right_item.date_created.strftime("%Y-%m-%d %H:%M:%S.%f") if right_item.date_created else "None" # v001.0010 changed - full microsecond precision debug display
                    left_raw = left_item.date_created.timestamp() if left_item.date_created else 0 # v001.0010 added [debug date created comparison with full microsecond precision]
                    right_raw = right_item.date_created.timestamp() if right_item.date_created else 0 # v001.0010 added [debug date created comparison with full microsecond precision]
                    diff_microseconds = abs(left_raw - right_raw) * 1_000_000 # v001.0010 added [debug date created comparison with full microsecond precision]
                    logger.debug(f"DATE CREATED DIFFERENCE found for {left_item.path}:") # v001.0010 added [debug date created comparison with full microsecond precision]
                    logger.debug(f"  Left display : {left_display}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    logger.debug(f"  Right display: {right_display}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    logger.debug(f"  Left raw     : {left_item.date_created}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    logger.debug(f"  Right raw    : {right_item.date_created}") # v001.0010 added [debug date created comparison with full microsecond precision]
                    logger.debug(f"  Difference   : {diff_microseconds:.1f} microseconds") # v001.0010 added [debug date created comparison with full microsecond precision]
                
            if self.compare_date_modified.get() and left_item.date_modified != right_item.date_modified:
                differences.add('date_modified')
                # v001.0010 added [debug date modified comparison with full microsecond precision]
                if __debug__:
                    left_display = left_item.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f") if left_item.date_modified else "None" # v001.0010 changed - full microsecond precision debug display
                    right_display = right_item.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f") if right_item.date_modified else "None" # v001.0010 changed - full microsecond precision debug display
                    left_raw = left_item.date_modified.timestamp() if left_item.date_modified else 0 # v001.0010 added [debug date modified comparison with full microsecond precision]
                    right_raw = right_item.date_modified.timestamp() if right_item.date_modified else 0 # v001.0010 added [debug date modified comparison with full microsecond precision]
                    diff_microseconds = abs(left_raw - right_raw) * 1_000_000 # v001.0010 added [debug date modified comparison with full microsecond precision]
                    logger.debug(f"DATE MODIFIED DIFFERENCE found for {left_item.path}:") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    logger.debug(f"  Left display : {left_display}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    logger.debug(f"  Right display: {right_display}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    logger.debug(f"  Left raw     : {left_item.date_modified}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    logger.debug(f"  Right raw    : {right_item.date_modified}") # v001.0010 added [debug date modified comparison with full microsecond precision]
                    logger.debug(f"  Difference   : {diff_microseconds:.1f} microseconds") # v001.0010 added [debug date modified comparison with full microsecond precision]
                
            if (self.compare_sha512.get() and left_item.sha512 and right_item.sha512 
                and left_item.sha512 != right_item.sha512):
                differences.add('sha512')
                
        return differences
        
    def update_comparison_ui(self): # v000.0002 changed - removed sorting parameters 
        """Update UI with comparison results and limit checking (no sorting)."""
        if self.limit_exceeded:
            logger.warning("Skipping UI update due to file limit exceeded")
            return
            
        logger.info("Updating UI with comparison results")
        
        # Clear existing tree content
        left_items = len(self.left_tree.get_children())
        right_items = len(self.right_tree.get_children())
        
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)
            
        if __debug__:
            logger.debug(f"Cleared {left_items} left tree items and {right_items} right tree items")
            
        # Build tree structure with root handling # v000.0002 changed - removed sorting
        self.build_trees_with_root_paths() # v000.0002 changed - (no sorting)
                                                 
                                              
         
        
        # Update status
        self.status_var.set("Ready")
        self.update_summary()
        logger.info("UI update completed")

    def update_comparison_ui_filtered(self): # v000.0002 changed - removed sorting parameters
        """Update UI with filtered comparison results and limit checking (no sorting)."""
        if self.limit_exceeded:
            logger.warning("Skipping filtered UI update due to file limit exceeded")
            return
            
        logger.info("Updating UI with filtered comparison results")
        
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
        logger.info("Filtered UI update completed")

    def build_trees_with_filtered_results(self):
        """Build tree structures from filtered comparison results with limit checking (no sorting)."""
        if self.limit_exceeded:
            return
            
        if __debug__:
            logger.debug(f"Building trees from {len(self.filtered_results)} filtered results")
        
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
                    date_created_str = result.left_item.date_created.strftime("%Y-%m-%d %H:%M:%S.%f") if result.left_item.date_created else ""     # v001.0010 changed - full microsecond precision timestamp display
                    date_modified_str = result.left_item.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f") if result.left_item.date_modified else ""  # v001.0010 changed - full microsecond precision timestamp display
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
                    date_created_str = result.left_item.date_created.strftime("%Y-%m-%d %H:%M:%S.%f") if result.left_item.date_created else ""     # v001.0010 changed - full microsecond precision timestamp display
                    date_modified_str = result.left_item.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f") if result.left_item.date_modified else ""  # v001.0010 changed - full microsecond precision timestamp display
                    sha512_str = result.left_item.sha512[:16] + "..." if result.left_item.sha512 else ""
                    status = "Different" if result.is_different else "Same"
                    item_text = f"☐ {rel_path}"
                
                # v000.0004 changed - Use folder-aware display values
                size_str = self.format_size(result.left_item.size) if result.left_item.size else ""
                item_id = self.left_tree.insert(self.root_item_left, tk.END, text=item_text,
                                              values=(size_str, date_created_str, date_modified_str, sha512_str, status))
                self.path_to_item_left[rel_path] = item_id
                
            # Add right item if it exists
            if result.right_item and result.right_item.exists:
                # v000.0006 added - Handle folder vs file display with timestamps
                if result.right_item.is_folder:
                    # This is a folder - show timestamps and smart status
                    date_created_str = result.right_item.date_created.strftime("%Y-%m-%d %H:%M:%S.%f") if result.right_item.date_created else ""     # v001.0010 changed - full microsecond precision timestamp display
                    date_modified_str = result.right_item.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f") if result.right_item.date_modified else ""  # v001.0010 changed - full microsecond precision timestamp display
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
                    date_created_str = result.right_item.date_created.strftime("%Y-%m-%d %H:%M:%S.%f") if result.right_item.date_created else ""     # v001.0010 changed - full microsecond precision timestamp display
                    date_modified_str = result.right_item.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f") if result.right_item.date_modified else ""  # v001.0010 changed - full microsecond precision timestamp display
                    sha512_str = result.right_item.sha512[:16] + "..." if result.right_item.sha512 else ""
                    status = "Different" if result.is_different else "Same"
                    item_text = f"☐ {rel_path}"
                
                # v000.0006 changed - Use folder-aware display values
                size_str = self.format_size(result.right_item.size) if result.right_item.size else ""
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
            logger.debug(f"Building trees with root paths from {len(self.comparison_results)} comparison results")
                                                                                    
        
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
            logger.debug(f"Created root items: left={self.root_item_left}, right={self.root_item_right}")
        
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
                    logger.debug("Skipping empty relative path")
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
                                logger.debug(f"REAL CONFLICT: Cannot add folder '{final_name}' - file exists with same name")
                        # v000.0003 changed - for folders, don't store metadata directly, just ensure dict exists
                    else:
                        # This is a file
                        if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: file trying to replace a folder (should be very rare)
                            if __debug__:
                                logger.debug(f"REAL CONFLICT: Cannot add file '{final_name}' - folder exists with same name")
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
                                logger.debug(f"REAL CONFLICT: Cannot add folder '{final_name}' - file exists with same name")
                        # v000.0003 changed - for folders, don't store metadata directly, just ensure dict exists
                    else:
                        # This is a file
                        if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: file trying to replace a folder (should be very rare)
                            if __debug__:
                                logger.debug(f"REAL CONFLICT: Cannot add file '{final_name}' - folder exists with same name")
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
            logger.debug(f"Added {missing_left} missing left placeholders, {missing_right} missing right placeholders")
            
        # Populate trees under root items with stable alphabetical ordering # v000.0002 changed - removed sorting
        logger.info("Populating tree views under root paths with stable ordering...") # v000.0002 changed - removed sorting
        self.populate_tree(self.left_tree, left_structure, self.root_item_left, 'left', '') # v000.0002 changed - removed sorting
                                                                         
        self.populate_tree(self.right_tree, right_structure, self.root_item_right, 'right', '') # v000.0002 changed - removed sorting
                                                                         
        
        elapsed_time = time.time() - start_time
        if __debug__:
            logger.debug(f"Tree building with root paths completed in {elapsed_time:.3f} seconds")
            
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
                            if folder_metadata.date_created:
                                date_created_str = folder_metadata.date_created.strftime("%Y-%m-%d %H:%M:%S.%f")    # v001.0010 changed - full microsecond precision timestamp display
                            if folder_metadata.date_modified:
                                date_modified_str = folder_metadata.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f")  # v001.0010 changed - full microsecond precision timestamp display
                        
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
                    size_str = self.format_size(content.size) if content.size else ""
                    date_created_str = content.date_created.strftime("%Y-%m-%d %H:%M:%S.%f") if content.date_created else ""     # v001.0010 changed - full microsecond precision timestamp display
                    date_modified_str = content.date_modified.strftime("%Y-%m-%d %H:%M:%S.%f") if content.date_modified else ""  # v001.0010 changed - full microsecond precision timestamp display
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
        
    def format_size(self, size_bytes):
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
            logger.debug("Auto-clearing all selections before selecting differences in left pane")
            
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
            logger.debug(f"Selected {count} different items in left pane (after auto-clear)")
            
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
            logger.debug("Auto-clearing all selections before selecting differences in right pane")
            
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
            logger.debug(f"Selected {count} different items in right pane (after auto-clear)")
            
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
            logger.debug(f"Clearing ALL {cleared_count} selections in left pane")
            
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
            logger.debug(f"Clearing ALL {cleared_count} selections in right pane")
            
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
        
        logger.info(f"Starting copy operation{dry_run_text}: {direction} with {len(selected_paths)} items")
        
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
                            size_str = self.format_size(file_size)
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
                    logger.error(error_msg)
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
            logger.info(summary)
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
            logger.error(f"Copy operation{dry_run_text} failed: {e}")
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
        logger.info("Refreshing trees and clearing selections after copy operation")
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
        logger.error(f"Displaying error to user: {message}")
        
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
        logger.info("Starting FolderCompareSync GUI application.")
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Application crashed: {type(e).__name__}: {str(e)}")
            if __debug__:
                import traceback
                logger.debug("Crash traceback:")
                logger.debug(traceback.format_exc())
            raise
        finally:
            logger.info("Application shutdown")

def main():
    """
    Main entry point with system detection and configuration logging.
    
    Purpose:
    --------
    Application startup function that initializes logging, detects system
    configuration, and starts the main application with proper error handling.
    """
    logger.info("=== FolderCompareSync Startup ===")
    if __debug__:
        logger.debug("Working directory : " + os.getcwd())
        logger.debug("Python version    : " + sys.version)
        logger.debug("Computer name     : " + platform.node())
        logger.debug("Platform          : " + sys.platform)
        logger.debug("Architecture      : " + platform.architecture()[0])
        logger.debug("Machine           : " + platform.machine())
        logger.debug("Processor         : " + platform.processor())

    # Detailed Windows information
    if sys.platform == "win32":
        try:
            win_ver = platform.win32_ver()
            logger.debug(f"Windows version   : {win_ver[0]}")
            logger.debug(f"Windows build     : {win_ver[1]}")
            if win_ver[2]:  # Service pack
                logger.debug(f"Service pack      : {win_ver[2]}")
            logger.debug(f"Windows type      : {win_ver[3]}")
            # Try to get Windows edition
            try:
                edition = platform.win32_edition()
                if edition:
                    logger.debug(f"Windows edition   : {edition}")
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
                logger.debug(f"Windows 11 version: {win_versions[build_num]} (build {build_num})")
            elif build_num.startswith("27") or build_num.startswith("28"):
                logger.debug(f"Windows version   : Future windows build {build_num}")
            elif build_num.startswith("26") or build_num.startswith("22"):
                logger.debug(f"Windows 11 version: Unknown windows build {build_num}")
            elif build_num.startswith("19"):
                logger.debug(f"Windows 10 build  : {build_num}")
            else:
                logger.debug(f"Windows version   : Unknown windows build {build_num}")
        except Exception as e:
            logger.debug(f"Error getting Windows details: {e}")

    # Log  configuration including new limits and features
    logger.debug("FolderCompareSync Configuration:")
    logger.debug(f"  Max files/folders: {MAX_FILES_FOLDERS:,}")
    logger.debug(f"  Status log history: {STATUS_LOG_MAX_HISTORY:,} lines")
    logger.debug(f"  Copy strategy threshold: {COPY_STRATEGY_THRESHOLD / (1024*1024):.1f} MB")
    logger.debug(f"  SHA512 status threshold: {SHA512_STATUS_MESSAGE_THRESHOLD / (1024*1024):.1f} MB")
    logger.debug(f"  Simple verification enabled: {COPY_VERIFICATION_ENABLED}")
    logger.debug(f"  Retry count: {COPY_RETRY_COUNT}")
    logger.debug(f"  Network timeout: {COPY_NETWORK_TIMEOUT}s")
    logger.debug(f"  Dry run support: Enabled")
    logger.debug(f"  Status log export: Enabled")
    logger.debug(f"  Error details dialog: Enabled")
    logger.debug(f"  Path handling: Standardized on pathlib")
    
    try:
        FolderCompareSync_class_app = FolderCompareSync_class()
        # uncomment the next line to MANUALLY Enable debug mode logging for testing the application GUI event loop
        #FolderCompareSync_class_app.set_debug_loglevel(True)

        FolderCompareSync_class_app.run()    # start the application GUI event loop
    except Exception as e:
        logger.error(f"Fatal error: {type(e).__name__}: {str(e)}")
        if __debug__:
            import traceback
            logger.debug("Fatal error traceback:")
            logger.debug(traceback.format_exc())
        raise
    finally:
        logger.info("=== FolderCompareSync Shutdown ===")


if __name__ == "__main__":
    main()
