# FolderCompareSync - Technical Specification

*A Professional Folder Comparison & Synchronization Tool for Windows*

![Status](https://img.shields.io/badge/status-active-brightgreen)  
![Version](https://img.shields.io/badge/version-0.3.1-blue)  
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey)

**License:** AGPL-3.0  
**Current Version:** 0.3.1 - Performance Optimizations

---

## Core Concept

A **dual-pane folder comparison tool** with synchronized tree views, similar to Windows Explorer but focused on comparison and selective copying between two folder structures. Designed specifically for **Windows 10, Windows 11, and future compatible versions**.

---

## Enhanced Main Window Layout (v0.3.0)

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
│                                                                             │
│ Filter Files by Wildcard: [*.jpg____________] [Apply Filter] [Clear Filter]│
│ [Expand All] [Collapse All]                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ LEFT                                    │ RIGHT                             │
│ ╔════════════════════════════════════════╬═══════════════════════════════════╗  │
│ ║ Structure  │Size│Date Created│Date Mod │SHA512  │Status║                  ║  │
│ ╠════════════════════════════════════════╬═══════════════════════════════════╣  │
│ ║ ☐ C:\Projects\MyApp\                   ║ ☐ D:\Backup\MyApp\               ║  │
│ ║   ☑ ☐ src/                             ║   ☑ ☐ src/                       ║  │
│ ║   ☐   ☑ file1.txt│2KB│2024-08-01│2024-08-02│a1b2c3...│Different ║       ║  │
│ ║   ☐   ☐ file2.txt│3KB│2024-08-01│2024-08-01│d4e5f6...│Same      ║       ║  │
│ ║   ☐   docs/ [MISSING]                  ║   ☐   ☐ docs/                   ║  │ ← Missing folder: no checkbox
│ ║   ☐   README.md [MISSING]              ║   ☐   ☐ README.md │5KB│...│...   ║  │ ← Missing file: no checkbox  
│ ╚════════════════════════════════════════╩═══════════════════════════════════╝  │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Copy LEFT to Right] [Copy RIGHT to Left] [Quit]                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Status Log (5 visible lines, 500 line history)                             │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ 14:32:15 - Application initialized - Ready to compare folders        │   │
│ │ 14:32:23 - Selected left folder: C:\Projects\MyApp                   │   │
│ │ 14:32:30 - Selected right folder: D:\Backup\MyApp                    │   │
│ │ 14:32:35 - Starting folder comparison...                             │   │
│ │ 14:32:37 - Comparison complete: 49 differences found in 2.3 seconds  │   │
│ │ 14:32:45 - Applied filter: *.jpg - 23 files match                    │   │
│ │ 14:32:50 - Sorted by size (ascending) - 1,247 files processed       │   │
│ │ 14:33:10 - Copy operation complete: 23 files copied in 5.2 seconds   │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Summary (filtered): 4 differences | 1 missing left | 2 missing right | 3 marked │
│                                                        Status: Ready (DEBUG) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Enhanced Features & Implementation Status

### ✅ **FULLY IMPLEMENTED: Enhanced Metadata Display**

**All metadata columns always visible:**
- **Size column**: Human-readable format (KB, MB, GB, TB) with sorting capability
- **Date Created column**: Full timestamp display with sortable date comparison
- **Date Modified column**: Full timestamp display with sortable date comparison
- **SHA512 column**: First 16 characters with "..." for space efficiency
- **Status column**: Clear indication of differences (Same, Different, Missing)

**Display behavior:**
- All columns show regardless of comparison options selected
- Users can see complete metadata even if not using all comparison criteria
- Sortable headers for all columns (click to sort ascending/descending)
- Professional column sizing with configurable defaults and minimums

### ✅ **FULLY IMPLEMENTED: Wildcard File Filtering**

**Standard Windows wildcard patterns supported:**
- **Single file**: `specific_file.txt`
- **Extension filtering**: `*.jpg`, `*.pdf`, `*.mp4`
- **Partial name matching**: `*data*.txt`, `test*.log`
- **Complex patterns**: `IMG_*.JPG`, `backup_*_2024.zip`

**Filter features:**
- **Case-insensitive matching**: Works with any case combination
- **Files-only filtering**: Folders are never filtered (maintains tree structure)
- **Performance optimization**: Limited to 200,000 results for responsiveness
- **Real-time feedback**: Progress dialog shows matching count
- **Clear filter button**: Instantly restore full view

### ✅ **FULLY IMPLEMENTED: Sortable Column Headers**

