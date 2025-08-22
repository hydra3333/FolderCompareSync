# FileCopyManager Refactor — Technical Specification v01

## 1. Executive Summary

**Primary Objective:** Replace the existing `FileCopyManager_class` with an enhanced implementation that provides robust, high-performance file copying with comprehensive verification, rollback capabilities, and Windows-optimized strategies for Python 3.13+ on Windows 10+.

**Critical Design Goals:**
- **Drop-in compatibility:** Maintain existing API surface for seamless integration with `FolderCompareSync_class`
- **Performance optimization:** Intelligent strategy selection based on file size and location characteristics
- **Data integrity:** Zero tolerance for corrupted files through comprehensive verification
- **Operational safety:** Guaranteed rollback mechanisms with atomic operations
- **Developer clarity:** Extensive documentation, pseudo-code, and technical examples

## 2. Technical Change Goals

**G.1: Safe Copying with Notification and Status Returns**
- All copy operations must return detailed status information including error codes, messages, and recovery suggestions
- User cancellation support with graceful cleanup and rollback
- Comprehensive error classification (network, permission, space, corruption, etc.)

**G.2: Complete Date-Time Metadata Preservation**
- Preserve Windows file timestamps (Created/Modified) with sub-second precision
- Support for setting/resetting timestamps post-operation for workflow flexibility
- Timestamp validation and verification capabilities

**G.3: Efficient (Fast) Copying, Verifying, and Hash Calculation**
- Native Windows API utilization (`CopyFileExW`, memory-mapped I/O) for maximum throughput
- Intelligent chunking strategies optimized for different storage types (SSD/HDD/Network)
- Minimized redundant I/O operations through progressive hashing and verification

**G.4: Progress Updates via Tkinter**
- Tkinter-integrated progress callbacks with configurable update frequencies
- Granular progress reporting at chunk/window level for responsive cancellation
- Multi-level progress (per-file and overall operation progress)

**G.5: Very Efficient (Fast) Verification with Rollback Mechanism**
- Multiple verification modes: none, all files, size-threshold based
- Content verification using BLAKE3 hashing with fallback to byte comparison
- Verification false-positive rate of zero through robust implementation
- Immediate rollback mechanism when verification detects problems

**G.6: Well Named Global Parameters for Control**
- Well-named global constants for all thresholds, chunk sizes, and operational parameters
- Runtime configurability for different deployment scenarios
- Performance tuning capabilities through parameter adjustment

**G.7: Safety of Target Files with Guaranteed Rollback**
- Guaranteed restoration of original file state on any operation failure
- Atomic rename operations for backup/restore procedures
- No corrupted partial files remain after failed operations

**G.8: Drop-in Compatible Replacement FileCopyManager_class**
- Existing method signatures maintained: `copy_file(src, dst, overwrite=True)`
- Return object compatibility with current `CopyOperationResult` structure
- Preserved integration patterns with UI progress systems

**G.9: Well Commented Code at Function and Code Block Level**
- Function-level docstrings with purpose, arguments, returns, and usage examples
- Code block comments for complex algorithms and Windows API interactions
- Developer guidance for maintenance and extension

**G.10: Best Practice Coding for Speed-Essential Operations**
- Optimized tight loops for copying, verification, and hashing operations
- Commented-out debug statements in performance-critical sections
- Best practice implementations for memory usage and I/O efficiency

## 3. Mandatory Requirements

**M01:** Must support **two copy strategies**: Direct and Staged

**M02:** **Direct Copy** is fast, kernel-assisted, and optimized for local transfers, aimed at local non-networked files < specified gigabytes (global constant)

**M03:** **Staged Copy** is chunked, hash-driven, and optimized for networked files or where any file to be copied is >= specified gigabytes (global constant)

**M04:** Must provide **robust verification** options: verify all, verify none, verify only files < specified gigabytes (global constant)

**M05:** Must guarantee **rollback safety**: no corrupted partials remain after failure

**M06:** Must integrate with **Tkinter progress reporting**

**M07:** Must preserve metadata (timestamps, attributes)

**M08:** Must use **configurable constants** for thresholds and chunk/window sizes etc.

**M09:** Must be fully commented and maintainable

