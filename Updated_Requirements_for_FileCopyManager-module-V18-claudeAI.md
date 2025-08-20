# FileCopyManager Refactor Plan - Complete Implementation Strategy

## Executive Summary

Create a drop-in replacement for `FileCopyManager_class` that maintains full API compatibility while implementing modern copy strategies, enhanced verification, and simplified architecture. The refactor preserves the dual-strategy approach but streamlines implementation and adds Windows native APIs for performance.

## Requirements Mapping (R.1-R.6)

### R.1: Safe Copying with Notifications & Status
- **Enhanced error handling**: Structured results with Win32 error codes where applicable
- **Cancellation support**: `threading.Event`-based cancellation for all copy/verify operations
- **Rollback capability**: Maintain backup/restore logic for staged operations
- **Status reporting**: Rich status messages via callback without touching tkinter directly

### R.2: Metadata Preservation
- **Files**: `CopyFileExW` preserves most metadata; follow with explicit `SetFileTime` for guarantees
- **Directories**: Centralize timestamp copying in the manager (instead of GUI calling timestamp_manager directly)
- **Verification**: Ensure creation/modification times are preserved correctly

### R.3: Efficient Copying
- **Local drives**: Windows `CopyFileExW` with kernel-level buffering
- **Network/SMB**: Chunked copy with inline BLAKE3 hashing (I/O optimized)
- **Strategy selection**: Maintain DIRECT/STAGED approach based on file size and location

### R.4: Progress Updates via Tkinter
- **Copy progress**: `CopyFileExW` progress callback feeds thread-safe queue
- **Verify progress**: Windowed progress updates during verification
- **Thread isolation**: Manager pushes to queue, GUI pumps via `root.after(50, pump_queue)`

### R.5: Very Efficient Verification
- **Local files**: Windowed mmap byte-compare (8-64 MiB windows)
- **Network files**: BLAKE3 hash comparison or buffered chunk compare
- **Fallback**: Per-window buffered comparison when mmap fails
- **Multiple modes**: NONE | SIZE | MMAP | HASH based on file characteristics

### R.6: Configurable Verification Threshold
- **Threshold-based**: Verify files < 1GB by default, configurable via global constants
- **Mode selection**: 'none' | 'all' | 'lt_threshold'
- **Per-file decision**: Based on size and location characteristics

## Detailed Copy/Verify Requirements (Mandatory Implementation Criteria)

## A) Local HDD → HDD (NTFS, same machine) - Requirements

### A.1) Copy Requirements
**Mandatory: Use Windows native `CopyFileExW` API via ctypes**

**Rationale for CopyFileExW selection:**
- Performs actual copy using OS (fast, kernel-level, buffered)
- Automatically preserves most metadata
- **Critical capability**: Accepts callback function that Windows calls periodically with progress information
- Callback provides: Total file size, Bytes copied so far, Pause/cancel status
- Enables real-time progress bar during copy operation

**Implementation requirements:**
- Must use proper ctypes bindings with `PROGRESS_ROUTINE` callback type
- Progress callback must be thread-safe (push to queue, GUI pulls via `root.after()`)
- Must follow copy with explicit `SetFileTime` call for timestamp guarantee
- Must support cancellation via callback return values (`PROGRESS_CANCEL` to abort)

### A.2) Verification Requirements
**Mandatory: Windowed mmap byte-compare (no hashing)**

**UI Configuration Requirements:**
- Implement mutually exclusive verification options in pre-copy UI using **radio buttons** (grouped):
  ```
  File Verification Mode:
  ○ Verify no files (skip all verification)
  ● Verify every file after each copy (default selection)
  ○ Verify only files < threshold after each copy (uses configurable FILE_VERIFY_THRESHOLD_BYTES)
  ```
- **Control type rationale**: Radio buttons enforce mutual exclusivity and prevent invalid multi-selection states
- **Default behavior**: "Verify every file after each copy" must be pre-selected on application startup

