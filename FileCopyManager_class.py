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
        Determine the optimal copy strategy based on enhanced detection logic (M01-M03).
        
        Purpose:
        --------
        Analyzes file characteristics, drive types, and network/cloud locations to select 
        the most efficient copy strategy for optimal performance and reliability.
        
        Strategy Logic per M01-M03:
        ---------------------------
        - Cloud storage locations always use STAGED (regardless of file size)
        - Network drives always use STAGED strategy 
        - Files >= 2GB use STAGED strategy
        - Local files < 2GB use DIRECT strategy
        
        Args:
        -----
        source_path: Source file path for analysis
        target_path: Target file path for analysis  
        file_size: File size in bytes for threshold comparison
        
        Returns:
        --------
        CopyStrategy: Optimal strategy for the given file and drive combination
        """
        # Enhanced network and cloud detection
        source_network = FileCopyManager_class._is_network_or_cloud_location(source_path)
        target_network = FileCopyManager_class._is_network_or_cloud_location(target_path)
        
        # Priority 1: Network or cloud location detection (M01, M03)
        if source_network or target_network:
            return FileCopyManager_class.CopyStrategy.STAGED
        
        # Priority 2: Large file size threshold (M01, M03)
        if file_size >= C.FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES:
            return FileCopyManager_class.CopyStrategy.STAGED
        
        # Default: Local small files use DIRECT strategy (M02)
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
                if drive_type == C.FILECOPY_DRIVE_REMOTE:
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
    
    def copy_file(self, source_path: str, target_path: str) -> FileCopyManager_class.CopyOperationResult:
        """
        Main copy method with enhanced strategy selection and secure rollback (M12: overwrite removed).
        
        Purpose:
        --------
        Orchestrates file copy operations using intelligent strategy selection based on
        file characteristics and drive types, with comprehensive verification and 
        bulletproof rollback mechanisms.
        
        Args:
        -----
        source_path: Source file path
        target_path: Target file path
        
        Returns:
        --------
        CopyOperationResult: Detailed result of the copy operation
        """
        # Increment sequence number for this operation
        self.operation_sequence += 1
        
        start_time = time.time()
        
        # Validate input paths
        if not Path(source_path).exists():
            return FileCopyManager_class.CopyOperationResult(
                success=False,
                strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,
                source_path=source_path,
                target_path=target_path,
                file_size=0,
                duration_seconds=0,
                error_message="Source file does not exist",
                recovery_suggestion="Check the source file path and ensure the file exists"
            )
        
        if not Path(source_path).is_file():
            return FileCopyManager_class.CopyOperationResult(
                success=False,
                strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,
                source_path=source_path,
                target_path=target_path,
                file_size=0,
                duration_seconds=0,
                error_message="Source path is not a file",
                recovery_suggestion="Ensure the source path points to a file, not a directory"
            )
        
        # Get file size for strategy determination and validate size limits
        file_size = Path(source_path).stat().st_size
        
        if file_size > C.FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES:
            return FileCopyManager_class.CopyOperationResult(
                success=False,
                strategy_used=FileCopyManager_class.CopyStrategy.STAGED,
                source_path=source_path,
                target_path=target_path,
                file_size=file_size,
                duration_seconds=0,
                error_message=f"File exceeds maximum size limit ({C.FILECOPY_MAXIMUM_COPY_FILE_SIZE_BYTES:,} bytes)",
                recovery_suggestion="Split large files or increase the maximum file size limit"
            )

        # >>> CHANGE START: engine-level UNC rejection (strict mode) # per chatGPT change 3
        if C.FILECOPY_UNC_PATH_REJECTION_STRICT and (source_path.startswith('\\\\') or target_path.startswith('\\\\')):
            suggestion = "Map the UNC path to a drive letter (e.g., Z:) and retry."
            return FileCopyManager_class.CopyOperationResult(
                success=False,
                strategy_used=FileCopyManager_class.CopyStrategy.STAGED,
                source_path=source_path,
                target_path=target_path,
                file_size=file_size,
                duration_seconds=0,
                error_message="UNC paths are not allowed by policy",
                recovery_suggestion=suggestion
            )
        # <<< CHANGE END
        
        # Determine copy strategy
        strategy = FileCopyManager_class.determine_copy_strategy(source_path, target_path, file_size)
        
        # Log operation start with sequence number
        sequence_info = f"[{self.operation_sequence}]"
        
        self._log_status(f"Starting copy operation {sequence_info}:")
        self._log_status(f"  Source: {source_path}")
        self._log_status(f"  Target: {target_path}")
        self._log_status(f"  Size: {file_size:,} bytes")
        self._log_status(f"  Strategy: {strategy.value.upper()}")

        # >>> CHANGE START
        # Respect DRY RUN at the engine level: do not touch the filesystem.
        if getattr(self, "_dry_run", False):
            self._log_status(f"DRY RUN: Would copy '{source_path}' → '{target_path}' using {strategy.value.upper()}")
            result = FileCopyManager_class.CopyOperationResult(
                success=True,
                strategy_used=strategy,
                source_path=source_path,
                target_path=target_path,
                file_size=file_size,
                duration_seconds=0.0,
                bytes_copied=0,
                verification_passed=True,
                verification_mode="none"
            )
            return result
        # <<< CHANGE END

        # Execute appropriate strategy
        if strategy == FileCopyManager_class.CopyStrategy.DIRECT:
            result = self._execute_direct_strategy(source_path, target_path)
        else:  # STAGED strategy
            result = self._execute_staged_strategy(source_path, target_path)
        
        # Calculate final metrics
        result.duration_seconds = time.time() - start_time
        if result.duration_seconds > 0 and result.bytes_copied > 0:
            result.throughput_mbps = (result.bytes_copied / (1024 * 1024)) / result.duration_seconds
        
        # Log final result with sequence number
        if result.success:
            self._log_status(f"Copy operation {sequence_info} SUCCESSFUL - {result.bytes_copied:,} bytes in {result.duration_seconds:.2f}s ({result.throughput_mbps:.1f} MB/s)")
            if result.verification_passed:
                self._log_status(f"Verification passed using {result.verification_mode} mode")
        else:
            self._log_status(f"Copy operation {sequence_info} FAILED - {result.error_message}")
            if result.rollback_performed:
                rollback_status = "successful" if result.rollback_success else "FAILED"
                self._log_status(f"Rollback {rollback_status}")
        
        return result
    
    def _execute_direct_strategy(self, source_path: str, target_path: str) -> FileCopyManager_class.CopyOperationResult:
        """
        DIRECT strategy implementation using Windows CopyFileExW API with secure rollback (M02).
        
        Purpose:
        --------
        Optimized for local drives with kernel-level performance, progress callbacks,
        and memory-mapped verification. Uses secure temporary file approach.
        
        Process Flow:
        -------------
        1. Preflight validation and timestamp capture
        2. Create secure temporary file path
        3. Windows CopyFileExW copy to temporary file
        4. Memory-mapped window verification (if enabled)
        5. Atomic file placement sequence
        6. Timestamp application and cleanup
        
        Args:
        -----
        source_path: Source file path
        target_path: Target file path
        
        Returns:
        --------
        CopyOperationResult: Detailed operation result
        """
        start_time = time.time()
        file_size = Path(source_path).stat().st_size
        
        self._log_status(f"Using DIRECT strategy for {os.path.basename(source_path)} ({file_size:,} bytes)")
        
        result = FileCopyManager_class.CopyOperationResult(
            success=False,
            strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0,
            bytes_copied=0
        )
        
        # Phase 1: Preflight validation and timestamp capture
        backup_start_time = time.time()
        source_timestamps = None
        target_timestamps = None
        temp_file_path = None
        backup_path = None
        
        try:
            source_timestamps = self.timestamp_manager.get_file_timestamps(source_path)
        except Exception as e:
            result.error_message = f"Failed to read source timestamps: {e}"
            result.recovery_suggestion = "Check file permissions and ensure the file is accessible"
            return result
        
        if Path(target_path).exists():
            try:
                target_timestamps = self.timestamp_manager.get_file_timestamps(target_path)
            except Exception as e:
                result.error_message = f"Failed to read target timestamps for backup: {e}"
                result.recovery_suggestion = "Check target file permissions"
                return result
        
        # Phase 2: Disk space check
        if not self._check_sufficient_disk_space(source_path, target_path):
            result.error_message = "Insufficient disk space for copy operation"
            result.recovery_suggestion = "Free up disk space on the target drive"
            return result

        # >>> CHANGE START: sparse-file warning (DIRECT) ) # per chatGPT change 6
        try:
            attrs = kernel32.GetFileAttributesW(ctypes.c_wchar_p(source_path))
            if attrs != C.FILECOPY_INVALID_FILE_ATTRIBUTES and (attrs & C.FILECOPY_FILE_ATTRIBUTE_SPARSE_FILE):
                result.sparse_file_detected = True
                self._log_status(f"WARNING: Source has SPARSE FILE attribute; this copy may MASSIVELY inflate size on target")
                log_and_flush(logging.WARNING, f"WARNING: Source has SPARSE FILE attribute; this copy may MASSIVELY inflate size on target")
        except Exception:
            pass  # Warning best-effort only
        # <<< CHANGE END
        
        # Phase 3: Create secure temporary file path
        target_dir = Path(target_path).parent
        target_name = Path(target_path).name
        temp_file_path = str(target_dir / f"{target_name}.tmp_{uuid.uuid4().hex[:8]}")
        result.temp_path = temp_file_path
        
        result.time_backup = time.time() - backup_start_time
        
        try:
            # Phase 4: Windows CopyFileExW copy to temporary file
            copy_start_time = time.time()
            copy_result = self._copy_with_windows_api(source_path, temp_file_path)
            result.time_copy = time.time() - copy_start_time
            
            if not copy_result['success']:
                # >>> CHANGE START: explicit cancel semantics + cleanup (DIRECT) # per chatGPT change 1.3
                self._cleanup_temp_file(temp_file_path)  # always safe to remove temp
                result.error_message = copy_result['error']
                result.error_code = copy_result.get('error_code', 0)
                result.cancelled_by_user = copy_result.get('cancelled', False)
                if result.cancelled_by_user:
                    self._log_status("User cancelled copy; temp removed; original target preserved")
                    result.recovery_suggestion = "No changes were made. You can resume later or retry the file."
                else:
                    result.recovery_suggestion = copy_result.get('recovery_suggestion', "")
                return result
                # <<< CHANGE END
            
            result.bytes_copied = copy_result['bytes_copied']
            
            # Phase 5: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                self._log_status(f"Verifying copied file using memory-mapped comparison")
                verify_result = self._verify_by_mmap_windows(source_path, temp_file_path)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
                
                if not verify_result:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = "Content verification failed - files do not match"
                    result.recovery_suggestion = "Check source file integrity and retry the operation"
                    return result
            else:
                result.verification_mode = "none"
                result.verification_passed = True  # No verification requested
                result.time_verify = 0
            
            # Phase 6: Atomic file placement sequence
            cleanup_start_time = time.time()
            if Path(target_path).exists():
                backup_path = f"{target_path}.backup_{uuid.uuid4().hex[:8]}"
                result.backup_path = backup_path
                os.rename(target_path, backup_path)  # Atomic: original → backup
                self._log_status(f"Original file moved to backup: {backup_path}")
            
            os.rename(temp_file_path, target_path)  # Atomic: temp → final location
            self._log_status(f"Verified file moved to final location: {target_path}")
            
            # Phase 7: Apply source timestamps
            try:
                self.timestamp_manager.copy_timestamps(source_path, target_path)
                self._log_status(f"Timestamps copied from source to target")
            except Exception as e:
                self._log_status(f"Warning: Could not copy timestamps: {e}")
            
            # Phase 8: Success cleanup - remove backup
            if backup_path and Path(backup_path).exists():
                os.remove(backup_path)
                self._log_status(f"Backup file removed: {backup_path}")
            
            result.time_cleanup = time.time() - cleanup_start_time
            result.success = True
            self._log_status(f"DIRECT copy completed successfully")
            
        except Exception as e:
            # Comprehensive rollback for any failure
            result.error_message = str(e)
            result.rollback_performed = True
            
            try:
                rollback_success = self._perform_secure_rollback(
                    temp_file_path, backup_path, target_path, target_timestamps, str(e)
                )
                result.rollback_success = rollback_success
                
            except Exception as rollback_error:
                result.error_message += f" | Rollback failed: {rollback_error}"
                result.rollback_success = False
                result.recovery_suggestion = "Manual intervention required - check backup files"
                
        return result
    
    def _execute_staged_strategy(self, source_path: str, target_path: str) -> FileCopyManager_class.CopyOperationResult:
        """
        STAGED strategy implementation using chunked I/O with progressive BLAKE3 hashing (M03).
        
        Purpose:
        --------
        Optimized for networked files and large file handling with progressive hash calculation,
        chunked I/O, and secure temporary file rollback approach.
        
        Process Flow:
        -------------
        1. Preflight validation and timestamp capture
        2. Create secure temporary file path
        3. Chunked copy with progressive source hash calculation
        4. Target hash calculation and comparison (if enabled)
        5. Atomic file placement sequence
        6. Timestamp application and cleanup
        
        Args:
        -----
        source_path: Source file path
        target_path: Target file path
        
        Returns:
        --------
        CopyOperationResult: Detailed operation result
        """
        start_time = time.time()
        file_size = Path(source_path).stat().st_size
        
        self._log_status(f"Using STAGED strategy for {os.path.basename(source_path)} ({file_size:,} bytes)")
        
        result = FileCopyManager_class.CopyOperationResult(
            success=False,
            strategy_used=FileCopyManager_class.CopyStrategy.STAGED,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0,
            bytes_copied=0
        )
        
        # Determine hash algorithm
        if self.blake3_available:
            result.hash_algorithm = "BLAKE3"
        else:
            result.hash_algorithm = "SHA-256"
        
        # Phase 1: Preflight validation and timestamp capture
        backup_start_time = time.time()
        source_timestamps = None
        target_timestamps = None
        temp_file_path = None
        backup_path = None
        
        try:
            source_timestamps = self.timestamp_manager.get_file_timestamps(source_path)
        except Exception as e:
            result.error_message = f"Failed to read source timestamps: {e}"
            result.recovery_suggestion = "Check file permissions and ensure the file is accessible"
            return result
        
        if Path(target_path).exists():
            try:
                target_timestamps = self.timestamp_manager.get_file_timestamps(target_path)
            except Exception as e:
                result.error_message = f"Failed to read target timestamps for backup: {e}"
                result.recovery_suggestion = "Check target file permissions"
                return result

        # >>> CHANGE START: sparse-file warning (STAGED) # per chatGPT change 6
        try:
            attrs = kernel32.GetFileAttributesW(ctypes.c_wchar_p(source_path))
            if attrs != C.FILECOPY_INVALID_FILE_ATTRIBUTES and (attrs & C.FILECOPY_FILE_ATTRIBUTE_SPARSE_FILE):
                result.sparse_file_detected = True
                self._log_status(f"WARNING: Source has SPARSE FILE attribute; this STAGED copy may MASSIVELY inflate size on target")
                log_and_flush(logging.WARNING, f"WARNING: Source has SPARSE FILE attribute; this STAGED copy may MASSIVELY inflate size on target")
        except Exception:
            pass
        # <<< CHANGE END
        
        # >>> CHANGE START: 
        # Phase 2.0 = Disk space check (was missing in STAGED) # per chatGPT change 4
        # Enforce local free-space check; for network where API can’t determine, proceed but warn
        if not self._check_sufficient_disk_space(source_path, target_path):
            result.error_message = "Insufficient disk space for copy operation (STAGED)"
            result.recovery_suggestion = "Free space on the target drive or choose another destination"
            return result
        # <<< CHANGE END

        # Phase 2.1: Create secure temporary file path
        target_dir = Path(target_path).parent
        target_name = Path(target_path).name
        temp_file_path = str(target_dir / f"{target_name}.tmp_{uuid.uuid4().hex[:8]}")
        result.temp_path = temp_file_path
        
        result.time_backup = time.time() - backup_start_time
        
        try:
            # Phase 3: Chunked copy with progressive hash calculation
            copy_start_time = time.time()
            copy_result = self._copy_with_progressive_hash(source_path, temp_file_path)
            result.time_copy = time.time() - copy_start_time
            
            if not copy_result['success']:
                # >>> CHANGE START: explicit cancel semantics + cleanup (STAGED) # per chatGPT change 8
                self._cleanup_temp_file(temp_file_path)
                result.error_message = copy_result['error']
                result.cancelled_by_user = copy_result.get('cancelled', False)
                if result.cancelled_by_user:
                    self._log_status("User cancelled copy; temp removed; original target preserved")
                    result.recovery_suggestion = "No changes were made. You can resume later or retry the file."
                else:
                    result.recovery_suggestion = copy_result.get('recovery_suggestion', "")
                return result
                # <<< CHANGE END
                
            result.bytes_copied = copy_result['bytes_copied']
            result.computed_hash = copy_result['hash']
            
            # Phase 4: Verification (if enabled by policy)
            verify_start_time = time.time()
            if self._should_verify_file(file_size):
                self._log_status(f"Verifying copied file using hash comparison ({result.hash_algorithm})")
                verify_result = self._verify_by_hash_comparison(temp_file_path, result.computed_hash, result.hash_algorithm)
                result.verification_mode = self._get_verification_mode()
                result.verification_passed = verify_result
                result.time_verify = time.time() - verify_start_time
                
                if not verify_result:
                    self._cleanup_temp_file(temp_file_path)
                    result.error_message = f"Hash verification failed - {result.hash_algorithm} hashes do not match"
                    result.recovery_suggestion = "Check source file integrity and retry the operation"
                    return result
            else:
                result.verification_mode = "none"
                result.verification_passed = True  # No verification requested
                result.time_verify = 0
            
            # Phase 5: Atomic file placement sequence
            cleanup_start_time = time.time()
            if Path(target_path).exists():
                backup_path = f"{target_path}.backup_{uuid.uuid4().hex[:8]}"
                result.backup_path = backup_path
                os.rename(target_path, backup_path)  # Atomic: original → backup
                self._log_status(f"Original file moved to backup: {backup_path}")
            
            os.rename(temp_file_path, target_path)  # Atomic: temp → final location
            self._log_status(f"Verified file moved to final location: {target_path}")
            
            # Phase 6: Apply source timestamps
            try:
                self.timestamp_manager.copy_timestamps(source_path, target_path)
                self._log_status(f"Timestamps copied from source to target")
            except Exception as e:
                self._log_status(f"Warning: Could not copy timestamps: {e}")
            
            # Phase 7: Success cleanup - remove backup
            if backup_path and Path(backup_path).exists():
                os.remove(backup_path)
                self._log_status(f"Backup file removed: {backup_path}")
            
            result.time_cleanup = time.time() - cleanup_start_time
            result.success = True
            self._log_status(f"STAGED copy completed successfully")
            
        except Exception as e:
            # Comprehensive rollback for any failure
            result.error_message = str(e)
            result.rollback_performed = True
            
            try:
                rollback_success = self._perform_secure_rollback(
                    temp_file_path, backup_path, target_path, target_timestamps, str(e)
                )
                result.rollback_success = rollback_success
                
            except Exception as rollback_error:
                result.error_message += f" | Rollback failed: {rollback_error}"
                result.rollback_success = False
                result.recovery_suggestion = "Manual intervention required - check backup files"
        
        return result
    
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
        # Commented out and replaced per chatGPT change 1.2 below ...
        #def copy_progress_callback(total_size, transferred, stream_size, 
        #                          stream_transferred, stream_num, reason,
        #                          src_handle, dst_handle, user_data):
        #    """Windows progress callback - called by OS during copy operation."""
        #    
        #    # # DEBUG: Uncomment for detailed progress tracking
        #    # if transferred % (64 * 1024 * 1024) == 0:  # Every 64MB
        #    #     progress_pct = (transferred / total_size * 100) if total_size > 0 else 0
        #    #     log_and_flush(logging.DEBUG, f"Copy progress: {progress_pct:.1f}% ({transferred:,} / {total_size:,} bytes)")
        #    
        #    # Update progress if callback available
        #    if self.status_callback:
        #        progress_percentage = (transferred / total_size) * 100 if total_size > 0 else 0
        #        if transferred > 0:  # Avoid spam for initial callback
        #            self.status_callback(f"Copying: {progress_percentage:.1f}% ({transferred:,} bytes)")
        #    
        #    return C.FILECOPY_PROGRESS_CONTINUE

        # >>> CHANGE START: Progress + cancel wiring for DIRECT (CopyFileExW) # per chatGPT change 1.2
        cancel_flag = wintypes.BOOL(0)  # module-level global, LPBOOL for CopyFileExW
        
        def copy_progress_callback(total_size, transferred, stream_size, 
                                  stream_transferred, stream_num, reason,
                                  src_handle, dst_handle, user_data):
            """Windows progress callback - called by OS during copy operation."""
            # 1) Cancellation: Event from UI or progress manager
            if getattr(self, "cancel_event", None) and self.cancel_event.is_set():
                return C.FILECOPY_PROGRESS_CANCEL
            pm = getattr(self, "progress_manager", None)
            if pm and callable(getattr(pm, "cancellation_callback", None)) and pm.cancellation_callback():
                return C.FILECOPY_PROGRESS_CANCEL

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

            return C.FILECOPY_PROGRESS_CONTINUE
        # <<< CHANGE END
        
        # Create callback wrapper for Windows
        callback_func = PROGRESS_ROUTINE(copy_progress_callback)
        
        try:
            # Execute Windows CopyFileExW
            result = kernel32.CopyFileExW(
                ctypes.c_wchar_p(source_path),
                ctypes.c_wchar_p(temp_path), 
                callback_func,
                None,                                    # No user data
                ctypes.byref(cancel_flag),               # Cancel flag
                C.FILECOPY_COPY_FILE_RESTARTABLE         # Restartable if interrupted
            )
            
            if not result:
                error_code = kernel32.GetLastError()
                if error_code == C.FILECOPY_ERROR_REQUEST_ABORTED:
                    return {
                        'success': False, 
                        'cancelled': True, 
                        'error': "Copy operation cancelled by user",
                        'error_code': error_code
                    }
                else:
                    error_msg = self._get_windows_error_message(error_code)
                    return {
                        'success': False, 
                        'error': f"CopyFileExW failed: {error_msg}",
                        'error_code': error_code,
                        'recovery_suggestion': self._get_recovery_suggestion_for_error(error_code)
                    }
            
            bytes_copied = Path(source_path).stat().st_size
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
        Chunked copy with progressive hash calculation for STAGED strategy.
        
        Args:
        -----
        source_path: Source file path
        temp_path: Temporary target file path
        
        Returns:
        --------
        dict: Copy result with success status, bytes copied, hash, and error information
        """
        chunk_size = C.FILECOPY_NETWORK_CHUNK_BYTES
        
        # Initialize hasher
        if self.blake3_available:
            hasher = blake3.blake3()
        else:
            hasher = hashlib.sha256()
        
        bytes_copied = 0
        
        try:
            with open(source_path, 'rb') as src_file, open(temp_path, 'wb') as temp_file:
                while True:
                    # >>> CHANGE START: progress + cancel (STAGED loop) # per chatGPT change 1.4
                    # Cancellation (UI event or progress manager)
                    if getattr(self, "cancel_event", None) and self.cancel_event.is_set():
                        return {'success': False, 'cancelled': True, 'error': "Copy operation cancelled by user"}
                    pm = getattr(self, "progress_manager", None)
                    if pm and callable(getattr(pm, "cancellation_callback", None)) and pm.cancellation_callback():
                        return {'success': False, 'cancelled': True, 'error': "Copy operation cancelled by user"}
                    # <<< CHANGE END

                    chunk = src_file.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Update hash with chunk
                    hasher.update(chunk)
                    
                    # Write chunk to temporary file
                    temp_file.write(chunk)
                    bytes_copied += len(chunk)

                    # >>> CHANGE START: per-file progress feed to UI # per chatGPT change 1.4
                    # Progress update
                    if pm and hasattr(pm, "update_file_progress"):
                        try:
                            total_size = Path(source_path).stat().st_size
                            pm.update_file_progress(source_path, bytes_copied, total_size, strategy="STAGED")
                            mb_copied = bytes_copied / (1024 * 1024)
                            mb_total_size = total_size / (1024 * 1024)
                            log_and_flush(logging.DEBUG, f"Copying (STAGED): 'update_file_progress': {mb_copied} MB of {mb_total_size} MB transferred")
                        except Exception:
                            pass
                    elif self.status_callback and bytes_copied % (chunk_size * 4) == 0:
                        mb_copied = bytes_copied / (1024 * 1024)
                        mb_total_size = total_size / (1024 * 1024)
                        self.status_callback(f"Copying (STAGED): no hasattr 'update_file_progress': {mb_copied:.1f} MB or of {mb_total_size} MB transferred")
                        #log_and_flush(logging.DEBUG, f"Copying (STAGED): no hasattr 'update_file_progress': {mb_copied:.1f} MB or of {mb_total_size} MB transferred")
                    # <<< CHANGE END
                    
                    # # DEBUG: Uncomment for detailed chunked copy tracking
                    # if bytes_copied % (chunk_size * 10) == 0:  # Every 10 chunks
                    #     log_and_flush(logging.DEBUG, f"Chunked copy progress: {bytes_copied:,} bytes")

                    # Progress update with throttling
                    #if self.status_callback and bytes_copied % (chunk_size * 4) == 0:  # Every 16MB
                    #    mb_copied = bytes_copied / (1024 * 1024)
                    #    self.status_callback(f"Copying (STAGED): {mb_copied:.1f} MB transferred")
            
            computed_hash = hasher.hexdigest()
            
            return {
                'success': True,
                'bytes_copied': bytes_copied,
                'hash': computed_hash
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Chunked copy failed: {str(e)}",
                'recovery_suggestion': "Check source file integrity and available disk space"
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
        error_messages = {
            C.FILECOPY_ERROR_SUCCESS: "Success",
            C.FILECOPY_ERROR_REQUEST_ABORTED: "Operation cancelled by user",
            C.FILECOPY_ERROR_DISK_FULL: "Insufficient disk space",
            C.FILECOPY_ERROR_HANDLE_DISK_FULL: "Disk full",
            C.FILECOPY_ERROR_NOT_ENOUGH_MEMORY: "Insufficient memory",
            C.FILECOPY_ERROR_ACCESS_DENIED: "Access denied",
            C.FILECOPY_ERROR_FILE_NOT_FOUND: "File not found",
            C.FILECOPY_ERROR_PATH_NOT_FOUND: "Path not found",
            C.FILECOPY_ERROR_FILE_EXISTS: "File already exists",
            C.FILECOPY_ERROR_ALREADY_EXISTS: "File already exists"
        }
        
        return error_messages.get(error_code, f"Windows error {error_code}")
    
    def _get_recovery_suggestion_for_error(self, error_code: int) -> str:
        """Get recovery suggestion for specific Windows error codes."""
        suggestions = {
            C.FILECOPY_ERROR_DISK_FULL: "Free up disk space on the destination drive",
            C.FILECOPY_ERROR_ACCESS_DENIED: "Check file permissions or run as administrator",
            C.FILECOPY_ERROR_FILE_NOT_FOUND: "Verify the source file exists and is accessible",
            C.FILECOPY_ERROR_PATH_NOT_FOUND: "Check that the target directory exists",
            C.FILECOPY_ERROR_NOT_ENOUGH_MEMORY: "Close other applications to free memory"
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