**M10:** Rollback ensures that **only verified files appear in the destination**

**M11:** Tkinter provides real-time **progress feedback** at both per-file and overall levels

**M12:** Any existing "overwrite" function is to be removed as deprecated, files will be copied and verified and all files will have capability to be rolled back

**M13:** Abstract global constants (including Windows-related constants) into the global constants module which exposes them as "C." via "import xxx as C"

**M14:** Abstract imports into global imports module which has code to expose them

## 4. User Interface Requirements

### 4.1 Verification Mode Radio Buttons

**Mandatory UI Component (M04):** Pre-copy UI must have 3 mutually exclusive radio buttons for verification policy selection:

1. **"Verify no files"** - Skip all verification (fastest, use with caution)
2. **"Verify every file after each copy"** - Verify all copied files regardless of size (**default selection**)
3. **"Verify only files < [threshold] after each copy"** - Verify only files under specified size threshold (configurable via global constant, initially 2GB)

### 4.2 UI Implementation Requirements

**Technical Integration:**
- Radio button selection controls the `FILECOPY_VERIFY_POLICY` global constant
- Default selection must be "verify every file after each copy" for maximum safety
- Threshold value in option 3 should be dynamically populated from `FILECOPY_VERIFY_THRESHOLD_BYTES`
- Radio button state must be preserved across UI sessions
- Clear labeling to help users understand performance vs safety trade-offs

**Display Format Example:**
```
Verification Options:
○ Verify no files (fastest)
● Verify every file after each copy (recommended) 
○ Verify only files < 2.0 GB after each copy (balanced)
```

### 4.3 UI Integration Points

**Progress Reporting Integration (M06, M11):**
- Real-time progress updates during copy operations
- Separate progress indicators for copy phase and verification phase  
- Cancel button must be responsive within 500ms during all operations
- Status messages must indicate which strategy (DIRECT/STAGED) is being used

## 5. Copy Strategy Implementation Details

### 5.1 Strategy Selection Matrix

| File Location | File Size | Strategy Applied |
|---------------|-----------|------------------|
| Local drives, < 2GB | Small | DIRECT |
| Local drives, >= 2GB | Large | STAGED |
| Network drives, any size | Any | STAGED |

**Implementation Note:** Strategy selection occurs in `determine_copy_strategy()` method using `GetDriveType` Windows API calls for accurate drive type detection.

### 5.2 DIRECT Strategy Specifications (M01, M02)

**When Used:**
- File size < 2GB AND no network drive letters involved
- Both source and target are on local drives (SSD/HDD on same machine)

**Technical Method:**
1. **Copy Phase:** Windows `CopyFileExW` API with progress callbacks
2. **Verification Phase:** Memory-mapped window comparison (64MB windows)
3. **Optimization:** Kernel-level, buffered operations for maximum local performance
4. **Progress:** Real-time callbacks from Windows API during copy, window-based progress during verification

### 5.3 STAGED Strategy Specifications (M01, M03)

**When Used:**
- File size >= 2GB OR any network drive letters involved
- Optimized for networked files and large file handling

**Technical Method:**
1. **Copy Phase:** Chunked I/O (4MB chunks) with progressive BLAKE3 hash calculation
2. **Verification Phase:** Hash comparison with fallback to byte comparison
3. **Optimization:** Network-aware chunking, reduced redundant reads (3x file size max vs 5x)
4. **Progress:** Chunk-based progress reporting for both copy and verification phases

## 6. Enhanced Global Constants Configuration

