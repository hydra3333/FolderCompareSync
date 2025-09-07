# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
from FolderCompareSync_Global_Imports import *

# import out global constants first
import FolderCompareSync_Global_Constants as C

# import our flushed_logging before other modules
from flushed_logging import log_and_flush, get_log_level, LoggerManager

# Import the things this class references
from ProgressDialog_class import ProgressDialog_class, CopyProgressManager_class
from FileTimestampManager_class import FileTimestampManager_class

class FileCopyManager_class:
    """
    Enhanced file copy manager implementing DIRECT and STAGED strategies with comprehensive
    verification, secure rollback, and Windows API optimization.
    
    Purpose:
    --------
    Manages file copy operations using intelligent strategy selection based on file
    size and drive types, with support for Windows CopyFileExW, memory-mapped verification,
    BLAKE3 hashing, and bulletproof rollback mechanisms.
    
    Key Features:
    -------------
    - Dual copy strategies (DIRECT and STAGED) with automatic selection
    - Secure temporary file rollback (original files never corrupted)
    - Windows CopyFileExW integration with progress callbacks
    - Memory-mapped verification for local files
    - BLAKE3 hashing for network/large files
    - Enhanced network and cloud storage detection
    - Comprehensive error handling and logging
    
    Usage:
    ------
    copy_manager = FileCopyManager_class(status_callback=add_status_message)
    operation_id = copy_manager.start_copy_operation("Copy Operation")
    result = copy_manager.copy_file(source, target)  # overwrite parameter removed (M12)
    copy_manager.end_copy_operation(success_count, error_count, total_bytes)
    """

    class CopyStrategy(Enum):
        """
        Copy strategy enumeration for different file handling approaches.
        
        Purpose:
        --------
        Defines the available copy strategies for file operations based on file 
        size, location, and drive type characteristics per M01-M03.
        """
        DIRECT = "direct".lower()      # Strategy A: CopyFileExW + mmap verification for local files <2GB
        STAGED = "staged".lower()      # Strategy B: Chunked I/O + BLAKE3 hashing for network/large files
    
    class DriveType(Enum):
        """
        Drive type enumeration for enhanced path analysis and strategy selection.
        
        Purpose:
        --------
        Categorizes different drive types to enable optimal copy strategy
        selection based on the characteristics of source and destination drives.
        """
        LOCAL_FIXED = "local_fixed".lower()
        LOCAL_REMOVABLE = "local_removable".lower()
        NETWORK_MAPPED = "network_mapped".lower()
        NETWORK_UNC = "network_unc".lower()
        CLOUD_STORAGE = "cloud_storage".lower()
        RELATIVE = "relative".lower()
        UNKNOWN = "unknown".lower()
    
    @dataclass
    class CopyOperationResult:
        """
        Enhanced result container for copy operation outcomes with detailed information.
        
        Purpose:
        --------
        Stores comprehensive information about copy operation results including
        success status, strategy used, performance metrics, verification results,
        and detailed error information for debugging and user feedback.
        """
        success: bool
        strategy_used: FileCopyManager_class.CopyStrategy
        source_path: str
        target_path: str
        file_size: int
        duration_seconds: float
        bytes_copied: int = 0
        error_message: str = ""
        verification_passed: bool = False
        verification_mode: str = ""          # none/all/lt_threshold
        hash_algorithm: str = ""             # BLAKE3/SHA256/etc
        computed_hash: str = ""              # Source file hash (for STAGED)
        rollback_performed: bool = False     # Whether rollback was needed
        rollback_success: bool = False       # Rollback success status
        sparse_file_detected: bool = False   # Sparse file warning
        throughput_mbps: float = 0.0         # Transfer rate in MB/s
        cancelled_by_user: bool = False      # User cancellation flag
        retry_count: int = 0
        temp_path: str = ""
        backup_path: str = ""
        
        # Performance metrics breakdown
        time_backup: float = 0.0             # Time spent on backup creation
        time_copy: float = 0.0               # Time spent on actual copy
        time_verify: float = 0.0             # Time spent on verification
        time_cleanup: float = 0.0            # Time spent on cleanup
        
        # Enhanced error details
        error_code: int = 0                  # Windows error code if applicable
        error_details: str = ""              # Detailed error information
        recovery_suggestion: str = ""        # Suggested recovery action
    
    def __init__(self, status_callback=None):
        """
        Initialize the enhanced copy manager with callback and supporting components.
        
        Args:
        -----
        status_callback: Function to call for status updates (optional)
        """
        self.status_callback = status_callback
        self.operation_id = None
        self.operation_logger = None
        self.timestamp_manager = FileTimestampManager_class()
        self.operation_sequence = 0

        # >>> CHANGE START: Add optional wiring points (no API break) # per chatGPT change 1.1
        # UI may set these directly: e.g. copy_mgr.progress_manager = CopyProgressManager_class(...)
        # and copy_mgr.cancel_event = threading.Event()
        self.progress_manager = getattr(self, "progress_manager", None)
        self.cancel_event = getattr(self, "cancel_event", None)
        # <<< CHANGE END

        # Initialize hash support
        self.blake3_available = BLAKE3_AVAILABLE
        
        log_and_flush(logging.INFO, f"Enhanced FileCopyManager initialized with BLAKE3 support: {self.blake3_available}")
        
        if self.status_callback:
            hash_info = "BLAKE3" if self.blake3_available else "SHA-256 fallback"
            self.status_callback(f"Enhanced copy manager ready with {hash_info} hashing")

    def _log_status(self, message: str):
        """Log status message to both operation logger and status callback."""
        if self.operation_logger:
            self.operation_logger.info(message)
        if self.status_callback:
            self.status_callback(message)
        log_and_flush(logging.DEBUG, f"Copy operation status: {message}")
    
    @staticmethod
    def determine_copy_strategy(source_path: str, target_path: str, file_size: int) -> FileCopyManager_class.CopyStrategy:
        """
        Decide STAGED vs DIRECT according to the v3 spec.
    
        Rules (preview-safe; actual filesystem mutations happen inside executors):
          1) If either side is network/cloud => STAGED.
          2) If local but "compression intended" => STAGED.
          3) Otherwise DIRECT (small/large split is logged by caller using the size threshold).
    
        Notes:
          - "compression intended" means the source is compressed OR the destination folder has
            compression default-on. (Policy knob can be added later; not required now.)
          - The small/large distinction is NOT a separate enum (we keep DIRECT/STAGED API);
            we log "DIRECT-SMALL" vs "DIRECT-LARGE" in the explainer string based on the size
            threshold C.FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES.
        """
        # Network or cloud on either side? -> STAGED
        try:
            if FileCopyManager_class._is_network_or_cloud_location(source_path)                or FileCopyManager_class._is_network_or_cloud_location(target_path):
                return FileCopyManager_class.CopyStrategy.STAGED
        except Exception:
            # Be conservative on detection failure: treat as local (continue below)
            pass
    
        # Compression intended? -> STAGED
        try:
            if FileCopyManager_class._is_compression_intended(source_path, target_path):
                return FileCopyManager_class.CopyStrategy.STAGED
        except Exception:
            # If detection fails, do not force STAGED on that basis alone.
            pass
    
        # Otherwise DIRECT (SMALL/LARGE split is only for logging / internal executor branching)
        return FileCopyManager_class.CopyStrategy.DIRECT
    
    @staticmethod
    def _is_network_or_cloud_location(path: str) -> bool:
        """
        Comprehensive network and cloud storage detection with multi-layered approach.
        
        Purpose:
        --------
        Uses multiple validation layers for accurate drive type detection including
        traditional network drives, cloud storage patterns, and symbolic link resolution.
        
        Detection Layers:
        -----------------
        1. Primary: GetDriveType Windows API for traditional network drives
        2. Cloud Storage: Pattern matching for common cloud sync folders
        3. Symbolic Links: Resolution of junction points and symbolic links
        4. UNC Path: Checks if resolved paths point to UNC locations
        
        Args:
        -----
        path: File or directory path to analyze
        
        Returns:
        --------
        bool: True if location should use STAGED strategy
        """
        if not path:
            return False
        
        try:
            # Layer 1: Traditional network drive detection
            drive = Path(path).drive or Path(path).parts[0] if Path(path).parts else ""
            if drive:
                drive_type = kernel32.GetDriveTypeW(drive + '\\' if not drive.endswith('\\') else drive)
                if drive_type == win32con.DRIVE_REMOTE:
                    return True
            
            # Layer 2: Cloud storage folder detection (if enabled)
            if C.FILECOPY_ENABLE_CLOUD_DETECTION and FileCopyManager_class._is_cloud_storage_path(path):
                return True
            
            # Layer 3: Symbolic link/junction resolution (if enabled)
            if C.FILECOPY_ENABLE_SYMLINK_RESOLUTION:
                try:
                    resolved_path = os.path.realpath(path)
                    if resolved_path.startswith('\\\\'):  # UNC path
                        return True
                    
                    # Also check resolved path for cloud storage patterns
                    if C.FILECOPY_ENABLE_CLOUD_DETECTION and FileCopyManager_class._is_cloud_storage_path(resolved_path):
                        return True
                        
                except Exception:
                    pass  # Continue with other detection methods
            
            return False
            
        except Exception as e:
            # On detection failure, default to False (use DIRECT strategy)
            log_and_flush(logging.DEBUG, f"Network detection failed for {path}: {e}")
            return False
    
    @staticmethod
    def _is_cloud_storage_path(path: str) -> bool:
        """
        Detect cloud storage folders using configurable pattern matching.
        
        Args:
        -----
        path: File or directory path to check
        
        Returns:
        --------
        bool: True if path appears to be in cloud storage folder
        """
        if not path:
            return False
        
        path_upper = path.upper()
        
        # Check against configured cloud storage patterns
        for pattern in C.FILECOPY_CLOUD_STORAGE_PATTERNS:
            if pattern in path_upper:
                return True
        
        return False

    @staticmethod
    def _is_compression_intended(source_path: str, target_path: str) -> bool:
        """
        Determine whether the copy intends to maintain/enable NTFS compression on the target.
    
        Heuristics per v3 spec (minimal, side-effect free; no writes here):
          - If the source file is compressed -> True
          - OR if the destination folder has compression-default ON -> True
          - Else -> False
    
        Returns:
          bool
        """
        try:
            # Provided by FolderCompareSync_Global_Imports
            compressed_src = is_file_compressed(source_path)[0]
        except Exception:
            compressed_src = None
    
        if compressed_src is True:
            return True
    
        # Destination folder default compression?
        try:
            dst_dir = os.path.dirname(target_path) if target_path else ""
            if dst_dir:
                comp_default = is_folder_compression_default_on(dst_dir)[0]
                if comp_default is True:
                    return True
        except Exception:
            pass
    
        return False

    def _progress_update(self, source_path: str, bytes_done: int, total_bytes: int, strategy_label: str) -> bool:
        """Unified progress hook (simplified): UI+cancel only via progress_manager."""
        try:
            if getattr(self, 'cancel_event', None) and self.cancel_event.is_set():
                return False
        except Exception:
            pass
        try:
            pm = getattr(self, 'progress_manager', None)
            if pm and callable(getattr(pm, 'cancellation_callback', None)) and pm.cancellation_callback():
                return False
        except Exception:
            pass
        try:
            pm = getattr(self, 'progress_manager', None)
            if pm and callable(getattr(pm, 'update_file_progress', None)):
                pm.update_file_progress(source_path, int(bytes_done), int(total_bytes), strategy=strategy_label)
        except Exception:
            pass
        return True

    def copy_file(self, source_path: str, target_path: str) -> FileCopyManager_class.CopyOperationResult:
        """
        Copy with v3 decisioning, sparse fail-fast, and consistent explainer lines.
        """
        start_time = time.time()
    
        # Prepare result shell
        try:
            file_size = Path(source_path).stat().st_size
        except Exception:
            file_size = 0
    
        result = FileCopyManager_class.CopyOperationResult(
            success=False,
            strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,  # placeholder; updated below
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0.0,
        )
    
        # DRY RUN short-circuit still uses decisioning & explainer, but no mutations happen later
        dry_run = getattr(self, "_dry_run", False)
    
        # --------- PRECHECKS (fail fast) ---------
        try:
            sparse = is_sparse_file(source_path)
            if sparse is True:
                # Spec: abort early for SPARSE source
                msg = "abort: SPARSE source detected"
                self._log_status(msg)
                log_and_flush(logging.WARNING, msg)
                result.error_message = msg
                result.strategy_used = FileCopyManager_class.CopyStrategy.DIRECT  # not used; abort path
                result.duration_seconds = time.time() - start_time
                return result
        except Exception as _e_sparse:
            # On detection error, continue cautiously
            log_and_flush(logging.DEBUG, f"sparse precheck skipped ({_e_sparse})")
    
        # Decide base strategy
        strategy = FileCopyManager_class.determine_copy_strategy(source_path, target_path, file_size)
        result.strategy_used = strategy
    
        # Compose explainer string per v3
        threshold = C.FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES
        is_net = False
        try:
            is_net = FileCopyManager_class._is_network_or_cloud_location(source_path)                      or FileCopyManager_class._is_network_or_cloud_location(target_path)
        except Exception:
            pass
    
        compression_intended = False
        try:
            compression_intended = FileCopyManager_class._is_compression_intended(source_path, target_path)
        except Exception:
            pass
    
        if strategy == FileCopyManager_class.CopyStrategy.STAGED:
            if is_net:
                expl = "decision: STAGED (network)"
            elif compression_intended:
                expl = "decision: STAGED (compression-intended)"
            else:
                expl = "decision: STAGED"
        else:
            if file_size >= threshold:
                expl = "decision: DIRECT-LARGE | reason: size>=threshold"
            else:
                expl = "decision: DIRECT-SMALL | reason: size<threshold"
    
        try:
            self._log_status(expl)
            log_and_flush(logging.INFO, expl)
        except Exception:
            pass
    
        if dry_run:
            # Preview-only, no mutations
            result.success = True
            result.duration_seconds = time.time() - start_time
            return result
    
        # Dispatch to executor
        if strategy == FileCopyManager_class.CopyStrategy.STAGED:
            exec_result = self._execute_staged_strategy(source_path, target_path)
        else:
            exec_result = self._execute_direct_strategy(source_path, target_path)
    
        # Bubble up execution result
        exec_result.duration_seconds = time.time() - start_time
        return exec_result
   
    def _execute_direct_strategy(self, source_path: str, target_path: str) -> FileCopyManager_class.CopyOperationResult:
        """
        DIRECT strategy implementation per v3:
          - DIRECT-SMALL  (size < C.FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES): CopyFileExW to temp
          - DIRECT-LARGE  (size >= threshold): windowed mmap copy to temp with best-effort preallocation
        Progress: uses self._progress_update(...) across both branches.
        """
        # Shell result
        try:
            file_size = Path(source_path).stat().st_size
        except Exception:
            file_size = 0
    
        result = FileCopyManager_class.CopyOperationResult(
            success=False,
            strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0.0,
            bytes_copied=0
        )
    
        start_time = time.time()
        temp_file_path = None
        backup_path = None
    
        try:
            # Phase 1: Preflight (timestamps only; sparse already fail-fast in copy_file)
            source_ts = None
            try:
                source_ts = self.timestamp_manager.get_file_timestamps(source_path)
            except Exception:
                pass
    
            # Phase 2: Prepare secure temp path
            target_dir = Path(target_path).parent
            target_dir.mkdir(parents=True, exist_ok=True)
            temp_file_path = str(Path(target_path).with_suffix(Path(target_path).suffix + ".tmp_copy"))
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception:
                pass
    
            # Phase 3: Perform copy based on size split
            threshold = C.FILECOPY_DIRECT_MMAP_COPY_THRESHOLD_BYTES
            if file_size >= threshold:
                # DIRECT-LARGE: mmap copy (handles preallocation and hashing inside)
                copy_info = self._copy_by_mmap_windows(source_path, temp_file_path, file_size)
                if not copy_info.get("success"):
                    # Cleanup temp on failure
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = copy_info.get("error", "DIRECT-LARGE copy failed")
                    result.cancelled_by_user = copy_info.get("cancelled", False)
                    result.recovery_suggestion = copy_info.get("recovery_suggestion", "Check permissions/disk space")
                    return result
                result.bytes_copied = copy_info.get("bytes_copied", 0)
                result.hash_algorithm = copy_info.get("hash_algorithm", "BLAKE3" if getattr(self, "blake3_available", False) else "SHA-256")
                result.verification_mode = "hash on the fly"  # per spec for DIRECT-LARGE
                result.computed_hash = copy_info.get("hash")
            else:
                # DIRECT-SMALL: CopyFileExW to temp with restartable flag and progress callback
                cancel_flag = wintypes.BOOL(False)
    
                @ctypes.WINFUNCTYPE(wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE, wintypes.HANDLE, wintypes.LPVOID)
                def callback_func(
                    TotalFileSize, TotalBytesTransferred, StreamSize, StreamBytesTransferred,
                    dwStreamNumber, dwCallbackReason, hSourceFile, hDestinationFile, lpData
                ):
                    try:
                        tb = int(TotalBytesTransferred) if TotalBytesTransferred else 0
                        ts = int(TotalFileSize) if TotalFileSize else (result.file_size or 0)
                        # unified progress hook; False => cancel
                        cont = self._progress_update(source_path, tb, ts, "DIRECT-SMALL")
                        return win32con.PROGRESS_CONTINUE if cont else win32con.PROGRESS_CANCEL
                    except Exception:
                        return win32con.PROGRESS_CONTINUE
    
                ok = kernel32.CopyFileExW(
                    ctypes.c_wchar_p(source_path),
                    ctypes.c_wchar_p(temp_file_path),
                    callback_func,
                    None,
                    ctypes.byref(cancel_flag),
                    win32con.COPY_FILE_RESTARTABLE
                )
    
                if not ok or bool(cancel_flag.value):
                    # Cleanup temp on failure
                    self._cleanup_temp_file(temp_file_path)
                    if bool(cancel_flag.value):
                        result.cancelled_by_user = True
                        result.error_message = "Copy cancelled by user"
                        return result
                    err = kernel32.GetLastError()
                    result.error_message = f"CopyFileExW failed ({err}: {format_last_error(err)})"
                    result.recovery_suggestion = "Check file locks/permissions and retry"
                    return result
    
                result.bytes_copied = file_size
                result.hash_algorithm = None
                result.verification_mode = "mmap compare bytes"
    
            # Phase 4: Optional verification happens elsewhere
    
            # Phase 5: Atomic placement
            if os.path.exists(target_path):
                backup_path = target_path + ".bak"
                try:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                except Exception:
                    pass
                try:
                    os.replace(target_path, backup_path)
                except Exception as e:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = f"backup/replace failed: {e}"
                    result.recovery_suggestion = "Check permissions/locks and retry"
                    return result
    
            try:
                os.replace(temp_file_path, target_path)
            except Exception as e:
                # Try rollback
                try:
                    if backup_path and os.path.exists(backup_path):
                        os.replace(backup_path, target_path)
                except Exception:
                    pass
                self._cleanup_temp_file(temp_file_path)
                result.error_message = f"finalize failed: {e}"
                result.recovery_suggestion = "Check permissions/locks and retry"
                return result
    
            # Phase 6: Restore timestamps
            try:
                self.timestamp_manager.copy_timestamps(source_path, target_path) if hasattr(self, "timestamp_manager") else FileTimestampManager_class.apply_timestamps_safe(target_path, source_ts)
            except Exception:
                pass
    
            result.success = True
            result.duration_seconds = time.time() - start_time
            return result
    
        except Exception as e:
            result.error_message = str(e)
            result.recovery_suggestion = "Check permissions/disk space"
            result.duration_seconds = time.time() - start_time
            return result
    
    def _execute_staged_strategy(self, source_path: str, target_path: str) -> FileCopyManager_class.CopyOperationResult:
        """
        STAGED: chunked copy with progressive hashing; if compression intended, enable it
        on the *existing* temp file (create zero-length file first), then copy.
    
        Progress: we use self._progress_update(source_path, done, total, "STAGED") at start/end.
        (Per-chunk progress depends on _copy_with_progressive_hash implementation and is not changed here.)
        """
        # Shell result
        try:
            file_size = Path(source_path).stat().st_size
        except Exception:
            file_size = 0
    
        result = FileCopyManager_class.CopyOperationResult(
            success=False,
            strategy_used=FileCopyManager_class.CopyStrategy.STAGED,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0.0,
        )
    
        temp_file_path = None
        backup_path = None
    
        try:
            # 1) Preflight, timestamps capture
            source_timestamps = self.timestamp_manager.get_file_timestamps(source_path)
            target_timestamps = self.timestamp_manager.get_file_timestamps(target_path) if os.path.exists(target_path) else None
    
            # Pre-progress (0%); allow early cancel
            if not self._progress_update(source_path, 0, file_size, "STAGED"):
                result.cancelled_by_user = True
                result.error_message = "Copy cancelled by user"
                return result
    
            # 2) Temp path + ensure parent dir
            temp_file_path = str(Path(target_path).with_suffix(Path(target_path).suffix + ".tmp_copy"))
            Path(temp_file_path).parent.mkdir(parents=True, exist_ok=True)
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass
    
            # 2a) Create the temp file so compression FSCTL has a handle
            try:
                open(temp_file_path, "wb").close()
            except Exception:
                pass
    
            # 2b) Compression intent -> try FSCTL on temp, but DO NOT abort on failure
            try:
                if self._is_compression_intended(source_path, target_path):
                    ok, err, msg = set_file_compression(temp_file_path, enable=True)
                    if ok is True:
                        self._log_status("compression: enabled on temp (FSCTL_SET_COMPRESSION)")
                        log_and_flush(logging.INFO, "compression: enabled on temp (FSCTL_SET_COMPRESSION)")
                    else:
                        self._log_status("override: proceeding uncompressed (compression enable failed)")
                        log_and_flush(logging.INFO, f"override: proceeding uncompressed (compression enable failed; err={err} msg={msg})")
            except Exception as _e_comp:
                self._log_status("override: proceeding uncompressed (compression enable exception)")
                log_and_flush(logging.INFO, f"override: proceeding uncompressed (compression enable exception: {_e_comp})")
    
            # 3) Chunked copy with progressive source hashing
            copy_result = self._copy_with_progressive_hash(source_path, temp_file_path)
            if not copy_result.get("success"):
                # Cleanup temp on failure
                self._cleanup_temp_file(temp_file_path)
                result.error_message = copy_result.get("error", "Copy failed")
                result.cancelled_by_user = copy_result.get("cancelled", False)
                if result.cancelled_by_user:
                    result.recovery_suggestion = "No changes were made. You can retry the file later."
                else:
                    result.recovery_suggestion = copy_result.get("recovery_suggestion", "")
                return result
    
            result.bytes_copied = copy_result.get("bytes_copied", 0)
            result.hash_algorithm = "BLAKE3" if getattr(self, "blake3_available", False) else "SHA-256"
            result.verification_mode = "hash on the fly"
            result.computed_hash = copy_result.get("hash")
    
            # Post-progress (100%)
            self._progress_update(source_path, result.bytes_copied or file_size, file_size, "STAGED")
    
            # 4) Atomic placement (rename, with backup if target exists)
            if os.path.exists(target_path):
                backup_path = target_path + ".bak"
                try:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                except Exception:
                    pass
                try:
                    os.replace(target_path, backup_path)
                except Exception as e:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = f"backup/replace failed: {e}"
                    result.recovery_suggestion = "Check permissions/locks and retry"
                    return result
    
            try:
                os.replace(temp_file_path, target_path)
            except Exception as e:
                # Try rollback
                try:
                    if backup_path and os.path.exists(backup_path):
                        os.replace(backup_path, target_path)
                except Exception:
                    pass
                self._cleanup_temp_file(temp_file_path)
                result.error_message = f"finalize failed: {e}"
                result.recovery_suggestion = "Check permissions/locks and retry"
                return result
    
            # 5) Restore timestamps
            try:
                self.timestamp_manager.copy_timestamps(source_path, target_path)
            except Exception:
                pass
    
            result.success = True
            return result
    
        except Exception as e:
            result.error_message = str(e)
            return result

    def _copy_by_mmap_windows(self, source_path: str, temp_path: str, file_size: int) -> dict:
        """
        DIRECT-LARGE path: windowed mmap copy with safe, non-fatal pre-allocation.
    
        Progress: uses self._progress_update(source_path, bytes_copied, total, "DIRECT-LARGE").
        """
        log_and_flush(logging.DEBUG, f"_copy_by_mmap_windows: Entered function")
        # ---- Try to pre-create & grow the destination for mmap use
        prealloc_ok = False
        file_handle = None
        try:
            # Ensure parent directory exists
            Path(temp_path).parent.mkdir(parents=True, exist_ok=True)
    
            # Create/overwrite the temp file via CreateFileW (HANDLE-safe binding)
            log_and_flush(logging.DEBUG, f"[DIAG BEFORE Pre-allocating temp file] kernel32.CreateFileW")
            file_handle = kernel32.CreateFileW(
                ctypes.c_wchar_p(temp_path),
                wintypes.DWORD(win32con.GENERIC_READ | win32con.GENERIC_WRITE | win32con.FILE_WRITE_DATA ),
                wintypes.DWORD(win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE),
                None,
                wintypes.DWORD(win32con.CREATE_ALWAYS),
                wintypes.DWORD(win32con.FILE_ATTRIBUTE_NORMAL),
                None
            )
    
            if file_handle in (0, win32file.INVALID_HANDLE_VALUE):
                err = kernel32.GetLastError()
                log_and_flush(logging.INFO, f"prealloc: CreateFileW failed ({err}: {format_last_error(err)}); will fall back to buffered dest writes")
            else:
                log_and_flush(logging.DEBUG, f"[DIAG AFTER Pre-allocating temp file] kernel32.CreateFileW Created file with handle: {file_handle}")
                # Build FILE_ALLOCATION_INFO using the shared struct from Global_Imports
                alloc = FILE_ALLOCATION_INFO()
                alloc.AllocationSize.QuadPart = int(file_size)
                log_and_flush(logging.DEBUG, f"Setting allocation size to: {file_size:,} bytes")
                log_and_flush(logging.DEBUG, f"QuadPart value: {alloc.AllocationSize.QuadPart}")
    
                ok = False
                try:
                    ok = kernel32.SetFileInformationByHandle(
                        wintypes.HANDLE(file_handle),
                        wintypes.DWORD(win32file.FileAllocationInfo),
                        ctypes.byref(alloc),
                        wintypes.DWORD(ctypes.sizeof(alloc))
                    )
                except Exception as e:
                    err = kernel32.GetLastError()
                    log_and_flush(logging.INFO, f"prealloc: SetFileInformationByHandle exception: {e} ({err}: {format_last_error(err)})")
                    ok = False
    
                if not ok:
                    err1 = kernel32.GetLastError()
                    log_and_flush(logging.INFO, f"prealloc: SetFileInformationByHandle not supported/failed ({err1}: {format_last_error(err1)}); trying SetFilePointerEx + SetEndOfFile")
                    # As a secondary attempt, try SetFilePointerEx + SetEndOfFile (no raise; explicit checks)
                    new_pos = LARGE_INTEGER()
                    new_pos.QuadPart = 0  # explicit init to mirror old behavior
                    moved = kernel32.SetFilePointerEx(
                        wintypes.HANDLE(file_handle),
                        LARGE_INTEGER(int(file_size)),  # liDistanceToMove
                        ctypes.byref(new_pos),          # lpNewFilePointer (out)
                        win32con.FILE_BEGIN
                        )
                    if not moved:
                        err2 = kernel32.GetLastError()
                        log_and_flush(logging.INFO, f"prealloc: SetFilePointerEx failed ({err2}: {format_last_error(err2)})")
                        ok = False
                    else:
                        ended = kernel32.SetEndOfFile(wintypes.HANDLE(file_handle))
                        if not ended:
                            err3 = kernel32.GetLastError()
                            log_and_flush(logging.INFO, f"prealloc: SetEndOfFile failed ({err3}: {format_last_error(err3)})")
                            ok = False
                        else:
                            ok = True
    
                prealloc_ok = bool(ok)
                if prealloc_ok:
                    log_and_flush(logging.INFO, f"prealloc: destination grown to {file_size:,} bytes (OK)")
        except Exception as e:
            log_and_flush(logging.INFO, f"prealloc: skipped due to exception: {e}")
        finally:
            if file_handle not in (None, 0, win32file.INVALID_HANDLE_VALUE):
                try:
                    kernel32.CloseHandle(wintypes.HANDLE(file_handle))
                except Exception:
                    pass
    
        # ---- Perform copy: mmap src; mmap dest if prealloc_ok, else buffered dest writes
        if prealloc_ok:
            log_and_flush(logging.DEBUG, f"_copy_by_mmap_windows: pre-Allocation of disk space OK, will use mmap READ source, mmap WRITE target")
        else:
            log_and_flush(logging.DEBUG, f"_copy_by_mmap_windows: pre-Allocation of disk space FAILED, will use mmap READ source, chunked (buffered) WRITE target")
    
        bytes_copied = 0
        cancelled = False
        try:
            window = C.FILECOPY_MMAP_WINDOW_BYTES
            hasher = blake3.blake3() if getattr(self, "blake3_available", False) else hashlib.sha256()
            copy_type = "DIRECT-LARGE mmap" if prealloc_ok else "DIRECT-LARGE chunked (buffered)"
            log_and_flush(logging.DEBUG, f"Start '{copy_type}' copying to temp file '{temp_path}' {file_size:,} bytes")
            with open(source_path, "rb") as sf:
                tf = open(temp_path, "r+b") if prealloc_ok else open(temp_path, "wb")
                try:
                    dst_fd = tf.fileno()
                    src_fd = sf.fileno()
                    offset = 0
                    gran = mmap.ALLOCATIONGRANULARITY
                    while offset < file_size:
                        # async cancel checks
                        if not self._progress_update(source_path, bytes_copied, file_size, "DIRECT-LARGE"):
                            cancelled = True
                            break
    
                        remaining = file_size - offset
                        length = window if remaining > window else remaining
                        base = (offset // gran) * gran
                        shift = offset - base
                        maplen = shift + length
                        with mmap.mmap(src_fd, length=maplen, access=mmap.ACCESS_READ, offset=base) as sm:
                            view = memoryview(sm)
                            try:
                                # Update hash with window slice
                                if shift == 0 and length == maplen:
                                    hasher.update(view)
                                    src_bytes = view
                                else:
                                    hasher.update(view[shift:shift+length])
                                    src_bytes = view[shift:shift+length]
    
                                if prealloc_ok:
                                    with mmap.mmap(dst_fd, length=maplen, access=mmap.ACCESS_WRITE, offset=base) as dm:
                                        dm[shift:shift+length] = src_bytes
                                        dm.flush()
                                else:
                                    tf.write(src_bytes)
                            finally:
                                view.release()
    
                        offset += length
                        bytes_copied = offset
    
                        # report progress and allow user-cancel
                        if not self._progress_update(source_path, bytes_copied, file_size, "DIRECT-LARGE"):
                            cancelled = True
                            break
    
                    if not prealloc_ok:
                        tf.flush()
                        try:
                            os.fsync(dst_fd)
                        except Exception:
                            pass
                finally:
                    try:
                        tf.close()
                    except Exception:
                        pass
            if cancelled:
                log_and_flush(logging.INFO, "copy cancelled by user during DIRECT-LARGE")
                return {"success": False, "cancelled": True, "bytes_copied": bytes_copied}
            return {"success": True, "bytes_copied": bytes_copied, "hash": hasher.hexdigest(), "hash_algorithm": ("BLAKE3" if getattr(self, "blake3_available", False) else "SHA-256")}
        except Exception as e:
            return {"success": False, "error": str(e), "bytes_copied": bytes_copied, "recovery_suggestion": "Check permissions/disk space"}

    def _copy_with_windows_api(self, source_path: str, temp_path: str) -> dict:
        """
        Windows CopyFileExW implementation with progress callbacks and cancellation.
        
        Args:
        -----
        source_path: Source file path
        temp_path: Temporary target file path
        
        Returns:
        --------
        dict: Copy result with success status, bytes copied, and error information
        """
        # >>> CHANGE START: DEBUG preamble for DIRECT-SMALL (CopyFileExW)
        if __debug__:
            try:
                _sz = Path(source_path).stat().st_size
            except Exception:
                _sz = -1
            if os.path.exists(source_path):
                source_exists = "exists"
            else:
                source_exists = "NOT exists"
            if os.path.exists(temp_path):
                temp_path_exists = "exists"
            else:
                temp_path_exists = "NOT exists"
            log_and_flush(
                logging.DEBUG,
                f"[DIRECT-SMALL] Starting CopyFileExW: src='{source_path}' {source_exists}, temp='{temp_path}' {temp_path_exists}, "
                f"size={_sz if _sz >= 0 else 'unknown'} bytes, verify_policy={getattr(C, 'FILECOPY_VERIFY_POLICY', 'n/a')}"
            )
        # <<< CHANGE END

        # Progress + cancel wiring for DIRECT (CopyFileExW) # per chatGPT change 1.2
        cancel_flag = wintypes.BOOL(0)  # module-level global, LPBOOL for CopyFileExW
        
        def copy_progress_callback(total_size, transferred, stream_size, 
                                  stream_transferred, stream_num, reason,
                                  src_handle, dst_handle, user_data):
            """Windows progress callback - called by OS during copy operation."""
            # 1) Cancellation: Event from UI or progress manager
            if getattr(self, "cancel_event", None) and self.cancel_event.is_set():
                return win32con.PROGRESS_CANCEL
            pm = getattr(self, "progress_manager", None)
            if pm and callable(getattr(pm, "cancellation_callback", None)) and pm.cancellation_callback():
                return win32con.PROGRESS_CANCEL

            # 2) Per-file progress to UI (throttling handled by UI)
            if pm and hasattr(pm, "update_file_progress"):
                try:
                    pm.update_file_progress(source_path, transferred, total_size, strategy="DIRECT")
                except Exception:
                    pass  # Never fail the copy on UI update
            elif self.status_callback:
                if total_size > 0:
                    pct = (transferred / total_size) * 100
                    if transferred > 0:
                        self.status_callback(f"Copying: {pct:.1f}% ({transferred:,} bytes)")

            if __debug__ and total_size:
                try:
                    _mb_done = transferred / (1024 * 1024)
                    _mb_total = total_size / (1024 * 1024)
                    log_and_flush(logging.DEBUG, f"[DIRECT...CopyFileExW progress: {_mb_done:.1f} MB of {_mb_total:.1f} MB")
                except Exception:
                    pass

            return win32con.PROGRESS_CONTINUE
        
        # Create callback wrapper for Windows
        callback_func = PROGRESS_ROUTINE(copy_progress_callback)
        
        try:
            # Ensure dest folder exists for both CopyFileExW and mmap paths
            try:
                Path(temp_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                result.error_message = f"Unable to create destination directory '{target_dir}': {e}"
                result.recovery_suggestion = "Check permissions and path validity for the destination folder"
                result.success = False
                result.error_code = e
                return result
            # Execute Windows CopyFileExW
            result = kernel32.CopyFileExW(
                ctypes.c_wchar_p(source_path),
                ctypes.c_wchar_p(temp_path), 
                callback_func,
                None,                                    # No user data
                ctypes.byref(cancel_flag),               # Cancel flag
                win32con.COPY_FILE_RESTARTABLE          # Restartable if interrupted
            )
            
            if not result:
                error_code = kernel32.GetLastError()
                if error_code == winerror.ERROR_REQUEST_ABORTED:
                    return {
                        'success': False, 
                        'cancelled': True, 
                        'error': f"Copy operation cancelled by user '{source_path}' to '{temp_path}'",
                        'error_code': error_code
                    }
                else:
                    error_msg = format_last_error(error_code)
                    error_recovery = self._get_recovery_suggestion_for_error(error_code)
                    return {
                        'success': False, 
                        'error': f"CopyFileExW failed: '{source_path}' to '{temp_path}' {error_msg}",
                        'error_code': error_code,
                        'recovery_suggestion': error_recovery
                    }
            
            # DEBUG summary for DIRECT-SMALL (CopyFileExW)
            try:
                _elapsed = time.time() - start_time if 'start_time' in locals() else None
            except Exception:
                _elapsed = None
            bytes_copied = Path(source_path).stat().st_size
            if __debug__ and (bytes_copied is not None) and _elapsed:
                _mb = bytes_copied / (1024 * 1024)
                _mbps = (_mb / _elapsed) if _elapsed > 0 else 0.0
                log_and_flush(logging.DEBUG, f"[DIRECT-SMALL] CopyFileExW done: {_mb:.1f} MB in {_elapsed:.2f}s ({_mbps:.1f} MB/s)")

            return {
                'success': True, 
                'bytes_copied': bytes_copied
            }
            
        except Exception as e:
            return {
                'success': False, 
                'error': f"Windows API call failed: {str(e)}",
                'recovery_suggestion': "Check file paths and permissions"
            }
    
    def _copy_with_progressive_hash(self, source_path: str, temp_path: str) -> dict:
        """
        STAGED copy path: chunked copy with progressive hash calculation and
        per-chunk progress updates for both copy and verification (second bar).
    
        Behavior (aligned to simplification plan):
          - Uses only progress_manager + cancel_event for progress/cancel.
          - Calls _progress_update(...) for copy bar.
          - Calls progress_manager.update_verify_progress(...) for verify bar, in lockstep with hashing.
          - Returns a dict with success, bytes_copied, hash, and hash_algorithm.
        """
        try:
            import os
            import hashlib
    
            # Determine source size for progress
            try:
                file_size = os.path.getsize(source_path)
            except Exception:
                file_size = 0
    
            # Chunk sizing from globals
            chunk_size = C.FILECOPY_NETWORK_CHUNK_BYTES
    
            # Hash setup
            hasher = blake3.blake3() if getattr(self, "blake3_available", False) else hashlib.sha256()
            hash_algo = "BLAKE3" if getattr(self, "blake3_available", False) else "SHA-256"
    
            bytes_copied = 0
    
            # Open both files and stream
            with open(source_path, 'rb') as src_file, open(temp_path, 'wb') as temp_file:
                while True:
                    # Cancellation checks (event + UI)
                    if getattr(self, "cancel_event", None) and self.cancel_event.is_set():
                        return {'success': False, 'cancelled': True, 'bytes_copied': bytes_copied, 'error': "Copy operation cancelled by user"}
                    pm = getattr(self, "progress_manager", None)
                    if pm and callable(getattr(pm, "cancellation_callback", None)) and pm.cancellation_callback():
                        return {'success': False, 'cancelled': True, 'bytes_copied': bytes_copied, 'error': "Copy operation cancelled by user"}
    
                    chunk = src_file.read(chunk_size)
                    if not chunk:
                        break
    
                    # Hash & write
                    hasher.update(chunk)
                    temp_file.write(chunk)
                    bytes_copied += len(chunk)
    
                    # Report per-chunk progress
                    # - Copy progress via unified hook
                    if not self._progress_update(source_path, bytes_copied, file_size, "STAGED (hash on the fly)"):
                        return {'success': False, 'cancelled': True, 'bytes_copied': bytes_copied, 'error': "Copy operation cancelled by user"}
    
                    # - Verify progress via manager's second bar
                    try:
                        pm = getattr(self, "progress_manager", None)
                        if pm and callable(getattr(pm, "update_verify_progress", None)):
                            pm.update_verify_progress(bytes_copied, file_size)
                    except Exception:
                        # Never fail copy due to UI issues
                        pass
    
                # Ensure buffered writes hit disk
                try:
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                except Exception:
                    pass
    
            return {
                'success': True,
                'bytes_copied': bytes_copied,
                'hash': hasher.hexdigest(),
                'hash_algorithm': hash_algo
            }
    
        except Exception as e:
            return {
                'success': False,
                'bytes_copied': locals().get("bytes_copied", 0),
                'error': str(e),
                'recovery_suggestion': "Check permissions, disk space, and paths"
            }
    
    def _verify_by_mmap_windows(self, source_path: str, temp_path: str) -> bool:
        """
        Memory-mapped window verification for DIRECT strategy with intelligent fallback.
        
        Purpose:
        --------
        High-performance local file verification using OS-optimized memory mapping
        with automatic fallback to buffered comparison on mmap failures.
        
        Args:
        -----
        source_path: Source file path
        temp_path: Temporary file path to verify
        
        Returns:
        --------
        bool: True if files match, False otherwise
        """
        try:
            # Quick pre-check: compare file sizes
            source_size = Path(source_path).stat().st_size
            temp_size = Path(temp_path).stat().st_size
            
            if source_size != temp_size:
                self._log_status(f"Verification failed: Size mismatch ({source_size} vs {temp_size})")
                return False
            
            if source_size == 0:
                return True  # Empty files match
            
            window_size = C.FILECOPY_MMAP_WINDOW_BYTES
            consecutive_failures = 0
            
            with open(source_path, 'rb') as src_file, open(temp_path, 'rb') as temp_file:
                offset = 0
                
                while offset < source_size:
                    # >>> CHANGE START: cancel + progress for verify (DIRECT) # per chatGPT change 1.4
                    if getattr(self, "cancel_event", None) and self.cancel_event.is_set():
                        self._log_status("User cancelled during verification (DIRECT)")
                        return False
                    pm = getattr(self, "progress_manager", None)
                    if pm and callable(getattr(pm, "cancellation_callback", None)) and pm.cancellation_callback():
                        self._log_status("User cancelled during verification (DIRECT)")
                        return False
                    if pm and hasattr(pm, "update_verify_progress"):
                        try:
                            pm.update_verify_progress(offset, source_size)
                        except Exception:
                            pass
                    # <<< CHANGE END
                    # >>> CHANGE START: DEBUG verify window progress
                    if __debug__ and source_size:
                        _mb_done = offset / (1024*1024)
                        _mb_total = source_size / (1024*1024)
                        log_and_flush(logging.DEBUG, f"[DIRECT VERIFY/mmap] {_mb_done:.1f} MB of {_mb_total:.1f} MB")
                    # <<< CHANGE END
                    current_window_size = min(window_size, source_size - offset)
                    try:
                        # Try memory mapping for this window
                        with mmap.mmap(src_file.fileno(), current_window_size, offset=offset, access=mmap.ACCESS_READ) as src_map:
                            with mmap.mmap(temp_file.fileno(), current_window_size, offset=offset, access=mmap.ACCESS_READ) as temp_map:
                                if src_map[:] != temp_map[:]:
                                    self._log_status(f"Verification failed: Content mismatch at offset {offset}")
                                    return False
                        
                        consecutive_failures = 0  # Reset failure counter on success
                        
                    except (OSError, ValueError) as e:
                        # Memory mapping failed - use buffered fallback for this window
                        consecutive_failures += 1
                        self._log_status(f"Memory mapping failed at offset {offset}, using buffered fallback: {e}")
                        
                        if consecutive_failures > C.FILECOPY_MMAP_FALLBACK_MAX_CONSECUTIVE_FAILURES:
                            self._log_status(f"Too many consecutive mmap failures ({consecutive_failures}), aborting verification")
                            return False
                        
                        # Buffered comparison for this window
                        src_file.seek(offset)
                        temp_file.seek(offset)
                        
                        src_data = src_file.read(current_window_size)
                        temp_data = temp_file.read(current_window_size)
                        
                        if src_data != temp_data:
                            self._log_status(f"Verification failed: Content mismatch at offset {offset} (buffered)")
                            return False
                    
                    offset += current_window_size
                    
                    # # DEBUG: Uncomment for detailed window verification tracking
                    # if offset % (window_size * 4) == 0:  # Every 4 windows
                    #     progress = offset / source_size * 100
                    #     log_and_flush(logging.DEBUG, f"Verification progress: {progress:.1f}% ({offset:,} bytes)")
            
            self._log_status(f"Memory-mapped verification completed successfully")
            return True
            
        except Exception as e:
            self._log_status(f"Verification error: {str(e)}")
            return False
    
    def _verify_by_hash_comparison(self, temp_path: str, expected_hash: str, algorithm: str) -> bool:
        """
        Hash-based verification for STAGED strategy with chunked I/O.
        
        Args:
        -----
        temp_path: Temporary file path to verify
        expected_hash: Expected hash from source file
        algorithm: Hash algorithm used (BLAKE3/SHA-256)
        
        Returns:
        --------
        bool: True if hashes match, False otherwise
        """
        try:
            # Initialize hasher based on algorithm
            if algorithm == "BLAKE3" and self.blake3_available:
                hasher = blake3.blake3()
            else:
                hasher = hashlib.sha256()
            
            chunk_size = C.FILECOPY_NETWORK_CHUNK_BYTES
            bytes_processed = 0

            # >>> CHANGE START: progress + cancel wiring for STAGED verify (hash) # per chatGPT change 3 re-done
            try:
                total_size = Path(temp_path).stat().st_size
            except Exception:
                total_size = 0  # fallback if stat fails

            pm = getattr(self, "progress_manager", None)
            # <<< CHANGE END
            
            with open(temp_path, 'rb') as temp_file:
                while True:
                    # >>> CHANGE START: allow responsive cancellation # per chatGPT change 3 re-done
                    if getattr(self, "cancel_event", None) and self.cancel_event.is_set():
                        self._log_status("User cancelled during verification (STAGED)")
                        log_and_flush(logging.WARNING, f"WARNING: User cancelled during verification (STAGED)")
                        return False
                    if pm and callable(getattr(pm, "cancellation_callback", None)) and pm.cancellation_callback():
                        self._log_status("User cancelled (progress manager) during verification (STAGED)")
                        log_and_flush(logging.WARNING, f"WARNING: User cancelled (progress manager) during verification (STAGED)")
                        return False
                    # <<< CHANGE END

                    chunk = temp_file.read(chunk_size)
                    if not chunk:
                        break
                    
                    hasher.update(chunk)
                    bytes_processed += len(chunk)

                    # >>> CHANGE START: emit verify progress to UI # per chatGPT change 3 re-done
                    if pm and hasattr(pm, "update_verify_progress"):
                        try:
                            pm.update_verify_progress(bytes_processed, total_size or bytes_processed)
                            #mb_processed = bytes_processed / (1024 * 1024)
                            #mb_total_size = (total_size or bytes_processed) / (1024 * 1024)
                            #log_and_flush(logging.DEBUG, f"Verify Progress (STAGED) {mb_processed} MB of {mb_total_size} MB")
                        except Exception:
                            pass
                    # <<< CHANGE END

            # >>> CHANGE START: final 100% progress tick after loop # per chatGPT change 3 re-done
            if pm and hasattr(pm, "update_verify_progress"):
                try:
                    pm.update_verify_progress(total_size or bytes_processed, total_size or bytes_processed)
                    #mb_processed = bytes_processed / (1024 * 1024)
                    #mb_total_size = (total_size or bytes_processed) / (1024 * 1024)
                    #log_and_flush(logging.DEBUG, f"Verify Progress (STAGED) {mb_processed} MB of {mb_total_size} MB")
                except Exception:
                    pass
            # <<< CHANGE END
            
            computed_hash = hasher.hexdigest()
            
            # Secure hash comparison
            matches = computed_hash == expected_hash
            
            if matches:
                self._log_status(f"Hash verification successful ({algorithm})")
            else:
                self._log_status(f"Hash verification failed: {algorithm} hashes do not match")
                self._log_status(f"Expected: {expected_hash[:32]}...")
                self._log_status(f"Computed: {computed_hash[:32]}...")
            
            return matches
            
        except Exception as e:
            self._log_status(f"Hash verification error: {str(e)}")
            return False
    
    def _should_verify_file(self, file_size: int) -> bool:
        """
        Determine if file should be verified based on verification policy (M04).
        
        Args:
        -----
        file_size: Size of file in bytes
        
        Returns:
        --------
        bool: True if file should be verified
        """
        verify_policy = C.FILECOPY_VERIFY_POLICY
        
        if verify_policy.lower() == 'none'.lower():
            return False
        elif verify_policy.lower() == 'lt_threshold'.lower():
            return file_size < C.FILECOPY_VERIFY_THRESHOLD_BYTES
        elif verify_policy.lower() == 'all'.lower():
            return True
        else:
            # Safety default: verify everything if policy is corrupted
            return True
    
    def _get_verification_mode(self) -> str:
        """Get current verification mode as string."""
        return C.FILECOPY_VERIFY_POLICY
    
    def _check_sufficient_disk_space(self, source_path: str, target_path: str) -> bool:
        """
        Check if there is sufficient disk space for the copy operation.
        
        Args:
        -----
        source_path: Source file path
        target_path: Target file path
        
        Returns:
        --------
        bool: True if sufficient space available
        """
        try:
            source_size = Path(source_path).stat().st_size
            target_dir = Path(target_path).parent
            
            # Calculate space needed (source + safety margin + existing target if present)
            space_needed = source_size + C.FILECOPY_FREE_DISK_SPACE_MARGIN
            if Path(target_path).exists():
                space_needed += Path(target_path).stat().st_size
            
            # Get available space
            drive = str(target_dir.drive) + '\\' if target_dir.drive else str(target_dir) + '\\'
            
            free_bytes = ctypes.c_ulonglong()
            result = kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(drive),
                ctypes.byref(free_bytes),
                None, None
            )
            
            if not result:
                self._log_status(f"Warning: Could not check disk space for {drive}")
                return True  # Proceed if we can't check
            
            available = free_bytes.value
            
            if available < space_needed:
                shortage = space_needed - available
                self._log_status(f"Insufficient disk space: need {space_needed:,} bytes, have {available:,} bytes (shortage: {shortage:,} bytes)")
                return False
            
            return True
            
        except Exception as e:
            self._log_status(f"Warning: Disk space check failed: {e}")
            return True  # Proceed if check fails
    
    def _cleanup_temp_file(self, temp_path: str):
        """Safely remove temporary file if it exists."""
        try:
            if temp_path and Path(temp_path).exists():
                os.remove(temp_path)
                # # DEBUG: Uncomment for temp file cleanup tracking
                # log_and_flush(logging.DEBUG, f"Cleaned up temporary file: {temp_path}")
        except Exception as e:
            self._log_status(f"Warning: Could not remove temporary file {temp_path}: {e}")
    
    def _perform_secure_rollback(self, temp_path: str, backup_path: str, 
                               target_path: str, original_timestamps: tuple, error_msg: str) -> bool:
        """
        Secure rollback procedure with guaranteed original file preservation (M05, M10).
        
        Args:
        -----
        temp_path: Temporary file path to clean up
        backup_path: Backup file path (if exists)
        target_path: Target file path
        original_timestamps: Original target timestamps (if exists)
        error_msg: Original error message
        
        Returns:
        --------
        bool: True if rollback successful
        """
        self._log_status(f"Beginning secure rollback due to: {error_msg}")
        rollback_success = True
        
        try:
            # Step 1: Always cleanup temporary file
            if temp_path:
                self._cleanup_temp_file(temp_path)
                self._log_status(f"Temporary file cleaned up: {temp_path}")
            
            # Step 2: Restore original target if we moved it
            if backup_path and Path(backup_path).exists():
                if not Path(target_path).exists():
                    # Target missing - restore from backup
                    os.rename(backup_path, target_path)  # Atomic restore
                    self._log_status(f"Original file restored from backup: {backup_path} -> {target_path}")
                    
                    # Restore original timestamps
                    if original_timestamps:
                        try:
                            self.timestamp_manager.set_file_timestamps(target_path, *original_timestamps)
                            self._log_status(f"Original timestamps restored")
                        except Exception as e:
                            self._log_status(f"Warning: Could not restore timestamps: {e}")
                else:
                    # Target exists (atomic operations succeeded) - just cleanup backup
                    os.remove(backup_path)
                    self._log_status(f"Backup file removed: {backup_path}")
            
            self._log_status("Secure rollback completed successfully")
            
        except Exception as rollback_error:
            self._log_status(f"CRITICAL: Rollback error: {rollback_error}")
            rollback_success = False
        
        return rollback_success
    
    def _get_windows_error_message(self, error_code: int) -> str:
        """Get human-readable Windows error message."""
        # >>> CHANGE START: use standard winerror.* symbols
        error_messages = {
            winerror.ERROR_SUCCESS: "Success",
            winerror.ERROR_REQUEST_ABORTED: "Operation cancelled by user",
            winerror.ERROR_DISK_FULL: "Insufficient disk space",
            winerror.ERROR_HANDLE_DISK_FULL: "Disk full",
            winerror.ERROR_NOT_ENOUGH_MEMORY: "Insufficient memory",
            winerror.ERROR_ACCESS_DENIED: "Access denied",
            winerror.ERROR_FILE_NOT_FOUND: "File not found",
            winerror.ERROR_PATH_NOT_FOUND: "Path not found",
            winerror.ERROR_FILE_EXISTS: "File already exists",
            winerror.ERROR_ALREADY_EXISTS: "File already exists",
        }
        return error_messages.get(error_code, f"Windows error {error_code}")
    
    def _get_recovery_suggestion_for_error(self, error_code: int) -> str:
        """Get recovery suggestion for specific Windows error codes."""
        suggestions = {
            winerror.ERROR_DISK_FULL: "Free up disk space on the destination drive",
            winerror.ERROR_ACCESS_DENIED: "Check file permissions or run as administrator",
            winerror.ERROR_FILE_NOT_FOUND: "Verify the source file exists and is accessible",
            winerror.ERROR_PATH_NOT_FOUND: "Check that the target directory exists",
            winerror.ERROR_NOT_ENOUGH_MEMORY: "Close other applications to free memory",
        }
        
        return suggestions.get(error_code, "Check file paths, permissions, and available resources")
    
    @staticmethod
    def create_copy_operation_logger(operation_id: str) -> logging.Logger:
        """
        Create a dedicated logger for a copy operation with timestamped log file.
        
        Purpose:
        --------
        Establishes isolated logging for individual copy operations to enable
        detailed tracking, debugging, and performance analysis per operation.
        
        Args:
        -----
        operation_id: Unique identifier for the copy operation
        
        Returns:
        --------
        logging.Logger: Configured logger instance for the operation
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"enhanced_filecopy_{timestamp}_{operation_id}.log"
        log_filepath = os.path.join(os.path.dirname(__file__), log_filename)
        
        # Create a new logger instance for this operation
        operation_logger = logging.getLogger(f"enhanced_copy_operation_{operation_id}")
        operation_logger.setLevel(logging.DEBUG)
        
        # Create file handler for this operation with UTF-8 encoding
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter for operation logs
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        operation_logger.addHandler(file_handler)
        operation_logger.propagate = False  # Don't propagate to root logger
        
        return operation_logger
    
    def start_copy_operation(self, operation_name: str, dry_run: bool = False) -> str:
        """
        Start a new enhanced copy operation session with dedicated logging.
        
        Args:
        -----
        operation_name: Descriptive name for the operation
        dry_run: If True, simulate the operation without modifying the filesystem
        
        Returns:
        --------
        str: Operation ID for tracking
        """
        # >>> CHANGE START chatGPT
        self._dry_run = bool(dry_run)
        # Propagate to timestamp manager (it supports dry_run internally)
        try:
            if hasattr(self, "timestamp_manager"):
                self.timestamp_manager._dry_run = self._dry_run
        except Exception:
            pass
        # >>> CHANGE END

        self.operation_id = uuid.uuid4().hex[:8]
        self.operation_logger = FileCopyManager_class.create_copy_operation_logger(self.operation_id)
        self.operation_sequence = 0  # Reset sequence counter for new operation
        
        self.operation_logger.info("=" * 80)
        self.operation_logger.info(f"ENHANCED COPY OPERATION STARTED: {operation_name}")
        self.operation_logger.info(f"Operation ID: {self.operation_id}")
        self.operation_logger.info(f"Copy Strategies: DIRECT (CopyFileExW + mmap), STAGED (chunked + BLAKE3)")
        self.operation_logger.info(f"Verification Policy: {C.FILECOPY_VERIFY_POLICY}")
        self.operation_logger.info(f"BLAKE3 Available: {self.blake3_available}")
        # >>> CHANGE START chatGPT
        self.operation_logger.info(f"Dry run mode: {self._dry_run}")
        # >>> CHANGE END
        self.operation_logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.operation_logger.info("=" * 80)
        
        return self.operation_id
    
    def end_copy_operation(self, success_count: int, error_count: int, total_bytes: int):
        """
        End the current copy operation session with comprehensive summary.
        
        Args:
        -----
        success_count: Number of successfully processed files
        error_count: Number of files that failed
        total_bytes: Total bytes processed
        """
        if self.operation_logger:
            self.operation_logger.info("=" * 80)
            self.operation_logger.info(f"ENHANCED COPY OPERATION COMPLETED")
            self.operation_logger.info(f"Operation ID: {self.operation_id}")
            self.operation_logger.info(f"Files processed successfully: {success_count}")
            self.operation_logger.info(f"Files failed: {error_count}")
            self.operation_logger.info(f"Total bytes processed: {total_bytes:,}")
            self.operation_logger.info(f"Total operations: {self.operation_sequence}")
            self.operation_logger.info(f"BLAKE3 Available: {self.blake3_available}")
            self.operation_logger.info(f"Timestamp: {datetime.now().isoformat()}")
            self.operation_logger.info("=" * 80)
            
            # Close the operation logger
            for handler in self.operation_logger.handlers[:]:
                handler.close()
                self.operation_logger.removeHandler(handler)
        
        self.operation_id = None
        self.operation_logger = None
        self.operation_sequence = 0
