# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
from FolderCompareSync_Global_Imports import *

"""
KNOW THIS: "import FolderCompareSync_Global_Constants as C"  vs  "from FolderCompareSync_Global_Constants import *"
-------------------------------------------------------------------------------------------------------------------

In Python, modules are singletons per process — they live ONCE in sys.modules.
Because Python caches imported modules in sys.modules, any object you put in a module becomes
a process-wide singleton. 
Imported modules are dynamically shared by modules as long as every module imports
that same module via "import xxx as Y".
Hence module level global variables in an imported module are dynamically shared by modules as long as
every module imports that same module via "import xxx as Y".

When module A does:
    import FolderCompareSync_Global_Constants as C
Python looks in sys.modules:
If the module has not been loaded yet, it’s imported and inserted into sys.modules["FolderCompareSync_Global_Constants"].
Module A then binds its local name C to that single module object.

When module B later does the same import:
    import FolderCompareSync_Global_Constants as C
Python checks sys.modules, sees it’s already loaded, and reuses the same module object.
Module B then binds its local name C to that same object.

So:
"C in A" and "C in B" are just two different references to the same underlying module object.
If a separate module DebugGlobalEditor modifies C.STATUS_LOG_MAX_HISTORY, both module A and module B
see the updated value in C.STATUS_LOG_MAX_HISTORY IMMEDIATELY because they reference the same module object.

What wouldn’t see changes is if module D instead did:
    from FolderCompareSync_Global_Constants import STATUS_LOG_MAX_HISTORY
Using "from ... import ..." COPIES the value into module D’s local globals at import time, so 
- later updates to STATUS_LOG_MAX_HISTORY in module D will NOT propagate back into sys.modules
- later updates to "C.STATUS_LOG_MAX_HISTORY" by other modules using "import ... as C" will NOT be seen by module D

Summary:
1. "import … as C"    ->  shared live module object (safe for on-the-fly editing).
2. "from … import X"  ->  copies the value at import time (edits won’t propagate).

Example code that shares dynamically:
    from __future__ import annotations
    import FolderCompareSync_Global_Constants as C     # reference constants via "C.variable_name"

Example code that DOES NOT share dynamically:
    from __future__ import annotations
    from FolderCompareSync_Global_Constants import *   # reference constants via "variable_name" (no "C.")
"""

# ============================================================================
# GLOBAL CONFIGURATION CONSTANTS
# ============================================================================
# These constants control various aspects of the application behavior and UI.
# Modify these values to customize the application without hunting through code.

# Performance and file handling limits
MAX_FILES_FOLDERS = 100000         # Maximum number of files/folders supported for performance
STATUS_LOG_MAX_HISTORY = 5000      # Maximum lines to keep in status history (expanded from 500)

# >>> CHANGE START # per chatGPT [logging presentation knobs]
# Console shows only the last N frames of the call chain; file logs keep the full chain.
# Keep this small (e.g., 2–4) for compact on-screen logs.
FLUSHED_LOGGING_CALLPATH_LAST_N = 3
# <<< CHANGE END

# Window sizing and layout constants
WINDOW_WIDTH_PERCENT = 0.98        # 98% of screen width
WINDOW_HEIGHT_PERCENT = 0.93       # 93% of screen height  
MIN_WINDOW_WIDTH = 800             # Minimum window width in pixels
MIN_WINDOW_HEIGHT = 600            # Minimum window height in pixels
WINDOW_TOP_OFFSET = 0              # Pixels from top of screen

# Progress dialog appearance and behavior
PROGRESS_DIALOG_WIDTH = 400        # Progress dialog width in pixels
PROGRESS_DIALOG_HEIGHT = 150       # Progress dialog height in pixels
PROGRESS_ANIMATION_SPEED = 10      # Animation speed for indeterminate progress
PROGRESS_UPDATE_FREQUENCY = 100    # Update progress every N items processed
PROGRESS_PERCENTAGE_FREQUENCY = 1  # Update percentage display every N%