```python
# Copy Strategy Control (M01, M02, M03, M13)
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3      # 2 GiB - DIRECT vs STAGED
FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3     # 20 GiB - Hard size limit

# Performance Tuning - DIRECT Strategy (M08)
FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2                # 64 MiB - Verification windows
# Rationale: Balances memory usage vs cancellation responsiveness
# Larger windows = fewer progress updates but better I/O efficiency
# 64MB provides ~500ms cancellation latency on typical HDDs

# Performance Tuning - STAGED Strategy (M08)
FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2               # 4 MiB - Network I/O chunks
# Rationale: Optimized for 100Mbps networks with older PCs
# Provides ~320ms cancellation latency while maintaining throughput
# Larger chunks reduce network overhead but increase cancellation delay

# Verification Configuration (M04)
FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3            # 2 GiB - Verify size limit
FILECOPY_VERIFY_POLICY = 'all'                           # none | all | lt_threshold (default: all)

# System Resource Management
FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2           # 64 MiB - Safety margin
FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True            # Warn on sparse files

# Error Handling and Recovery
FILECOPY_BLAKE3_FALLBACK_ENABLED = True                  # Enable byte comparison fallback
FILECOPY_UNC_PATH_REJECTION_STRICT = True               # Reject UNC paths
FILECOPY_LONG_PATH_NORMALIZATION = True                 # Enable \\?\ prefix support

# Windows API Constants (M13)
FILECOPY_COPY_FILE_RESTARTABLE = 0x00000002             # CopyFileExW flags
FILECOPY_PROGRESS_CONTINUE = 0                           # Progress callback returns
FILECOPY_PROGRESS_CANCEL = 1
FILECOPY_ERROR_REQUEST_ABORTED = 1235                    # Windows error codes
FILECOPY_DRIVE_REMOTE = 4                                # Drive type constants
```

**Constants Rationale Documentation:**
Each constant includes inline comments explaining performance trade-offs, recommended values for different scenarios, and impact on user experience.

## 7. Detailed Copy Algorithm Specifications

### 7.1 DIRECT Strategy Implementation

**Algorithmic Flow:**
```python
def _execute_direct_strategy(src: str, dst: str, overwrite: bool,
                             progress_cb, cancel_event) -> CopyOperationResult:
    """
    DIRECT strategy implementation using Windows CopyFileExW API.
    Optimized for local drives with kernel-level performance.
    """
    
    # Phase 1: Preflight Validation and Backup
    backup_path = None
    original_timestamps = None
    
    if Path(dst).exists():
        if not overwrite:
            return _create_error_result("Overwrite disabled, target exists")
        
        # Save original timestamps for rollback
        original_timestamps = timestamp_manager.get_file_timestamps(dst)
        
        # Create atomic backup using rename
        backup_path = f"{dst}.backup_{uuid.uuid4().hex[:8]}"
        try:
            os.rename(dst, backup_path)  # Atomic operation
        except OSError as e:
            return _create_error_result(f"Backup creation failed: {e}")
    
    # Phase 2: Preflight Space Check
    if not _check_sufficient_space(src, dst, backup_path):
        _restore_backup_if_needed(backup_path, dst, original_timestamps)
        return _create_error_result("Insufficient disk space")
    
    # Phase 3: Windows CopyFileExW Copy Operation
    copy_result = _copy_with_windows_api(src, dst, progress_cb, cancel_event)
    if not copy_result.success:
        _restore_backup_if_needed(backup_path, dst, original_timestamps)
        return copy_result
    
    # Phase 4: Timestamp Preservation
    timestamp_result = timestamp_manager.copy_timestamps(src, dst)
    if not timestamp_result:
        _restore_backup_if_needed(backup_path, dst, original_timestamps)
        return _create_error_result("Timestamp preservation failed")
    
    # Phase 5: Verification (if enabled by radio button selection)
    if _should_verify_file(Path(src).stat().st_size):
        verify_result = _verify_by_mmap_windows(src, dst, progress_cb, cancel_event)
        if not verify_result:
            _restore_backup_if_needed(backup_path, dst, original_timestamps)
            return _create_error_result("Content verification failed")
    
    # Phase 6: Success Cleanup
    if backup_path and Path(backup_path).exists():
        os.remove(backup_path)  # Permanent deletion (M12)
    
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

### 7.2 STAGED Strategy Implementation

**Algorithmic Flow:**
```python
def _execute_staged_strategy(src: str, dst: str, overwrite: bool,
                             progress_cb, cancel_event) -> CopyOperationResult:
    """
    STAGED strategy implementation using chunked I/O with progressive hashing.
    Optimized for large files and network drives.
    """
    
    # Phase 1: Identical backup and preflight logic as DIRECT
    backup_path, original_timestamps = _prepare_operation(dst, overwrite)
    
    # Phase 2: Progressive Copy with Hash Calculation
    copy_result = _copy_with_progressive_hash(src, dst, progress_cb, cancel_event)
    if not copy_result.success:
        _restore_backup_if_needed(backup_path, dst, original_timestamps)
        return copy_result
    
    source_hash = copy_result.computed_hash
    
    # Phase 3: Timestamp Preservation (identical to DIRECT)
    timestamp_result = timestamp_manager.copy_timestamps(src, dst)
    if not timestamp_result:
        _restore_backup_if_needed(backup_path, dst, original_timestamps)
        return _create_error_result("Timestamp preservation failed")
    
    # Phase 4: Hash Verification (if enabled by radio button selection)
    if _should_verify_file(Path(src).stat().st_size):
        target_hash = _compute_target_hash(dst, progress_cb, cancel_event)
        if target_hash != source_hash:
            _restore_backup_if_needed(backup_path, dst, original_timestamps)
            return _create_error_result("Hash verification failed")
    
    # Phase 5: Success cleanup (identical to DIRECT)
    if backup_path and Path(backup_path).exists():
        os.remove(backup_path)  # Permanent deletion (M12)
    
    return _create_success_result(copy_result, "STAGED")
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

