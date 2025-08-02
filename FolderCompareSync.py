#!/usr/bin/env python3
"""
FolderCompareSync - A Folder Comparison and Syncing Tool

A GUI application for comparing two directory trees based on metadata and syncing them.

This tool provides a visual interface to compare two folder structures and identifying
differences based on file existence, size, dates, and SHA512 hashes.

Users can mark files/folders for copying between the two trees with overwrite options.

Author: hydra3333
License: AGPL-3.0
GitHub: https://github.com/hydra3333/FolderCompareSync

DEBUG & LOGGING:
================
This application uses Python's built-in __debug__ flag and logging for debugging:

1. __debug__ is a built-in Python constant and is:
   - True by default (debug mode) when "-O" on the python commandline is omitted  :  python FolderCompareSync.py
   - False when running with "-O" flag (optimized mode) on the python commandline :  python -O FolderCompareSync.py
   - i.e. using "-O" turns off debugging via __debug__
   - Controls assert statements and debug-only code

2. Running the application:
   - Debug mode (verbose):     python FolderCompareSync.py
   - Optimized mode (quiet):   python -O FolderCompareSync.py
   
3. Logging output:
   - File: foldercomparesync.log (always enabled, detailed log for troubleshooting)
   - Console: Real-time debug/info messages (only in debug mode when "-O" flag is omitted)

4. Turn debug loglevel on/off within section of code within any Class Method:
    # debug some specific section of code
    self.set_debug_loglevel(True)  # Turn on debug logging
    ...
    self.set_debug_loglevel(False)  # Turn off debug logging

    # If you hit an error and want more detail:
    if some_error_condition:
        self.set_debug_loglevel(True)  # Turn on debug logging
        logger.debug("Now getting detailed debug info...")
        ...
        self.set_debug_loglevel(False)  # Turn off debug logging

CHANGELOG:
==========
Version 0.2.6 (2024-08-02):
- ADDED: Full-width status log window at bottom with 5 visible lines and 200-line history
- ADDED: Progress dialogs for long operations (folder scanning, comparison, copying)
- ADDED: Comprehensive status logging for all major operations with timestamps
- ADDED: Real-time progress indication for folder scanning with running file/folder counts
- ADDED: Progress tracking for comparison operations with percentage completion
- ADDED: Selection change tracking and logging in status window
- ADDED: Global constants for easy configuration of UI parameters and performance settings
- ENHANCED: Professional user experience with clear operation feedback
- IMPROVED: UI layout restructured to accommodate status log window
- ADDED: Status log auto-scrolling and line limit management (200 lines max)
- ADDED: Threaded progress updates that don't block the main UI
- IMPROVED: User feedback for all operations from start to completion
- ENHANCED: Error reporting with helpful guidance displayed in status log
- IMPROVED: Code maintainability with configurable constants at top of file

Version 0.2.5 (2024-08-02):
- FIXED: Critical issue with expand/collapse operations clearing selection state
- FIXED: Smart folder selection - ticking folders now only selects different items underneath (not same/missing)
- FIXED: Console logging now conditional - only appears in debug mode, silent in optimized mode
- FIXED: Removed emoji arrows from copy buttons to prevent encoding errors on Windows
- IMPROVED: Selection state management completely independent of tree display state
- ENHANCED: Robust state preservation during all tree operations (expand/collapse/refresh)
- IMPROVED: tick_children() method now intelligently filters items based on comparison status
- ADDED: is_different_item() helper method for efficient difference checking
- ENHANCED: Tree event handling to prevent selection interference during UI operations
- IMPROVED: Better separation of concerns between selection logic and display logic
- FIXED: Edge cases in selection state preservation during tree manipulation
- IMPROVED: More reliable checkbox display updates that don't affect underlying selection state

Version 0.2.4 (2024-08-02):
- ADDED: Fully qualified root paths as selectable tree items with functional checkboxes
- CHANGED: "Unselect All Differences" buttons renamed to "Clear All" - now clear ALL selections
- IMPROVED: "Select All Differences" buttons now auto-clear all selections first for clean workflow
- IMPROVED: Missing items no longer have checkboxes and are non-clickable for logical consistency
- FIXED: Missing folders now properly display without checkboxes
- ADDED: Instructional text "select options then click Compare" for better user guidance
- IMPROVED: Root unticking logic with safety checks to prevent attempting to untick non-existent parents
- ENHANCED: Tree building to include qualified paths as root items with proper path mapping
- ENHANCED: Selection system to handle root-level selection and bulk operations more effectively
- ENHANCED: Missing folder detection using MissingFolder sentinel class for proper differentiation

Version 0.2.3 (2024-08-02):
- ADDED: Smart window sizing - automatically sizes to 98%(width) and 93%(height) of screen resolution
- ADDED: Window positioning at top of screen for optimal taskbar clearance
- FIXED: TypeError in tree building when files and folders have conflicting path names
- IMPROVED: Better path conflict resolution in tree structure building
- IMPROVED: Enhanced debug logging for tree building conflicts
- IMPROVED: Better screen real estate utilization for dual-pane view
- IMPROVED: Responsive design that works on all monitor sizes
- IMPROVED: Maintains minimum window size constraints (800x600)

Version 0.2.2 (2024-08-02):
- ADDED: Comprehensive Windows system information in debug logs
- ADDED: Windows build number and version name mapping (24H2, 23H2, etc.)
- ADDED: Windows edition detection (Home/Pro/Enterprise)
- ADDED: Computer name and detailed processor information
- ADDED: Better system identification for troubleshooting
- FIXED: Emoji encoding errors in log messages (replaced with ASCII)
- IMPROVED: More detailed system environment logging

Version 0.2.1 (2024-08-02):
- ADDED: Comprehensive logging system with __debug__ support
- ADDED: Debug mode explanation and usage instructions
- ADDED: Strategic debug logging throughout key functions
- ADDED: Assert statements for critical conditions
- ADDED: Log file output (foldercomparesync.log)
- IMPROVED: Error reporting with detailed stack traces
- IMPROVED: Performance monitoring with timing logs

Version 0.2.0 (2024-08-02):
- FIXED: TypeError when building trees due to NoneType comparison results
- FIXED: Missing item handling - now properly shows placeholders for missing files/folders
- FIXED: Empty folder support - empty directories are now included in comparison and trees
- FIXED: Status determination - now uses proper path mapping instead of name-only matching
- IMPROVED: Error handling for invalid/null paths during tree construction
- IMPROVED: Better tree structure building with null-safe operations
- ADDED: Proper path-to-item mapping for accurate status reporting
- ADDED: Support for preserving empty folder structures in sync operations

Version 0.1.0 (2024-08-01):
- Initial implementation with dual-pane folder comparison
- Basic tree view with synchronized scrolling
- File metadata comparison (existence, size, dates, SHA512)
- Checkbox selection system with parent/child logic
- Background comparison threading
- Safety mode for copy operations (preview only)
"""

import platform
import os
import sys
import hashlib
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging

# ============================================================================
# GLOBAL CONFIGURATION CONSTANTS
# ============================================================================
# These constants control various aspects of the application behavior and UI.
# Modify these values to customize the application without hunting through code.

# Window sizing and layout constants
WINDOW_WIDTH_PERCENT = 0.98        # 98% of screen width
WINDOW_HEIGHT_PERCENT = 0.93       # 93% of screen height  
MIN_WINDOW_WIDTH = 800             # Minimum window width in pixels
MIN_WINDOW_HEIGHT = 600            # Minimum window height in pixels
WINDOW_TOP_OFFSET = 0              # Pixels from top of screen

# Status log configuration
STATUS_LOG_VISIBLE_LINES = 5       # Visible lines in status log window
STATUS_LOG_MAX_HISTORY = 500       # Maximum lines to keep in history
STATUS_LOG_FONT = ("Courier", 9)   # Monospace font for better alignment
STATUS_LOG_BG_COLOR = "#f8f8f8"    # Light background color
STATUS_LOG_FG_COLOR = "#333333"    # Dark text color