**Windowed mmap implementation requirements:**
- **Window processing**: After copying, walk both source and target files simultaneously in fixed-size windows (8-64 MiB range, configurable via `FILE_MMAP_WINDOW_BYTES`)
- **Per-window comparison**: Compare each corresponding window using windowed mmap operations (omit hashing scheme for local verification)
- **Direct byte comparison**: Use `memcmp`-style comparison, fail fast on first byte mismatch within window
- **Memory efficiency rationale**: Provides OS-paged reads (4 KiB pages) without loading whole file, works on memory-constrained PCs, faster than `read()` entire file into Python buffers, avoids `==` on full bytes objects that force full file materialization and can thrash memory
- **Fail-fast requirement**: Stop comparison immediately on first window mismatch for immediate error detection
- **Window-level fallback**: If mmap window read fails for any specific window (e.g., exotic filesystem), automatically fall back to plain buffered compare for that individual window only, then continue with mmap for subsequent windows
- **Fallback transparency**: Fallback must be transparent to caller - same interface, different implementation per window

**Progress reporting requirement:**
- Advance progress bar by window size after each comparison window
- Must integrate with tkinter UI via thread-safe queue mechanism
- Check cancellation `threading.Event` between windows

**Future extensibility requirement:**
- Structure must allow provision for computing source hash during windowed mmap copy and target hash via separate windowed mmap parse of closed-then-reopened target for hash comparison (if hash-based verification added later)

## B) Network / NAS / SMB Operations - Requirements

### B.1) Copy Requirements
**Mandatory: Chunked I/O with inline source hashing (I/O efficiency optimization)**

**Method selection rationale:**
- CopyFileExW over network is possible but I/O inefficient for large files
- CopyFileExW approach: `[read source → write target → re-read source for verify → re-read target for verify → compare hash]` = **4 total file reads**
- Required chunked I/O approach: `[read source + calculate hash inline → write target → re-read target for verify → compare hash]` = **3 total file reads**
- Must use non-mmap chunked I/O for network conditions

**Implementation requirements:**
- **Chunked copy process**: Read source in configurable chunks (recommend 4 MiB, must be configurable via `FILE_CHUNK_WINDOW_BYTES`)
- **Progressive hashing during copy**: During each source chunk read, progressively calculate hash using BLAKE3 algorithm before writing chunk to target
- **Copy cycle per chunk**: `[read source chunk → update hash with chunk → write chunk to target → update progress]` repeated until complete
- **Hash algorithm requirement**: Use BLAKE3 (faster than SHA-512 on >=5 year old CPUs, much faster than SHA-2, optimized for verification purposes)
- **Progress reporting**: Update progress per chunk written to target
- **Metadata preservation**: Must follow copy with explicit `SetFileTime` call for metadata preservation
- **Return source hash**: Return calculated source_hash for verification phase (avoids re-reading source)
- **Cancellation checking**: Check `threading.Event` between chunks

### B.2) Verification Requirements
**Mandatory: Hash-based verification with buffered I/O**

**UI Configuration Requirements:**
- Same mutually exclusive verification options as local scenario using **radio buttons** (grouped):
  ```
  File Verification Mode:
  ○ Verify no files (skip all verification)
  ● Verify every file after each copy (default selection)
  ○ Verify only files < threshold after each copy (uses configurable FILE_VERIFY_THRESHOLD_BYTES)
  ```
- **Implementation note**: Identical UI control to local verification - single radio button group applies to both local and network operations

**Target hash calculation requirements:**
- **Network-optimized process**: For post-copy verification of target file, use buffered chunked I/O (1-8 MiB chunks, configurable via global constant)
- **Network-specific constraint**: Avoid mmap over SMB to prevent pathological page-fault latency spikes over network stack
- **Target verification cycle**: `[read target chunk → update hash with chunk → update progress]` repeated until complete
- **Hash algorithm consistency**: Calculate target hash using same BLAKE3 algorithm as source (faster than SHA-512 on >=5 year old CPUs, much faster than SHA-2 per advice)
- **Hash comparison**: Compare source_hash (from copy phase) with calculated target_hash for verification
- **Progress reporting requirement**: Advance progress bar by chunk size during target hash calculation
- **Cancellation checking**: Check `threading.Event` between chunks

