#!/usr/bin/env python3
"""
FolderCompareSync Test Kit Generator
Creates a comprehensive test environment for testing folder synchronization scenarios.

This script creates two folder trees (left and right) with various test cases including:
- Files with identical content but different timestamps
- Files with different content
- Files existing only on one side
- Empty folders
- Nested folder structures
- Special characters in names
- Various file sizes for performance testing (1MB to 15GB)
- Edge cases for synchronization testing
- SHA512 timing analysis for all file sizes
"""

import os
import sys
import time
import random
import hashlib
import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import ctypes
from ctypes import wintypes
from collections import defaultdict

# Configuration
TEST_ROOT = "FolderCompareSync_TestKit"
LEFT_FOLDER = "Left_Source"
RIGHT_FOLDER = "Right_Target"
MAX_DEPTH = 5
FILES_PER_FOLDER = 25

# File sizes for performance testing
SMALL_FILE_SIZE = 1024  # 1KB
MEDIUM_FILE_SIZE = 1024 * 100  # 100KB
LARGE_FILE_SIZE = 1024 * 1024 * 15  # 15MB (triggers staged copy strategy)

# Specific performance test file sizes
PERFORMANCE_SIZES = {
    "1MB": 1024 * 1024,
    "2MB": 2 * 1024 * 1024,
    "10MB": 10 * 1024 * 1024,
    "100MB": 100 * 1024 * 1024,
    "500MB": 500 * 1024 * 1024,
    "1GB": 1024 * 1024 * 1024,
    "2GB": 2 * 1024 * 1024 * 1024,
    "5GB": 5 * 1024 * 1024 * 1024,
    "10GB": 10 * 1024 * 1024 * 1024,
    "15GB": 15 * 1024 * 1024 * 1024,
}

# Global SHA512 timing tracker
sha512_timings: Dict[str, List[float]] = defaultdict(list)

# Test case categories
class TestCase:
    IDENTICAL = "identical"  # Same content, same timestamps
    SAME_CONTENT_DIFF_TIME = "same_content_diff_time"  # Same content, different timestamps
    DIFFERENT_CONTENT = "different_content"  # Different content
    LEFT_ONLY = "left_only"  # Exists only on left
    RIGHT_ONLY = "right_only"  # Exists only on right
    DIFFERENT_SIZE = "different_size"  # Different file sizes
    EMPTY_FOLDER = "empty_folder"  # Empty folder
    SPECIAL_CHARS = "special_chars"  # Special characters in names
    LARGE_FILE = "large_file"  # Large file to test staged copy
    PERFORMANCE_TEST = "performance_test"  # Specific sized files for performance testing
    HIDDEN_FILE = "hidden_file"  # Hidden file attribute
    READ_ONLY = "read_only"  # Read-only file

def calculate_sha512_with_timing(file_path: Path) -> Tuple[str, float]:
    """Calculate SHA512 hash of a file and return hash and time taken."""
    start_time = time.time()
    sha512_hash = hashlib.sha512()
    
    try:
        with open(file_path, 'rb') as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b''):
                sha512_hash.update(chunk)
    except Exception as e:
        print(f"Error calculating SHA512 for {file_path}: {e}")
        return "", 0.0
    
    elapsed_time = time.time() - start_time
    return sha512_hash.hexdigest(), elapsed_time

def set_file_timestamps(file_path: str, creation_time: datetime.datetime, modified_time: datetime.datetime):
    """Set file creation and modification times using Windows API."""
    # Convert datetime to Windows FILETIME
    def datetime_to_filetime(dt):
        epoch = datetime.datetime(1601, 1, 1)
        delta = dt - epoch
        filetime = int(delta.total_seconds() * 10000000)
        return filetime
    
    creation_filetime = datetime_to_filetime(creation_time)
    modified_filetime = datetime_to_filetime(modified_time)
    
    # Open file handle
    handle = ctypes.windll.kernel32.CreateFileW(
        file_path,
        wintypes.DWORD(0x40000000),  # GENERIC_WRITE
        wintypes.DWORD(0x00000001 | 0x00000002),  # FILE_SHARE_READ | FILE_SHARE_WRITE
        None,
        wintypes.DWORD(3),  # OPEN_EXISTING
        wintypes.DWORD(0x80),  # FILE_ATTRIBUTE_NORMAL
        None
    )
    
    if handle != -1:
        # Set file times
        ctypes.windll.kernel32.SetFileTime(
            handle,
            ctypes.byref(ctypes.c_ulonglong(creation_filetime)),
            None,  # Last access time (unchanged)
            ctypes.byref(ctypes.c_ulonglong(modified_filetime))
        )
        ctypes.windll.kernel32.CloseHandle(handle)

