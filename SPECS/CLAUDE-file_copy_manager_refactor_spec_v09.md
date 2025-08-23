# FileCopyManager Refactor — Technical Specification v02

## 1. Executive Summary

**Primary Objective:** Replace the existing `FileCopyManager_class` with an enhanced implementation that provides robust, high-performance file copying with comprehensive verification, rollback capabilities, and Windows-optimized strategies for Python 3.13+ on Windows 10+.

**Critical Design Goals:**
- **Performance optimization:** Intelligent copy/verify strategy selection based on file size and location characteristics
- **Data integrity:** Zero tolerance for corrupted files through comprehensive verification and rollback
- **Operational safety:** Guaranteed rollback mechanisms with atomic operations
- **Developer/Maintainer clarity:** Extensive documentation in terms of well-commented code for classes, functions, and code blocks
- **Drop-in compatibility:** Maintain existing API surfaces where possible (some change may be required) for relatively seamless integration with other modules

## 2. Technical Change Goals

**G.1: Safe Copying with Notification and Status Returns**
- All copy operations must return detailed status information including error codes, messages, and recovery suggestions
- User cancellation support with graceful cleanup and rollback
- Comprehensive error classification (network, permission, space, corruption, etc.)

**G.2: Complete Date-Time Metadata Preservation**
- Preserve Windows file timestamps (Created/Modified) with full precision
- Support for setting/resetting timestamps post-operation for identical files and rollback restoration as appropriate
- Timestamp validation and verification capabilities

**G.3: Efficient (Fast) Copying, Verifying, and Hash Calculation**
- Native Windows API utilization (`CopyFileExW`, memory-mapped I/O) for maximum throughput for specified file categories with callabacks for progress display
- Intelligent chunking strategies optimized for different storage types (SSD/HDD/Network) and specified file categories
- Minimized redundant I/O operations through progressive BLAKE3 hashing during copying and verification for specified file categories

**G.4: Progress Updates via Tkinter**
- Tkinter-integrated progress calls and/or callbacks with configurable update frequencies
- Granular progress reporting at chunk/window level for responsive cancellation, deigned to cater for configurable update frequencies
- Multi-level progress (per-file and overall operation progress)

**G.5: Very Efficient (Fast) Verification with Rollback Mechanism**
- Multiple verification modes: none, all files, size-threshold based
- Content verification using BLAKE3 hashing with fallback to byte comparison
- Verification false-positive rate of zero through robust implementation
- Immediate rollback mechanism when verification detects problems

**G.6: Well Named Global Parameters for Control**
- Well-named global constants for all thresholds, chunk sizes, and operational parameters, each commencing with a common identifier to clarify which function it is mainly associated with
- Runtime configurability for different deployment scenarios
- Performance tuning capabilities through parameter adjustment

**G.7: Safety of Target Files with Guaranteed Rollback**
- Guaranteed preservation of original target files during all copy operations incorporating a robust restore approach
- Secure temporary files approach minimises corruption risk during copy/restore phase
- Atomic rename operations for final file placement
- Simple, reliable rollback: delete temporary files only (original never touched)
- Existing overwrite functionality must be deprecated and removed

**G.8: Drop-in Compatible Replacement FileCopyManager_class**
- Existing method signatures maintained where practicable: `copy_file(src, dst, overwrite=True)` may have `overwrite=True` removed
- Return object compatibility with current `CopyOperationResult` structure
- Preserved integration patterns with UI progress systems

**G.9: Well Commented Code at Function and Code Block Level**
- Function-level docstrings with purpose, arguments, returns, and usage examples
- Code block comments for complex algorithms and Windows API interactions
- Developer guidance for maintenance and extension

**G.10: Best Practice Coding for Speed-Essential Operations**
- Optimized tight loops for copying, verification, and hashing operations to ensure that best possible speed is the goal in these code blocks
- Commented-out debug statements in performance-critical sections
- Best practice implementations for I/O efficiency since I/O is very likely to be the primary performance limiting factor

## 3. Mandatory Requirements

**M01:** Must support **two copy strategies**: Direct and Staged

**M02:** **Direct Copy** is fast, kernel-assisted, and optimized for local transfers, aimed at local non-networked files < specified gigabytes (global constant)

**M03:** **Staged Copy** is chunked, hash-driven, and optimized for networked files or where any file to be copied is >= specified gigabytes (global constant)

**M04:** Must provide **robust verification** options: verify none, verify only files < specified gigabytes, verify all (global constant)

**M05:** Must guarantee **rollback safety**: original target files are never corrupted during copy operations

**M06:** Must integrate with **Tkinter progress reporting**

**M07:** Must preserve metadata (timestamps, attributes)

**M08:** Must use **configurable constants** for thresholds and chunk/window sizes etc.

**M09:** Must be fully commented and maintainable

**M10:** Rollback ensures that **only verified files appear in the destination** with zero risk of data loss

**M11:** Tkinter provides near real-time **progress feedback** at both per-file and overall levels

**M12:** Any existing "overwrite" function is to be removed as deprecated, files will be copied and verified and all files will have capability to be rolled back

**M13:** Abstract global constants (including Windows-related constants) into the global constants module which exposes them as "C." via "import xxx as C"

**M14:** Abstract imports into global imports module which has code to expose them

## 4. User Interface Requirements

### 4.1 Verification Mode Radio Buttons

**Mandatory UI Component (M04):** Pre-copy UI must have 3 mutually exclusive radio buttons for verification policy selection:

1. **"Verify no files"** - Skip all verification (fastest, use with caution)
2. **"Verify only files < [threshold] after each copy"** - Verify only files under specified size threshold (configurable via global constant, initially 2GB) (**default selection**)
3. **"Verify every file after each copy"** - Verify all copied files regardless of size (very slow for large files)

### 4.2 UI Implementation Requirements

**Technical Integration:**
- Radio button selection controls the `FILECOPY_VERIFY_POLICY` global constant
- Default selection must be "Verify only files < x.x GB after each copy (balanced)" for balanced safety
- Threshold value in option 3 should be dynamically populated from `FILECOPY_VERIFY_THRESHOLD_BYTES`
- Radio button state must be preserved across UI sessions
- Clear labeling to help users understand performance vs safety trade-offs

**Display Format Example:**
```
Verification Options:
○ Verify no files (fastest)
● Verify only files < 2.0 GB after each copy (balanced)
○ Verify every file after each copy (very slow with large files; maximum safety) 
```
noting that
- the `2 GB` value in the example derives from a global constant
- the radio button which is on by default derives from a global constant

### 4.3 UI Integration Points

**Progress Reporting Integration (M06, M11):**
- Near Real-time progress updates during copy operations
- Separate progress indicators for copy phase and verification phase in the status messages area 
- Cancel button must be responsive and aim for within 500ms (possibly configurable, refer to global constant(s)) during all operations
- Status messages must indicate which strategy (DIRECT/STAGED) is being used

## 5. Copy Strategy Implementation Details

### 5.1 Strategy Selection Matrix

| File Location |   File Size   | Strategy Applied |
|---------------|-----------|------------------|
| Local drives, < 2GB     | Small | DIRECT |
| Local drives, >= 2GB     | Large | STAGED |
| Any Network drives, any size     | Any | STAGED |

**Implementation Note:** Strategy selection occurs in `determine_copy_strategy()` method using `GetDriveType` Windows API calls for accurate drive type detection.

### 5.2 DIRECT Strategy Specifications (M01, M02)

**When Used:**
- File size < 2GB AND no network drive letters involved
- Both source and target are on local drives (SSD/HDD on same machine)

**Technical Method - Detailed Implementation:**

**1. Copy Phase: Windows CopyFileExW API Implementation**
- Uses Windows native `CopyFileExW` API via ctypes for maximum performance
- Provides kernel-level, buffered operations optimized for local drive-to-drive transfers
- Preserves all file metadata automatically during copy operation
- Accepts callback function that Windows calls periodically with detailed progress information:
  - Total file size in bytes
  - Bytes copied so far
  - Current transfer rate
  - Copy pause/cancel status
- Callback enables near real-time progress bar updates in Tkinter UI
- Copy operation targets secure temporary file in target directory
- Rationale: For local SSD/HDD copies, CopyFileExW provides optimal performance through OS-level optimization

**2. Verification Phase: Windowed Memory-Mapped Comparison**
- **Window Size:** Configurable 8-64 MiB windows (default 64 MiB via `FILECOPY_MMAP_WINDOW_BYTES`)
- **Memory Efficiency:** Uses OS-paged reads (4KB pages) without loading entire files into memory
- **Process Flow:**
  1. Open both source and temporary files with read-only memory mapping
  2. Compare files in fixed-size windows sequentially from start to end
  3. Each window comparison uses direct memory comparison for maximum speed
  4. **Early Failure Detection:** Stop immediately on first window mismatch
  5. Update progress bar after each window comparison (responsive cancellation)
- **Fallback Mechanism:** If mmap fails on any window (exotic filesystems, access issues):
  1. Automatically fall back to buffered file read/compare for that specific window
  2. Continue with mmap for subsequent windows
  3. Log fallback occurrence for debugging