**Alternative fallback requirement:**
- If BLAKE3 unavailable, fall back to buffered chunk-by-chunk byte comparison (1-8 MiB chunks) with same progress reporting interface

## Technical Implementation Strategy

### Core Architecture Improvements

#### 1. Modular Internal Design
- **Keep public surface**: Maintain exact same public API for drop-in compatibility
- **Split strategies internally**: Break DIRECT and STAGED paths into small, focused helper functions
- **Testable components**: Each helper function handles one specific responsibility
- **Clear separation**: Copy logic, verification logic, backup logic, and metadata logic isolated
- **Function composition**: Public methods orchestrate calls to focused helpers

#### 2. Simplified Dry-Run Handling
- **Abstract simulation pattern**: Single `_execute_or_simulate()` wrapper method
- **Consistent behavior**: All operations check dry-run mode in one place
- **Cleaner code**: Eliminate scattered dry-run conditionals throughout methods

#### 3. Windows Native API Integration
- **CopyFileExW**: Primary copy method for local drives
- **SetFileTime**: Explicit timestamp preservation after copy
- **Progress callbacks**: Native progress reporting during copy operations
- **Error handling**: Capture and translate Win32 error codes

#### 4. Enhanced Verification System
- **Multiple verification modes**:
  - `NONE`: Skip verification entirely
  - `SIZE`: Size-only check (current behavior)
  - `MMAP`: Memory-mapped byte comparison for local files
  - `HASH`: BLAKE3 hash comparison for network files
- **Automatic mode selection**: Based on file size, location, and global settings
- **Windowed processing**: Bounded memory usage for large files

#### 5. Reduced Logging Verbosity
- **Essential messages only**: Eliminate granular step-by-step logging
- **Structured reporting**: Clear start/success/failure messages
- **Error focus**: Detailed logging only for errors and critical operations
- **Performance tracking**: Summary statistics without noise

### Internal Helper Function Architecture

#### Core Helper Functions (Private):
```python
# Copy operations
def _copy_local_file(src, dst, progress_callback, cancel_event) -> CopyResult
def _copy_network_file(src, dst, progress_callback, cancel_event) -> CopyResult
def _create_directory_path(path, dry_run) -> bool

# Verification operations  
def _verify_by_size(src, dst) -> bool
def _verify_by_mmap(src, dst, progress_callback, cancel_event) -> bool
def _verify_by_hash(src, dst, progress_callback, cancel_event) -> bool

# Metadata operations (delegating to FileTimestampManager_class)
def _preserve_timestamps(src, dst) -> bool  # Uses self.timestamp_manager.copy_timestamps()
def _validate_timestamp_preservation(src, dst) -> bool  # Optional verification helper

# Backup/restore operations (STAGED strategy)
def _create_backup(target_path, dry_run) -> Optional[str]
def _restore_backup(backup_path, target_path, dry_run) -> bool
def _cleanup_backup(backup_path, dry_run) -> bool

# Strategy coordination
def _execute_direct_strategy(src, dst, overwrite, progress_cb, cancel_event) -> CopyOperationResult
def _execute_staged_strategy(src, dst, overwrite, progress_cb, cancel_event) -> CopyOperationResult
```

#### Public API Orchestration:
- **copy_file()**: Validates inputs, selects strategy, calls appropriate `_execute_*_strategy()`
- **Strategy helpers**: Compose the focused helper functions in correct sequence
- **Error handling**: Each helper returns structured results, orchestrator handles rollback
- **Testing**: Each helper can be unit tested independently with mock objects