def create_file_with_content(file_path: Path, content: bytes, 
                           creation_time: Optional[datetime.datetime] = None,
                           modified_time: Optional[datetime.datetime] = None,
                           calculate_hash: bool = True):
    """Create a file with specific content and timestamps, optionally calculate SHA512."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)
    
    if creation_time or modified_time:
        if not creation_time:
            creation_time = datetime.datetime.now()
        if not modified_time:
            modified_time = datetime.datetime.now()
        set_file_timestamps(str(file_path), creation_time, modified_time)
    
    # Calculate SHA512 and track timing
    if calculate_hash:
        file_size = len(content)
        size_label = get_size_label(file_size)
        _, elapsed_time = calculate_sha512_with_timing(file_path)
        sha512_timings[size_label].append(elapsed_time)

def get_size_label(size_bytes: int) -> str:
    """Get human-readable size label for tracking."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes // (1024 * 1024)}MB"
    else:
        return f"{size_bytes // (1024 * 1024 * 1024)}GB"

def generate_random_content(size: int) -> bytes:
    """Generate random file content of specified size."""
    return os.urandom(size)

def generate_test_structure():
    """Generate the complete test folder structure."""
    print("FolderCompareSync Test Kit Generator")
    print("=" * 50)
    
    # Create root directory
    root = Path(TEST_ROOT)
    if root.exists():
        print(f"Warning: {TEST_ROOT} already exists. Delete it? (y/n): ", end="")
        if input().lower() != 'y':
            print("Aborted.")
            return
        import shutil
        shutil.rmtree(root)
    
    left_root = root / LEFT_FOLDER
    right_root = root / RIGHT_FOLDER
    
    print(f"Creating test structure in: {root.absolute()}")
    print(f"  Left tree:  {left_root}")
    print(f"  Right tree: {right_root}")
    print()
    
    # Test scenarios to create
    test_scenarios = [
        # (folder_name, test_case, file_count)
        ("01_Identical_Files", TestCase.IDENTICAL, 5),
        ("02_Same_Content_Diff_Times", TestCase.SAME_CONTENT_DIFF_TIME, 5),  # Tests all timestamp combinations
        ("03_Different_Content", TestCase.DIFFERENT_CONTENT, 5),
        ("04_Left_Only_Files", TestCase.LEFT_ONLY, 5),
        ("05_Right_Only_Files", TestCase.RIGHT_ONLY, 5),
        ("06_Different_Sizes", TestCase.DIFFERENT_SIZE, 3),
        ("07_Empty_Folders", TestCase.EMPTY_FOLDER, 0),
        ("08_Special_Chars", TestCase.SPECIAL_CHARS, 5),  # Updated to match special_names list
        ("09_Large_Files", TestCase.LARGE_FILE, 2),
        ("10_Mixed_Scenarios", "mixed", 10),
        ("11_Performance_Tests", TestCase.PERFORMANCE_TEST, 0),  # Special handling
    ]
    
    # Create nested folder structure
    for depth in range(1, MAX_DEPTH + 1):
        folder_prefix = f"Level_{depth}"
        
        for scenario_name, test_case, file_count in test_scenarios:
            if depth > 1 and test_case == TestCase.EMPTY_FOLDER:
                continue  # Only create empty folders at level 1
            
            if depth > 1 and test_case == TestCase.PERFORMANCE_TEST:
                continue  # Only create performance tests at level 1
            
            left_folder = left_root / folder_prefix / scenario_name
            right_folder = right_root / folder_prefix / scenario_name
            
            # Create folders
            left_folder.mkdir(parents=True, exist_ok=True)
            
            if test_case != TestCase.LEFT_ONLY:
                right_folder.mkdir(parents=True, exist_ok=True)
            
            # Skip file creation for empty folders
            if test_case == TestCase.EMPTY_FOLDER:
                print(f"Created empty folders: {folder_prefix}/{scenario_name}")
                continue
            
            # Special handling for performance tests
            if test_case == TestCase.PERFORMANCE_TEST and depth == 1:
                create_performance_test_files(left_folder, right_folder)
                continue
            
            # Create files based on test case
            for i in range(file_count):
                create_test_files(left_folder, right_folder, test_case, i, depth)
            
            if depth == 1:  # Only print summary for first level to avoid spam
                if test_case == TestCase.SAME_CONTENT_DIFF_TIME:
                    print(f"Created {scenario_name}: Testing all timestamp combinations")
                elif test_case != "mixed" and test_case != TestCase.PERFORMANCE_TEST:
                    print(f"Created {scenario_name}: {file_count} test files")
    
    # Create some special edge cases at root level
    create_edge_cases(left_root, right_root)
    
    # Create summary file with SHA512 timing report
    create_summary_file(root)
    
    print("\nTest kit generation complete!")
    print(f"Total size: {get_folder_size(root) / (1024*1024):.2f} MB")
    
    # Print SHA512 timing summary
    print_sha512_timing_summary()
    
    print(f"\nYou can now test FolderCompareSync with:")
    print(f"  Left:  {left_root.absolute()}")
    print(f"  Right: {right_root.absolute()}")