- **Performance Benefits:**
  - Faster than reading entire files into Python buffers for large files
  - Avoids memory thrashing on memory-constrained systems
  - Enables responsive cancellation every 64MB (approximately 500ms on typical HDDs)
- **Hash Provision:** Structure includes commented placeholders for future BLAKE3 hash implementation matching STAGED strategy approach

**3. Progress Reporting:**
- Copy phase: Near Real-time callbacks from Windows API (sub-second updates)
- Verification phase: Progress updates after each 64MB window comparison
- Responsive cancellation within 500ms during both phases

### 5.3 STAGED Strategy Specifications (M01, M03)

**When Used:**
- File size >= 2GB OR any network drive letters involved
- Optimized for networked files and large file handling

**Technical Method - Detailed Implementation:**

**1. Copy Phase: Chunked I/O with Progressive Hash Calculation**
- **Chunk Size:** Network-optimized 4MB chunks (via `FILECOPY_NETWORK_CHUNK_BYTES`)
- **Rationale for Non-CopyFileExW Approach:** While Windows CopyFileExW could handle network copies, it requires additional costly full-file reads for verification:
  - Traditional approach: [1. read source, 2. write target, 3. re-read source for verify, 4. re-read target for verify, 5. compare hashes] = 4x file size network transfer
  - STAGED approach: [1. read source + calculate hash during copy, 2. write target, 3. re-read target for verify, 4. compare hashes] = 3x file size network transfer
- **Progressive Hash Calculation:**
  - Primary: BLAKE3 hashing (significantly faster than SHA-512 on modern CPUs)
  - Fallback: SHA-256 if BLAKE3 unavailable
  - Hash calculated incrementally during each 4MB chunk read from source
  - Single-pass source reading eliminates redundant network I/O
- **Process Flow:**
  1. Open source file for reading, temporary target file for writing
  2. Initialize BLAKE3 hasher
  3. Read 4MB chunks from source sequentially
  4. Update hash with each chunk immediately after read
  5. Write chunk to temporary target file
  6. Update progress bar after each chunk (responsive cancellation every ~320ms on 100Mbps networks)
  7. Finalize source hash after complete file processing
- **Network Optimization:** 4MB chunks balance network efficiency with cancellation responsiveness

**2. Verification Phase: Chunked Hash Calculation of Target**
- **Chunk Size:** 1-8MB chunks for target verification (via configurable constant, default 4MB)
- **Method Rationale:** Buffered chunked I/O preferred over mmap for network files to avoid pathological page-fault latency over network stack
- **Process Flow:**
  1. Open temporary target file for reading
  2. Initialize matching hasher (BLAKE3 or SHA-256 to match source)
  3. Read chunks sequentially from temporary target
  4. Update hash with each chunk
  5. Update progress bar after each chunk
  6. Finalize target hash
  7. Compare source hash vs target hash for verification
- **Fallback Verification:** If hash comparison fails or hash calculation errors occur:
  1. Fall back to byte-by-byte comparison using same chunked approach
  2. Log hash failure for debugging
  3. Ensure verification still completes reliably

**3. Performance Benefits:**
- **Reduced Network Traffic:** 25% reduction in network I/O compared to traditional verify approaches
- **Memory Efficient:** Large files never fully materialized in memory
- **Responsive Cancellation:** User can cancel within 320ms on typical 100Mbps networks
- **Hash Speed:** BLAKE3 provides superior performance on modern multi-core CPUs

**4. Progress Reporting:**
- Copy phase: Progress updates every 4MB chunk processed (both read and hash calculation)
- Verification phase: Progress updates every 4MB of target hash calculation
- Dual progress indication: separate bars for copy phase and verify phase

## 6. Enhanced Rollback Process Description

### 6.1 Secure Temporary File Rollback Process

The enhanced rollback system uses a secure temporary file approach that completely eliminates the risk of target file corruption during copy operations. This process ensures that original target files are never modified until the entire copy and verification process is complete and successful.

**Process Overview:**

**Preparation Phase:**
- The system first captures and saves the source file timestamps for later application to the target
- If a target file already exists, the system captures and saves its original timestamps for potential rollback purposes
- The system checks if overwrite is permitted when a target file exists

**Secure Copy Phase:**
- A unique temporary filename is generated in the target directory using the pattern `{target_name}.tmp_{unique_id}`
- The source file is copied to this temporary location using either DIRECT or STAGED strategy
- During this entire phase, the original target file (if it exists) remains completely untouched and unmodified
- If verification is enabled, the temporary file is verified against the source
- Any failure during this phase simply requires deleting the temporary file - the original target remains intact

**Atomic Success Phase (only executed if copy and verification are successful):**
- If a target file exists, it is moved to a backup location using an atomic rename operation
- The verified temporary file is then renamed to the final target location using another atomic rename operation
- Source file timestamps are applied to the new target file
- The renamed original target file (backup) is deleted

**Automatic Rollback on Failure:**
- If any error occurs during the preparation or secure copy phases, only the temporary file needs to be deleted
- The original target file has never been modified and remains in its original state
- If an error occurs during the atomic success phase after the original has been moved to backup, the backup is restored using atomic rename
- In all failure scenarios, the user's original files are preserved

**Key Safety Benefits:**
- **Zero corruption window:** Original target files are never modified during the risky copy/verification phase
- **Simple rollback:** Most failures only require deleting a temporary file
- **Atomic final operations:** File placement uses instantaneous rename operations
- **Guaranteed data preservation:** Original files cannot be lost or corrupted during copy operations

This approach is significantly safer than traditional copy methods that overwrite the target file directly, as it eliminates the window of vulnerability where a target file could be left in a corrupted or incomplete state.

## 7. Enhanced Global Constants Configuration - Detailed Technical Rationale

```python
# Copy Strategy Control (M01, M02, M03, M13)
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3      # 2 GiB - DIRECT vs STAGED
# Rationale: 2GB threshold balances local optimization vs network efficiency
# - Files < 2GB: Local CopyFileExW + mmap verification optimal
# - Files >= 2GB: Chunked approach reduces memory pressure and enables better progress reporting

FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3     # 20 GiB - Hard size limit
# Rationale: Prevents runaway operations on extremely large files
# - Protects against accidental VM disk images, database files
# - Can be increased for specialized use cases

# Performance Tuning - DIRECT Strategy (M08)
FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2                # 64 MiB - Verification windows
# Rationale: Optimal balance for memory-mapped verification
# - Memory usage: Conservative for 4GB+ systems (1.6% of 4GB RAM)
# - I/O efficiency: Reduces system calls while maintaining responsiveness
# - Cancellation latency: ~400ms on 150MB/s HDDs, ~130ms on 500MB/s SSDs
# - Memory constraint handling: Auto-reduces to 32MB on systems with <2GB RAM
# Alternative values: 32MB (memory-constrained), 128MB (high-performance systems)

# Performance Tuning - STAGED Strategy (M08)
FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2               # 4 MiB - Network I/O chunks
# Rationale: Network-optimized chunk size for SMB/NAS scenarios
# - Network efficiency: Balances throughput vs latency on 100Mbps+ networks
# - Cancellation responsiveness: ~320ms on 100Mbps, ~80ms on 400Mbps networks
# - SMB optimization: Aligns with typical SMB protocol buffer sizes
# - Hash calculation: Optimal granularity for BLAKE3 progressive hashing
# - Memory usage: Low memory footprint (4MB active buffer)
# Alternative values: 1MB (slower networks), 8MB (gigabit+ networks)

# Verification Configuration (M04)
FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3            # 2 GiB - Verify size limit
# Rationale: "Balanced" verification mode threshold
# - Matches copy strategy threshold for consistency
# - Covers majority of user files (documents, images, videos)
# - Large files (ISOs, backups) can skip verification for performance
# - User-configurable based on specific use case requirements

FILECOPY_VERIFY_POLICY = 'lt_threshold' # none | lt_threshold | all (default: lt_threshold)
# Rationale: balanced safety as default setting
# - 'none': Skip all verification (use with caution, fastest performance)
# - 'lt_threshold': Verify only files under FILECOPY_VERIFY_THRESHOLD_BYTES (balanced; default)
# - 'all': Verify every file regardless of size (very slow for large files)

# System Resource Management
FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2           # 64 MiB - Safety margin
# Rationale: Prevents disk full scenarios during copy operations
# - Accounts for filesystem overhead and metadata
# - Provides buffer for concurrent system operations
# - Windows: Allows for NTFS journal and system file growth

FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True            # Warn on sparse files
# Rationale: User notification for potential storage impact
# - Sparse files expand to full size when copied to non-sparse target
# - Critical for VM disk images, database files with sparse allocation
# - Prevents unexpected disk space consumption

# Error Handling and Recovery
FILECOPY_BLAKE3_FALLBACK_ENABLED = True                  # Enable byte comparison fallback
# Rationale: Guaranteed verification even if hashing fails
# - BLAKE3 library may be missing on some systems
# - Hash calculation can fail due to memory pressure or file corruption
# - Byte comparison provides definitive verification result
# - Performance cost acceptable for reliability

FILECOPY_UNC_PATH_REJECTION_STRICT = True               # Reject UNC paths
# Rationale: Prevent unsupported network path operations
# - UNC paths (\\server\share) often have permission complexities
# - Drive mapping provides better Windows integration
# - Clearer error handling and user guidance

FILECOPY_LONG_PATH_NORMALIZATION = True                 # Enable \\?\ prefix support
# Rationale: Windows long path support (>260 characters)
# - Automatic \\?\ prefix for paths exceeding MAX_PATH
# - Enables copying of deeply nested directory structures
# - Essential for modern development environments (node_modules, etc.)

# Windows API Constants (M13)
FILECOPY_COPY_FILE_RESTARTABLE = 0x00000002             # CopyFileExW flags
# Rationale: Enables resume capability for interrupted operations
# - Large file copies can be resumed if interrupted by system restart
# - Improves reliability for lengthy copy operations

FILECOPY_PROGRESS_CONTINUE = 0                           # Progress callback returns
FILECOPY_PROGRESS_CANCEL = 1                            # User cancellation
# Rationale: Windows API standard return codes for progress callbacks
# - Enables responsive user cancellation during CopyFileExW operations
# - Integrates with Windows progress reporting infrastructure

FILECOPY_ERROR_REQUEST_ABORTED = 1235                    # Windows error codes
# Rationale: Specific Windows error code for user-cancelled operations
# - Distinguishes user cancellation from system errors
# - Enables appropriate user feedback and error handling

FILECOPY_DRIVE_REMOTE = 4                                # Drive type constants
# Rationale: Windows GetDriveType return value for network drives
# - Enables automatic strategy selection based on drive type
# - Network drives automatically use STAGED strategy regardless of file size
```