#### Benefits:
- **Maintainability**: Small, focused functions are easier to understand and modify
- **Testability**: Each operation can be tested in isolation with controlled inputs
- **Reusability**: Helpers can be shared between DIRECT and STAGED strategies where appropriate
- **Debugging**: Easier to isolate issues to specific operations
- **Code clarity**: Public methods become clear orchestration of well-defined steps

### Global Constants Extensions

Add to `FolderCompareSync_Global_Constants.py`:

```python
# File verification configuration (from advice requirements)
FILE_VERIFY_MODE = 'lt_threshold'  # 'none' | 'all' | 'lt_threshold' (default per advice)
FILE_VERIFY_THRESHOLD_BYTES = 1_073_741_824  # 1 GiB (exact value from advice)
FILE_MMAP_WINDOW_BYTES = 16 * 1024 * 1024    # 16 MiB (advice: 8-64 MiB range typical)
FILE_CHUNK_WINDOW_BYTES = 4 * 1024 * 1024    # 4 MiB (network chunks per advice)

# Copy engine configuration
COPY_USE_NATIVE_API = True        # Use CopyFileExW when available
COPY_PROGRESS_UPDATE_FREQUENCY = 1024 * 1024  # Update every 1MB
COPY_CANCEL_CHECK_FREQUENCY = 100  # Check cancellation every N chunks

# Progress/UI integration (from advice patterns)
PROGRESS_QUEUE_POLL_MS = 50       # 50ms polling interval from advice
PROGRESS_QUEUE_BATCH_SIZE = 10    # Process up to N queue items per poll
```

### Windows API Centralization

Add to `FolderCompareSync_Global_Imports.py`:

```python
# Windows API bindings shared by FileCopyManager and FileTimestampManager
if platform.system() == 'Windows':
    # Centralized Windows API setup
    kernel32 = ctypes.windll.kernel32
    
    # Common structures
    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]
    
    # Progress callback type for CopyFileExW
    PROGRESS_ROUTINE = ctypes.WINFUNCTYPE(
        wintypes.DWORD,      # Return type
        wintypes.LARGE_INTEGER,  # TotalFileSize
        wintypes.LARGE_INTEGER,  # TotalBytesTransferred
        wintypes.LARGE_INTEGER,  # StreamSize
        wintypes.LARGE_INTEGER,  # StreamBytesTransferred
        wintypes.DWORD,          # dwStreamNumber
        wintypes.DWORD,          # dwCallbackReason
        wintypes.HANDLE,         # hSourceFile
        wintypes.HANDLE,         # hDestinationFile
        wintypes.LPVOID          # lpData
    )
    
    # API function bindings with proper signatures
    kernel32.CopyFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, PROGRESS_ROUTINE, wintypes.LPVOID, wintypes.LPBOOL, wintypes.DWORD]
    kernel32.CopyFileExW.restype = wintypes.BOOL
    
    kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    
    kernel32.SetFileTime.argtypes = [wintypes.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
    kernel32.SetFileTime.restype = wintypes.BOOL
    
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD
    
    # Constants used by both managers
    INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    GENERIC_WRITE = 0x40000000
    FILE_WRITE_ATTRIBUTES = 0x100
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    
    # Copy-specific constants
    COPY_FILE_FAIL_IF_EXISTS = 0x00000001
    COPY_FILE_RESTARTABLE = 0x00000002
    PROGRESS_CONTINUE = 0
    PROGRESS_CANCEL = 1
    PROGRESS_STOP = 2
    PROGRESS_QUIET = 3
```

**Benefits:**
- **Eliminate duplication**: Both FileCopyManager and FileTimestampManager use shared API bindings
- **Centralized maintenance**: Windows API setup in one location
- **Consistent signatures**: Proper argtypes/restype definitions for all APIs
- **Platform safety**: Wrapped in Windows platform check

