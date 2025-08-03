"""
Complete Standalone File Timestamp Manager for Windows
Everything in one file - no external dependencies needed.

This script can:
1. Get file creation and modification times with proper timezone handling
2. Set file creation and modification times using Windows API
3. Process media files and set timestamps based on dates in filenames
4. Run tests to verify functionality

Usage examples:
    # Process media files (dry run first)
    python standalone_file_timestamp_manager.py --folder "C:\\Videos" --dry-run
    
    # Actually process files
    python standalone_file_timestamp_manager.py --folder "C:\\Videos" --recurse
    
    # Run tests
    python standalone_file_timestamp_manager.py --test
    
    # Show usage examples
    python standalone_file_timestamp_manager.py --demo
"""

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


def process_media_files_with_dates(folder_path, recurse=False, dry_run=False):
    """
    Process media files and set their timestamps based on dates in filenames.
    Falls back to existing creation time if no date is found in filename.
    
    Args:
        folder_path: Path to folder containing media files
        recurse: Whether to process subdirectories recursively
        dry_run: If True, shows what would be done without actually changing files
    """
    # Initialize timestamp manager
    timestamp_manager = FileTimestampManager()
    
    # Valid file extensions for media files
    valid_extensions = ('.ts', '.mp4', '.mpg', '.avi', '.mkv', '.mov', '.wmv', 
                       '.mp3', '.aac', '.wav', '.flac', '.m4a', '.jpg', '.jpeg', 
                       '.png', '.tiff', '.bmp', '.gif', '.vob', '.bprj')
    
    # Regex pattern for date in filename (YYYY-MM-DD format)
    date_pattern = r'\b(\d{4})-(\d{2})-(\d{2})\b'
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: Folder '{folder}' does not exist.")
        return
    
    print(f"Processing folder: {folder}")
    print(f"Recursive: {recurse}")
    print(f"Dry run: {dry_run}")
    print(f"Valid extensions: {valid_extensions}")
    print("-" * 60)
    
    # Collect files to process
    files_to_process = []
    
    if recurse:
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(valid_extensions):
                    files_to_process.append(Path(root) / file)
    else:
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                files_to_process.append(file_path)
    
    if not files_to_process:
        print("No media files found to process.")
        return
    
    print(f"Found {len(files_to_process)} media files to process.")
    print()
    
    # Process each file
    processed_count = 0
    error_count = 0
    
    for file_path in files_to_process:
        try:
            # Look for date pattern in filename
            filename = file_path.name
            match = re.search(date_pattern, filename)
            
            if match:
                # Extract date from filename
                year, month, day = match.groups()
                target_date = datetime(int(year), int(month), int(day), 0, 0, 0)
                source = "filename"
                print(f"📅 Found date in filename: {target_date.strftime('%Y-%m-%d')} - {filename}")
                
            else:
                # Fall back to existing creation time
                creation_time, _ = timestamp_manager.get_file_timestamps(file_path)
                # Set time to midnight but keep the date
                target_date = creation_time.replace(hour=0, minute=0, second=0, microsecond=0)
                source = "existing creation time"
                print(f"⏰ Using existing creation time: {target_date.strftime('%Y-%m-%d')} - {filename}")
            
            if not dry_run:
                # Set both creation and modification times
                success = timestamp_manager.set_file_timestamps(
                    file_path,
                    creation_time=target_date,
                    modification_time=target_date
                )
                
                if success:
                    print(f"✅ Successfully set timestamps from {source}")
                    processed_count += 1
                else:
                    print(f"❌ Failed to set timestamps")
                    error_count += 1
            else:
                print(f"🔍 Would set timestamps from {source}")
                processed_count += 1
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            error_count += 1
        
        print()
    
    # Summary
    print("-" * 60)
    print(f"Processing complete!")
    print(f"Files processed: {processed_count}")
    if error_count > 0:
        print(f"Errors: {error_count}")
    
    if dry_run:
        print("\nThis was a dry run - no files were actually modified.")
        print("Run again without --dry-run to apply changes.")

