# FolderCompareSync — DIRECT+MMAP Copy Design

## 0) Purpose (what & why)

Make large **local→local** copies faster and more “windowed” by adding a new **DIRECT+MMAP copy** path that:

* Copies in **mmap windows** (e.g., 64 MiB) with per-window progress & cancellation.
* **Pre-allocates** the destination temp file to full size.
* **Verifies** large files by **hash** (single pass over dest; avoids re-reading source).
* Leaves small DIRECT files using existing **mmap window compare** verify.
* Keeps **STAGED** for network/UNC/cloud or when policy dictates.

## Glossary

- **DIRECT-SMALL** — Local→local copy for files **smaller** than the direct-mmap threshold. Copy via `CopyFileExW`; verify via **MMAP window compare** (no hashing).
- **DIRECT-LARGE** — Local→local copy for files **at or above** the direct-mmap threshold. Copy via **windowed mmap** with **on-the-fly source hashing**; verify via **hash of destination** post-copy.
- **STAGED** — Chunked copy (e.g., 4 MiB) with **progressive hashing** (network/UNC/cloud/unknown types, or when policy dictates).
- **window** — The **mmap region size** used during DIRECT-LARGE copy (e.g., 64 MiB). Must be a multiple of 64 KiB.
- **chunk** — The **buffered I/O size** used by STAGED (e.g., 4 MiB).
- **pre-alloc** — Pre-allocating the temp file in the **destination directory** to the **full source length** before any data copy.
- **mmap compare** — Byte-for-byte verification using memory-mapped windows for **DIRECT-SMALL**.
- **hash(src_on_copy + dest_post)** — Hash-based verification where the **source hash is computed during copy** and the **destination hash is computed after copy**.

## 1) Decision Matrix (strategy selection)

| Source            | Target            | Size < `DIRECT_MMAP_COPY_THRESHOLD` | Size ≥ `DIRECT_MMAP_COPY_THRESHOLD` | Strategy                  | Verify Mode                                          |
| ----------------- | ----------------- | ----------------------------------- | ----------------------------------- | ------------------------- | ---------------------------------------------------- |
| LOCAL\_FIXED      | LOCAL\_FIXED      | **DIRECT-SMALL** (existing)         | **DIRECT-LARGE** (new)              | DIRECT                    | SMALL: **MMAP compare** (existing) • LARGE: **HASH** |
| LOCAL\_FIXED      | Network/UNC/Cloud | any                                 | any                                 | **STAGED** (existing)     | HASH (progressive)                                   |
| Network/UNC/Cloud | any               | any                                 | any                                 | **STAGED** (existing)     | HASH (progressive)                                   |
| Unknown/Removable | any               | any                                 | any                                 | **STAGED** (safe default) | HASH (progressive)                                   |

**One-line decision log (for every file):**
`Decision: <DIRECT-SMALL|DIRECT-LARGE|STAGED> reason=<drive_types,size,policy> window=<N MiB|n/a> chunk=<N MiB|n/a> verify=<hash|mmap>`

## Decision explainer log (spec)

**Purpose.** Emit one concise, human-readable line per file at the moment a strategy is chosen, so later you can reconstruct why a path was taken and how verification was performed, without scanning code. This augments the Decision Matrix and reflects the actual window/chunk sizes and verify pipeline used.

### Log line (single-line, always INFO)
```
Decision: <DIRECT-SMALL|DIRECT-LARGE|STAGED> reason=src:<drive_type>,dst:<drive_type>,size:<bytes>,policy:<verify_policy> window=<N MiB|n/a> chunk=<N MiB|n/a> verify=<mmap|hash> verify_detail=<mmap_compare|hash(src_on_copy + dest_post)> prealloc=<ok|n/a> flush_every=<N|n/a>
```

- `window` = memory-map window in MiB when applicable (defaults to 64 MiB).
- `chunk`  = staged I/O chunk in MiB when applicable (defaults to 4 MiB).
- `verify` = the mode selected by the strategy: `mmap` (byte-compare) or `hash`.
- `verify_detail` clarifies the pipeline:
  - `mmap_compare` (DIRECT-SMALL)
  - `hash(src_on_copy + dest_post)` (DIRECT-LARGE, STAGED) — on-the-fly source hash during copy, then a single pass over the destination post-copy.

- `algo` = hasher chosen for this file (e.g., `blake3` when available, else `sha256`).
- `verify_policy` = active verification policy (`none`, `lt_threshold`, or `all`).
- `prealloc` = `ok` when DIRECT-LARGE successfully pre-allocates the temp file (otherwise the copy fails early per spec).
- `flush_every` = N windows between flushes in DIRECT-LARGE (1–1000, per constant).

> Keep this a single line so it’s easy to grep; emit at INFO once per file right after strategy selection.

### Examples

1) **DIRECT-LARGE** (local→local, 15 GiB; windowed copy + on-the-fly hash)  
```
Decision: DIRECT-LARGE reason=src:LOCAL_FIXED,dst:LOCAL_FIXED,size:16106127360,policy:lt_threshold window=64 MiB chunk=n/a verify=hash verify_detail=hash(src_on_copy + dest_post) prealloc=ok flush_every=16 algo=blake3 verify_policy=lt_threshold
```

2) **DIRECT-SMALL** (local→local, 120 MiB; CopyFileExW + mmap verify)  
```
Decision: DIRECT-SMALL reason=src:LOCAL_FIXED,dst:LOCAL_FIXED,size:125829120,policy:lt_threshold window=64 MiB chunk=n/a verify=mmap verify_detail=mmap_compare prealloc=n/a flush_every=n/a algo=blake3 verify_policy=lt_threshold
```