**Constants Tuning Guidelines:**

**Memory-Constrained Systems (< 4GB RAM):**
- FILECOPY_MMAP_WINDOW_BYTES = 32 * 1024**2 (32MB)
- Reduces memory pressure while maintaining verification benefits

**High-Performance Systems (16GB+ RAM, SSD storage):**
- FILECOPY_MMAP_WINDOW_BYTES = 128 * 1024**2 (128MB)
- Maximizes I/O efficiency for large file operations

**Slow Network Environments (< 50Mbps):**
- FILECOPY_NETWORK_CHUNK_BYTES = 1 * 1024**2 (1MB)
- Reduces latency and improves cancellation responsiveness

**High-Speed Network Environments (Gigabit+):**
- FILECOPY_NETWORK_CHUNK_BYTES = 8 * 1024**2 (8MB)
- Maximizes network throughput for large file transfers

**Conservative Verification (Limited CPU):**
- FILECOPY_VERIFY_THRESHOLD_BYTES = 512 * 1024**2 (512MB)
- Reduces verification overhead for slower systems

**Performance-Oriented (Fast CPU, Time-Critical):**
- FILECOPY_VERIFY_POLICY = 'lt_threshold'
- FILECOPY_VERIFY_THRESHOLD_BYTES = 4 * 1024**3 (4GB)
- Balances integrity checking with copy speed

## 8. Detailed Copy Algorithm Specifications

### 8.1 DIRECT Strategy Implementation

**Algorithmic Flow:**
```python
def _execute_direct_strategy(src: str, dst: str, overwrite: bool,
                             progress_cb, cancel_event) -> CopyOperationResult:
    """
    DIRECT strategy implementation using Windows CopyFileExW API.
    Optimized for local drives with kernel-level performance and secure rollback.
    """
    
    # Phase 1: Preflight Validation and Timestamp Capture
    source_timestamps = None
    target_timestamps = None
    temp_file_path = None
    
    try:
        source_timestamps = timestamp_manager.get_file_timestamps(src)
    except Exception as e:
        return _create_error_result(f"Failed to read source timestamps: {e}")
    
    if Path(dst).exists():
        if not overwrite:
            return _create_error_result("Overwrite disabled, target exists")
        try:
            target_timestamps = timestamp_manager.get_file_timestamps(dst)
        except Exception as e:
            return _create_error_result(f"Failed to read target timestamps: {e}")
    
    # Phase 2: Preflight Space Check
    if not _check_sufficient_space(src, dst):
        return _create_error_result("Insufficient disk space")
    
    # Phase 3: Create secure temporary file path
    dst_dir = Path(dst).parent
    dst_name = Path(dst).name
    temp_file_path = str(dst_dir / f"{dst_name}.tmp_{uuid.uuid4().hex[:8]}")
    
    # Phase 4: Windows CopyFileExW Copy to Temporary File
    copy_result = _copy_with_windows_api(src, temp_file_path, progress_cb, cancel_event)
    if not copy_result.success:
        _cleanup_temp_file(temp_file_path)
        return copy_result
    
    # Phase 5: Verification (if enabled by radio button selection)
    if _should_verify_file(Path(src).stat().st_size):
        verify_result = _verify_by_mmap_windows(src, temp_file_path, progress_cb, cancel_event)
        if not verify_result:
            _cleanup_temp_file(temp_file_path)
            return _create_error_result("Content verification failed")
    
    # Phase 6: Atomic file placement sequence
    backup_path = None
    if Path(dst).exists():
        backup_path = f"{dst}.backup_{uuid.uuid4().hex[:8]}"
        os.rename(dst, backup_path)  # Atomic: original → backup
    
    os.rename(temp_file_path, dst)  # Atomic: temp → final location
    
    # Phase 7: Apply source timestamps
    timestamp_result = timestamp_manager.set_file_timestamps(dst, *source_timestamps)
    if not timestamp_result:
        _log_warning("Timestamp preservation failed after successful copy")
    
    # Phase 8: Success cleanup - delete the renamed original target
    if backup_path and Path(backup_path).exists():
        os.remove(backup_path)  # Delete renamed original target (M12)
    
    return _create_success_result(copy_result, "DIRECT")
```

**Windows API Integration - CopyFileExW Implementation:**
```python
def _copy_with_windows_api(src: str, dst: str, progress_cb, cancel_event) -> CopyResult:
    """
    Windows CopyFileExW implementation with progress callbacks and cancellation.
    
    Technical Details:
    - Uses kernel32.CopyFileExW for maximum performance
    - Progress callback receives TotalFileSize, BytesTransferred
    - Cancel detection through progress callback return values
    - Proper error code handling via GetLastError()
    """
    
    # Progress callback signature for CopyFileExW
    def copy_progress_callback(total_size, transferred, stream_size, 
                              stream_transferred, stream_num, reason,
                              src_handle, dst_handle, user_data):
        """
        Windows progress callback - called by OS during copy operation.
        
        Returns:
        - PROGRESS_CONTINUE (0): Continue copying
        - PROGRESS_CANCEL (1): Cancel operation
        - PROGRESS_STOP (2): Stop with error
        """
        
        # Check for user cancellation
        if cancel_event and cancel_event.is_set():
            return C.FILECOPY_PROGRESS_CANCEL
        
        # Update progress via Tkinter callback
        if progress_cb:
            progress_percentage = (transferred / total_size) * 100 if total_size > 0 else 0
            progress_cb(transferred, total_size, progress_percentage)
        
        return C.FILECOPY_PROGRESS_CONTINUE
    
    # Create callback wrapper for Windows
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
    
    callback_func = PROGRESS_ROUTINE(copy_progress_callback)
    
    # Execute Windows CopyFileExW
    result = kernel32.CopyFileExW(
        ctypes.c_wchar_p(src),
        ctypes.c_wchar_p(dst), 
        callback_func,
        None,                        # No user data
        None,                        # No cancel flag
        C.FILECOPY_COPY_FILE_RESTARTABLE  # Restartable if interrupted
    )
    
    if not result:
        error_code = kernel32.GetLastError()
        if error_code == C.FILECOPY_ERROR_REQUEST_ABORTED:
            return CopyResult(success=False, cancelled=True, error="User cancelled")
        else:
            error_msg = f"CopyFileExW failed with error {error_code}"
            return CopyResult(success=False, error=error_msg, error_code=error_code)
    
    return CopyResult(success=True, bytes_copied=Path(src).stat().st_size)
```

### 8.2 STAGED Strategy Implementation