**Click-to-sort functionality:**
- **Structure column**: Alphabetical sorting (name-based)
- **Size column**: Numerical sorting (actual bytes, not display format)
- **Date columns**: Chronological sorting (newest/oldest first)
- **SHA512 column**: Alphabetical sorting of hash values
- **Status column**: Categorical sorting (Different, Same, Missing)

**Sort behavior:**
- **Toggle sorting**: First click = ascending, second click = descending
- **Visual feedback**: Progress dialog during sort operations
- **Files-only sorting**: Only files are sorted, folder hierarchy preserved
- **Status logging**: All sort operations logged with timing

### ✅ **FULLY IMPLEMENTED: Tree Expansion Controls**

**Complete tree management:**
- **Expand All button**: Recursively opens all folders in both trees
- **Collapse All button**: Recursively closes all folders (except root)
- **Synchronized operation**: Both trees expand/collapse together
- **Status feedback**: Operations logged in status window
- **Performance optimized**: Handles large folder structures efficiently

### ✅ **FULLY IMPLEMENTED: Actual File Copy Operations**

**Real file copying with safeguards:**
- **Confirmation dialogs**: Preview what will be copied before operation
- **Progress tracking**: File-by-file progress with current file display
- **Error handling**: Continues operation even if individual files fail
- **Overwrite mode**: Respects overwrite setting for existing files
- **Metadata preservation**: Uses shutil.copy2 to preserve timestamps

**Post-copy behavior (CRITICAL FEATURE):**
- **Automatic folder re-scan**: Both folders scanned after copy completion
- **Tree rebuild**: Display updated to show current state
- **Selection clearing**: All checkboxes cleared for fresh start
- **Status confirmation**: Completion message with statistics

### ✅ **FULLY IMPLEMENTED: Enhanced Status Logging**

**Comprehensive operation tracking:**
- **Folder operations**: Selection, scanning start/finish with counts
- **Comparison events**: Progress updates, completion with timing and results
- **Selection tracking**: Item selection/deselection with running counts
- **Filter operations**: Filter application, results count, clear operations
- **Tree operations**: Expand/collapse all, sort operations with timing
- **Copy operations**: Start, progress updates, completion with statistics
- **Error reporting**: All errors with helpful context and guidance

### ✅ **FULLY IMPLEMENTED: Enhanced Progress Dialogs**

**Operation-specific progress indication:**

**Folder Scanning Progress:**
- **Indeterminate progress bar** with running animation
- **Running item counter**: "1,247 items found" with real-time updates
- **Operation context**: "Scanning left folder..." / "Scanning right folder..."
- **Performance adaptive**: Adjusts update frequency based on folder size

**Comparison Progress:**
- **Determinate progress bar** with 0-100% completion
- **File progress display**: "Comparing... 1,247 of 2,445 files"
- **Multi-phase tracking**: Scanning (40%), Comparison (50%), UI Building (10%)
- **Real-time updates**: Progress updates every configurable interval

**Copy Operations Progress:**
- **File-by-file tracking**: "Copying 23 of 67 files..."
- **Current file display**: Shows name of file being copied
- **Error resilience**: Continues and reports errors without stopping
- **Statistics tracking**: Running count of copied/failed/skipped files

---

## Technical Architecture Enhancements

### **Advanced Data Structures**

```python
class EnhancedProgressDialog:
    """Professional progress dialog with adaptive behavior"""
    - Multi-phase progress tracking
    - Resource-aware update frequencies
    - Error-resilient operation continuation
    - Adaptive UI updates based on operation complexity

class FolderCompareSync_class:
    """Enhanced main application with comprehensive features"""
    # Enhanced filtering and sorting
    filter_wildcard: tk.StringVar              # Current filter pattern
    filtered_results: Dict[str, ComparisonResult_class]  # Filtered comparison results
    current_sort_column: Optional[str]         # Currently sorted column
    current_sort_order: str                    # 'asc' or 'desc'
    is_filtered: bool                          # Whether filter is active
    
    # Enhanced progress tracking
    operation_start_time: float                # For timing operations
    last_progress_update: float                # Rate limiting for progress updates
    
    # Enhanced metadata display
    all_metadata_visible: bool = True          # Always show all columns
    
    # Copy operation management
    copy_in_progress: bool = False             # Track copy operation state
    auto_refresh_after_copy: bool = True       # Auto-refresh setting
```

### **Enhanced Threading Architecture**
- **Main UI thread**: All user interaction and display updates
- **Background comparison thread**: File system operations and metadata comparison
- **Background copy thread**: File copy operations with progress reporting
- **Background filter thread**: Large-scale filtering operations
- **Background sort thread**: File sorting operations
- **Progress update threads**: Thread-safe status and progress updates
- **Error propagation**: Safe error handling across all thread boundaries