# Progress dialog appearance and behavior
PROGRESS_DIALOG_WIDTH = 400        # Progress dialog width in pixels
PROGRESS_DIALOG_HEIGHT = 150       # Progress dialog height in pixels
PROGRESS_ANIMATION_SPEED = 10      # Animation speed for indeterminate progress
PROGRESS_UPDATE_FREQUENCY = 100    # Update progress every N items processed
PROGRESS_PERCENTAGE_FREQUENCY = 1  # Update percentage display every N%

# File processing limits and thresholds
SHA512_MAX_FILE_SIZE = 1000 * 1024 * 1024  # 1,000MB filesize limit for hash computation (a short gig)
COPY_PREVIEW_MAX_ITEMS = 10                # Max items to show in copy preview dialog
SCAN_PROGRESS_UPDATE_INTERVAL = 50         # Update scanning progress every N items
COMPARISON_PROGRESS_BATCH = 100            # Process comparison updates every N items

# Performance and debug settings
DEBUG_LOG_FREQUENCY = 100          # Log debug info every N items (avoid spam in large operations)
TREE_UPDATE_BATCH_SIZE = 20        # Process tree updates in batches of N items
MEMORY_EFFICIENT_THRESHOLD = 10000 # Switch to memory-efficient mode above N items

# Tree column configuration (default widths)
TREE_STRUCTURE_WIDTH = 300         # Default structure column width
TREE_STRUCTURE_MIN_WIDTH = 150     # Minimum structure column width
TREE_SIZE_WIDTH = 80              # Size column width
TREE_SIZE_MIN_WIDTH = 60          # Minimum size column width
TREE_DATE_WIDTH = 120             # Date column width
TREE_DATE_MIN_WIDTH = 100         # Minimum date column width
TREE_STATUS_WIDTH = 100           # Status column width
TREE_STATUS_MIN_WIDTH = 80        # Minimum status column width

# Display colors and styling
MISSING_ITEM_COLOR = "gray"       # Color for missing items in tree
INSTRUCTION_TEXT_COLOR = "darkblue"  # Color for instructional text
INSTRUCTION_TEXT_SIZE = 8         # Font size for instructional text

# ============================================================================
# LOGGING SETUP
# ============================================================================

# Setup logging loglevel based on __debug__ flag
# using "-O" on the python commandline turns __debug__ off:  python -O FolderCompareSync.py
if __debug__:
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
else:
    log_level = logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'

# Create handlers list - file logging always enabled, console logging only in debug mode
handlers = [
    logging.FileHandler(os.path.join(os.path.dirname(__file__), 'foldercomparesync.log'), mode='w')   # Always log to file
]

# Add console logging only in debug mode (when __debug__ is True)
if __debug__:
    handlers.append(logging.StreamHandler())  # Console output only in debug mode

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=handlers
)
logger = logging.getLogger(__name__)


@dataclass
class FileMetadata_class:
    """Stores file/folder metadata for comparison"""
    path: str
    name: str
    is_folder: bool
    size: Optional[int] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    sha512: Optional[str] = None
    exists: bool = True
    
    @classmethod
    def from_path(cls, path: str, compute_hash: bool = False):
        """Create FileMetadata from a file system path"""
        p = Path(path)
        if not p.exists():
            return cls(path=path, name=p.name, is_folder=False, exists=False)
        
        try:
            stat = p.stat()
            size = stat.st_size if p.is_file() else None
            date_created = datetime.fromtimestamp(stat.st_ctime)
            date_modified = datetime.fromtimestamp(stat.st_mtime)
            
            sha512 = None
            if compute_hash and p.is_file() and size and size < SHA512_MAX_FILE_SIZE:  # Use configurable limit
                try:
                    with open(path, 'rb') as f:
                        sha512 = hashlib.sha512(f.read()).hexdigest()
                except Exception:
                    pass  # Hash computation failed, leave as None
            
            return cls(
                path=path,
                name=p.name,
                is_folder=p.is_dir(),
                size=size,
                date_created=date_created,
                date_modified=date_modified,
                sha512=sha512,
                exists=True
            )
        except Exception:
            return cls(path=path, name=p.name, is_folder=False, exists=False)


@dataclass
class ComparisonResult_class:
    """Stores comparison result between left/right items"""
    left_item: Optional[FileMetadata_class]
    right_item: Optional[FileMetadata_class]
    differences: Set[str]  # Set of difference types: 'existence', 'size', 'date_created', 'date_modified', 'sha512'
    is_different: bool = False
    
    def __post_init__(self):
        self.is_different = len(self.differences) > 0