def run_tests():
    """Run comprehensive tests of the FileTimestampManager."""
    print("="*60)
    print("RUNNING FILE TIMESTAMP MANAGER TESTS")
    print("="*60)
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    # Initialize manager and test variables
    manager = FileTimestampManager()
    print(f"Detected timezone: {manager._local_tz}")
    
    test_dir = None
    success_count = 0
    total_tests = 0
    
    def assert_test(condition, test_name, error_msg=""):
        nonlocal success_count, total_tests
        total_tests += 1
        if condition:
            print(f"✓ PASS: {test_name}")
            success_count += 1
        else:
            print(f"✗ FAIL: {test_name}")
            if error_msg:
                print(f"  Error: {error_msg}")
    
    try:
        # Setup test environment
        print("\nSetting up test environment...")
        test_dir = Path(tempfile.mkdtemp(prefix="timestamp_test_"))
        print(f"Test directory: {test_dir}")
        
        # Create test files
        test_files = []
        for i in range(3):
            test_file = test_dir / f"test_file_{i+1}.txt"
            test_file.write_text(f"Test file {i+1} content")
            test_files.append(test_file)
        
        time.sleep(0.1)  # Ensure files are created
        
        print("\n" + "="*40)
        print("TEST 1: Timestamp Retrieval")
        print("="*40)
        
        for test_file in test_files:
            try:
                creation_time, modification_time = manager.get_file_timestamps(test_file)
                
                assert_test(
                    isinstance(creation_time, datetime),
                    f"Creation time is a datetime object for {test_file.name}"
                )
                
                assert_test(
                    isinstance(modification_time, datetime),
                    f"Modification time is a datetime object for {test_file.name}"
                )
                
                assert_test(
                    creation_time.tzinfo is not None,
                    f"Creation time is timezone-aware for {test_file.name}"
                )
                
                assert_test(
                    modification_time.tzinfo is not None,
                    f"Modification time is timezone-aware for {test_file.name}"
                )
                
                print(f"  {test_file.name}: Created {manager.format_timestamp(creation_time)}")
                
            except Exception as e:
                assert_test(False, f"Retrieve timestamps for {test_file.name}", str(e))
        
        print("\n" + "="*40)
        print("TEST 2: Timestamp Setting")
        print("="*40)
        
        test_dates = [
            datetime(2020, 1, 1, 12, 0, 0),
            datetime(2022, 6, 15, 9, 30, 45),
            datetime(2023, 12, 25, 18, 15, 30),
        ]
        
        for i, test_file in enumerate(test_files):
            test_date = test_dates[i]
            
            try:
                success = manager.set_file_timestamps(
                    test_file,
                    creation_time=test_date,
                    modification_time=test_date
                )
                
                assert_test(success, f"Set timestamps for {test_file.name}")
                
                if success:
                    new_creation, new_modification = manager.get_file_timestamps(test_file)
                    
                    creation_diff = abs((new_creation.replace(tzinfo=None) - test_date).total_seconds())
                    modification_diff = abs((new_modification.replace(tzinfo=None) - test_date).total_seconds())
                    
                    assert_test(
                        creation_diff < 2,
                        f"Creation time accuracy for {test_file.name} (diff: {creation_diff:.3f}s)"
                    )
                    
                    assert_test(
                        modification_diff < 2,
                        f"Modification time accuracy for {test_file.name} (diff: {modification_diff:.3f}s)"
                    )
                    
                    print(f"  {test_file.name}: Set to {manager.format_timestamp(new_creation)}")
                
            except Exception as e:
                assert_test(False, f"Set timestamps for {test_file.name}", str(e))
        
        print("\n" + "="*40)
        print("TEST 3: Edge Cases")
        print("="*40)
        
        # Test non-existent file
        try:
            non_existent = test_dir / "does_not_exist.txt"
            manager.get_file_timestamps(non_existent)
            assert_test(False, "Non-existent file should raise FileNotFoundError")
        except FileNotFoundError:
            assert_test(True, "Non-existent file raises FileNotFoundError")
        except Exception as e:
            assert_test(False, "Non-existent file error handling", str(e))
        
        # Test timezone-naive datetime
        if test_files:
            naive_date = datetime(2021, 8, 20, 10, 0, 0)
            try:
                success = manager.set_file_timestamps(test_files[0], creation_time=naive_date)
                assert_test(success, "Handle timezone-naive datetime")
            except Exception as e:
                assert_test(False, "Handle timezone-naive datetime", str(e))
        
        # Test copy timestamps
        if len(test_files) >= 2:
            try:
                success = manager.copy_timestamps(test_files[0], test_files[1])
                assert_test(success, "Copy timestamps between files")
            except Exception as e:
                assert_test(False, "Copy timestamps", str(e))
        
    finally:
        # Cleanup
        if test_dir and test_dir.exists():
            print(f"\nCleaning up test directory: {test_dir}")
            shutil.rmtree(test_dir)
    
    # Final results
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("✅ FileTimestampManager is working correctly!")
    else:
        print(f"❌ {total_tests - success_count} test(s) failed")
        print("You may need to run as administrator or check file permissions.")
    
    success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    return success_count == total_tests