### **Memory Management Enhancements**
- **Adaptive processing**: Switch to memory-efficient mode for large folders (>10,000 items)
- **Streaming operations**: Process large file lists without loading all into memory
- **Progress batching**: Update UI in configurable batches to maintain responsiveness
- **Status log management**: Automatic trimming with configurable history limits
- **Resource monitoring**: Track memory usage and adjust processing accordingly

---

## Performance Characteristics & Scalability

### **Enhanced Performance Metrics**
- **Small folders (< 1,000 files)**: Near-instant all operations
- **Medium folders (1,000-10,000 files)**: 1-5 seconds with real-time progress
- **Large folders (10,000-50,000 files)**: Background processing with percentage progress
- **Very large folders (50,000+ files)**: Memory-efficient processing with batch updates
- **Filter operations**: Sub-second for most patterns, progress for complex filters
- **Sort operations**: Optimized batch processing, progress for large datasets
- **Copy operations**: File-by-file progress, efficient error handling

### **Scalability Enhancements**
- **Configurable thresholds**: All performance limits adjustable via constants
- **Adaptive algorithms**: Automatically adjust processing based on data size
- **Efficient data structures**: Optimized path mapping and tree navigation
- **Progress optimization**: Smart update frequencies to balance feedback and performance
- **Memory management**: Automatic cleanup and efficient memory usage patterns

---

## Configuration Constants

### **Window Layout Constants**
```python
WINDOW_WIDTH_PERCENT = 0.98        # 98% of screen width
WINDOW_HEIGHT_PERCENT = 0.93       # 93% of screen height  
MIN_WINDOW_WIDTH = 800             # Minimum window width in pixels
MIN_WINDOW_HEIGHT = 600            # Minimum window height in pixels
```

### **Status Log Configuration**
```python
STATUS_LOG_VISIBLE_LINES = 5       # Visible lines in status log window
STATUS_LOG_MAX_HISTORY = 500       # Maximum lines to keep in history
STATUS_LOG_FONT = ("Courier", 9)   # Monospace font for better alignment
```

### **Performance Settings**
```python
SHA512_MAX_FILE_SIZE = (1000 * 1024 * 1024) * 25  # 25GB limit for hash computation
MEMORY_EFFICIENT_THRESHOLD = 10000                  # Switch to efficient mode above N items
MAX_FILTER_RESULTS = 200000                         # Maximum items when filtering (200K)
TREE_UPDATE_BATCH_SIZE = 200000                     # Process tree updates in batches (200K)
```

### **Tree Column Configuration**
```python
TREE_STRUCTURE_WIDTH = 280         # Default structure column width
TREE_SIZE_WIDTH = 80              # Size column width
TREE_DATE_CREATED_WIDTH = 110     # Date created column width
TREE_DATE_MODIFIED_WIDTH = 110    # Date modified column width
TREE_SHA512_WIDTH = 100           # SHA512 column width
TREE_STATUS_WIDTH = 100           # Status column width
```

---

## Metadata Comparison Logic

### **Comparison Criteria**
- ☑ **Existence** - File exists in one location but not the other *(DEFAULT: ON)*
- ☑ **Size** - File sizes differ *(DEFAULT: ON)*  
- ☑ **Date Created** - Creation dates differ *(DEFAULT: ON)*
- ☑ **Date Modified** - Modification dates differ *(DEFAULT: ON)*
- ☐ **SHA512** - File content differs (hash comparison) *(DEFAULT: OFF)*

### **Enhanced Comparison Features**
- **Background processing**: Multi-threaded comparison with progress tracking
- **Memory efficient**: Handles large directories without memory issues
- **Error resilient**: Continues comparison even when individual files fail
- **Progress logging**: Real-time progress updates in status log

---

## User Experience Enhancements

### **Professional Workflow**
1. **Comprehensive guidance**: Clear instructions and status feedback at every step
2. **Real-time visibility**: Progress dialogs and status log show exactly what's happening
3. **Smart filtering**: Find specific files quickly in large folder structures
4. **Intelligent sorting**: Organize display by any metadata field
5. **Complete tree control**: Expand/collapse all for overview or detail focus
6. **Safe operations**: Confirmation dialogs and preview before destructive actions
7. **Automatic refresh**: Post-operation refresh ensures display accuracy

### **Enhanced Status Log Events**

**Application lifecycle:**
- Application startup/shutdown with system information
- Folder selection and validation
- Window resizing and UI state changes

**Comparison operations:**
- Scan start with folder paths and settings
- Progress updates during scanning (every N items)
- Scan completion with item counts and timing
- Comparison phase start with criteria
- Progress updates during comparison (every N items or N%)
- Comparison completion with differences found and timing