**Algorithmic Flow:**
```python
def _execute_staged_strategy(src: str, dst: str, overwrite: bool,
                             progress_cb, cancel_event) -> CopyOperationResult:
    """
    STAGED strategy implementation using secure temporary file approach.
    Optimized for large files and network drives with guaranteed rollback safety.
    """
    
    # Phase 1: Preflight Validation and Timestamp Capture
    source_timestamps = None
    target_timestamps = None
    temp_file_path = None
    
    # Capture source timestamps for later application
    try:
        source_timestamps = timestamp_manager.get_file_timestamps(src)
    except Exception as e:
        return _create_error_result(f"Failed to read source timestamps: {e}")
    
    # Capture target timestamps for potential rollback (if target exists)
    if Path(dst).exists():
        if not overwrite:
            return _create_error_result("Target file exists and overwrite is disabled")
        try:
            target_timestamps = timestamp_manager.get_file_timestamps(dst)
        except Exception as e:
            return _create_error_result(f"Failed to read target timestamps: {e}")
    
    # Phase 2: Create unique temporary filename in target directory
    dst_dir = Path(dst).parent
    dst_name = Path(dst).name
    temp_file_path = str(dst_dir / f"{dst_name}.tmp_{uuid.uuid4().hex[:8]}")
    
    try:
        # Phase 3: Copy and verify to temporary file with progressive hashing
        copy_result = _copy_with_progressive_hash(src, temp_file_path, progress_cb, cancel_event)
        if not copy_result.success:
            # Rollback: Simply delete temporary file
            if Path(temp_file_path).exists():
                os.remove(temp_file_path)
            return copy_result
        
        source_hash = copy_result.computed_hash
        
        # Phase 4: Verify temporary file (if enabled by radio button selection)
        if _should_verify_file(Path(src).stat().st_size):
            temp_hash = _compute_target_hash(temp_file_path, progress_cb, cancel_event)
            if temp_hash != source_hash:
                # Rollback: Delete corrupted temporary file
                os.remove(temp_file_path)
                return _create_error_result("Hash verification failed")
        
        # Phase 5: Atomic success sequence (original target is never corrupted)
        backup_path = None
        if Path(dst).exists():
            # Move original target to backup location
            backup_path = f"{dst}.backup_{uuid.uuid4().hex[:8]}"
            os.rename(dst, backup_path)  # Atomic operation
        
        # Atomic rename of verified temporary file to final location
        os.rename(temp_file_path, dst)  # Atomic operation
        
        # Phase 6: Apply source timestamps to final target
        timestamp_result = timestamp_manager.set_file_timestamps(dst, *source_timestamps)
        if not timestamp_result:
            # Critical error after atomic operations - log warning but don't fail
            _log_warning("Timestamp preservation failed after successful copy")
        
        # Phase 7: Success cleanup - delete the renamed original target
        if backup_path and Path(backup_path).exists():
            os.remove(backup_path)  # Delete renamed original target (M12)
        
        return _create_success_result(copy_result, "STAGED")
        
    except Exception as e:
        # Comprehensive rollback for any failure during atomic sequence
        try:
            # Remove temporary file if it exists
            if temp_file_path and Path(temp_file_path).exists():
                os.remove(temp_file_path)
            
            # If we moved target to backup but failed after that, restore it
            if backup_path and Path(backup_path).exists() and not Path(dst).exists():
                os.rename(backup_path, dst)  # Restore original
                if target_timestamps:
                    timestamp_manager.set_file_timestamps(dst, *target_timestamps)
                    
        except Exception as rollback_error:
            return _create_error_result(f"Copy failed: {e}. Rollback also failed: {rollback_error}")
        
        return _create_error_result(f"Copy operation failed: {e}")
```

**Progressive Hash Copy Implementation:**
```python
def _copy_with_progressive_hash(src: str, dst: str, progress_cb, cancel_event) -> CopyResult:
    """
    Chunked copy with simultaneous source hash calculation.
    
    Benefits:
    - Single read pass through source file
    - Progressive hash calculation during copy
    - Reduced total I/O compared to copy-then-hash approach
    - Network-optimized chunk sizes
    """
    
    chunk_size = C.FILECOPY_NETWORK_CHUNK_BYTES
    total_size = Path(src).stat().st_size
    bytes_copied = 0
    
    # Initialize BLAKE3 hasher (with fallback)
    try:
        import blake3
        hasher = blake3.blake3()
        hash_algorithm = "BLAKE3"
    except ImportError:
        # Fallback to hashlib implementation
        import hashlib
        hasher = hashlib.sha256()  # Or sha512 based on preference
        hash_algorithm = "SHA256"
    
    try:
        with open(src, 'rb') as src_file, open(dst, 'wb') as dst_file:
            while bytes_copied < total_size:
                # Check cancellation
                if cancel_event and cancel_event.is_set():
                    return CopyResult(success=False, cancelled=True)
                
                # Read chunk from source
                remaining = total_size - bytes_copied
                current_chunk_size = min(chunk_size, remaining)
                chunk = src_file.read(current_chunk_size)
                
                if not chunk:  # EOF reached unexpectedly
                    break
                
                # Write to destination
                dst_file.write(chunk)
                
                # Update hash
                hasher.update(chunk)
                
                # Update progress
                bytes_copied += len(chunk)
                if progress_cb:
                    progress_percentage = (bytes_copied / total_size) * 100
                    progress_cb(bytes_copied, total_size, progress_percentage)
        
        # Finalize hash
        computed_hash = hasher.hexdigest()
        
        return CopyResult(
            success=True, 
            bytes_copied=bytes_copied,
            computed_hash=computed_hash,
            hash_algorithm=hash_algorithm
        )
        
    except Exception as e:
        return CopyResult(success=False, error=f"Copy operation failed: {e}")
```

## 9. Comprehensive Verification Algorithms - Detailed Technical Implementation

### 9.1 Memory-Mapped Window Verification (DIRECT Strategy) - Complete Technical Specification

**Purpose:** High-performance local file verification using OS-optimized memory mapping with intelligent fallback mechanisms.

**Technical Implementation Details:**

**9.1.1 Window Configuration and Sizing**
- **Default Window Size:** 64 MiB (configurable via `FILECOPY_MMAP_WINDOW_BYTES`)
- **Rationale:** 64MB provides optimal balance between:
  - Memory usage (conservative for older systems)
  - I/O efficiency (fewer system calls)
  - Cancellation responsiveness (~500ms latency on typical 150MB/s HDDs)
- **Adjustable Range:** 8MB minimum to 256MB maximum for different system configurations
- **Memory Constraint Handling:** Automatically reduce window size if system memory < 2GB available

**9.1.2 Detailed Process Flow**
```python
def _verify_by_mmap_windows(src: str, dst: str, progress_cb, cancel_event) -> bool:
    """
    Comprehensive memory-mapped window verification with fallback support.
    
    Technical Process:
    1. Validate file sizes match (quick pre-check)
    2. Handle empty files (immediate success)
    3. Open both files with read-only memory mapping
    4. Process files in sequential windows from start to end
    5. Compare each window using direct memory comparison
    6. Implement automatic fallback on mmap failures
    7. Provide responsive progress reporting and cancellation
    """
```

**9.1.3 Memory Mapping Advantages**
- **OS-Paged Reads:** Utilizes 4KB OS page reads without full file materialization
- **Memory Efficiency:** Large files never fully loaded into RAM (critical for memory-constrained systems)
- **Early Failure Detection:** Comparison stops immediately on first window mismatch
- **Cache Optimization:** OS handles memory caching automatically for optimal performance
- **Virtual Memory Benefits:** Leverages OS virtual memory management for large files

**9.1.4 Intelligent Fallback Mechanism**
```python
# Fallback triggers:
# - Exotic filesystem incompatibilities (network filesystems, encrypted volumes)
# - Memory mapping failures (insufficient virtual address space)
# - File locking conflicts (antivirus interference)
# - Permission issues (read-only files, access denied)

if mmap_fails_for_window:
    # Automatic fallback to buffered comparison for THIS window only
    success = _buffered_window_compare(src_file, dst_file, offset, window_size)
    # Continue with mmap for subsequent windows
    continue_with_mmap = True
```

**9.1.5 Progress Reporting and Cancellation**
- **Progress Updates:** After each 64MB window comparison
- **Cancellation Responsiveness:** Check cancel event before each window
- **Performance Metrics:** Track windows processed, bytes verified, elapsed time
- **Memory Usage:** Monitor and report memory mapping efficiency

**9.1.6 Error Handling and Recovery**
- **File Size Mismatches:** Immediate failure with detailed size information
- **Mapping Failures:** Automatic fallback with logging for debugging
- **Comparison Errors:** Detailed reporting of mismatch location and window
- **Resource Cleanup:** Guaranteed memory mapping cleanup on success or failure

### 9.2 Hash Verification with BLAKE3 (STAGED Strategy) - Complete Technical Specification

**Purpose:** Network-optimized hash-based verification using progressive calculation and chunked I/O for maximum efficiency.

**9.2.1 Hash Algorithm Selection and Performance**
- **Primary Algorithm:** BLAKE3
  - **Speed:** 3-5x faster than SHA-512 on modern multi-core CPUs
  - **Security:** Cryptographically secure with 256-bit output
  - **Parallelization:** Utilizes multiple CPU cores automatically
  - **Memory Efficiency:** Low memory footprint during computation
- **Fallback Algorithm:** SHA-256 (if BLAKE3 unavailable)
  - **Compatibility:** Available in Python standard library
  - **Reliability:** Well-tested, widely supported
  - **Performance:** Adequate for network-limited scenarios