### Progress Integration & Cancellation (meets R.4, R.1)

**Threading Architecture Requirements:**
- **Worker thread execution**: Run all copy/verify operations in dedicated worker thread (never touch tkinter from worker)
- **Main thread UI updates**: All tkinter updates via `root.after()` calls from main thread only

**Progress Reporting Queue Pattern:**
- **Queue mechanics**: Worker thread pushes `(bytes_done, bytes_total)` tuples to thread-safe queue
- **Main thread polling**: Use `root.after(50, pump_queue)` pattern to drive `ttk.Progressbar` and status labels
- **Polling frequency**: 50ms polling interval for responsive UI without excessive overhead
- **Queue consumption**: Main thread pump function processes all available queue items per call

**Cancellation Architecture:**
- **Cancellation mechanism**: Use `threading.Event` that UI can set for cancel requests
- **Native API integration**: Pass Event address to `CopyFileExW` callback for immediate cancellation support
- **Verify loop integration**: Check cancellation Event in all verification loops (mmap windows, hash chunks)
- **Graceful termination**: Return `status='cancelled'` in result structure when Event is set

**Implementation pattern:**
```python
# Worker thread pattern
def _copy_with_progress(src, dst, progress_queue, cancel_event):
    # CopyFileExW progress callback pushes to queue and checks cancel_event
    # Returns when cancelled or complete
    
# Main thread pattern  
def pump_progress_queue():
    while not progress_queue.empty():
        bytes_done, bytes_total = progress_queue.get_nowait()
        progress_bar.configure(value=bytes_done, maximum=bytes_total)
    root.after(50, pump_progress_queue)  # Continue polling
```

### Enhanced Copy Operation Flow

#### For Local Files:
1. **Validate inputs** and check cancellation
2. **Select strategy** based on file size and characteristics
3. **Setup backup** (STAGED only) with atomic rename
4. **Copy file** using `CopyFileExW` with progress callback
5. **Set timestamps** explicitly via `SetFileTime`
6. **Verify copy** using windowed mmap comparison with per-window fallback
7. **Cleanup backup** (STAGED only) or rollback on failure
8. **Report results** with detailed statistics

#### For Network Files:
1. **Validate inputs** and check cancellation
2. **Select strategy** and verification mode
3. **Setup backup** (STAGED only)
4. **Chunked copy** with inline BLAKE3 hashing per chunk
5. **Set timestamps** via `SetFileTime`
6. **Verify copy** using hash comparison with buffered target hash calculation
7. **Cleanup/rollback** as needed
8. **Report results** with network-specific metrics

### Error Handling Strategy

#### Structured Results:
```python
@dataclass
class CopyOperationResult:
    # Core status (from advice requirements)
    status: str  # 'ok' | 'cancelled' | 'error'
    success: bool  # For backward compatibility with existing GUI
    
    # Byte tracking (from advice)
    bytes_total: int
    bytes_copied: int
    
    # Error diagnostics (from advice)
    error_code: int  # Win32 GetLastError() when applicable
    error_message: str
    
    # Existing fields for GUI compatibility
    strategy_used: CopyStrategy
    verification_mode: str  # 'none' | 'size' | 'mmap' | 'hash'
    verification_passed: bool
    duration_seconds: float
    # ... other existing fields preserved
```

#### Error Recovery:
- **Automatic fallbacks**: mmap → buffered compare, CopyFileExW → chunked copy
- **Detailed diagnostics**: Win32 error codes and system error messages
- **Rollback guarantees**: Atomic operations with cleanup on failure

### API Compatibility Matrix

