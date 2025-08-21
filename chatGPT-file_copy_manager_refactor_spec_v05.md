# FileCopyManager Refactor – Technical Specification

## 1. Overview
**Goal:** Provide a safe, efficient, developer-friendly file copy manager for Windows (Python 3.13+), with robust verification, rollback, and UI progress updates.

**Scope:**
- Copy files between folder trees with metadata preservation (Created/Modified timestamps).
- Verification policies (none, all, lt_threshold).
- Robust rollback with backups.
- Support for both local and network file copies.
- Efficient cancel and progress mechanisms.

**Out-of-scope:**
- ACLs, SIDs, ADS, reparse points, symlinks, read-only targets.
- Sparse file preservation beyond warning.
- Non-Windows platforms.

---

## 2. Definitions
- **DIRECT strategy**: Local, below threshold → use `CopyFileExW` with mmap verify.
- **STAGED strategy**: File ≥ threshold or any network drive → chunked copy + hash verify.
- **Verify Policy**: `'none' | 'all' | 'lt_threshold'`.
- **Backup/rollback**: Always backup existing targets before overwrite, restore on failure/cancel.

---

## 3. Decision Matrix
| File Location | File Size | Strategy  |
|---------------|-----------|-----------|
| Local, < threshold | Small | DIRECT |
| Local, ≥ threshold | Large | STAGED |
| Network (any size) | Any | STAGED |

---

## 4. Public API Contract
### Methods
- `copy_file(src, dst, overwrite=True)` → `CopyOperationResult`
- `determine_copy_strategy(src, dst, size)` → `DIRECT | STAGED`
- `cancel_copy(event)`

### Return type `CopyOperationResult`
- `status`: 'ok' | 'cancelled' | 'error'
- `success`: bool (GUI compatibility)
- `bytes_total, bytes_copied`
- `error_code, error_message`
- `strategy_used, verification_mode, verification_passed`
- `duration_seconds`

**Breaking changes:** None. Drop-in compatibility preserved.

---

## 5. Copy Algorithms

**Note:** Windows API bindings (CopyFileExW, SetFileTime, etc.) are centralized in Appendix D. Refer there for `PROGRESS_ROUTINE` signature and constants when implementing low-level helpers.
### DIRECT (local, small)
1. Backup target if exists (atomic rename).
2. `CopyFileExW` with progress callback.
3. `SetFileTime` for timestamps.
4. Verify with mmap windows.
5. On success → delete backup permanently.
6. On fail/cancel → delete bad copy, restore backup + timestamps.

### STAGED (large or network)
1. Backup target if exists (atomic rename).
2. Chunked copy (4 MiB default) with inline BLAKE3 hash.
3. `SetFileTime` for timestamps.
4. Verify by computing target hash and comparing.
5. On success → delete backup permanently.
6. On fail/cancel → delete bad copy, restore backup + timestamps.

---

## 6. Verification Algorithms
- **DIRECT**: Windowed mmap compare (`FILECOPY_MMAP_WINDOW_BYTES`, default 64 MiB). Fallback: buffered compare if mmap fails.
- **STAGED**: Hash verify (BLAKE3). Fallback: buffered chunk compare (same chunk size).
- **Verify Policy**:
  - `none`: skip verify
  - `all`: verify every file
  - `lt_threshold`: verify only files < threshold (default)

Progress increments per window/chunk. Cancel granularity tied to chunk/window size.

---

## 7. Progress & Cancellation
- Progress via `CopyFileExW` callback or chunk loop.
- Updates queued to Tkinter every 50 ms.
- Cancel checked at each chunk/window.
- Expected cancel latency:
  - DIRECT: ≤ 0.5 s worst-case (64 MiB @ 120 MB/s HDD).
  - STAGED: ≤ 0.32 s worst-case (4 MiB @ 12.5 MB/s, 100 Mbit/s).

---

## 8. Metadata Handling

**Note:** Timestamps are preserved via `SetFileTime`; see Appendix D for centralized Windows API bindings and correct `FILETIME` handling.
- Preserve: CreationTime, ModificationTime.
- Out-of-scope: ACLs, SIDs, ADS, symlinks, attributes.
- Fail copy if unsupported metadata encountered.

---

## 9. Config & Defaults
```python
# FileCopyManager configuration constants
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3      # 2 GiB
FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3      # 20 GiB hard stop
FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2                 # 64 MiB (DIRECT verify)
FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2                # 4 MiB (STAGED copy/verify)
FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3             # 2 GiB verify threshold
FILECOPY_VERIFY_POLICY = 'lt_threshold'                   # none | all | lt_threshold (default)
FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2            # 64 MiB
FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True             # Warn once per sparse file
```

Notes:
- Constants in `*_BYTES` form for clarity.
- Cancel latency trade-offs explained in comments.

---