# File processing limits and thresholds
SHA512_MAX_FILE_SIZE = (1000 * 1024 * 1024) * 25  # 25 GB filesize limit for hash computation
SHA512_STATUS_MESSAGE_THRESHOLD = 100 * 1024 * 1024  # 100 MB - Show status for files larger than this
COPY_PREVIEW_MAX_ITEMS = 10                       # Max items to show in copy preview dialog
SCAN_PROGRESS_UPDATE_INTERVAL = 50                # Update scanning progress every N items
COMPARISON_PROGRESS_BATCH = 100                   # Process comparison updates every N items

# Copy System Configuration (Legacy - kept for backward compatibility)
COPY_VERIFICATION_ENABLED = True                 # Enable post-copy simple verification
COPY_RETRY_COUNT = 3                             # Number of retries for failed operations
COPY_RETRY_DELAY = 1.0                           # Delay between retries in seconds
COPY_CHUNK_SIZE = 64 * 1024                      # 64KB chunks for large file copying
COPY_NETWORK_TIMEOUT = 30.0                      # Network operation timeout in seconds

# ============================================================================
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
FILECOPY_LONG_PATH_NORMALIZATION = True                 # Enable \\?\ prefix support

# Progress Reporting Configuration (M06, M11)
FILECOPY_PROGRESS_UPDATE_FREQUENCY_HZ = 2.0              # Progress updates per second was 20.0
FILECOPY_PROGRESS_CANCELLATION_CHECK_MS = 1000           # Target cancellation responsiveness (ms) was 500

# Enhanced Network Detection Control Flags
FILECOPY_ENABLE_CLOUD_DETECTION = True                  # Enable cloud storage detection
FILECOPY_ENABLE_SYMLINK_RESOLUTION = True               # Resolve symbolic links for network detection

# Cloud Storage Detection Patterns (configurable)
FILECOPY_CLOUD_STORAGE_PATTERNS = [
    '\\ONEDRIVE\\', '\\ONEDRIVE - ',                    # OneDrive personal and business
    '\\GOOGLE DRIVE\\',                                  # Google Drive
    '\\DROPBOX\\',                                       # Dropbox
    '\\BOX\\', '\\BOX SYNC\\',                          # Box storage
    '\\ICLOUD DRIVE\\',                                  # iCloud Drive
    '\\AMAZON DRIVE\\',                                  # Amazon Drive
]

# ============================================================================
# WINDOWS API CONSTANTS AND STRUCTURES (M13, M15)
# ============================================================================

# File Copy Constants
FILECOPY_COPY_FILE_FAIL_IF_EXISTS = 0x00000001
FILECOPY_COPY_FILE_RESTARTABLE = 0x00000002
FILECOPY_COPY_FILE_OPEN_SOURCE_FOR_WRITE = 0x00000004
FILECOPY_COPY_FILE_ALLOW_DECRYPTED_DESTINATION = 0x00000008

# Progress Callback Constants
FILECOPY_PROGRESS_CONTINUE = 0
FILECOPY_PROGRESS_CANCEL = 1
FILECOPY_PROGRESS_STOP = 2
FILECOPY_PROGRESS_QUIET = 3

# Copy Callback Reasons
FILECOPY_CALLBACK_CHUNK_FINISHED = 0x00000000
FILECOPY_CALLBACK_STREAM_SWITCH = 0x00000001

# Windows Error Codes
FILECOPY_ERROR_SUCCESS = 0
FILECOPY_ERROR_REQUEST_ABORTED = 1235
FILECOPY_ERROR_DISK_FULL = 112
FILECOPY_ERROR_HANDLE_DISK_FULL = 39
FILECOPY_ERROR_NOT_ENOUGH_MEMORY = 8
FILECOPY_ERROR_ACCESS_DENIED = 5
FILECOPY_ERROR_FILE_NOT_FOUND = 2
FILECOPY_ERROR_PATH_NOT_FOUND = 3
FILECOPY_ERROR_FILE_EXISTS = 80
FILECOPY_ERROR_ALREADY_EXISTS = 183

