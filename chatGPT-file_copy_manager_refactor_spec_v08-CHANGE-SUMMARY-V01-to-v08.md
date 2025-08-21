# FileCopyManager Refactor Specification — Version History

This document provides a summary of the changes made between versions of the FileCopyManager refactor specification. Each version section includes (a) what was added, (b) what was changed, and (c) what was omitted compared to prior drafts.

---

## v1 → v2
- **Added**: Initial outline of objectives, draft constants, and verification approaches. 
- **Changed**: Early discussion of overwrite semantics still present.
- **Omitted**: No clear rollback mechanism details; sparse file handling not addressed.

## v2 → v3
- **Added**: Draft backup/rollback strategies, preliminary UNC handling notes.
- **Changed**: Expanded verification strategies (mmap vs staged copy).
- **Omitted**: Still lacked explicit user-facing constants; no detailed Windows API references.

## v3 → v4
- **Added**: More complete set of global constants, preliminary cancel-latency reasoning.
- **Changed**: Clarified verification fallback (hash vs byte-compare).
- **Omitted**: Recycle Bin vs permanent deletion discussion not yet present.

## v4 → v5
- **Added**: Backup deletion policy discussion; preflight low-space check proposal.
- **Changed**: Beginnings of structured mandatory requirements.
- **Omitted**: Windows API centralization section absent; no explicit UI alignment guidance.

## v5 → v6
- **Added**: Mandatory requirements section introduced, aligning with safe copy, rollback, verification.
- **Changed**: Constants unified into consistent `*_BYTES` naming.
- **Omitted**: Project Goals (R.1–R.10) not included; overwrite option still mentioned though marked obsolete.

## v6 → v7
- **Added**: Explicit answers to Q&A (UNC rejection, sparse warnings, backup deletion permanent, etc.).
- **Changed**: Constants finalized; improved structure with overview.
- **Omitted**: Some older programming snippets and background notes (e.g., Windows API constants).

## v7 → v8
- **Added**: Project Goals (R.1–R.10) reinstated ahead of Mandatory Requirements; appendices structure reinforced.
- **Changed**: Overwrite removed entirely; verification clarified as mmap or Blake3 with fallback; internal consistency reviewed.
- **Omitted**: None of the agreed items. However, older exploratory text, verbose prose, and redundant drafts of constants remain left out intentionally for clarity.

---

**Note:** Earlier drafts often contained exploratory content, code fragments, or alternative strategies. Where these were omitted, it was intentional to streamline the developer-facing specification. Useful background (e.g., Windows API centralization, Win32 constants) is planned to be collected into appendices for reference rather than mainline spec text.