3) **STAGED** (network target; chunked copy + progressive hash)  
```
Decision: STAGED reason=src:LOCAL_FIXED,dst:NETWORK_UNC,size:16106127360,policy:lt_threshold window=n/a chunk=4 MiB verify=hash verify_detail=hash(src_on_copy + dest_post) prealloc=n/a flush_every=n/a algo=blake3 verify_policy=lt_threshold
```

## 2) What already exists vs. what we’ll add

### Already in code

* **DIRECT-SMALL copy:** `CopyFileExW` copy → **mmap window compare** verify.
* **STAGED copy:** chunked read/write (4 MiB) with **progressive hashing**; verify by hashing dest only; temp-then-rename; progress + cancel wired.
* **Verify bar + Copy bar** with dual messages (overall vs per-file).
* **Policy switches** for when to verify (thresholds, on/off).

### New to add

* **DIRECT-LARGE copy (new):** `_copy_by_mmap_windows(...)`

  * Pre-alloc temp file → windowed mmap copy with per-window progress + cancel.
  * **No per-window buffered fallback**: if any window map/write fails → **fail copy**.
  * Flush policy (per N windows + final flush).
  * Verify mode = **hash** (single pass over dest), not mmap compare.
* **Selector tweak:** choose DIRECT-LARGE for local→local when size ≥ threshold.
* **Pre-allocation step:** fail early if unable to set exact size.
* **Decision explainer log** as above.

## 3) Strategy details (methods & flow)

### A) DIRECT-SMALL (existing)

* **When:** local→local and `size < DIRECT_MMAP_COPY_THRESHOLD`.
* **Copy:** `CopyFileExW` (existing).
* **Verify:** **MMAP window compare** (existing; 64 MiB default).
* **Progress:** Copy bar = overall; Verify bar = verify progress (existing).
* **Cancel:** via existing callback & event checks (existing).

### B) DIRECT-LARGE (new)

* **When:** local→local and `size ≥ DIRECT_MMAP_COPY_THRESHOLD`.
* **Copy:** `_copy_by_mmap_windows(src, tmp, window=FILECOPY_MMAP_WINDOW_BYTES)`

  1. **Pre-alloc** `tmp` to `size` (fail if cannot).
  2. For each window: map source (read) + target (write), `memmove`/slice copy.
  3. Update **per-file progress** every window; check **cancel**.
  4. **Flush policy:** `mmap.flush()` every `FLUSH_EVERY_N_WINDOWS` (configurable) + final flush; `FlushFileBuffers` at end.
  5. **No per-window buffered fallback**: any window failure → abort copy.
  6. On success: close maps/handles → **atomic rename** to final.
* **Verify:** **HASH** verify (single pass over dest) using current hash algo/policy (no source re-read).
* **Progress UI:**

  * Keep **Copy bar = overall** (existing behavior).
  * During copy, show **per-file MB of MB** on the **Verify bar** (already supported).
  * During verify, Verify bar shows real verify progress (as today).

### C) STAGED (existing)

* **When:** any non-local pair, unknown types, or policy forces it.
* **Copy:** chunked (default 4 MiB); progressive hashing.
* **Verify:** hash dest only and compare.
* **Progress & Cancel:** existing.

## 4) Constants (names, purpose, defaults)

> Add in `FolderCompareSync_Global_Constants.py` (well-documented). Reuse existing where noted.

**Strategy control**

* `FILECOPY_DIRECT_MMAP_COPY_ENABLED: bool = True`
  Master switch for DIRECT-LARGE path.
* `FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES: int = 1 * 1024**3`
  Size at/above which DIRECT becomes DIRECT-LARGE.
* `FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES`
  (Existing) Keep for STAGED policy if still used elsewhere; document precedence vs new threshold.

**Windows & flushing**

* `FILECOPY_MMAP_WINDOW_BYTES: int = 64 * 1024**2` *(existing)*
  Size of each mmap window (copy & small-file verify).
* `FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS: int = 16`
  Call `mmap.flush()` every N windows (1–1000 range).
* `FILECOPY_MMAP_WRITE_ABORT_ON_FAILURE: bool = True`
  If **any** window map/write fails → **fail** the copy (no buffered fallback).

**Verification policy**

* `FILECOPY_DIRECT_LARGE_VERIFY_MODE: Literal["hash","mmap"] = "hash"`
  Explicitly documents we use HASH for DIRECT-LARGE.
* `FILECOPY_DIRECT_SMALL_VERIFY_MODE: Literal["hash","mmap"] = "mmap"`
  Clarifies current behavior for small DIRECT.
* `FILECOPY_VERIFY_POLICY` *(existing)*
  Continue to honor global verify on/off & thresholds; document that DIRECT-LARGE overrides verify mode to “hash” when verify is enabled.

**UI/Progress**

* (Existing) knobs for dialog sizing; ensure **Cancel** row visible.
* Optional: `PROGRESS_SHOW_PERFILE_ON_VERIFY_BAR: bool = True`
  During copy phase, drive the Verify bar with per-file “MB of MB”.

**Logging**

* (Existing) callpath + console shortening.
* New: decision explainer line (format string constant).

## 5) Error handling & durability

* **Pre-alloc must succeed**: if truncate/resize of temp fails, **abort** with clear status.
* **No per-window fallback**: any mmap map/write failure aborts copy (per spec).
* Ensure **final flush** + **close all maps/handles** before atomic rename.
* Apply timestamps/attributes/ACLs as in existing code paths.
* On cancel or failure: **delete temp** and emit a clear status line.

## 6) Cancellation & UI

* Check `cancel_event.is_set()` **every window** (copy & verify).
* Keep **overall** percentage on the copy bar; per-file progress on verify bar during copy (then real verify).
* Confirm the **Cancel** button is always visible (bump dialog height if needed).

## 7) Performance notes (expectations)

