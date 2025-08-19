# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
from FolderCompareSync_Global_Imports import *

# import out global constants first
import FolderCompareSync_Global_Constants as C

# import our flushed_logging before other modules
#from flushed_logging import *   # includes LoggerManager
from flushed_logging import log_and_flush, get_log_level, LoggerManager

#--- For DEBUGGING issues with importing FolderCompareSync_Global_Imports
import FolderCompareSync_Global_Imports as GI   
import logging
#--- For DEBUGGING issues with importing FolderCompareSync_Global_Imports

# Import the things this class references
from ProgressDialog_class import ProgressDialog_class
from FileCopyManager_class import FileCopyManager_class
from DeleteOrphansManager_class import DeleteOrphansManager_class
from DebugGlobalEditor_class import DebugGlobalEditor_class
from FileTimestampManager_class import FileTimestampManager_class

class FolderCompareSync_class:
    """
    Main application class for folder comparison and synchronization with limits and dry run capability.
    
    Purpose:
    --------
    Provides the primary GUI interface for comparing two folder structures, identifying differences,
    and synchronizing files between them using a copy system with comprehensive safety features.
    
    Key Features:
    -------------
    - Dual-pane folder comparison with detailed metadata analysis
    - Configurable file/folder limits (100,000 max) with early abort protection
    - Dry run mode for safe operation testing without file modifications
    - Advanced filtering and selection capabilities
    - Status log export functionality for record keeping
    - Comprehensive error handling and user guidance
    
    Usage:
    ------
    app = FolderCompareSync_class()
    app.run()
    """

    @dataclass
    class FileMetadata_class:
        """
        Container for file and folder metadata used in comparison operations.
        
        Purpose:
        --------
        Stores comprehensive metadata about files and folders including timestamps,
        size, hash values, and existence status for comparison and synchronization.
        
        Usage:
        ------
        metadata = FolderCompareSync_class.FileMetadata_class.from_path("/path/to/file.txt", compute_hash=True)
        if metadata.exists and not metadata.is_folder:
            print(f"File size: {metadata.size} bytes")
        """
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
            """Create FileMetadata from a file system path with optional hash computation."""
            p = Path(path)
            if not p.exists():
                return cls(path=path, name=p.name, is_folder=False, exists=False)
            
            try:
                stat = p.stat()
                size = stat.st_size if p.is_file() else None
                date_created = datetime.fromtimestamp(stat.st_ctime)
                date_modified = datetime.fromtimestamp(stat.st_mtime)
                
                sha512 = None
                if compute_hash and p.is_file() and size and size < C.SHA512_MAX_FILE_SIZE:  # Use configurable limit
                    try:
                        hasher = hashlib.sha512()
                        with open(path, 'rb') as f:
                            #sha512 = hashlib.sha512(f.read()).hexdigest()
                            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
                                hasher.update(chunk)
                        sha512 = hasher.hexdigest()
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
        """
        Container for storing comparison results between left and right items.
        
        Purpose:
        --------
        Holds the comparison outcome between corresponding files/folders from
        left and right directories, including difference types and overall status.
        
        Usage:
        ------
        result = FolderCompareSync_class.ComparisonResult_class(left_item, right_item, differences_set)
        if result.is_different:
            print(f"Found differences: {result.differences}")
        """
        left_item: Optional[FolderCompareSync_class.FileMetadata_class]
        right_item: Optional[FolderCompareSync_class.FileMetadata_class]
        differences: set[str]  # Set of difference types: 'existence', 'size', 'date_created', 'date_modified', 'sha512'
        is_different: bool = False
        
        def __post_init__(self):
            self.is_different = len(self.differences) > 0
    
    class ErrorDetailsDialog_class:
        """Custom error dialog with expandable details section."""
        
        def __init__(self, parent, title, summary, details):
            self.dialog = tk.Toplevel(parent)
            self.dialog.title(title)
            self.dialog.geometry("500x200")
            self.dialog.resizable(True, True)
            self.dialog.transient(parent)
            self.dialog.grab_set()
            
            # v001.0014 added [create scaled fonts for error dialog]
            # Create scaled fonts for this dialog
            default_font = tkfont.nametofont("TkDefaultFont") # v001.0014 added [create scaled fonts for error dialog]
            
            self.scaled_label_font = default_font.copy() # v001.0014 added [create scaled fonts for error dialog]
            self.scaled_label_font.configure(size=C.SCALED_LABEL_FONT_SIZE) # v001.0014 added [create scaled fonts for error dialog]
            # Create a bold version
            self.scaled_label_font_bold = self.scaled_label_font.copy()
            self.scaled_label_font_bold.configure(weight="bold")
            
            self.scaled_button_font = default_font.copy() # v001.0014 added [create scaled fonts for error dialog]
            self.scaled_button_font.configure(size=C.SCALED_BUTTON_FONT_SIZE) # v001.0014 added [create scaled fonts for error dialog]
            # Create a bold version
            self.scaled_button_font_bold = self.scaled_button_font.copy()
            self.scaled_button_font_bold.configure(weight="bold")
            
            # Main frame
            main_frame = ttk.Frame(self.dialog, padding=12) # v001.0014 changed [tightened padding from padding=15 to padding=12]
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Error icon and summary
            summary_frame = ttk.Frame(main_frame)
            summary_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
            
            ttk.Label(summary_frame, text="❌", font=("TkDefaultFont", 16)).pack(side=tk.LEFT, padx=(0, 10))
            
            # Truncate summary if too long
            display_summary = summary[:200] + "..." if len(summary) > 200 else summary
            ttk.Label(summary_frame, text=display_summary, wraplength=400, font=self.scaled_label_font).pack(side=tk.LEFT, fill=tk.X, expand=True) # v001.0014 changed [use scaled label font instead of default]
            
            # Buttons frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
            
            self.details_shown = False
            self.details_button = ttk.Button(button_frame, text="Show Details ▼", command=self.toggle_details)
            self.details_button.pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="OK", command=self.dialog.destroy).pack(side=tk.RIGHT)
            
            # Details frame (initially hidden)
            self.details_frame = ttk.LabelFrame(main_frame, text="Full Error Details", padding=5)
            
            # Details text with scrollbar
            self.details_text = tk.Text(self.details_frame, wrap=tk.WORD, height=10, width=60)
            details_scroll = ttk.Scrollbar(self.details_frame, command=self.details_text.yview)
            self.details_text.configure(yscrollcommand=details_scroll.set)
            
            self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.details_text.insert('1.0', details)
            self.details_text.config(state=tk.DISABLED)
            
            self.full_error = f"{summary}\n\nDetails:\n{details}"
            
            # Center on parent
            self.dialog.update_idletasks()
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
            self.dialog.geometry(f"+{x}+{y}")
    
        def toggle_details(self):
            if self.details_shown:
                self.details_frame.pack_forget()
                self.details_button.config(text="Show Details ▼")
                self.dialog.geometry("500x200")
            else:
                self.details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
                self.details_button.config(text="Hide Details ▲")
                self.dialog.geometry("500x400")
            self.details_shown = not self.details_shown
            
        def copy_to_clipboard(self):
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(self.full_error)
            self.dialog.update()
            # Show temporary confirmation
            self.details_button.config(text="Copied! ✓")
            self.dialog.after(1500, lambda: self.details_button.config(
                text="Hide Details ▲" if self.details_shown else "Show Details ▼"
            ))

    @staticmethod
    def format_timestamp(timestamp: Union[datetime, float, int, None], 
                        include_timezone: bool = False, 
                        include_microseconds: bool = True) -> str:
        """
        Universal timestamp formatting utility function.
        
        Purpose:
        --------
        Handles multiple timestamp input types and formatting options for consistent
        timestamp display throughout the application.
        
        Args:
        -----
        timestamp: Can be datetime object, float/int epoch time, or None
        include_timezone: Whether to include timezone info in output
        include_microseconds: Whether to include microsecond precision
        
        Returns:
        --------
        str: Formatted timestamp string or empty string if None
        
        Examples:
        ---------
        >>> format_timestamp(datetime.now())
        "2024-12-08 14:30:22.123456"
        
        >>> format_timestamp(1701234567.123456, include_microseconds=True)
        "2023-11-29 08:02:47.123456"
        
        >>> format_timestamp(None)
        ""
        
        >>> dt_with_tz = datetime.now(timezone.utc)
        >>> format_timestamp(dt_with_tz, include_timezone=True)
        "2024-12-08 14:30:22.123456 UTC"
        """
        if timestamp is None:
            return ""
        try:
            # Convert input to datetime object
            if isinstance(timestamp, datetime):
                dt = timestamp
            elif isinstance(timestamp, (int, float)):
                # Convert epoch timestamp to datetime in local timezone
                dt = datetime.fromtimestamp(timestamp)
            else:
                # Fallback for unexpected types
                return str(timestamp)
            
            # Build format string based on options
            if include_microseconds:
                base_format = "%Y-%m-%d %H:%M:%S.%f"
            else:
                base_format = "%Y-%m-%d %H:%M:%S"
            
            # Format the datetime
            formatted = dt.strftime(base_format)
            
            # Add timezone if requested and available
            if include_timezone and dt.tzinfo is not None:
                tz_name = dt.strftime("%Z")
                if tz_name:  # Only add if timezone name is available
                    formatted += f" {tz_name}"
            
            return formatted
        except (ValueError, OSError, OverflowError) as e:
            # Handle invalid timestamps gracefully
            log_and_flush(logging.DEBUG, f"Invalid timestamp formatting: {timestamp} - {e}")
            return f"Invalid timestamp: {timestamp}"
    
    @staticmethod
    def format_size(size_bytes):
        """
        Format file size in human readable format.
        
        Purpose:
        --------
        Converts byte values to human-readable format with appropriate
        units (B, KB, MB, GB, TB) for display in the UI.
        
        Args:
        -----
        size_bytes: Size in bytes
        
        Returns:
        --------
        str: Formatted size string
        """
        if size_bytes is None:
            return ""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
    
    def __init__(self):
        """Initialize the main application with all components and limits."""
        log_and_flush(logging.INFO, "Initializing FolderCompareSync application")

        if __debug__:
            if get_log_level() == logging.DEBUG:
                log_and_flush(logging.DEBUG, "Debug mode enabled - Debug log_level active")
            else:
                log_and_flush(logging.DEBUG, "Debug mode enabled - non-Debug log_level active")
        else:
            if get_log_level() == logging.DEBUG:
                log_and_flush(logging.INFO, "Debug mode disabled - Debug log_level active")
            else:
                log_and_flush(logging.INFO, "Debug mode disabled - non-Debug log_level active")

        #---------------------------------------------------------------------------------------------------------------
        # Purely debug code to dump a list of global modules imported
        if __debug__:
            try:
                # Basic identities
                log_and_flush(logging.DEBUG, f"[GI] module file: {getattr(GI, '__file__', '<no __file__>')}")
                log_and_flush(logging.DEBUG, f"[GI] has __all__? {hasattr(GI,'__all__')}")
                max_dumped_entries = 200
                if hasattr(GI, '__all__'):
                    log_and_flush(logging.DEBUG, f"[GI] __all__ count: {len(GI.__all__)}")
                    log_and_flush(logging.DEBUG, f"[GI] __all__ (first 25): {list(GI.__all__)[:25]}")
                    for idx, name in enumerate(GI.__all__[:max_dumped_entries], start=1):
                        log_and_flush(logging.DEBUG, f"[GI] __all__ #{idx}: {name}")
                    if len(GI.__all__) > max_dumped_entries:
                        log_and_flush(logging.DEBUG, f"[GI] __all__ ... truncated after {max_dumped_entries} entries")
                    log_and_flush(logging.DEBUG, f"[GI] 'tk' in __all__? {'tk' in GI.__all__}")
                else:
                    log_and_flush(logging.DEBUG, f"[GI] __all__ count: {len(GI.__all__)} : __all__ has NO entries")
                # Is tk actually an attribute on the hub module?
                log_and_flush(logging.DEBUG, f"[GI] hasattr(GI,'tk')? {hasattr(GI,'tk')}")
        
                # Did star-import bind tk into *this* module’s globals?
                log_and_flush(logging.DEBUG, f"[local] 'tk' in globals()? {'tk' in globals()}")
                if 'tk' in globals():
                    # Optional: show the Tk version for sanity
                    try:
                        log_and_flush(logging.DEBUG, f"[local] Tk version: {tk.TkVersion}")
                    except Exception as e:
                        log_and_flush(logging.DEBUG, f"[local] tk present but version check failed: {e!r}")
                else:
                    log_and_flush(logging.DEBUG, f"[local] Tk is NOT IN globals()")
            except Exception as e:
                log_and_flush(logging.DEBUG, f"[GI] debug-dump failed: {type(e).__name__}: {e}")
        #---------------------------------------------------------------------------------------------------------------

        self.root = tk.Tk()
        self.root.title("FolderCompareSync - Folder Comparison and Syncing Tool")
    
        # v001.0021 - fix UI recreation to use in-place rebuild instead of new instance
        # v001.0021 - Create fonts and styles (extracted to separate method for UI recreation)
        self.create_fonts_and_styles()
    
        # Get screen dimensions for smart window sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Use configurable window sizing percentages
        window_width = int(screen_width * C.WINDOW_WIDTH_PERCENT)
        window_height = int(screen_height * C.WINDOW_HEIGHT_PERCENT)
        
        # Center horizontally, use configurable top offset for optimal taskbar clearance
        x = (screen_width - window_width) // 2
        y = C.WINDOW_TOP_OFFSET
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(C.MIN_WINDOW_WIDTH, C.MIN_WINDOW_HEIGHT)  # Use configurable minimum size
        
        # Application state variables
        self.left_folder = tk.StringVar()
        self.right_folder = tk.StringVar()
        self.compare_existence = tk.BooleanVar(value=True)
        self.compare_size = tk.BooleanVar(value=True)
        self.compare_date_created = tk.BooleanVar(value=True)
        self.compare_date_modified = tk.BooleanVar(value=True)
        self.compare_sha512 = tk.BooleanVar(value=False)
        self.overwrite_mode = tk.BooleanVar(value=True)
        self.dry_run_mode = tk.BooleanVar(value=False)
        
        # Filtering state # v000.0002 changed - removed sorting
        self.filter_wildcard = tk.StringVar()

        self.filtered_results = {}  # Store filtered comparison results
        self.is_filtered = False
        
        # Data storage for comparison results and selection state
        self.comparison_results: dict[str, FolderCompareSync_class.ComparisonResult_class] = {}
        self.selected_left: set[str] = set()
        self.selected_right: set[str] = set()
        self.tree_structure: dict[str, list[str]] = {C.LEFT_SIDE_LOWERCASE: [], C.RIGHT_SIDE_LOWERCASE: []}
        
        # Path mapping for proper status determination and tree navigation
        # Maps relative_path -> tree_item_id for efficient lookups
        self.path_to_item_left: dict[str, str] = {}  # rel_path -> tree_item_id
        self.path_to_item_right: dict[str, str] = {}  # rel_path -> tree_item_id
        
        # Store root item IDs for special handling in selection logic
        self.root_item_left: Optional[str] = None
        self.root_item_right: Optional[str] = None
        
        # Flag to prevent recursive display updates during tree operations
        self._updating_display = False
        
        # Status log management using configurable constants
        self.status_log_lines = []  # Store status messages
        self.max_status_lines = C.STATUS_LOG_MAX_HISTORY  # Use configurable maximum (5000)
        
        # File count tracking for limits
        self.file_count_left = 0
        self.file_count_right = 0
        self.total_file_count = 0
        self.limit_exceeded = False
        
        # UI References for widget interaction
        self.left_tree = None
        self.right_tree = None
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="Summary: No comparison performed")
        self.status_log_text = None  # Will be set in setup_ui
        
        # copy system with staged strategy and dry run support
        self.copy_manager = FileCopyManager_class(status_callback=self.add_status_message)
        
        if __debug__:
            log_and_flush(logging.DEBUG, "Application state initialized with dual copy system")
        
        self.setup_ui()
        
        # Add startup warnings about performance and limits
        self.add_status_message("Application initialized - dual copy system ready")
        self.add_status_message(f"WARNING: Large folder operations may be slow. Maximum {C.MAX_FILES_FOLDERS:,} files/folders supported.")
        self.add_status_message("Tip: Use filtering and dry run mode for testing with large datasets.")
        
        # Display detected timezone information
        timezone_str = self.copy_manager.timestamp_manager.get_timezone_string()
        self.add_status_message(f"Timezone detected: {timezone_str} - will be used for timestamp operations")
        log_and_flush(logging.INFO, "Application initialization complete ")

    def create_fonts_and_styles(self):
        """Create or recreate fonts and styles based on current global values."""
        # v001.0021 added [extracted font/style creation for UI recreation support]
        # 1) Get the existing default font and make a bold copy
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.bold_font = self.default_font.copy()
        self.bold_font.configure(weight="bold")
        
        # v001.0014 added [create scaled fonts for UI elements while preserving tree fonts]
        # Create scaled fonts based on configuration
        self.scaled_button_font = self.default_font.copy()
        self.scaled_button_font.configure(size=C.SCALED_BUTTON_FONT_SIZE)
        # Create a bold version
        self.scaled_button_font_bold = self.scaled_button_font.copy()
        self.scaled_button_font_bold.configure(weight="bold")
        
        self.scaled_label_font = self.default_font.copy()
        self.scaled_label_font.configure(size=C.SCALED_LABEL_FONT_SIZE)
        
        self.scaled_entry_font = self.default_font.copy()
        self.scaled_entry_font.configure(size=C.SCALED_ENTRY_FONT_SIZE)
        
        self.scaled_checkbox_font = self.default_font.copy()
        self.scaled_checkbox_font.configure(size=C.SCALED_CHECKBOX_FONT_SIZE)
        
        self.scaled_dialog_font = self.default_font.copy()
        self.scaled_dialog_font.configure(size=C.SCALED_DIALOG_FONT_SIZE)
        
        self.scaled_status_font = self.default_font.copy()
        self.scaled_status_font.configure(size=C.SCALED_STATUS_MESSAGE_FONT_SIZE)
        
        self.style = ttk.Style(self.root)
        # 2) Create colour styles for some bolded_fonts
        self.style.configure("LimeGreenBold.TButton", foreground="limegreen",font=self.scaled_button_font_bold)
        self.style.configure("GreenBold.TButton", foreground="green",font=self.scaled_button_font_bold)
        self.style.configure("DarkGreenBold.TButton", foreground="darkgreen",font=self.scaled_button_font_bold)
        self.style.configure("RedBold.TButton", foreground="red",font=self.scaled_button_font_bold)
        self.style.configure("PurpleBold.TButton", foreground="purple",font=self.scaled_button_font_bold)
        self.style.configure("MediumPurpleBold.TButton", foreground="mediumpurple",font=self.scaled_button_font_bold)
        self.style.configure("IndigoBold.TButton", foreground="indigo",font=self.scaled_button_font_bold)
        self.style.configure("BlueBold.TButton", foreground="blue",font=self.scaled_button_font_bold)
        self.style.configure("GoldBold.TButton", foreground="gold",font=self.scaled_button_font_bold)
        self.style.configure("YellowBold.TButton", foreground="yellow",font=self.scaled_button_font_bold)

        # v001.0016 added [default button style for buttons without specific colors]
        self.style.configure("DefaultNormal.TButton", font=self.scaled_button_font, weight="normal")
        self.style.configure("DefaultBold.TButton.TButton", font=self.scaled_button_font_bold, weight="bold")

        # v001.0014 added [create custom ttk styles for scaled fonts]
        # Create custom styles for ttk widgets that need scaled fonts
        self.style.configure("Scaled.TCheckbutton", font=self.scaled_checkbox_font)
        self.style.configure("Scaled.TLabel", font=self.scaled_label_font)
        self.style.configure("StatusMessage.TLabel", font=self.scaled_status_font)
        self.style.configure("Scaled.TEntry", font=self.scaled_entry_font)
    
        # Configure tree row height for all treeviews globally # v001.0015 added [tree row height control for compact display]
        self.style.configure("Treeview", rowheight=C.TREE_ROW_HEIGHT) # v001.0015 added [tree row height control for compact display]

    def add_status_message(self, message):
        """
        FolderCompareSync_class: Add a timestamped message to the status log using configurable history limit.
        
        Purpose:
        --------
        Maintains a comprehensive log of all application operations with timestamps
        for debugging, auditing, and user feedback purposes.
        
        Args:
        -----
        message: Message to add to status log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_line = f"{timestamp} - {message}"
        
        # Add to our internal list
        self.status_log_lines.append(status_line)
        
        # Trim to configurable maximum lines (5000)
        if len(self.status_log_lines) > self.max_status_lines:
            self.status_log_lines = self.status_log_lines[-self.max_status_lines:]
            
        # Update the text widget if it exists
        if self.status_log_text:
            self.status_log_text.config(state=tk.NORMAL)
            self.status_log_text.delete('1.0', tk.END)
            self.status_log_text.insert('1.0', '\n'.join(self.status_log_lines))
            self.status_log_text.config(state=tk.DISABLED)
            self.status_log_text.see(tk.END)  # Auto-scroll to bottom
            
        log_and_flush(logging.INFO, f"FolderCompareSync_class: POSTED STATUS MESSAGE: {message}")

    def export_status_log(self):
        """
        Export the complete status log to clipboard and optionally to a file.
        
        Purpose:
        --------
        Provides users with the ability to save or share comprehensive operation
        logs for debugging, record keeping, or support purposes.
        """
        if not self.status_log_lines:
            messagebox.showinfo("Export Status Log", "No status log data to export.")
            return
        
        # Prepare export data
        export_text = "\n".join(self.status_log_lines)
        total_lines = len(self.status_log_lines)
        
        try:
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(export_text)
            self.root.update()  # Make sure clipboard is updated
            
            # Ask user if they want to save to file as well
            response = messagebox.askyesnocancel(
                "Export Status Log", 
                f"Status log ({total_lines:,} lines) copied to clipboard!\n\n"
                f"Would you also like to save to a file?\n\n"
                f"Yes = Save to file\n"
                f"No = Clipboard only\n"
                f"Cancel = Cancel export"
            )
            
            if response is True:  # Yes - save to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                default_filename = f"foldercomparesync_status_{timestamp}.log"
                
                file_path = filedialog.asksaveasfilename(
                    title="Save Status Log",
                    defaultextension=".log",
                    initialname=default_filename,
                    filetypes=[
                        ("Log files", "*.log"),
                        ("Text files", "*.txt"),
                        ("All files", "*.*")
                    ]
                )
                
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(export_text)
                    
                    self.add_status_message(f"Status log exported to: {file_path}")
                    messagebox.showinfo("Export Complete", f"Status log saved to:\n{file_path}")
                else:
                    self.add_status_message("Status log export to file cancelled")
            elif response is False:  # No - clipboard only
                self.add_status_message(f"Status log ({total_lines:,} lines) exported to clipboard")
            else:  # Cancel
                self.add_status_message("Status log export cancelled")
                
        except Exception as e:
            error_msg = f"Failed to export status log: {str(e)}"
            self.add_status_message(f"ERROR: {error_msg}")
            self.show_error(error_msg)

    def on_dry_run_changed(self):
        """
        Handle dry run mode checkbox changes.
        
        Purpose:
        --------
        Ensures proper interaction between dry run and overwrite modes,
        automatically disabling overwrite when dry run is enabled for safety.
        """
        if self.dry_run_mode.get():
            # When dry run is enabled, disable overwrite mode for safety
            self.overwrite_mode.set(False)
            self.add_status_message("DRY RUN mode enabled - Overwrite mode disabled for safety")
        else:
            self.add_status_message("DRY RUN mode disabled - Normal operations enabled")

    def delete_left_orphans_onclick(self): # v001.0017 changed [now calls consolidated method]
        """Handle Delete Orphaned Files from LEFT-only button using enhanced orphan detection."""
        self.delete_orphans(C.LEFT_SIDE_LOWERCASE)

    def delete_right_orphans_onclick(self): # v001.0017 changed [now calls consolidated method]
        """Handle Delete Orphaned Files from RIGHT-only button using enhanced orphan detection."""
        self.delete_orphans(C.RIGHT_SIDE_LOWERCASE)

    def delete_orphans(self, side: str): # v001.0017 added [consolidated delete orphans method]
        """
        Handle Delete Orphaned Files button for specified side with enhanced orphan detection.
        
        Purpose:
        --------
        Consolidated method that handles delete orphans functionality for both left and right sides
        using enhanced orphan classification logic that distinguishes true orphans from folders
        that just contain orphaned files.
        
        Args:
        -----
        side: LEFT_SIDE_LOWERCASE or RIGHT_SIDE_LOWERCASE - which side to process orphaned files for
        """
        log_and_flush(logging.DEBUG, f"Entered FolderCompareSync_class: delete_orphans: side='{side}'")
        if self.limit_exceeded:
            log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': Operation Disabled, Delete operations are disabled when file limits are exceeded.")
            messagebox.showwarning("Operation Disabled", "Delete operations are disabled when file limits are exceeded.")
            return
            
        if not self.comparison_results:
            log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': No comparison data available")
            self.add_status_message("No comparison data available - please run comparison first")
            messagebox.showinfo("No Data", "Please perform a folder comparison first.")
            return
            
        # Get current filter if active
        active_filter = self.filter_wildcard.get() if self.is_filtered else None
        
        # v001.0017 changed [use enhanced detect_orphaned_files method]
        # Get enhanced orphan detection results
        log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': calling 'DeleteOrphansManager_class.detect_orphaned_files'")
        orphaned_files, orphan_detection_metadata = DeleteOrphansManager_class.detect_orphaned_files(
            self.comparison_results, side, active_filter
        )
        log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': returned from 'DeleteOrphansManager_class.detect_orphaned_files'")
        
        side_upper = side.upper()  # v001.0017 added [preserve original case for display while using case insensitive logic]
        if not orphaned_files:
            filter_text = f" (with active filter: {active_filter})" if active_filter else ""
            log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': No orphaned files found on {side_upper} side {filter_text}")
            self.add_status_message(f"No orphaned files found on {side_upper} side {filter_text}")
            return
            
        # v001.0017 added [log enhanced orphan classification results]
        true_orphans = sum(1 for meta in orphan_detection_metadata.values() if meta.get('is_true_orphan', False))
        contains_orphans = sum(1 for meta in orphan_detection_metadata.values() if not meta.get('is_true_orphan', True))
        
        log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': side='{side_upper}' true orphans='{true_orphans}' folders containing orphans={contains_orphans}")
        self.add_status_message(f"Enhanced orphan detection on {side_upper} side: {true_orphans} true orphans, {contains_orphans} folders containing orphans")
        self.add_status_message(f"Opening enhanced delete orphans dialog for {side_upper} side: {len(orphaned_files)} total items")
        
        try:
            # v001.0017 changed [pass enhanced detection metadata to DeleteOrphansManager]
            # Get the appropriate source folder with case insensitive comparison
            source_folder = self.left_folder.get() if side.lower() == C.LEFT_SIDE_LOWERCASE else self.right_folder.get()  # v001.0017 changed [case insensitive comparison]
            
            # Create and show enhanced delete orphans manager/dialog
            log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': creating a 'DeleteOrphansManager_class' manager")
            manager = DeleteOrphansManager_class(
                parent=self.root,
                orphaned_files=orphaned_files,
                side=side,
                source_folder=source_folder,
                dry_run_mode=self.dry_run_mode.get(),
                comparison_results=self.comparison_results,
                active_filter=active_filter
            )
            log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': created a 'DeleteOrphansManager_class' manager")
            
            # v001.0017 added [pass enhanced detection metadata to manager for smart initialization]
            # Note: This requires enhancement to DeleteOrphansManager_class.__init__ to accept this parameter
            if hasattr(manager, 'set_enhanced_detection_metadata'):  # v001.0017 added [backward compatibility check]
                manager.set_enhanced_detection_metadata(orphan_detection_metadata)  # v001.0017 added [pass enhanced metadata]
            
            # Wait for dialog to complete
            self.root.wait_window(manager.dialog)
            
            # Check if files were actually deleted (not dry run)
            #if hasattr(manager, 'result') and manager.result.lower() == 'deleted'.lower() and not self.dry_run_mode.get(): # v001.0018 superseded, [add None check for manager.result before calling .lower()]
            if hasattr(manager, 'result') and manager.result and manager.result.lower() == 'deleted'.lower():   # v001.0018 changed [add None check for manager.result before calling .lower()]
                self.add_status_message("Enhanced {side_upper} side delete operation completed - refreshing folder comparison...")
                log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': delete operation completed - refreshing folder comparison...")
                # Refresh comparison to show updated state
                self.refresh_after_copy_or_delete_operation()
            else:
                log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': Enhanced {side_upper} side delete orphans dialog closed")
                self.add_status_message("Enhanced {side_upper} side delete orphans dialog closed")
                
        except Exception as e:
            error_msg = f"Error opening enhanced {side_upper} side delete orphans dialog: {str(e)}"
            log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': ERROR: {error_msg}")
            self.add_status_message(f"ERROR: {error_msg}")
            self.show_error(error_msg)
        finally:
            # Cleanup memory after dialog operations
            gc.collect()
        log_and_flush(logging.DEBUG, f"FolderCompareSync_class: delete_orphans: side='{side}': exiting 'delete_orphans'")

    def setup_ui(self):
        """
        Initialize the user interface with features including dry run and export capabilities.
        
        Purpose:
        --------
        Creates and configures all GUI components including the new dry run checkbox,
        export functionality, and limit warnings for the application interface.
        """
        log_and_flush(logging.DEBUG, "Setting up FolderCompareSync_class user interface with features")
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3) # v001.0014 changed [tightened padding from pady=5 to pady=3]
        
        # Performance warning frame at top
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        warning_label = ttk.Label(
            warning_frame, 
            text=(
                f"⚠ Performance Notice: Large folder operations may be slow. "
                f"Maximum {C.MAX_FILES_FOLDERS:,} files/folders supported. "
                f"SHA512 operations will take circa 2 to 10 seconds elapsed per GB of file read."
            ),
            foreground="royalblue",
            style="Scaled.TLabel" # v001.0014 changed [use scaled label style instead of font]
        )
    
        warning_label.pack(side=tk.LEFT)
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        folder_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
    
        # Left folder selection
        ttk.Label(folder_frame, text="Left Folder:", style="Scaled.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 5)) # v001.0014 changed [use scaled label style]
        ttk.Button(folder_frame, text="Browse", command=self.browse_left_folder, style="DefaultNormal.TButton").grid(row=0, column=1, padx=(0, 5)) # v001.0016 changed [use default button style]
        left_entry = ttk.Entry(folder_frame, textvariable=self.left_folder, width=60, style="Scaled.TEntry") # v001.0014 changed [use scaled entry style]
        left_entry.grid(row=0, column=2, sticky=tk.EW)
        
        # Right folder selection
        ttk.Label(folder_frame, text="Right Folder:", style="Scaled.TLabel").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(3, 0)) # v001.0014 changed [use scaled label style and tightened padding from pady=(5, 0) to pady=(3, 0)]
        ttk.Button(folder_frame, text="Browse", command=self.browse_right_folder, style="DefaultNormal.TButton").grid(row=1, column=1, padx=(0, 5), pady=(3, 0)) # v001.0016 changed [use default button style and tightened padding from pady=(5, 0) to pady=(3, 0)]
        right_entry = ttk.Entry(folder_frame, textvariable=self.right_folder, width=60, style="Scaled.TEntry") # v001.0014 changed [use scaled entry style]
        right_entry.grid(row=1, column=2, sticky=tk.EW, pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
    
        # Let column 2 (the entry) grow
        folder_frame.columnconfigure(2, weight=1)
       
        # Comparison options frame with instructional text
        options_frame = ttk.LabelFrame(main_frame, text="Comparison Options", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        options_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Comparison criteria checkboxes with instructional text
        criteria_frame = ttk.Frame(options_frame)
        criteria_frame.pack(fill=tk.X)
        
        # Add instructional text for better user guidance using configurable styling
        instruction_frame = ttk.Frame(criteria_frame)
        instruction_frame.pack(fill=tk.X)
        
        ttk.Label(instruction_frame, text="Compare Options:", style="Scaled.TLabel").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled label style]
        ttk.Checkbutton(instruction_frame, text="Existence", variable=self.compare_existence, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        ttk.Checkbutton(instruction_frame, text="Size", variable=self.compare_size, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        #ttk.Checkbutton(instruction_frame, text="Date Created", variable=self.compare_date_created, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        #ttk.Checkbutton(instruction_frame, text="Date Modified", variable=self.compare_date_modified, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        ttk.Checkbutton(instruction_frame, text=f"Date Created (tolerance {C.TIMESTAMP_TOLERANCE:.6f}s)", variable=self.compare_date_created, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text=f"Date Modified (tolerance {C.TIMESTAMP_TOLERANCE:.6f}s)", variable=self.compare_date_modified, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(instruction_frame, text="SHA512", variable=self.compare_sha512, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0014 changed [use scaled checkbox style]
        
        # Add instructional text for workflow guidance using configurable colors and font size
        ttk.Label(instruction_frame, text="<- select options then click Compare (see sha512 note above)", 
                 foreground=C.INSTRUCTION_TEXT_COLOR, 
                 font=("TkDefaultFont", C.SCALED_INSTRUCTION_FONT_SIZE, "italic")).pack(side=tk.LEFT, padx=(20, 0))
        
        # Control frame - reorganized for better layout
        control_frame = ttk.Frame(options_frame)
        control_frame.pack(fill=tk.X, pady=(8, 0)) # v001.0014 changed [tightened padding from pady=(10, 0) to pady=(8, 0)]
        
        # Top row of controls with dry run support
        top_controls = ttk.Frame(control_frame)
        top_controls.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Dry run checkbox next to overwrite mode
        dry_run_cb = ttk.Checkbutton(top_controls, text="DRY RUN Only", variable=self.dry_run_mode, command=self.on_dry_run_changed, style="Scaled.TCheckbutton") # v001.0014 changed [use scaled checkbox style]
        dry_run_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Checkbutton(top_controls, text="Overwrite Mode", variable=self.overwrite_mode, style="Scaled.TCheckbutton").pack(side=tk.LEFT, padx=(0, 20)) # v001.0014 changed [use scaled checkbox style]
        ttk.Button(top_controls, text="Compare", command=self.start_comparison, style="LimeGreenBold.TButton").pack(side=tk.LEFT, padx=(0, 20))
    
        # selection controls with auto-clear and complete reset functionality
        # Left pane selection controls
        ttk.Button(top_controls, text="Select All Differences - Left", 
                  command=self.select_all_differences_left, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(top_controls, text="Clear All - Left", 
                  command=self.clear_all_left, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 15)) # v001.0016 changed [use default button style]
        
        # Right pane selection controls  
        ttk.Button(top_controls, text="Select All Differences - Right", 
                  command=self.select_all_differences_right, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(top_controls, text="Clear All - Right", 
                  command=self.clear_all_right, style="DefaultNormal.TButton").pack(side=tk.LEFT) # v001.0016 changed [use default button style]
    
        # Filter and tree control frame
        filter_tree_frame = ttk.Frame(control_frame)
        filter_tree_frame.pack(fill=tk.X, pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
        
        # Wildcard filter controls
        ttk.Label(filter_tree_frame, text="Filter Files by Wildcard:", style="Scaled.TLabel").pack(side=tk.LEFT, padx=(0, 5)) # v001.0014 changed [use scaled label style]
        filter_entry = ttk.Entry(filter_tree_frame, textvariable=self.filter_wildcard, width=20, style="Scaled.TEntry") # v001.0014 changed [use scaled entry style]
        filter_entry.pack(side=tk.LEFT, padx=(0, 5))
        filter_entry.bind('<Return>', lambda e: self.apply_filter())
        
        ttk.Button(filter_tree_frame, text="Apply Filter", command=self.apply_filter, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(filter_tree_frame, text="Clear Filter", command=self.clear_filter, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 20)) # v001.0016 changed [use default button style]
        
        # Tree expansion controls
        ttk.Button(filter_tree_frame, text="Expand All", command=self.expand_all_trees, style="DefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use default button style]
        ttk.Button(filter_tree_frame, text="Collapse All", command=self.collapse_all_trees, style="DefaultNormal.TButton").pack(side=tk.LEFT) # v001.0016 changed [use default button style]
        
        # Debug button (debug mode only) # v001.0019 added [DebugGlobalEditor_class integration - UI button]
        if __debug__:
            ttk.Button(
                filter_tree_frame,
                text="Debug Globals",
                command=self.open_debug_global_editor,
                style="DefaultNormal.TButton"
            ).pack(side=tk.LEFT, padx=(10, 0))

        # Tree comparison frame (adjusted height to make room for status log)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Left tree with columns
        left_frame = ttk.LabelFrame(tree_frame, text=C.LEFT_SIDE_UPPERCASE, padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.left_tree = ttk.Treeview(left_frame, show='tree headings', selectmode='none')
        self.left_tree.heading('#0', text='Structure', anchor=tk.W)
        self.left_tree.column('#0', width=C.TREE_STRUCTURE_WIDTH, minwidth=C.TREE_STRUCTURE_MIN_WIDTH)
        
        # Configure columns for metadata display
        self.setup_tree_columns(self.left_tree)
        
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.left_tree.yview)
        self.left_tree.configure(yscrollcommand=left_scroll.set)
        self.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right tree with columns
        right_frame = ttk.LabelFrame(tree_frame, text=C.RIGHT_SIDE_UPPERCASE, padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self.right_tree = ttk.Treeview(right_frame, show='tree headings', selectmode='none')
        self.right_tree.heading('#0', text='Structure', anchor=tk.W)
        self.right_tree.column('#0', width=C.TREE_STRUCTURE_WIDTH, minwidth=C.TREE_STRUCTURE_MIN_WIDTH)
        
        self.setup_tree_columns(self.right_tree)
        
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_tree.yview)
        self.right_tree.configure(yscrollcommand=right_scroll.set)
        self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Synchronize scrolling between panes
        self.setup_synchronized_scrolling()
        
        # Copy and delete buttons frame - all on one row # v001.0022 changed [reorganized button layout to put copy and delete orphan buttons on same row]
        copy_frame = ttk.Frame(main_frame)
        copy_frame.pack(fill=tk.X, pady=(0, 3))
        
        # Copy buttons pair # v001.0022 added [copy buttons pair comment]
        ttk.Button(copy_frame, text="Copy LEFT to Right", command=self.copy_left_to_right, style="RedBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Copy RIGHT to Left", command=self.copy_right_to_left, style="LimeGreenBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        
        # Moderate gap between button pairs # v001.0022 added [moderate gap between copy and delete button pairs]
        separator_frame = ttk.Frame(copy_frame, width=20)
        separator_frame.pack(side=tk.LEFT, padx=(10, 10))
        
        # Delete orphaned files buttons pair # v001.0022 added [delete buttons pair on same row as copy buttons]
        ttk.Button(copy_frame, text="Delete Orphaned Files from LEFT-only", 
                      command=self.delete_left_orphans_onclick, style="PurpleBold.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Delete Orphaned Files from RIGHT-only", 
                      command=self.delete_right_orphans_onclick, style="DarkGreenBold.TButton").pack(side=tk.LEFT, padx=(0, 10))

        # Quit button on far right
        ttk.Button(copy_frame, text="Quit", command=self.root.quit, style="BlueBold.TButton").pack(side=tk.RIGHT)
    
        # status log frame at bottom with export functionality
        status_log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding=5)
        status_log_frame.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        # Status log header with export button
        status_header = ttk.Frame(status_log_frame)
        status_header.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        ttk.Label(status_header, text=f"Operation History ({C.STATUS_LOG_MAX_HISTORY:,} lines max):", 
                 style="Scaled.TLabel").pack(side=tk.LEFT) # v001.0014 changed [use scaled label style]
        ttk.Button(status_header, text="Export Log", command=self.export_status_log, style="DefaultNormal.TButton").pack(side=tk.RIGHT) # v001.0016 changed [use default button style]
        
        # Create text widget with scrollbar for status log using configurable parameters
        status_log_container = ttk.Frame(status_log_frame)
        status_log_container.pack(fill=tk.X)
        
        self.status_log_text = tk.Text(
            status_log_container, 
            height=C.STATUS_LOG_VISIBLE_LINES,  # Use configurable visible lines
            wrap=tk.WORD,
            state=tk.DISABLED,  # Read-only
            font=C.STATUS_LOG_FONT,    # v001.0016 changed [now uses SCALED_STATUS_MESSAGE_FONT_SIZE]
            bg=C.STATUS_LOG_BG_COLOR,  # Use configurable background color
            fg=C.STATUS_LOG_FG_COLOR   # Use configurable text color
        )
        
        status_log_scroll = ttk.Scrollbar(status_log_container, orient=tk.VERTICAL, command=self.status_log_text.yview)
        self.status_log_text.configure(yscrollcommand=status_log_scroll.set)
        
        self.status_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status and summary frame (moved to bottom, below status log)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        
        ttk.Label(status_frame, textvariable=self.summary_var, style="StatusMessage.TLabel").pack(side=tk.LEFT) # v001.0016 changed [use status message style for summary]
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        ttk.Label(status_frame, text="Status:", style="StatusMessage.TLabel").pack(side=tk.RIGHT, padx=(0, 5)) # v001.0016 changed [use status message style for status label]
        ttk.Label(status_frame, textvariable=self.status_var, style="StatusMessage.TLabel").pack(side=tk.RIGHT) # v001.0016 changed [use status message style for status]
        
        # Configure tree event bindings for interaction
        self.setup_tree_events()
        
        log_and_flush(logging.DEBUG, "FolderCompareSync_class User interface setup complete with features")

    def setup_tree_columns(self, tree): # v000.0002 changed - column sorting disabled
        """
        Setup columns for metadata display in tree (sorting disabled).
        
        Purpose:
        --------
        Configures tree view columns with proper sizing and alignment
        for comprehensive file metadata display. Column sorting has been
        disabled to maintain mandatory folder structure compliance.
        
        Args:
        -----
        tree: Treeview widget to configure
        """
        # columns to show all metadata regardless of compare settings
        tree['columns'] = ('size', 'date_created', 'date_modified', 'sha512', 'status')
        
        # v000.0002 changed - removed column sorting command bindings to restore mandatory compliance
        tree.heading('size', text='Size', anchor=tk.E)
        tree.heading('date_created', text='Date Created', anchor=tk.CENTER)
        tree.heading('date_modified', text='Date Modified', anchor=tk.CENTER)
        tree.heading('sha512', text='SHA512', anchor=tk.CENTER)
        tree.heading('status', text='Status', anchor=tk.W)
        
        # Use configurable column widths
        tree.column('size', width=C.TREE_SIZE_WIDTH, minwidth=C.TREE_SIZE_MIN_WIDTH, anchor=tk.E)
        tree.column('date_created', width=C.TREE_DATE_CREATED_WIDTH, minwidth=C.TREE_DATE_CREATED_MIN_WIDTH, anchor=tk.CENTER)
        tree.column('date_modified', width=C.TREE_DATE_MODIFIED_WIDTH, minwidth=C.TREE_DATE_MODIFIED_MIN_WIDTH, anchor=tk.CENTER)
        tree.column('sha512', width=C.TREE_SHA512_WIDTH, minwidth=C.TREE_SHA512_MIN_WIDTH, anchor=tk.CENTER)
        tree.column('status', width=C.TREE_STATUS_WIDTH, minwidth=C.TREE_STATUS_MIN_WIDTH, anchor=tk.W)

    def check_file_limit_exceeded(self, file_count: int, operation_name: str) -> bool:
        """
        Check if file count exceeds the configured limit and handle appropriately.
        
        Purpose:
        --------
        Provides early detection of file count limits to prevent performance issues
        and provides clear user guidance when limits are exceeded.
        
        Args:
        -----
        file_count: Current number of files/folders found
        operation_name: Name of the operation being performed
        
        Returns:
        --------
        bool: True if limit exceeded, False if within limits
        """
        if file_count > C.MAX_FILES_FOLDERS:
            self.limit_exceeded = True
            
            # Clear trees and data structures
            self.clear_all_data_structures()
            
            # Create bold error message
            error_msg = f"LIMIT EXCEEDED: Found {file_count:,} files/folders in {operation_name}"
            limit_msg = f"Maximum supported: {C.MAX_FILES_FOLDERS:,} files/folders"
            
            self.add_status_message(f"ERROR: {error_msg}")
            self.add_status_message(f"ERROR: {limit_msg}")
            self.add_status_message("SOLUTION: Use filtering to reduce dataset size, or work with smaller folders")
            self.add_status_message("NOTE: This limit prevents performance issues with large datasets")
            
            # Update status display
            self.status_var.set("LIMIT EXCEEDED - Operation Aborted")
            self.summary_var.set(f"ERROR: {error_msg}")
            
            # Show user dialog with detailed error
            detailed_error = (
                f"{error_msg}\n\n"
                f"{limit_msg}\n\n"
                f"To resolve this issue:\n"
                f"• Use filtering to work with specific file types\n"
                f"• Work with smaller subdirectories\n"
                f"• Consider organizing large datasets into manageable chunks\n\n"
                f"This limit prevents performance issues with very large datasets."
            )
            FolderCompareSync_class.ErrorDetailsDialog_class(self.root, "File Limit Exceeded", error_msg, detailed_error)
            
            return True
        
        return False

    def clear_all_data_structures(self):
        """
        Clear all trees and data structures when limits are exceeded.
        
        Purpose:
        --------
        Provides clean reset of all application state when file limits
        are exceeded to ensure consistent application behavior.
        """
        # Clear trees
        if self.left_tree:
            for item in self.left_tree.get_children():
                self.left_tree.delete(item)
        if self.right_tree:
            for item in self.right_tree.get_children():
                self.right_tree.delete(item)
        
        # Clear data structures
        self.comparison_results.clear()
        self.filtered_results.clear()
        self.selected_left.clear()
        self.selected_right.clear()
        self.path_to_item_left.clear()
        self.path_to_item_right.clear()
        
        # Reset state variables
        self.root_item_left = None
        self.root_item_right = None
        self.is_filtered = False
        self.file_count_left = 0
        self.file_count_right = 0
        self.total_file_count = 0

    def apply_filter(self):
        """Apply wildcard filter to display only matching files with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Filtering is disabled when file limits are exceeded.")
            return
            
        wildcard = self.filter_wildcard.get().strip()
        
        if not wildcard:
            self.add_status_message("No wildcard pattern specified")
            return
        
        if not self.comparison_results:
            self.add_status_message("No comparison data to filter - please run comparison first")
            return
        
        log_and_flush(logging.DEBUG, f"Applying wildcard filter: {wildcard}")
        self.add_status_message(f"Applying filter: {wildcard}")
        
        # Create progress dialog for filtering
        progress = ProgressDialog_class(self.root, "Filtering Files", f"Applying filter: {wildcard}...", max_value=100)
        
        try:
            # Use thread for filtering to keep UI responsive
            def filter_thread():
                try:
                    self.perform_filtering(wildcard, progress)
                except Exception as e:
                    log_and_flush(logging.ERROR, f"Filter operation failed: {e}")
                    self.root.after(0, lambda: self.add_status_message(f"Filter failed: {str(e)}"))
                finally:
                    self.root.after(0, progress.close)
            
            threading.Thread(target=filter_thread, daemon=True).start()
            
        except Exception as e:
            progress.close()
            log_and_flush(logging.ERROR, f"Failed to start filter operation: {e}")
            self.add_status_message(f"Filter failed: {str(e)}")

    def perform_filtering(self, wildcard, progress):
        """Perform the actual filtering operation with performance tracking."""
        log_and_flush(logging.DEBUG, f"Performing filtering with pattern: {wildcard}")
        
        progress.update_progress(10, "Preparing filter...")
        
        # Filter comparison results based on wildcard (files only, not folders)
        self.filtered_results = {}
        matched_count = 0
        total_items = len(self.comparison_results)
        
        progress.update_progress(30, "Filtering files...")
        
        for rel_path, result in self.comparison_results.items():
            if rel_path:  # Skip empty paths
                filename = rel_path.split('/')[-1]  # Get just the filename
                
                # Only filter files, not folders
                is_file = ((result.left_item and not result.left_item.is_folder) or 
                          (result.right_item and not result.right_item.is_folder))
                
                if is_file and fnmatch.fnmatch(filename.lower(), wildcard.lower()):
                    self.filtered_results[rel_path] = result
                    matched_count += 1
                    
                    # Limit results for performance using configurable threshold
                    if matched_count >= C.MAX_FILTER_RESULTS:
                        log_and_flush(logging.WARNING, f"Filter results limited to {C.MAX_FILTER_RESULTS} items for performance")
                        break
        
        progress.update_progress(70, f"Found {matched_count} matches, updating display...")
        
        # Update tree display with filtered results
        self.is_filtered = True
        
        # Rebuild trees with filtered results
        self.root.after(0, lambda: self.update_comparison_ui_filtered())
        
        # Update status
        filter_summary = f"Filter applied: {matched_count:,} files match '{wildcard}'"
        if matched_count >= C.MAX_FILTER_RESULTS:
            filter_summary += f" (limited to {C.MAX_FILTER_RESULTS:,} for performance)"
        
        progress.update_progress(100, "Filter complete")
        self.root.after(0, lambda: self.add_status_message(filter_summary))

    def clear_filter(self):
        """Clear the wildcard filter and show all results with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Filter operations are disabled when file limits are exceeded.")
            return
            
        log_and_flush(logging.DEBUG, "Clearing wildcard filter")
        
        self.filter_wildcard.set("")
        self.filtered_results = {}
        self.is_filtered = False
        
        self.add_status_message("Filter cleared - showing all results")
        
        # Rebuild trees with all results
        if self.comparison_results:
            self.update_comparison_ui()

    def expand_all_trees(self):
        """Expand all items in both trees with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Tree operations are disabled when file limits are exceeded.")
            return
            
        log_and_flush(logging.DEBUG, "Expanding all tree items")
        self.add_status_message("Expanding all folders")
        
        def expand_all_recursive(tree, item=''):
            """Recursively expand all items"""
            children = tree.get_children(item)
            for child in children:
                tree.item(child, open=True)
                expand_all_recursive(tree, child)
        
        # Expand both trees
        expand_all_recursive(self.left_tree)
        expand_all_recursive(self.right_tree)
        
        self.add_status_message("All folders expanded")

    def collapse_all_trees(self):
        """Collapse all items in both trees with limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Tree operations are disabled when file limits are exceeded.")
            return
            
        log_and_flush(logging.DEBUG, "Collapsing all tree items")
        self.add_status_message("Collapsing all folders")
        
        def collapse_all_recursive(tree, item=''):
            """Recursively collapse all items"""
            children = tree.get_children(item)
            for child in children:
                tree.item(child, open=False)
                collapse_all_recursive(tree, child)
        
        # Collapse both trees (but keep root expanded)
        for child in self.left_tree.get_children():
            self.left_tree.item(child, open=False)
            collapse_all_recursive(self.left_tree, child)
            
        for child in self.right_tree.get_children():
            self.right_tree.item(child, open=False)
            collapse_all_recursive(self.right_tree, child)
        
        self.add_status_message("All folders collapsed")

    def setup_synchronized_scrolling(self):
        """Setup synchronized scrolling between tree views."""
        def sync_yview(*args):
            self.left_tree.yview(*args)
            self.right_tree.yview(*args)
        
        # Create a shared scrollbar command for synchronized scrolling
        self.left_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.right_tree, *args))
        self.right_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.left_tree, *args))
        
    def sync_scrollbar(self, other_tree, *args):
        """Synchronize scrollbar between trees."""
        # Update both trees' scroll position for synchronized viewing
        self.left_tree.yview_moveto(args[0])
        self.right_tree.yview_moveto(args[0])
        
    def setup_tree_events(self):
        """
        Setup event bindings for tree interactions with limit checking.
        
        Purpose:
        --------
        Configures mouse and keyboard event handling for tree widgets
        while respecting file count limits for performance.
        """
        log_and_flush(logging.DEBUG, "Setting up tree event bindings")
        
        # Bind tree expansion/collapse events with state preservation
        self.left_tree.bind('<<TreeviewOpen>>', lambda e: self.handle_tree_expand_collapse(self.left_tree, self.right_tree, e, True))
        self.left_tree.bind('<<TreeviewClose>>', lambda e: self.handle_tree_expand_collapse(self.left_tree, self.right_tree, e, False))
        self.right_tree.bind('<<TreeviewOpen>>', lambda e: self.handle_tree_expand_collapse(self.right_tree, self.left_tree, e, True))
        self.right_tree.bind('<<TreeviewClose>>', lambda e: self.handle_tree_expand_collapse(self.right_tree, self.left_tree, e, False))
        
        # Bind checkbox-like behavior for item selection (with missing item exclusion)
        self.left_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.left_tree, C.LEFT_SIDE_LOWERCASE, e))
        self.right_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.right_tree, C.RIGHT_SIDE_LOWERCASE, e))
        
    def handle_tree_expand_collapse(self, source_tree, target_tree, event, is_expand):
        """
        Handle tree expansion/collapse with proper state preservation and limit checking.
        
        Purpose:
        --------
        Ensures selection state is maintained during expand/collapse operations
        while respecting performance limits.
        """
        if self._updating_display or self.limit_exceeded:
            return  # Prevent recursive updates or operations when limits exceeded
            
        item = source_tree.selection()[0] if source_tree.selection() else source_tree.focus()
        if item:
            try:
                # Synchronize expand/collapse state with other tree
                target_tree.item(item, open=is_expand)
                
                if __debug__:
                    action = "expand" if is_expand else "collapse"
                    log_and_flush(logging.DEBUG, f"Synchronized tree {action} for item {item}")
                    
            except tk.TclError:
                pass  # Item doesn't exist in target tree
                
            # CRITICAL: Do NOT call update_tree_display() here as it interferes with selection state
            # Selection state should remain completely independent of expand/collapse operations
                
    def is_missing_item(self, tree, item_id):
        """
        Check if an item is a missing item (has [MISSING] in text or 'missing' tag).
        
        Purpose:
        --------
        Helper function to identify non-clickable missing items for proper
        user interaction handling and UI consistency.
        
        Args:
        -----
        tree: Tree widget containing the item
        item_id: ID of the item to check
        
        Returns:
        --------
        bool: True if item is missing, False otherwise
        """
        if not item_id:
            return False
            
        item_text = tree.item(item_id, 'text')
        item_tags = tree.item(item_id, 'tags')
        
        # Check if item is marked as missing
        is_missing = '[MISSING]' in item_text or 'missing' in item_tags
        
        if __debug__ and is_missing:
            log_and_flush(logging.DEBUG, f"Identified missing item: {item_id} with text: {item_text}")
            
        return is_missing
        
    def is_different_item(self, item_id, side):
        """
        Check if an item represents a different file/folder that needs syncing.
        
        Purpose:
        --------
        Used for smart folder selection logic to identify items that
        have differences and should be included in copy operations.
        
        Args:
        -----
        item_id: Tree item ID to check
        side: Which tree side (LEFT_SIDE_LOWERCASE or RIGHT_SIDE_LOWERCASE)
        
        Returns:
        --------
        bool: True if item is different and exists, False otherwise
        """
        if not item_id:
            return False
            
        # Get the relative path for this item
        rel_path = self.get_item_relative_path(item_id, side)
        if not rel_path:
            return False
            
        # Check in appropriate results set (filtered or full)
        results = self.filtered_results if self.is_filtered else self.comparison_results
        result = results.get(rel_path)
        
        if result and result.is_different:
            # Also ensure the item exists on this side
            item_exists = False
            if side.lower() == C.LEFT_SIDE_LOWERCASE and result.left_item and result.left_item.exists:
                item_exists = True
            elif side.lower() == C.RIGHT_SIDE_LOWERCASE and result.right_item and result.right_item.exists:
                item_exists = True
                
            if __debug__ and item_exists:
                log_and_flush(logging.DEBUG, f"Item {item_id} ({rel_path}) is different and exists on {side} side")
                
            return item_exists
            
        return False
        
    def get_item_relative_path(self, item_id, side):
        """
        Get the relative path for a tree item by looking it up in path mappings.
        
        Purpose:
        --------
        More efficient than reconstructing from tree hierarchy,
        provides fast lookup for tree item paths.
        
        Args:
        -----
        item_id: Tree item ID
        side: Which tree side (LEFT_SIDE_LOWERCASE or RIGHT_SIDE_LOWERCASE)
        
        Returns:
        --------
        str: Relative path or None if not found
        """
        path_map = self.path_to_item_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.path_to_item_right
        
        # Find the relative path by searching the mapping
        for rel_path, mapped_item_id in path_map.items():
            if mapped_item_id == item_id:
                return rel_path
                
        return None
                
    def handle_tree_click(self, tree, side, event):
        """
        Handle clicks on tree items (for checkbox behavior) with limit checking.
        
        Purpose:
        --------
        Processes user clicks on tree items to toggle selection state
        while ignoring clicks on missing items and respecting limits.
        """
        if self.limit_exceeded:
            return  # Don't process clicks when limits exceeded

        # Ignore clicks on the +/- indicator (expand/collapse control) and column headers/separators
        element = tree.identify('element', event.x, event.y)
        region  = tree.identify('region',  event.x, event.y)
        if element == 'Treeitem.indicator' or region in ('heading', 'separator'):
            return
            
        item = tree.identify('item', event.x, event.y)
        if item:
            # Check if item is missing and ignore clicks on missing items
            if self.is_missing_item(tree, item):
                if __debug__:
                    log_and_flush(logging.DEBUG, f"Ignoring click on missing item: {item}")
                return  # Don't process clicks on missing items
                
            # Toggle selection for this item if it's not missing
            self.toggle_item_selection(item, side)
            
    def toggle_item_selection(self, item_id, side):
        """Toggle selection state of an item and handle parent/child logic with root safety."""
        if self.limit_exceeded:
            return  # Don't process selections when limits exceeded
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Toggling selection for item {item_id} on {side} side")
            
        selected_set = self.selected_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.selected_right
        tree = self.left_tree if side.lower() == C.LEFT_SIDE_LOWERCASE else self.right_tree
        
        was_selected = item_id in selected_set
        
        if item_id in selected_set:
            # Unticking - remove from selection and untick all parents and children
            selected_set.discard(item_id)
            # unticking with root safety check
            self.untick_parents_with_root_safety(item_id, side)
            self.untick_children(item_id, side)
        else:
            # Ticking - add to selection and tick all children (only different ones)
            selected_set.add(item_id)
            self.tick_children_smart(item_id, side)
            
        if __debug__:
            action = "unticked" if was_selected else "ticked"
            log_and_flush(logging.DEBUG, f"Item {action}, {side} selection count: {len(selected_set)}")
            
        # Log selection changes to status window
        total_selected = len(self.selected_left) + len(self.selected_right)
        action_word = "Deselected" if was_selected else "Selected"
        rel_path = self.get_item_relative_path(item_id, side) or "item"
        self.add_status_message(f"{action_word} {rel_path} ({side}) - Total selected: {total_selected}")
            
        self.update_tree_display_safe()
        self.update_summary()
        
    def tick_children_smart(self, item_id, side):
        """
        Smart tick children - only select different items underneath.
        
        Purpose:
        --------
        Implements intelligent folder selection logic that only selects
        child items that have actual differences requiring synchronization.
        """
        selected_set = self.selected_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.selected_right
        tree = self.left_tree if side.lower() == C.LEFT_SIDE_LOWERCASE else self.right_tree
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Smart ticking children for {item_id} - only selecting different items")
        
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
                    log_and_flush(logging.DEBUG, f"Smart-selected different item: {item} ({rel_path})")
                    
            # Recursively process children
            for child in tree.get_children(item):
                tick_recursive(child)
                
        # Process all children of the ticked item
        for child in tree.get_children(item_id):
            tick_recursive(child)
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Smart selection complete: {different_count}/{total_count} children selected (only different items)")
            
        # Log smart selection results
        if different_count > 0:
            folder_path = self.get_item_relative_path(item_id, side) or "folder"
            self.add_status_message(f"Smart-selected {different_count} different items in {folder_path} ({side})")
            
    def untick_children(self, item_id, side):
        """Untick all children of an item recursively."""
        selected_set = self.selected_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.selected_right
        tree = self.left_tree if side.lower() == C.LEFT_SIDE_LOWERCASE else self.right_tree
        
        def untick_recursive(item):
            selected_set.discard(item)
            for child in tree.get_children(item):
                untick_recursive(child)
                
        for child in tree.get_children(item_id):
            untick_recursive(child)
            
    def untick_parents_with_root_safety(self, item_id, side):
        """
        Untick all parents of an item with safety check for root level.
        
        Purpose:
        --------
        Also prevent attempting to untick parents of root items
        which can cause errors and inconsistent selection state.
        """
        selected_set = self.selected_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.selected_right
        tree = self.left_tree if side.lower() == C.LEFT_SIDE_LOWERCASE else self.right_tree
        root_item = self.root_item_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.root_item_right
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Unticking parents for item {item_id}, root_item: {root_item}")
        
        parent = tree.parent(item_id)
        while parent:
            selected_set.discard(parent)
            if __debug__:
                log_and_flush(logging.DEBUG, f"Unticked parent: {parent}")
            
            # Safety check - if we've reached the root item, stop here
            # Don't try to untick the parent of the root item as it doesn't exist
            if parent == root_item:
                if __debug__:
                    log_and_flush(logging.DEBUG, f"Reached root item {root_item}, stopping parent unticking")
                break
                
            next_parent = tree.parent(parent)
            if not next_parent:  # Additional safety check for empty parent
                if __debug__:
                    log_and_flush(logging.DEBUG, f"No parent found for {parent}, stopping parent unticking")
                break
            parent = next_parent
            
    def update_tree_display_safe(self):
        """
        Safe tree display update that preserves selection state and respects limits.
        
        Purpose:
        --------
        Prevents recursive updates during expand/collapse operations
        and ensures consistent behavior when file limits are exceeded.
        """
        if self._updating_display or self.limit_exceeded:
            if __debug__:
                log_and_flush(logging.DEBUG, "Skipping tree display update - already updating or limits exceeded")
            return
            
        self._updating_display = True
        try:
            self.update_tree_display()
        finally:
            self._updating_display = False
            
    def update_tree_display(self):
        """Update tree display to show selection state (only for non-missing items)."""
        # Update left tree
        for item in self.left_tree.get_children():
            self.update_item_display(self.left_tree, item, 'left')
            
        # Update right tree  
        for item in self.right_tree.get_children():
            self.update_item_display(self.right_tree, item, C.RIGHT_SIDE_LOWERCASE)
            
    def update_item_display(self, tree, item, side, recursive=True):
        """
        Update display of a single item and optionally its children.
        
        Purpose:
        --------
        Only updates checkbox display for non-missing items
        to maintain consistent visual representation of selectable items.
        """
        selected_set = self.selected_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.selected_right
        
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
        """Browse for left folder with limit awareness."""
        log_and_flush(logging.DEBUG, "Opening left folder browser")
        folder = filedialog.askdirectory(title="Select Left Folder")
        if folder:
            self.left_folder.set(folder)
            self.add_status_message(f"Selected left folder: {folder}")
            log_and_flush(logging.INFO, f"Selected left folder: {folder}")
            
    def browse_right_folder(self):
        """Browse for right folder with limit awareness."""
        log_and_flush(logging.DEBUG, "Opening right folder browser")
        folder = filedialog.askdirectory(title="Select Right Folder")
        if folder:
            self.right_folder.set(folder)
            self.add_status_message(f"Selected right folder: {folder}")
            log_and_flush(logging.INFO, f"Selected right folder: {folder}")
            
    def start_comparison(self): # v000.0002 changed - removed sorting state reset
        """Start folder comparison in background thread with limit checking and complete reset."""
        log_and_flush(logging.INFO, "Starting folder comparison with complete reset")
        
        if not self.left_folder.get() or not self.right_folder.get():
            error_msg = "Both folders must be selected before comparison"
            log_and_flush(logging.ERROR, f"Comparison failed: {error_msg}")
            self.add_status_message(f"Error: {error_msg}")
            self.show_error("Please select both folders to compare")
            return
            
        if not Path(self.left_folder.get()).exists():
            error_msg = f"Left folder does not exist: {self.left_folder.get()}"
            log_and_flush(logging.ERROR, error_msg)
            self.add_status_message(f"Error: {error_msg}")
            self.show_error(error_msg)
            return
            
        if not Path(self.right_folder.get()).exists():
            error_msg = f"Right folder does not exist: {self.right_folder.get()}"
            log_and_flush(logging.ERROR, error_msg)
            self.add_status_message(f"Error: {error_msg}")
            self.show_error(error_msg)
            return
        
        # Reset application state for fresh comparison # v000.0002 changed - removed sorting
        self.limit_exceeded = False
                                                             
                                                             
        
        # Log the reset
        self.add_status_message("RESET: Clearing all data structures for fresh comparison") # v000.0002 changed - removed sorting
        log_and_flush(logging.INFO, "Complete application reset initiated - clearing all data") # v000.0002 changed - removed sorting
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Left folder: {self.left_folder.get()}")
            log_and_flush(logging.DEBUG, f"Right folder: {self.right_folder.get()}")
            log_and_flush(logging.DEBUG, f"Compare criteria: existence={self.compare_existence.get()}, "
                        f"size={self.compare_size.get()}, "
                        f"date_created={self.compare_date_created.get()}, "
                        f"date_modified={self.compare_date_modified.get()}, "
                        f"sha512={self.compare_sha512.get()}")
                                                                        
            
        # Start comparison in background thread
        self.status_var.set("Comparing folders...")
        self.add_status_message("Starting fresh folder comparison...") # v000.0002 changed - removed sorting
        log_and_flush(logging.INFO, "Starting background comparison thread with reset state")
        threading.Thread(target=self.perform_comparison, daemon=True).start()

    def perform_comparison(self):
        """
        Perform the actual folder comparison with progress tracking and limit checking.
        
        Purpose:
        --------
        Orchestrates the complete comparison process including scanning, comparison,
        and UI updates while enforcing file count limits for performance management.
        """
        log_and_flush(logging.DEBUG, f"Entered FolderCompareSync_class: perform_comparison")

        # v001.0021 added [check if UI is being recreated to prevent threading issues]
        if hasattr(self, '_ui_recreating') and self._ui_recreating:
            log_and_flush(logging.WARNING, "Comparison aborted - UI is being recreated")
            return
            
        start_time = time.time()
        log_and_flush(logging.INFO, "Beginning folder comparison operation")
        
        # Create progress dialog for the overall comparison process
        progress = ProgressDialog_class(
            self.root, 
            "Comparing Folders", 
            "Preparing comparison...",
            max_value=100  # We'll estimate progress as percentage
        )
        
        try:
            # Clear previous results and reset state
            self.comparison_results.clear()
            self.filtered_results.clear()
            self.is_filtered = False
            self.selected_left.clear()
            self.selected_right.clear()
            self.path_to_item_left.clear()
            self.path_to_item_right.clear()
            self.root_item_left = None
            self.root_item_right = None
            self.file_count_left = 0
            self.file_count_right = 0
            self.total_file_count = 0
            
            if __debug__:
                log_and_flush(logging.DEBUG, "Cleared previous comparison results and reset root items")
            
            # Step 1: Build file lists for both folders (40% of total work) with early limit checking
            progress.update_progress(5, "Scanning left folder...")
            self.root.after(0, lambda: self.add_status_message("Scanning left folder for files and folders..."))
            
            left_files = self.build_file_list_with_progress(self.left_folder.get(), progress, 5, 25)
            
            if left_files is None:  # Limit exceeded during left scan
                return
            
            file_count_left = len(left_files)
            self.file_count_left = file_count_left
            
            self.root.after(0, lambda: self.add_status_message(f"Left folder scan complete: {file_count_left:,} items found"))
            log_and_flush(logging.INFO, f"Found {file_count_left} items in left folder")
            
            progress.update_progress(30, "Scanning right folder...")
            self.root.after(0, lambda: self.add_status_message("Scanning right folder for files and folders..."))
            
            right_files = self.build_file_list_with_progress(self.right_folder.get(), progress, 30, 50)
            
            if right_files is None:  # Limit exceeded during right scan
                return
                
            file_count_right = len(right_files)
            self.file_count_right = file_count_right
            
            # Check combined file count limit
            self.total_file_count = file_count_left + file_count_right
            if self.check_file_limit_exceeded(self.total_file_count, "combined folders"):
                return
            
            self.root.after(0, lambda: self.add_status_message(f"Right folder scan complete: {file_count_right:,} items found"))
            log_and_flush(logging.INFO, f"Found {file_count_right} items in right folder")
            
            # Step 2: Compare files (50% of total work)
            progress.update_progress(50, "Comparing files and folders...")
            self.root.after(0, lambda: self.add_status_message("Comparing files and folders for differences..."))
            
            # Get all unique relative paths
            all_paths = set(left_files.keys()) | set(right_files.keys())
            total_paths = len(all_paths)
            log_and_flush(logging.INFO, f"Comparing {total_paths} unique paths")
            
            if __debug__:
                log_and_flush(logging.DEBUG, f"Left-only paths: {len(left_files.keys() - right_files.keys())}")
                log_and_flush(logging.DEBUG, f"Right-only paths: {len(right_files.keys() - left_files.keys())}")
                log_and_flush(logging.DEBUG, f"Common paths: {len(left_files.keys() & right_files.keys())}")
            
            # Compare each path with progress updates using configurable frequency
            differences_found = 0
            for i, rel_path in enumerate(all_paths):
                # Update progress using configurable frequency settings
                if i % max(1, total_paths // C.PROGRESS_PERCENTAGE_FREQUENCY) == 0 or i % C.COMPARISON_PROGRESS_BATCH == 0:
                    comparison_progress = 50 + int((i / total_paths) * 40)  # 40% of work for comparison
                    progress.update_progress(comparison_progress, f"Comparing... {i+1:,} of {total_paths:,}")
                
                left_item = left_files.get(rel_path)
                right_item = right_files.get(rel_path)
                
                differences = self.compare_items(left_item, right_item)
                
                self.comparison_results[rel_path] = FolderCompareSync_class.ComparisonResult_class(
                    left_item=left_item,
                    right_item=right_item,
                    differences=differences
                )
                
                if differences:
                    differences_found += 1
                    if __debug__:
                        log_and_flush(logging.DEBUG, f"Difference found in '{rel_path}': {differences}")
            
            # Step 3: Update UI (10% of total work)
            progress.update_progress(90, "Building comparison trees...")
            self.root.after(0, lambda: self.add_status_message("Building comparison tree views..."))
            
            elapsed_time = time.time() - start_time
            log_and_flush(logging.INFO, f"Comparison completed in {elapsed_time:.2f} seconds")
            log_and_flush(logging.INFO, f"Found {differences_found} items with differences")
            
            # Update UI in main thread
            progress.update_progress(100, "Finalizing...")
            self.root.after(0, self.update_comparison_ui)
            
            # Add completion status message with file counts
            self.root.after(0, lambda: self.add_status_message(
                f"Comparison complete: {differences_found:,} differences found in {elapsed_time:.1f} seconds"
            ))
            self.root.after(0, lambda: self.add_status_message(
                f"Total files processed: {self.total_file_count:,} (Left: {self.file_count_left:,}, Right: {self.file_count_right:,})"
            ))
            
        except Exception as e:
            log_and_flush(logging.ERROR, f"Comparison failed with exception: {type(e).__name__}: {str(e)}")
            if __debug__:
                log_and_flush(logging.DEBUG, "Full exception traceback:")
                log_and_flush(logging.DEBUG, traceback.format_exc())
            
            error_msg = f"Comparison failed: {str(e)}"
            self.root.after(0, lambda: self.add_status_message(f"Error: {error_msg}"))
            self.root.after(0, lambda: self.show_error(error_msg))
        finally:
            # Always close the progress dialog
            progress.close()
        log_and_flush(logging.DEBUG, f"Exiting FolderCompareSync_class: perform_comparison")
            
    def build_file_list_with_progress(self, root_path: str, progress: ProgressDialog_class, 
                                    start_percent: int, end_percent: int) -> Optional[dict[str, FolderCompareSync_class.FileMetadata_class]]:
        """
        Build a dictionary of relative_path -> FileMetadata with progress tracking and early limit checking.
        
        Purpose:
        --------
        Scans directory structure while monitoring file count limits to prevent
        performance issues with very large datasets, providing early abort capability.
        
        Args:
        -----
        root_path: Root directory to scan
        progress: Progress dialog to update
        start_percent: Starting percentage for this operation
        end_percent: Ending percentage for this operation
        
        Returns:
        --------
        dict[str, FolderCompareSync_class.FileMetadata_class] or None: File metadata dict or None if limit exceeded
        """
        if __debug__:
            log_and_flush(logging.DEBUG, f"Building file list with progress for: {root_path}")
        
        assert Path(root_path).exists(), f"Root path must exist: {root_path}"
        
        files = {}
        root = Path(root_path)
        file_count = 0
        dir_count = 0
        error_count = 0
        items_processed = 0
        
        try:
            # Use memory-efficient processing for large folders
            total_items = 0
            if len(list(root.iterdir())) < C.MEMORY_EFFICIENT_THRESHOLD:
                # For smaller folders, count total items first for better progress tracking
                total_items = sum(1 for _ in root.rglob('*'))
            else:
                # For larger folders, use estimated progress
                total_items = C.MEMORY_EFFICIENT_THRESHOLD  # Use threshold as estimate
                
            # Include the root directory itself if it's empty
            if not any(root.iterdir()):
                if __debug__:
                    log_and_flush(logging.DEBUG, f"Root directory is empty: {root_path}")
                
            for path in root.rglob('*'):
                try:
                    items_processed += 1
                    
                    # Early limit checking during scanning
                    if items_processed > C.MAX_FILES_FOLDERS:
                        folder_name = os.path.basename(root_path)
                        if self.check_file_limit_exceeded(items_processed, f"'{folder_name}' folder"):
                            return None  # Return None to indicate limit exceeded
                    
                    # Update progress using configurable intervals for optimal performance
                    if items_processed % max(1, min(C.SCAN_PROGRESS_UPDATE_INTERVAL, total_items // 20)) == 0:
                        current_percent = start_percent + int(((items_processed / total_items) * (end_percent - start_percent)))
                        progress.update_progress(current_percent, f"Scanning... {items_processed:,} items found")
                    
                    rel_path = path.relative_to(root).as_posix()
                    
                    # v000.0004 added - handle SHA512 computation with progress at scanning level for better separation.
					#                   Yes that's a trade-off for a clean FolderCompareSync_class.FileMetadata_class ... so be it.
                    #                   Even though all other metadata is calculated by "FolderCompareSync_class.FileMetadata_class.from_path"
					#                   we remove the sha512 computation to here so as to be able to display progress here
					#                   since the FolderCompareSync_class.FileMetadata_class must not interact with the UI.
					#                   Note that FolderCompareSync_class.FileMetadata_class.from_path can still compute the hash if compute_hash=False,
					#                   however that does not update the UI with progress.
					#                   Put compute_sha512_with_progress() underneath this def at the same level
					#                   
                    sha512_hash = None
                    if self.compare_sha512.get() and path.is_file():
                        try:
                            size = path.stat().st_size
                            if size > C.SHA512_STATUS_MESSAGE_THRESHOLD:
                                # Large files: Use separate SHA512 computation utility function for progress tracking # v000.0004 added
                                log_and_flush(logging.DEBUG, f"Large file: Performing SHA512 computation via compute_sha512_with_progress() for {path}")
                                sha512_hash = self.compute_sha512_with_progress(str(path), progress)
                            else:
                                # Small files: compute directly without progress overhead # v000.0004 added
                                log_and_flush(logging.DEBUG, f"Small file: Performing SHA512 computation locally in build_file_list_with_progress() for {path}")
                                if size < C.SHA512_MAX_FILE_SIZE:
                                    hasher = hashlib.sha512()
                                    with open(str(path), 'rb') as f:
                                        hasher.update(f.read())
                                    sha512_hash = hasher.hexdigest()
                        except Exception as e:
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"SHA512 computation failed for {path}: {e}")
                    
                    # v000.0004 NOTE: Create metadata without SHA512 computation (since SHA512 computation already handled above) # v000.0004 changed
                    metadata = FolderCompareSync_class.FileMetadata_class.from_path(str(path), compute_hash=False)
                    
                    # v000.0004 added - manually (re)set SHA512 if we computed it at scanning level
                    if sha512_hash:
                        metadata.sha512 = sha512_hash
                    
                    files[rel_path] = metadata
                    
                    if path.is_file():
                        file_count += 1
                    else:
                        dir_count += 1
                        
                except Exception as e:
                    error_count += 1
                    if __debug__:
                        log_and_flush(logging.DEBUG, f"Skipping file due to error: {path} - {e}")
                    continue  # Skip files we can't process
                    
            # Also scan for empty directories that might not be caught by rglob('*')
            for path in root.rglob(''):  # This gets all directories
                try:
                    if path.is_dir() and path != root:
                        rel_path = path.relative_to(root).as_posix()
                        if rel_path not in files:  # Only add if not already added
                            metadata = FolderCompareSync_class.FileMetadata_class.from_path(str(path), compute_hash=False)  # Directories don't need SHA512
                            files[rel_path] = metadata
                            dir_count += 1
                            
                            # Check limit for directories too
                            if len(files) > C.MAX_FILES_FOLDERS:
                                folder_name = os.path.basename(root_path)
                                if self.check_file_limit_exceeded(len(files), f"'{folder_name}' folder"):
                                    return None
                                    
                except Exception as e:
                    error_count += 1
                    if __debug__:
                        log_and_flush(logging.DEBUG, f"Skipping directory due to error: {path} - {e}")
                    continue
                    
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error scanning directory {root_path}: {e}")
            if __debug__:
                log_and_flush(logging.DEBUG, traceback.format_exc())
            
        log_and_flush(logging.INFO, f"Scanned {root_path}: {file_count} files, {dir_count} directories, {error_count} errors")
        if __debug__:
            log_and_flush(logging.DEBUG, f"Total items found: {len(files)}")
            
        return files

    def compute_sha512_with_progress(self, file_path: str, progress_dialog: ProgressDialog_class) -> Optional[str]: # v000.0004 added - separated SHA512 computation with progress tracking
        """
        Compute SHA512 hash for a file with progress tracking in the UI every ~50MB.
        
        Purpose:
        --------
        Provides SHA512 computation with user progress feedback for large files,
        maintaining separation of UI updating concerns from the metadata creation only in class FolderCompareSync_class.FileMetadata_class.
        
        Args:
        -----
        file_path: Path to the file to hash
        progress_dialog: Progress dialog for user feedback
        
        Returns:
        --------
        str: SHA512 hash as hexadecimal string, or None if computation failed
        
        Usage:
        ------
        hash_value = compute_sha512_with_progress("/path/to/large_file.dat", progress)
        """
        try:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                log_and_flush(logging.DEBUG, f"In compute_sha512_with_progress() ... returning None ... not path.exists() or not path.is_file() for {file_path}")
                return None
                
            size = path.stat().st_size
            if size >= C.SHA512_MAX_FILE_SIZE:  # v000.0004 respect configurable limit
                if __debug__:
                    log_and_flush(logging.DEBUG, f"In compute_sha512_with_progress() File too large for SHA512 computation: {size} bytes > {C.SHA512_MAX_FILE_SIZE} bytes")
                return None
            
            hasher = hashlib.sha512()
            
            # v000.0004 progress tracking variables
            bytes_processed = 0
            chunk_count = 0
            
            # v000.0004 Show initial progress message for large files
            if size > C.SHA512_STATUS_MESSAGE_THRESHOLD:
                size_mb = size / (1024 * 1024)
                progress_dialog.update_message(f"Computing SHA512 for {path.name} ({size_mb} MB)...\n(computed 0 MB of {size_mb} MB)")
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):  # v000.0004 8MB chunks
                    hasher.update(chunk)
                    bytes_processed += len(chunk) # v000.0004
                    chunk_count += 1 # v000.0004
                    
                    # v000.0004 update progress every ~6 chunks (48MB) for large files
                    if size > C.SHA512_STATUS_MESSAGE_THRESHOLD:
                        if chunk_count % 6 == 0 or bytes_processed >= size:  # Update every ~50MB
                            processed_mb = bytes_processed / (1024 * 1024)
                            total_mb = size / (1024 * 1024)
                            progress_dialog.update_message(f"Computing SHA512 for {path.name} ({total_mb:.1f} MB)...\n(computed {processed_mb} MB of {total_mb} MB)")
            
            return hasher.hexdigest() # v000.0004
            
        except Exception as e:
            if __debug__:
                log_and_flush(logging.DEBUG, f"In compute_sha512_with_progress() SHA512 computation failed for {file_path}: {e}")
            return None  # v000.0004 hash computation failed
        
    def compare_items(self, left_item: Optional[FolderCompareSync_class.FileMetadata_class], 
                     right_item: Optional[FolderCompareSync_class.FileMetadata_class]) -> set[str]:
        """
        Compare two items and return set of differences with configurable timestamp difference tolerance.
        
        Purpose:
        --------
        Performs detailed comparison of file/folder metadata based on
        selected comparison criteria to identify synchronization needs.
        v002.0002 Uses configurable tolerance ("TIMESTAMP_TOLERANCE") for timestamp comparisons to
                  handle file system precision differences and operational variations when copying.

        Args:
        -----
        left_item: Metadata for left side item (or None if missing)
        right_item: Metadata for right side item (or None if missing)
        
        Returns:
        --------
        set[str]: Set of difference types found
        """
        differences = set()
        
        # Check existence
        if self.compare_existence.get():
            if (left_item is None) != (right_item is None):
                differences.add('existence')
            elif left_item and right_item and (not left_item.exists or not right_item.exists):
                differences.add('existence')
                
        # If both items exist, compare other attributes
        if left_item and right_item and left_item.exists and right_item.exists:
            # size comparison
            if self.compare_size.get() and left_item.size != right_item.size:
                differences.add('size')
                
            # v002.0002 enhanced date_created timestamp comparison with configurable tolerance
            if self.compare_date_created.get(): # if the optional date_created tickbox is ticked
                if self._timestamps_differ(left_item.date_created, right_item.date_created, C.TIMESTAMP_TOLERANCE, 'date_created'):
                    differences.add('date_created')
                    
            # v002.0002 enhanced date_modified timestamp comparison with configurable tolerance
            if self.compare_date_modified.get(): # if the optional date_modified tickbox is ticked
                if self._timestamps_differ(left_item.date_modified, right_item.date_modified, C.TIMESTAMP_TOLERANCE, 'date_modified'):
                    differences.add('date_modified')

            # content sha512 comparison
            if (self.compare_sha512.get() and left_item.sha512 and right_item.sha512 
                and left_item.sha512 != right_item.sha512):
                differences.add('sha512')
                
        return differences
    
    def _timestamps_differ(self, left_timestamp: Optional[datetime], right_timestamp: Optional[datetime], 
                          acceptable_timestamp_tolerance: float, timestamp_type: str) -> bool:
        """
        Compare two timestamps with configurable tolerance ("acceptable_timestamp_tolerance").
        
        Purpose:
        --------
        Provides tolerance-based timestamp comparison to handle file system
        precision differences and operational timing variations gracefully.
        
        Args:
        -----
        left_timestamp: Left side timestamp
        right_timestamp: Right side timestamp  
        acceptable_timestamp_tolerance: Maximum acceptable difference in seconds (eg 0.01 for 1/100 of a second)
        timestamp_type: Type of timestamp for logging ('date_created' or 'date_modified')
        
        Returns:
        --------
        bool: True if timestamps differ beyond tolerance, False if within tolerance
        """
        # Handle None cases
        if left_timestamp is None and right_timestamp is None:
            return False
        if left_timestamp is None or right_timestamp is None:
            return True
            
        # Check if tolerance is disabled (revert to exact equality)
        if acceptable_timestamp_tolerance <= 0:
            are_different = left_timestamp != right_timestamp
            if __debug__ and are_different:
                left_display = self.format_timestamp(left_timestamp, include_timezone=False) or "None"
                right_display = self.format_timestamp(right_timestamp, include_timezone=False) or "None"
                left_timestamp_seconds = left_timestamp.timestamp()
                right_timestamp_seconds = right_timestamp.timestamp()
                diff_seconds = abs(left_timestamp_seconds - right_timestamp_seconds)
                diff_microseconds = diff_seconds * 1_000_000
                log_and_flush(logging.DEBUG, f"TIMESTAMP DIFFERENCE (EXACT): {timestamp_type.upper()} Left : {left_display}  Right: {right_display}  ... Difference : {diff_microseconds:.1f} microseconds")
            return are_different
        
        # Calculate absolute difference
        try:
            left_timestamp_seconds = left_timestamp.timestamp()
            right_timestamp_seconds = right_timestamp.timestamp()
            diff_seconds = abs(left_timestamp_seconds - right_timestamp_seconds)
            diff_microseconds = diff_seconds * 1_000_000
            
            # Check if difference exceeds tolerance
            differs = diff_seconds > acceptable_timestamp_tolerance
            
            # Enhanced debug logging with tolerance information
            if __debug__:
                left_display = self.format_timestamp(left_timestamp, include_timezone=False) or "None"
                right_display = self.format_timestamp(right_timestamp, include_timezone=False) or "None"
                
                if differs:
                    log_and_flush(logging.DEBUG, f"TIMESTAMP DIFFERENCE (EXCEEDS TOLERANCE): {timestamp_type.upper()} Left : {left_display}  Right: {right_display}  ... Difference : {diff_seconds:.6f} EXCEEDS TOLERANCE {acceptable_timestamp_tolerance:.6f}")
                elif diff_seconds > 0:
                    log_and_flush(logging.DEBUG, f"TIMESTAMP DIFFERENCE (WITHIN TOLERANCE): {timestamp_type.upper()} Left : {left_display}  Right: {right_display}  ... Difference : {diff_seconds:.6f} WITHIN TOLERANCE {acceptable_timestamp_tolerance:.6f}")

            # Yield the result, whether it exceeds the trolderance or not
            return differs
            
        except (ValueError, OSError, OverflowError) as e:
            # Handle timestamp conversion errors gracefully
            log_and_flush(logging.DEBUG, f"Timestamp comparison error for {timestamp_type}: {e}")
            # Fall back to direct comparison
            return left_timestamp != right_timestamp
        
    def update_comparison_ui(self): # v000.0002 changed - removed sorting parameters 
        """Update UI with comparison results and limit checking (no sorting)."""
        if self.limit_exceeded:
            log_and_flush(logging.WARNING, "Skipping UI update due to file limit exceeded")
            return
            
        log_and_flush(logging.INFO, "Updating UI with comparison results")
        
        # Clear existing tree content
        left_items = len(self.left_tree.get_children())
        right_items = len(self.right_tree.get_children())
        
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Cleared {left_items} left tree items and {right_items} right tree items")
            
        # Build tree structure with root handling # v000.0002 changed - removed sorting
        self.build_trees_with_root_paths() # v000.0002 changed - (no sorting)
                                                 
                                              
         
        
        # Update status
        self.status_var.set("Ready")
        self.update_summary()
        log_and_flush(logging.INFO, "UI update completed")

    def update_comparison_ui_filtered(self): # v000.0002 changed - removed sorting parameters
        """Update UI with filtered comparison results and limit checking (no sorting)."""
        if self.limit_exceeded:
            log_and_flush(logging.WARNING, "Skipping filtered UI update due to file limit exceeded")
            return
            
        log_and_flush(logging.INFO, "Updating UI with filtered comparison results")
        
        # Clear existing tree content
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)
            
        # Build tree structure with filtered results # v000.0002 changed - removed sorting
        self.build_trees_with_filtered_results() # v000.0002 changed - removed sorting
        
        # Update status
        self.status_var.set("Ready (Filtered)")
        self.update_summary()
        log_and_flush(logging.INFO, "Filtered UI update completed")

    def build_trees_with_filtered_results(self):
        """Build tree structures from filtered comparison results with limit checking (no sorting)."""
        if self.limit_exceeded:
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Building trees from {len(self.filtered_results)} filtered results")
        
        # Use filtered results instead of full results
        results_to_use = self.filtered_results
        
        # Create root items with fully qualified paths and functional checkboxes
        left_root_path = self.left_folder.get()
        right_root_path = self.right_folder.get()
        
        # Insert root items as top-level entries with checkboxes
        left_root_text = f"☐ {left_root_path}"
        right_root_text = f"☐ {right_root_path}"
        
        self.root_item_left = self.left_tree.insert('', tk.END, text=left_root_text, open=True,
                                                   values=("", "", "", "", "Root"))
        self.root_item_right = self.right_tree.insert('', tk.END, text=right_root_text, open=True,
                                                     values=("", "", "", "", "Root"))
        
        # Store root path mappings for selection system
        self.path_to_item_left[''] = self.root_item_left  # Empty path represents root
        self.path_to_item_right[''] = self.root_item_right
        
        # For filtered results, show a flattened view under each root # v000.0002 changed - removed sorting
        for rel_path, result in results_to_use.items(): # v000.0002 changed - removed sorting
            if not rel_path:
                continue
                
            # Add left item if it exists
            if result.left_item and result.left_item.exists:
                # v000.0006 ---------- START CODE BLOCK - facilitate folder timestamp and smart status display
                # v000.0006 added - Handle folder vs file display with timestamps
                if result.left_item.is_folder:
                    # This is a folder - show timestamps and smart status
                    date_created_str = self.format_timestamp(result.left_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = self.format_timestamp(result.left_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = ""  # Folders never have SHA512
                    
                    # Determine smart status for folders
                    if result.is_different and result.differences:
                        # Check if folder is different ONLY due to timestamps
                        timestamp_only_differences = {'date_created', 'date_modified'}
                        if result.differences.issubset(timestamp_only_differences):
                            status = "Folder (timestamp)"
                        else:
                            status = "Folder"
                    else:
                        status = "Folder"
                    item_text = f"☐ {rel_path}/"  # Add folder indicator
                else:
                    # v000.0006 ---------- END CODE BLOCK - facilitate folder timestamp and smart status display
                    # This is a file - show all metadata as before
                    date_created_str = self.format_timestamp(result.left_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = self.format_timestamp(result.left_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = result.left_item.sha512[:16] + "..." if result.left_item.sha512 else ""
                    status = "Different" if result.is_different else "Same"
                    item_text = f"☐ {rel_path}"
                
                # v000.0004 changed - Use folder-aware display values
                size_str = self.format_size(result.left_item.size) if result.left_item.size else ""
                item_id = self.left_tree.insert(self.root_item_left, tk.END, text=item_text,
                                              values=(size_str, date_created_str, date_modified_str, sha512_str, status))
                self.path_to_item_left[rel_path] = item_id
                
            # Add right item if it exists
            if result.right_item and result.right_item.exists:
                # v000.0006 added - Handle folder vs file display with timestamps
                if result.right_item.is_folder:
                    # This is a folder - show timestamps and smart status
                    date_created_str = self.format_timestamp(result.right_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = self.format_timestamp(result.right_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = ""  # Folders never have SHA512
                    
                    # Determine smart status for folders
                    if result.is_different and result.differences:
                        # Check if folder is different ONLY due to timestamps
                        timestamp_only_differences = {'date_created', 'date_modified'}
                        if result.differences.issubset(timestamp_only_differences):
                            status = "Folder (timestamp)"
                        else:
                            status = "Folder"
                    else:
                        status = "Folder"
                    item_text = f"☐ {rel_path}/"  # Add folder indicator
                else:
                    # This is a file - show all metadata as before
                    # v000.0006 ---------- END CODE BLOCK - facilitate folder timestamp and smart status display
                    date_created_str = self.format_timestamp(result.right_item.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = self.format_timestamp(result.right_item.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = result.right_item.sha512[:16] + "..." if result.right_item.sha512 else ""
                    status = "Different" if result.is_different else "Same"
                    item_text = f"☐ {rel_path}"
                
                # v000.0006 changed - Use folder-aware display values
                size_str = self.format_size(result.right_item.size) if result.right_item.size else ""
                item_id = self.right_tree.insert(self.root_item_right, tk.END, text=item_text,
                                               values=(size_str, date_created_str, date_modified_str, sha512_str, status))
                self.path_to_item_right[rel_path] = item_id

    def build_trees_with_root_paths(self): # v000.0003 changed - fixed false conflict detection bug
        """
        Build tree structures from comparison results with fully qualified root paths # v000.0002 changed - removed sorting
        
        Purpose:
        --------
        Creates stable tree structure that maintains row correspondence and folder hierarchy
        without any sorting functionality to comply with mandatory features.
        """
        if self.limit_exceeded:
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, f"Building trees with root paths from {len(self.comparison_results)} comparison results")
                                                                                    
        
        start_time = time.time()
        
        # Create root items with fully qualified paths and functional checkboxes
        left_root_path = self.left_folder.get()
        right_root_path = self.right_folder.get()
        
        # Insert root items as top-level entries with checkboxes
        left_root_text = f"☐ {left_root_path}"
        right_root_text = f"☐ {right_root_path}"
        
        self.root_item_left = self.left_tree.insert('', tk.END, text=left_root_text, open=True,
                                                   values=("", "", "", "", "Root"))
        self.root_item_right = self.right_tree.insert('', tk.END, text=right_root_text, open=True,
                                                     values=("", "", "", "", "Root"))
        
        # Store root path mappings for selection system
        self.path_to_item_left[''] = self.root_item_left  # Empty path represents root
        self.path_to_item_right[''] = self.root_item_right
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Created root items: left={self.root_item_left}, right={self.root_item_right}")
        
        # Create sentinel class for missing folders to distinguish from real empty folders
        class MissingFolder:
            def __init__(self):
                self.contents = {}
        
        # Organize paths into tree structure (same as before)
        left_structure = {}
        right_structure = {}
        
        # First pass: Build structure for existing items
        for rel_path, result in self.comparison_results.items():
            if not rel_path:  # Skip empty paths
                if __debug__:
                    log_and_flush(logging.DEBUG, "Skipping empty relative path")
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
                            current[part] = {}
                        elif isinstance(current[part], MissingFolder):
                            current[part] = current[part].contents
                        current = current[part] if isinstance(current[part], dict) else current[part].contents
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    
                    # v000.0003 changed - fixed folder vs file handling to prevent false conflicts
                    if result.left_item.is_folder:
                        # This is a folder - ensure it exists as a dict structure
                        if final_name not in current:
                            current[final_name] = {}  # v000.0003 added - create folder dict structure
                        elif not isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: folder trying to replace a file (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add folder '{final_name}' - file exists with same name")
                        # v000.0003 changed - for folders, don't store metadata directly, just ensure dict exists
                    else:
                        # This is a file
                        if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: file trying to replace a folder (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add file '{final_name}' - folder exists with same name")
                        else:
                            current[final_name] = result.left_item  # v000.0003 changed - only store file metadata for files
            
            # Build right structure  
            if result.right_item is not None:
                current = right_structure
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = {}
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = {}
                        elif isinstance(current[part], MissingFolder):
                            current[part] = current[part].contents
                        current = current[part] if isinstance(current[part], dict) else current[part].contents
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    
                    # v000.0003 changed - fixed folder vs file handling to prevent false conflicts
                    if result.right_item.is_folder:
                        # This is a folder - ensure it exists as a dict structure
                        if final_name not in current:
                            current[final_name] = {}  # v000.0003 added - create folder dict structure
                        elif not isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: folder trying to replace a file (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add folder '{final_name}' - file exists with same name")
                        # v000.0003 changed - for folders, don't store metadata directly, just ensure dict exists
                    else:
                        # This is a file
                        if final_name in current and isinstance(current[final_name], (dict, MissingFolder)):
                            # Real conflict: file trying to replace a folder (should be very rare)
                            if __debug__:
                                log_and_flush(logging.DEBUG, f"REAL CONFLICT: Cannot add file '{final_name}' - folder exists with same name")
                        else:
                            current[final_name] = result.right_item  # v000.0003 changed - only store file metadata for files
                            
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
                
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = MissingFolder()
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = MissingFolder()
                        current = current[part].contents if isinstance(current[part], MissingFolder) else current[part]
                        
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    if result.right_item and result.right_item.is_folder:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = MissingFolder()
                    else:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = None
                    
            # Add missing right items
            if result.right_item is None and result.left_item is not None:
                missing_right += 1
                current = right_structure
                
                for part in path_parts[:-1]:
                    if part:
                        if part not in current:
                            current[part] = MissingFolder()
                        elif not isinstance(current[part], (dict, MissingFolder)):
                            current[part] = MissingFolder()
                        current = current[part].contents if isinstance(current[part], MissingFolder) else current[part]
                        
                if path_parts[-1]:
                    final_name = path_parts[-1]
                    if result.left_item and result.left_item.is_folder:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = MissingFolder()
                    else:
                        if final_name not in current or not isinstance(current[final_name], (dict, MissingFolder)):
                            current[final_name] = None
        
        if __debug__:
            log_and_flush(logging.DEBUG, f"Added {missing_left} missing left placeholders, {missing_right} missing right placeholders")
            
        # Populate trees under root items with stable alphabetical ordering # v000.0002 changed - removed sorting
        log_and_flush(logging.INFO, "Populating tree views under root paths with stable ordering...") # v000.0002 changed - removed sorting
        self.populate_tree(self.left_tree, left_structure, self.root_item_left, C.LEFT_SIDE_LOWERCASE, '') # v000.0002 changed - removed sorting
                                                                         
        self.populate_tree(self.right_tree, right_structure, self.root_item_right, C.RIGHT_SIDE_LOWERCASE, '') # v000.0002 changed - removed sorting
                                                                         
        
        elapsed_time = time.time() - start_time
        if __debug__:
            log_and_flush(logging.DEBUG, f"Tree building with root paths completed in {elapsed_time:.3f} seconds")
            
    def populate_tree(self, tree, structure, parent_id, side, current_path):
        """
        Recursively populate tree with structure using stable alphabetical ordering.
        
        Purpose:
        --------
        Creates stable tree structure that maintains consistent ordering without
        any custom sorting to comply with mandatory features. Uses simple alphabetical
        ordering for predictable results.
        """
        if self.limit_exceeded:
            return
        
        # Use simple alphabetical sorting for stable, predictable ordering  # v000.0002 changed - removed sorting
        sorted_items = sorted(structure.items()) # v000.0002 changed - removed sorting
        
        # Import the MissingFolder class (defined in build_trees_with_root_paths)
        for name, content in sorted_items:
            # Build the full relative path for this item
            item_rel_path = current_path + ('/' if current_path else '') + name
            
            # Check if content is a MissingFolder (defined in the calling method)
            is_missing_folder = hasattr(content, 'contents')
            
            if isinstance(content, dict) or is_missing_folder:
                # This is a folder (either real or missing)
                if is_missing_folder:
                    # Missing folder - NO checkbox, just plain text with [MISSING]
                    item_text = f"{name}/ [MISSING]"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, open=False,
                                        values=("", "", "", "", "Missing"), tags=('missing',))
                    # Recursively populate children from the missing folder's contents
                    self.populate_tree(tree, content.contents, item_id, side, item_rel_path) # v000.0002 changed - removed sorting
                else:
                    # Real folder - has checkbox
                    item_text = f"☐ {name}/"
                    
                    # v000.0006 ---------- START CODE BLOCK - facilitate folder timestamp and smart status display
                    # v000.0006 added - Get folder metadata for timestamp display and smart status
                    result = self.comparison_results.get(item_rel_path)
                    folder_metadata = None
                    date_created_str = ""
                    date_modified_str = ""
                    status = "Folder"
                    
                    if result:
                        # Get the folder metadata from the appropriate side
                        if side.lower() == C.LEFT_SIDE_LOWERCASE and result.left_item:
                            folder_metadata = result.left_item
                        elif side.lower() == C.RIGHT_SIDE_LOWERCASE and result.right_item:
                            folder_metadata = result.right_item
                        
                        # v000.0006 added - Format folder timestamps if available
                        if folder_metadata and folder_metadata.is_folder:
                            date_created_str = self.format_timestamp(folder_metadata.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                            date_modified_str = self.format_timestamp(folder_metadata.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                        
                        # v000.0006 added - Determine smart status for folders
                        if result.is_different and result.differences:
                            # Check if folder is different ONLY due to timestamps
                            timestamp_only_differences = {'date_created', 'date_modified'}
                            if result.differences.issubset(timestamp_only_differences):
                                status = "Folder (timestamp)"
                            elif result.differences:
                                # Other differences exist (existence, contents, etc.)
                                status = "Folder"
                    # v000.0006 ---------- END CODE BLOCK - facilitate folder timestamp and smart status display                 
                    # v000.0006 changed - Insert folder with timestamp data and smart status
                    item_id = tree.insert(parent_id, tk.END, text=item_text, open=False,
                                        values=("", date_created_str, date_modified_str, "", status))
                    # Recursively populate children
                    self.populate_tree(tree, content, item_id, side, item_rel_path) # v000.0002 changed - removed sorting
                                                                                    
                
                # Store path mapping for both real and missing folders
                path_map = self.path_to_item_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.path_to_item_right
                path_map[item_rel_path] = item_id
                
            else:
                # This is a file
                if content is None:
                    # Missing file - NO checkbox, just plain text with [MISSING]
                    item_text = f"{name} [MISSING]"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, 
                                        values=("", "", "", "", "Missing"), tags=('missing',))
                else:
                    # Existing file - has checkbox and shows ALL metadata
                    size_str = self.format_size(content.size) if content.size else ""
                    date_created_str = self.format_timestamp(content.date_created, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    date_modified_str = self.format_timestamp(content.date_modified, include_timezone=False) # v001.0011 changed [use centralized format_timestamp method]
                    sha512_str = content.sha512[:16] + "..." if content.sha512 else ""
                    
                    # Determine status using proper path lookup
                    result = self.comparison_results.get(item_rel_path)
                    status = "Different" if result and result.is_different else "Same"
                    
                    item_text = f"☐ {name}"
                    item_id = tree.insert(parent_id, tk.END, text=item_text,
                                        values=(size_str, date_created_str, date_modified_str, sha512_str, status))
                
                # Store path mapping for both missing and existing files
                path_map = self.path_to_item_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.path_to_item_right
                path_map[item_rel_path] = item_id
                                        
        # Configure missing item styling using configurable color
        tree.tag_configure('missing', foreground=C.MISSING_ITEM_COLOR)

    def get_item_path(self, tree, item_id):
        """
        Get the full relative path for a tree item.
        
        Purpose:
        --------
        Reconstructs the relative path for a tree item by traversing
        the tree hierarchy up to the root item.
        
        Args:
        -----
        tree: Tree widget containing the item
        item_id: ID of the tree item
        
        Returns:
        --------
        str: Relative path of the item
        """
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
        
    def find_tree_item_by_path(self, rel_path, side):
        """
        Find tree item ID by relative path using efficient path mapping.
        
        Purpose:
        --------
        Provides fast lookup of tree items by their relative paths
        using pre-built mapping dictionaries for optimal performance.
        
        Args:
        -----
        rel_path: Relative path to search for
        side: Which tree side (LEFT_SIDE_LOWERCASE or RIGHT_SIDE_LOWERCASE)
        
        Returns:
        --------
        str: Tree item ID or None if not found
        """
        path_map = self.path_to_item_left if side.lower() == C.LEFT_SIDE_LOWERCASE else self.path_to_item_right
        return path_map.get(rel_path)
        
    def select_all_differences_left(self):
        """
        Select all different items in left pane with auto-clear first and limit checking.
        
        Purpose:
        --------
        Automatically clears all selections before selecting for clean workflow.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Selection operations are disabled when file limits are exceeded.")
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, "Auto-clearing all selections before selecting differences in left pane")
            
        # First clear all selections for clean state
        self.clear_all_left()
        
        # Use appropriate results set (filtered or full)
        results_to_use = self.filtered_results if self.is_filtered else self.comparison_results
        
        count = 0
        for rel_path, result in results_to_use.items():
            if result.is_different and result.left_item and result.left_item.exists:
                item_id = self.find_tree_item_by_path(rel_path, 'left')
                if item_id:
                    self.selected_left.add(item_id)
                    count += 1
                    
        if __debug__:
            log_and_flush(logging.DEBUG, f"Selected {count} different items in left pane (after auto-clear)")
            
        filter_text = " (filtered)" if self.is_filtered else ""
        self.add_status_message(f"Selected all differences in left pane{filter_text}: {count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def select_all_differences_right(self):
        """
        Select all different items in right pane with auto-clear first and limit checking.
        
        Purpose:
        --------
        Automatically clears all selections before selecting for clean workflow.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Selection operations are disabled when file limits are exceeded.")
            return
            
        if __debug__:
            log_and_flush(logging.DEBUG, "Auto-clearing all selections before selecting differences in right pane")
            
        # First clear all selections for clean state
        self.clear_all_right()
        
        # Use appropriate results set (filtered or full)
        results_to_use = self.filtered_results if self.is_filtered else self.comparison_results
        
        count = 0
        for rel_path, result in results_to_use.items():
            if result.is_different and result.right_item and result.right_item.exists:
                item_id = self.find_tree_item_by_path(rel_path, C.RIGHT_SIDE_LOWERCASE)
                if item_id:
                    self.selected_right.add(item_id)
                    count += 1
                    
        if __debug__:
            log_and_flush(logging.DEBUG, f"Selected {count} different items in right pane (after auto-clear)")
            
        filter_text = " (filtered)" if self.is_filtered else ""
        self.add_status_message(f"Selected all differences in right pane{filter_text}: {count:,} items")
        self.update_tree_display_safe() 
        self.update_summary()
        
    def clear_all_left(self):
        """
        Clear ALL selections in left pane (not just differences) with limit checking.
        
        Purpose:
        --------
        Provides complete reset functionality for workflow flexibility.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            # Allow clearing even when limits exceeded to help user reset
            pass
            
        cleared_count = len(self.selected_left)
        if __debug__:
            log_and_flush(logging.DEBUG, f"Clearing ALL {cleared_count} selections in left pane")
            
        self.selected_left.clear()
        if cleared_count > 0:
            self.add_status_message(f"Cleared all selections in left pane: {cleared_count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def clear_all_right(self):
        """
        Clear ALL selections in right pane (not just differences) with limit checking.
        
        Purpose:
        --------
        Provides complete reset functionality for workflow flexibility.
        Includes limit checking to prevent operations when file limits are exceeded.
        """
        if self.limit_exceeded:
            # Allow clearing even when limits exceeded to help user reset
            pass
            
        cleared_count = len(self.selected_right)
        if __debug__:
            log_and_flush(logging.DEBUG, f"Clearing ALL {cleared_count} selections in right pane")
            
        self.selected_right.clear()
        if cleared_count > 0:
            self.add_status_message(f"Cleared all selections in right pane: {cleared_count:,} items")
        self.update_tree_display_safe()
        self.update_summary()
        
    def copy_left_to_right(self):
        """Copy selected items from left to right with dry run support and limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Copy operations are disabled when file limits are exceeded.")
            return
            
        if not self.selected_left:
            self.add_status_message("No items selected for copying from left to right")
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # Get selected paths for copying
        selected_paths = []
        for item_id in self.selected_left:
            path = self.get_item_path(self.left_tree, item_id)
            if path:  # Only include non-empty paths
                selected_paths.append(path)
            
        if not selected_paths:
            self.add_status_message("No valid paths selected for copying")
            messagebox.showinfo("Info", "No valid paths selected for copying")
            return
        
        # Include dry run information in status message
        dry_run_text = " (DRY RUN)" if self.dry_run_mode.get() else ""
        self.add_status_message(f"Starting copy operation{dry_run_text}: {len(selected_paths):,} items from LEFT to RIGHT")
        
        # Show confirmation dialog with dry run information
        dry_run_notice = "\n\n*** DRY RUN MODE - No files will be modified ***" if self.dry_run_mode.get() else ""
        message = f"Copy {len(selected_paths)} items from LEFT to RIGHT?{dry_run_notice}\n\n"
        message += "\n".join(selected_paths[:C.COPY_PREVIEW_MAX_ITEMS])
        if len(selected_paths) > C.COPY_PREVIEW_MAX_ITEMS:
            message += f"\n... and {len(selected_paths) - C.COPY_PREVIEW_MAX_ITEMS} more items"
        
        if not messagebox.askyesno("Confirm Copy Operation", message):
            self.add_status_message("Copy operation cancelled by user")
            return
        
        # Start copy operation in background thread
        status_text = "Simulating copy..." if self.dry_run_mode.get() else "Copying files..."
        self.status_var.set(status_text)
        threading.Thread(target=self.perform_enhanced_copy_operation, args=('left_to_right'.lower(), selected_paths), daemon=True).start()
        
    def copy_right_to_left(self):
        """Copy selected items from right to left with dry run support and limit checking."""
        if self.limit_exceeded:
            messagebox.showwarning("Operation Disabled", "Copy operations are disabled when file limits are exceeded.")
            return
            
        if not self.selected_right:
            self.add_status_message("No items selected for copying from right to left")
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # Get selected paths for copying
        selected_paths = []
        for item_id in self.selected_right:
            path = self.get_item_path(self.right_tree, item_id)
            if path:  # Only include non-empty paths
                selected_paths.append(path)
            
        if not selected_paths:
            self.add_status_message("No valid paths selected for copying")
            messagebox.showinfo("Info", "No valid paths selected for copying")
            return
        
        # Include dry run information in status message
        dry_run_text = " (DRY RUN)" if self.dry_run_mode.get() else ""
        self.add_status_message(f"Starting copy operation{dry_run_text}: {len(selected_paths):,} items from RIGHT to LEFT")
        
        # Show confirmation dialog with dry run information
        dry_run_notice = "\n\n*** DRY RUN MODE - No files will be modified ***" if self.dry_run_mode.get() else ""
        message = f"Copy {len(selected_paths)} items from RIGHT to LEFT?{dry_run_notice}\n\n"
        message += "\n".join(selected_paths[:C.COPY_PREVIEW_MAX_ITEMS])
        if len(selected_paths) > C.COPY_PREVIEW_MAX_ITEMS:
            message += f"\n... and {len(selected_paths) - C.COPY_PREVIEW_MAX_ITEMS} more items"
        
        if not messagebox.askyesno("Confirm Copy Operation", message):
            self.add_status_message("Copy operation cancelled by user")
            return
        
        # Start copy operation in background thread
        status_text = "Simulating copy..." if self.dry_run_mode.get() else "Copying files..."
        self.status_var.set(status_text)
        threading.Thread(target=self.perform_enhanced_copy_operation, args=('right_to_left'.lower(), selected_paths), daemon=True).start()

    def perform_enhanced_copy_operation(self, direction, selected_paths): # changed for v000.0005
        """
        Perform file copy operations with comprehensive logging, dry run support, and tracking.
        
        Purpose:
        --------
        Orchestrates file copy operations using Strategy A/B with comprehensive logging,
        dry run simulation capability, sequential numbering, and automatic refresh after completion.
        
        Args:
        -----
        direction: Copy direction ('left_to_right'.lower() or 'right_to_left'.lower())
        selected_paths: List of relative paths to copy
        """
        start_time = time.time()
        is_dry_run = self.dry_run_mode.get()
        dry_run_text = " (DRY RUN)" if is_dry_run else ""
        
        log_and_flush(logging.INFO, f"Starting copy operation{dry_run_text}: {direction} with {len(selected_paths)} items")
        
        # Determine source and destination folders
        if direction.lower() == 'left_to_right'.lower():
            source_folder = self.left_folder.get()
            dest_folder = self.right_folder.get()
            direction_text = f"{C.LEFT_SIDE_UPPERCASE} to {C.RIGHT_SIDE_UPPERCASE}"
        else:
            source_folder = self.right_folder.get()
            dest_folder = self.left_folder.get()
            direction_text = f"{C.RIGHT_SIDE_UPPERCASE} to {C.LEFT_SIDE_UPPERCASE}"
        
        # Start copy operation session with dedicated logging and dry run support
        operation_name = f"Copy {len(selected_paths)} items from {direction_text}{dry_run_text}"
        operation_id = self.copy_manager.start_copy_operation(operation_name, dry_run=is_dry_run)
        
        # Create progress dialog for copy operation with dry run indication
        progress_title = f"{'Simulating' if is_dry_run else 'Copying'} Files"
        progress_message = f"{'Simulating' if is_dry_run else 'Copying'} files from {direction_text}..."
        progress = ProgressDialog_class(
            self.root,
            progress_title,
            progress_message,
            max_value=len(selected_paths)
        )
        
        copied_count = 0
        error_count = 0
        skipped_count = 0
        total_bytes_copied = 0
        critical_errors = []  # Track critical errors that require user attention
        
        # Track copy strategies used for summary
        direct_strategy_count = 0
        staged_strategy_count = 0
        
        try:
            for i, rel_path in enumerate(selected_paths):
                try:
                    # Update progress with dry run indication if required
                    source_path = str(Path(source_folder) / rel_path)
                    # Check if this file will use staged strategy for large file indication
                    base_progress_text = f"{'Simulating' if is_dry_run else 'Copying'} {i+1} of {len(selected_paths)}: {os.path.basename(rel_path)}"
                    if Path(source_path).exists() and Path(source_path).is_file():
                        file_size = Path(source_path).stat().st_size
                        strategy = FileCopyManager_class.determine_copy_strategy(source_path, str(Path(dest_folder) / rel_path), file_size)
                        if strategy == FileCopyManager_class.CopyStrategy.STAGED and file_size >= C.COPY_STRATEGY_THRESHOLD:
                            size_str = self.format_size(file_size)
                            progress_text = f"{base_progress_text}\n({size_str} file copy in progress ...not frozen, just busy)"
                        else:
                            progress_text = base_progress_text
                    else:
                        progress_text = base_progress_text
                    progress.update_progress(i+1, progress_text)
                                                       
                    dest_path = str(Path(dest_folder) / rel_path)
                    
                    # Skip if source doesn't exist
                    if not Path(source_path).exists():
                        skipped_count += 1
                        self.copy_manager._log_status(f"Source file not found, skipping: {source_path}")
                        continue
                    
                    # Handle directories separately (create them, don't copy as files) # v000.0005 changed - added folder timestamp copying
                    if Path(source_path).is_dir():
                        # Create destination directory if needed (or simulate in dry run)
                        if not Path(dest_path).exists():
                            if not is_dry_run:
                                Path(dest_path).mkdir(parents=True, exist_ok=True)
                                copied_count += 1
                                self.copy_manager._log_status(f"Created directory: {dest_path}")
                                
                                # v000.0005 added - Copy timestamps for newly created directories
                                try:                                                                                                     # v000.0005 added - Copy timestamps for newly created directories
                                    self.copy_manager.timestamp_manager.copy_timestamps(source_path, dest_path)                          # v000.0005 added - Copy timestamps for newly created directories
                                    self.copy_manager._log_status(f"Copied directory timestamps: {dest_path}")                           # v000.0005 added - Copy timestamps for newly created directories
                                except Exception as e:                                                                                   # v000.0005 added - Copy timestamps for newly created directories
                                    # Non-critical error - directory was created successfully                                            # v000.0005 added - Copy timestamps for newly created directories
                                    self.copy_manager._log_status(f"Warning: Could not copy directory timestamps for {dest_path}: {e}")  # v000.0005 added - Copy timestamps for newly created directories
                            else:
                                copied_count += 1
                                self.copy_manager._log_status(f"DRY RUN: Would create directory: {dest_path}")
                                self.copy_manager._log_status(f"DRY RUN: Would copy directory timestamps: {dest_path}")  # v000.0005 added
                        else:
                            # v000.0005 added - Directory already exists - still copy timestamps to sync metadata  
                            if not is_dry_run:                                                                                             # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                try:                                                                                                       # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    self.copy_manager.timestamp_manager.copy_timestamps(source_path, dest_path)                            # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    copied_count += 1  # Count as a successful operation                                                   # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    self.copy_manager._log_status(f"Updated directory timestamps: {dest_path}")                            # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                except Exception as e:                                                                                     # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    # Non-critical error - directory exists                                                                # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    self.copy_manager._log_status(f"Warning: Could not update directory timestamps for {dest_path}: {e}")  # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                    skipped_count += 1                                                                                     # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                            else:                                                                                                          # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                copied_count += 1                                                                                          # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                                self.copy_manager._log_status(f"DRY RUN: Would update directory timestamps: {dest_path}")                  # v000.0005 added - Directory already exists - still copy timestamps to sync metadata 
                        continue
                    
                    # Copy individual file using copy manager with dry run support
                    result = self.copy_manager.copy_file(source_path, dest_path, self.overwrite_mode.get())
                    
                    # Track strategy usage for summary
                    if result.strategy_used == FileCopyManager_class.CopyStrategy.DIRECT:
                        direct_strategy_count += 1
                    elif result.strategy_used == FileCopyManager_class.CopyStrategy.STAGED:
                        staged_strategy_count += 1
                    
                    if result.success:
                        copied_count += 1
                        total_bytes_copied += result.bytes_copied
                        success_msg = f"Successfully {'simulated' if is_dry_run else 'copied'}: {rel_path} ({result.strategy_used.value} strategy)"
                        self.copy_manager._log_status(success_msg)
                    else:
                        error_count += 1
                        error_msg = f"Failed to {'simulate' if is_dry_run else 'copy'} {rel_path}: {result.error_message}"
                        self.copy_manager._log_status(error_msg)
                        self.root.after(0, lambda msg=error_msg: self.add_status_message(f"ERROR: {msg}"))
                        
                        # Check for critical errors that require immediate user attention (only in non-dry-run)
                        if not is_dry_run and ("CRITICAL" in result.error_message or "Rename operation failed" in result.error_message):
                            critical_errors.append((rel_path, result.error_message))
                    
                    # Update progress every few items using configurable frequency
                    if i % max(1, len(selected_paths) // 20) == 0:
                        status_msg = f"Progress: {copied_count} {'simulated' if is_dry_run else 'copied'}, {error_count} errors, {skipped_count} skipped"
                        self.root.after(0, lambda msg=status_msg: self.add_status_message(msg))
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"Error processing {rel_path}: {str(e)}"
                    log_and_flush(logging.ERROR, error_msg)
                    self.copy_manager._log_status(error_msg)
                    self.root.after(0, lambda msg=error_msg: self.add_status_message(f"ERROR: {msg}"))
                    continue
            
            # Final progress update
            final_progress_text = f"{'Simulation' if is_dry_run else 'Copy'} operation complete"
            progress.update_progress(len(selected_paths), final_progress_text)
            
            elapsed_time = time.time() - start_time
            
            # End copy operation session
            self.copy_manager.end_copy_operation(copied_count, error_count, total_bytes_copied)
            
            # summary message with strategy breakdown
            summary = f"Copy operation{dry_run_text} complete ({direction_text}): "
            summary += f"{copied_count} {'simulated' if is_dry_run else 'copied'}, {error_count} errors, "
            summary += f"{skipped_count} skipped, {total_bytes_copied:,} bytes in {elapsed_time:.1f}s"
            log_and_flush(logging.INFO, summary)
            self.root.after(0, lambda: self.add_status_message(summary))
            
            # strategy summary
            if direct_strategy_count > 0 or staged_strategy_count > 0:
                strategy_summary = f"Strategy usage: {direct_strategy_count} direct, {staged_strategy_count} staged"
                self.root.after(0, lambda: self.add_status_message(strategy_summary))
            
            # Show completion dialog with information including dry run status
            completion_msg = f"Copy operation{dry_run_text} completed!\n\n"
            completion_msg += f"Successfully {'simulated' if is_dry_run else 'copied'}: {copied_count} items\n"
            completion_msg += f"Total bytes {'simulated' if is_dry_run else 'copied'}: {total_bytes_copied:,}\n"
            completion_msg += f"Errors: {error_count}\n"
            completion_msg += f"Skipped: {skipped_count}\n"
            completion_msg += f"Time: {elapsed_time:.1f} seconds\n"
            completion_msg += f"Operation ID: {operation_id}\n"
            
            # Include strategy breakdown
            if direct_strategy_count > 0 or staged_strategy_count > 0:
                completion_msg += f"\nStrategy Usage:\n"
                completion_msg += f"• Direct strategy: {direct_strategy_count} files\n"
                completion_msg += f"• Staged strategy: {staged_strategy_count} files\n"
            
            if is_dry_run:
                completion_msg += f"\n*** DRY RUN SIMULATION ***\n"
                completion_msg += f"No actual files were modified. This was a test run.\n"
                completion_msg += f"Check the detailed log for complete operation simulation.\n"
            else:
                if critical_errors:
                    # Build error details separately
                    error_details = f"CRITICAL ERRORS ENCOUNTERED ({len(critical_errors)}):\n\n"
                    for i, (path, error) in enumerate(critical_errors):
                        error_details += f"{i+1}. {path}:\n   {error}\n\n"
                    error_details += "\nRECOMMENDED ACTION: Check the detailed log file for troubleshooting.\n"
                    error_details += "These errors may indicate network issues or file locking problems."
                    
                    # Add summary to main message
                    completion_msg += f"\n⚠️ {len(critical_errors)} CRITICAL ERRORS - Click 'Show Details' to view\n\n"
                
                completion_msg += "The folder trees will now be refreshed and selections cleared."
            
            # Use error dialog if there were critical errors, otherwise info dialog
            if critical_errors and not is_dry_run:
                self.root.after(0, lambda: FolderCompareSync_class.ErrorDetailsDialog_class(
                    self.root, 
                    f"Copy Complete with Errors", 
                    completion_msg, 
                    error_details
                ))
            else:
                self.root.after(0, lambda: messagebox.showinfo(
                    f"{'Simulation' if is_dry_run else 'Copy'} Complete", 
                    completion_msg
                ))
            
            # IMPORTANT: Only refresh trees and clear selections for actual copy operations (not dry runs)
            if not is_dry_run:
                self.root.after(0, self.refresh_after_copy_or_delete_operation)
            else:
                self.root.after(0, lambda: self.add_status_message("DRY RUN complete - no file system changes made"))
            
        except Exception as e:
            log_and_flush(logging.ERROR, f"Copy operation{dry_run_text} failed: {e}")
            error_msg = f"Copy operation{dry_run_text} failed: {str(e)}"
            self.copy_manager._log_status(error_msg)
            self.root.after(0, lambda: self.add_status_message(f"ERROR: {error_msg}"))
            self.root.after(0, lambda: self.show_error(error_msg))
        finally:
            progress.close()
            self.root.after(0, lambda: self.status_var.set("Ready"))

    def refresh_after_copy_or_delete_operation(self):
        """
        Refresh folder trees and clear all selections after copy/delete operation with limit checking.
        
        Purpose:
        --------
        This ensures the user sees the current state after copying,
        but only performs refresh for actual copy or delete operations (not dry runs).
        """
        log_and_flush(logging.INFO, "Refreshing trees and clearing selections after copy or delete operation")
        self.add_status_message("Refreshing folder trees after copy or delete operation...")
        
        # Clear all selections first
        self.selected_left.clear()
        self.selected_right.clear()
        
        # Clear any active filter
        if self.is_filtered:
            self.clear_filter()
        
        # Reset limit state for refresh
        self.limit_exceeded = False
        
        # Restart comparison to refresh trees
        # This will re-scan both folders and rebuild the trees
        if self.left_folder.get() and self.right_folder.get():
            self.add_status_message("Re-scanning folders to show updated state...")
            threading.Thread(target=self.perform_comparison, daemon=True).start()
        else:
            self.add_status_message("Copy or Delete operation complete - ready for next operation")
        
    def update_summary(self):
        """Update summary information with filter status and limit checking."""
        # Use appropriate results set (filtered or full)
        results_to_use = self.filtered_results if self.is_filtered else self.comparison_results
        
        if self.limit_exceeded:
            self.summary_var.set("Summary: File limit exceeded - operations disabled")
            return
        
        if not results_to_use:
            if self.is_filtered:
                self.summary_var.set("Summary: No matching files in filter")
            else:
                self.summary_var.set("Summary: No comparison performed")
            return
            
        total_differences = sum(1 for r in results_to_use.values() if r.is_different)
        missing_left = sum(1 for r in results_to_use.values() 
                          if r.left_item is None or not r.left_item.exists)
        missing_right = sum(1 for r in results_to_use.values()
                           if r.right_item is None or not r.right_item.exists)
        selected_total = len(self.selected_left) + len(self.selected_right)
        
        filter_text = " (filtered)" if self.is_filtered else ""
        dry_run_text = " | DRY RUN MODE" if self.dry_run_mode.get() else ""
        summary = f"Summary{filter_text}: {total_differences} differences | {missing_left} missing left | {missing_right} missing right | {selected_total} marked{dry_run_text}"
        self.summary_var.set(summary)
        
    def show_error(self, message):
        """Show error message to user with context and details option."""
        log_and_flush(logging.ERROR, f"Displaying error to user: {message}")
        
        # Split message into summary and details if it's long
        if len(message) > 100 or '\n' in message or '|' in message:
            # Try to create meaningful summary
            if ':' in message:
                summary = message.split(':')[0] + " (see details)"
            else:
                summary = message[:100] + "..."
            FolderCompareSync_class.ErrorDetailsDialog_class(self.root, "Error", summary, message)
        else:
            # Short message - use simple dialog
            messagebox.showerror("Error", message)
            
        self.status_var.set("Ready")
        
    def run(self):
        """
        Start the application GUI event loop
        
        Purpose:
        --------
        Main application entry point that starts the GUI event loop
        with comprehensive error handling and graceful shutdown.
        """
        log_and_flush(logging.INFO, "Starting FolderCompareSync GUI application.")
        try:
            self.root.mainloop()
        except Exception as e:
            log_and_flush(logging.ERROR, f"Application crashed: {type(e).__name__}: {str(e)}")
            if __debug__:
                log_and_flush(logging.DEBUG, "Crash traceback:")
                log_and_flush(logging.DEBUG, traceback.format_exc())
            raise
        finally:
            log_and_flush(logging.INFO, "Application shutdown")

    def open_debug_global_editor(self): # v001.0019 added [DebugGlobalEditor_class integration - main editor method]
        """
        Open the DebugGlobalEditor_class and handle UI recreation if changes are applied.
        
        Purpose:
        --------
        Main integration method that captures application state, opens the debug editor,
        and handles UI recreation with updated global values using the destroy/recreate
        pattern for clean integration.
        """
        if not __debug__:
            self.add_status_message("Debug Global Editor is only available in debug builds")
            return
        
        log_and_flush(logging.INFO, "Opening DebugGlobalEditor_class for global variable modification")
        self.add_status_message("Opening Debug Global Editor...")
        
        try:
            # Capture current application state before opening editor
            captured_state = self.capture_application_state()
            
            # Create and open the debug editor
            editor = DebugGlobalEditor_class(
                self.root,
                module=sys.modules[__name__],  # v001.0019 changed [explicitly pass FolderCompareSync module instead of auto-detection]
                title="FolderCompareSync - Debug Global Variables",
                allow_recompute=True
            )
            
            # Open modal dialog and get result
            result = editor.open()
            
            # Handle result
            if result.get('applied', False):
                changes = result.get('changes', {})
                if changes:
                    log_and_flush(logging.INFO, f"Debug editor applied {len(changes)} global changes:\n{changes}")
                    self.add_status_message(f"Debug Global Editor applied {len(changes)} changes:\n{changes}")
                    
                    # v001.0021 changed [directly recreate UI in-place instead of scheduling]
                    # Recreate UI with updated globals
                    self._recreate_ui_with_new_globals(captured_state, changes)
                else:
                    self.add_status_message("Debug Global Editor completed - no changes applied")
            else:
                self.add_status_message("Debug Global Editor cancelled")
                
            # Clean up editor reference
            del editor
            
        except Exception as e:
            error_msg = f"Error opening Debug Global Editor: {str(e)}"
            log_and_flush(logging.ERROR, error_msg)
            if __debug__:
                log_and_flush(logging.DEBUG, f"Debug editor exception: {traceback.format_exc()}")
            self.add_status_message(f"ERROR: {error_msg}")
            self.show_error(error_msg)
    
    def _recreate_ui_with_new_globals(self, captured_state: dict, changes: dict): # v001.0021 changed [recreate UI in-place instead of new instance]
        """
        Recreate the UI in-place using updated global values.
        
        Purpose:
        --------
        Implements in-place UI recreation to avoid multiple Tk instance issues.
        Destroys all widgets, recreates fonts/styles with new globals, rebuilds UI,
        and restores state - all within the same application instance.
        """
        log_and_flush(logging.INFO, "Recreating UI in-place with updated global values")
        
        try:
            # Add final status message before UI destruction
            self.add_status_message("Rebuilding UI with new global settings...")
            
            # v001.0021 added [stop any running background operations before UI recreation]
            # Store a flag to prevent new operations during recreation
            self._ui_recreating = True
            
            # v001.0021 added [destroy all child widgets of root]
            # This removes everything but keeps the root window
            log_and_flush(logging.DEBUG, "Destroying all UI widgets for recreation")
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # v001.0021 added [clear widget references to prevent stale references]
            self.left_tree = None
            self.right_tree = None
            self.status_log_text = None
            
            # v001.0021 added [recreate fonts and styles with new global values]
            log_and_flush(logging.DEBUG, "Recreating fonts and styles with new global values")
            self.create_fonts_and_styles()
            
            # v001.0021 added [rebuild the entire UI using existing setup_ui method]
            log_and_flush(logging.DEBUG, "Rebuilding UI structure")
            self.setup_ui()
            
            # v001.0021 added [clear recreation flag]
            self._ui_recreating = False
            
            # v001.0021 added [restore application state to the rebuilt UI]
            log_and_flush(logging.DEBUG, "Restoring application state to rebuilt UI")
            self.restore_application_state(captured_state)
            
            # Add status messages about the recreation
            change_summary = ", ".join(f"{name}={info['new']}" for name, info in changes.items())
            self.add_status_message(f"UI recreated with debug changes: {change_summary}")
            
            # v001.0021 added [check if we should offer auto-compare]
            should_auto_compare = (
                captured_state.get('left_folder') and 
                captured_state.get('right_folder') and
                captured_state.get('has_comparison_data', False)
            )
            
            if should_auto_compare:
                # Ask user if they want to auto-compare
                auto_compare = messagebox.askyesno(
                    "Auto-Compare",
                    "UI has been recreated with new global settings.\n\n"
                    "Would you like to automatically re-compare the folders\n"
                    "to see the results with the new settings?",
                    parent=self.root
                )
                
                if auto_compare:
                    self.add_status_message("Auto-comparing folders with new settings...")
                    # Start comparison in background thread
                    threading.Thread(target=self.perform_comparison, daemon=True).start()
            
            log_and_flush(logging.INFO, "UI recreation completed successfully")
            
        except Exception as e:
            error_msg = f"Error recreating UI: {str(e)}"
            log_and_flush(logging.ERROR, error_msg)
            if __debug__:
                log_and_flush(logging.DEBUG, f"UI recreation exception: {traceback.format_exc()}")
            self.add_status_message(f"ERROR: {error_msg}")
            messagebox.showerror("UI Recreation Failed", f"{error_msg}\n\nThe application may need to be restarted.")

    def capture_application_state(self) -> dict[str, Any]: # v001.0019 added [DebugGlobalEditor_class integration - state capture]
        """
        Capture current application state for restoration after UI recreation.
        
        Purpose:
        --------
        Saves all important application state including folder paths, comparison results,
        selections, filter state, and UI configuration for restoration after debug
        global changes trigger UI recreation.
        
        Returns:
        --------
        dict: Complete application state dictionary
        """
        if __debug__: 
            log_and_flush(logging.DEBUG, "Capturing application state for debug UI recreation") 
        
        state = {} 
        
        try: 
            # Folder paths 
            state['left_folder'] = self.left_folder.get() 
            state['right_folder'] = self.right_folder.get() 
            
            # Comparison options 
            state['compare_existence'] = self.compare_existence.get() 
            state['compare_size'] = self.compare_size.get() 
            state['compare_date_created'] = self.compare_date_created.get() 
            state['compare_date_modified'] = self.compare_date_modified.get() 
            state['compare_sha512'] = self.compare_sha512.get() 
            
            # Operation modes 
            state['overwrite_mode'] = self.overwrite_mode.get() 
            state['dry_run_mode'] = self.dry_run_mode.get() 
            
            # Filter state 
            state['filter_wildcard'] = self.filter_wildcard.get() 
            state['is_filtered'] = self.is_filtered 
            
            # Window geometry 
            state['window_geometry'] = self.root.geometry() 
            state['window_state'] = self.root.state() 
            
            # Comparison data (if exists) 
            if hasattr(self, 'comparison_results') and self.comparison_results: 
                state['has_comparison_data'] = True 
                state['comparison_results'] = self.comparison_results.copy() 
                if hasattr(self, 'filtered_results') and self.filtered_results: 
                    state['filtered_results'] = self.filtered_results.copy() 
            else: 
                state['has_comparison_data'] = False 
            
            # Selection state 
            if hasattr(self, 'selected_left') and hasattr(self, 'selected_right'): 
                state['selected_left'] = self.selected_left.copy() 
                state['selected_right'] = self.selected_right.copy() 
            
            # File count tracking 
            state['file_count_left'] = getattr(self, 'file_count_left', 0) 
            state['file_count_right'] = getattr(self, 'file_count_right', 0) 
            state['total_file_count'] = getattr(self, 'total_file_count', 0) 
            state['limit_exceeded'] = getattr(self, 'limit_exceeded', False) 
            
            # Status information 
            state['status_var'] = self.status_var.get() 
            state['summary_var'] = self.summary_var.get() 
            
            # Status log history 
            if hasattr(self, 'status_log_lines'): 
                state['status_log_lines'] = self.status_log_lines.copy() 
            
            if __debug__: 
                log_and_flush(logging.DEBUG, f"Successfully captured application state: {len(state)} items") 
                
        except Exception as e: 
            log_and_flush(logging.ERROR, f"Error capturing application state: {e}") 
            if __debug__: 
                log_and_flush(logging.DEBUG, f"State capture exception: {traceback.format_exc()}") 
        
        return state 

    def restore_application_state(self, state: dict[str, Any]): # v001.0021 changed [simplified for in-place UI recreation]
        """
        Restore application state after UI recreation.
        
        Purpose:
        --------
        Restores all captured application state including folder paths, comparison results,
        selections, filter state, and UI configuration after debug global changes have
        triggered in-place UI recreation with new global values.
        
        Args:
        -----
        state: Application state dictionary from capture_application_state
        """
        if __debug__:
            log_and_flush(logging.DEBUG, "Restoring application state after in-place UI recreation")
        
        try:
            # Restore folder paths
            if 'left_folder' in state and state['left_folder']:
                self.left_folder.set(state['left_folder'])
                log_and_flush(logging.DEBUG, f"Restored left folder: {state['left_folder']}")
                    
            if 'right_folder' in state and state['right_folder']:
                self.right_folder.set(state['right_folder'])
                log_and_flush(logging.DEBUG, f"Restored right folder: {state['right_folder']}")
            
            # Restore comparison options
            if 'compare_existence' in state:
                self.compare_existence.set(state['compare_existence'])
            if 'compare_size' in state:
                self.compare_size.set(state['compare_size'])
            if 'compare_date_created' in state:
                self.compare_date_created.set(state['compare_date_created'])
            if 'compare_date_modified' in state:
                self.compare_date_modified.set(state['compare_date_modified'])
            if 'compare_sha512' in state:
                self.compare_sha512.set(state['compare_sha512'])
            
            # Restore operation modes
            if 'overwrite_mode' in state:
                self.overwrite_mode.set(state['overwrite_mode'])
            if 'dry_run_mode' in state:
                self.dry_run_mode.set(state['dry_run_mode'])
            
            # Restore filter state
            if 'filter_wildcard' in state:
                self.filter_wildcard.set(state['filter_wildcard'])
            if 'is_filtered' in state:
                self.is_filtered = state['is_filtered']
            
            # Restore window geometry (after a brief delay for UI to settle)
            if 'window_geometry' in state:
                self.root.after(100, lambda: self.root.geometry(state['window_geometry']))
            if 'window_state' in state and state['window_state'] != 'normal':
                self.root.after(200, lambda: self.root.state(state['window_state']))
            
            # Restore comparison data
            if state.get('has_comparison_data', False):
                if 'comparison_results' in state:
                    self.comparison_results = state['comparison_results']
                if 'filtered_results' in state:
                    self.filtered_results = state['filtered_results']
                    
                # v001.0021 added [rebuild trees with restored comparison data]
                # Update the UI to show the restored comparison results
                if self.is_filtered:
                    self.update_comparison_ui_filtered()
                else:
                    self.update_comparison_ui()
            
            # Restore selection state
            if 'selected_left' in state:
                self.selected_left = state['selected_left']
            if 'selected_right' in state:
                self.selected_right = state['selected_right']
            
            # Restore file count tracking
            self.file_count_left = state.get('file_count_left', 0)
            self.file_count_right = state.get('file_count_right', 0)
            self.total_file_count = state.get('total_file_count', 0)
            self.limit_exceeded = state.get('limit_exceeded', False)
            
            # Restore status information
            if 'status_var' in state:
                self.status_var.set(state['status_var'])
            if 'summary_var' in state:
                self.summary_var.set(state['summary_var'])
            
            # Restore status log history
            if 'status_log_lines' in state:
                self.status_log_lines = state['status_log_lines']
                # Update status log display
                if self.status_log_text:
                    self.status_log_text.config(state=tk.NORMAL)
                    self.status_log_text.delete('1.0', tk.END)
                    self.status_log_text.insert('1.0', '\n'.join(self.status_log_lines))
                    self.status_log_text.config(state=tk.DISABLED)
                    self.status_log_text.see(tk.END)
            
            # Add status message about restoration
            self.add_status_message("Application state restored after debug global changes")
            
            if __debug__:
                log_and_flush(logging.DEBUG, "Successfully restored application state")
                
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error restoring application state: {e}")
            if __debug__:
                log_and_flush(logging.DEBUG, f"State restore exception: {traceback.format_exc()}")
            self.add_status_message(f"Warning: Some application state could not be restored: {str(e)}")