## 10. Edge Cases
- **UNC paths**: Rejected at UI and engine. Users must map drives.
- **Long paths**: Normalize with `\\?\` prefix for local drive letters.
- **Locked files**: Fail with clear message.
- **Read-only targets**: Fail.
- **Low disk space**: Preflight check (local = enforce, network = attempt then warn).
- **Sparse files**: Warn if detected, proceed with content copy only.
- **Partial network failures**: Fail with error message.

---

## 11. Performance Targets & Test Plan
- Local throughput: maximize via native APIs.
- Network copies: minimize redundant reads (3× file size max).
- Verification false positives: 0.
- UI updates: 0.2–60 Hz cadence.
- Debug logging: commented-out hooks in hot loops for perf troubleshooting.

---

## 12. Migration Notes
- API compatibility preserved.
- Overwrite semantics removed from UI; always backup/rollback instead.
- Constants renamed to `FILECOPY_*` form for clarity.

---

## Appendix A: Windows API Constants & Structures

To aid developers, the following Windows-specific constants and structures are relevant:

```python
# Windows File Attributes
generate_sparse = 0x200  # FILE_ATTRIBUTE_SPARSE_FILE

# CopyFileExW flags
COPY_FILE_FAIL_IF_EXISTS = 0x00000001
COPY_FILE_RESTARTABLE   = 0x00000002
COPY_FILE_OPEN_SOURCE_FOR_WRITE = 0x00000004
COPY_FILE_ALLOW_DECRYPTED_DESTINATION = 0x00000008

# FILETIME structure
typedef struct _FILETIME {
    DWORD dwLowDateTime;
    DWORD dwHighDateTime;
} FILETIME;

# Progress callback routine type for CopyFileExW
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

# Copy progress callback reasons
CALLBACK_CHUNK_FINISHED = 0x00000000
CALLBACK_STREAM_SWITCH  = 0x00000001
CALLBACK_ERROR_OCCURRED = 0xFFFFFFFF
```

### Notes for Developers
- `CopyFileExW` is the preferred API for DIRECT strategy due to kernel-level optimizations.
- Sparse detection: check `FILE_ATTRIBUTE_SPARSE_FILE` flag.
- Timestamps: use `SetFileTime` to guarantee Created/Modified preservation.

Reference these when implementing low-level bindings or troubleshooting.

---

## Appendix B: Rollback Workflow
1. If target exists, backup via atomic rename.
2. On failure/cancel:
   - If target didn’t exist: delete bad copy.
   - If target existed: delete bad copy, restore backup, reset timestamps.
3. On success: delete backup permanently.

---

## Appendix C: Developer Guidance
- Place constants in `FolderCompareSync_Global_Constants.py`.
- Centralize Windows API bindings in `FolderCompareSync_Global_Imports.py`.
- Document cancel latency rationale in comments above constants.
- Keep debug logging in hot loops commented out, with clear notes on re-enabling.

---

## Appendix D: Windows API Centralization (from prior spec)

Centralize Windows API bindings used by **FileCopyManager** and **FileTimestampManager** in `FolderCompareSync_Global_Imports.py` for consistency and easier maintenance. This mirrors the prior "Windows API Centralization" guidance and remains relevant.

```python
# Windows API bindings shared by FileCopyManager and FileTimestampManager
# ... (see full ctypes structures and constants above) ...
```

**Why keep this centralized?**
- Eliminates duplication and drift between modules.
- Ensures consistent `argtypes/restype` for correctness and better debugging.
- Keeps platform checks in one place.

**Cross-references:**
- Used in §5 (Copy Algorithms) and §8 (Metadata Handling).
- Complements `FileTimestampManager_class`’s proper FILETIME usage.

**Future extensions:**
- Add FSCTL support (e.g., `FSCTL_SET_SPARSE`) to preserve sparseness when implemented.
- Consider adding wrappers for `GetDiskFreeSpaceExW` for preflight free-space checks.
- Extend with recycle-bin deletion via Windows Shell API if ever required.

---

## Appendix E: Helper Function Skeletons (from prior spec)

For maintainability and testing, internal helpers are broken down into small, focused functions. These skeletons from the prior spec remain relevant as developer guidance.

```python
# Copy operations
def _copy_local_file(src, dst, progress_callback, cancel_event) -> CopyResult:
    pass

def _copy_network_file(src, dst, progress_callback, cancel_event) -> CopyResult:
    pass

def _create_directory_path(path, dry_run) -> bool:
    pass

# Verification operations
def _verify_by_size(src, dst) -> bool:
    pass

def _verify_by_mmap(src, dst, progress_callback, cancel_event) -> bool:
    pass

def _verify_by_hash(src, dst, progress_callback, cancel_event) -> bool:
    pass

# Metadata operations (delegating to FileTimestampManager_class)
def _preserve_timestamps(src, dst) -> bool:
    pass

def _validate_timestamp_preservation(src, dst) -> bool:
    pass

# Backup/restore operations
def _create_backup(target_path, dry_run) -> Optional[str]:
    pass