# Drive Type Constants
FILECOPY_DRIVE_UNKNOWN = 0
FILECOPY_DRIVE_NO_ROOT_DIR = 1
FILECOPY_DRIVE_REMOVABLE = 2
FILECOPY_DRIVE_FIXED = 3
FILECOPY_DRIVE_REMOTE = 4
FILECOPY_DRIVE_CDROM = 5
FILECOPY_DRIVE_RAMDISK = 6

# File Attribute Constants
FILECOPY_FILE_ATTRIBUTE_SPARSE_FILE = 0x200
FILECOPY_FILE_ATTRIBUTE_COMPRESSED = 0x800
FILECOPY_FILE_ATTRIBUTE_ENCRYPTED = 0x4000
FILECOPY_INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

# File Access and Share Constants
FILECOPY_GENERIC_WRITE = 0x40000000
FILECOPY_FILE_WRITE_ATTRIBUTES = 0x100
FILECOPY_FILE_SHARE_READ = 0x00000001
FILECOPY_FILE_SHARE_WRITE = 0x00000002
FILECOPY_OPEN_EXISTING = 3
FILECOPY_FILE_ATTRIBUTE_NORMAL = 0x80
FILECOPY_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILECOPY_INVALID_HANDLE_VALUE = -1

# Enhanced Path Resolution Constants
FILECOPY_FILE_NAME_NORMALIZED = 0x0
FILECOPY_FILE_NAME_OPENED = 0x8
FILECOPY_VOLUME_NAME_DOS = 0x0
FILECOPY_VOLUME_NAME_GUID = 0x1
FILECOPY_VOLUME_NAME_NT = 0x2
FILECOPY_VOLUME_NAME_NONE = 0x4

# Performance and debug settings
DEBUG_LOG_FREQUENCY = 100           # Log debug info every N items (avoid spam in large operations)
TREE_UPDATE_BATCH_SIZE = 200000     # Process tree updates in batches of N items (used in sorting)
MEMORY_EFFICIENT_THRESHOLD = 10000  # Switch to memory-efficient mode above N items

# Tree column configuration (default widths)
LEFT_SIDE_LOWERCASE = 'left'.lower()
LEFT_SIDE_UPPERCASE = LEFT_SIDE_LOWERCASE.upper()
RIGHT_SIDE_LOWERCASE = 'right'.lower()
RIGHT_SIDE_UPPERCASE = RIGHT_SIDE_LOWERCASE.upper()
#
TREE_STRUCTURE_WIDTH = 350         # Default structure column width
TREE_STRUCTURE_MIN_WIDTH = 120     # Minimum structure column width
TREE_SIZE_WIDTH = 50               # Size column width
TREE_SIZE_MIN_WIDTH = 30           # Minimum size column width
TREE_DATE_CREATED_WIDTH = 140      # Date created column width # v001.0010 changed - increased width for full precision timestamps
TREE_DATE_CREATED_MIN_WIDTH = 120  # Minimum date created column width # v001.0010 changed - increased minimum width for full precision timestamps
TREE_DATE_MODIFIED_WIDTH = 140     # Date modified column width # v001.0010 changed - increased width for full precision timestamps
TREE_DATE_MODIFIED_MIN_WIDTH = 120 # Minimum date modified column width # v001.0010 changed - increased minimum width for full precision timestamps
TREE_SHA512_WIDTH = 100            # SHA512 column width (first 16 chars)
TREE_SHA512_MIN_WIDTH = 80         # Minimum SHA512 column width
TREE_STATUS_WIDTH = 100            # Status column width
TREE_STATUS_MIN_WIDTH = 80         # Minimum status column width

