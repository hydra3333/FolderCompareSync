# FileCopyManager Refactor – Technical Specification (v08)

---

## 1. Introduction
This document specifies the design and requirements for the **refactored FileCopyManager_class module**. It consolidates all prior discussions, Q&A decisions, and mandatory requirements into a single authoritative reference. The intent is to ensure that implementation is consistent, safe, efficient, and developer-friendly.

---

## 2. Project Goals
The following goals (R.1 – R.10) represent the high-level objectives that guide the design of the refactored module:

- **R.1**: Safe copying with notification and status returns if errors and/or cancelled by user.  
- **R.2**: Copying of date-time metadata (date-created and date-modified), with allowance for setting afterward.  
- **R.3**: Efficient (fast) copying and verifying.  
- **R.4**: Progress updates via Tkinter.  
- **R.5**: Very efficient (fast) verification to guarantee identical file contents, with a rollback mechanism if something is astray.  
- **R.6**: Well-named Global Parameters controlling thresholds for sizing and for chunked (or windowed) copying and verification.  
- **R.7**: Safety of target files: if a copy or verify fails, guarantee rollback of the target file to its original state.  
- **R.8**: A replacement FileCopyManager_class module must be reasonably close to drop-in compatible with the old module.  
- **R.9**: Well-commented code, both at function level and at code block level.  
- **R.10**: Due regard to best practice coding, especially where speed is essential (tight copy loops, verification loops, hashing loops, etc.).  

---

## 3. Mandatory Requirements
These requirements are binding and must be fully implemented:

- **No Overwrite Mode**: Overwrite semantics are removed. All copies proceed via *backup-rename, copy, verify, rollback on failure*. UI and code must not reference overwrite.
- **Metadata Preservation**: Copy both `creation` and `modification` timestamps. Use `FileTimestampManager_class` for platform-specific calls.
- **Verification Policy**: Must guarantee byte-identical verification. Hash-compare or mmap-windowed compare are valid; size-only compare is disallowed.
- **Rollback Safety**: If copy or verification fails, target must be restored from backup.
- **Cancel Responsiveness**: Windowed mmap (DIRECT) and chunked staged copy (STAGED) must honor cancellation quickly (<250ms typical).
- **Network vs Local Policy**:
  - UNC paths: hard reject at UI *and* engine.
  - Long local paths: normalize to `\\?\` form internally.
- **Backup Deletion**: Backups are deleted permanently after successful verify. No Recycle Bin option.
- **Low-space Preflight**: Require free space ≥ `new_file_size + backup_size + margin (64MiB)`. If check fails, abort with user-facing message. Network free-space check best-effort.
- **Sparse Handling**: Detect sparse attribute. Warn user once per file if sparse, then proceed with content-identical copy (sparseness not preserved).
- **Verification Options**: UI exposes `verify_policy = {none | all | lt_threshold}`. Default = `lt_threshold`. Threshold = 2 GiB.
- **Fallbacks**:
  - If BLAKE3 unavailable, fallback to chunked byte-compare.
  - If mmap fails (Win32 errors, e.g. low memory), fallback to buffered compare.

---

## 4. Global Constants
All thresholds, margins, and chunk sizes are defined in one place (`FolderCompareSync_Global_Constants.py`).

```python
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3   # 2 GiB, switch DIRECT vs STAGED
FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES  = 20 * 1024**3  # 20 GiB, hard stop
FILECOPY_MMAP_WINDOW_BYTES             = 64 * 1024**2  # 64 MiB DIRECT verify window
FILECOPY_NETWORK_CHUNK_BYTES           = 4 * 1024**2   # 4 MiB STAGED copy/verify chunk
FILECOPY_VERIFY_THRESHOLD_BYTES        = 2 * 1024**3   # 2 GiB verify threshold for lt_threshold policy
FILECOPY_VERIFY_POLICY                 = 'lt_threshold' # {none|all|lt_threshold}, default = lt_threshold
FILECOPY_FREE_DISK_SPACE_MARGIN        = 64 * 1024**2  # 64 MiB free space margin
FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True          # Warn on sparse file detection
```

---

## 5. Copying Strategy
### 5.1 DIRECT Copy (local, small/medium files)
- Use `CopyFileExW` if available; otherwise fallback to read/write loop.
- Verify via `mmap` windowed compare (64 MiB default).
- Cancel responsive.

### 5.2 STAGED Copy (network, large files)
- Chunked read/write using 4 MiB chunks.
- Verify via BLAKE3 hash; fallback to chunked byte-compare.
- Cancel responsive.

### 5.3 Threshold Switching
- If file_size < `FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES`: DIRECT strategy.
- Else: STAGED strategy.

### 5.4 Hard Stop
- Abort with user-facing message if file_size > `FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES`.

---

## 6. Verification
- **Primary**: BLAKE3 hash (fast, parallelizable).
- **Fallback**: chunked byte-compare (same cadence).
- **Direct**: mmap windowed compare.
- **UI**: expose verify options (none | all | lt_threshold).
- **Size-only verification**: explicitly disallowed.

---

## 7. Rollback
- Before copy, rename target (if exists) → backup name.
- On success: delete backup permanently.
- On failure: restore backup.
- Rollback must survive power loss mid-operation where possible.

---

## 8. Low-space Enforcement
- Preflight check: free space ≥ `file_size + backup_size + margin`.
- Margin defined by `FILECOPY_FREE_DISK_SPACE_MARGIN`.
- If check fails, abort with clear error.
- For network: warn if free space cannot be queried.

---

## 9. UI / UX
- **Progress**: updates via Tkinter progress bar, windowed for responsiveness.
- **Messages**: clear, user-facing errors for: UNC rejection, path too long, free space failure, over max file size.
- **Verify Options**: exposed as drop-down or radio buttons (none | all | lt_threshold).
- **Cancel**: immediate responsiveness (<250ms typical).
- **No Overwrite**: UI text must not contain overwrite semantics; replaced with *Replace (with backup/rollback)*.

---

## 10. Developer Notes
- **Windows API Centralization**: All kernel32 calls (`CopyFileExW`, `GetDiskFreeSpaceExW`, `SetFileTime`, etc.) are centralized in a helper module. Constants like `FILE_ATTRIBUTE_SPARSE_FILE` are defined there.
- **Cross-Platform**: Non-Windows implementations may fallback to Python I/O and `os`/`shutil` primitives.
- **Testing**: unit tests must simulate cancel, low-space, sparse file, and UNC rejection scenarios.

---

## Appendix A – Windows Constants
```python
FILE_ATTRIBUTE_SPARSE_FILE = 0x200
FILE_ATTRIBUTE_NORMAL      = 0x80
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
GENERIC_READ  = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
```

---

## Appendix B – API Centralization Example
```python
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# CopyFileExW
def copy_file_ex(src, dst, progress_routine, cancel_flag):
    return kernel32.CopyFileExW(
        wintypes.LPCWSTR(src),
        wintypes.LPCWSTR(dst),
        progress_routine,
        None,
        ctypes.byref(cancel_flag),
        0
    )
```

---

## Appendix C – Error Handling Patterns
- Always capture `ctypes.get_last_error()` after failed API calls.
- Log both numeric error and formatted message.
- Surface clear, user-facing messages in Tkinter dialogs.

---

## Appendix D – Verification Fallback Notes
- If BLAKE3 not importable: auto-switch to chunked byte-compare.
- If `mmap` fails: fallback to buffered compare.
- Always log which fallback path was taken.

---

## Appendix E – Cancel Handling
- Cancel flag must be polled every chunk/window.
- UI cancel sets global atomic flag.
- Copy/verify loops check flag and abort gracefully if set.

---

## 11. Conclusion
This specification (v08) integrates all prior requirements, goals, and design decisions. It ensures:
- Safety first (rollback, no overwrite).
- Efficiency (windowed mmap, BLAKE3, chunking).
- Developer clarity (constants centralized, API centralized, appendices for reference).
- User clarity (UI aligned, clear error messages, fast cancel).

Implementation should now proceed directly against this specification.