def create_performance_test_files(left_folder: Path, right_folder: Path):
    """Create specific sized files for performance testing."""
    print("\nCreating performance test files...")
    base_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
    
    # MB-sized files - create in both trees
    mb_sizes = ["1MB", "2MB", "10MB", "100MB", "500MB"]
    for size_label in mb_sizes:
        size = PERFORMANCE_SIZES[size_label]
        print(f"  Creating {size_label} file in both trees...", end='', flush=True)
        
        filename = f"perf_test_{size_label}.bin"
        content = generate_random_content(size)
        
        # Same content in both trees but slightly different timestamps
        create_file_with_content(
            left_folder / filename, 
            content,
            base_time,
            base_time
        )
        create_file_with_content(
            right_folder / filename,
            content,
            base_time + datetime.timedelta(hours=1),
            base_time + datetime.timedelta(hours=1)
        )
        print(" Done")
    
    # GB-sized files - distribute between trees
    gb_sizes = ["1GB", "2GB", "5GB", "10GB", "15GB"]
    gb_distribution = [
        ("1GB", "left"),
        ("2GB", "right"),
        ("5GB", "left"),
        ("10GB", "right"),
        ("15GB", "left"),
    ]
    
    for size_label, location in gb_distribution:
        size = PERFORMANCE_SIZES[size_label]
        print(f"  Creating {size_label} file in {location} tree...", end='', flush=True)
        
        filename = f"perf_test_{size_label}.bin"
        content = generate_random_content(size)
        
        target_folder = left_folder if location == "left" else right_folder
        create_file_with_content(
            target_folder / filename,
            content,
            base_time,
            base_time
        )
        print(" Done")