## 8. Comprehensive Verification Algorithms

### 8.1 Memory-Mapped Window Verification (DIRECT Strategy)

```python
def _verify_by_mmap_windows(src: str, dst: str, progress_cb, cancel_event) -> bool:
    """
    High-performance verification using memory-mapped windows.
    
    Technical Advantages:
    - OS-paged reads (4KB pages) without full file materialization
    - Memory-efficient for large files
    - Early failure detection on first mismatch
    - Faster than full-file byte comparison for large files
    """
    
    window_size = C.FILECOPY_MMAP_WINDOW_BYTES
    src_size = Path(src).stat().st_size
    dst_size = Path(dst).stat().st_size
    
    # Quick size check
    if src_size != dst_size:
        return False
    
    if src_size == 0:  # Empty files are identical
        return True
    
    try:
        with open(src, 'rb') as src_file, open(dst, 'rb') as dst_file:
            # Use memory mapping for large files
            with mmap.mmap(src_file.fileno(), 0, access=mmap.ACCESS_READ) as src_map:
                with mmap.mmap(dst_file.fileno(), 0, access=mmap.ACCESS_READ) as dst_map:
                    
                    offset = 0
                    while offset < src_size:
                        # Check cancellation
                        if cancel_event and cancel_event.is_set():
                            return False
                        
                        # Calculate window bounds
                        remaining = src_size - offset
                        current_window = min(window_size, remaining)
                        
                        # Compare window content
                        src_window = src_map[offset:offset + current_window]
                        dst_window = dst_map[offset:offset + current_window]
                        
                        if src_window != dst_window:
                            return False  # Early failure detection
                        
                        # Update progress
                        offset += current_window
                        if progress_cb:
                            progress = (offset / src_size) * 100
                            progress_cb(offset, src_size, progress)
                    
                    return True
                    
    except (OSError, ValueError) as e:
        # Fallback to buffered comparison on mmap failure
        return _verify_by_buffered_compare(src, dst, progress_cb, cancel_event)
```

### 8.2 Hash Verification with BLAKE3 Fallback (STAGED Strategy)

```python
def _compute_target_hash(target_path: str, progress_cb, cancel_event) -> str:
    """
    Compute hash of target file with progress reporting.
    
    Implementation Notes:
    - Uses same chunk size as copy operation for consistency
    - Supports BLAKE3 with automatic fallback to SHA256
    - Progress reporting for large files
    - Cancellation support
    """
    
    chunk_size = C.FILECOPY_NETWORK_CHUNK_BYTES
    file_size = Path(target_path).stat().st_size
    bytes_processed = 0
    
    # Initialize hasher (match the algorithm used during copy)
    try:
        import blake3
        hasher = blake3.blake3()
    except ImportError:
        import hashlib
        hasher = hashlib.sha256()
    
    try:
        with open(target_path, 'rb') as file:
            while bytes_processed < file_size:
                # Check cancellation
                if cancel_event and cancel_event.is_set():
                    raise OperationCancelledException("Verification cancelled")
                
                # Read chunk
                remaining = file_size - bytes_processed
                current_chunk_size = min(chunk_size, remaining)
                chunk = file.read(current_chunk_size)
                
                if not chunk:
                    break
                
                # Update hash
                hasher.update(chunk)
                bytes_processed += len(chunk)
                
                # Update progress
                if progress_cb:
                    progress = (bytes_processed / file_size) * 100
                    progress_cb(bytes_processed, file_size, progress)
        
        return hasher.hexdigest()
        
    except Exception as e:
        if C.FILECOPY_BLAKE3_FALLBACK_ENABLED:
            # Fallback to byte comparison if hashing fails
            return _fallback_to_byte_comparison(target_path, progress_cb, cancel_event)
        else:
            raise VerificationException(f"Hash computation failed: {e}")
```