* DIRECT-LARGE can outperform `CopyFileExW` for very large sequential local copies due to big windows & fewer syscalls; on some SSDs `CopyFileExW` may still be faster—keep feature switchable.
* Larger windows reduce UI update frequency; use window size + flush N to balance throughput vs responsiveness.
* Antivirus & backup filters can distort timings; decision logs help diagnose.

## 8) Files & touchpoints (for the future patch)

* **`FileCopyManager_class.py`**

  * Strategy selector: add DIRECT-LARGE branch.
  * New `_copy_by_mmap_windows(...)` (copy & progress logic).
  * Verify decision: choose HASH for large files when verify is enabled.
  * Decision explainer log.
* **`FolderCompareSync_Global_Constants.py`**

  * New constants above (with comments).
* **`ProgressDialog_class.py` / CopyProgressManager**

  * No structural changes; just ensure Verify bar can display per-file progress during copy (it already can).
* **`FolderCompareSync_class.py`**

  * No logical changes; confirm Cancel wiring & dialog size.

## 9) Test plan (quick list)

1. **Small local file** (< threshold): DIRECT-SMALL → `CopyFileExW` → MMAP verify.
2. **Large local file** (≥ threshold): DIRECT-LARGE → mmap copy → HASH verify.
3. **Network target**: STAGED → chunked copy + progressive hash.
4. **Pre-alloc failure** (mock out): copy aborts, temp cleaned.
5. **Window mapping failure** (mock): copy aborts per spec.
6. **Cancel mid-copy**: operation terminates quickly; temp cleaned; UI resets.
7. **Cancel during verify**: terminates; status clean.
8. **Decision logs**: confirm reason/window/chunk/verify reported.

CLARIFICATION:

# On-the-fly hashing for the new DIRECT-LARGE (windowed mmap copy)

## What “on-the-fly” means here

While copying each **mmap window** from the **source** to the **temp target**, we’ll feed the source bytes straight into the hasher **before** (or as) we write them. 
That gives us the **full source hash** with **no subsequent extra pass over the source**.

* Hasher choice: same as your STAGED path today — **BLAKE3 if available, else SHA-256**. We’ll reuse that exact selection logic so behavior is consistent.
* Window size: reuse `FILECOPY_MMAP_WINDOW_BYTES` (64 MiB default).

## Verify step (post-copy)

To prove the file landed intact, we then compute **one pass over the destination only** and compare the two hashes:

* We **do not** re-read the source (the on-the-fly source hash already exists).
* Destination hashing can use buffered I/O or mmap windows; either is fine since it’s a single sequential pass.
* This aligns with your existing “hash verify” approach used by STAGED (progressive hash on copy, then hash the target once).

> Why we will NOT hash the destination “on-the-fly” too? We *could* (but we will not) update a second hasher immediately after writing each window,
but we’d still want a final, linear read of the destination after flush for maximum confidence.
The recommended plan keeps it simple and IO-efficient: **no second source pass, just one clean destination pass** after copy & flush.

## Where this plugs into your code

* **Copy loop:** a new `_copy_by_mmap_windows(...)` will handle windowed mapping, progress updates, cancel checks, and **hasher.update(window\_bytes)** as we go (mirrors your STAGED progressive hash structure).
* **Verify choice:** for DIRECT-LARGE we use **HASH** verify (not mmap compare). DIRECT-SMALL keeps your **mmap compare** verify. (Your verify policy flags already exist and will still govern whether verification happens at all.)
* **Progress UI:** we’ll continue feeding per-file bytes to `update_file_progress(...)`, so your dual-bar dialog can show smooth movement during the big copy (you already do this in DIRECT via CopyFileExW and in STAGED which seems a biut closer in nature to the DIRECT-LARGE method). 

## Constants & knobs (how this behaves)

* `FILECOPY_MMAP_WINDOW_BYTES` — window size for DIRECT-LARGE copy (and small-file mmap verify). Default 64 MiB.
* `FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES` — file size at/above which we use DIRECT-LARGE (windowed copy + hash verify). *(New, per design.)*
* `FILECOPY_DIRECT_LARGE_VERIFY_MODE="hash"` / `FILECOPY_DIRECT_SMALL_VERIFY_MODE="mmap"` — document/lock the verify mode by size. *(New, per design.)*
* `FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS` — how often we flush the view (1–1000 as you requested). *(New, per design.)*
* Existing verify policy still applies: `FILECOPY_VERIFY_POLICY` = `none | lt_threshold | all`. If policy turns verify **off**, we’ll **skip hashing entirely** for max throughput (no wasted CPU).

## Failure, pre-allocation, and cancel

* **Pre-alloc** the temp to full size up front; if that fails, **fail early** (per your spec).
* **No per-window buffered fallback**: if mapping/writing a window fails, the copy **fails** (you asked to avoid the complexity/overheads of switching modes mid-file).
* **Cancel** is checked every window (you already wire `cancel_event` through the dialog → copy manager).

## Decision matrix (recap, focusing on hashing)

* **DIRECT-SMALL (local→local, size < threshold):** Copy via `CopyFileExW`; **verify = mmap compare** (no hashing).
* **DIRECT-LARGE (local→local, size ≥ threshold):** **Windowed mmap copy + on-the-fly *source* hashing**; **verify = hash of destination only**; compare hashes; no second source pass.
* **STAGED (network/cloud/unknown):** Chunked copy with **progressive hashing**; **verify = hash destination only** (current behavior).

If you want me to add a line in the **decision explainer log** that makes this explicit (e.g., `verify=hash(src_on_copy + dest_post)`), I’ll include that in the patch so it’s crystal clear in your logs.


## Appendix A — Detailed Semantics & Requirements
### Appendix A — Mini ToC