# Tree row height configuration # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_VERY_PACKED = 14   # REALLY Packed them up spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_PACKED = 16        # Packed them up spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_VERY_COMPACT = 18  # Quite tight spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_COMPACT = 20       # Tight spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_NORMAL = 22        # Comfortable spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_DEFAULT = 24       # Tkinter default spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_LOOSE = 26         # Relaxed spacing # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT_VERY_LOOSE = 28    # Very relaxed spacing # v001.0015 added [tree row height control for compact display]

# Active tree row height setting - change this to switch spacing globally # v001.0015 added [tree row height control for compact display]
TREE_ROW_HEIGHT = TREE_ROW_HEIGHT_VERY_COMPACT  # v001.0015 added [tree row height control for compact display]

# Font scaling configuration # v001.0014 added [font scaling system for UI text size control]
UI_FONT_SCALE = 1                  # v001.0014 added [font scaling system for UI text size control]
                                   # Global font multiplier (can be Real number)- KEEP AT 1 for direct as-is font sizes
                                   # (1 = no scaling, 1.2 = 20% larger, etc.)
                                   # Font scaling infrastructure preserved for future use if needed

# Specific font sizes # v001.0014 added [font scaling system for UI text size control]
BUTTON_FONT_SIZE = 10               # Button text size (default ~9, so +1) # v001.0014 added [font scaling system for UI text size control]
LABEL_FONT_SIZE = 11                # Label text size (default ~8, so +3) # v001.0014 added [font scaling system for UI text size control]
ENTRY_FONT_SIZE = 11                # Entry field text size (default ~8, so +3) # v001.0014 added [font scaling system for UI text size control]
CHECKBOX_FONT_SIZE = 11             # Checkbox text size (default ~8, so +3) # v001.0014 added [font scaling system for UI text size control]
DIALOG_FONT_SIZE = 11               # Dialog text size # v001.0014 added [font scaling system for UI text size control]
STATUS_MESSAGE_FONT_SIZE = 12       # Status message text size # v001.0014 added [font scaling system for UI text size control]
INSTRUCTION_FONT_SIZE = 11          # formerly INSTRUCTION_TEXT_SIZE Font size for instructional text
# pre-calculate scaled font sizes
SCALED_BUTTON_FONT_SIZE = ( BUTTON_FONT_SIZE * UI_FONT_SCALE )                 # Button text size (default ~9, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_LABEL_FONT_SIZE = ( LABEL_FONT_SIZE * UI_FONT_SCALE )                   # Label text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_ENTRY_FONT_SIZE = ( ENTRY_FONT_SIZE * UI_FONT_SCALE )                   # Entry field text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_CHECKBOX_FONT_SIZE = ( CHECKBOX_FONT_SIZE * UI_FONT_SCALE )             # Checkbox text size (default ~8, so +2) # v001.0014 added [font scaling system for UI text size control]
SCALED_DIALOG_FONT_SIZE = ( DIALOG_FONT_SIZE * UI_FONT_SCALE )                 # Dialog text size # v001.0014 added [font scaling system for UI text size control]
SCALED_STATUS_MESSAGE_FONT_SIZE = ( STATUS_MESSAGE_FONT_SIZE * UI_FONT_SCALE ) # Status message text size # v001.0014 added [font scaling system for UI text size control]
SCALED_INSTRUCTION_FONT_SIZE = ( INSTRUCTION_FONT_SIZE * UI_FONT_SCALE )       # Font size for instructional text

# Status log configuration
STATUS_LOG_VISIBLE_LINES = 6       # Visible lines in status log window
STATUS_LOG_FONT = ("Courier", SCALED_STATUS_MESSAGE_FONT_SIZE)   # v001.0016
STATUS_LOG_BG_COLOR = "#f8f8f8"    # Light background color
STATUS_LOG_FG_COLOR = "#333333"    # Dark text color

