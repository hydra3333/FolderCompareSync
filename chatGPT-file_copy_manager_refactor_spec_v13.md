# FileCopyManager Refactor – Technical Specification (v12)

---

## Developer Quickstart (Onboarding)

Welcome! This module implements **safe, efficient file copying** with **verification** and **guaranteed rollback**. Start here:

1) **Two strategies, auto-selected**
- **DIRECT** (local + smaller files): Uses `CopyFileExW` (fast, kernel-level) and **mmap** windowed verify.
- **STAGED** (network or larger files): Chunked copy with **BLAKE3** hashing and hash-verify.

2) **Rollback is always on**
- We never overwrite in place. We back up any existing target, copy to a temp name, verify, then atomically swap on success.
- On cancel/failure, partial temp is deleted and original target is restored automatically.

3) **Verification policy (UI)**
- `none` | `all` | `lt_threshold` (default). Threshold = 2 GiB.
- DIRECT verifies via mmap; STAGED verifies via hash (BLAKE3 → fallback byte-compare).

4) **Key constants (tune as needed)**
- `FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 GiB`
- `FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES  = 20 GiB`  (hard stop)
- `FILECOPY_MMAP_WINDOW_BYTES            = 64 MiB`    (DIRECT verify window)
- `FILECOPY_NETWORK_CHUNK_BYTES          = 4 MiB`     (STAGED copy/verify chunk)
- `FILECOPY_VERIFY_THRESHOLD_BYTES       = 2 GiB`
- `FILECOPY_VERIFY_POLICY                = 'lt_threshold'`
- `FILECOPY_FREE_DISK_SPACE_MARGIN       = 64 MiB`
- `FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING= True`

5) **Understand the flow**
- Read the **High‑Level Process Walkthrough** right below. Then see **Appendix F** (code fragments) for ctypes/API details.

---

## Project Goals (R.1 – R.10)

- **R.1** Safe copying with notification and status returns if errors and/or cancelled by user.  
- **R.2** Copy date-time metadata (Created/Modified) with allowance for setting afterward.  
- **R.3** Efficient (fast) copying and verifying.  
- **R.4** Progress updates via Tkinter.  
- **R.5** Very efficient verification to guarantee identical file contents, with rollback if anything is astray.  
- **R.6** Well-named Global Parameters controlling thresholds for sizing and for chunked/windowed copying and verification.  
- **R.7** Safety of target files: if a copy or verify fails, guarantee rollback to original state.  
- **R.8** Replacement `FileCopyManager_class` should be reasonably close to “drop-in compatible.”  
- **R.9** Well-commented code (function-level and code-block level where appropriate).  
- **R.10** Best-practice coding, especially in tight copy/verify/hash loops.

---

## Mandatory Requirements

- **No overwrite mode:** Always backup-rename first; never write into the visible name until verification passes.  
- **Verification required:**  
  - DIRECT → mmap windowed compare (fallback: buffered compare).  
  - STAGED → BLAKE3 hash compare (fallback: chunked byte-compare).  
  - Size-only verification is **not** permitted as a final method.  
- **UNC policy:** UNC paths are **rejected** at both UI and engine; require mapped drive letters instead.  
- **Long-path support:** Normalize local paths with `\\?\` where needed; still reject UNC.  
- **Free-space preflight:** Require `free ≥ file_size + backup_size + FILECOPY_FREE_DISK_SPACE_MARGIN`. Network check is best-effort; warn if unknown.  
- **Sparse awareness:** Detect `FILE_ATTRIBUTE_SPARSE_FILE`; if `FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING=True`, warn once per file; proceed content-identical (sparse-preserving copy is out of scope for v12).  
- **Backup deletion:** After a successful verify and atomic finalize, delete backup **permanently** (no Recycle Bin).  
- **Metadata:** Preserve Created/Modified timestamps using `FileTimestampManager_class`.  
- **Hard size stop:** Refuse to copy files larger than `FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES` (20 GiB).  
- **Compatibility:** Preserve public surface and return types where possible; changes documented here.

---

## Decision Matrix (Strategy Selection)

| Location          | Size vs Threshold                     | Strategy |
|------------------|----------------------------------------|----------|
| Local            | `< 2 GiB` (below threshold)            | DIRECT   |
| Local            | `≥ 2 GiB` (at/above threshold)         | STAGED   |
| Network (mapped) | **Any**                                | STAGED   |

---

## High‑Level Process Walkthrough (Direct vs Staged)

### Common Preflight
1. Validate inputs; **reject UNC** and normalize long local paths with `\\?\`.  
2. Enforce **hard size stop** (20 GiB).  
3. **Free-space**: require `free ≥ file_size + backup_size + margin` (64 MiB). For network shares, attempt `GetDiskFreeSpaceExW`; warn if not available.  
4. If destination exists, **atomically rename** it to `target.~bak` (enables rollback). Create `target.copying.tmp` as the temp output.

### A) DIRECT Copy (Local + below threshold)
- **Copy:** Use `CopyFileExW` to copy **source → temp** with OS progress callbacks.  
- **Verify:** Windowed **mmap** compare using `FILECOPY_MMAP_WINDOW_BYTES` (64 MiB). Early-exit on mismatch; fallback to buffered compare if mmap fails. Obey `FILECOPY_VERIFY_POLICY` (none | all | lt_threshold).  
- **Finalize (success):** Atomically swap temp into the visible name; delete `~bak`; re-apply timestamps as needed.  
- **Rollback (failure/cancel):** Delete temp; restore `~bak` to original name; surface clear error/cancel to UI.

### B) STAGED Copy (Network or ≥ threshold)
- **Copy (with inline hashing):** Read source in `FILECOPY_NETWORK_CHUNK_BYTES` (4 MiB), write to temp, and update a rolling **source hash** (BLAKE3 preferred; if unavailable we still copy). UI updates once per chunk.  
- **Verify:** Re-read temp using same chunk size to compute **target hash**. Compare `source_hash == target_hash`. If `blake3` is unavailable, perform **chunked byte-compare**. Obey `FILECOPY_VERIFY_POLICY`.  
- **Finalize / Rollback:** Same as DIRECT.

**Safety principles:** Never write into the visible name; always temp + verify + atomic finalize. On any failure/cancel, rollback guarantees the original remains intact.

---

## Public API Contract (Minimal Surface)

```python
class FileCopyManager:
    def copy_file(self, src: str, dst: str) -> "CopyOperationResult":
        """
        Copy a single file with full backup/rollback semantics and verification.
        - Raises FileCopyError on fatal errors (UI should translate to messages).
        - Returns a structured result including strategy, verify mode, bytes, and timing.
        """
        ...

