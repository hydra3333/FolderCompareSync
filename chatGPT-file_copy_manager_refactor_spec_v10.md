# FileCopyManager Refactor Technical Specification (v9)

---

## Overview
This document defines the complete technical specification for the refactor of `FileCopyManager_class`. It consolidates all requirements, decisions, and implementation details agreed upon during discussions. The specification aims to ensure clarity, completeness, and consistency for developers implementing or maintaining the system.

---

## Goals (High-Level)
- **R.1**: Safe copying with notification and status returns if errors or cancelled by user.
- **R.2**: Copying of date-time metadata (created/modified) with allowance for setting afterward.
- **R.3**: Efficient (fast) copying and verifying.
- **R.4**: Progress updates via Tkinter.
- **R.5**: Efficient verification to guarantee identical file contents and rollback if issues occur.
- **R.6**: Well-named global parameters for thresholds (copy/verify chunk sizes, etc).
- **R.7**: Safety of target files with rollback if copy/verify fails.
- **R.8**: Replacement `FileCopyManager_class` must remain close to drop-in compatible with old module.
- **R.9**: Well-commented code (function-level and block-level).
- **R.10**: Best-practice coding, especially in tight loops (copy, verify, hashing).

---

## Mandatory Requirements
1. **Copy strategy thresholds**:
   - `FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3` (2 GiB).
   - `FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3` (20 GiB).
   - Above max → fail with user-facing error.

2. **Verification**:
   - Policy constant: `FILECOPY_VERIFY_POLICY = 'lt_threshold'`.
   - Options: `none | all | lt_threshold (default)`.
   - Threshold constant: `FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3` (2 GiB).
   - Implementation:
     - Direct mode (< threshold): mmap windowed verify.
     - Staged mode (≥ threshold): chunked verify.
     - Hashing with **BLAKE3**, fallback to buffered byte-compare.
     - *Removed*: size-only verification.

3. **Cancel latency targets**:
   - Direct verify window: `FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2` (64 MiB).
   - Staged copy/verify chunk: `FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2` (4 MiB).
   - Cancel latency ≤ 200–320ms worst case.