# Display colors and styling
MISSING_ITEM_COLOR = "gray"           # Color for missing items in tree
INSTRUCTION_TEXT_COLOR = "royalblue"  # Color for instructional text
FILTER_HIGHLIGHT_COLOR = "#ffffcc"    # Background color for filtered items

# Filtering and sorting configuration
MAX_FILTER_RESULTS = 200000       # Maximum items to show when filtering (performance)

TIMESTAMP_TOLERANCE_CREATED_SECONDS = 0.01   # Specific tolerance for date_created comparisons  
TIMESTAMP_TOLERANCE_MODIFIED_SECONDS = 0.01  # Specific tolerance for date_modified comparisons

# Alternative tolerance presets for different scenarios
TIMESTAMP_TOLERANCE_EXACT = 0.0              # Exact equality (unreasonable even in NTFS)
TIMESTAMP_TOLERANCE_VERY_STRICT = 0.0001      # 1/10000th second
TIMESTAMP_TOLERANCE_QUITE_STRICT = 0.001      # 1/1000th  second
TIMESTAMP_TOLERANCE_REASONABLE = 0.01         # 1/100th   second
TIMESTAMP_TOLERANCE_LENIENT = 0.1             # 1/10th    second
TIMESTAMP_TOLERANCE_VERY_LENIENT = 1.0        # 1 second
TIMESTAMP_TOLERANCE_FAT32_SAFE = 2.0          # 2 seconds ... for FAT32 compatibility
# Timestamp comparison tolerance settings
TIMESTAMP_TOLERANCE = TIMESTAMP_TOLERANCE_REASONABLE # in fractions of a second
                                                                         
# ============================================================================
# DELETE ORPHANS CONFIGURATION CONSTANTS
# ============================================================================
# Delete Orphans Dialog Configuration
DELETE_ORPHANS_DIALOG_WIDTH_PERCENT = 0.40     # 50% of main window width  # v001.0013 changed [reduced delete orphans dialog width from 85% to 60%]
DELETE_ORPHANS_DIALOG_HEIGHT_PERCENT = 1.0     # Full height               # v001.0012 added [delete orphans dialog sizing]
DELETE_ORPHANS_STATUS_LINES = 10               # Visible lines in status log  # v001.0012 added [delete orphans status area]
DELETE_ORPHANS_STATUS_MAX_HISTORY = 5000       # Maximum lines to keep     # v001.0012 added [delete orphans status area]

# Delete Orphans Memory Management Thresholds
DELETE_LARGE_FILE_LIST_THRESHOLD = 1000        # Clear if >1000 files      # v001.0012 added [delete orphans memory management]
DELETE_LARGE_TREE_DATA_THRESHOLD = 5000        # Clear if >5000 tree items # v001.0012 added [delete orphans memory management]
DELETE_LARGE_SELECTION_THRESHOLD = 500         # Clear if >500 selected items # v001.0012 added [delete orphans memory management]

# Delete Orphans Progress and UI Configuration
DELETE_ORPHANS_PROGRESS_UPDATE_FREQUENCY = 50  # Update progress every N files # v001.0012 added [delete orphans progress]
DELETE_ORPHANS_TREE_STRUCTURE_WIDTH = 400      # Tree structure column width   # v001.0012 added [delete orphans tree display]
DELETE_ORPHANS_TREE_SIZE_WIDTH = 80            # Size column width             # v001.0012 added [delete orphans tree display]
DELETE_ORPHANS_TREE_STATUS_WIDTH = 120         # Status column width           # v001.0012 added [delete orphans tree display]

# Export only all ALL-CAPS names where they do not start with "_"
__all__ = [name for name in globals() if name.isupper() and not name.startswith("_")]

################################################################################
# Use this global constants file in the main program and every .py module like:
#    import FolderCompareSync_Global_Constants as C
################################################################################

#Tip: if you also want a few non-caps items (e.g., a function) exported, append them:
#   VERSION_INFO = "v1.2.3"
#   __all__.extend(["some_function_name", "VERSION_INFO"])
