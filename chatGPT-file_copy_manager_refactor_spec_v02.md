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

This expanded spec includes **appendices with Windows constants, structures, and callback types** for developer reference, cross-referenced in sections 5–7 (copy, verify, cancellation).