| Current Interface | New Implementation | Notes |
|------------------|-------------------|-------|
| `FileCopyManager_class(status_callback)` | ✅ Preserved | Enhanced with progress callback support |
| `start_copy_operation(name, dry_run)` | ✅ Preserved | Returns operation_id for logging |
| `copy_file(src, dst, overwrite)` | ✅ Preserved | Enhanced with cancellation support |
| `end_copy_operation(success, error, bytes)` | ✅ Preserved | Updated with strategy statistics |
| `CopyOperationResult` | ✅ Enhanced | Additional fields for verification details |
| `determine_copy_strategy()` | ✅ Preserved | Updated logic for new thresholds |
| `timestamp_manager` attribute | ✅ Preserved | Maintains GUI compatibility |

### Performance Optimizations

#### Memory Management:
- **Bounded windows**: Fixed memory usage regardless of file size
- **Lazy allocation**: Allocate verification buffers only when needed
- **Resource cleanup**: Explicit cleanup of mmap handles and buffers

#### I/O Efficiency:
- **Kernel-level copy**: `CopyFileExW` for maximum throughput
- **Sequential access**: Optimize for disk/network access patterns
- **Minimal reads**: Inline hashing to avoid redundant source reads

## Default Implementation Policy (Satisfies R.1–R.6)

**Copy Strategy Selection (per advice):**
- **Local drives**: `CopyFileExW` + `SetFileTime` for guaranteed metadata preservation
- **Network/SMB/NAS**: Chunked copy + inline BLAKE3 hashing (Option B1 for I/O efficiency)

**Verification Strategy Selection (per advice):**
- **Local drives**: Windowed `mmap` byte-compare (no hashing - faster for local)
- **Network drives**: BLAKE3 hash comparison (hash calculated during copy, verified post-copy)

**Verification Mode Implementation:**
- **Default setting**: `'lt_threshold'` with 1 GiB threshold (balances performance vs verification)
- **Mode behavior**:
  - `'none'` → Skip all verification (fastest)
  - `'all'` → Verify every file regardless of size (most thorough)
  - `'lt_threshold'` → Verify only files smaller than `FILE_VERIFY_THRESHOLD_BYTES` (balanced)

**Progress Reporting (meets R.4):**
- **Both phases**: Live tkinter updates for copy and verify operations
- **Queue pattern**: Worker thread → queue → main thread `root.after(50ms)` polling
- **Cancellation**: `threading.Event` integration with immediate response in native callbacks

**Error Handling (meets R.1):**
- **Structured returns**: All operations return standardized result objects
- **Win32 integration**: Include `GetLastError()` codes when applicable for native API failures
- **Status values**: `'ok'` | `'cancelled'` | `'error'` for clear operation outcomes
- **Detailed diagnostics**: Error messages with context for troubleshooting

## Implementation Timeline

### Phase 1: Core Infrastructure
- Windows API integration (`CopyFileExW`, `SetFileTime`)
- Enhanced error handling and result structures
- Simplified dry-run abstraction
- Global constants extensions

### Phase 2: Verification System
- mmap-based verification for local files
- BLAKE3 hash verification for network files
- Configurable verification modes and thresholds
- Progress reporting for verification phase

### Phase 3: Integration & Testing
- Drop-in compatibility testing with existing GUI
- Performance benchmarking against current implementation
- Error handling validation and edge case testing
- Documentation and logging cleanup

## Validation Criteria

### Functionality:
- ✅ All existing copy operations work unchanged
- ✅ Dry-run mode produces identical simulation behavior
- ✅ Progress reporting maintains current fidelity
- ✅ Error handling preserves existing behavior while adding enhancements

### Performance:
- ✅ Local copy operations faster via `CopyFileExW`
- ✅ Verification time reduced via mmap for large local files
- ✅ Network operations maintain current performance or better
- ✅ Memory usage bounded regardless of file size

### Reliability:
- ✅ Enhanced error reporting with Win32 error codes
- ✅ Improved cancellation responsiveness
- ✅ More robust verification options
- ✅ Simplified code reduces maintenance burden

This approach delivers a modernized, high-performance file copy manager while maintaining complete backward compatibility with the existing GUI integration.

#### Clarity for processes in Copying and Verifying