class ProgressDialog:
    """Progress dialog for long-running operations"""
    
    def __init__(self, parent, title, message, max_value=None):
        """
        Initialize progress dialog with configurable dimensions
        Args:
            parent: Parent window
            title: Dialog title
            message: Progress message
            max_value: Maximum value for percentage (None for indeterminate)
        """
        logger.debug(f"Creating progress dialog: {title}")
        
        self.parent = parent
        self.max_value = max_value
        self.current_value = 0
        
        # Create dialog window using global constants
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{PROGRESS_DIALOG_WIDTH}x{PROGRESS_DIALOG_HEIGHT}")
        self.dialog.resizable(False, False)
        
        # Center the dialog on parent
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create progress frame
        progress_frame = ttk.Frame(self.dialog, padding=20)
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # Progress message label
        self.message_var = tk.StringVar(value=message)
        ttk.Label(progress_frame, textvariable=self.message_var, 
                 font=("TkDefaultFont", 10)).pack(pady=(0, 10))
        
        # Progress bar or counter display
        if max_value is not None:
            # Determinate progress bar for operations with known total
            self.progress_bar = ttk.Progressbar(
                progress_frame, mode='determinate', maximum=max_value, length=300
            )
            self.progress_bar.pack(pady=(0, 10))
            
            # Percentage label
            self.percent_var = tk.StringVar(value="0%")
            ttk.Label(progress_frame, textvariable=self.percent_var).pack()
        else:
            # Indeterminate progress for operations with unknown total (like file counting)
            self.progress_bar = ttk.Progressbar(
                progress_frame, mode='indeterminate', length=300
            )
            self.progress_bar.pack(pady=(0, 10))
            self.progress_bar.start(PROGRESS_ANIMATION_SPEED)  # Use configurable animation speed
            
            # Running counter display
            self.count_var = tk.StringVar(value="0 items")
            ttk.Label(progress_frame, textvariable=self.count_var, 
                     font=("TkDefaultFont", 9)).pack()
        
        # Update the display
        self.dialog.update_idletasks()
        
        # Center on parent window using configurable dialog dimensions
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (PROGRESS_DIALOG_WIDTH // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (PROGRESS_DIALOG_HEIGHT // 2)
        self.dialog.geometry(f"{PROGRESS_DIALOG_WIDTH}x{PROGRESS_DIALOG_HEIGHT}+{x}+{y}")
        
    def update_message(self, message):
        """Update the progress message"""
        self.message_var.set(message)
        self.dialog.update_idletasks()
        
    def update_progress(self, value, message=None):
        """Update progress value and optionally message"""
        if self.max_value is not None:
            # Determinate progress
            self.current_value = value
            self.progress_bar['value'] = value
            percentage = int((value / self.max_value) * 100) if self.max_value > 0 else 0
            self.percent_var.set(f"{percentage}%")
        else:
            # Indeterminate progress - update counter
            self.count_var.set(f"{value:,} items")
            
        if message:
            self.message_var.set(message)
            
        self.dialog.update_idletasks()
        
    def close(self):
        """Close the progress dialog"""
        logger.debug("Closing progress dialog")
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.stop()  # Stop any animation
            self.dialog.grab_release()
            self.dialog.destroy()
        except tk.TclError:
            pass  # Dialog already destroyed


class FolderCompareSync_class:
    """Main application class for folder comparison and syncing"""
    
    def __init__(self):
        logger.info("Initializing FolderCompareSync application")
        global log_level
        if __debug__:
            if log_level == logging.DEBUG:
                logger.debug("Debug mode enabled - Debug log_level active")
            else:
                logger.debug("Debug mode enabled - non-Debug log_level active")
        
        self.root = tk.Tk()
        self.root.title("FolderCompareSync - Folder Comparison and Syncing Tool")
        
        # Get screen dimensions for smart window sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Use configurable window sizing percentages
        window_width = int(screen_width * WINDOW_WIDTH_PERCENT)
        window_height = int(screen_height * WINDOW_HEIGHT_PERCENT)
        
        # Center horizontally, use configurable top offset for optimal taskbar clearance
        x = (screen_width - window_width) // 2
        y = WINDOW_TOP_OFFSET
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)  # Use configurable minimum size
        
        # Application state variables
        self.left_folder = tk.StringVar()
        self.right_folder = tk.StringVar()
        self.compare_existence = tk.BooleanVar(value=True)
        self.compare_size = tk.BooleanVar(value=True)
        self.compare_date_created = tk.BooleanVar(value=True)
        self.compare_date_modified = tk.BooleanVar(value=True)
        self.compare_sha512 = tk.BooleanVar(value=False)
        self.overwrite_mode = tk.BooleanVar(value=True)
        
        # Data storage for comparison results and selection state
        self.comparison_results: Dict[str, ComparisonResult_class] = {}
        self.selected_left: Set[str] = set()
        self.selected_right: Set[str] = set()
        self.tree_structure: Dict[str, List[str]] = {'left': [], 'right': []}
        
        # Path mapping for proper status determination and tree navigation
        # Maps relative_path -> tree_item_id for efficient lookups
        self.path_to_item_left: Dict[str, str] = {}  # rel_path -> tree_item_id
        self.path_to_item_right: Dict[str, str] = {}  # rel_path -> tree_item_id
        
        # Store root item IDs for special handling in selection logic
        self.root_item_left: Optional[str] = None
        self.root_item_right: Optional[str] = None
        
        # Flag to prevent recursive display updates during tree operations
        self._updating_display = False
        
        # Status log management using configurable constants
        self.status_log_lines = []  # Store status messages
        self.max_status_lines = STATUS_LOG_MAX_HISTORY  # Use configurable maximum
        
        # UI References for widget interaction
        self.left_tree = None
        self.right_tree = None
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="Summary: No comparison performed")
        self.status_log_text = None  # Will be set in setup_ui
        
        if __debug__:
            logger.debug("Application state initialized with enhanced state management and configurable constants")
        
        self.setup_ui()
        self.add_status_message("Application initialized - Ready to compare folders")
        logger.info("Application initialization complete")

    def add_status_message(self, message):
        """
        Add a timestamped message to the status log using configurable history limit
        Args:
            message: Message to add to status log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_line = f"{timestamp} - {message}"
        
        # Add to our internal list
        self.status_log_lines.append(status_line)
        
        # Trim to configurable maximum lines
        if len(self.status_log_lines) > self.max_status_lines:
            self.status_log_lines = self.status_log_lines[-self.max_status_lines:]
            
        # Update the text widget if it exists
        if self.status_log_text:
            self.status_log_text.config(state=tk.NORMAL)
            self.status_log_text.delete('1.0', tk.END)
            self.status_log_text.insert('1.0', '\n'.join(self.status_log_lines))
            self.status_log_text.config(state=tk.DISABLED)
            self.status_log_text.see(tk.END)  # Auto-scroll to bottom
            
        logger.info(f"STATUS: {message}")

    def set_debug_loglevel(self, enabled: bool):
        """
        Toggle debug loglevel in logging on/off during runtime
        Args:
            enabled (bool): True to enable debug logging, False to disable
        Usage:
            # Enable debug logging
            app.set_debug_loglevel(True)
            # Disable debug logging  
            app.set_debug_loglevel(False)
        Can be called from:
            - Button/menu callback: lambda: self.set_debug_loglevel(True)
            - Keyboard shortcut handler
            - Error handler to get more details
            - Any method within the class: self.set_debug_loglevel(True)
        """
        global log_level
        if enabled:
            log_level = logging.DEBUG
            logger.info("[DEBUG] Debug logging enabled - Debug output activated")
        else:
            log_level = logging.INFO
            logger.info("[INFO] Debug logging disabled - Info mode activated")
        logger.setLevel(log_level)
        # Update status to show updated current mode
        if hasattr(self, 'status_var'):
            current_status = self.status_var.get()
            mode = "DEBUG" if enabled else "NORMAL"
            self.status_var.set(f"{current_status} ({mode})")

    def setup_ui(self):
        """Initialize the user interface with configurable constants for layout and styling"""
        logger.debug("Setting up user interface with configurable constants")
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding=10)
        folder_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Left folder selection
        ttk.Label(folder_frame, text="Left Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        left_entry = ttk.Entry(folder_frame, textvariable=self.left_folder, width=60)
        left_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_left_folder).grid(row=0, column=2)
        
        # Right folder selection
        ttk.Label(folder_frame, text="Right Folder:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        right_entry = ttk.Entry(folder_frame, textvariable=self.right_folder, width=60)
        right_entry.grid(row=1, column=1, sticky=tk.EW, padx=(0, 5), pady=(5, 0))
        ttk.Button(folder_frame, text="Browse", command=self.browse_right_folder).grid(row=1, column=2, pady=(5, 0))
        
        folder_frame.columnconfigure(1, weight=1)
        
        # Comparison options frame with instructional text
        options_frame = ttk.LabelFrame(main_frame, text="Comparison Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Comparison criteria checkboxes with instructional text
        criteria_frame = ttk.Frame(options_frame)
        criteria_frame.pack(fill=tk.X)
        
        # Add instructional text for better user guidance using configurable styling
        instruction_frame = ttk.Frame(criteria_frame)
        instruction_frame.pack(fill=tk.X)
        
        ttk.Label(instruction_frame, text="Compare Options:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Existence", variable=self.compare_existence).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Size", variable=self.compare_size).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Date Created", variable=self.compare_date_created).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="Date Modified", variable=self.compare_date_modified).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="SHA512", variable=self.compare_sha512).pack(side=tk.LEFT, padx=(0, 10))
        
        # Add instructional text for workflow guidance using configurable colors and font size
        ttk.Label(instruction_frame, text="← select options then click Compare", 
                 foreground=INSTRUCTION_TEXT_COLOR, 
                 font=("TkDefaultFont", INSTRUCTION_TEXT_SIZE, "italic")).pack(side=tk.LEFT, padx=(20, 0))
        
        # Overwrite mode and buttons (enhanced with new Clear All buttons)
        control_frame = ttk.Frame(options_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Left side controls
        left_controls = ttk.Frame(control_frame)
        left_controls.pack(side=tk.LEFT)
        
        ttk.Checkbutton(left_controls, text="Overwrite Mode", variable=self.overwrite_mode).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Button(left_controls, text="Compare", command=self.start_comparison).pack(side=tk.LEFT, padx=(0, 20))
        
        # Enhanced selection controls with auto-clear and complete reset functionality
        # Left pane selection controls
        ttk.Button(left_controls, text="Select All Differences - Left", 
                  command=self.select_all_differences_left).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_controls, text="Clear All - Left", 
                  command=self.clear_all_left).pack(side=tk.LEFT, padx=(0, 15))
        
        # Right pane selection controls  
        ttk.Button(left_controls, text="Select All Differences - Right", 
                  command=self.select_all_differences_right).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_controls, text="Clear All - Right", 
                  command=self.clear_all_right).pack(side=tk.LEFT)
        
        # Tree comparison frame (adjusted height to make room for status log)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Left tree with configurable column widths
        left_frame = ttk.LabelFrame(tree_frame, text="LEFT", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.left_tree = ttk.Treeview(left_frame, show='tree headings', selectmode='none')
        self.left_tree.heading('#0', text='Structure', anchor=tk.W)
        self.left_tree.column('#0', width=TREE_STRUCTURE_WIDTH, minwidth=TREE_STRUCTURE_MIN_WIDTH)
        
        # Configure columns for metadata display using configurable widths
        self.setup_tree_columns(self.left_tree)
        
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.left_tree.yview)
        self.left_tree.configure(yscrollcommand=left_scroll.set)
        self.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right tree with configurable column widths
        right_frame = ttk.LabelFrame(tree_frame, text="RIGHT", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self.right_tree = ttk.Treeview(right_frame, show='tree headings', selectmode='none')
        self.right_tree.heading('#0', text='Structure', anchor=tk.W)
        self.right_tree.column('#0', width=TREE_STRUCTURE_WIDTH, minwidth=TREE_STRUCTURE_MIN_WIDTH)
        
        self.setup_tree_columns(self.right_tree)
        
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_tree.yview)
        self.right_tree.configure(yscrollcommand=right_scroll.set)
        self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Synchronize scrolling between panes
        self.setup_synchronized_scrolling()
        
        # Copy buttons frame
        copy_frame = ttk.Frame(main_frame)
        copy_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(copy_frame, text="Copy LEFT to Right", command=self.copy_left_to_right).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Copy RIGHT to Left", command=self.copy_right_to_left).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Quit", command=self.root.quit).pack(side=tk.RIGHT)
        
        # Status log frame at bottom using configurable dimensions and styling
        status_log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding=5)
        status_log_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Create text widget with scrollbar for status log using configurable parameters
        status_log_container = ttk.Frame(status_log_frame)
        status_log_container.pack(fill=tk.X)
        
        self.status_log_text = tk.Text(
            status_log_container, 
            height=STATUS_LOG_VISIBLE_LINES,  # Use configurable visible lines
            wrap=tk.WORD,
            state=tk.DISABLED,  # Read-only
            font=STATUS_LOG_FONT,  # Use configurable font
            bg=STATUS_LOG_BG_COLOR,  # Use configurable background color
            fg=STATUS_LOG_FG_COLOR   # Use configurable text color
        )
        
        status_log_scroll = ttk.Scrollbar(status_log_container, orient=tk.VERTICAL, command=self.status_log_text.yview)
        self.status_log_text.configure(yscrollcommand=status_log_scroll.set)
        
        self.status_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status and summary frame (moved to bottom, below status log)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        
        ttk.Label(status_frame, textvariable=self.summary_var).pack(side=tk.LEFT)
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        ttk.Label(status_frame, text="Status:").pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.RIGHT)
        
        # Configure tree event bindings for enhanced interaction
        self.setup_tree_events()
        
        logger.debug("User interface setup complete with configurable constants")
        
    def setup_tree_columns(self, tree):
        """Setup columns for metadata display in tree using configurable widths"""
        tree['columns'] = ('size', 'date_modified', 'status')
        
        tree.heading('size', text='Size', anchor=tk.E)
        tree.heading('date_modified', text='Date Modified', anchor=tk.CENTER)
        tree.heading('status', text='Status', anchor=tk.W)
        
        # Use configurable column widths
        tree.column('size', width=TREE_SIZE_WIDTH, minwidth=TREE_SIZE_MIN_WIDTH, anchor=tk.E)
        tree.column('date_modified', width=TREE_DATE_WIDTH, minwidth=TREE_DATE_MIN_WIDTH, anchor=tk.CENTER)
        tree.column('status', width=TREE_STATUS_WIDTH, minwidth=TREE_STATUS_MIN_WIDTH, anchor=tk.W)
        
    def setup_synchronized_scrolling(self):
        """Setup synchronized scrolling between tree views"""
        def sync_yview(*args):
            self.left_tree.yview(*args)
            self.right_tree.yview(*args)
        
        # Create a shared scrollbar command for synchronized scrolling
        self.left_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.right_tree, *args))
        self.right_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.left_tree, *args))
        
    def sync_scrollbar(self, other_tree, *args):
        """Synchronize scrollbar between trees"""
        # Update both trees' scroll position for synchronized viewing
        self.left_tree.yview_moveto(args[0])
        self.right_tree.yview_moveto(args[0])
        
    def setup_tree_events(self):
        """
        Setup event bindings for tree interactions
        Enhanced: Improved event handling to prevent selection interference during expand/collapse
        """
        logger.debug("Setting up tree event bindings")
        
        # Enhanced: Bind tree expansion/collapse events with state preservation
        self.left_tree.bind('<<TreeviewOpen>>', lambda e: self.handle_tree_expand_collapse(self.left_tree, self.right_tree, e, True))
        self.left_tree.bind('<<TreeviewClose>>', lambda e: self.handle_tree_expand_collapse(self.left_tree, self.right_tree, e, False))
        self.right_tree.bind('<<TreeviewOpen>>', lambda e: self.handle_tree_expand_collapse(self.right_tree, self.left_tree, e, True))
        self.right_tree.bind('<<TreeviewClose>>', lambda e: self.handle_tree_expand_collapse(self.right_tree, self.left_tree, e, False))
        
        # Bind checkbox-like behavior for item selection (with missing item exclusion)
        self.left_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.left_tree, 'left', e))
        self.right_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.right_tree, 'right', e))
        
    def handle_tree_expand_collapse(self, source_tree, target_tree, event, is_expand):
        """
        Enhanced: Handle tree expansion/collapse with proper state preservation
        Ensures selection state is maintained during expand/collapse operations
        """
        if self._updating_display:
            return  # Prevent recursive updates
            
        item = source_tree.selection()[0] if source_tree.selection() else source_tree.focus()
        if item:
            try:
                # Synchronize expand/collapse state with other tree
                target_tree.item(item, open=is_expand)
                
                if __debug__:
                    action = "expand" if is_expand else "collapse"
                    logger.debug(f"Synchronized tree {action} for item {item}")
                    
            except tk.TclError:
                pass  # Item doesn't exist in target tree
                
            # CRITICAL: Do NOT call update_tree_display() here as it interferes with selection state
            # Selection state should remain completely independent of expand/collapse operations
                
    def is_missing_item(self, tree, item_id):
        """
        Check if an item is a missing item (has [MISSING] in text or 'missing' tag)
        Helper function to identify non-clickable missing items
        """
        if not item_id:
            return False
            
        item_text = tree.item(item_id, 'text')
        item_tags = tree.item(item_id, 'tags')
        
        # Check if item is marked as missing
        is_missing = '[MISSING]' in item_text or 'missing' in item_tags
        
        if __debug__ and is_missing:
            logger.debug(f"Identified missing item: {item_id} with text: {item_text}")
            
        return is_missing
        
    def is_different_item(self, item_id, side):
        """
        Enhanced: Check if an item represents a different file/folder that needs syncing
        Used for smart folder selection logic
        """
        if not item_id:
            return False
            
        # Get the relative path for this item
        rel_path = self.get_item_relative_path(item_id, side)
        if not rel_path:
            return False
            
        # Check if this item has differences
        result = self.comparison_results.get(rel_path)
        if result and result.is_different:
            # Also ensure the item exists on this side
            item_exists = False
            if side == 'left' and result.left_item and result.left_item.exists:
                item_exists = True
            elif side == 'right' and result.right_item and result.right_item.exists:
                item_exists = True
                
            if __debug__ and item_exists:
                logger.debug(f"Item {item_id} ({rel_path}) is different and exists on {side} side")
                
            return item_exists
            
        return False
        
    def get_item_relative_path(self, item_id, side):
        """
        Get the relative path for a tree item by looking it up in path mappings
        More efficient than reconstructing from tree hierarchy
        """
        path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
        
        # Find the relative path by searching the mapping
        for rel_path, mapped_item_id in path_map.items():
            if mapped_item_id == item_id:
                return rel_path
                
        return None
                
    def handle_tree_click(self, tree, side, event):
        """
        Handle clicks on tree items (for checkbox behavior)
        Enhanced: Now ignores clicks on missing items for logical consistency
        """
        item = tree.identify('item', event.x, event.y)
        if item:
            # Check if item is missing and ignore clicks on missing items
            if self.is_missing_item(tree, item):
                if __debug__:
                    logger.debug(f"Ignoring click on missing item: {item}")
                return  # Don't process clicks on missing items
                
            # Toggle selection for this item if it's not missing
            self.toggle_item_selection(item, side)
            
    def toggle_item_selection(self, item_id, side):
        """Toggle selection state of an item and handle parent/child logic with root safety"""
        if __debug__:
            logger.debug(f"Toggling selection for item {item_id} on {side} side")
            
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        was_selected = item_id in selected_set
        
        if item_id in selected_set:
            # Unticking - remove from selection and untick all parents and children
            selected_set.discard(item_id)
            # Enhanced unticking with root safety check
            self.untick_parents_with_root_safety(item_id, side)
            self.untick_children(item_id, side)
        else:
            # Ticking - add to selection and tick all children (Enhanced: only different ones)
            selected_set.add(item_id)
            self.tick_children_smart(item_id, side)
            
        if __debug__:
            action = "unticked" if was_selected else "ticked"
            logger.debug(f"Item {action}, {side} selection count: {len(selected_set)}")
            
        # Log selection changes to status window
        total_selected = len(self.selected_left) + len(self.selected_right)
        action_word = "Deselected" if was_selected else "Selected"
        rel_path = self.get_item_relative_path(item_id, side) or "item"
        self.add_status_message(f"{action_word} {rel_path} ({side}) - Total selected: {total_selected}")
            
        self.update_tree_display_safe()
        self.update_summary()
        
    def tick_children_smart(self, item_id, side):
        """
        Enhanced: Smart tick children - only select different items underneath
        This implements the corrected folder selection logic
        """
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        if __debug__:
            logger.debug(f"Smart ticking children for {item_id} - only selecting different items")
        
        different_count = 0
        total_count = 0
        
        def tick_recursive(item):
            nonlocal different_count, total_count
            total_count += 1
            
            # Only tick if item is not missing AND is different
            if not self.is_missing_item(tree, item) and self.is_different_item(item, side):
                selected_set.add(item)
                different_count += 1
                if __debug__:
                    rel_path = self.get_item_relative_path(item, side)
                    logger.debug(f"Smart-selected different item: {item} ({rel_path})")
                    
            # Recursively process children
            for child in tree.get_children(item):
                tick_recursive(child)
                
        # Process all children of the ticked item
        for child in tree.get_children(item_id):
            tick_recursive(child)
            
        if __debug__:
            logger.debug(f"Smart selection complete: {different_count}/{total_count} children selected (only different items)")
            
        # Log smart selection results
        if different_count > 0:
            folder_path = self.get_item_relative_path(item_id, side) or "folder"
            self.add_status_message(f"Smart-selected {different_count} different items in {folder_path} ({side})")
            
    def untick_children(self, item_id, side):
        """Untick all children of an item recursively"""
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        def untick_recursive(item):
            selected_set.discard(item)
            for child in tree.get_children(item):
                untick_recursive(child)
                
        for child in tree.get_children(item_id):
            untick_recursive(child)
            
    def untick_parents_with_root_safety(self, item_id, side):
        """
        Untick all parents of an item with safety check for root level
        Enhanced to prevent attempting to untick parents of root items
        """
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        root_item = self.root_item_left if side == 'left' else self.root_item_right
        
        if __debug__:
            logger.debug(f"Unticking parents for item {item_id}, root_item: {root_item}")
        
        parent = tree.parent(item_id)
        while parent:
            selected_set.discard(parent)
            if __debug__:
                logger.debug(f"Unticked parent: {parent}")
            
            # Safety check - if we've reached the root item, stop here
            # Don't try to untick the parent of the root item as it doesn't exist
            if parent == root_item:
                if __debug__:
                    logger.debug(f"Reached root item {root_item}, stopping parent unticking")
                break
                
            next_parent = tree.parent(parent)
            if not next_parent:  # Additional safety check for empty parent
                if __debug__:
                    logger.debug(f"No parent found for {parent}, stopping parent unticking")
                break
            parent = next_parent
            
    def update_tree_display_safe(self):
        """
        Enhanced: Safe tree display update that preserves selection state
        Prevents recursive updates during expand/collapse operations
        """
        if self._updating_display:
            if __debug__:
                logger.debug("Skipping tree display update - already updating")
            return
            
        self._updating_display = True
        try:
            self.update_tree_display()
        finally:
            self._updating_display = False
            
    def update_tree_display(self):
        """Update tree display to show selection state (only for non-missing items)"""
        # Update left tree
        for item in self.left_tree.get_children():
            self.update_item_display(self.left_tree, item, 'left')
            
        # Update right tree  
        for item in self.right_tree.get_children():
            self.update_item_display(self.right_tree, item, 'right')
            
    def update_item_display(self, tree, item, side, recursive=True):
        """
        Update display of a single item and optionally its children
        Enhanced: Only updates checkbox display for non-missing items
        """
        selected_set = self.selected_left if side == 'left' else self.selected_right
        
        # Get current text 
        current_text = tree.item(item, 'text')
        
        # Skip updating missing items (they shouldn't have checkboxes)
        if self.is_missing_item(tree, item):
            if recursive:
                for child in tree.get_children(item):
                    self.update_item_display(tree, child, side, True)
            return
        
        # Remove existing checkbox indicators for non-missing items
        if current_text.startswith('☑ ') or current_text.startswith('☐ '):
            current_text = current_text[2:]
            
        # Add checkbox indicator based on selection state
        if item in selected_set:
            new_text = '☑ ' + current_text
        else:
            new_text = '☐ ' + current_text
            
        tree.item(item, text=new_text)
        
        if recursive:
            for child in tree.get_children(item):
                self.update_item_display(tree, child, side, True)
                
    def browse_left_folder(self):
        """Browse for left folder"""
        logger.debug("Opening left folder browser")
        folder = filedialog.askdirectory(title="Select Left Folder")
        if folder:
            self.left_folder.set(folder)
            self.add_status_message(f"Selected left folder: {folder}")
            logger.info(f"Selected left folder: {folder}")
            
    def browse_right_folder(self):
        """Browse for right folder"""
        logger.debug("Opening right folder browser")
        folder = filedialog.askdirectory(title="Select Right Folder")
        if folder:
            self.right_folder.set(folder)
            self.add_status_message(f"Selected right folder: {folder}")
            logger.info(f"Selected right folder: {folder}")
            
    def start_comparison(self):
        """Start folder comparison in background thread"""
        logger.info("Starting folder comparison")
        
        if not self.left_folder.get() or not self.right_folder.get():
            error_msg = "Both folders must be selected before comparison"
            logger.error(f"Comparison failed: {error_msg}")
            self.add_status_message(f"Error: {error_msg}")
            messagebox.showerror("Error", "Please select both folders to compare")
            return
            
        if not os.path.exists(self.left_folder.get()):
            error_msg = f"Left folder does not exist: {self.left_folder.get()}"
            logger.error(error_msg)
            self.add_status_message(f"Error: {error_msg}")
            messagebox.showerror("Error", "Left folder does not exist")
            return
            
        if not os.path.exists(self.right_folder.get()):
            error_msg = f"Right folder does not exist: {self.right_folder.get()}"
            logger.error(error_msg)
            self.add_status_message(f"Error: {error_msg}")
            messagebox.showerror("Error", "Right folder does not exist")
            return
        
        if __debug__:
            logger.debug(f"Left folder: {self.left_folder.get()}")
            logger.debug(f"Right folder: {self.right_folder.get()}")
            logger.debug(f"Compare criteria: existence={self.compare_existence.get()}, "
                        f"size={self.compare_size.get()}, "
                        f"date_created={self.compare_date_created.get()}, "
                        f"date_modified={self.compare_date_modified.get()}, "
                        f"sha512={self.compare_sha512.get()}")
            
        # Start comparison in background thread
        self.status_var.set("Comparing folders...")
        self.add_status_message("Starting folder comparison...")
        logger.info("Starting background comparison thread")
        threading.Thread(target=self.perform_comparison, daemon=True).start()
        
    def perform_comparison(self):
        """Perform the actual folder comparison with progress tracking"""
        start_time = time.time()
        logger.info("Beginning folder comparison operation")
        
        # Create progress dialog for the overall comparison process
        progress = ProgressDialog(
            self.root, 
            "Comparing Folders", 
            "Preparing comparison...",
            max_value=100  # We'll estimate progress as percentage
        )
        
        try:
            # Clear previous results and reset state
            self.comparison_results.clear()
            self.selected_left.clear()
            self.selected_right.clear()
            self.path_to_item_left.clear()
            self.path_to_item_right.clear()
            self.root_item_left = None
            self.root_item_right = None
            
            if __debug__:
                logger.debug("Cleared previous comparison results and reset root items")
            
            # Step 1: Build file lists for both folders (40% of total work)
            progress.update_progress(5, "Scanning left folder...")
            self.root.after(0, lambda: self.add_status_message("Scanning left folder for files and folders..."))
            
            left_files = self.build_file_list_with_progress(self.left_folder.get(), progress, 5, 25)
            file_count_left = len(left_files)
            
            self.root.after(0, lambda: self.add_status_message(f"Left folder scan complete: {file_count_left:,} items found"))
            logger.info(f"Found {file_count_left} items in left folder")
            
            progress.update_progress(30, "Scanning right folder...")
            self.root.after(0, lambda: self.add_status_message("Scanning right folder for files and folders..."))
            
            right_files = self.build_file_list_with_progress(self.right_folder.get(), progress, 30, 50)
            file_count_right = len(right_files)
            
            self.root.after(0, lambda: self.add_status_message(f"Right folder scan complete: {file_count_right:,} items found"))
            logger.info(f"Found {file_count_right} items in right folder")
            
            # Step 2: Compare files (50% of total work)
            progress.update_progress(50, "Comparing files and folders...")
            self.root.after(0, lambda: self.add_status_message("Comparing files and folders for differences..."))
            
            # Get all unique relative paths
            all_paths = set(left_files.keys()) | set(right_files.keys())
            total_paths = len(all_paths)
            logger.info(f"Comparing {total_paths} unique paths")
            
            if __debug__:
                logger.debug(f"Left-only paths: {len(left_files.keys() - right_files.keys())}")
                logger.debug(f"Right-only paths: {len(right_files.keys() - left_files.keys())}")
                logger.debug(f"Common paths: {len(left_files.keys() & right_files.keys())}")
            
            # Compare each path with progress updates using configurable frequency
            differences_found = 0
            for i, rel_path in enumerate(all_paths):
                # Update progress using configurable frequency settings
                if i % max(1, total_paths // PROGRESS_PERCENTAGE_FREQUENCY) == 0 or i % COMPARISON_PROGRESS_BATCH == 0:
                    comparison_progress = 50 + int((i / total_paths) * 40)  # 40% of work for comparison
                    progress.update_progress(comparison_progress, f"Comparing... {i+1:,} of {total_paths:,}")
                
                left_item = left_files.get(rel_path)
                right_item = right_files.get(rel_path)
                
                differences = self.compare_items(left_item, right_item)
                
                self.comparison_results[rel_path] = ComparisonResult_class(
                    left_item=left_item,
                    right_item=right_item,
                    differences=differences
                )
                
                if differences:
                    differences_found += 1
                    if __debug__:
                        logger.debug(f"Difference found in '{rel_path}': {differences}")
            
            # Step 3: Update UI (10% of total work)
            progress.update_progress(90, "Building comparison trees...")
            self.root.after(0, lambda: self.add_status_message("Building comparison tree views..."))
            
            elapsed_time = time.time() - start_time
            logger.info(f"Comparison completed in {elapsed_time:.2f} seconds")
            logger.info(f"Found {differences_found} items with differences")
            
            # Update UI in main thread
            progress.update_progress(100, "Finalizing...")
            self.root.after(0, self.update_comparison_ui)
            
            # Add completion status message
            self.root.after(0, lambda: self.add_status_message(
                f"Comparison complete: {differences_found:,} differences found in {elapsed_time:.1f} seconds"
            ))
            
        except Exception as e:
            logger.error(f"Comparison failed with exception: {type(e).__name__}: {str(e)}")
            if __debug__:
                import traceback
                logger.debug("Full exception traceback:")
                logger.debug(traceback.format_exc())
            
            error_msg = f"Comparison failed: {str(e)}"
            self.root.after(0, lambda: self.add_status_message(f"Error: {error_msg}"))
            self.root.after(0, lambda: self.show_error(error_msg))
        finally:
            # Always close the progress dialog
            progress.close()
            
    def build_file_list_with_progress(self, root_path: str, progress: ProgressDialog, 
                                    start_percent: int, end_percent: int) -> Dict[str, FileMetadata_class]:
        """
        Build a dictionary of relative_path -> FileMetadata with progress tracking
        Uses configurable update intervals for optimal performance
        Args:
            root_path: Root directory to scan
            progress: Progress dialog to update
            start_percent: Starting percentage for this operation
            end_percent: Ending percentage for this operation
        """
        if __debug__:
            logger.debug(f"Building file list with progress for: {root_path}")
        
        assert os.path.exists(root_path), f"Root path must exist: {root_path}"
        
        files = {}
        root = Path(root_path)
        file_count = 0
        dir_count = 0
        error_count = 0
        items_processed = 0
        
        try:
            # First pass: count total items for better progress tracking
            total_items = sum(1 for _ in root.rglob('*'))
            
            # Include the root directory itself if it's empty
            if not any(root.iterdir()):
                if __debug__:
                    logger.debug(f"Root directory is empty: {root_path}")
                
            for path in root.rglob('*'):
                try:
                    items_processed += 1
                    
                    # Update progress using configurable intervals for optimal performance
                    if items_processed % max(1, min(SCAN_PROGRESS_UPDATE_INTERVAL, total_items // 20)) == 0:
                        current_percent = start_percent + int(((items_processed / total_items) * (end_percent - start_percent)))
                        progress.update_progress(current_percent, f"Scanning... {items_processed:,} items found")
                    
                    rel_path = path.relative_to(root).as_posix()
                    metadata = FileMetadata_class.from_path(str(path), self.compare_sha512.get())
                    files[rel_path] = metadata
                    
                    if path.is_file():
                        file_count += 1
                    else:
                        dir_count += 1
                        
                except Exception as e:
                    error_count += 1
                    if __debug__:
                        logger.debug(f"Skipping file due to error: {path} - {e}")
                    continue  # Skip files we can't process
                    
            # Also scan for empty directories that might not be caught by rglob('*')
            for path in root.rglob(''):  # This gets all directories
                try:
                    if path.is_dir() and path != root:
                        rel_path = path.relative_to(root).as_posix()
                        if rel_path not in files:  # Only add if not already added
                            metadata = FileMetadata_class.from_path(str(path), False)
                            files[rel_path] = metadata
                            dir_count += 1
                except Exception as e:
                    error_count += 1
                    if __debug__:
                        logger.debug(f"Skipping directory due to error: {path} - {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scanning directory {root_path}: {e}")
            if __debug__:
                import traceback
                logger.debug(traceback.format_exc())
            
        logger.info(f"Scanned {root_path}: {file_count} files, {dir_count} directories, {error_count} errors")
        if __debug__:
            logger.debug(f"Total items found: {len(files)}")
            
        return files
        
    def compare_items(self, left_item: Optional[FileMetadata_class], 
                     right_item: Optional[FileMetadata_class]) -> Set[str]:
        """Compare two items and return set of differences"""
        differences = set()
        
        # Check existence
        if self.compare_existence.get():
            if (left_item is None) != (right_item is None):
                differences.add('existence')
            elif left_item and right_item and (not left_item.exists or not right_item.exists):
                differences.add('existence')
                
        # If both items exist, compare other attributes
        if left_item and right_item and left_item.exists and right_item.exists:
            if self.compare_size.get() and left_item.size != right_item.size:
                differences.add('size')
                
            if self.compare_date_created.get() and left_item.date_created != right_item.date_created:
                differences.add('date_created')
                
            if self.compare_date_modified.get() and left_item.date_modified != right_item.date_modified:
                differences.add('date_modified')
                
            if (self.compare_sha512.get() and left_item.sha512 and right_item.sha512 
                and left_item.sha512 != right_item.sha512):
                differences.add('sha512')
                
        return differences
        
    def update_comparison_ui(self):
        """Update UI with comparison results"""
        logger.info("Updating UI with comparison results")
        
        # Clear existing tree content
        left_items = len(self.left_tree.get_children())
        right_items = len(self.right_tree.get_children())
        
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)
            
        if __debug__:
            logger.debug(f"Cleared {left_items} left tree items and {right_items} right tree items")
            
        # Build tree structure with enhanced root handling
        self.build_trees_with_root_paths()
        
        # Update status
        self.status_var.set("Ready")
        self.update_summary()
        logger.info("UI update completed")
        
    def build_trees_with_root_paths(self):
        """
        Build tree structures from comparison results with fully qualified root paths
        Enhanced to include root paths as selectable tree items and properly handle missing folders
        """
        if __debug__:
            logger.debug(f"Building trees with root paths from {len(self.comparison_results)} comparison results")
        
        start_time = time.time()
        
        # Create root items with fully qualified paths and functional checkboxes
        left_root_path = self.left_folder.get()
        right_root_path = self.right_folder.get()
        
        # Insert root items as top-level entries with checkboxes
        left_root_text = f"☐ {left_root_path}"
        right_root_text = f"☐ {right_root_path}"
        
        self.root_item_left = self.left_tree.insert('', tk.END, text=left_root_text, open=True,
                                                   values=("", "", "Root"))
        self.root_item_right = self.right_tree.insert('', tk.END, text=right_root_text, open=True,
                                                     values=("", "", "Root"))
        
        # Store root path mappings for selection system
        self.path_to_item_left[''] = self.root_item_left  # Empty path represents root
        self.path_to_item_right[''] = self.root_item_right
        
        if __debug__:
            logger.debug(f"Created root items: left={self.root_item_left}, right={self.root_item_right}")
        
        # Create sentinel class for missing folders to distinguish from real empty folders
        class MissingFolder:
            def __init__(self):
                self.contents = {}
        
        # Organize paths into tree structure
        left_structure = {}
        right_structure = {}
        
        # First pass: Build structure for existing items
        for rel_path, result in self.comparison_results.items():
            if not rel_path:  # Skip empty paths (but this shouldn't happen now)
                if __debug__:
                    logger.debug("Skipping empty relative path")
                continue
                
            path_parts = rel_path.split('/')
            assert len(path_parts) > 0, f"Path parts should not be empty for: {rel_path}"
            
            # Build left structure
            if result.left_item is not None:
                current = left_structure
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = {}
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            # Handle conflict: file exists where we need a folder
                            if __debug__:
                                logger.debug(f"Path conflict in left structure: '{part}' exists as file, need as folder")
                            current[part] = {}
                        elif isinstance(current[part], MissingFolder):
                            # Convert missing folder to real folder since we have content
                            current[part] = current[part].contents
                        current = current[part] if isinstance(current[part], dict) else current[part].contents
                if path_parts[-1]:
                    # Only add if it doesn't conflict with existing folder
                    final_name = path_parts[-1]
                    if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                        if __debug__:
                            logger.debug(f"Cannot add file '{final_name}' - folder exists with same name")
                    else:
                        current[final_name] = result.left_item
            
            # Build right structure  
            if result.right_item is not None:
                current = right_structure
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = {}
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            # Handle conflict: file exists where we need a folder
                            if __debug__:
                                logger.debug(f"Path conflict in right structure: '{part}' exists as file, need as folder")
                            current[part] = {}
                        elif isinstance(current[part], MissingFolder):
                            # Convert missing folder to real folder since we have content
                            current[part] = current[part].contents
                        current = current[part] if isinstance(current[part], dict) else current[part].contents
                if path_parts[-1]:
                    # Only add if it doesn't conflict with existing folder
                    final_name = path_parts[-1]
                    if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                        if __debug__:
                            logger.debug(f"Cannot add file '{final_name}' - folder exists with same name")
                    else:
                        current[final_name] = result.right_item
                    
        # Second pass: Add missing items as placeholders
        missing_left = 0
        missing_right = 0
        for rel_path, result in self.comparison_results.items():
            if not rel_path:
                continue
                
            path_parts = rel_path.split('/')
            
            # Add missing left items
            if result.left_item is None and result.right_item is not None:
                missing_left += 1
                current = left_structure
                
                # Build missing folder structure
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = MissingFolder()  # Mark as missing folder
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = MissingFolder()
                        current = current[part].contents if isinstance(current[part], MissingFolder) else current[part]
                        
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    # For missing files/folders, use None for files and MissingFolder for folders
                    if result.right_item and result.right_item.is_folder:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = MissingFolder()  # Missing folder
                    else:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = None  # Missing file
                    
            # Add missing right items
            if result.right_item is None and result.left_item is not None:
                missing_right += 1
                current = right_structure
                
                # Build missing folder structure
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = MissingFolder()  # Mark as missing folder
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = MissingFolder()
                        current = current[part].contents if isinstance(current[part], MissingFolder) else current[part]
                        
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    # For missing files/folders, use None for files and MissingFolder for folders
                    if result.left_item and result.left_item.is_folder:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = MissingFolder()  # Missing folder
                    else:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = None  # Missing file
        
        if __debug__:
            logger.debug(f"Added {missing_left} missing left placeholders, {missing_right} missing right placeholders")
            
        # Populate trees under root items
        logger.info("Populating tree views under root paths...")
        self.populate_tree(self.left_tree, left_structure, self.root_item_left, 'left', '')
        self.populate_tree(self.right_tree, right_structure, self.root_item_right, 'right', '')
        
        elapsed_time = time.time() - start_time
        if __debug__:
            logger.debug(f"Tree building with root paths completed in {elapsed_time:.3f} seconds")
        
    def populate_tree(self, tree, structure, parent_id, side, current_path):
        """
        Recursively populate tree with structure
        Enhanced: Missing items (both files and folders) no longer have checkboxes for logical consistency
        """
        # Import the MissingFolder class (defined in build_trees_with_root_paths)
        # We need to check for this class type
        for name, content in sorted(structure.items()):
            # Build the full relative path for this item
            item_rel_path = current_path + ('/' if current_path else '') + name
            
            # Check if content is a MissingFolder (defined in the calling method)
            is_missing_folder = hasattr(content, 'contents')
            
            if isinstance(content, dict) or is_missing_folder:
                # This is a folder (either real or missing)
                if is_missing_folder:
                    # Enhanced: Missing folder - NO checkbox, just plain text with [MISSING]
                    item_text = f"{name}/ [MISSING]"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, open=False,
                                        values=("", "", "Missing"), tags=('missing',))
                    # Recursively populate children from the missing folder's contents
                    self.populate_tree(tree, content.contents, item_id, side, item_rel_path)
                else:
                    # Real folder - has checkbox
                    item_text = f"☐ {name}/"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, open=False)
                    # Recursively populate children
                    self.populate_tree(tree, content, item_id, side, item_rel_path)
                
                # Store path mapping for both real and missing folders
                path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
                path_map[item_rel_path] = item_id
                
            else:
                # This is a file
                if content is None:
                    # Enhanced: Missing file - NO checkbox, just plain text with [MISSING]
                    item_text = f"{name} [MISSING]"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, 
                                        values=("", "", "Missing"), tags=('missing',))
                else:
                    # Existing file - has checkbox
                    size_str = self.format_size(content.size) if content.size else ""
                    date_str = content.date_modified.strftime("%Y-%m-%d %H:%M") if content.date_modified else ""
                    
                    # Determine status using proper path lookup
                    result = self.comparison_results.get(item_rel_path)
                    status = "Different" if result and result.is_different else "Same"
                    
                    item_text = f"☐ {name}"
                    item_id = tree.insert(parent_id, tk.END, text=item_text,
                                        values=(size_str, date_str, status))
                
                # Store path mapping for both missing and existing files
                path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
                path_map[item_rel_path] = item_id
                                        
        # Configure missing item styling using configurable color
        tree.tag_configure('missing', foreground=MISSING_ITEM_COLOR)
        
    def get_item_path(self, tree, item_id):
        """Get the full relative path for a tree item"""
        if not item_id:
            return ""
        path_parts = []
        current = item_id
        while current:
            text = tree.item(current, 'text')
            # Remove checkbox and extract name
            if text.startswith('☑ ') or text.startswith('☐ '):
                text = text[2:]
            # Remove folder indicator
            if text.endswith('/'):
                text = text[:-1]
            # Remove [MISSING] indicator
            if text.endswith(' [MISSING]'):
                text = text[:-10]
            
            # Stop at root item (don't include the full path in relative path calculation)
            root_item = self.root_item_left if tree == self.left_tree else self.root_item_right
            if current == root_item:
                break
                
            path_parts.append(text)
            current = tree.parent(current)
        return '/'.join(reversed(path_parts))
        
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes is None:
            return ""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
        
    def find_tree_item_by_path(self, rel_path, side):
        """Find tree item ID by relative path"""
        path_map = self.path_to_item_left if side == 'left' else self.path_to_item_right
        return path_map.get(rel_path)
        
    def select_all_differences_left(self):
        """
        Enhanced: Select all different items in left pane with auto-clear first
        Automatically clears all selections before selecting for clean workflow
        """
        if __debug__:
            logger.debug("Auto-clearing all selections before selecting differences in left pane")
            
        # First clear all selections for clean state
        self.clear_all_left()
        
        count = 0
        for rel_path, result in self.comparison_results.items():
            if result.is_different and result.left_item and result.left_item.exists:
                item_id = self.find_tree_item_by_path(rel_path, 'left')
                if item_id:
                    self.selected_left.add(item_id)
                    count += 1
                    
        if __debug__:
            logger.debug(f"Selected {count} different items in left pane (after auto-clear)")
            
        self.add_status_message(f"Selected all differences in left pane: {count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def select_all_differences_right(self):
        """
        Enhanced: Select all different items in right pane with auto-clear first
        Automatically clears all selections before selecting for clean workflow
        """
        if __debug__:
            logger.debug("Auto-clearing all selections before selecting differences in right pane")
            
        # First clear all selections for clean state
        self.clear_all_right()
        
        count = 0
        for rel_path, result in self.comparison_results.items():
            if result.is_different and result.right_item and result.right_item.exists:
                item_id = self.find_tree_item_by_path(rel_path, 'right')
                if item_id:
                    self.selected_right.add(item_id)
                    count += 1
                    
        if __debug__:
            logger.debug(f"Selected {count} different items in right pane (after auto-clear)")
            
        self.add_status_message(f"Selected all differences in right pane: {count:,} items")
        self.update_tree_display_safe() 
        self.update_summary()
        
    def clear_all_left(self):
        """
        Enhanced: Clear ALL selections in left pane (not just differences)
        Provides complete reset functionality for workflow flexibility
        """
        cleared_count = len(self.selected_left)
        if __debug__:
            logger.debug(f"Clearing ALL {cleared_count} selections in left pane")
            
        self.selected_left.clear()
        if cleared_count > 0:
            self.add_status_message(f"Cleared all selections in left pane: {cleared_count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def clear_all_right(self):
        """
        Enhanced: Clear ALL selections in right pane (not just differences)  
        Provides complete reset functionality for workflow flexibility
        """
        cleared_count = len(self.selected_right)
        if __debug__:
            logger.debug(f"Clearing ALL {cleared_count} selections in right pane")
            
        self.selected_right.clear()
        if cleared_count > 0:
            self.add_status_message(f"Cleared all selections in right pane: {cleared_count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def copy_left_to_right(self):
        """Copy selected items from left to right with progress tracking"""
        if not self.selected_left:
            self.add_status_message("No items selected for copying from left to right")
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # For safety during development, just show what would be copied using configurable preview limit
        selected_paths = []
        for item_id in self.selected_left:
            path = self.get_item_path(self.left_tree, item_id)
            selected_paths.append(path)
            
        self.add_status_message(f"Copy preview: {len(self.selected_left):,} items from LEFT to RIGHT")
        
        message = f"Would copy {len(self.selected_left)} items from LEFT to RIGHT:\n\n"
        message += "\n".join(selected_paths[:COPY_PREVIEW_MAX_ITEMS])  # Use configurable preview limit
        if len(selected_paths) > COPY_PREVIEW_MAX_ITEMS:
            message += f"\n... and {len(selected_paths) - COPY_PREVIEW_MAX_ITEMS} more items"
        message += "\n\nActual copying is disabled for safety during development."
        messagebox.showinfo("Copy Preview", message)
        
    def copy_right_to_left(self):
        """Copy selected items from right to left with progress tracking"""
        if not self.selected_right:
            self.add_status_message("No items selected for copying from right to left")
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # For safety during development, just show what would be copied using configurable preview limit
        selected_paths = []
        for item_id in self.selected_right:
            path = self.get_item_path(self.right_tree, item_id)
            selected_paths.append(path)
            
        self.add_status_message(f"Copy preview: {len(self.selected_right):,} items from RIGHT to LEFT")
        
        message = f"Would copy {len(self.selected_right)} items from RIGHT to LEFT:\n\n"
        message += "\n".join(selected_paths[:COPY_PREVIEW_MAX_ITEMS])  # Use configurable preview limit
        if len(selected_paths) > COPY_PREVIEW_MAX_ITEMS:
            message += f"\n... and {len(selected_paths) - COPY_PREVIEW_MAX_ITEMS} more items"
        message += "\n\nActual copying is disabled for safety during development."
        messagebox.showinfo("Copy Preview", message)
        
    def update_summary(self):
        """Update summary information"""
        if not self.comparison_results:
            self.summary_var.set("Summary: No comparison performed")
            return
            
        total_differences = sum(1 for r in self.comparison_results.values() if r.is_different)
        missing_left = sum(1 for r in self.comparison_results.values() 
                          if r.left_item is None or not r.left_item.exists)
        missing_right = sum(1 for r in self.comparison_results.values()
                           if r.right_item is None or not r.right_item.exists)
        selected_total = len(self.selected_left) + len(self.selected_right)
        
        summary = f"Summary: {total_differences} differences | {missing_left} missing left | {missing_right} missing right | {selected_total} marked"
        self.summary_var.set(summary)
        
    def show_error(self, message):
        """Show error message to user"""
        logger.error(f"Displaying error to user: {message}")
        messagebox.showerror("Error", message)
        self.status_var.set("Ready")
        
    def run(self):
        """Start the application"""
        logger.info("Starting FolderCompareSync GUI application")
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Application crashed: {type(e).__name__}: {str(e)}")
            if __debug__:
                import traceback
                logger.debug("Crash traceback:")
                logger.debug(traceback.format_exc())
            raise
        finally:
            logger.info("Application shutdown")


def main():
    """Main entry point"""
    logger.info("=== FolderCompareSync Starting ===")
    if __debug__:
        logger.debug("Working directory : " + os.getcwd())
        logger.debug("Python version    : " + sys.version)
        logger.debug("Computer name     : " + platform.node())
        logger.debug("Platform          : " + sys.platform)
        logger.debug("Architecture      : " + platform.architecture()[0])
        logger.debug("Machine           : " + platform.machine())
        logger.debug("Processor         : " + platform.processor())

    # Detailed Windows information
    if sys.platform == "win32":
        try:
            win_ver = platform.win32_ver()
            logger.debug(f"Windows version   : {win_ver[0]}")
            logger.debug(f"Windows build     : {win_ver[1]}")
            if win_ver[2]:  # Service pack
                logger.debug(f"Service pack      : {win_ver[2]}")
            logger.debug(f"Windows type      : {win_ver[3]}")
            # Try to get Windows edition
            try:
                edition = platform.win32_edition()
                if edition:
                    logger.debug(f"Windows edition   : {edition}")
            except:
                pass
            # Extract build number from version string like "10.0.26100"
            version_parts = win_ver[1].split('.')
            if len(version_parts) >= 3:
                build_num = version_parts[2]  # Get "26100" from "10.0.26100"
            else:
                build_num = win_ver[1]  # Fallback to full string
                
            win_versions = {
                # Windows 11 versions
                "22000": "21H2 (Original release)",
                "22621": "22H2", 
                "22631": "23H2",
                "26100": "24H2",
                # Future Windows versions (anticipated)
                "27000": "25H1 (anticipated)",
                "27100": "25H2 (anticipated)"
            }
            if build_num in win_versions:
                logger.debug(f"Windows 11 version: {win_versions[build_num]} (build {build_num})")
            elif build_num.startswith("27") or build_num.startswith("28"):
                logger.debug(f"Windows version   : Future windows build {build_num}")
            elif build_num.startswith("26") or build_num.startswith("22"):
                logger.debug(f"Windows 11 version: Unknown windows build {build_num}")
            elif build_num.startswith("19"):
                logger.debug(f"Windows 10 build  : {build_num}")
            else:
                logger.debug(f"Windows version   : Unknown windows build {build_num}")
        except Exception as e:
            logger.debug(f"Error getting Windows details: {e}")
    
    try:
        app = FolderCompareSync_class()
        # uncomment to MANUALLY Enable debug mode logging for testing
        #app.set_debug_loglevel(True)
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {type(e).__name__}: {str(e)}")
        if __debug__:
            import traceback
            logger.debug("Fatal error traceback:")
            logger.debug(traceback.format_exc())
        raise
    finally:
        logger.info("=== FolderCompareSync Shutdown ===")


if __name__ == "__main__":
    main()