**9.2.2 Progressive Hash Calculation During Copy**
```python
def _copy_with_progressive_hash(src: str, temp_dst: str, progress_cb, cancel_event):
    """
    Single-pass copy with simultaneous hash calculation.
    
    Network Efficiency Benefits:
    - Eliminates redundant source file reads over network
    - Reduces total network I/O from 4x to 3x file size
    - Calculates source hash during mandatory copy operation
    - No additional network latency for source verification
    """
    
    chunk_size = C.FILECOPY_NETWORK_CHUNK_BYTES  # 4MB default
    hasher = blake3.blake3()  # or hashlib.sha256() fallback
    
    while copying:
        chunk = src_file.read(chunk_size)
        hasher.update(chunk)  # Progressive hash calculation
        temp_dst_file.write(chunk)
        # Progress update every 4MB (~320ms on 100Mbps networks)
```

**9.2.3 Target Hash Calculation with Chunked I/O**
- **Chunk Size:** 4MB chunks (matching copy phase for consistency)
- **Method Rationale:** Buffered I/O preferred over mmap for network files
  - **Network Optimization:** Avoids pathological page-fault latency over network stack
  - **SMB/NAS Compatibility:** Better performance with network filesystem protocols
  - **Memory Predictability:** Consistent memory usage regardless of file size
- **Process Flow:**
  1. Open temporary target file for sequential reading
  2. Initialize hasher matching copy phase algorithm
  3. Read and hash in 4MB chunks with progress reporting
  4. Compare final hash against source hash from copy phase

**9.2.4 Hash Comparison and Verification**
```python
def _verify_hash_comparison(source_hash: str, target_hash: str, algorithm: str) -> bool:
    """
    Secure hash comparison with timing attack protection.
    
    Verification Process:
    1. Compare hash lengths (basic validation)
    2. Perform constant-time comparison (security best practice)
    3. Log verification results with algorithm and hash details
    4. Return boolean success/failure result
    """
    
    if len(source_hash) != len(target_hash):
        return False
    
    # Constant-time comparison prevents timing attacks
    return hmac.compare_digest(source_hash.encode(), target_hash.encode())
```

**9.2.5 Fallback Verification for Hash Failures**
```python
# Hash calculation fallback triggers:
# - BLAKE3 import failure (missing library)
# - Hash calculation exceptions (memory issues, file corruption)
# - Hash comparison mismatches (potential false positives)

if hash_verification_fails:
    # Automatic fallback to byte-by-byte comparison
    return _chunked_byte_comparison(src, temp_dst, chunk_size, progress_cb)
    # Uses same 4MB chunking for consistency
    # Provides definitive verification result
    # Logs hash failure details for debugging
```

### 9.3 Verification Policy Implementation - User Control Interface

**9.3.1 Three-Mode Verification System**
Based on mandatory UI radio button requirements (M04):

1. **"Verify no files" Mode:**
   - Skip all verification operations
   - Fastest copy performance
   - Use with caution - no integrity checking
   - Recommended only for trusted local operations

2. **"Verify every file after each copy" Mode (DEFAULT):**
   - Apply verification to all files regardless of size
   - Maximum data integrity assurance
   - Uses appropriate method (mmap for DIRECT, hash for STAGED)
   - Recommended setting for maximum safety

3. **"Verify only files < [threshold] after each copy" Mode:**
   - Verify files under specified size threshold (default 2GB)
   - Balance between performance and safety
   - Large files skip verification (performance optimization)
   - Threshold configurable via `FILECOPY_VERIFY_THRESHOLD_BYTES`

**9.3.2 Implementation Logic**
```python
def _should_verify_file(file_size: int, copy_strategy: str) -> bool:
    """
    Determine verification requirement based on user policy and file characteristics.
    
    Decision Matrix:
    - Policy 'none': Never verify
    - Policy 'all': Always verify
    - Policy 'lt_threshold': Verify if file_size < threshold
    - Invalid policy: Default to 'all' for safety
    """
    
    verify_policy = C.FILECOPY_VERIFY_POLICY
    
    if verify_policy == 'none':
        return False
    elif verify_policy == 'all':
        return True
    elif verify_policy == 'lt_threshold':
        return file_size < C.FILECOPY_VERIFY_THRESHOLD_BYTES
    else:
        # Safety default: verify everything if policy corrupted
        return True
```

**9.3.3 Performance Impact and User Guidance**
- **Verification Overhead:** Typically 15-30% additional time for local files
- **Network Verification:** Minimal overhead due to progressive hashing approach
- **User Education:** Clear labeling explains performance vs safety trade-offs
- **Threshold Guidance:** 2GB default balances verification coverage with performance

## 10. Advanced Error Handling and Edge Cases

### 10.1 UNC Path Rejection Implementation

```python
def _validate_paths(src: str, dst: str) -> ValidationResult:
    """
    Comprehensive path validation with UNC rejection.
    
    Implements dual-layer UNC rejection:
    - UI level: Prevent UNC path entry
    - Engine level: Safety net for programmatic calls
    """
    
    def is_unc_path(path: str) -> bool:
        """Detect UNC paths (\\server\share format)"""
        return path.startswith('\\\\') and len(path.split('\\')) >= 4
    
    def normalize_long_path(path: str) -> str:
        """Apply \\?\ prefix for long local paths"""
        if (len(path) > 260 and 
            not path.startswith('\\\\?\\') and 
            C.FILECOPY_LONG_PATH_NORMALIZATION):
            return f"\\\\?\\{path}"
        return path
    
    # UNC rejection (M13: use global constants)
    if is_unc_path(src) or is_unc_path(dst):
        if C.FILECOPY_UNC_PATH_REJECTION_STRICT:
            return ValidationResult(
                valid=False,
                error="UNC paths not supported. Please map network drives to drive letters.",
                suggestion="Use 'net use Z: \\\\server\\share' to map network paths"
            )
    
    # Path normalization
    normalized_src = normalize_long_path(src)
    normalized_dst = normalize_long_path(dst)
    
    return ValidationResult(
        valid=True,
        normalized_src=normalized_src,
        normalized_dst=normalized_dst
    )
```

### 10.2 Sparse File Detection and Handling

```python
def _check_sparse_file_attributes(file_path: str) -> SparseFileInfo:
    """
    Detect sparse files using Windows file attributes.
    
    Technical Implementation:
    - Uses GetFileAttributes Windows API
    - Checks FILE_ATTRIBUTE_SPARSE_FILE flag
    - Returns comprehensive sparse file information
    """
    
    FILE_ATTRIBUTE_SPARSE_FILE = 0x200
    
    try:
        # Get file attributes via Windows API
        attributes = kernel32.GetFileAttributesW(ctypes.c_wchar_p(file_path))
        
        if attributes == INVALID_FILE_ATTRIBUTES:
            error_code = kernel32.GetLastError()
            return SparseFileInfo(
                is_sparse=False,
                error=f"GetFileAttributes failed: {error_code}"
            )
        
        is_sparse = bool(attributes & FILE_ATTRIBUTE_SPARSE_FILE)
        
        if is_sparse:
            # Get additional sparse file information
            file_size = Path(file_path).stat().st_size
            
            # Get allocated size (actual disk usage)
            allocated_size = _get_allocated_size(file_path)
            compression_ratio = (file_size - allocated_size) / file_size if file_size > 0 else 0
            
            return SparseFileInfo(
                is_sparse=True,
                logical_size=file_size,
                allocated_size=allocated_size,
                compression_ratio=compression_ratio,
                warning_message=f"Sparse file detected: {compression_ratio:.1%} compression"
            )
        
        return SparseFileInfo(is_sparse=False)
        
    except Exception as e:
        return SparseFileInfo(is_sparse=False, error=f"Sparse file check failed: {e}")

def _handle_sparse_file_copy(src: str, dst: str) -> CopyResult:
    """
    Handle sparse file copying with user notification.
    
    Current Implementation:
    - Content-only copy (sparseness not preserved)
    - User warning about potential disk usage increase
    - Future enhancement: FSCTL_SET_SPARSE implementation
    """
    
    sparse_info = _check_sparse_file_attributes(src)
    
    if sparse_info.is_sparse and C.FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING:
        warning_message = (
            f"Copying sparse file: {Path(src).name}\n"
            f"Source compression: {sparse_info.compression_ratio:.1%}\n"
            f"Target will use full disk space: {sparse_info.logical_size:,} bytes\n"
            f"Note: Sparseness preservation not yet implemented"
        )
        
        # Log warning for user visibility
        if hasattr(status_callback, '__call__'):
            status_callback(f"WARNING: {warning_message}")
    
    # Proceed with regular copy (content-identical but not sparse-preserving)
    return _execute_standard_copy(src, dst)
```

### 10.3 Comprehensive Disk Space Checking