def create_test_files(left_folder: Path, right_folder: Path, test_case: str, index: int, depth: int):
    """Create test files based on the test case type."""
    base_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
    time_offset = datetime.timedelta(days=index, hours=depth)
    
    if test_case == TestCase.IDENTICAL:
        # Identical files - same content, same timestamps
        filename = f"identical_{index:02d}.txt"
        content = generate_random_content(SMALL_FILE_SIZE + index * 100)  # Randomized content
        timestamp = base_time + time_offset
        
        create_file_with_content(left_folder / filename, content, timestamp, timestamp)
        create_file_with_content(right_folder / filename, content, timestamp, timestamp)
        
    elif test_case == TestCase.SAME_CONTENT_DIFF_TIME:
        # Same content but different timestamps - test all combinations
        content = generate_random_content(MEDIUM_FILE_SIZE)  # Randomized content
        
        # Define timestamp combinations to test
        # These test different comparison scenarios when content is identical
        timestamp_scenarios = [
            # (name_suffix, left_created_offset, left_modified_offset, right_created_offset, right_modified_offset)
            ("both_diff", 0, 0, 30, 30),  # Both timestamps different - most common sync scenario
            ("created_diff", 0, 0, 30, 0),  # Only creation different - tests creation time comparison
            ("modified_diff", 0, 0, 0, 30),  # Only modification different - tests modification time comparison
            ("created_newer_left", 30, 0, 0, 0),  # Left newer creation, right newer modification - conflict scenario
            ("modified_newer_left", 0, 30, 0, 0),  # Left newer modification, right newer creation - inverse conflict
        ]
        
        if index < len(timestamp_scenarios):
            suffix, lc_days, lm_days, rc_days, rm_days = timestamp_scenarios[index]
            filename = f"same_content_{suffix}_{index:02d}.txt"
            
            left_created = base_time + time_offset + datetime.timedelta(days=lc_days)
            left_modified = base_time + time_offset + datetime.timedelta(days=lm_days)
            right_created = base_time + time_offset + datetime.timedelta(days=rc_days)
            right_modified = base_time + time_offset + datetime.timedelta(days=rm_days)
            
            create_file_with_content(left_folder / filename, content, left_created, left_modified)
            create_file_with_content(right_folder / filename, content, right_created, right_modified)
        
    elif test_case == TestCase.DIFFERENT_CONTENT:
        # Different content
        filename = f"different_{index:02d}.txt"
        left_content = generate_random_content(SMALL_FILE_SIZE + index * 200)
        right_content = generate_random_content(SMALL_FILE_SIZE + index * 200)
        
        timestamp = base_time + time_offset
        create_file_with_content(left_folder / filename, left_content, timestamp, timestamp)
        create_file_with_content(right_folder / filename, right_content, timestamp, timestamp)
        
    elif test_case == TestCase.LEFT_ONLY:
        # Files only on left side
        filename = f"left_only_{index:02d}.dat"
        content = generate_random_content(SMALL_FILE_SIZE + index * 500)
        timestamp = base_time + time_offset
        create_file_with_content(left_folder / filename, content, timestamp, timestamp)
        
    elif test_case == TestCase.RIGHT_ONLY:
        # Files only on right side
        filename = f"right_only_{index:02d}.dat"
        content = generate_random_content(SMALL_FILE_SIZE + index * 500)
        timestamp = base_time + time_offset
        create_file_with_content(right_folder / filename, content, timestamp, timestamp)
        
    elif test_case == TestCase.DIFFERENT_SIZE:
        # Different file sizes
        filename = f"diff_size_{index:02d}.bin"
        left_size = SMALL_FILE_SIZE * (index + 1)
        right_size = MEDIUM_FILE_SIZE * (index + 1)
        
        timestamp = base_time + time_offset
        create_file_with_content(left_folder / filename, generate_random_content(left_size), timestamp, timestamp)
        create_file_with_content(right_folder / filename, generate_random_content(right_size), timestamp, timestamp)
        
    elif test_case == TestCase.SPECIAL_CHARS:
        # Special characters in filenames
        special_names = [
            "file with spaces.txt",
            "file_with_#hash.txt",
            "file.with.multiple.dots.txt",
            "file_with_[brackets].txt",
            "file_with_(parens).txt",
        ]
        if index < len(special_names):
            filename = special_names[index]
            content = generate_random_content(SMALL_FILE_SIZE)
            timestamp = base_time + time_offset
            create_file_with_content(left_folder / filename, content, timestamp, timestamp)
            create_file_with_content(right_folder / filename, content, timestamp, timestamp)
            
    elif test_case == TestCase.LARGE_FILE:
        # Large files to trigger staged copy
        filename = f"large_file_{index:02d}.bin"
        content = generate_random_content(LARGE_FILE_SIZE)
        timestamp = base_time + time_offset
        
        if index == 0:
            # First large file exists on both sides with same content
            create_file_with_content(left_folder / filename, content, timestamp, timestamp)
            create_file_with_content(right_folder / filename, content, timestamp, timestamp)
        else:
            # Second large file only on left
            create_file_with_content(left_folder / filename, content, timestamp, timestamp)
            
    elif test_case == "mixed":
        # Mixed scenarios for realistic testing
        scenarios = [
            (TestCase.IDENTICAL, "mixed_identical"),
            (TestCase.DIFFERENT_CONTENT, "mixed_different"),
            (TestCase.LEFT_ONLY, "mixed_left_only"),
            (TestCase.RIGHT_ONLY, "mixed_right_only"),
            (TestCase.SAME_CONTENT_DIFF_TIME, "mixed_same_diff_time"),
        ]
        
        scenario_type, prefix = scenarios[index % len(scenarios)]
        filename = f"{prefix}_{index:02d}.txt"
        
        if scenario_type == TestCase.LEFT_ONLY:
            content = generate_random_content(SMALL_FILE_SIZE * 2)
            timestamp = base_time + time_offset
            create_file_with_content(left_folder / filename, content, timestamp, timestamp)
        elif scenario_type == TestCase.RIGHT_ONLY:
            content = generate_random_content(SMALL_FILE_SIZE * 2)
            timestamp = base_time + time_offset
            create_file_with_content(right_folder / filename, content, timestamp, timestamp)
        else:
            # Handle other mixed scenarios
            create_test_files(left_folder, right_folder, scenario_type, index, depth)