def demonstrate_usage():
    """Show basic usage examples."""
    print("="*60)
    print("BASIC USAGE EXAMPLES")
    print("="*60)
    
    manager = FileTimestampManager()
    
    print("1. CREATING AND USING FileTimestampManager:")
    print("   manager = FileTimestampManager()")
    print()
    
    print("2. GETTING FILE TIMESTAMPS:")
    print("   creation_time, mod_time = manager.get_file_timestamps('myfile.txt')")
    print("   print(f'Created: {manager.format_timestamp(creation_time)}')")
    print()
    
    print("3. SETTING FILE TIMESTAMPS:")
    print("   from datetime import datetime")
    print("   new_date = datetime(2023, 6, 15, 12, 0, 0)")
    print("   success = manager.set_file_timestamps('myfile.txt',")
    print("                                         creation_time=new_date,")
    print("                                         modification_time=new_date)")
    print()
    
    print("4. COPYING TIMESTAMPS:")
    print("   success = manager.copy_timestamps('source.txt', 'target.txt')")
    print()
    
    print("5. PROCESSING MEDIA FILES (your use case):")
    print("   # Run this script with --folder option:")
    print("   python standalone_file_timestamp_manager.py --folder 'C:\\Videos' --dry-run")
    print("   python standalone_file_timestamp_manager.py --folder 'C:\\Videos' --recurse")
    print()
    
    # Try to demonstrate with actual file
    try:
        script_file = Path(__file__)
        if script_file.exists():
            creation_time, mod_time = manager.get_file_timestamps(script_file)
            print("6. REAL EXAMPLE (this script file):")
            print(f"   File: {script_file.name}")
            print(f"   Created:  {manager.format_timestamp(creation_time)}")
            print(f"   Modified: {manager.format_timestamp(mod_time)}")
            print()
    except Exception as e:
        print(f"   Could not demonstrate with real file: {e}")
    
    print("Your detected timezone:", manager._local_tz)


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Complete File Timestamp Manager for Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show usage examples
  python standalone_file_timestamp_manager.py --demo
  
  # Run tests to verify functionality
  python standalone_file_timestamp_manager.py --test
  
  # Process current directory (dry run first)
  python standalone_file_timestamp_manager.py --folder . --dry-run
  
  # Process specific folder recursively
  python standalone_file_timestamp_manager.py --folder "C:\\Media\\Videos" --recurse
  
  # Process folder with double backslashes (Windows command line)
  python standalone_file_timestamp_manager.py --folder "T:\\\\HDTV\\\\" --recurse

Notes:
  - Always run with --dry-run first to see what would be done
  - You may need to run as administrator for some operations
  - Files with dates in format YYYY-MM-DD in filename will use that date
  - Other files will use their existing creation date (time set to 00:00:00)
        """
    )
    
    parser.add_argument("--folder", 
                       help="Folder to process (use double backslashes on Windows cmd)")
    parser.add_argument("--recurse", action="store_true",
                       help="Recursively process subdirectories")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--test", action="store_true",
                       help="Run comprehensive tests")
    parser.add_argument("--demo", action="store_true",
                       help="Show basic usage examples")
    
    args = parser.parse_args()
    
    # Check platform
    if sys.platform != "win32":
        print("⚠️  WARNING: This script is designed for Windows systems.")
        print("Some functionality may not work correctly on other platforms.")
    
    if args.test:
        success = run_tests()
        return 0 if success else 1
    
    if args.demo:
        demonstrate_usage()
        return 0
    
    if not args.folder:
        print("Please specify an action:")
        print("  --demo     Show usage examples")
        print("  --test     Run functionality tests")
        print("  --folder   Process media files in specified folder")
        print()
        print("Use --help for more information")
        return 1
    
    # Handle Windows double backslashes
    folder_path = args.folder.replace("\\\\", "\\").rstrip("\\").rstrip(" ")
    
    print("Complete File Timestamp Manager")
    print("="*60)
    
    process_media_files_with_dates(folder_path, args.recurse, args.dry_run)
    return 0


if __name__ == "__main__":
    exit(main())
