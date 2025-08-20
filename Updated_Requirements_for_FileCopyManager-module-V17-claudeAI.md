# FileCopyManager Refactor Plan - Complete Implementation Strategy

## Executive Summary

Create a drop-in replacement for `FileCopyManager_class` that maintains full API compatibility while implementing modern copy strategies, enhanced verification, and simplified architecture. The refactor preserves the dual-strategy approach but streamlines implementation and adds Windows native APIs for performance.

## Requirements Mapping (R.1-R.6)

### R.1: Safe Copying with Notifications & Status
- **Enhanced error handling**: Structured results with Win32 error codes where applicable
- **Cancellation support**: Threading.Event-based cancellation for all copy/verify operations
- **Rollback capability**: Maintain backup/restore logic for staged operations
- **Status reporting**: Rich status messages via callback without touching tkinter directly

### R.2: Metadata Preservation
- **Files**: `CopyFileExW` preserves most metadata; follow with explicit `SetFileTime` for guarantees
- **Directories**: Centralize timestamp copying in the manager (instead of GUI calling timestamp_manager directly)
- **Verification**: Ensure creation/modification times are preserved correctly

### R.3: Efficient Copying
- **Local drives**: Windows `CopyFileExW` with kernel-level buffering
- **Network/SMB**: Chunked copy with configurable buffer sizes
- **Strategy selection**: Maintain DIRECT/STAGED approach based on file size and location

### R.4: Progress Updates via Tkinter
- **Copy progress**: `CopyFileExW` progress callback feeds thread-safe queue
- **Verify progress**: Windowed progress updates during verification
- **Thread isolation**: Manager pushes to queue, GUI pumps via `root.after()`

### R.5: Very Efficient Verification
- **Local files**: Windowed mmap byte-compare (16MB windows)
- **Network files**: BLAKE3 hash comparison or buffered chunk compare
- **Fallback**: Buffered comparison when mmap fails
- **Multiple modes**: NONE | SIZE | MMAP | HASH based on file characteristics

### R.6: Configurable Verification Threshold
- **Threshold-based**: Verify files < 1GB by default, configurable via global constants
- **Mode selection**: 'none' | 'all' | 'lt_threshold'
- **Per-file decision**: Based on size and location characteristics

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

#### 2. Windows Native API Integration
- **CopyFileExW**: Primary copy method for local drives
- **SetFileTime**: Explicit timestamp preservation after copy
- **Progress callbacks**: Native progress reporting during copy operations
- **Error handling**: Capture and translate Win32 error codes

#### 3. Enhanced Verification System
- **Multiple verification modes**:
  - `NONE`: Skip verification entirely
  - `SIZE`: Size-only check (current behavior)
  - `MMAP`: Memory-mapped byte comparison for local files
  - `HASH`: BLAKE3 hash comparison for network files
- **Automatic mode selection**: Based on file size, location, and global settings
- **Windowed processing**: Bounded memory usage for large files

#### 4. Reduced Logging Verbosity
- **Essential messages only**: Eliminate granular step-by-step logging
- **Structured reporting**: Clear start/success/failure messages
- **Error focus**: Detailed logging only for errors and critical operations
- **Performance tracking**: Summary statistics without noise

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

# Metadata operations
def _preserve_timestamps(src, dst, dry_run) -> bool
def _get_file_times(path) -> Tuple[datetime, datetime, datetime]
def _set_file_times(path, created, modified, accessed) -> bool

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

#### DIRECT Strategy (Enhanced)
- **Local files**: `CopyFileExW` with progress callback
- **Network files**: Chunked copy with inline hash (option B1)
- **Metadata**: `SetFileTime` after copy for timestamp guarantees
- **Verification**: Size check or mmap compare based on global settings
- **Progress**: Real-time updates during copy operation

#### STAGED Strategy (Streamlined)
- **Backup approach**: Maintain rename-to-backup for safety
- **Copy operation**: Same as DIRECT strategy
- **Rollback logic**: Simplified error recovery with explicit cleanup
- **Verification**: Enhanced verification before backup removal
- **Progress**: Combined copy + verify progress reporting

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

### Enhanced Copy Operation Flow

#### For Local Files:
1. **Validate inputs** and check cancellation
2. **Select strategy** based on file size and characteristics
3. **Setup backup** (STAGED only) with atomic rename
4. **Copy file** using `CopyFileExW` with progress callback
5. **Set timestamps** explicitly via `SetFileTime`
6. **Verify copy** using mmap comparison or size check
7. **Cleanup backup** (STAGED only) or rollback on failure
8. **Report results** with detailed statistics

#### For Network Files:
1. **Validate inputs** and check cancellation
2. **Select strategy** and verification mode
3. **Setup backup** (STAGED only)
4. **Chunked copy** with optional inline BLAKE3 hashing
5. **Set timestamps** via `SetFileTime`
6. **Verify copy** using hash comparison or chunk compare
7. **Cleanup/rollback** as needed
8. **Report results** with network-specific metrics

### Progress Integration

#### Copy Progress:
- **Native progress**: `CopyFileExW` PROGRESS_ROUTINE callback
- **Chunked progress**: Per-chunk updates for network operations
- **Thread-safe queue**: Progress data pushed to queue, GUI pulls via `root.after()`
- **Cancellation**: Check cancellation event in progress callback

#### Verification Progress:
- **Windowed updates**: Progress per mmap window or hash chunk
- **Combined reporting**: Single progress stream for copy + verify phases
- **Time estimation**: ETA calculation based on throughput

### Error Handling Strategy

#### Structured Results:
```python
@dataclass
class CopyOperationResult:
    status: str  # 'ok' | 'cancelled' | 'error'
    success: bool  # For backward compatibility
    strategy_used: CopyStrategy
    bytes_total: int
    bytes_copied: int
    verification_mode: str  # 'none' | 'size' | 'mmap' | 'hash'
    verification_passed: bool
    error_code: int  # Win32 error code when applicable
    error_message: str
    duration_seconds: float
    # ... existing fields preserved
```

#### Error Recovery:
- **Automatic fallbacks**: mmap → buffered compare, CopyFileExW → chunked copy
- **Detailed diagnostics**: Win32 error codes and system error messages
- **Rollback guarantees**: Atomic operations with cleanup on failure

### Performance Optimizations

#### Memory Management:
- **Bounded windows**: Fixed memory usage regardless of file size
- **Lazy allocation**: Allocate verification buffers only when needed
- **Resource cleanup**: Explicit cleanup of mmap handles and buffers

#### I/O Efficiency:
- **Kernel-level copy**: `CopyFileExW` for maximum throughput
- **Sequential access**: Optimize for disk/network access patterns
- **Minimal reads**: Inline hashing to avoid redundant source reads

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