```python
def _check_sufficient_space(src: str, dst: str, backup_path: str = None) -> SpaceCheckResult:
    """
    Comprehensive disk space validation with margin.
    
    Checks:
    - Source file size
    - Backup space requirements (if overwriting)
    - Safety margin for system operations
    - Different handling for local vs network drives
    """
    
    src_size = Path(src).stat().st_size
    safety_margin = C.FILECOPY_FREE_DISK_SPACE_MARGIN
    
    # Calculate total space needed
    total_needed = src_size + safety_margin
    
    # Add backup space if overwriting existing file
    if backup_path and Path(dst).exists():
        total_needed += Path(dst).stat().st_size
    
    # Get destination drive info
    dst_drive = Path(dst).drive or Path(dst).parts[0]
    
    try:
        # Use Windows API for accurate space information
        free_bytes = ctypes.c_ulonglong()
        total_bytes = ctypes.c_ulonglong()
        
        result = kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(dst_drive),
            ctypes.byref(free_bytes),
            ctypes.byref(total_bytes),
            None
        )
        
        if not result:
            error_code = kernel32.GetLastError()
            # Network drive space check might fail
            if _is_network_drive(dst_drive):
                return SpaceCheckResult(
                    sufficient=True,  # Proceed but warn
                    warning=f"Cannot verify free space on network drive {dst_drive}",
                    available=None,
                    required=total_needed
                )
            else:
                return SpaceCheckResult(
                    sufficient=False,
                    error=f"GetDiskFreeSpaceEx failed: {error_code}",
                    available=None,
                    required=total_needed
                )
        
        available_space = free_bytes.value
        
        if available_space < total_needed:
            shortage = total_needed - available_space
            return SpaceCheckResult(
                sufficient=False,
                error=f"Insufficient disk space",
                details=f"Need {total_needed:,} bytes, have {available_space:,} bytes",
                shortage=shortage,
                available=available_space,
                required=total_needed
            )
        
        return SpaceCheckResult(
            sufficient=True,
            available=available_space,
            required=total_needed,
            margin=available_space - total_needed
        )
        
    except Exception as e:
        return SpaceCheckResult(
            sufficient=False,
            error=f"Space check failed: {e}",
            available=None,
            required=total_needed
        )
```

## 11. Windows API Implementation Details

### 11.1 Centralized Windows API Bindings (M13, M14)

**Note:** These bindings should be added to `FolderCompareSync_Global_Imports.py` for centralized management and consistency across modules.

```python
# Windows API Constants and Structures
# Add to FolderCompareSync_Global_Imports.py

# File Copy Constants
COPY_FILE_FAIL_IF_EXISTS = 0x00000001
COPY_FILE_RESTARTABLE = 0x00000002
COPY_FILE_OPEN_SOURCE_FOR_WRITE = 0x00000004
COPY_FILE_ALLOW_DECRYPTED_DESTINATION = 0x00000008

# Progress Callback Constants
PROGRESS_CONTINUE = 0
PROGRESS_CANCEL = 1
PROGRESS_STOP = 2
PROGRESS_QUIET = 3

# Copy Callback Reasons
CALLBACK_CHUNK_FINISHED = 0x00000000
CALLBACK_STREAM_SWITCH = 0x00000001

# Error Codes
ERROR_SUCCESS = 0
ERROR_REQUEST_ABORTED = 1235
ERROR_DISK_FULL = 112
ERROR_HANDLE_DISK_FULL = 39
ERROR_NOT_ENOUGH_MEMORY = 8

# Drive Type Constants
DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_REMOTE = 4
DRIVE_CDROM = 5
DRIVE_RAMDISK = 6

# File Attribute Constants
FILE_ATTRIBUTE_SPARSE_FILE = 0x200
FILE_ATTRIBUTE_COMPRESSED = 0x800
FILE_ATTRIBUTE_ENCRYPTED = 0x4000
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

# Windows API Function Signatures
kernel32.CopyFileExW.argtypes = [
    wintypes.LPCWSTR,                    # lpExistingFileName
    wintypes.LPCWSTR,                    # lpNewFileName
    wintypes.LPVOID,                     # lpProgressRoutine
    wintypes.LPVOID,                     # lpData
    wintypes.LPBOOL,                     # pbCancel
    wintypes.DWORD                       # dwCopyFlags
]
kernel32.CopyFileExW.restype = wintypes.BOOL

kernel32.GetDiskFreeSpaceExW.argtypes = [
    wintypes.LPCWSTR,                    # lpDirectoryName
    ctypes.POINTER(wintypes.ULARGE_INTEGER),  # lpFreeBytesAvailable
    ctypes.POINTER(wintypes.ULARGE_INTEGER),  # lpTotalNumberOfBytes
    ctypes.POINTER(wintypes.ULARGE_INTEGER)   # lpTotalNumberOfFreeBytes
]
kernel32.GetDiskFreeSpaceExW.restype = wintypes.BOOL

kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
kernel32.GetDriveTypeW.restype = wintypes.UINT

kernel32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
kernel32.GetFileAttributesW.restype = wintypes.DWORD
```

### 11.2 Progress Callback Implementation Pattern

```python
class ProgressManager:
    """
    Centralized progress management for copy operations.
    
    Handles:
    - Tkinter thread-safe updates
    - Cancellation detection
    - Progress throttling for performance
    - Multi-level progress tracking
    """
    
    def __init__(self, total_size: int, progress_callback, cancel_event,
                 update_frequency_hz: float = 20.0):
        self.total_size = total_size
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event
        self.last_update_time = 0
        self.update_interval = 1.0 / update_frequency_hz  # Convert Hz to seconds
        self.bytes_transferred = 0
    
    def update_progress(self, bytes_transferred: int) -> bool:
        """
        Update progress with throttling.
        
        Returns:
            bool: True to continue, False to cancel
        """
        self.bytes_transferred = bytes_transferred
        current_time = time.time()
        
        # Throttle updates for performance
        if current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            
            if self.progress_callback:
                percentage = (bytes_transferred / self.total_size) * 100 if self.total_size > 0 else 0
                self.progress_callback(bytes_transferred, self.total_size, percentage)
        
        # Check cancellation
        if self.cancel_event and self.cancel_event.is_set():
            return False
        
        return True
    
    def create_windows_progress_callback(self):
        """
        Create Windows API compatible progress callback.
        
        Returns function that can be passed to CopyFileExW.
        """
        def windows_callback(total_size, transferred, stream_size,
                           stream_transferred, stream_num, reason,
                           src_handle, dst_handle, user_data):
            
            if self.update_progress(transferred):
                return PROGRESS_CONTINUE
            else:
                return PROGRESS_CANCEL
        
        return windows_callback
```

## 12. Enhanced Rollback Procedures (M05, M10, M12)

### 12.1 Secure Temporary File Rollback Implementation

The enhanced rollback system uses secure temporary files to eliminate data corruption risk:

**Rollback Process Overview:**
1. **Preparation Phase:** Save source and target timestamps
2. **Safe Copy Phase:** Copy/verify to unique temporary file in target directory  
3. **Atomic Success Phase:** Move original → backup, rename temp → target, apply timestamps
4. **Automatic Rollback:** On any failure, simply delete temporary file (original untouched)

```python
def _execute_secure_copy_with_rollback(src: str, dst: str, overwrite: bool) -> CopyOperationResult:
    """
    Secure copy implementation with guaranteed rollback safety.
    
    Key Safety Features:
    - Original target file is never corrupted during operation
    - Atomic rename operations for final file placement  
    - Simple rollback: delete temporary file only
    - Zero risk of data loss during copy phase
    """
    
    source_timestamps = None
    target_timestamps = None 
    temp_file_path = None
    backup_path = None
    
    try:
        # Phase 1: Timestamp Capture (never fails the operation)
        source_timestamps = _capture_timestamps(src)
        if Path(dst).exists():
            if not overwrite:
                return _create_error_result("Target exists and overwrite disabled")
            target_timestamps = _capture_timestamps(dst)
        
        # Phase 2: Create secure temporary file path
        temp_file_path = _generate_temp_path(dst)
        
        # Phase 3: Copy and verify to temporary file
        # Original target remains completely untouched during this phase
        copy_result = _copy_and_verify_to_temp(src, temp_file_path)
        if not copy_result.success:
            # Simple rollback: just delete temp file
            _cleanup_temp_file(temp_file_path)
            return copy_result
        
        # Phase 4: Atomic file placement sequence
        # This is the only phase where original target is affected
        if Path(dst).exists():
            backup_path = _generate_backup_path(dst)
            os.rename(dst, backup_path)  # Atomic: original → backup
        
        os.rename(temp_file_path, dst)  # Atomic: temp → final location
        
        # Phase 5: Apply source timestamps and cleanup
        _apply_timestamps(dst, source_timestamps)
        _cleanup_backup(backup_path)  # Delete the renamed original target
        
        return _create_success_result(copy_result, "SECURE_STAGED")
        
    except Exception as e:
        # Comprehensive rollback with guaranteed safety
        return _perform_secure_rollback(
            temp_file_path, backup_path, dst, target_timestamps, str(e)
        )

def _perform_secure_rollback(temp_path: str, backup_path: str, target_path: str, 
                           original_timestamps: tuple, error_msg: str) -> CopyOperationResult:
    """
    Secure rollback procedure with guaranteed original file preservation.
    
    Rollback Safety Guarantees:
    1. Temporary file is always cleaned up
    2. Original target is restored if it was moved to backup
    3. Original timestamps are preserved
    4. No partial or corrupted files remain
    """
    
    rollback_errors = []
    
    try:
        # Step 1: Always cleanup temporary file
        if temp_path and Path(temp_path).exists():
            os.remove(temp_path)
            
        # Step 2: Restore original target if we moved it
        if backup_path and Path(backup_path).exists():
            if not Path(target_path).exists():
                # Target missing - restore from backup
                os.rename(backup_path, target_path)  # Atomic restore
                
                # Restore original timestamps
                if original_timestamps:
                    timestamp_manager.set_file_timestamps(target_path, *original_timestamps)
            else:
                # Target exists (rename succeeded) - just cleanup backup
                os.remove(backup_path)
                
    except Exception as rollback_error:
        rollback_errors.append(f"Rollback error: {rollback_error}")
    
    # Build comprehensive error message
    full_error = f"Copy failed: {error_msg}"
    if rollback_errors:
        full_error += f". Rollback issues: {'; '.join(rollback_errors)}"
    
    return _create_error_result(full_error)
```

