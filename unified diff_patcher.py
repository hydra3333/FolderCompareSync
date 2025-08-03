#!/usr/bin/env python3
"""
unified_diff_patcher.py
-----------------------
Apply a unified diff (.patch or .diff) to original files and create numbered
output files (e.g., program.py -> program.001.py).

Features:
- Supports multiple files in a single patch
- Skips missing files (warns user)
- Dry-run mode to preview changes without writing files
- Handles standard git-style prefixes (a/ and b/)
- Displays a summary of operations
- Verbose mode to show detailed hunk application steps
- Improved error handling for malformed patches
- Supports --base-dir PATH to apply patches when original files are in a specific folder

Usage:
    python unified_diff_patcher.py patchfile.diff
    python unified_diff_patcher.py patchfile.diff --dry-run
    python unified_diff_patcher.py patchfile.diff --verbose
    python unified_diff_patcher.py patchfile.diff --base-dir "C:\\path\\to\\files"
    python unified_diff_patcher.py patchfile.diff --dry-run --verbose --base-dir "./src"

Examples:
    # Apply patch and create numbered files in current dir
    python unified_diff_patcher.py changes.diff

    # Preview without making changes
    python unified_diff_patcher.py changes.diff --dry-run

    # Apply to files inside ./src directory
    python unified_diff_patcher.py changes.diff --base-dir "./src"

    # Verbose dry-run
    python unified_diff_patcher.py changes.diff --dry-run --verbose

Author: ChatGPT
"""

import sys
import os
import re
import argparse

def next_numbered_filename(original):
    """Return next available numbered filename: file.py -> file.001.py, file.002.py, etc."""
    base, ext = os.path.splitext(original)
    counter = 1
    while True:
        new_name = f"{base}.{counter:03d}{ext}"
        if not os.path.exists(new_name):
            return new_name
        counter += 1

def parse_patch(diff_file):
    """Parse unified diff into a list of file patches."""
    with open(diff_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    patches = []
    current = None
    for line in lines:
        if line.startswith('--- '):
            if current:
                patches.append(current)
            current = {'old': line[4:].strip(), 'new': None, 'hunks': []}
        elif line.startswith('+++ ') and current:
            current['new'] = line[4:].strip()
        elif line.startswith('@@') and current:
            current['hunks'].append({'header': line, 'lines': []})
        elif current and current['hunks']:
            current['hunks'][-1]['lines'].append(line)

    if current:
        patches.append(current)
    return patches

def strip_prefix(filename):
    """Strip 'a/' or 'b/' from filename."""
    return re.sub(r'^[ab]/', '', filename)

def apply_hunks(original_lines, hunks, verbose=False):
    """Apply hunks to original lines, return patched content."""
    patched = original_lines[:]
    offset = 0  # Adjust for insertions/deletions
    for hunk in hunks:
        header = hunk['header']
        m = re.match(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', header)
        if not m:
            raise ValueError(f"Invalid hunk header: {header}")
        old_start = int(m.group(1))
        index = old_start - 1 + offset

        remove_count = 0
        new_lines = []
        if verbose:
            print(f"    Applying hunk: {header.strip()}")
        for line in hunk['lines']:
            if line.startswith('-'):
                remove_count += 1
                if verbose:
                    print(f"      - {line[1:].rstrip()}")
            elif line.startswith('+'):
                new_lines.append(line[1:])
                if verbose:
                    print(f"      + {line[1:].rstrip()}")
            elif line.startswith(' '):
                new_lines.append(line[1:])
        if index < 0 or index > len(patched):
            raise ValueError(f"Hunk cannot be applied: index {index} out of range.")
        patched[index:index+remove_count] = new_lines
        offset += len(new_lines) - remove_count
    return patched

def main():
    parser = argparse.ArgumentParser(description="Apply a unified diff and create numbered output files.")
    parser.add_argument('patchfile', help='Path to the .diff or .patch file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen without making changes')
    parser.add_argument('--verbose', action='store_true', help='Show detailed hunk processing information')
    parser.add_argument('--base-dir', help='Base directory where original files are located (default: current directory)', default='.')
    args = parser.parse_args()

    base_dir = os.path.abspath(args.base_dir)

    patches = parse_patch(args.patchfile)

    if not patches:
        print("No patches found in file.")
        return

    total_processed = 0
    total_patched = 0
    total_skipped = 0
    total_errors = 0

    for p in patches:
        old_file = strip_prefix(p['old'])
        new_file = strip_prefix(p['new'])

        original_path = os.path.join(base_dir, old_file)
        total_processed += 1

        if not os.path.exists(original_path):
            print(f"[SKIP] Original file '{original_path}' not found.")
            total_skipped += 1
            continue

        try:
            with open(original_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            patched_lines = apply_hunks(original_lines, p['hunks'], verbose=args.verbose)
        except Exception as e:
            print(f"[ERROR] Failed to apply patch to '{original_path}': {e}")
            total_errors += 1
            continue

        new_name = next_numbered_filename(original_path)
        if args.dry_run:
            print(f"[DRY-RUN] Would create: {new_name} (from {original_path})")
        else:
            try:
                with open(new_name, 'w', encoding='utf-8') as f:
                    f.writelines(patched_lines)
                print(f"[OK] Patched '{original_path}' -> '{new_name}'")
                total_patched += 1
            except Exception as e:
                print(f"[ERROR] Could not write '{new_name}': {e}")
                total_errors += 1

    # Summary
    print("\nSummary:")
    print(f"  Files processed: {total_processed}")
    print(f"  Patched:         {total_patched}")
    print(f"  Skipped:         {total_skipped}")
    print(f"  Errors:          {total_errors}")

if __name__ == '__main__':
    main()