4. **UNC path policy**:
   - Hard reject UNC paths in UI and in engine.
   - User must map drive letters.
   - Local path normalization: add `\?\` prefix for long-path support.

5. **Backup/rollback**:
   - Always use backup-rename, never overwrite in place.
   - On failure/cancel → restore backup automatically.
   - On success+verify → delete backup permanently (no recycle bin).

6. **Low-space checks**:
   - Local: require free space ≥ `file_size + backup_size + margin`.
   - Margin: `FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2` (64 MiB).
   - Network: attempt `GetDiskFreeSpaceExW`; if not available, warn but continue.

7. **Sparse handling**:
   - Detect sparse attribute.
   - Global: `FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True`.
   - Warn once per file if sparse → proceed content-identical.

8. **UI alignment**:
   - Remove “overwrite” option.
   - Replace with “Replace with backup/rollback” semantics.

9. **Metadata**:
   - Always preserve created/modified timestamps.
   - Use `FileTimestampManager_class` functions.

10. **Compatibility**:
    - Preserve class/method signatures where possible.
    - New functionality exposed via constants and controlled policy.

---

## High-Level Process Walkthrough (Direct vs Staged)

File copying in **FolderCompareSync** follows one of two strategies — **DIRECT** or **STAGED** — selected automatically from file size and whether a network drive is involved. The system guarantees **safe, verifiable copying with rollback**, so no partial or corrupted file ever replaces a valid destination.

### Common Preflight (both strategies)
1. **Reject UNC** paths and normalize long local paths with `\?\` as needed.
2. **Check size caps**: abort if `size > FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES` (20 GiB).
3. **Free-space check**: require `free_space ≥ file_size + backup_size + FILECOPY_FREE_DISK_SPACE_MARGIN` (64 MiB). For network shares, attempt the check; warn if not available.
4. **Backup existing target** (if it exists): rename atomically to `target.~bak` to enable rollback. From this point, the visible destination filename is free to be replaced safely on success.

---

### A. DIRECT copy (Local HDD/SSD → HDD/SSD on same machine)
**When used:** Local paths (no network) **and** `size < FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES` (2 GiB).

**Copy phase:**
- Create a temporary file next to the destination (e.g., `target.copying.tmp`).
- Use Windows `CopyFileExW` to copy **source → temp** with OS-level buffering and a progress callback. UI progress updates per callback tick.

**Verification phase:**
- Compare **source vs temp** using windowed `mmap` reads of `FILECOPY_MMAP_WINDOW_BYTES` (64 MiB). Early-exit on mismatch.
- Fallback: if `mmap` read fails, compare the current window with buffered `read()`.
- Respect the global verify policy (`FILECOPY_VERIFY_POLICY`: `none | all | lt_threshold`).
- UI shows verification progress by advancing one window per tick.

**Commit / Rollback:**
- **Success**: atomically replace the destination name with the temp file, then delete the `~bak` backup; re-apply timestamps if needed.
- **Failure or cancel**: delete the temp file and **restore** `target.~bak` to the original name; report error/cancel to UI.

---

### B. STAGED copy (Network/NAS/SMB or Large Files)
**When used:** Network path involved **or** `size ≥ FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES` (2 GiB).

**Copy phase (with inline hashing):**
- Create `target.copying.tmp` next to destination.
- Read source in chunks of `FILECOPY_NETWORK_CHUNK_BYTES` (4 MiB), writing to temp, and simultaneously update a rolling **source hash** (BLAKE3 preferred; if unavailable, we still copy and will fall back to byte-compare during verify).
- UI progress updates once per chunk.

**Verification phase (hash-based):**
- Re-read the temp file in the same chunk size to compute **target hash**.
- Compare `source_hash == target_hash`.
- If BLAKE3 library is not available, perform chunked byte-compare (`FILECOPY_NETWORK_CHUNK_BYTES`).
- Verification policy obeys `FILECOPY_VERIFY_POLICY`.

**Commit / Rollback:**
- **Success**: atomically swap temp into the destination name; delete `~bak`; re-apply timestamps if needed.
- **Failure or cancel**: delete temp; **restore** `target.~bak` to original name; surface a clear error/cancel.

---

### Key Safety & UX Principles
- **Never overwrite in place**: all writes target a `.copying.tmp`. The visible name is only updated after successful verification.
- **Rollback guarantee**: an existing destination is first moved to `~bak` and restored on any failure/cancel.
- **Progress visibility**: both copy and verify feed progress—per callback (DIRECT) or per chunk/window (STAGED & DIRECT verify).
- **Sparse awareness**: detect `FILE_ATTRIBUTE_SPARSE_FILE`; warn once and proceed (content-identical copy; sparseness not preserved yet).
- **Clear messaging**: all failures (UNC rejected, size cap, low space, network errors, mismatches) produce user-facing messages.

---

## Implementation Strategy
- **Copy engine**:
  - < threshold → direct `CopyFileExW` with cancel callback.
  - ≥ threshold → staged chunked copy loop.
  - Cancel checks per window/chunk.
- **Verify engine**:
  - Direct: mmap windowed byte-compare.
  - Staged: BLAKE3 hash compare, fallback to byte-compare.
- **Rollback**:
  - Always rename destination → `.backup` before writing.
  - If fail, restore `.backup` → original.
  - If success, delete `.backup`.
- **Error handling**:
  - Raise `FileCopyError` with user-readable messages.
  - Return status to UI.
- **Tkinter integration**:
  - Progress updates each window/chunk.
  - Cancel flag bound to UI button.

---

## Global Constants
```python
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3      # 2 GiB
FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3      # 20 GiB
FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2                 # 64 MiB
FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2                # 4 MiB
FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3             # 2 GiB
FILECOPY_VERIFY_POLICY = 'lt_threshold'                   # none | all | lt_threshold (default)
FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2            # 64 MiB
FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True             # Warn if sparse detected
```

---

## Error Reporting & Logging
- Log at INFO level for start/end, WARN for recoverable, ERROR for abort.
- User-facing messages must be clear and reference rollback status.
- Sparse warnings: once per file.

---

## Appendices

### Appendix F: Code Fragments & Examples
- **Windows API Imports**
```python
from ctypes import windll, wintypes
kernel32 = windll.kernel32
CopyFileExW = kernel32.CopyFileExW
GetDiskFreeSpaceExW = kernel32.GetDiskFreeSpaceExW
SetFileTime = kernel32.SetFileTime
```

- **Cancel Callback Signature**
```python
def cancel_callback(total_bytes_transferred, bytes_per_second, user_data):
    if user_cancelled:
        return 1  # nonzero = cancel
    return 0
```

- **Rollback Example**
```python
backup_path = target_path + ".backup"
os.rename(target_path, backup_path)
try:
    do_copy(...)
    verify(...)
    os.remove(backup_path)
except Exception:
    os.rename(backup_path, target_path)
    raise
```

- **Free Space Check**
```python
def check_free_space(path, required):
    free = wintypes.ULARGE_INTEGER()
    if not GetDiskFreeSpaceExW(path, None, None, byref(free)):
        logger.warning("Free space check unavailable on network")
        return True
    return free.value >= required + FILECOPY_FREE_DISK_SPACE_MARGIN
```

### Appendix G: Version History
- **v1 → v2**: Initial restructuring, added constants.
- **v2 → v3**: Integrated cancel-latency guidance, UNC policy.
- **v3 → v4**: Sparse handling decision added.
- **v4 → v5**: Low-space check logic.
- **v5 → v6**: Cleanup, overwrite mention removed in answers (but not fully).
- **v6 → v7**: Clarified mandatory requirements; unified constants naming.
- **v7 → v8**: Added goals vs mandatory reqs separation.
- **v8 → v9**: Added Appendix F (code), Appendix G (version history); ensured overwrite fully removed; integrated rollback logic; clarified verify fallback; cleaned inconsistencies.

---

**End of Document**