class CopyOperationResult(TypedDict):
    status: Literal["ok", "cancelled", "error"]
    success: bool
    strategy_used: Literal["DIRECT", "STAGED"]
    verification_mode: Literal["none", "all", "lt_threshold"]
    verification_passed: bool
    bytes_total: int
    bytes_copied: int
    duration_seconds: float
    error_code: int | None
    error_message: str | None
```

**Breaking changes:** None intended. “Overwrite” parameters/options have been removed from UI and code. Behavior is now always *backup/rollback*.

---

## Global Constants

```python
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3      # 2 GiB
FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3      # 20 GiB
FILECOPY_MMAP_WINDOW_BYTES            = 64 * 1024**2      # 64 MiB (DIRECT verify window)
FILECOPY_NETWORK_CHUNK_BYTES          = 4 * 1024**2       # 4 MiB (STAGED copy/verify)
FILECOPY_VERIFY_THRESHOLD_BYTES       = 2 * 1024**3       # 2 GiB verify threshold
FILECOPY_VERIFY_POLICY                = 'lt_threshold'    # none | all | lt_threshold (default)
FILECOPY_FREE_DISK_SPACE_MARGIN       = 64 * 1024**2      # 64 MiB free space margin
FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING= True              # Warn once per sparse file
```

> Place these in `FolderCompareSync_Global_Constants.py`. Use `*_BYTES` suffix for clarity. Document trade‑offs (cancel granularity vs throughput) directly above the constants.

---

## Edge Cases & Policies

- **Locked files (sharing violations):** Fail with clear message.  
- **Existing read‑only target:** Fail (surface to UI).  
- **Path case differences:** Treat comparisons case-insensitively (NTFS‑like), but preserve original case in filenames.  
- **UNC paths:** Reject with actionable guidance (“Map a drive letter first”).  
- **Long local paths:** Normalize with `\\?\` to avoid MAX_PATH issues (still reject UNC).  
- **Low space:** Preflight check on local; best-effort on network; abort with guidance if insufficient.  
- **Sparse files:** Warn if detected; proceed content-identical (sparseness not preserved in v12).  
- **Partial network failures / SMB reconnect:** Treat as failure; rollback; surface network guidance to user.

---

## Verification (Detailed)

- **DIRECT**: mmap windowed byte-compare; fallback to buffered compare per window on mmap error.  
- **STAGED**: BLAKE3 hash compare; if `blake3` not importable, fallback to chunked byte-compare.  
- **Policy (`FILECOPY_VERIFY_POLICY`)**:  
  - `none` → skip verify entirely.  
  - `all` → verify every file.  
  - `lt_threshold` (default) → verify only files `< FILECOPY_VERIFY_THRESHOLD_BYTES` (2 GiB).  
- **Progress integration:** UI updated per window (DIRECT) or per chunk (STAGED).  
- **Zero false positives:** Any mismatch causes immediate rollback and a clear error.

---

## Backup / Rollback Workflow (Detailed)

1. **If destination exists**, atomically rename it to `target.~bak`; record original timestamps.  
2. **Copy to temp** (`target.copying.tmp`).  
3. **Verify** (per strategy/policy).  
4. **Failure/cancel**: delete temp if present.  
   - If `~bak` exists, **restore** it to the original name and **reapply timestamps**.  
5. **Success**: atomically swap temp into the destination name; delete `~bak` permanently.  
6. **Crash/restart hygiene**: stale `.copying.tmp` or `.~bak` files are cleaned on the next run (best-effort).

---

## Windows API Centralization (Appendix D)

Centralize all ctypes bindings in `FolderCompareSync_Global_Imports.py` for consistency and debuggability:

- `CopyFileExW` (with `PROGRESS_ROUTINE` signature)  
- `GetDiskFreeSpaceExW`  
- `CreateFileW`, `SetFileTime`, `CloseHandle`, `GetLastError`  
- Common constants: `FILE_ATTRIBUTE_SPARSE_FILE`, `FILE_ATTRIBUTE_NORMAL`, `FILE_FLAG_BACKUP_SEMANTICS`, `GENERIC_WRITE`, `FILE_SHARE_*`, `OPEN_EXISTING`, etc.

> This avoids drift between modules and ensures consistent `argtypes`/`restype` definitions.

---

## Helper Function Skeletons (Appendix E)

```python
def _execute_direct_strategy(src, dst, progress_cb, cancel_event) -> CopyOperationResult: ...
def _execute_staged_strategy(src, dst, progress_cb, cancel_event) -> CopyOperationResult: ...
def _verify_by_mmap(src, tmp, progress_cb, cancel_event) -> bool: ...
def _verify_by_hash_or_compare(src, tmp, progress_cb, cancel_event) -> bool: ...
def _create_backup_if_exists(dst) -> str | None: ...
def _restore_backup(backup_path: str | None, dst: str) -> bool: ...
def _finalize_success(tmp: str, dst: str, backup_path: str | None) -> None: ...
def _preserve_timestamps(src: str, dst: str) -> bool: ...
def _check_free_space(path: str, required: int) -> bool: ...
```

Each helper is unit-testable in isolation; orchestrator paths cover success/failure/rollback flows.

---

## Code Fragments & Examples (Appendix F)

```python
# Windows API imports
from ctypes import wintypes, windll, byref, POINTER, Structure, WinDLL
kernel32 = windll.kernel32