To reduce risk of confusion arising from multiple possible approaches,
the following discussion summary of explanations explores in some detail
how the "copy" and "verfy" may work in terms of means and fallbacks and
must be read in conjunction with and subject to the rest of this document. 

Where conflicts occur or clarity is inadequate, please query the developer
for assessments and decisions.

```
A) Local HDD -> HDD (NTFS, same machine)
---------------------------------------
1. Copy first
1.1. Copy using a native copy with progress/callbacks: Windows native CopyFileExW API (via ctypes) because it:
- Does the actual copy using the OS (fast, kernel-level, buffered).
- Preserves metadata
- Crucially: accepts a callback function that Windows calls periodically with progress info.
- That callback gives you Total file size, Bytes copied so far, Whether the copy is paused or cancelled etc 
So, for local drive-to-drive copies (both HDDs, SSDs, or mixed), CopyFileExW is preferred because we
want a fast windows-optimized we copy function which facilitates a progress bar during the copy.

2. Verify with a windowed mmap compare.
2.1 In the pre-copy UI, have mutually exclusive checkboxes or radio buttons
(i) verify no files
(ii) verify every file after each copy (the default), and 
(iii) verify only files < 1GB after each copy (using a global constant instead of a fixed 1GB threshold)

2.2 After copying, walk the files in fixed-size windows (e.g., 8–64 MiB), comparing windowed chunks,
(i.e. omit a hashing scheme) and compare each window during the windowed mmap compare.
(perhaps maybe permits early failing when aa window mismatch occurs).
Fallback: if a mmap window read fails (e.g., on exotic FS), then automatically fall back to plain buffered compare for a window.
This gives OS-paged reads (4 KiB pages) without loading the whole file, works well on memory-constrained PCs,
and is faster than read() the entire file into Python buffers for large files, as well as avoids "==" on
full bytes objects for big files which forces full file reads/materialization in RAM and can thrash memory.

2.3 If later in the development cycle want to implement a hash method (perhaps ?blake3?, refer B.1.2 below and use the same type of hash),
allow in the structure provision for computing the source hash during the windowed mmap copy and then in post-copy for
computing the target hash with a separate windowed mmap parse of the closed-then-reopened target, then compare the hashes. 

2.4 Progress bar: advance by the window size after each compare window; easy to wire (into tqdm or) your own UI eg tkinter.

B) Across networks / NAS / SMB
------------------------------
1. Copy first
1.1. Copy using (non-mmap) chunked I/O or whatever the best copy method is under network circumstances. 
1.1.1 Over networks/SMB/NAS, we could still use CopyFileExW (Windows lets it stream), 
1.1.2 HOWEVER in this networking case the CopyFileExW method requires an additional costly-for-large-networked-files full-file-read:
[read source, write target, re-read-source for verify, re-read-target for verify, compare computed hash]
vs chunked I/O copying whilst calculating the source hash on the fly which has 
[read source and calculate hash on the fly, write target, re-read-target for verify, compare computed hash]

1.2 during copying of source->target, perform progressive calculation of the source hash using ?blake3?
(?BLAKE3? was said to be much faster than SHA-512?) or whatever is fastest on a >=5yo cpu given that the sole aim is
to ensure the copied target file has content identical to the source, using whatever the best copy method
is under network circumstances. 

2. Verify with chunked I/O
2.1 In the pre-copy UI, have mutually exclusive checkboxes or radio buttons
(i) verify no files
(ii) verify every file after each copy (the default), and 
(iii) verify only files < 1GB after each copy (using a global constant instead of a fixed 1GB threshold)

2.3 For post-copy hashing calculation of the target, prefer buffered chunked I/O over mmap for
target verification (e.g., 1–8 MiB chunks) to avoid pathological page-fault latency over the network stack.
Then compare the hashes. Or suggest a better method.

2.4 Progress bar: advance by the window size after each compare window; easy to wire into our own UI eg tkinter.
```
