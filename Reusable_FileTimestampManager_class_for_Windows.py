# ---------- Start of Common FileTimestampManager Code ----------

"""
Reusable FileTimestampManager class for Windows
Copy this entire section into your own programs.
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


class FileTimestampManager:
    """
    A class to reliably manage file timestamps on Windows systems.
    Handles both retrieval and setting of creation and modification times
    with proper timezone awareness.
    """
    
    def __init__(self):
        """Initialize the timestamp manager with local timezone detection."""
        self._local_tz = self._get_local_timezone()
        self._windows_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    
    def _get_local_timezone(self):
        """Get the system's local timezone reliably."""
        try:
            # Try to get system timezone using zoneinfo (Python 3.9+)
            import zoneinfo
            # Get the system timezone key from the system
            if hasattr(time, 'tzname') and time.tzname[0]:
                # Try common mappings for Windows timezone names
                windows_to_iana = {
                    'Cen. Australia Standard Time': 'Australia/Adelaide',
                    'AUS Central Standard Time': 'Australia/Darwin',
                    'E. Australia Standard Time': 'Australia/Brisbane',
                    'AUS Eastern Standard Time': 'Australia/Sydney',
                    'W. Australia Standard Time': 'Australia/Perth',
                    'Tasmania Standard Time': 'Australia/Hobart',
                    'Eastern Standard Time': 'America/New_York',
                    'Central Standard Time': 'America/Chicago',
                    'Mountain Standard Time': 'America/Denver',
                    'Pacific Standard Time': 'America/Los_Angeles',
                }
                
                # Try to map Windows timezone name to IANA
                win_tz_name = time.tzname[0]
                if win_tz_name in windows_to_iana:
                    return zoneinfo.ZoneInfo(windows_to_iana[win_tz_name])
                
                # Try the name directly (might work on some systems)
                try:
                    return zoneinfo.ZoneInfo(win_tz_name)
                except:
                    pass
        except (ImportError, AttributeError, Exception):
            pass
        
        try:
            # Fallback to getting timezone from time module offset
            if time.daylight:
                # DST is observed
                offset_seconds = -time.altzone
            else:
                # No DST
                offset_seconds = -time.timezone
            
            # Create timezone object with the offset
            return timezone(timedelta(seconds=offset_seconds))
        except:
            # Final fallback - assume UTC
            return timezone.utc
    
    def get_file_timestamps(self, file_path: Union[str, Path]) -> Tuple[datetime, datetime]:
        """
        Get creation and modification timestamps from a file.
        
        Args:
            file_path: Path to the file
            
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
            # Get timestamps as UTC seconds since epoch
            creation_timestamp = os.path.getctime(file_path)
            modification_timestamp = os.path.getmtime(file_path)
            
            # Convert to timezone-aware datetime objects in local timezone
            creation_time = datetime.fromtimestamp(creation_timestamp, tz=self._local_tz)
            modification_time = datetime.fromtimestamp(modification_timestamp, tz=self._local_tz)
            
            return creation_time, modification_time
            
        except OSError as e:
            raise OSError(f"Error accessing file timestamps for {file_path}: {e}")
    
    def set_file_timestamps(self, file_path: Union[str, Path], 
                          creation_time: Optional[datetime] = None,
                          modification_time: Optional[datetime] = None) -> bool:
        """
        Set creation and/or modification timestamps on a file.
        
        Args:
            file_path: Path to the file
            creation_time: New creation time (optional)
            modification_time: New modification time (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If neither timestamp is provided
        """
        if creation_time is None and modification_time is None:
            raise ValueError("At least one timestamp must be provided")
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Convert datetime objects to Windows FILETIME format
            creation_filetime = None
            modification_filetime = None
            
            if creation_time is not None:
                creation_filetime = self._datetime_to_filetime(creation_time)
            
            if modification_time is not None:
                modification_filetime = self._datetime_to_filetime(modification_time)
            
            # Use Windows API to set timestamps
            return self._set_file_times_windows(str(file_path), creation_filetime, modification_filetime)
            
        except Exception as e:
            print(f"Error setting timestamps for {file_path}: {e}")
            return False
    
    def _datetime_to_filetime(self, dt: datetime) -> int:
        """
        Convert a datetime object to Windows FILETIME format.
        
        Args:
            dt: Datetime object (timezone-aware or naive)
            
        Returns:
            Windows FILETIME as integer (100-nanosecond intervals since 1601-01-01)
        """
        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            # Assume naive datetime is in local timezone
            dt = dt.replace(tzinfo=self._local_tz)
        
        # Convert to UTC
        dt_utc = dt.astimezone(timezone.utc)
        
        # Calculate time difference from Windows epoch
        time_diff = dt_utc - self._windows_epoch
        
        # Convert to 100-nanosecond intervals
        filetime = int(time_diff.total_seconds() * 10_000_000)
        
        return filetime
    
    def _set_file_times_windows(self, file_path: str, 
                               creation_time: Optional[int] = None,
                               modification_time: Optional[int] = None) -> bool:
        """
        Use Windows API to set file timestamps.
        
        Args:
            file_path: Path to the file
            creation_time: Creation time in FILETIME format (optional)
            modification_time: Modification time in FILETIME format (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open file handle with write access
            handle = ctypes.windll.kernel32.CreateFileW(
                file_path,
                wintypes.DWORD(0x40000000),  # GENERIC_WRITE
                wintypes.DWORD(0x00000001 | 0x00000002),  # FILE_SHARE_READ | FILE_SHARE_WRITE
                None,  # Security attributes
                wintypes.DWORD(3),  # OPEN_EXISTING
                wintypes.DWORD(0x80),  # FILE_ATTRIBUTE_NORMAL
                None   # Template file
            )
            
            if handle == -1:  # INVALID_HANDLE_VALUE
                return False
            
            # Prepare FILETIME structures
            creation_ft = None
            modification_ft = None
            
            if creation_time is not None:
                creation_ft = ctypes.byref(ctypes.c_ulonglong(creation_time))
            
            if modification_time is not None:
                modification_ft = ctypes.byref(ctypes.c_ulonglong(modification_time))
            
            # Set file times
            result = ctypes.windll.kernel32.SetFileTime(
                handle,
                creation_ft,      # Creation time
                None,             # Last access time (unchanged)
                modification_ft   # Modification time
            )
            
            # Close handle
            ctypes.windll.kernel32.CloseHandle(handle)
            
            return bool(result)
            
        except Exception as e:
            print(f"Windows API error: {e}")
            return False
    
    def copy_timestamps(self, source_file: Union[str, Path], 
                       target_file: Union[str, Path]) -> bool:
        """
        Copy timestamps from source file to target file.
        
        Args:
            source_file: Source file path
            target_file: Target file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            creation_time, modification_time = self.get_file_timestamps(source_file)
            return self.set_file_timestamps(target_file, creation_time, modification_time)
        except Exception as e:
            print(f"Error copying timestamps: {e}")
            return False
    
    def format_timestamp(self, dt: datetime, include_timezone: bool = True) -> str:
        """
        Format a datetime object for display.
        
        Args:
            dt: Datetime object
            include_timezone: Whether to include timezone info
            
        Returns:
            Formatted datetime string
        """
        if include_timezone:
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")

    """
    # EXAMPLE OF HOW TO USE THE FileTimestampManager CLASS
    # Instantiate the FileTimestampManager class as an object
    timestamp_manager = FileTimestampManager()
    # Get timestamps from a file
    try:
        creation_time, mod_time = timestamp_manager.get_file_timestamps(__file__)
        print(f"This script was created: {timestamp_manager.format_timestamp(creation_time)}")
        print(f"This script was modified: {timestamp_manager.format_timestamp(mod_time)}")
    except Exception as e:
        print(f"Error: {e}")
    # Set a specific timestamp
    from datetime import datetime
    new_date = datetime(2023, 6, 15, 12, 0, 0)
    # success = timestamp_manager.set_file_timestamps("somefile.txt", creation_time=new_date)
    """

# ---------- End of Common FileTimestampManager Code ----------