**User interactions:**
- Selection changes with item counts
- Filter application/clearing with result counts
- Sort operations with column and order
- Tree expansion/collapse operations
- Copy operation initiation with item counts

**Copy operations:**
- Operation start with source/destination and file count
- Progress updates during copying (every N files or N%)
- Individual file copy success/failure
- Operation completion with statistics (copied/failed/skipped/timing)
- Post-copy refresh operations

---

## Development Standards & Requirements

### **Windows Compatibility**
- **Target platforms**: Windows 10, Windows 11, and subsequent compatible versions
- **Character encoding**: ASCII-only text to prevent encoding errors
- **File path handling**: Windows-native path resolution and validation
- **System integration**: Proper Windows version detection and logging

### **Enhanced Code Quality**
- **Comprehensive configuration**: All UI and performance parameters configurable via constants
- **Professional error handling**: Graceful degradation with helpful user guidance
- **Strategic logging**: Detailed debug information without performance impact
- **Modular architecture**: Clean separation of concerns for maintainability
- **Extensive documentation**: Comprehensive docstrings and comments

### **Enhanced Testing Considerations**
- **Large folder testing**: Validated with folders containing 50,000+ files
- **Error condition testing**: Network failures, permission errors, disk space issues
- **Performance testing**: Memory usage and response time under various loads
- **User workflow testing**: Complete end-to-end scenarios with real data
- **Edge case handling**: Empty folders, conflicting names, special characters

---

## Installation & System Requirements

### **Enhanced Dependencies**
- **Python 3.7+**: Core language requirement with enhanced features
- **tkinter**: GUI framework with extended widget usage
- **Built-in libraries**: pathlib, hashlib, threading, logging, datetime, shutil, fnmatch
- **No external dependencies**: Self-contained application

### **Enhanced Supported Systems**
- **✅ Windows 10**: Full support with all features
- **✅ Windows 11**: Full support with system detection and optimization
- **✅ Future Windows**: Designed for forward compatibility with version detection

### **Enhanced System Resources**
- **RAM**: 100MB base + ~1MB per 10,000 files + filter/sort overhead
- **Disk**: Minimal base + configurable log file growth
- **CPU**: Single background thread for operations + adaptive batch processing
- **Performance**: Scales efficiently with configurable thresholds and adaptive algorithms

---

## Future Development Roadmap

### **Phase 1: Advanced UI Features**
- **Column sorting implementation**: Complete tree reordering based on sort criteria
- **Advanced filtering**: Regular expressions, date ranges, size ranges
- **Search functionality**: Find specific files across entire tree structures
- **Keyboard shortcuts**: Arrow keys, space for selection, Ctrl+A, etc.
- **Context menus**: Right-click operations for files and folders

### **Phase 2: Enterprise Features**
- **Operation history**: Save and load previous comparison sessions
- **Configuration profiles**: Save comparison settings for different scenarios
- **Batch operations**: Queue multiple copy operations
- **Export functionality**: Export comparison results to CSV/Excel
- **Command-line interface**: Headless operation for automation

### **Phase 3: Advanced Synchronization**
- **Bidirectional sync**: Intelligent two-way synchronization
- **Conflict resolution**: Handle files modified in both locations
- **Incremental updates**: Only process changed files in subsequent runs
- **Scheduling**: Automated sync operations at specified intervals
- **Network optimization**: Efficient handling of network drives and cloud storage

### **Phase 4: Integration Features**
- **Version control integration**: Git status awareness and handling
- **Cloud storage support**: Direct integration with OneDrive, Google Drive, etc.
- **Network monitoring**: Detect and handle network drive connectivity changes
- **System integration**: Windows shell extension for context menu access
- **Backup verification**: Verify copied files with hash comparison

---

## Copy Queue Implementation Strategy

For handling large copy operations with thousands of files:

### **Recommended Implementation**
1. **Staged Preview**: Show first 100 items in preview, with "... and N more" summary
2. **Progress Logging**: Real-time progress with file counts, not individual filenames
3. **Batch Status Updates**: Update status log every 100 files or 10% completion
4. **Error Summary**: Collect errors during operation, show summary at end
5. **Performance Optimization**: Use configurable batch sizes for UI updates
6. **Memory Management**: Stream file lists rather than loading all into memory

### **Alternative Approaches**
- **Chunked Operations**: Break large operations into smaller, manageable chunks
- **Priority Queuing**: Allow users to prioritize certain files for copying first
- **Background Processing**: Copy operations run completely in background with summary notifications
- **Pause/Resume**: Allow users to pause long-running operations and resume later

---

*This specification document is maintained alongside the main program and updated with each version release. For version history, see CHANGELOG.md*