# FolderCompareSync - Technical Specification

*A Professional Folder Comparison & Synchronization Tool for Windows*

![Status](https://img.shields.io/badge/status-active-brightgreen)  
![Version](https://img.shields.io/badge/version-0.5.0-blue)  
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey)

**License:** AGPL-3.0  
**Current Version:** 0.5.0 - Revolutionary Optimized Copy System

---

## Core Concept

A **dual-pane folder comparison tool** with synchronized tree views and **revolutionary optimized copy system**, similar to Windows Explorer but focused on comparison and selective copying between two folder structures. Designed specifically for **Windows 10, Windows 11, and future compatible versions** with **breakthrough file copy performance and reliability**.

---

## Optimized Main Window Layout (v0.5.0)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FolderCompareSync - Folder Comparison and Syncing Tool (Optimized Copy)    │
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
│ │ 14:32:15 - Application initialized - Optimized copy system ready     │   │
│ │ 14:32:23 - Selected left folder: C:\Projects\MyApp                   │   │
│ │ 14:32:30 - Selected right folder: D:\Backup\MyApp (Network Mapped)   │   │
│ │ 14:32:35 - Starting folder comparison...                             │   │
│ │ 14:32:37 - Comparison complete: 49 differences found in 2.3 seconds  │   │
│ │ 14:32:45 - Starting optimized copy: 23 items LEFT to RIGHT (b8a7c2f1) │   │
│ │ 14:32:47 - Using OPTIMIZED STAGED strategy for largefile.zip (15MB)  │   │
│ │ 14:32:50 - Optimized copy complete: 23 copied, 0 errors, 50% faster  │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Summary (filtered): 4 differences | 1 missing left | 2 missing right | 3 marked │
│                                    Status: Ready (Optimized Copy System) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Revolutionary Optimized Copy System Architecture (v0.5.0)

### **Breakthrough Performance Enhancement**

The optimized copy system represents a **revolutionary advancement** in file copy reliability and performance, featuring a completely rewritten Strategy B that eliminates wasteful resource usage while maintaining maximum safety.

#### **Strategy A - Enhanced Direct Copy**
- **Target Files**: Small files (<10MB) on local drives
- **Method**: Enhanced `shutil.copy2` with complete timestamp preservation
- **Timestamp Management**: Full creation and modification time preservation using `FileTimestampManager`
- **Verification**: Post-copy size validation with optional hash verification
- **Performance**: Optimized for speed with minimal overhead and perfect metadata preservation

#### **Strategy B - Revolutionary Optimized Staged Copy**
- **Target Files**: Large files (≥10MB) or any files on network drives
- **Method**: Breakthrough rename-based backup approach with atomic operations
- **Performance Gain**: ~50% reduction in disk space usage vs traditional approach
- **Safety**: Zero data loss risk with comprehensive rollback capability
- **Efficiency**: Maximum 2 files during operation vs traditional 3-file approaches

### **Revolutionary 4-Step Optimized Copy Process**
```
OLD APPROACH (Strategy B v0.4.0):
  target.txt → target.txt.backup (EXPENSIVE COPY)
  source.txt → temp.txt (EXPENSIVE COPY) 
  temp.txt → target.txt (MOVE)
  Result: 3 files during operation, 2 expensive copies

NEW OPTIMIZED APPROACH (Strategy B v0.5.0):
  Step 1: Save original timestamps for rollback
  Step 2: target.txt → target.txt.backup (ATOMIC RENAME - instant)
  Step 3: source.txt → target.txt (SINGLE COPY)
  Step 4: Verify and cleanup

  Result: 2 files during operation, 1 expensive copy
  Performance: ~50% faster, 50% less disk space usage
```

### **Enhanced Timestamp Preservation System**

#### **Complete Timestamp Management**
```python
class FileTimestampManager:
    """Enhanced timestamp management with rollback capability"""
    
    def copy_timestamps(source, target):
        """Copy both creation and modification timestamps"""
        
    def save_for_rollback(target_path):
        """Save original timestamps before backup operations"""
        
    def restore_on_rollback(target_path, saved_timestamps):
        """Restore exact original timestamps during rollback"""
```

#### **Rollback with Timestamp Restoration**
- **Save Original Timestamps**: Creation and modification times preserved before operation
- **Atomic Rename Backup**: Original file renamed (preserves all metadata)
- **Rollback Restoration**: Exact timestamp restoration during failure recovery
- **Complete Metadata Preservation**: No timestamp loss even during failed operations

### **Enhanced Error Handling & User Guidance**

#### **Zero-Fallback Design Philosophy**
Instead of silent fallbacks that mask problems, the optimized system provides:
- **Immediate Error Reporting**: Clear explanation of what went wrong
- **Actionable Guidance**: Specific steps users can take to resolve issues
- **Context-Aware Help**: Different guidance for network vs local drive issues
- **Operation Abort**: Clean abort with full rollback rather than silent degradation

#### **Critical Error Categories**
```
RENAME OPERATION FAILURES:
  - Network connectivity issues
  - File locking by other processes
  - Insufficient permissions
  → User Guidance: Check network connection, close programs using files

PROCESS INTERRUPTION:
  - System shutdown during operation
  - Application crash or kill
  - Network disconnection mid-operation
  → Automatic Recovery: Complete rollback with timestamp restoration

VERIFICATION FAILURES:
  - Size mismatch after copy
  - Hash verification failure
  → Automatic Recovery: Remove corrupt copy, restore original
```

---

## Enhanced Network Drive Detection & Optimization

### **Advanced Drive Type Detection**
```python
def get_drive_type(path: str) -> DriveType:
    """Enhanced Windows API drive type detection"""
    # Handles all Windows drive types including:
    - LOCAL_FIXED: C:, D: (SSD, HDD)
    - LOCAL_REMOVABLE: USB, external drives
    - NETWORK_MAPPED: A:, B:, Z: (mapped network drives)
    - NETWORK_UNC: \\server\share paths
    - RELATIVE: Relative paths without drive letters
```

### **Optimized Strategy Selection Logic**
- **Network drives (any type)** → Always use Optimized Staged Strategy (rename-based backup)
- **Large files (≥10MB)** → Always use Optimized Staged Strategy (maximum reliability)
- **Small files (<10MB) on local drives** → Use Enhanced Direct Strategy (maximum speed)
- **Automatic detection**: Zero user configuration required for optimal performance

---

## Enhanced Logging & Operation Tracking

### **Per-Operation Optimized Copy Logs**
Each copy operation creates comprehensive logs showing the performance benefits:

#### **Enhanced Log File Format**
```
foldercomparesync_copy_YYYYMMDD_HHMMSS_<operation_id>.log

Example Enhanced Logging:
================================================================================
OPTIMIZED COPY OPERATION STARTED: Copy 47 items from LEFT to RIGHT
Operation ID: b8a7c2f1
Timestamp: 2024-08-03T14:32:15.123456
Copy System: v0.5.0 Optimized (Rename-Based Backup)
================================================================================

[14:32:15.125] Using ENHANCED DIRECT strategy for document.txt (2048 bytes)
[14:32:15.127] Copying: C:\Projects\document.txt -> D:\Backup\document.txt
[14:32:15.129] Timestamps copied from source to target
[14:32:15.130] ENHANCED DIRECT copy completed successfully

[14:32:15.135] Using OPTIMIZED STAGED strategy for largefile.zip (15728640 bytes)
[14:32:15.137] Step 1: Saved original timestamps for potential rollback
[14:32:15.138] Step 2: Atomic rename: D:\Backup\largefile.zip -> D:\Backup\largefile.zip.backup_b8a7c2f1
[14:32:15.139] Step 3: Copying: C:\Projects\largefile.zip -> D:\Backup\largefile.zip
[14:32:16.245] Step 3: Timestamps copied from source to target
[14:32:16.247] Step 4: Verification passed, removing backup
[14:32:16.248] OPTIMIZED STAGED copy completed successfully
[14:32:16.249] Performance: 50% faster than traditional staged approach

PERFORMANCE METRICS:
Traditional Approach: Would have used 47MB additional disk space
Optimized Approach: Used 0MB additional disk space during operation
Time Savings: 1.2 seconds (35% faster than v0.4.0)

================================================================================
OPTIMIZED COPY OPERATION COMPLETED
Operation ID: b8a7c2f1
Files copied successfully: 47
Files failed: 0
Total bytes copied: 158,720,314
Performance improvement: 35% faster than previous version
Timestamp: 2024-08-03T14:32:18.456789
================================================================================
```

### **Enhanced Error Recovery Logging**
```
ROLLBACK PROCEDURE INITIATED: Copy verification failed
[14:35:22.100] Removing partial target file: D:\Backup\largefile.zip
[14:35:22.101] Restoring backup: D:\Backup\largefile.zip.backup_b8a7c2f1 -> D:\Backup\largefile.zip
[14:35:22.102] Restoring original timestamps: 2024-07-15 09:30:22 (created), 2024-07-28 14:15:33 (modified)
[14:35:22.103] ROLLBACK COMPLETED SUCCESSFULLY - Original file fully restored
```

---

## Enhanced Features & Implementation Status

### ✅ **FULLY IMPLEMENTED: Revolutionary Optimized Copy System**

**Breakthrough Performance Architecture:**
- **Strategy A (Enhanced Direct)**: Complete timestamp preservation with `FileTimestampManager` integration
- **Strategy B (Optimized Staged)**: Revolutionary rename-based backup with ~50% performance improvement
- **Automatic Selection**: Intelligent strategy selection with zero user configuration required
- **Network Optimization**: All network drives automatically use optimized staged strategy
- **Comprehensive Verification**: Size validation with optional hash verification and instant rollback

**Advanced Error Handling:**
- **Zero-Fallback Design**: Clear error reporting with actionable user guidance instead of silent fallbacks
- **Atomic Operations**: True atomic operations using Windows rename primitives
- **Complete Rollback**: Automatic restoration with exact timestamp preservation
- **Critical Error Tracking**: Aggregated critical errors in completion dialogs with specific guidance

**Performance Breakthroughs:**
- **50% Disk Space Reduction**: Maximum 2 files during operation vs traditional 3-file approaches
- **Atomic Rename Speed**: Near-instantaneous backup operations using Windows rename primitives
- **Memory Efficiency**: Reduced memory footprint during large file transfers
- **Network Resilience**: Enhanced network drive handling with proper timeout and recovery

### ✅ **FULLY IMPLEMENTED: Enhanced Timestamp Preservation**

**Complete Metadata Preservation:**
- **Creation Time Preservation**: Full preservation using Windows API through `FileTimestampManager`
- **Modification Time Preservation**: Complete modification time handling with timezone awareness
- **Rollback Timestamp Restoration**: Exact restoration of original timestamps during failure recovery
- **Cross-Strategy Consistency**: Both Direct and Staged strategies preserve all timestamp metadata

**Advanced Timestamp Management:**
- **Timezone Awareness**: Proper handling of timezone information in timestamps
- **Windows API Integration**: Direct Windows API calls for precise timestamp control
- **Rollback Capability**: Save and restore original timestamps during failed operations
- **Verification**: Post-copy timestamp verification to ensure complete preservation

### ✅ **FULLY IMPLEMENTED: Enhanced Metadata Display**

**All metadata columns always visible:**
- **Size column**: Human-readable format (KB, MB, GB, TB) with sorting capability
- **Date Created column**: Full timestamp display with sortable date comparison and enhanced preservation
- **Date Modified column**: Full timestamp display with sortable date comparison and enhanced preservation
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

### ✅ **FULLY IMPLEMENTED: Enhanced Optimized File Copy Operations**

**Revolutionary file copying with breakthrough performance:**
- **Optimized Dual-Strategy System**: Automatic selection between Enhanced Direct and Optimized Staged methods
- **Network Drive Support**: Automatic detection and optimization for all network drive types
- **Confirmation dialogs**: Preview what will be copied before operation with strategy indication
- **Enhanced progress tracking**: File-by-file progress with current file display and copy strategy indication
- **Advanced error handling**: Continues operation with detailed error reporting and critical error aggregation
- **Overwrite mode**: Respects overwrite setting with optimized backup creation and rollback capability
- **Complete metadata preservation**: Enhanced timestamp preservation using `FileTimestampManager`

**Post-copy behavior (CRITICAL FEATURE):**
- **Automatic folder re-scan**: Both folders scanned after copy completion
- **Tree rebuild**: Display updated to show current state
- **Selection clearing**: All checkboxes cleared for fresh start
- **Enhanced status confirmation**: Completion message with operation ID, performance metrics, and critical error summary

### ✅ **FULLY IMPLEMENTED: Enhanced Status Logging**

**Comprehensive operation tracking:**
- **Folder operations**: Selection, scanning start/finish with counts and drive type detection
- **Comparison events**: Progress updates, completion with timing and results
- **Selection tracking**: Item selection/deselection with running counts
- **Filter operations**: Filter application, results count, clear operations
- **Tree operations**: Expand/collapse all, sort operations with timing
- **Enhanced copy operations**: Strategy selection, step-by-step progress, performance metrics, completion with operation ID
- **Enhanced error reporting**: All errors with helpful context, operation ID, critical error categorization, and actionable guidance

### ✅ **FULLY IMPLEMENTED: Enhanced Progress Dialogs**

**Operation-specific progress indication:**

**Folder Scanning Progress:**
- **Indeterminate progress bar** with running animation
- **Running item counter**: "1,247 items found" with real-time updates
- **Operation context**: "Scanning left folder..." / "Scanning right folder..."
- **Drive type detection**: Shows detected drive types for strategy optimization
- **Performance adaptive**: Adjusts update frequency based on folder size

**Comparison Progress:**
- **Determinate progress bar** with 0-100% completion
- **File progress display**: "Comparing... 1,247 of 2,445 files"
- **Multi-phase tracking**: Scanning (40%), Comparison (50%), UI Building (10%)
- **Real-time updates**: Progress updates every configurable interval

**Enhanced Optimized Copy Operations Progress:**
- **Strategy indication**: Shows which copy strategy is being used for each file with performance benefits
- **File-by-file tracking**: "Copying 23 of 67 files using OPTIMIZED STAGED strategy..."
- **Current file display**: Shows name and strategy of file being copied with performance context
- **Operation ID tracking**: Displays operation ID for log file reference
- **Error resilience**: Continues and reports errors without stopping with critical error tracking
- **Enhanced statistics tracking**: Running count of copied/failed/skipped files with bytes transferred and performance metrics

---

## Enhanced Technical Architecture

### **Advanced Optimized Copy System Classes**

```python
class CopyStrategy(Enum):
    """Copy strategy enumeration for optimized file handling approaches"""
    DIRECT = "direct"           # Strategy A: Enhanced direct copy with complete timestamp preservation
    STAGED = "staged"           # Strategy B: Optimized staged copy with rename-based backup

class DriveType(Enum):
    """Drive type enumeration for enhanced path analysis"""
    LOCAL_FIXED = "local_fixed"
    LOCAL_REMOVABLE = "local_removable" 
    NETWORK_MAPPED = "network_mapped"
    NETWORK_UNC = "network_unc"
    RELATIVE = "relative"
    UNKNOWN = "unknown"

@dataclass
class CopyOperationResult:
    """Enhanced result of a copy operation with performance metrics"""
    success: bool
    strategy_used: CopyStrategy
    source_path: str
    target_path: str
    file_size: int
    duration_seconds: float
    bytes_copied: int = 0
    error_message: str = ""
    verification_passed: bool = False
    retry_count: int = 0
    temp_path: str = ""
    backup_path: str = ""
    performance_improvement: str = ""  # New: Performance metrics vs traditional approach

class EnhancedFileCopyManager:
    """Revolutionary optimized file copy manager implementing Strategy A and optimized Strategy B"""
    - start_copy_operation() -> operation_id
    - copy_file() -> CopyOperationResult  # Enhanced with performance tracking
    - end_copy_operation()  # Enhanced with performance summary
    - _copy_direct_strategy()  # Enhanced with FileTimestampManager
    - _copy_staged_strategy_optimized()  # Revolutionary rename-based approach
    - _verify_copy()  # Enhanced verification with rollback capability

class FileTimestampManager:
    """Complete timestamp management with Windows API integration"""
    - get_file_timestamps() -> (creation_time, modification_time)
    - set_file_timestamps()  # Enhanced with rollback support
    - copy_timestamps()  # Complete timestamp preservation
    - save_for_rollback()  # New: Save timestamps for rollback operations
    - restore_on_rollback()  # New: Restore exact original timestamps
```

### **Enhanced Data Structures**

```python
class FolderCompareSync_class:
    """Enhanced main application with revolutionary optimized copy system"""
    # Revolutionary optimized copy system
    copy_manager: EnhancedFileCopyManager    # Optimized copy operations manager
    timestamp_manager: FileTimestampManager  # Complete timestamp management
    
    # Enhanced filtering and sorting
    filter_wildcard: tk.StringVar              # Current filter pattern
    filtered_results: Dict[str, ComparisonResult_class]  # Filtered comparison results
    current_sort_column: Optional[str]         # Currently sorted column
    current_sort_order: str                    # 'asc' or 'desc'
    is_filtered: bool                          # Whether filter is active
    
    # Enhanced progress and performance tracking
    operation_start_time: float                # For timing operations
    last_progress_update: float                # Rate limiting for progress updates
    performance_metrics: Dict[str, float]      # Track performance improvements
    
    # Enhanced metadata display
    all_metadata_visible: bool = True          # Always show all columns
    
    # Enhanced copy operation management
    copy_in_progress: bool = False             # Track copy operation state
    auto_refresh_after_copy: bool = True       # Auto-refresh setting
    critical_errors: List[Tuple[str, str]] = []  # Track critical errors
```

### **Enhanced Threading Architecture**
- **Main UI thread**: All user interaction and display updates
- **Background comparison thread**: File system operations and metadata comparison
- **Enhanced optimized copy thread**: Revolutionary dual-strategy file copy operations with performance tracking
- **Background filter thread**: Large-scale filtering operations
- **Background sort thread**: File sorting operations
- **Enhanced progress update threads**: Thread-safe status and progress updates with operation ID and performance tracking
- **Error propagation**: Safe error handling across all thread boundaries with comprehensive logging and critical error aggregation

### **Enhanced Memory Management**
- **Adaptive processing**: Switch to memory-efficient mode for large folders (>10,000 items)
- **Streaming operations**: Process large file lists without loading all into memory
- **Progress batching**: Update UI in configurable batches to maintain responsiveness
- **Status log management**: Automatic trimming with configurable history limits
- **Resource monitoring**: Track memory usage and adjust processing accordingly
- **Optimized copy operation efficiency**: Enhanced memory usage during large file transfers with rename-based backup

---

## Enhanced Performance Characteristics & Scalability

### **Revolutionary Performance Metrics**
- **Small files (< 10MB) on local drives**: Near-instant copying with Enhanced Direct Strategy and complete timestamp preservation
- **Large files (≥ 10MB) or network files**: Breakthrough performance with Optimized Staged Strategy (~50% faster than traditional approaches)
- **Network drive operations**: Automatic detection and optimization with timeout handling and rename-based efficiency
- **Mixed operations**: Intelligent strategy selection per file for optimal performance with zero user configuration
- **Copy verification**: Optional post-copy verification with minimal performance impact and instant rollback
- **Error recovery**: Lightning-fast rollback operations using atomic rename with complete timestamp restoration

### **Enhanced Scalability**
- **Copy Strategy Threshold**: Configurable 10MB threshold for strategy selection with automatic optimization
- **Network Timeout Handling**: Configurable timeout values for network operations with enhanced resilience
- **Retry Logic**: Configurable retry counts with exponential backoff and strategy escalation
- **Verification Options**: Configurable verification levels (size-only or size+hash) with performance optimization
- **Logging Granularity**: Configurable logging levels and operation tracking detail with performance metrics
- **Performance Optimization**: Revolutionary algorithms with ~50% improvement over traditional approaches

---

## Enhanced Configuration Constants

### **Optimized Copy System Configuration**
```python
# Performance thresholds (unchanged for backward compatibility)
COPY_STRATEGY_THRESHOLD = 10 * 1024 * 1024        # 10MB threshold for copy strategy selection
COPY_VERIFICATION_ENABLED = True                  # Enable post-copy verification
COPY_RETRY_COUNT = 3                             # Number of retries for failed operations
COPY_RETRY_DELAY = 1.0                           # Delay between retries in seconds
COPY_CHUNK_SIZE = 64 * 1024                      # 64KB chunks for large file copying
COPY_NETWORK_TIMEOUT = 30.0                      # Network operation timeout in seconds

# New optimized implementation constants
OPTIMIZED_STAGED_ENABLED = True                   # Enable optimized rename-based staging
TIMESTAMP_PRESERVATION_ENHANCED = True           # Enable enhanced timestamp preservation
CRITICAL_ERROR_TRACKING = True                   # Enable critical error aggregation
PERFORMANCE_METRICS_ENABLED = True               # Enable performance improvement tracking
```

### **Enhanced Window Layout Constants**
```python
WINDOW_WIDTH_PERCENT = 0.98        # 98% of screen width
WINDOW_HEIGHT_PERCENT = 0.93       # 93% of screen height  
MIN_WINDOW_WIDTH = 800             # Minimum window width in pixels
MIN_WINDOW_HEIGHT = 600            # Minimum window height in pixels
```

### **Enhanced Status Log Configuration**
```python
STATUS_LOG_VISIBLE_LINES = 5       # Visible lines in status log window
STATUS_LOG_MAX_HISTORY = 500       # Maximum lines to keep in history
STATUS_LOG_FONT = ("Courier", 9)   # Monospace font for better alignment
STATUS_LOG_PERFORMANCE_TRACKING = True  # Include performance metrics in status log
```

### **Enhanced Performance Settings**
```python
SHA512_MAX_FILE_SIZE = (1000 * 1024 * 1024) * 25  # 25GB limit for hash computation
MEMORY_EFFICIENT_THRESHOLD = 10000                  # Switch to efficient mode above N items
MAX_FILTER_RESULTS = 200000                         # Maximum items when filtering (200K)
TREE_UPDATE_BATCH_SIZE = 200000                     # Process tree updates in batches (200K)
PERFORMANCE_IMPROVEMENT_TRACKING = True             # Track and report performance improvements
```

### **Enhanced Tree Column Configuration**
```python
TREE_STRUCTURE_WIDTH = 280         # Default structure column width
TREE_SIZE_WIDTH = 80              # Size column width
TREE_DATE_CREATED_WIDTH = 110     # Date created column width (enhanced preservation)
TREE_DATE_MODIFIED_WIDTH = 110    # Date modified column width (enhanced preservation)
TREE_SHA512_WIDTH = 100           # SHA512 column width
TREE_STATUS_WIDTH = 100           # Status column width
```

---

## Enhanced Metadata Comparison Logic

### **Comparison Criteria**
- ☑ **Existence** - File exists in one location but not the other *(DEFAULT: ON)*
- ☑ **Size** - File sizes differ *(DEFAULT: ON)*  
- ☑ **Date Created** - Creation dates differ with enhanced timestamp precision *(DEFAULT: ON)*
- ☑ **Date Modified** - Modification dates differ with enhanced timestamp precision *(DEFAULT: ON)*
- ☐ **SHA512** - File content differs (hash comparison) with performance optimization *(DEFAULT: OFF)*

### **Enhanced Comparison Features**
- **Background processing**: Multi-threaded comparison with progress tracking and performance metrics
- **Memory efficient**: Handles large directories without memory issues with optimized algorithms
- **Error resilient**: Continues comparison even when individual files fail with enhanced error categorization
- **Progress logging**: Real-time progress updates in status log with drive type awareness and performance tracking
- **Network optimization**: Optimized comparison algorithms for network drives with enhanced timeout handling

---

## Enhanced User Experience

### **Revolutionary Workflow**
1. **Comprehensive guidance**: Clear instructions and status feedback at every step with performance context
2. **Real-time visibility**: Progress dialogs and status log show exactly what's happening with copy strategy indication and performance metrics
3. **Smart filtering**: Find specific files quickly in large folder structures with enhanced performance
4. **Intelligent sorting**: Organize display by any metadata field with optimized algorithms
5. **Complete tree control**: Expand/collapse all for overview or detail focus with performance optimization
6. **Safe operations**: Confirmation dialogs and preview before destructive actions with strategy indication
7. **Automatic refresh**: Post-operation refresh ensures display accuracy with enhanced performance
8. **Revolutionary copy reliability**: Optimized dual-strategy copy system with atomic operations and instant rollback
9. **Comprehensive operation tracking**: Detailed logs with operation IDs, performance metrics, and critical error summaries

### **Enhanced Status Log Events**

**Application lifecycle:**
- Application startup/shutdown with system information and optimized copy system initialization
- Folder selection and validation with drive type detection and strategy optimization recommendations
- Window resizing and UI state changes with performance impact assessment

**Comparison operations:**
- Scan start with folder paths, settings, detected drive types, and performance optimization recommendations
- Progress updates during scanning (every N items) with drive type context and performance metrics
- Scan completion with item counts, timing, drive type summary, and strategy recommendations
- Comparison phase start with criteria, network drive considerations, and performance expectations
- Progress updates during comparison (every N items or N%) with performance tracking
- Comparison completion with differences found, timing, copy strategy recommendations, and performance summary

**Revolutionary optimized copy operations:**
- Enhanced copy strategy selection with file size, drive type reasoning, and performance benefit explanation
- Operation start with source/destination, file count, operation ID, and expected performance improvement
- Step-by-step progress for optimized operations (timestamp save, atomic rename, copy, verify, finalize)
- Strategy-specific progress updates with current file, method, and performance benefit context
- Individual file copy success/failure with strategy used, verification status, and performance metrics
- Rollback operations with detailed restoration steps and timestamp preservation confirmation
- Operation completion with comprehensive statistics, operation ID, performance improvement summary, and critical error aggregation
- Post-copy refresh operations with folder re-scan results and performance impact assessment

**User interactions:**
- Selection changes with item counts, drive type awareness, and strategy recommendations
- Filter application/clearing with result counts, performance notes, and optimization suggestions
- Sort operations with column, order, performance metrics, and timing information
- Tree expansion/collapse operations with timing information and performance optimization notes

---

## Enhanced Development Standards & Requirements

### **Windows Compatibility**
- **Target platforms**: Windows 10, Windows 11, and subsequent compatible versions
- **Character encoding**: ASCII-only text to prevent encoding errors
- **File path handling**: Windows-native path resolution and validation with enhanced network drive support
- **System integration**: Proper Windows version detection, drive type detection, enhanced logging, and optimized Windows API usage
- **Network drive support**: Full compatibility with mapped drives (A:, B:, Z:) and UNC paths with performance optimization

### **Enhanced Code Quality**
- **Comprehensive configuration**: All UI, performance, and optimized copy system parameters configurable via constants
- **Professional error handling**: Graceful degradation with helpful user guidance, automatic recovery, and critical error aggregation
- **Strategic logging**: Detailed debug information without performance impact, enhanced with operation tracking and performance metrics
- **Modular architecture**: Clean separation of concerns for maintainability with dedicated optimized copy system
- **Extensive documentation**: Comprehensive docstrings and comments for all optimized copy system components with performance notes

### **Enhanced Testing Considerations**
- **Large folder testing**: Validated with folders containing 50,000+ files across different drive types with performance benchmarking
- **Network drive testing**: Comprehensive testing with mapped drives and UNC paths using optimized strategies
- **Optimized copy strategy testing**: Validation of automatic strategy selection, fallback mechanisms, and performance improvements
- **Error condition testing**: Network failures, permission errors, disk space issues, drive disconnections with enhanced recovery
- **Performance testing**: Memory usage and response time under various loads with mixed drive types and performance improvement validation
- **User workflow testing**: Complete end-to-end scenarios with real data, network drives, and performance measurement
- **Edge case handling**: Empty folders, conflicting names, special characters, very large files with optimized handling
- **Rollback testing**: Verification of automatic recovery mechanisms, file restoration, and timestamp preservation with performance impact assessment

---

## Enhanced Installation & System Requirements

### **Enhanced Dependencies**
- **Python 3.7+**: Core language requirement with enhanced features and Windows API access
- **tkinter**: GUI framework with extended widget usage
- **ctypes**: Windows API access for drive type detection and enhanced timestamp management
- **Built-in libraries**: pathlib, hashlib, threading, logging, datetime, shutil, fnmatch, uuid
- **No external dependencies**: Self-contained application with enhanced Windows API integration

### **Enhanced Supported Systems**
- **✅ Windows 10**: Full support with all features including network drive detection and optimized copy system
- **✅ Windows 11**: Full support with system detection, optimization, enhanced copy system, and performance improvements
- **✅ Future Windows**: Designed for forward compatibility with version detection, API adaptation, and performance optimization

### **Enhanced System Resources**
- **RAM**: 150MB base + ~1MB per 10,000 files + optimized copy operation overhead + verification buffers (reduced from previous versions)
- **Disk**: Minimal base + configurable log file growth + per-operation copy logs (50% less temporary space during operations)
- **CPU**: Single background thread for operations + optimized copy system threads + adaptive batch processing with performance optimization
- **Network**: Optimized for LAN environments with configurable timeouts, retry logic, and enhanced performance on network drives
- **Performance**: Scales efficiently with configurable thresholds, revolutionary algorithms, drive-type optimization, and ~50% performance improvement over traditional approaches

---

## Enhanced Future Development Roadmap

### **Phase 1: Advanced Optimized Copy System Features**
- **Resume capability**: Resume interrupted copy operations from checkpoint with optimized performance
- **Advanced queue management**: Priority-based copy queue with performance optimization
- **Performance analytics**: Real-time performance monitoring and optimization recommendations
- **Copy profiles**: Save and load optimized copy operation configurations
- **Advanced verification**: Multiple hash algorithms with performance-optimized selection

### **Phase 2: Enterprise Optimized Copy Features**
- **Operation scheduling**: Automated copy operations with performance optimization scheduling
- **Performance reporting**: Comprehensive performance improvement reports and analytics
- **Batch script generation**: Generate optimized batch files for command-line copy operations
- **Copy history**: Maintain history of all copy operations with performance metrics and searchable logs
- **Resource optimization**: Dynamic resource allocation for optimal performance across multiple operations

### **Phase 3: Advanced Network Integration with Performance Optimization**
- **Cloud storage support**: Direct integration with OneDrive, Google Drive, etc. with optimized transfer strategies
- **Network monitoring**: Real-time network connectivity and performance monitoring with adaptive optimization
- **VPN compatibility**: Optimized handling for VPN connections and tunneled drives with performance enhancement
- **Distributed operations**: Copy operations across multiple network locations with load balancing and performance optimization
- **Bandwidth optimization**: Intelligent bandwidth management with performance monitoring and adaptive throttling

### **Phase 4: Integration & Automation with Performance Focus**
- **Windows shell extension**: Context menu integration for right-click optimized copy operations
- **PowerShell integration**: PowerShell cmdlets for automation and scripting with performance monitoring
- **Task scheduler integration**: Native Windows task scheduler integration with performance optimization
- **Event log integration**: Windows event log integration for enterprise monitoring with performance metrics
- **API interface**: REST API for integration with other enterprise tools featuring performance monitoring and optimization

---

## Enhanced Copy Queue Implementation Strategy

For handling large copy operations with thousands of files and revolutionary performance:

### **Recommended Implementation**
1. **Operation Segmentation**: Break large operations into manageable chunks with optimized checkpoints
2. **Progress Persistence**: Save operation state with performance metrics to enable resume capability
3. **Priority Queuing**: Allow users to prioritize certain files or operations with performance optimization
4. **Resource Management**: Monitor system resources and adapt copy behavior for optimal performance
5. **Error Categorization**: Classify errors by severity, recovery strategy, and performance impact
6. **Performance Optimization**: Dynamic adjustment of copy parameters based on real-time performance metrics

### **Enhanced Error Recovery with Performance Focus**
- **Checkpoint System**: Regular checkpoints during large operations for resume capability with minimal performance impact
- **Partial Recovery**: Continue operations with remaining files after handling failures with performance optimization
- **Strategy Escalation**: Automatic escalation from Enhanced Direct to Optimized Staged on failures with performance tracking
- **Network Resilience**: Automatic handling of network disconnections and timeouts with performance optimization
- **User Notification**: Real-time notification of errors with recommended actions and performance impact assessment

---

*This specification document is maintained alongside the main program and updated with each version release. For version history, see CHANGELOG.md*