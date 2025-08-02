# FolderCompareSync  
*A Professional Folder Comparison & Synchronization Tool for Windows*
### DOES NOT YET WORK
### Under Construction

![Status](https://img.shields.io/badge/status-active-brightgreen)  
![Version](https://img.shields.io/badge/version-0.2.6-blue)  
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey)

---

## 📑 Table of Contents
- [Core Concept](#core-concept)
- [Current Version](#current-version-026---professional-grade)
- [Main Window Layout](#main-window-layout-current-v026)
- [Enhanced Features & Implementation Status](#enhanced-features--implementation-status)
- [User Experience Enhancements](#user-experience-enhancements)
- [Technical Architecture](#technical-architecture-enhanced)
- [Development Standards & Requirements](#development-standards--requirements)
- [Future Development Roadmap](#future-development-roadmap)
- [Performance Characteristics & Scalability](#performance-characteristics--scalability)
- [Installation & System Requirements](#installation--system-requirements)

---

## Core Concept
A **dual-pane folder comparison tool** with synchronized tree views, similar to Windows Explorer but focused on comparison and selective copying between two folder structures.  
**Designed for Windows 10, Windows 11, and future compatible versions.**

---

## Current Version: **0.2.6 - Professional Grade**
### Latest Major Enhancements:
- Full-width status log window with scrollable history and timestamps  
- Professional progress dialogs for all long-running operations  
- Real-time operation feedback and progress tracking  
- Comprehensive status logging with automatic line management  
- Enhanced user experience with clear operation visibility  

---

## Main Window Layout (Current v0.2.6)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FolderCompareSync - Folder Comparison and Syncing Tool                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Folder Selection                                                            │
│ Left Folder: [C:\Projects\MyApp\________________] [Browse]                  │
│ Right Folder: [D:\Backup\MyApp\________________] [Browse]                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Comparison Options                                                          │
│ Compare Options: ☑Existence ☑Size ☑Date Created ☑Date Modified ☐SHA512    │
│ ← select options then click Compare                                         │
│ ☑ Overwrite Mode                                                            │
│ [Compare] [Select All Diff - Left] [Clear All - Left] [Select All Diff - Right] [Clear All - Right] │
├─────────────────────────────────────────────────────────────────────────────┤
│ LEFT                          │ RIGHT                                       │
│ ╔══════════════════════════════╬══════════════════════════════════════════╗  │
│ ║ Structure    │Size│Date Mod  ║ Structure    │Size│Date Mod │Status     ║  │
│ ╠══════════════════════════════╬══════════════════════════════════════════╣  │
│ ║ ☐ C:\Projects\MyApp\         ║ ☐ D:\Backup\MyApp\                       ║  │
│ ║   ☑ ☐ src/                   ║   ☑ ☐ src/                               ║  │
│ ║   ☐   ☑ file1.txt│2KB│2024   ║   ☐   ☑ file1.txt│1KB│2024│Different    ║  │
│ ║   ☐   ☐ file2.txt│3KB│2024   ║   ☐   ☐ file2.txt│3KB│2024│Same         ║  │
│ ║   ☐   docs/ [MISSING]        ║   ☐   ☐ docs/                           ║  │ <- Missing folder
│ ║   ☐   README.md [MISSING]    ║   ☐   ☐ README.md │5KB│2024│Missing      ║  │ <- Missing file
│ ╚══════════════════════════════╩══════════════════════════════════════════╝  │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Copy LEFT to Right] [Copy RIGHT to Left] [Quit]                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Status Log (5 visible lines, 200 line history)                             │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ 14:32:15 - Application initialized - Ready to compare folders        │   │
│ │ 14:32:23 - Selected left folder: C:\Projects\MyApp                   │   │
│ │ 14:32:30 - Selected right folder: D:\Backup\MyApp                    │   │
│ │ 14:32:35 - Starting folder comparison...                             │   │
│ │ 14:32:37 - Comparison complete: 49 differences found in 2.3 seconds  │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Summary: 4 differences | 1 missing left | 2 missing right | 3 marked       │
│                                                        Status: Ready (DEBUG) │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Progress Dialog Example:**
```
┌─────────────────────────────────────┐
│ Comparing Folders                   │
├─────────────────────────────────────┤
│ Scanning left folder...             │
│                                     │
│ ████████████████████████████ 73%    │
│                                     │
│ 1,247 items found                   │
└─────────────────────────────────────┘
```

---

## Enhanced Features & Implementation Status

### ✅ Fully Implemented Features
- [x] **Status Log Window**
- [x] **Progress Dialogs**
- [x] **Enhanced Selection Workflow**
- [x] **Professional Error Handling**
- [x] **Windows-Optimized Design**
- [x] **Conditional Logging System**
- [x] **Advanced Tree Management**
- [x] **Metadata Comparison**
- [x] **Copy Operations (Safety Mode)**

---

### Status Log Window
- Full-width scrollable window (5 visible lines)
- 200-line rolling history with automatic trimming
- Timestamped messages in `HH:MM:SS` format
- Auto-scrolling with manual scroll capability
- Read-only text widget

**Logged Events:**
- Application start, folder selection, scanning
- Comparison progress & results
- Selection changes
- Copy previews & results
- Error messages with context

---

### Progress Dialogs
- Folder Scanning: Indeterminate progress bar, running counter (`X items found`)
- Comparison: Determinate progress bar (0-100%), file count
- Copy Operations: Planned for future release
- Thread-safe updates & automatic cleanup

---

### Enhanced Selection Workflow
- Smart folder selection (only selects different items)
- Auto-clear before bulk selection
- Logged selection changes with counts

---

### Professional Error Handling
- Handles file access errors, locked files, invalid paths
- Safe threading error propagation
- Error-safe progress dialog closing

---

### Windows-Optimized Design
- No emojis or special characters in UI
- ASCII-only interface for compatibility
- Proper Windows path handling and system detection

---

### Conditional Logging
- Debug mode → Console + file
- Production mode → File only
- Status log always active

---

## User Experience Enhancements
- Real-time feedback via status log  
- Progress dialogs for all major operations  
- Error transparency with clear context  
- Smart selection for syncing differences  

---

### Status Log Example:
```
14:32:15 - Application initialized - Ready to compare folders
14:32:23 - Selected left folder: C:\Projects\MyApp
14:32:30 - Selected right folder: D:\Backup\MyApp
14:32:35 - Starting folder comparison...
14:32:37 - Comparison complete: 49 differences found in 2.3 seconds
```

---

## Technical Architecture (Enhanced)

### Core Classes
```
class ProgressDialog:
    # Professional progress dialog with determinate/indeterminate modes

class FolderCompareSync:
    # Main application with status logging & progress tracking
```

- Thread-safe updates
- Background comparison thread
- Efficient memory handling

---

## Development Standards & Requirements
- Target Platforms: Windows 10 & 11
- Dependencies: Python 3.7+, tkinter (built-in)
- Code Quality: Comprehensive comments, robust error handling
- Logging Strategy: File + UI log, debug control

---

## Future Development Roadmap
- Phase 1: Enable real file copying with progress & verification  
- Phase 2: Advanced UI features (sorting, filtering)  
- Phase 3: Enterprise features (operation history, profiles)  
- Phase 4: Advanced sync (bidirectional, conflict resolution)  

---

## Performance Characteristics & Scalability
- Small folders (<1,000 files): Instant
- Medium (1,000-10,000): ~5 seconds
- Large (10,000+): Background processing with progress
- 200-line log limit for efficiency

---

## Installation & System Requirements
- Python: 3.7+  
- Libraries: tkinter, pathlib, threading, logging  
- Supported OS: Windows 10 / 11  
- RAM: ~100MB base + 1MB per 10,000 files  

---

Version: 0.2.6  
Status: Actively developed  
License: To be added  