## 13. Performance Optimization Guidelines

### 13.1 Memory Management for Large Files

```python
def _optimize_memory_usage(file_size: int) -> MemoryStrategy:
    """
    Determine optimal memory strategy based on file size and system resources.
    
    Strategies:
    - Small files (< 64MB): Load entirely into memory
    - Medium files (64MB - 1GB): Use memory mapping
    - Large files (> 1GB): Use chunked streaming
    - Network files: Always use chunked streaming
    """
    
    # Get available system memory
    try:
        import psutil
        available_memory = psutil.virtual_memory().available
    except ImportError:
        # Fallback: Assume 4GB available
        available_memory = 4 * 1024**3
    
    # Conservative memory usage: max 25% of available memory
    max_memory_usage = available_memory * 0.25
    
    if file_size < 64 * 1024**2:  # < 64MB
        return MemoryStrategy(
            type="in_memory",
            buffer_size=file_size,
            description="Small file - load entirely into memory"
        )
    elif file_size < min(1024**3, max_memory_usage):  # < 1GB or available memory
        return MemoryStrategy(
            type="memory_mapped",
            window_size=C.FILECOPY_MMAP_WINDOW_BYTES,
            description="Medium file - use memory mapping"
        )
    else:
        return MemoryStrategy(
            type="chunked_streaming",
            chunk_size=C.FILECOPY_NETWORK_CHUNK_BYTES,
            description="Large file - use chunked streaming"
        )
```

### 13.2 Debug Instrumentation for Performance Tuning

```python
# Performance-critical sections with commented debug statements
def _copy_with_performance_monitoring(src: str, dst: str) -> CopyResult:
    """
    Copy implementation with performance monitoring capabilities.
    
    Debug statements are commented out for production performance.
    Uncomment during performance analysis as needed.
    """
    
    start_time = time.perf_counter()
    bytes_copied = 0
    
    # # DEBUG: Uncomment for detailed timing analysis
    # chunk_times = []
    # io_wait_times = []
    
    try:
        with open(src, 'rb') as src_file, open(dst, 'wb') as dst_file:
            while True:
                # # DEBUG: Uncomment for chunk-level timing
                # chunk_start = time.perf_counter()
                
                chunk = src_file.read(C.FILECOPY_NETWORK_CHUNK_BYTES)
                if not chunk:
                    break
                
                # # DEBUG: Uncomment for I/O wait timing
                # io_start = time.perf_counter()
                dst_file.write(chunk)
                # io_end = time.perf_counter()
                # io_wait_times.append(io_end - io_start)
                
                bytes_copied += len(chunk)
                
                # # DEBUG: Uncomment for chunk timing collection
                # chunk_end = time.perf_counter()
                # chunk_times.append(chunk_end - chunk_start)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = bytes_copied / total_time if total_time > 0 else 0
        
        # # DEBUG: Uncomment for performance analysis
        # if chunk_times:
        #     avg_chunk_time = sum(chunk_times) / len(chunk_times)
        #     max_chunk_time = max(chunk_times)
        #     avg_io_wait = sum(io_wait_times) / len(io_wait_times) if io_wait_times else 0
        #     
        #     debug_info = (
        #         f"Performance Analysis:\n"
        #         f"  Total time: {total_time:.3f}s\n"
        #         f"  Throughput: {throughput / (1024**2):.1f} MB/s\n"
        #         f"  Avg chunk time: {avg_chunk_time * 1000:.1f}ms\n"
        #         f"  Max chunk time: {max_chunk_time * 1000:.1f}ms\n"
        #         f"  Avg I/O wait: {avg_io_wait * 1000:.1f}ms\n"
        #         f"  Chunks processed: {len(chunk_times)}"
        #     )
        #     print(debug_info)  # Or log to debug file
        
        return CopyResult(
            success=True,
            bytes_copied=bytes_copied,
            duration=total_time,
            throughput=throughput
        )
        
    except Exception as e:
        return CopyResult(success=False, error=str(e))
```

## 14. Integration and Compatibility

### 14.1 API Preservation

**Current API Surface (to be preserved):**

```python
class FileCopyManager_class:
    """Maintain existing interface for drop-in compatibility."""
    
    # Constructor compatibility
    def __init__(self, status_callback=None):
        """Preserve existing constructor signature."""
        pass
    
    # Core method compatibility (M12: overwrite parameter deprecated but maintained)
    def copy_file(self, source_path: str, target_path: str, overwrite: bool = True) -> CopyOperationResult:
        """
        Preserve exact method signature and return type.
        
        Enhanced implementation provides:
        - Intelligent strategy selection
        - Comprehensive verification
        - Atomic rollback capabilities
        - Performance optimization
        
        Note: overwrite parameter is deprecated (M12) but maintained for compatibility.
        All operations now use backup/rollback semantics.
        """
        pass
    
    # Utility method compatibility
    @staticmethod
    def determine_copy_strategy(source_path: str, target_path: str, file_size: int) -> CopyStrategy:
        """Enhanced strategy determination with network drive detection."""
        pass
    
    # Session management compatibility
    def start_copy_operation(self, operation_name: str, dry_run: bool = False) -> str:
        """Preserve session management interface."""
        pass
    
    def end_copy_operation(self, success_count: int, error_count: int, total_bytes: int):
        """Preserve session cleanup interface.""" 
        pass
    
    # Mode management compatibility
    def set_dry_run_mode(self, enabled: bool):
        """Preserve dry run interface."""
        pass
```

**CopyOperationResult Enhancement:**

```python
@dataclass
class CopyOperationResult:
    """
    Enhanced result object maintaining backward compatibility.
    
    Existing fields preserved, new fields added for enhanced functionality.
    """
    
    # Existing fields (preserved)
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
    
    # Enhanced fields (new)
    verification_mode: str = ""          # none/all/lt_threshold
    hash_algorithm: str = ""             # BLAKE3/SHA256/etc
    computed_hash: str = ""              # Source file hash
    rollback_performed: bool = False     # Whether rollback was needed
    rollback_success: bool = False       # Rollback success status
    sparse_file_detected: bool = False   # Sparse file warning
    throughput_mbps: float = 0.0         # Transfer rate in MB/s
    cancelled_by_user: bool = False      # User cancellation flag
    
    # Performance metrics (new)
    time_backup: float = 0.0             # Time spent on backup creation
    time_copy: float = 0.0               # Time spent on actual copy
    time_verify: float = 0.0             # Time spent on verification
    time_cleanup: float = 0.0            # Time spent on cleanup
    
    # Error details (enhanced)
    error_code: int = 0                  # Windows error code if applicable
    error_details: str = ""              # Detailed error information
    recovery_suggestion: str = ""        # Suggested recovery action
```

### 14.2 Integration with FolderCompareSync_class

**Status Callback Enhancement:**

```python
def enhanced_status_callback(self, message: str, level: str = "INFO", 
                            operation_id: str = "", progress: float = 0.0):
    """
    Enhanced status callback supporting different message levels.
    
    Backward compatible with existing single-parameter calls.
    """
    
    # Maintain backward compatibility
    if isinstance(message, str) and level == "INFO":
        # Standard status message
        self.add_status_message(message)
    
    # Enhanced functionality for new features
    if level == "WARNING":
        self.add_status_message(f"WARNING: {message}")
    elif level == "ERROR":
        self.add_status_message(f"ERROR: {message}")
    elif level == "PROGRESS":
        # Progress updates with operation context
        if operation_id:
            self.add_status_message(f"[{operation_id}] {message} ({progress:.1f}%)")
        else:
            self.add_status_message(f"{message} ({progress:.1f}%)")
```

## 15. Testing and Validation Framework

### 15.1 Unit Test Structure