# FILETIME structure
class FILETIME(Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD)]

# Progress callback type (prototype)
# PROGRESS_ROUTINE = WINFUNCTYPE(DWORD, LARGE_INTEGER, LARGE_INTEGER, ...)

# CopyFileExW flags and constants (subset)
COPY_FILE_FAIL_IF_EXISTS  = 0x00000001
COPY_FILE_RESTARTABLE     = 0x00000002
FILE_ATTRIBUTE_SPARSE_FILE= 0x00000200
FILE_ATTRIBUTE_NORMAL     = 0x00000080
FILE_FLAG_BACKUP_SEMANTICS= 0x02000000
GENERIC_READ              = 0x80000000
GENERIC_WRITE             = 0x40000000
OPEN_EXISTING             = 3
```

Additional snippets: Tkinter progress wiring, cancel flag polling, free-space preflight wrapper.

---

## Hashing Options (Appendix H)

**BLAKE3** (default for STAGED verify)  
- *Pros*: Extremely fast, SIMD/parallel; cryptographic-grade; reduces total time for network scenarios.  
- *Cons*: Extra dependency (`blake3` package).

**SHA‑256 / SHA‑512** (fallback crypto)  
- *Pros*: Built-in `hashlib`; SHA‑512 can outperform SHA‑256 on x64.  
- *Cons*: Slower than BLAKE3.

**Byte‑compare** (fallback or DIRECT verify)  
- *Pros*: Guarantees identity; no dependency; often fastest locally (mmap).  
- *Cons*: Re-reads entire target; no digest reuse.

**Recommendation**:  
- DIRECT → **mmap byte-compare**.  
- STAGED → **BLAKE3**; fallback to chunked byte-compare if unavailable.

---

## Version History (Appendix G – always last)

**v1 → v4** – Early drafts exploring DIRECT/STAGED, verification, and UI progress.  
**v5** – Introduced constants, low-space preflight, temp+rollback pattern.  
**v6** – Stronger structure (requirements, decision matrix, appendices with Windows constants).  
**v7** – Removed overwrite semantics; clarified rollback universality; ban size-only verify.  
**v8** – Separated **Goals** vs **Mandatory Requirements**; improved consistency.  
**v9** – Added appendices (code fragments), clearer spec structure.  
**v10** – Added **Developer Quickstart** and long **English Walkthrough**; strengthened rollback text.  
**v11** – Expanded appendices (API centralization, helper skeletons), ensured UNC rejection + long-path handling.  
**v12** – This version: starts from v10, re-incorporates relevant v6 detail (decision matrix, edge cases, full constants/API notes), keeps onboarding/walkthrough, removes size-only verify and overwrite everywhere, and consolidates hashing guidance.
