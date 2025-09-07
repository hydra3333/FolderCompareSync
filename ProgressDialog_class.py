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
                                  overall_message="Copy: 75% | Verify: 25%")
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
        except Exception as ex:
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
        except Exception as ex:
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
        except Exception as ex:
            pass
        # Give both message areas a hint if present
        try:
            self.message_var.set("Cancelling...")
        except Exception as ex:
            pass
        try:
            if hasattr(self, "overall_status_var"):
                self.overall_status_var.set("Cancelling...")
        except Exception as ex:
            pass
        self.dialog.update_idletasks()
        # Call through to host if provided
        if getattr(self, "_on_cancel", None):
            try:
                self._on_cancel()
            except Exception as ex:
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
    Thread-safe progress manager for copy/verify.
    All updates are queued and applied on the Tk main thread via after_idle.
    """

    def __init__(self, parent, operation_name: str, total_files: int = 0,
                 total_bytes: int = 0, cancellation_callback=None):
        import time as _time
        import queue as _queue
        import FolderCompareSync_Global_Constants as C
        from ProgressDialog_class import ProgressDialog_class

        self._time = _time
        self._queue = _queue
        self.parent = parent
        self.operation_name = operation_name
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.cancellation_callback = cancellation_callback

        self.files_processed = 0
        self.bytes_processed = 0
        self.current_phase = "preparing"
        self.current_file = ""
        self.current_strategy = ""

        self.progress_dialog = ProgressDialog_class(
            parent,
            f"Copy Operation - {operation_name}",
            "Preparing copy operation.",
            dual_progress=True
        )

        self.last_update_time = 0.0
        self.update_frequency = 1.0 / getattr(C, "FILECOPY_PROGRESS_UPDATE_FREQUENCY_HZ", 20.0)

        self._q = self._queue.Queue()
        self._pump_scheduled = False
        self._last_verify_msg = None
        self._cancel_latched = False

    # Phases
    def start_copy_phase(self):
        self.current_phase = "copying"
        try:
            self.progress_dialog.set_copy_phase("Copying files...")
        except Exception:
            pass

    def start_verify_phase(self):
        self.current_phase = "verifying"
        try:
            self.progress_dialog.set_verify_phase("Verifying files...")
        except Exception:
            pass

    def complete_file(self, success: bool = True):
        if success:
            self.files_processed += 1

    def complete_operation(self, success: bool = True, message: str = ""):
        try:
            if success:
                self.progress_dialog.set_completion_phase("Operation complete")
            else:
                self.progress_dialog.set_completion_phase("Operation finished with errors")
        except Exception:
            pass
        try:
            self.progress_dialog.close()
        except Exception:
            pass

    # Public updates (thread-safe)
    def update_file_progress(self, file_path: str, bytes_copied: int, total_bytes: int, strategy: str = ""):
        if self._check_cancel():
            return False
        self._q.put(("file", (file_path, int(bytes_copied), int(total_bytes), str(strategy))))
        self._schedule_pump()
        return True

    def update_verify_progress(self, bytes_processed: int, total_bytes: int):
        if self._check_cancel():
            return False
        self._q.put(("verify", (int(bytes_processed), int(total_bytes))))
        self._schedule_pump()
        return True

    # Pumping
    def _schedule_pump(self):
        if self._pump_scheduled:
            return
        self._pump_scheduled = True
        try:
            widget = getattr(self.progress_dialog, "dialog", None) or self.parent
            widget.after_idle(self._pump_updates)
        except Exception:
            self._pump_scheduled = False
            self._pump_updates()

    def _pump_updates(self):
        self._pump_scheduled = False
        now = self._time.time()
        if (now - self.last_update_time) < self.update_frequency:
            self._schedule_pump()
            return

        coalesced = {"file": None, "verify": None}
        processed = False
        try:
            while True:
                kind, payload = self._q.get_nowait()
                coalesced[kind] = payload
                processed = True
        except self._queue.Empty:
            pass

        if not processed:
            return
        self.last_update_time = now

        if coalesced["file"] is not None:
            fp, bc, tb, strat = coalesced["file"]
            try:
                self._apply_file_update(fp, bc, tb, strat)
            except Exception:
                pass
        if coalesced["verify"] is not None:
            bp, tb = coalesced["verify"]
            try:
                self._apply_verify_update(bp, tb)
            except Exception:
                pass

        if not self._q.empty():
            self._schedule_pump()

    # Apply helpers
    def _apply_file_update(self, file_path: str, bytes_copied: int, total_bytes: int, strategy: str):
        name = (file_path or "").split("/")[-1].split("\\")[-1]
        self.current_file = name
        self.current_strategy = strategy or ""
        file_pct = (bytes_copied / total_bytes * 100.0) if total_bytes > 0 else 0.0
        overall_copy_pct = 0.0
        overall_verify_pct = 0.0
        if self.total_files > 0:
            base = (self.files_processed / self.total_files) * 100.0
            if self.current_phase == "copying":
                overall_copy_pct = min(base + (file_pct / self.total_files), 100.0)
            elif self.current_phase == "verifying":
                overall_copy_pct = 100.0
                overall_verify_pct = min(base + (file_pct / self.total_files), 100.0)

        strat_text = f" ({self.current_strategy})" if self.current_strategy else ""
        size_text = self._fmt_bytes(total_bytes) if total_bytes > 0 else ""
        phase_msg = f"Verifying: {name}" if self.current_phase == "verifying" else f"Copying{strat_text}: {name}"
        if size_text:
            phase_msg += f" ({size_text})"
        overall_msg = f"{phase_msg} - {self.files_processed + 1}/{self.total_files}"

        try:
            self.progress_dialog.update_dual_progress(
                copy_progress=overall_copy_pct,
                verify_progress=overall_verify_pct,
                overall_message=overall_msg
            )
        except Exception:
            pass

    def _apply_verify_update(self, bytes_processed: int, total_bytes: int):
        if getattr(self, "current_phase", "") != "verifying":
            try:
                self.start_verify_phase()
            except Exception:
                pass
            self.current_phase = "verifying"

        pct = (bytes_processed / total_bytes * 100.0) if total_bytes > 0 else 100.0
        mb_done = bytes_processed / (1024 * 1024)
        mb_total = (total_bytes / (1024 * 1024)) if total_bytes > 0 else mb_done
        verify_msg = f"{mb_done:.1f} MB of {mb_total:.1f} MB"
        self._last_verify_msg = verify_msg

        overall_msg = None
        if getattr(self, "current_file", ""):
            overall_msg = f"Verifying {self.current_file} - {verify_msg}"

        try:
            self.progress_dialog.update_dual_progress(
                verify_progress=pct,
                verify_message=verify_msg,
                overall_message=overall_msg
            )
        except Exception:
            pass

    @staticmethod
    def _fmt_bytes(n: int) -> str:
        try:
            units = ["B", "KB", "MB", "GB", "TB"]
            x = float(n)
            i = 0
            while x >= 1024.0 and i < len(units) - 1:
                x /= 1024.0
                i += 1
            return f"{x:.1f} {units[i]}"
        except Exception:
            return f"{n} B"

    # Cancel helpers
    def _check_cancel(self) -> bool:
        if self._cancel_latched:
            return True
        try:
            if self.cancellation_callback and self.cancellation_callback():
                self._cancel_latched = True
                return True
        except Exception:
            return False
        return False

    def get_cancelled(self) -> bool:
        return self._cancel_latched