### 8.3 Verification Policy Implementation

```python
def _should_verify_file(file_size: int) -> bool:
    """
    Determine if file should be verified based on radio button selection.
    
    Implements the three verification modes from UI radio buttons:
    - none: Skip all verification
    - all: Verify every file
    - lt_threshold: Verify only files under threshold
    """
    
    verify_policy = C.FILECOPY_VERIFY_POLICY
    
    if verify_policy == 'none':
        return False
    elif verify_policy == 'all':
        return True
    elif verify_policy == 'lt_threshold':
        return file_size < C.FILECOPY_VERIFY_THRESHOLD_BYTES
    else:
        # Default to 'all' for safety if policy is invalid
        return True
```

## 9. Advanced Error Handling and Edge Cases

### 9.1 UNC Path Rejection Implementation

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

### 9.2 Sparse File Detection and Handling

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

### 9.3 Comprehensive Disk Space Checking

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

## 10. Windows API Implementation Details

### 10.1 Centralized Windows API Bindings (M13, M14)

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

### 10.2 Progress Callback Implementation Pattern

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

## 11. Enhanced Rollback Procedures (M05, M10, M12)

### 11.1 Atomic Rollback Implementation

```python
def _restore_backup_if_needed(backup_path: str, target_path: str, 
                              original_timestamps: tuple = None) -> RollbackResult:
    """
    Comprehensive rollback procedure with error recovery.
    
    Rollback Steps:
    1. Remove corrupted target file (if exists)
    2. Restore backup using atomic rename
    3. Restore original timestamps
    4. Verify rollback success
    5. Report rollback status
    """
    
    rollback_result = RollbackResult()
    
    try:
        # Step 1: Remove corrupted target
        if Path(target_path).exists():
            try:
                os.remove(target_path)
                rollback_result.target_removed = True
            except Exception as e:
                rollback_result.errors.append(f"Failed to remove corrupted target: {e}")
                # Continue with rollback attempt
        
        # Step 2: Restore backup if it exists
        if backup_path and Path(backup_path).exists():
            try:
                os.rename(backup_path, target_path)  # Atomic operation
                rollback_result.backup_restored = True
            except Exception as e:
                critical_error = f"CRITICAL: Backup restore failed: {e}"
                rollback_result.errors.append(critical_error)
                rollback_result.critical_failure = True
                
                # Log critical failure for user attention
                log_message = (
                    f"CRITICAL ROLLBACK FAILURE: {critical_error}\n"
                    f"Original file may be lost. Backup location: {backup_path}\n"
                    f"MANUAL RECOVERY REQUIRED: Rename {backup_path} to {target_path}"
                )
                
                if hasattr(logging, 'error'):
                    logging.error(log_message)
                
                return rollback_result
        
        # Step 3: Restore original timestamps
        if original_timestamps and rollback_result.backup_restored:
            try:
                creation_time, modification_time = original_timestamps
                timestamp_manager = FileTimestampManager_class()
                
                success = timestamp_manager.set_file_timestamps(
                    target_path, creation_time, modification_time
                )
                
                if success:
                    rollback_result.timestamps_restored = True
                else:
                    rollback_result.warnings.append("Timestamp restoration failed")
                    
            except Exception as e:
                rollback_result.warnings.append(f"Timestamp restoration error: {e}")
        
        # Step 4: Verify rollback success
        if rollback_result.backup_restored:
            if Path(target_path).exists():
                rollback_result.verification_passed = True
                rollback_result.success = True
            else:
                rollback_result.errors.append("Rollback verification failed: Target file missing after restore")
        
        return rollback_result
        
    except Exception as e:
        rollback_result.errors.append(f"Unexpected rollback error: {e}")
        rollback_result.critical_failure = True
        return rollback_result

@dataclass
class RollbackResult:
    """Comprehensive rollback operation result."""
    success: bool = False
    target_removed: bool = False
    backup_restored: bool = False
    timestamps_restored: bool = False
    verification_passed: bool = False
    critical_failure: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def get_summary(self) -> str:
        """Generate human-readable rollback summary."""
        if self.success:
            return "Rollback completed successfully - original file state restored"
        elif self.critical_failure:
            return f"CRITICAL: Rollback failed - manual recovery required: {'; '.join(self.errors)}"
        else:
            return f"Rollback partially completed with issues: {'; '.join(self.errors + self.warnings)}"
```