```python
class TestFileCopyManager:
    """Comprehensive test suite for FileCopyManager functionality."""
    
    def test_strategy_selection(self):
        """Test DIRECT vs STAGED strategy selection logic."""
        # Local small file -> DIRECT
        strategy = FileCopyManager_class.determine_copy_strategy(
            "C:\\small_file.txt",    # 100MB file
            "D:\\target.txt",
            100 * 1024**2
        )
        assert strategy == CopyStrategy.DIRECT
        
        # Local large file -> STAGED  
        strategy = FileCopyManager_class.determine_copy_strategy(
            "C:\\large_file.bin",    # 5GB file
            "D:\\target.bin",
            5 * 1024**3
        )
        assert strategy == CopyStrategy.STAGED
        
        # Network file (any size) -> STAGED
        strategy = FileCopyManager_class.determine_copy_strategy(
            "Z:\\network_file.txt",  # Network mapped drive
            "C:\\target.txt",
            1024  # Small file
        )
        assert strategy == CopyStrategy.STAGED
    
    def test_rollback_mechanisms(self):
        """Test atomic rollback functionality."""
        # Create test scenario with existing target
        test_src = self.create_test_file("source.txt", "new content")
        test_dst = self.create_test_file("target.txt", "original content") 
        
        # Force copy failure after backup creation
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = [None, OSError("Simulated failure")]
            
            result = self.copy_manager.copy_file(test_src, test_dst)
            
            # Verify rollback occurred
            assert not result.success
            assert result.rollback_performed
            assert Path(test_dst).read_text() == "original content"
    
    def test_verification_modes(self):
        """Test different verification policy behaviors."""
        test_cases = [
            ("none", False),        # No verification
            ("all", True),          # Verify all files
            ("lt_threshold", True)  # Verify files under threshold
        ]
        
        for policy, should_verify in test_cases:
            with patch('C.FILECOPY_VERIFY_POLICY', policy):
                result = self.copy_manager.copy_file(self.small_test_file, self.temp_target)
                assert result.verification_passed == should_verify
    
    def test_ui_radio_button_integration(self):
        """Test radio button verification policy integration."""
        # Test that radio button selection affects verification behavior
        ui_policies = ['none', 'all', 'lt_threshold']
        
        for policy in ui_policies:
            # Simulate radio button selection
            with patch('C.FILECOPY_VERIFY_POLICY', policy):
                result = self.copy_manager.copy_file(self.test_file, self.temp_target)
                assert result.verification_mode == policy
```

### 15.2 Performance Benchmarking

```python
def benchmark_copy_strategies():
    """Performance comparison between DIRECT and STAGED strategies."""
    
    test_files = [
        ("10MB_file", 10 * 1024**2),
        ("100MB_file", 100 * 1024**2), 
        ("1GB_file", 1024**3),
        ("5GB_file", 5 * 1024**3)
    ]
    
    results = {}
    
    for filename, size in test_files:
        # Create test file
        test_file = create_test_file(filename, size)
        
        # Benchmark DIRECT strategy
        start_time = time.perf_counter()
        direct_result = copy_manager._execute_direct_strategy(test_file, f"{test_file}.direct")
        direct_time = time.perf_counter() - start_time
        
        # Benchmark STAGED strategy  
        start_time = time.perf_counter()
        staged_result = copy_manager._execute_staged_strategy(test_file, f"{test_file}.staged")
        staged_time = time.perf_counter() - start_time
        
        results[filename] = {
            'size': size,
            'direct_time': direct_time,
            'staged_time': staged_time,
            'direct_throughput': size / direct_time / (1024**2),  # MB/s
            'staged_throughput': size / staged_time / (1024**2),  # MB/s
        }
    
    # Generate performance report
    generate_performance_report(results)
```

## 16. Implementation Roadmap

### 16.1 Phase 1: Core Infrastructure (Week 1-2)

**Priority 1: Foundation Components**
1. **Enhanced Global Constants (M13)**
   - Update `FolderCompareSync_Global_Constants.py` with new constants
   - Add configuration validation and documentation
   - Implement constant loading and validation with "C." access pattern

2. **Windows API Centralization (M14)** 
   - Add enhanced Windows API bindings to `FolderCompareSync_Global_Imports.py`
   - Implement proper error handling for all API calls
   - Add API call logging and debugging support

3. **Strategy Selection Engine**
   - Implement `determine_copy_strategy()` with enhanced logic
   - Add drive type detection using Windows APIs
   - Implement UNC path rejection mechanisms

### 16.2 Phase 2: Copy Strategy Implementation (Week 3-4)

**Priority 2: DIRECT Strategy (M02)**
1. **CopyFileExW Integration**
   - Implement Windows native copy with progress callbacks
   - Add cancellation support through progress callbacks
   - Implement comprehensive error handling

2. **Memory-Mapped Verification**
   - Implement windowed mmap comparison algorithm
   - Add fallback to buffered comparison
   - Optimize window sizes for different file types

**Priority 3: STAGED Strategy (M03)**
1. **Chunked Copy with Progressive Hashing**
   - Implement chunked I/O with BLAKE3 integration
   - Add fallback to SHA256 when BLAKE3 unavailable
   - Optimize chunk sizes for network performance

2. **Hash Verification System**
   - Implement target hash computation
   - Add hash comparison and mismatch handling
   - Implement verification mode selection logic

### 16.3 Phase 3: UI Integration and Advanced Features (Week 5-6)

**Priority 4: UI Radio Button Implementation (M04)**
1. **Verification Mode Radio Buttons**
   - Implement 3 mutually exclusive radio buttons in pre-copy UI
   - Connect radio button selection to `FILECOPY_VERIFY_POLICY`
   - Ensure default selection is "Verify only files < [threshold] after each copy"
   - Add dynamic threshold display from global constants

2. **Progress Integration (M06, M11)**
   - Implement near real-time progress reporting
   - Add multi-level progress (file and operation level)
   - Ensure responsive cancellation within 500ms

**Priority 5: Rollback and Safety (M05, M10, M12)**
1. **Secure Temporary File Implementation**
   - Implement secure temporary file copy approach
   - Add comprehensive rollback procedures with guaranteed safety
   - Implement rollback verification and reporting
   - Remove deprecated overwrite semantics (M12)

2. **Edge Case Handling**
   - Implement sparse file detection and warnings
   - Add disk space checking with different strategies for local/network
   - Implement long path normalization

### 16.4 Phase 4: Testing and Documentation (Week 7-8)

**Priority 6: Comprehensive Testing**
1. **API Compatibility Layer**
   - Ensure drop-in compatibility with existing code
   - Implement enhanced `CopyOperationResult` with backward compatibility
   - Add migration support for existing configurations

2. **UI and Integration Testing**
   - Test radio button functionality and state persistence
   - Test progress reporting and cancellation responsiveness
   - Validate strategy selection with different file types and locations

**Priority 7: Documentation and Maintenance (M09)**
1. **Developer Documentation**
   - Complete API documentation with examples
   - Add troubleshooting guides for rollback scenarios
   - Create performance tuning guidelines

2. **User Documentation**
   - Update UI usage guides with radio button explanations
   - Add configuration guides for global constants
   - Create migration documentation from old FileCopyManager

## 17. Conclusion

This enhanced specification provides a comprehensive blueprint for implementing a robust, high-performance file copy system that maintains backward compatibility while significantly enhancing functionality, performance, and reliability. The secure temporary file rollback approach eliminates data corruption risk by ensuring original target files are never modified until the copy is completely verified and ready.

The detailed technical guidance, extensive pseudo-code examples, comprehensive Windows API integration details, and explicit UI requirements ensure that developers have all the information needed for successful implementation.

The specification addresses all mandatory requirements (M01-M14) while providing extensive flexibility for future enhancements and optimizations. The modular design, comprehensive error handling, detailed documentation support long-term maintainability and extensibility, and the clearly defined UI requirements ensure proper user interaction with the verification system.

**Key Benefits of This Implementation:**
- **Drop-in compatibility** ensures seamless integration (G.8, M08)
- **Performance optimization** provides significant speed improvements (G.3)
- **Enhanced rollback safety** guarantees zero data loss risk during copy operations (G.7, M05, M10)
- **Comprehensive verification** with user-controlled radio buttons ensures zero data corruption (G.5, M04)
- **Secure temporary file approach** eliminates corruption window during copy phase
- **Centralized constants and imports** improve maintainability (M13, M14)
- **Extensive documentation** supports long-term maintenance (G.9, M09)
- **Future-proof design** enables easy enhancement and extension

**Enhanced Safety Features:**
- **Zero corruption risk** during copy operations - original files never touched until verification complete
- **Atomic file placement** using proven rename operations for reliability
- **Simple rollback** mechanism with guaranteed cleanup
- **Progressive verification** ensures only validated files reach their final destination

**UI Integration Highlights:**
- **Three verification radio buttons** provide user control over verification policy
- **Default "Verify only files < [threshold] after each copy" selection** ensures balanced safety out of the box
- **Dynamic threshold display** keeps users informed of current settings
- **Near Real-time progress reporting** provides responsive user feedback
- **Sub-500ms cancellation** initial setting, ensures responsive user interaction