def create_edge_cases(left_root: Path, right_root: Path):
    """Create additional edge case scenarios."""
    print("\nCreating edge cases...")
    
    # Very deep nesting
    deep_path = "Deep/Nested/Folder/Structure/Level5/Level6/Level7"
    (left_root / deep_path).mkdir(parents=True, exist_ok=True)
    (right_root / deep_path).mkdir(parents=True, exist_ok=True)
    
    # Hidden files (Windows)
    hidden_file = left_root / "hidden_test.txt"
    hidden_file.write_bytes(generate_random_content(1024))
    ctypes.windll.kernel32.SetFileAttributesW(str(hidden_file), 0x02)  # FILE_ATTRIBUTE_HIDDEN
    
    # Read-only files
    readonly_file = left_root / "readonly_test.txt"
    readonly_file.write_bytes(generate_random_content(2048))
    readonly_file.chmod(0o444)  # Read-only
    
    # File with no extension
    no_ext_file = left_root / "file_without_extension"
    no_ext_file.write_bytes(generate_random_content(1500))
    
    # Very long filename (near Windows limit)
    long_name = "very_long_filename_" + "x" * 200 + ".txt"
    (left_root / long_name).write_bytes(generate_random_content(512))
    
    # Unicode characters in filename (if supported)
    try:
        unicode_file = left_root / "файл_测试_🚀.txt"
        unicode_file.write_bytes(generate_random_content(1024))
    except:
        pass  # Skip if unicode filenames not supported
    
    # Zero-byte file
    (left_root / "zero_byte.txt").touch()
    (right_root / "zero_byte.txt").touch()
    
    # Files with same name but different case (for case-sensitive systems)
    (left_root / "CaseTest.txt").write_bytes(generate_random_content(1024))
    (left_root / "casetest.txt").write_bytes(generate_random_content(1024))
    
    # Timestamp edge cases
    print("Creating timestamp edge cases...")
    base_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
    
    # File with modification time older than creation time
    weird_time_file = left_root / "EdgeCases" / "weird_timestamps.txt"
    weird_time_file.parent.mkdir(exist_ok=True)
    weird_time_file.write_bytes(generate_random_content(2048))
    create_file_with_content(
        weird_time_file,
        generate_random_content(2048),
        creation_time=base_time + datetime.timedelta(days=30),
        modified_time=base_time  # Modified is older than created!
    )
    
    # Files with identical content but complex timestamp differences
    complex_time_left = left_root / "EdgeCases" / "complex_time.dat"
    complex_time_right = right_root / "EdgeCases" / "complex_time.dat"
    complex_time_right.parent.mkdir(parents=True, exist_ok=True)
    
    identical_content = generate_random_content(10240)  # 10KB
    
    # Left: Created Jan 1, Modified Feb 1
    # Right: Created Feb 1, Modified Jan 1 (inverse of left)
    create_file_with_content(
        complex_time_left,
        identical_content,
        creation_time=base_time,
        modified_time=base_time + datetime.timedelta(days=31)
    )
    create_file_with_content(
        complex_time_right,
        identical_content,
        creation_time=base_time + datetime.timedelta(days=31),
        modified_time=base_time
    )
    
    # Files with microsecond timestamp differences (to test precision)
    micro_left = left_root / "EdgeCases" / "microsecond_diff.txt"
    micro_right = right_root / "EdgeCases" / "microsecond_diff.txt"
    
    micro_content = generate_random_content(4096)
    micro_time = datetime.datetime(2024, 6, 15, 14, 30, 45, 123456)
    
    create_file_with_content(
        micro_left,
        micro_content,
        creation_time=micro_time,
        modified_time=micro_time
    )
    create_file_with_content(
        micro_right,
        micro_content,
        creation_time=micro_time + datetime.timedelta(microseconds=1000),  # 1ms difference
        modified_time=micro_time + datetime.timedelta(microseconds=1000)
    )