def _restore_backup(backup_path, target_path, dry_run) -> bool:
    pass

def _cleanup_backup(backup_path, dry_run) -> bool:
    pass

# Strategy coordination
def _execute_direct_strategy(src, dst, overwrite, progress_cb, cancel_event) -> CopyOperationResult:
    pass

def _execute_staged_strategy(src, dst, overwrite, progress_cb, cancel_event) -> CopyOperationResult:
    pass
```

**Notes for developers:**
- Each helper should be small and testable in isolation.
- Orchestration happens in the public API (`copy_file`), which calls `_execute_*_strategy`.
- Rollback logic should be invoked consistently inside `_execute_*_strategy`.

---


---

## Appendix E: Helper Function Skeletons (modular layout)

These skeletons illustrate the intended modular breakdown and are referenced by §5–§7. They are **non-executable** templates for developers to flesh out.

```python
# --- Copy operations --------------------------------------------------------

def _copy_local_file(src: str, dst: str, progress_cb, cancel_event) -> "CopyResult":
    """DIRECT copy using CopyFileExW + callback routing to progress_cb.
    - Should raise on fatal errors, return structured result otherwise.
    - Check cancel_event in callback (map to PROGRESS_CANCEL).
    """
    ...


def _copy_network_file(src: str, dst: str, progress_cb, cancel_event) -> "CopyResult":
    """STAGED copy using buffered chunked I/O (FILECOPY_NETWORK_CHUNK_BYTES).
    - Compute inline BLAKE3 of source during copy.
    - Report progress per chunk; respect cancel_event.
    """
    ...


def _create_directory_path(path: str, dry_run: bool) -> bool:
    """Ensure parent directories exist; return True if ready or dry-run."""
    ...

# --- Verification operations ------------------------------------------------

def _verify_by_size(src: str, dst: str) -> bool:
    """Optional quick check: compare file sizes only (when policy permits)."""
    ...


def _verify_by_mmap(src: str, dst: str, progress_cb, cancel_event) -> bool:
    """DIRECT verification: windowed mmap compare with fallback to buffered compare.
    - Window size: FILECOPY_MMAP_WINDOW_BYTES.
    - Progress per window; bail early on mismatch; respect cancel_event.
    """
    ...


def _verify_by_hash(src: str, dst: str, progress_cb, cancel_event) -> bool:
    """STAGED verification: compute target BLAKE3 and compare to source_hash.
    - Chunk size: FILECOPY_NETWORK_CHUNK_BYTES.
    - Fallback when BLAKE3 unavailable: buffered byte-compare.
    - Progress per chunk; respect cancel_event.
    """
    ...

# --- Metadata operations ----------------------------------------------------

def _preserve_timestamps(src: str, dst: str) -> bool:
    """Use FileTimestampManager to copy Created/Modified (see §8, Appendix D)."""
    ...


def _validate_timestamp_preservation(src: str, dst: str) -> bool:
    """Optional post-check to assert timestamps copied correctly."""
    ...

# --- Backup/restore operations (applies to DIRECT & STAGED) -----------------

def _create_backup(target_path: str, dry_run: bool) -> str | None:
    """If target exists, atomically rename to a temp backup name and return it."""
    ...


def _restore_backup(backup_path: str | None, target_path: str, dry_run: bool) -> bool:
    """Restore backup by atomic rename back to the original name; return success."""
    ...


def _cleanup_backup(backup_path: str | None, dry_run: bool) -> bool:
    """Delete backup permanently after success (no recycle bin)."""
    ...

# --- Strategy coordination --------------------------------------------------

def _execute_direct_strategy(src: str, dst: str, overwrite: bool,
                             progress_cb, cancel_event) -> "CopyOperationResult":
    """Compose DIRECT steps:
    backup→copy(local)→timestamps→verify(mmap)→cleanup/rollback.
    """
    ...


def _execute_staged_strategy(src: str, dst: str, overwrite: bool,
                             progress_cb, cancel_event) -> "CopyOperationResult":
    """Compose STAGED steps:
    backup→copy(network+inline_hash)→timestamps→verify(hash)→cleanup/rollback.
    """
    ...

# --- Public API orchestration ----------------------------------------------

def copy_file(src: str, dst: str, overwrite: bool) -> "CopyOperationResult":
    """Validate inputs, enforce policy (UNC reject, size caps, free-space),
    select strategy, then call the appropriate executor; handle exceptions and
    ensure rollback semantics per Appendix B.
    """
    ...


def determine_copy_strategy(src: str, dst: str, size: int) -> str:
    """Return 'DIRECT' or 'STAGED' per matrix in §3 using FILECOPY_* constants."""
    ...
```

**Notes:**
- These are structural guides; actual implementations should call into the
  centralized Windows bindings (Appendix D) and respect constants from §9.
- Keep unit tests focused on each helper (I/O and error paths), with orchestrator
  tests exercising success/failure/rollback flows.