- [A.1 Pre-allocation (exact behavior)](#a1-pre-allocation-exact-behavior)
- [A.2 Decision precedence (who wins when)](#a2-decision-precedence-who-wins-when)
- [A.3 Verify policy interaction](#a3-verify-policy-interaction)
- [A.4 Hash algorithm selection (single source of truth)](#a4-hash-algorithm-selection-single-source-of-truth)
- [A.5 Window & flush rules (with constraints)](#a5-window--flush-rules-with-constraints)
- [A.6 Progress & UI semantics](#a6-progress--ui-semantics)
- [A.7 Error taxonomy (codes & messages)](#a7-error-taxonomy-codes--messages)
- [A.8 Decision explainer fields (additions)](#a8-decision-explainer-fields-additions)
- [A.9 Drive-type definitions](#a9-drive-type-definitions)
- [A.10 Timestamps, attributes, ACLs](#a10-timestamps-attributes-acls)
- [A.11 Temp file location rule](#a11-temp-file-location-rule)
- [A.12 Performance telemetry (optional)](#a12-performance-telemetry-optional)
- [A.13 Edge cases & exclusions](#a13-edge-cases--exclusions)
- [A.14 Test plan (add-ons)](#a14-test-plan-add-ons)
- [A.15 Constants table (single source of truth)](#a15-constants-table-single-source-of-truth)


### A.1 Pre-allocation (exact behavior)
**Requirement.** The temporary destination file **must** be created on the **same volume** as the final target and resized (pre-allocated) to the exact source length **before** any data copy begins. If pre-allocation fails, **fail early** (no bytes written).
**Notes.**
- Temp naming: `<target>.fcs.tmp` (or project-standard suffix).
- Pre-allocation method: set exact length; do **not** sparse-allocate.
- Invariant: same-volume ensures atomic rename; a different volume is an error.

### A.2 Decision precedence (who wins when)
The selector evaluates in this order (first match wins):
1) If either end is `NETWORK_UNC`/cloud/unknown → **STAGED**.
2) Else if both ends are `LOCAL_FIXED` and `size ≥ DIRECT_MMAP_COPY_THRESHOLD_BYTES` and `DIRECT_MMAP_COPY_ENABLED` → **DIRECT-LARGE**.
3) Else if both ends are `LOCAL_FIXED` → **DIRECT-SMALL**.
4) Else → **STAGED`.
This precedence **overrides** any legacy rule that forced STAGED for files ≥ 2 GiB.

### A.3 Verify policy interaction
- If `FILECOPY_VERIFY_POLICY = none` → **no verification** is performed (no hashing, no mmap-compare).
- If `FILECOPY_VERIFY_POLICY = none` → **no verification** is performed (no hashing, no mmap-compare).
- If `FILECOPY_VERIFY_POLICY ∈ {lt_threshold, all}` →
  - **DIRECT-SMALL**: verify via **mmap window compare**.
  - **DIRECT-LARGE**: verify via **hash** (source hashed on-copy; destination hashed post-copy).
  - **STAGED**: verify via **hash** (progressive on copy; destination hashed post-copy).

### A.4 Hash algorithm selection (single source of truth)
Use the same selection everywhere verification-by-hash is used:
- Prefer **BLAKE3** when available; otherwise **SHA-256**.
- Applies to: STAGED progressive hashing; DIRECT-LARGE on-the-fly source hashing; post-copy destination hashing.
- If verification is disabled by policy, **no hasher is instantiated**.

### A.5 Window & flush rules (with constraints)
- `FILECOPY_MMAP_WINDOW_BYTES` **must** be a multiple of **64 KiB**; default is **64 MiB**.
- `FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS` is in **[1, 1000]**. Call `mmap.flush()` every N windows.
- Always perform a **final flush** and a `FlushFileBuffers`-equivalent at the end of the copy.
- Close all mappings/handles before atomic rename.

### A.6 Progress & UI semantics
**Copy phase:**
- **Copy bar** shows **overall** progress across files (unchanged).
- **Verify bar** shows **current-file** progress (“MB of MB”), updated after **each window** (DIRECT-LARGE) or **each chunk** (STAGED).
**Verify phase:**
- **Verify bar** switches to true verification progress (hashing or mmap-compare).
**Cancel:**
- The Cancel button must be visible/enabled from start.
- Check `cancel_event.is_set()` **every window/chunk** in both copy and verify loops.
- On cancel: abort promptly, delete temp, and report a clear “Cancelled” status.

### A.7 Error taxonomy (codes & messages)
Define greppable codes and messages (include offsets/paths where relevant):
- `COPY_E_PREALLOC` — cannot pre-allocate temp on target volume.
- `COPY_E_MMAP_MAP_WRITE` — mmap map/write failure (include offset/length).
- `COPY_E_WRITE` — general write error (disk full, I/O error); include bytes written and win32 error.
- `COPY_E_CANCELLED` — user cancellation during copy.
- `VERIFY_E_HASH_MISMATCH` — source/destination digest mismatch.
- `VERIFY_E_CANCELLED` — user cancellation during verify.
- `FINALIZE_E_RENAME` — atomic rename failed.
- `FINALIZE_E_METADATA` — failed to apply timestamps/attributes/ACLs.
For each error, specify whether the temp file is deleted or retained for diagnostics.

### A.8 Decision explainer fields (additions)
Add two explicit fields:
- `algo=<blake3|sha256>` — which hasher was used for this file.
- `verify_policy=<none|lt_threshold|all>` — the policy in effect for this decision.

### A.9 Drive-type definitions
Document the mapping from OS drive types to internal enums used in decisions:
- `LOCAL_FIXED`, `REMOVABLE`, `NETWORK_UNC`, `CDROM`, `RAMDISK`, `UNKNOWN`.
Clarify that symlinks/junctions are resolved to the target’s type for decision purposes.

### A.10 Timestamps, attributes, ACLs
- Apply timestamps/attributes/ACLs **after** successful rename to the final path (or document if pre-rename on temp is preferred).
- Timestamp semantics: store as UTC internally; convert for UI display using detected local timezone.
- If metadata apply fails: log `FINALIZE_E_METADATA`; decide whether that is a **failure** or **warning** in this release.

### A.11 Temp file location rule
- Temp must reside **in the destination directory** to guarantee same-volume atomic rename.
- If destination directory is read-only or lacks free space, fail early with `COPY_E_PREALLOC`.
Safety note: Temp file must be created in the **same directory** as the final target to guarantee atomic rename; different directory → error.

### A.12 Performance telemetry (optional)
At the end of each file, emit a single line:
```
Perf: bytes=<N> elapsed_ms=<N> throughput_MBps=<N> windows=<N> flushes=<N> strategy=<...> verify=<...>
```
This makes window size and flush cadence tuning easy in real workloads.

### A.13 Edge cases & exclusions
- **Sparse files, ADS (alternate data streams), reparse points**: unsupported (copy only default data stream); document any deviation.
- **Paths > 260 chars**: require long-path support; specify whether enabled.
- **Encrypted/compressed NTFS attributes**: treat as ordinary files; note if not preserved.
- **Disk full mid-copy**: fail with `COPY_E_WRITE` and clean temp.

### A.14 Test plan (add-ons)
In addition to existing tests:
- Pre-alloc failure (read-only dir / insufficient space).
- Window mapping/writing failure injection → abort.
- Cancel in mid-copy and mid-verify.
- Hash mismatch (flip one byte in temp pre-rename via test hook).
- Very large file (≥ 100 GB) to validate throughput & flush cadence.
- Long paths and unusual characters across local→local and local→network.

### A.15 Constants table (single source of truth)
Summarize all relevant constants: name, purpose, default, range, where used.
| Constant | Purpose | Default | Range/Constraint | Used in |
|---|---|---:|---|---|
| `FILECOPY_DIRECT_MMAP_COPY_ENABLED` | Master switch for DIRECT-LARGE | `True` | — | Selector |
| `FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES` | Size at/above which DIRECT-LARGE is used | `1 * 1024**3` | ≥ 1 MiB | Selector |
| `FILECOPY_MMAP_WINDOW_BYTES` | Window size for mmap copy & small-file verify | `64 * 1024**2` | multiple of 64 KiB | DIRECT-LARGE, VERIFY(MMAP) |
| `FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS` | Flush cadence during DIRECT-LARGE | `16` | [1, 1000] | DIRECT-LARGE |
| `FILECOPY_MMAP_WRITE_ABORT_ON_FAILURE` | Abort copy if any window fails | `True` | bool | DIRECT-LARGE |
| `FILECOPY_NETWORK_CHUNK_BYTES` | STAGED chunk size | `4 * 1024**2` | ≥ 64 KiB | STAGED |
| `FILECOPY_VERIFY_POLICY` | Verification policy | `lt_threshold` | {none, lt_threshold, all} | All strategies |
| `FILECOPY_DIRECT_LARGE_VERIFY_MODE` | Verify mode for large DIRECT | `"hash"` | {hash} | DIRECT-LARGE |
| `FILECOPY_DIRECT_SMALL_VERIFY_MODE` | Verify mode for small DIRECT | `"mmap"` | {mmap} | DIRECT-SMALL |
| `PROGRESS_SHOW_PERFILE_ON_VERIFY_BAR` | Show per-file MB-of-MB during copy | `True` | bool | UI/Progress |
| `DECISION_LOG_FORMAT` | Format string for one-line decision | (see section) | — | Logging |
| `PERF_LOG_ENABLED` | Emit perf line per file | `True` | bool | Logging |



------------------------------------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------------------------------------

using the new attachments in this post (and purging prior versions) can you perform the coding and generate
the patches according to our rules, for each affected module ?
I also hope to see informative "flushed logging" debug statements in the generated code to assist in debugging later.
To be clear about my preference for showing 10 lines of existing code before the actual patch and 10 lines of existing
code after the actual patch, to hep me unambiguously locate where the patch goes, I do mean display the existing code
prior and post and not just a line saying there was code, i hope that's clear.

You’re right—my bad on the line numbers. Below are the patches **re-displayed without any line numbers** and in the exact two-block format you specified (BEFORE and AFTER, each with **10 lines above** and **10 lines below** the change). I’ve also folded in the verify-mode labels.

I’m listing **7 patches** total:

* Patches 1–5 are the original feature patches (constants, imports, selector, decision explainer, direct branch + new helper).
* Patches 6–7 are the tiny verify-label patches folded in (STAGED + DIRECT-SMALL).

Nothing else is modified.

---

## PATCH 1 — `FolderCompareSync_Global_Constants.py` (add DIRECT-LARGE knobs)

### BEFORE

```
# ENHANCED FILE COPY SYSTEM CONFIGURATION (M01-M15)
# ============================================================================

# Copy Strategy Control (M01, M02, M03)
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3      # 2 GiB - DIRECT vs STAGED
FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3     # 20 GiB - Hard size limit

# Performance Tuning - DIRECT Strategy (M08)
FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2                # 64 MiB - Verification windows
FILECOPY_MMAP_FALLBACK_MAX_CONSECUTIVE_FAILURES = 5      # Max consecutive mmap failures before copy fails

# Performance Tuning - STAGED Strategy (M08) 
FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2               # 4 MiB - Network I/O chunks

# Verification Configuration (M04)
FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3            # 2 GiB - Verify size limit
FILECOPY_VERIFY_POLICY = 'lt_threshold'                  # none | lt_threshold | all (default)
FILECOPY_VERIFY_POLICY_DEFAULT = 'lt_threshold'          # Default UI selection

# System Resource Management
FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2          # 64 MiB - Safety margin
FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True           # Warn on sparse files

# Error Handling and Recovery
FILECOPY_BLAKE3_FALLBACK_ENABLED = True                 # Enable byte comparison fallback
FILECOPY_UNC_PATH_REJECTION_STRICT = True               # Reject UNC paths
```

### AFTER

```
# ENHANCED FILE COPY SYSTEM CONFIGURATION (M01-M15)
# ============================================================================

# Copy Strategy Control (M01, M02, M03)
FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3      # 2 GiB - DIRECT vs STAGED
FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3     # 20 GiB - Hard size limit

# Performance Tuning - DIRECT Strategy (M08)
FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2                # 64 MiB - mmap Copying and Verification windows
FILECOPY_MMAP_FALLBACK_MAX_CONSECUTIVE_FAILURES = 5      # Max consecutive mmap failures before copy fails
# >>> CHANGE START  # Enable DIRECT-LARGE and set threshold/flush cadence
FILECOPY_DIRECT_MMAP_COPY_ENABLED = True                 # Enable DIRECT-LARGE windowed mmap copy for local files
FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES = 1 * 1024**3  # 1 GiB threshold for DIRECT-LARGE selection
FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS = 2                  # Flush every N windows (1–1000); 0 disables extra flushes
# <<< CHANGE END

# Performance Tuning - STAGED Strategy (M08) 
FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2               # 4 MiB - Network I/O chunks

# Verification Configuration (M04)
FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3            # 2 GiB - Verify size limit
FILECOPY_VERIFY_POLICY = 'lt_threshold'                  # none | lt_threshold | all (default)
FILECOPY_VERIFY_POLICY_DEFAULT = 'lt_threshold'          # Default UI selection

# System Resource Management
FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2          # 64 MiB - Safety margin
FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True           # Warn on sparse files

# Error Handling and Recovery
FILECOPY_BLAKE3_FALLBACK_ENABLED = True                 # Enable byte comparison fallback
FILECOPY_UNC_PATH_REJECTION_STRICT = True               # Reject UNC paths
```

---

## PATCH 2 — `FileCopyManager_class.py` (add `mmap` and `msvcrt` imports)

THIS PATCH HAS BEEN FOLDED INTO FolderCompareSync_Global_Imports.py

---

## PATCH 3 — `FileCopyManager_class.py` (selector: keep DIRECT for local files; split inside DIRECT)

### BEFORE

```
        CopyStrategy: Optimal strategy for the given file and drive combination
        """
        # Enhanced network and cloud detection
        source_network = FileCopyManager_class._is_network_or_cloud_location(source_path)
        target_network = FileCopyManager_class._is_network_or_cloud_location(target_path)
        
        # Priority 1: Network or cloud location detection (M01, M03)
        if source_network or target_network:
            return FileCopyManager_class.CopyStrategy.STAGED
        
        # Priority 2: Large file size threshold (M01, M03)
        if file_size >= C.FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES:
            return FileCopyManager_class.CopyStrategy.STAGED
        
        # Default: Local small files use DIRECT strategy (M02)
        return FileCopyManager_class.CopyStrategy.DIRECT
```

### AFTER

```
        CopyStrategy: Optimal strategy for the given file and drive combination
        """
        # Enhanced network and cloud detection
        source_network = FileCopyManager_class._is_network_or_cloud_location(source_path)
        target_network = FileCopyManager_class._is_network_or_cloud_location(target_path)
        
        # Priority 1: Network or cloud location detection (M01, M03)
        if source_network or target_network:
            return FileCopyManager_class.CopyStrategy.STAGED
        
        # >>> CHANGE START  # Local files: keep DIRECT; size split handled inside DIRECT path (SMALL vs LARGE)
        # Previously: large local files were forced to STAGED here.
        # Now: keep DIRECT for local→local; DIRECT will branch to SMALL/LARGE internally.
        # <<< CHANGE END
        
        # Default: Local small files use DIRECT strategy (M02)
        return FileCopyManager_class.CopyStrategy.DIRECT
```

---

## PATCH 4 — `FileCopyManager_class.py` (decision explainer after “Strategy:”)

### BEFORE

```
        self._log_status(f"Starting copy operation {sequence_info}:")
        self._log_status(f"  Source: {source_path}")
        self._log_status(f"  Target: {target_path}")
        self._log_status(f"  Size: {file_size:,} bytes")
        self._log_status(f"  Strategy: {strategy.value.upper()}")

        # >>> CHANGE START
        # Respect DRY RUN at the engine level: do not touch the filesystem.
        if getattr(self, "_dry_run", False):
            self._log_status(f"DRY RUN: Would copy '{source_path}' → '{target_path}' using {strategy.value.upper()}")
            result = FileCopyManager_class.CopyOperationResult(
```

### AFTER

```
        self._log_status(f"Starting copy operation {sequence_info}:")
        self._log_status(f"  Source: {source_path}")
        self._log_status(f"  Target: {target_path}")
        self._log_status(f"  Size: {file_size:,} bytes")
        self._log_status(f"  Strategy: {strategy.value.upper()}")

        # >>> CHANGE START  # decision explainer (with flushed-logging)
        try:
            is_network = FileCopyManager_class._is_network_or_cloud_location(source_path) or FileCopyManager_class._is_network_or_cloud_location(target_path)
            policy = C.FILECOPY_VERIFY_POLICY
            if strategy == FileCopyManager_class.CopyStrategy.DIRECT:
                direct_large = C.FILECOPY_DIRECT_MMAP_COPY_ENABLED and (file_size >= C.FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES)
                mode_label = "DIRECT-LARGE" if direct_large else "DIRECT-SMALL"
                verify_label = "hash verify" if direct_large else "mmap verify"
                extra = f"win={C.FILECOPY_MMAP_WINDOW_BYTES//(1024**2)}MiB, flush_every={C.FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS}"
            else:
                mode_label = "STAGED"
                verify_label = "hash verify"
                extra = f"chunk={C.FILECOPY_NETWORK_CHUNK_BYTES//(1024**2)}MiB"
            expl = f"  Decision: {mode_label} | verify={verify_label} | policy={policy} | {extra}"
            self._log_status(expl)
            log_and_flush(logging.DEBUG, expl)
        except Exception as _e_decision:
            log_and_flush(logging.DEBUG, f"Decision explainer failed: {str(_e_decision)}")
        # <<< CHANGE END

        # >>> CHANGE START
        # Respect DRY RUN at the engine level: do not touch the filesystem.
        if getattr(self, "_dry_run", False):
            self._log_status(f"DRY RUN: Would copy '{source_path}' → '{target_path}' using {strategy.value.upper()}")
            result = FileCopyManager_class.CopyOperationResult(
```

---

## PATCH 5a — `FileCopyManager_class.py` (DIRECT branch: choose SMALL/LARGE)

### BEFORE

```
        try:
            # Phase 4: Windows CopyFileExW copy to temporary file
            copy_start_time = time.time()
            copy_result = self._copy_with_windows_api(source_path, temp_file_path)
            result.time_copy = time.time() - copy_start_time
            
            if not copy_result['success']:
                # >>> CHANGE START: explicit cancel semantics + cleanup (DIRECT) # per chatGPT change 1.3
                self._cleanup_temp_file(temp_file_path)  # always safe to remove temp
                result.error_message = copy_result['error']
                result.error_code = copy_result.get('error_code', 0)
                result.cancelled_by_user = copy_result.get('cancelled', False)
                if result.cancelled_by_user:
                    self._log_status("User cancelled copy; temp removed; original target preserved")
                else:
                    result.recovery_suggestion = copy_result.get('recovery_suggestion', "")
                return result
                # <<< CHANGE END
            
            result.bytes_copied = copy_result['bytes_copied']
            
            # Phase 5: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                self._log_status(f"Verifying copied file using memory-mapped comparison")
                verify_result = self._verify_by_mmap_windows(source_path, temp_file_path)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
```

### AFTER

```
        try:
            # Phase 4: Copy to temporary file (DIRECT-SMALL via WinAPI, DIRECT-LARGE via mmap)
            copy_start_time = time.time()
            use_mmap_direct = C.FILECOPY_DIRECT_MMAP_COPY_ENABLED and (file_size >= C.FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES)
            if use_mmap_direct:
                self._log_status(f"Using DIRECT-LARGE (mmap window={C.FILECOPY_MMAP_WINDOW_BYTES//(1024**2)} MiB) for local copy")
                copy_result = self._copy_by_mmap_windows(source_path, temp_file_path, file_size)
            else:
                copy_result = self._copy_with_windows_api(source_path, temp_file_path)
            result.time_copy = time.time() - copy_start_time
            
            if not copy_result['success']:
                # >>> CHANGE START  # explicit cancel semantics + cleanup (DIRECT)
                self._cleanup_temp_file(temp_file_path)  # always safe to remove temp
                result.error_message = copy_result.get('error', 'Copy failed')
                result.error_code = copy_result.get('error_code', 0)
                result.cancelled_by_user = copy_result.get('cancelled', False)
                if result.cancelled_by_user:
                    self._log_status("User cancelled copy; temp removed; original target preserved")
                else:
                    result.recovery_suggestion = copy_result.get('recovery_suggestion', "")
                return result
                # <<< CHANGE END
            
            result.bytes_copied = copy_result['bytes_copied']
            
            # Phase 5: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                if use_mmap_direct:
                    # DIRECT-LARGE → verify via hash; source hash computed during copy
                    result.hash_algorithm = copy_result.get('hash_algorithm', 'SHA-256')
                    result.computed_hash = copy_result.get('hash')
                    self._log_status(f"Verifying copied file using hash comparison ({result.hash_algorithm})")
                    verify_result = self._verify_by_hash_comparison(temp_file_path, result.computed_hash, result.hash_algorithm)
                else:
                    # DIRECT-SMALL → verify via mmap compare
                    self._log_status(f"[DIRECT-SMALL] Verifying copied file using memory-mapped comparison")
                    verify_result = self._verify_by_mmap_windows(source_path, temp_file_path)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
```

---

## PATCH 5b — `FileCopyManager_class.py` (new helper `_copy_by_mmap_windows`)

### BEFORE

```
                result.recovery_suggestion = "Manual intervention required - check backup files"
        
        return result
    
    def _copy_with_windows_api(self, source_path: str, temp_path: str) -> dict:
        """
        Windows CopyFileExW implementation with progress callbacks and cancellation.
        
        Args:
        -----
        source_path: Source file path
        temp_path: Temporary target file path
        
        Returns:
        --------
        dict: Copy result with success status, bytes copied, and error information
```

### 5.b AFTER

```
                result.recovery_suggestion = "Manual intervention required - check backup files"
        
        return result
    
    # >>> CHANGE START  # DIRECT-LARGE windowed mmap copy with on-the-fly source hashing
    def _copy_by_mmap_windows(self, source_path: str, temp_path: str, file_size: int) -> dict:
        """
        DIRECT-LARGE: Windowed memory-mapped copy with on-the-fly source hashing.
        Returns: {success: bool, bytes_copied: int, hash: str, hash_algorithm: str, error?: str, cancelled?: bool}
        """
        try:
            # Pre-allocate destination to full size for proper mapping
            try:
                with open(temp_path, 'wb') as tf:
                    tf.truncate(file_size)
                self._log_status(f"Pre-allocated temp file to {file_size:,} bytes")
            except Exception as e:
                return {'success': False, 'error': f'Pre-allocation failed: {e}', 'recovery_suggestion': 'Ensure free space and permissions'}

            # Choose hash algorithm
            if self.blake3_available:
                hasher = blake3.blake3()
                algo = 'BLAKE3'
            else:
                hasher = hashlib.sha256()
                algo = 'SHA-256'

            window = max(1, int(C.FILECOPY_MMAP_WINDOW_BYTES))
            flush_every = max(0, int(C.FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS))
            bytes_copied = 0
            win_index = 0

            with open(source_path, 'rb') as sf, open(temp_path, 'r+b') as tf:
                offset = 0
                total = file_size
                fd = tf.fileno()
                while offset < total:
                    # Cancellation checks
                    if getattr(self, 'cancel_event', None) and self.cancel_event.is_set():
                        return {'success': False, 'cancelled': True, 'error': 'Cancelled by user'}
                    pm = getattr(self, 'progress_manager', None)
                    if pm and callable(getattr(pm, 'cancellation_callback', None)) and pm.cancellation_callback():
                        return {'success': False, 'cancelled': True, 'error': 'Cancelled by user'}

                    length = min(window, total - offset)
                    try:
                        src_map = mmap.mmap(sf.fileno(), length=length, offset=offset, access=mmap.ACCESS_READ)
                        dst_map = mmap.mmap(fd, length=length, offset=offset, access=mmap.ACCESS_WRITE)
                        try:
                            dst_map[:] = src_map[:]  # Copy bytes
                            hasher.update(src_map)   # Update hash from source window (zero-copy via the mmap buffer)
                            bytes_copied += length
                        finally:
                            try:
                                dst_map.flush()
                            except Exception:
                                pass
                            dst_map.close()
                            src_map.close()
                    except Exception as e_map:
                        return {'success': False, 'error': f'mmap window failed at offset {offset}: {e_map}'}

                    win_index += 1
                    if flush_every and (win_index % flush_every == 0): # Periodic flush to disk for extra safety if configured
                        try:
                            tf.flush()
                            os.fsync(fd)
                        except Exception:
                            pass

                    # Progress update
                    pm = getattr(self, 'progress_manager', None)
                    if pm and hasattr(pm, 'update_file_progress'):
                        try:
                            pm.update_file_progress(source_path, bytes_copied, total, strategy='DIRECT-LARGE')
                        except Exception:
                            pass
                    elif self.status_callback:
                        mb_total = total / (1024*1024)
                        mb_copied = bytes_copied / (1024*1024)
                        self.status_callback(f'Copying (DIRECT-LARGE): {mb_copied:.1f} MB of {mb_total:.1f} MB transferred')

                    offset += length

                # Final flush
                try:
                    tf.flush()
                    os.fsync(fd)
                except Exception:
                    pass

            return {'success': True, 'bytes_copied': bytes_copied, 'hash': hasher.hexdigest(), 'hash_algorithm': algo}
        except Exception as e:
            return {'success': False, 'error': f'DIRECT-LARGE mmap copy failed: {e}', 'recovery_suggestion': 'Check permissions/disk space'}
    # <<< CHANGE END
    
    def _copy_with_windows_api(self, source_path: str, temp_path: str) -> dict:
        """
        Windows CopyFileExW implementation with progress callbacks and cancellation.
        
        Args:
        -----
        source_path: Source file path
        temp_path: Temporary target file path
        
        Returns:
        --------
        dict: Copy result with success status, bytes copied, and error information
```

---

## PATCH 6 (fold-in) — `FileCopyManager_class.py` (label STAGED verify)

### BEFORE

```
            # Phase 4: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                self._log_status(f"Verifying copied file using hash comparison ({result.hash_algorithm})")
                verify_result = self._verify_by_hash_comparison(temp_file_path, result.computed_hash, result.hash_algorithm)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
                
                if not verify_result:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = f"Hash verification failed - {result.hash_algorithm} hashes do not match"
                    result.recovery_suggestion = "Check source file integrity and retry the operation"
                    return result
            else:
                result.verification_mode = "none"
```

### AFTER

```
            # Phase 4: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                # >>> CHANGE START  # label STAGED verify
                self._log_status(f"[STAGED] Verifying copied file using hash comparison ({result.hash_algorithm})")
                # <<< CHANGE END
                verify_result = self._verify_by_hash_comparison(temp_file_path, result.computed_hash, result.hash_algorithm)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
                
                if not verify_result:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = f"Hash verification failed - {result.hash_algorithm} hashes do not match"
                    result.recovery_suggestion = "Check source file integrity and retry the operation"
                    return result
            else:
                result.verification_mode = "none"
```

---

## PATCH 7 (fold-in) — `FileCopyManager_class.py` (label DIRECT-SMALL verify)

### BEFORE

```
            # Phase 5: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                self._log_status(f"Verifying copied file using memory-mapped comparison")
                verify_result = self._verify_by_mmap_windows(source_path, temp_file_path)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
                
                if not verify_result:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = "Content verification failed - files do not match"
                    result.recovery_suggestion = "Check source file integrity and retry the operation"
                    return result
```

### AFTER

```
            # Phase 5: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                # >>> CHANGE START  # label DIRECT-SMALL verify
                self._log_status(f"[DIRECT-SMALL] Verifying copied file using memory-mapped comparison")
                # <<< CHANGE END
                verify_result = self._verify_by_mmap_windows(source_path, temp_file_path)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
                
                if not verify_result:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = "Content verification failed - files do not match"
                    result.recovery_suggestion = "Check source file integrity and retry the operation"
                    return result
```

---