def create_summary_file(root: Path):
    """Create a summary file explaining the test structure."""
    summary = """FolderCompareSync Test Kit Summary
=====================================

This test kit contains various scenarios for testing folder synchronization:

1. Identical Files (01_Identical_Files/)
   - Files with same content and timestamps on both sides
   - Tests: Basic synchronization detection

2. Same Content, Different Times (02_Same_Content_Diff_Times/)
   - Files with identical content but different timestamp combinations:
     * Both creation and modification times different
     * Only creation time different, modification same
     * Only modification time different, creation same
     * Left has newer creation time, right has newer modification
     * Left has newer modification time, right has newer creation
   - Tests: Timestamp-based comparison logic

3. Different Content (03_Different_Content/)
   - Files with same names but different content
   - Tests: Content comparison and conflict detection

4. Left Only Files (04_Left_Only_Files/)
   - Files existing only in the left/source folder
   - Tests: Copy from left to right functionality

5. Right Only Files (05_Right_Only_Files/)
   - Files existing only in the right/target folder
   - Tests: Copy from right to left functionality

6. Different Sizes (06_Different_Sizes/)
   - Files with same names but different sizes
   - Tests: Size-based comparison

7. Empty Folders (07_Empty_Folders/)
   - Empty directory structures
   - Tests: Empty folder handling

8. Special Characters (08_Special_Chars/)
   - Files with spaces, symbols, and special characters
   - Tests: Filename compatibility

9. Large Files (09_Large_Files/)
   - Files over 10MB to trigger staged copy strategy
   - Tests: Copy strategy selection and performance

10. Mixed Scenarios (10_Mixed_Scenarios/)
    - Combination of various test cases
    - Tests: Real-world synchronization scenarios

11. Performance Tests (11_Performance_Tests/)
    - Specific file sizes for performance testing:
      * MB sizes (both trees): 1MB, 2MB, 10MB, 100MB, 500MB
      * GB sizes (distributed): 1GB (left), 2GB (right), 5GB (left), 10GB (right), 15GB (left)
    - Tests: Copy performance, SHA512 calculation speed, strategy selection

Edge Cases (in root folders):
- Very deep folder nesting
- Hidden files (Windows)
- Read-only files
- Files without extensions
- Very long filenames
- Zero-byte files
- Unicode filenames (if supported)

Timestamp Edge Cases (in EdgeCases folder):
- Files where modification time is older than creation time
- Files with inverted timestamp relationships between left/right
- Files with microsecond-level timestamp differences
- Complex timestamp scenarios for testing comparison logic

Test Recommendations:
1. First, run comparison without SHA512 for speed
2. Test individual scenarios before mixed scenarios
3. Test dry run mode before actual copying
4. Monitor copy strategy selection for large files
5. Verify timestamp preservation after copying
6. Test both "Date Created" and "Date Modified" comparison options
7. Try different combinations of comparison criteria

Note: 
- All files contain randomized binary content
- SHA512 hashes were calculated for all files during generation
- Performance timing data is included at the end of this file

Generated: {}

SHA512 TIMING REPORT
===================
{}
""".format(
    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    get_sha512_timing_report()
)
    
    (root / "TEST_KIT_README.txt").write_text(summary)

def get_sha512_timing_report() -> str:
    """Generate SHA512 timing report."""
    if not sha512_timings:
        return "No SHA512 timing data collected."
    
    report = []
    report.append("Average SHA512 calculation times by file size:")
    report.append("-" * 50)
    
    # Sort by file size for better readability
    size_order = ["0B", "512B", "1KB", "2KB", "4KB", "10KB", "100KB", 
                  "1MB", "2MB", "10MB", "15MB", "100MB", "500MB",
                  "1GB", "2GB", "5GB", "10GB", "15GB"]
    
    for size_label in size_order:
        if size_label in sha512_timings:
            times = sha512_timings[size_label]
            avg_time = sum(times) / len(times)
            report.append(f"{size_label:>8}: {avg_time:>10.4f} seconds (from {len(times)} files)")
    
    return "\n".join(report)

def print_sha512_timing_summary():
    """Print SHA512 timing summary to console."""
    print("\n" + "=" * 60)
    print("SHA512 TIMING SUMMARY")
    print("=" * 60)
    print(get_sha512_timing_report())
    print("=" * 60)

def get_folder_size(path: Path) -> int:
    """Calculate total size of a folder."""
    total = 0
    for item in path.rglob('*'):
        if item.is_file():
            total += item.stat().st_size
    return total

if __name__ == "__main__":
    try:
        generate_test_structure()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
