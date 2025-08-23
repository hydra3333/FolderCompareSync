# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
from FolderCompareSync_Global_Imports import *

# import out global constants first
import FolderCompareSync_Global_Constants as C

# import our flushed_logging before other modules
#from flushed_logging import *   # includes LoggerManager
from flushed_logging import log_and_flush, get_log_level, LoggerManager

# Import the things this class references
# nil

class ProgressDialog_class:
    """
    Progress dialog for long-running operations with configurable display options.
    
    Purpose:
    --------
    Provides user feedback during lengthy operations like scanning, comparison,
    and copy operations with both determinate and indeterminate progress modes.
    
    Usage:
    ------
    progress = ProgressDialog_class(parent, "Scanning", "Scanning files...", max_value=1000)
    progress.update_progress(500, "Processing file 500...")
    progress.close()
    """
    
    def __init__(self, parent, title, message, max_value=None):
        """
        Initialize progress dialog with configurable dimensions.
        
        Args:
        -----
        parent: Parent window for dialog positioning
        title: Dialog window title
        message: Initial progress message
        max_value: Maximum value for percentage (None for indeterminate)
        """
        log_and_flush(logging.DEBUG, f"Creating progress dialog: {title}")
        
        self.parent = parent
        self.max_value = max_value
        self.current_value = 0
        
        # Create dialog window using global constants
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{C.PROGRESS_DIALOG_WIDTH}x{C.PROGRESS_DIALOG_HEIGHT}")
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
            self.progress_bar.start(C.PROGRESS_ANIMATION_SPEED)  # Use configurable animation speed
            
            # Running counter display
            self.count_var = tk.StringVar(value="0 items")
            ttk.Label(progress_frame, textvariable=self.count_var, 
                     font=("TkDefaultFont", 9)).pack()
        
        # Update the display
        self.dialog.update_idletasks()
        
        # Center on parent window using configurable dialog dimensions
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (C.PROGRESS_DIALOG_WIDTH // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (C.PROGRESS_DIALOG_HEIGHT // 2)
        self.dialog.geometry(f"{C.PROGRESS_DIALOG_WIDTH}x{C.PROGRESS_DIALOG_HEIGHT}+{x}+{y}")
        
    def update_message(self, message):
        """Update the progress message display."""
        self.message_var.set(message)
        self.dialog.update_idletasks()
        
    def update_progress(self, value, message=None):
        """Update progress value and optionally message."""
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
        """Close the progress dialog and clean up resources."""
        log_and_flush(logging.DEBUG, "Closing progress dialog")
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.stop()  # Stop any animation
            self.dialog.grab_release()
            self.dialog.destroy()
        except tk.TclError:
            pass  # Dialog already destroyed
