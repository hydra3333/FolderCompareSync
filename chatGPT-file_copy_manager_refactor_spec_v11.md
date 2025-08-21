# FileCopyManager Refactor Technical Specification (v10)

---

## Developer Quickstart (Onboarding)

This project defines a safe, efficient, and verifiable file copy system with rollback capability. New developers should start by understanding the following:

1. **Two copy strategies:**
   - **DIRECT** (local disk-to-disk, below size threshold): uses `CopyFileExW` for OS-native performance and mmap-based verification.
   - **STAGED** (networked files or large files): uses chunked copy with BLAKE3 hash verification and rollback if mismatch.

2. **Rollback safety:**
   - Copies always go to a backup-rename file first.
   - Verification ensures integrity.
   - If verification fails or user cancels, backup is restored and incomplete target deleted.

3. **Verification modes (UI radio buttons):**
   - None
   - All files (default)
   - Files below threshold (2 GiB)

4. **Global constants:**
   - `FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES = 2 * 1024**3`
   - `FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES = 20 * 1024**3`
   - `FILECOPY_MMAP_WINDOW_BYTES = 64 * 1024**2`
   - `FILECOPY_NETWORK_CHUNK_BYTES = 4 * 1024**2`
   - `FILECOPY_VERIFY_THRESHOLD_BYTES = 2 * 1024**3`
   - `FILECOPY_FREE_DISK_SPACE_MARGIN = 64 * 1024**2`
   - `FILECOPY_ATTRIBUTE_SPARSE_FILE_WARNING = True`
   - `FILECOPY_VERIFY_POLICY = 'lt_threshold'`

5. **Mandatory goals (R.1–R.10):**
   - Safety, metadata preservation, efficiency, rollback, progress updates, proper naming, drop-in compatibility, best practice coding.

Developers should read the **English Walkthrough** section to understand flow, and refer to **Appendix F (Code Fragments)** for Windows constants and API references.

---

## English Walkthrough of Copy Process

### A) DIRECT Copy (Local HDD/SSD, below threshold)

**Use when:** source and target are local NTFS drives and file < 2 GiB.

**Steps:**
1. Preflight: check free space ≥ file size + backup size + margin.
2. Copy:
   - Use `CopyFileExW` for speed, metadata, and callbacks.
   - Progress callback drives UI updates.
   - Backup file created first; only after verify do we finalize.
3. Verify:
   - Windowed mmap compare, 64 MiB windows.
   - If mismatch → rollback to backup.
   - If mmap fails → fallback to buffered byte compare.
   - Progress updates increment per window.
4. Rollback:
   - If cancelled/error: delete incomplete file, restore backup.

---

### B) STAGED Copy (Network paths or ≥ 2 GiB)

**Use when:** source or target is on network, or file ≥ 2 GiB.

**Steps:**
1. Preflight: same free-space check (GetDiskFreeSpaceExW if available).
2. Copy:
   - Buffered chunked I/O, 4 MiB chunks.
   - Source hash (BLAKE3) computed on-the-fly.
   - Progress bar updated chunk by chunk.
   - Target written to backup file.
3. Verify:
   - Recompute target hash using same chunk size.
   - Compare against source hash.
   - Fallback: if BLAKE3 unavailable → buffered byte-compare.
4. Rollback:
   - On mismatch/cancel/error: delete incomplete file, restore backup.

---

### Rollback Mechanism (Both Modes)
- Always copy into backup-rename target.
- Verification ensures correctness.
- On success: finalize by replacing original.
- On failure/cancel: delete partial and restore previous version.

---

## Appendices

### Appendix F — Windows API Code Fragments
- Centralized constants (`GENERIC_READ`, `FILE_SHARE_READ`, `OPEN_EXISTING`…)
- Example: `CopyFileExW`, `GetDiskFreeSpaceExW`, `SetFileTime`.
- Code snippets provided for reference for developers working with ctypes.

### Appendix G — Version History
- **v1 → v2:** Initial structure, added mandatory requirements.
- **v3:** Clarified copy/verify split; added mmap window.
- **v4:** Added network staged strategy.
- **v5:** Refined constants, free-space check added.
- **v6:** User-added mandatory requirements list.
- **v7:** Removed overwrite; clarified rollback.
- **v8:** Goals vs mandatory requirements distinction.
- **v9:** Added English walkthrough, rollback explanation, hash appendix.
- **v10:** Added Developer Quickstart onboarding section.

---

Would you like me to export this full v10 spec now as a `.md` file so you can download it? 

