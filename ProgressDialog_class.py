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
    Progress dialog for long-running operations with configurable display options and dual-progress support.
    
    Purpose:
    --------
    Provides user feedback during lengthy operations like scanning, comparison,
    and copy operations with both determinate and indeterminate progress modes.
    Enhanced to support dual-progress display for copy and verification phases.
    
    Usage:
    ------
    # Single progress (existing)
    progress = ProgressDialog_class(parent, "Scanning", "Scanning files...", max_value=1000)
    progress.update_progress(500, "Processing file 500...")
    progress.close()
    
    # Dual progress (new for copy operations)
    progress = ProgressDialog_class(parent, "Copying Files", "Copying files...", 
                                   max_value=100, dual_progress=True)
    progress.update_dual_progress(copy_progress=75, verify_progress=25, 
                                 "Copy: 75% | Verify: 25%")
    progress.close()
    """
    
    def __init__(self, parent, title, message, max_value=None, dual_progress=False):
        """
        Initialize progress dialog with configurable dimensions and dual-progress support.
        
        Args:
        -----
        parent: Parent window for dialog positioning
        title: Dialog window title
        message: Initial progress message
        max_value: Maximum value for percentage (None for indeterminate)
        dual_progress: Enable dual progress bars for copy and verification
        """
        log_and_flush(logging.DEBUG, f"Creating progress dialog: {title} (dual_progress={dual_progress})")
        
        self.parent = parent
        self.max_value = max_value
        self.current_value = 0
        self.dual_progress = dual_progress
        
        # Calculate dialog height based on mode
        dialog_height = C.PROGRESS_DIALOG_HEIGHT
        if dual_progress:
            dialog_height += 60  # Extra height for second progress bar and labels
        
        # Create dialog window using global constants
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{C.PROGRESS_DIALOG_WIDTH}x{dialog_height}")
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
        
        if dual_progress:
            self._setup_dual_progress(progress_frame)
        else:
            self._setup_single_progress(progress_frame)
        
        # Update the display
        self.dialog.update_idletasks()
        
        # Center on parent window using configurable dialog dimensions
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (C.PROGRESS_DIALOG_WIDTH // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (dialog_height // 2)
        self.dialog.geometry(f"{C.PROGRESS_DIALOG_WIDTH}x{dialog_height}+{x}+{y}")
        
    def _setup_single_progress(self, parent_frame):
        """Setup single progress bar (original functionality)."""
        # Progress bar or counter display
        if self.max_value is not None:
            # Determinate progress bar for operations with known total
            self.progress_bar = ttk.Progressbar(
                parent_frame, mode='determinate', maximum=self.max_value, length=300
            )
            self.progress_bar.pack(pady=(0, 10))
            
            # Percentage label
            self.percent_var = tk.StringVar(value="0%")
            ttk.Label(parent_frame, textvariable=self.percent_var).pack()
        else:
            # Indeterminate progress for operations with unknown total (like file counting)
            self.progress_bar = ttk.Progressbar(
                parent_frame, mode='indeterminate', length=300
            )
            self.progress_bar.pack(pady=(0, 10))
            self.progress_bar.start(C.PROGRESS_ANIMATION_SPEED)  # Use configurable animation speed
            
            # Running counter display
            self.count_var = tk.StringVar(value="0 items")
            ttk.Label(parent_frame, textvariable=self.count_var, 
                     font=("TkDefaultFont", 9)).pack()
    
    def _setup_dual_progress(self, parent_frame):
        """Setup dual progress bars for copy and verification phases."""
        # Copy progress section
        copy_frame = ttk.LabelFrame(parent_frame, text="Copy Progress", padding=5)
        copy_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.copy_progress_bar = ttk.Progressbar(
            copy_frame, mode='determinate', maximum=100, length=280
        )
        self.copy_progress_bar.pack(pady=(2, 2))
        
        self.copy_percent_var = tk.StringVar(value="0%")
        ttk.Label(copy_frame, textvariable=self.copy_percent_var, 
                 font=("TkDefaultFont", 9)).pack()
        
        # Verification progress section
        verify_frame = ttk.LabelFrame(parent_frame, text="Verification Progress", padding=5)
        verify_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.verify_progress_bar = ttk.Progressbar(
            verify_frame, mode='determinate', maximum=100, length=280
        )
        self.verify_progress_bar.pack(pady=(2, 2))
        
        self.verify_percent_var = tk.StringVar(value="0%")
        ttk.Label(verify_frame, textvariable=self.verify_percent_var, 
                 font=("TkDefaultFont", 9)).pack()
        
        # Overall status
        self.overall_status_var = tk.StringVar(value="Preparing...")
        ttk.Label(parent_frame, textvariable=self.overall_status_var, 
                 font=("TkDefaultFont", 9, "bold")).pack(pady=(5, 0))

        # >>> CHANGE START # per chatGPT 1) Add a Cancel/Close row to the dual progress UI
        # Button row: Cancel (left) and Close (right). Close is enabled at completion.
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill=tk.X, pady=(6, 0))
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._handle_cancel)
        self.cancel_button.pack(side=tk.LEFT)
        self.close_button = ttk.Button(button_frame, text="Close", command=self.close)
        self.close_button.pack(side=tk.RIGHT)
        # Close should only be used after completion
        try:
            self.close_button.state(['disabled'])
        except Exception:
            pass
        self._on_cancel = None  # optional handler set via set_cancel_handler()
        # <<< CHANGE END
              
    def update_message(self, message):
        """Update the progress message display."""
        self.message_var.set(message)
        self.dialog.update_idletasks()
        
    def update_progress(self, value, message=None):
        """Update progress value and optionally message (single progress mode)."""
        if self.dual_progress:
            # In dual progress mode, this updates the main message only
            if message:
                self.message_var.set(message)
            self.dialog.update_idletasks()
            return
            
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
    
    def update_dual_progress(self, copy_progress=None, verify_progress=None, 
                           overall_message=None, copy_message=None, verify_message=None):
        """
        Update dual progress bars for copy and verification phases.
        
        Args:
        -----
        copy_progress: Copy progress percentage (0-100)
        verify_progress: Verification progress percentage (0-100)
        overall_message: Main message to display
        copy_message: Optional copy-specific message
        verify_message: Optional verification-specific message
        """
        if not self.dual_progress:
            return  # Not in dual progress mode
            
        if copy_progress is not None:
            self.copy_progress_bar['value'] = copy_progress
            copy_text = f"{int(copy_progress)}%"
            if copy_message:
                copy_text += f" - {copy_message}"
            self.copy_percent_var.set(copy_text)
            
        if verify_progress is not None:
            self.verify_progress_bar['value'] = verify_progress
            verify_text = f"{int(verify_progress)}%"
            if verify_message:
                verify_text += f" - {verify_message}"
            self.verify_percent_var.set(verify_text)
            
        if overall_message:
            self.overall_status_var.set(overall_message)
            
        self.dialog.update_idletasks()
    
    def set_copy_phase(self, message="Copying files..."):
        """Set dialog to copy phase (dual progress mode)."""
        if not self.dual_progress:
            return
        self.overall_status_var.set(message)
        self.copy_progress_bar.configure(style="")  # Normal style
        self.verify_progress_bar.configure(style="TProgressbar")  # Inactive style
        self.dialog.update_idletasks()
    
    def set_verify_phase(self, message="Verifying files..."):
        """Set dialog to verification phase (dual progress mode)."""
        if not self.dual_progress:
            return
        self.overall_status_var.set(message)
        self.copy_progress_bar.configure(style="TProgressbar")  # Inactive style
        self.verify_progress_bar.configure(style="")  # Normal style
        self.dialog.update_idletasks()
    
    def set_completion_phase(self, message="Operation complete"):
        """Set dialog to completion phase (dual progress mode)."""
        if not self.dual_progress:
            return
        self.overall_status_var.set(message)
        # Both bars remain as-is to show final results
        # >>> CHANGE START # per chatGPT 2) Add a Cancel/Close row to the dual progress UI
        # Enable Close button at completion (if present)
        try:
            if hasattr(self, "close_button"):
                self.close_button.state(['!disabled'])
        except Exception:
            pass
        # <<< CHANGE END
        self.dialog.update_idletasks()

    # >>> CHANGE START # per chatGPT 2) Add a Cancel/Close row to the dual progress UI
    def set_cancel_handler(self, handler):
        """Optional: host code can supply a no-arg handler to call when Cancel is clicked."""
        self._on_cancel = handler

    def _handle_cancel(self):
        """Internal: invoked by the Cancel button."""
        # Update UI to reflect cancelling
        try:
            if hasattr(self, "cancel_button"):
                self.cancel_button.state(['disabled'])
        except Exception:
            pass
        # Give both message areas a hint if present
        try:
            self.message_var.set("Cancelling...")
        except Exception:
            pass
        try:
            if hasattr(self, "overall_status_var"):
                self.overall_status_var.set("Cancelling...")
        except Exception:
            pass
        self.dialog.update_idletasks()
        # Call through to host if provided
        if getattr(self, "_on_cancel", None):
            try:
                self._on_cancel()
            except Exception:
                pass
    # <<< CHANGE END

    def close(self):
        """Close the progress dialog and clean up resources."""
        log_and_flush(logging.DEBUG, "Closing progress dialog")
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.stop()  # Stop any animation
            if hasattr(self, 'copy_progress_bar'):
                # Dual progress bars don't use animation, but clean up anyway
                pass
            self.dialog.grab_release()
            self.dialog.destroy()
        except tk.TclError:
            pass  # Dialog already destroyed


class CopyProgressManager_class:
    """
    Specialized progress manager for copy operations with DIRECT/STAGED strategy support.
    
    Purpose:
    --------
    Manages progress reporting for the enhanced file copy system with proper
    phase tracking, cancellation support, and strategy-aware progress updates.
    """
    
    def __init__(self, parent, operation_name: str, total_files: int = 0, 
                 total_bytes: int = 0, cancellation_callback=None):
        """
        Initialize copy progress manager.
        
        Args:
        -----
        parent: Parent window for progress dialog
        operation_name: Name of the copy operation
        total_files: Total number of files to process
        total_bytes: Total bytes to copy (if known)
        cancellation_callback: Callback function to check for user cancellation
        """
        self.parent = parent
        self.operation_name = operation_name
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.cancellation_callback = cancellation_callback
        
        # Progress tracking
        self.files_processed = 0
        self.bytes_processed = 0
        self.current_phase = "preparing"
        self.current_file = ""
        self.current_strategy = ""
        
        # Create dual progress dialog
        self.progress_dialog = ProgressDialog_class(
            parent, 
            f"Copy Operation - {operation_name}",
            "Preparing copy operation...",
            dual_progress=True
        )
        
        # Progress update frequency control
        self.last_update_time = 0
        self.update_frequency = 1.0 / C.FILECOPY_PROGRESS_UPDATE_FREQUENCY_HZ
        
        log_and_flush(logging.DEBUG, f"Created copy progress manager: {operation_name}")
    
    def start_copy_phase(self):
        """Start the copy phase of the operation."""
        self.current_phase = "copying"
        self.progress_dialog.set_copy_phase("Copying files...")
        log_and_flush(logging.DEBUG, "Copy phase started")
    
    def start_verify_phase(self):
        """Start the verification phase of the operation."""
        self.current_phase = "verifying"  
        self.progress_dialog.set_verify_phase("Verifying files...")
        log_and_flush(logging.DEBUG, "Verification phase started")
    
    def update_file_progress(self, file_path: str, bytes_copied: int, total_bytes: int, 
                           strategy: str = ""):
        """
        Update progress for current file being processed.
        
        Args:
        -----
        file_path: Path of file being processed
        bytes_copied: Bytes copied so far for this file
        total_bytes: Total bytes for this file
        strategy: Copy strategy being used (DIRECT/STAGED)
        """
        current_time = time.time()
        
        # Throttle updates for performance
        if current_time - self.last_update_time < self.update_frequency:
            return
        
        self.current_file = os.path.basename(file_path)
        self.current_strategy = strategy
        self.last_update_time = current_time
        
        # Calculate file progress percentage
        file_progress = (bytes_copied / total_bytes * 100) if total_bytes > 0 else 0
        
        # Calculate overall progress
        overall_copy_progress = 0
        overall_verify_progress = 0
        
        if self.total_files > 0:
            base_progress = (self.files_processed / self.total_files) * 100
            
            if self.current_phase == "copying":
                overall_copy_progress = min(base_progress + (file_progress / self.total_files), 100)
                overall_verify_progress = 0
            elif self.current_phase == "verifying":
                overall_copy_progress = 100  # Copy phase complete
                overall_verify_progress = min(base_progress + (file_progress / self.total_files), 100)
        
        # Build status message
        strategy_text = f" ({strategy})" if strategy else ""
        file_size_text = self._format_bytes(total_bytes) if total_bytes > 0 else ""
        
        if self.current_phase == "copying":
            phase_message = f"Copying{strategy_text}: {self.current_file}"
            if file_size_text:
                phase_message += f" ({file_size_text})"
        else:
            phase_message = f"Verifying: {self.current_file}"
            if file_size_text:
                phase_message += f" ({file_size_text})"
        
        overall_message = f"{phase_message} - {self.files_processed + 1}/{self.total_files}"
        
        # Update progress dialog
        self.progress_dialog.update_dual_progress(
            copy_progress=overall_copy_progress,
            verify_progress=overall_verify_progress,
            overall_message=overall_message
        )
        
        # Check for cancellation
        if self.cancellation_callback and self.cancellation_callback():
            log_and_flush(logging.DEBUG, "User cancellation detected")
            return False
        
        return True

    # >>> CHANGE START # per chatGPT 5) to wire in pop-up progress dialogue
    def update_verify_progress(self, bytes_processed: int, total_bytes: int):
        """Adapter for verification progress used by FileCopyManager.
        Updates the dual progress bars without changing the existing APIs."""
        # Ensure we are in verify phase for correct messaging
        self.current_phase = 'verifying'
        # Compute per-file verification percentage
        if total_bytes and total_bytes > 0:
            verify_pct = (bytes_processed / total_bytes) * 100
        else:
            verify_pct = 0
        # Update only the verify bar; copy bar is left as-is
        self.progress_dialog.update_dual_progress(verify_progress=verify_pct)
        return True
    # <<< CHANGE END
    
    def complete_file(self, success: bool = True):
        """Mark current file as complete."""
        if success:
            self.files_processed += 1
            # # DEBUG: Uncomment for detailed file completion logging
            # log_and_flush(logging.DEBUG, f"File completed: {self.current_file} ({self.files_processed}/{self.total_files})")
    
    def complete_operation(self, success: bool = True, message: str = ""):
        """Complete the copy operation."""
        if success:
            completion_msg = message or "Copy operation completed successfully"
        else:
            completion_msg = message or "Copy operation failed"
            
        self.progress_dialog.set_completion_phase(completion_msg)
        log_and_flush(logging.DEBUG, f"Copy operation completed: {completion_msg}")
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format byte value in human readable format."""
        if bytes_value is None:
            return ""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}TB"
    
    def close(self):
        """Close the progress dialog."""
        self.progress_dialog.close()