## 12. Performance Optimization Guidelines

### 12.1 Memory Management for Large Files

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

### 12.2 Debug Instrumentation for Performance Tuning

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

## 13. Integration and Compatibility

### 13.1 API Preservation

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

### 13.2 Integration with FolderCompareSync_class

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

## 14. Testing and Validation Framework

### 14.1 Unit Test Structure

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

### 14.2 Performance Benchmarking

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

## 15. Implementation Roadmap

### 15.1 Phase 1: Core Infrastructure (Week 1-2)

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

### 15.2 Phase 2: Copy Strategy Implementation (Week 3-4)

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

### 15.3 Phase 3: UI Integration and Advanced Features (Week 5-6)

**Priority 4: UI Radio Button Implementation (M04)**
1. **Verification Mode Radio Buttons**
   - Implement 3 mutually exclusive radio buttons in pre-copy UI
   - Connect radio button selection to `FILECOPY_VERIFY_POLICY`
   - Ensure default selection is "verify every file after each copy"
   - Add dynamic threshold display from global constants

2. **Progress Integration (M06, M11)**
   - Implement real-time progress reporting
   - Add multi-level progress (file and operation level)
   - Ensure responsive cancellation within 500ms

**Priority 5: Rollback and Safety (M05, M10, M12)**
1. **Atomic Rollback Implementation**
   - Implement backup creation using atomic rename
   - Add comprehensive rollback procedures
   - Implement rollback verification and reporting
   - Remove deprecated overwrite semantics (M12)

2. **Edge Case Handling**
   - Implement sparse file detection and warnings
   - Add disk space checking with different strategies for local/network
   - Implement long path normalization

### 15.4 Phase 4: Testing and Documentation (Week 7-8)

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

## 16. Conclusion

This enhanced specification provides a comprehensive blueprint for implementing a robust, high-performance file copy system that maintains backward compatibility while significantly enhancing functionality, performance, and reliability. The detailed technical guidance, extensive pseudo-code examples, comprehensive Windows API integration details, and explicit UI requirements ensure that developers have all the information needed for successful implementation.

The specification addresses all mandatory requirements (M01-M14) while providing extensive flexibility for future enhancements and optimizations. The modular design, comprehensive error handling, detailed documentation support long-term maintainability and extensibility, and the clearly defined UI requirements ensure proper user interaction with the verification system.

**Key Benefits of This Implementation:**
- **Drop-in compatibility** ensures seamless integration (G.8, M08)
- **Performance optimization** provides significant speed improvements (G.3)
- **Comprehensive verification** with user-controlled radio buttons ensures zero data corruption (G.5, M04)
- **Atomic rollback** guarantees operational safety (G.7, M05, M10)
- **Centralized constants and imports** improve maintainability (M13, M14)
- **Extensive documentation** supports long-term maintenance (G.9, M09)
- **Future-proof design** enables easy enhancement and extension

**UI Integration Highlights:**
- **Three verification radio buttons** provide user control over verification policy
- **Default "verify all" selection** ensures maximum safety out of the box
- **Dynamic threshold display** keeps users informed of current settings
- **Real-time progress reporting** provides responsive user feedback
- **Sub-500ms cancellation** ensures responsive user interaction