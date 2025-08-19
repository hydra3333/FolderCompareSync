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
from ProgressDialog_class import ProgressDialog_class
from FileTimestampManager_class import FileTimestampManager_class

class FileCopyManager_class:
    """
    file copy manager implementing Strategy A and Strategy B
    with rename-based backup , comprehensive error handling, and dry run capability.
    
    Purpose:
    --------
    Manages file copy operations using intelligent strategy selection based on file
    size and drive types, with support for both actual operations and dry run simulation.
    
    Key Features:
    -------------
    - Dual copy strategies (Direct and Staged) with automatic selection
    - Complete timestamp preservation with rollback capability
    - Dry run mode for safe operation testing without file modifications
    - Comprehensive logging and performance tracking
    - Atomic operations using Windows rename primitives
    
    Usage:
    ------
    copy_manager = FileCopyManager_class(status_callback=add_status_message)
    copy_manager.set_dry_run_mode(True)  # For testing
    operation_id = copy_manager.start_copy_operation("Test Copy")
    result = copy_manager.copy_file(source, target, overwrite=True)
    copy_manager.end_copy_operation(success_count, error_count, total_bytes)
    """


    class CopyStrategy(Enum):
        """
        Copy strategy enumeration for different file handling approaches.
        
        Purpose:
        --------
        Defines the available copy strategies for file operations
        based on file size, location, and drive type characteristics.
        """
        DIRECT = "direct".lower()           # Strategy A: Direct copy for small files on local drives
        STAGED = "staged".lower()           # Strategy B: Staged copy with rename-based backup for large files
        NETWORK = "network".lower()         # Network-optimized copy with retry logic
    
    class DriveType(Enum):
        """
        Drive type enumeration for path analysis and strategy selection.
        
        Purpose:
        --------
        Categorizes different drive types to enable optimal copy strategy
        selection based on the characteristics of source and destination drives.
        """
        LOCAL_FIXED = "local_fixed"
        LOCAL_REMOVABLE = "local_removable"
        NETWORK_MAPPED = "network_mapped"
        NETWORK_UNC = "network_unc"
        RELATIVE = "relative"
        UNKNOWN = "unknown"
    
    @dataclass
    class CopyOperationResult:
        """
        Result container for copy operation outcomes with detailed information.
        
        Purpose:
        --------
        Stores comprehensive information about copy operation results including
        success status, strategy used, performance metrics, and error details.
        
        Usage:
        ------
        Used by FileCopyManager_class to return detailed operation results
        for logging, error handling, and performance tracking purposes.
        """
        success: bool
        strategy_used: FileCopyManager_class.CopyStrategy #'FileCopyManager_class.CopyStrategy' 
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
    
    @staticmethod
    def get_drive_type(path: str) -> FileCopyManager_class.DriveType:
        """
        Determine the drive type for a given path using Windows API.
        
        Purpose:
        --------
        Analyzes the drive type to enable optimal copy strategy selection
        based on drive characteristics.
        
        Args:
        -----
        path: File or directory path to analyze
        
        Returns:
        --------
        DriveType: Enumerated drive type for strategy selection
        
        Usage:
        ------
        drive_type = FileCopyManager_class.get_drive_type("C:\\MyFiles\\file.txt")
        if drive_type == FileCopyManager_class.DriveType.NETWORK_MAPPED:
            # Use network-optimized copy strategy
        """
        if not path:
            return FileCopyManager_class.DriveType.RELATIVE
        
        # Handle UNC paths (\\server\share)
        if path.startswith('\\\\'):
            return FileCopyManager_class.DriveType.NETWORK_UNC
        
        # Extract drive letter
        drive = os.path.splitdrive(path)[0]
        if not drive:
            return FileCopyManager_class.DriveType.RELATIVE
        
        try:
            # Use Windows API to determine drive type
            drive_root = drive + '\\'
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive_root))
            
            # Map Windows drive types to our enum
            if drive_type == 2:  # DRIVE_REMOVABLE
                return FileCopyManager_class.DriveType.LOCAL_REMOVABLE
            elif drive_type == 3:  # DRIVE_FIXED
                return FileCopyManager_class.DriveType.LOCAL_FIXED
            elif drive_type == 4:  # DRIVE_REMOTE
                return FileCopyManager_class.DriveType.NETWORK_MAPPED
            elif drive_type == 5:  # DRIVE_CDROM
                return FileCopyManager_class.DriveType.LOCAL_REMOVABLE
            elif drive_type == 6:  # DRIVE_RAMDISK
                return FileCopyManager_class.DriveType.LOCAL_FIXED
            else:
                return FileCopyManager_class.DriveType.UNKNOWN
                
        except Exception as e:
            log_and_flush(logging.WARNING, f"Could not determine drive type for {path}: {e}")
            return FileCopyManager_class.DriveType.UNKNOWN
    
    @staticmethod
    def determine_copy_strategy(source_path: str, target_path: str, file_size: int) -> FileCopyManager_class.CopyStrategy:
        """
        Determine the optimal copy strategy based on file size and drive types.
        
        Purpose:
        --------
        Analyzes file characteristics and drive types to select the most efficient
        copy strategy for optimal performance and reliability.
        
        Strategy Logic:
        ---------------
        - Network drives always use STAGED strategy (rename-based backup)
        - Files >= COPY_STRATEGY_THRESHOLD use STAGED strategy (rename-based backup)
        - Small files on local drives use DIRECT strategy
        
        Args:
        -----
        source_path: Source file path for analysis
        target_path: Target file path for analysis  
        file_size: File size in bytes for threshold comparison
        
        Returns:
        --------
        CopyStrategy: Optimal strategy for the given file and drive combination
        """
        source_drive_type = FileCopyManager_class.get_drive_type(source_path)
        target_drive_type = FileCopyManager_class.get_drive_type(target_path)
        
        # Network drives always use staged strategy (rename-based backup)
        if (source_drive_type in [FileCopyManager_class.DriveType.NETWORK_MAPPED, FileCopyManager_class.DriveType.NETWORK_UNC] or
            target_drive_type in [FileCopyManager_class.DriveType.NETWORK_MAPPED, FileCopyManager_class.DriveType.NETWORK_UNC]):
            return FileCopyManager_class.CopyStrategy.STAGED
        
        # Large files use staged strategy (rename-based backup)
        if file_size >= C.COPY_STRATEGY_THRESHOLD:
            return FileCopyManager_class.CopyStrategy.STAGED
        
        # Small files on local drives use direct strategy
        return FileCopyManager_class.CopyStrategy.DIRECT
    
    @staticmethod
    def create_copy_operation_logger(operation_id: str) -> logging.Logger: # v000.0002 replaced by updated version
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
        
        Usage:
        ------
        logger = FileCopyManager_class.create_copy_operation_logger("abc123def")
        log_and_flush(logging.INFO, "Copy operation starting...")
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"foldercomparesync_copy_{timestamp}_{operation_id}.log"
        log_filepath = os.path.join(os.path.dirname(__file__), log_filename)
        
        # Create a new logger instance for this operation
        operation_logger = logging.getLogger(f"copy_operation_{operation_id}")
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
    
    def __init__(self, status_callback=None):
        """
        Initialize the copy manager with callback and supporting components.
        
        Args:
        -----
        status_callback: Function to call for status updates (optional)
        """
        self.status_callback = status_callback
        self.operation_id = None
        self.operation_logger = None
        self.timestamp_manager = FileTimestampManager_class()  # Single instance, will update in set_dry_run_mode
        self.dry_run_mode = False  # New: Dry run mode flag
        self.operation_sequence = 0  # New: Sequential numbering for operations
        
        # Log timezone information for the copy manager
        log_and_flush(logging.INFO, f"FileCopyManager_class initialized with timezone: {self.timestamp_manager.get_timezone_string()}")

    def set_dry_run_mode(self, enabled: bool):
        """
        Enable or disable dry run mode for safe operation testing.
        
        Purpose:
        --------
        When enabled, all copy operations are simulated without actual file I/O,
        providing full logging and strategy selection for testing purposes.
        
        Args:
        -----
        enabled: True to enable dry run mode, False for normal operations
        """
        self.dry_run_mode = enabled
        self.timestamp_manager = FileTimestampManager_class(dry_run=enabled)  # Update timestamp manager
        mode_text = "DRY RUN" if enabled else "NORMAL"
        self._log_status(f"Copy manager mode set to: {mode_text}")
        
    def _log_status(self, message: str):
        """Log status message to both operation logger and status callback."""
        if self.operation_logger:
            self.operation_logger.info(message)
        if self.status_callback:
            self.status_callback(message)
        log_and_flush(logging.DEBUG, f"Copy operation status: {message}")
    
    def _verify_copy(self, source_path: str, target_path: str) -> bool:
        """
        Verify (simple method) that a copy operation was successful (or simulate Simple verification in dry run).
        
        Returns True if Simple verification passes, False otherwise
        """
        if not C.COPY_VERIFICATION_ENABLED:
            return True
        
        if self.dry_run_mode:
            self._log_status(f"DRY RUN: Would verify copy - {target_path}")
            return True  # Assume Simple verification would pass in dry run
            
        try:
            # Check file existence
            if not Path(target_path).exists():
                self._log_status(f"Simple verification failed: Target file does not exist: {target_path}")
                return False
            
            # Check file size
            source_size = Path(source_path).stat().st_size
            target_size = Path(target_path).stat().st_size
            
            if source_size != target_size:
                self._log_status(f"Simple verification failed: Size mismatch - Source: {source_size}, Target: {target_size}")
                return False
            
            self._log_status(f"Simple verification passed: {target_path} ({source_size} bytes)")
            return True
            
        except Exception as e:
            self._log_status(f"Simple verification error: {str(e)}")
            return False
    
    def _copy_direct_strategy(self, source_path: str, target_path: str) -> FileCopyManager_class.CopyOperationResult:
        """
        Strategy A: Direct copy for small files on local drives (with dry run support).
        Uses shutil.copy2 with error handling and Simple verification.
        """
        start_time = time.time()
        file_size = Path(source_path).stat().st_size
        
        dry_run_prefix = "DRY RUN: " if self.dry_run_mode else ""
        self._log_status(f"{dry_run_prefix}Using DIRECT strategy for {os.path.basename(source_path)} ({file_size} bytes)")
        
        result = FileCopyManager_class.CopyOperationResult(
            success=False,
            strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0,
            bytes_copied=0
        )
        
        try:
            # Ensure target directory exists (or simulate in dry run)
            target_dir = Path(target_path).parent
            if target_dir and not target_dir.exists():
                if self.dry_run_mode:
                    self._log_status(f"DRY RUN: Would create target directory: {target_dir}")
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    self._log_status(f"Created target directory: {target_dir}")
            
            # Perform direct copy (or simulate in dry run)
            self._log_status(f"{dry_run_prefix}Copying: {source_path} -> {target_path}")
            
            if not self.dry_run_mode:
                shutil.copy2(source_path, target_path)
                result.bytes_copied = file_size
                
                # Copy timestamps from source to target for complete preservation
                self.timestamp_manager.copy_timestamps(source_path, target_path)
            else:
                # Simulate copy operation
                result.bytes_copied = file_size
                self._log_status(f"DRY RUN: Would copy timestamps from source to target")
            
            # Verify the copy (or simulate Simple verification in dry run)
            if self._verify_copy(source_path, target_path):
                result.success = True
                result.verification_passed = True
                self._log_status(f"{dry_run_prefix}DIRECT copy completed successfully")
            else:
                result.error_message = "Copy Simple verification failed"
                self._log_status(f"{dry_run_prefix}DIRECT copy failed Simple verification")
                
        except Exception as e:
            if not self.dry_run_mode:
                result.error_message = str(e)
                self._log_status(f"DIRECT copy failed: {str(e)}")
            else:
                # In dry run, we don't expect real exceptions
                result.success = True
                result.verification_passed = True
                self._log_status(f"DRY RUN: DIRECT copy simulation completed")
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def _copy_staged_strategy(self, source_path: str, target_path: str, overwrite: bool = True) -> FileCopyManager_class.CopyOperationResult:
        """
        Strategy B: staged copy using rename-based backup for large files or network drives (with dry run support).
        Implements 4-step process: save timestamps -> rename to backup -> copy source -> verify
        Uses atomic rename operations instead of expensive copy operations for backup.
        """
        start_time = time.time()
        file_size = Path(source_path).stat().st_size
        
        dry_run_prefix = "DRY RUN: " if self.dry_run_mode else ""
        self._log_status(f"{dry_run_prefix}Using STAGED strategy for {os.path.basename(source_path)} ({file_size} bytes)")
        
        result = FileCopyManager_class.CopyOperationResult(
            success=False,
            strategy_used=FileCopyManager_class.CopyStrategy.STAGED,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            duration_seconds=0,
            bytes_copied=0
        )
        
        # Generate unique identifier for backup file
        backup_uuid = uuid.uuid4().hex[:8]
        backup_path = f"{target_path}.backup_{backup_uuid}" if Path(target_path).exists() else None
        original_timestamps = None
        
        result.backup_path = backup_path
        
        try:
            # Ensure target directory exists (or simulate in dry run)
            target_dir = Path(target_path).parent
            if target_dir and not target_dir.exists():
                if self.dry_run_mode:
                    self._log_status(f"DRY RUN: Would create target directory: {target_dir}")
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    self._log_status(f"Created target directory: {target_dir}")
            
            # Step 1: Check overwrite permission and save original timestamps (or simulate in dry run)
            if Path(target_path).exists():
                if not overwrite:
                    result.error_message = "Target file exists and overwrite is disabled"
                    self._log_status(f"{dry_run_prefix}STAGED copy skipped: Target exists and overwrite disabled")
                    return result
                
                # Save original timestamps for potential rollback (or simulate in dry run)
                try:
                    if not self.dry_run_mode:
                        original_timestamps = self.timestamp_manager.get_file_timestamps(target_path)
                        self._log_status(f"Step 1: Saved original timestamps for potential rollback")
                    else:
                        self._log_status(f"DRY RUN: Step 1: Would save original timestamps for potential rollback")
                except Exception as e:
                    self._log_status(f"Warning: Could not save original timestamps: {e}")
                    # Continue anyway - this is not critical for copy operation
            
            # Step 2: Rename target to backup (atomic, fast operation) (or simulate in dry run)
            if Path(target_path).exists():
                try:
                    self._log_status(f"{dry_run_prefix}Step 2: Renaming target to backup: {target_path} -> {backup_path}")
                    if not self.dry_run_mode:
                        os.rename(target_path, backup_path)
                        self._log_status(f"Atomic rename completed successfully")
                    else:
                        self._log_status(f"DRY RUN: Atomic rename simulation completed")
                except OSError as e:
                    if not self.dry_run_mode:
                        # Critical failure - rename operation failed
                        result.error_message = f"CRITICAL: Rename operation failed - {str(e)}. This may indicate network drive issues or file locking. Operation aborted to prevent data loss."
                        self._log_status(f"CRITICAL FAILURE: Rename operation failed: {str(e)}")
                        self._log_status("RECOMMENDED ACTION: Check if target file is locked by another process, or if network drive has connectivity issues.")
                        return result
                    else:
                        # In dry run, simulate successful rename
                        self._log_status(f"DRY RUN: Rename simulation completed successfully")
            
            # Step 3: Copy source directly to target location (single copy operation) (or simulate in dry run)
            try:
                self._log_status(f"{dry_run_prefix}Step 3: Copying source to target: {source_path} -> {target_path}")
                
                if not self.dry_run_mode:
                    shutil.copy2(source_path, target_path)
                    result.bytes_copied = file_size
                    self._log_status(f"Copy operation completed")
                    
                    # Copy timestamps from source to target for complete preservation
                    self.timestamp_manager.copy_timestamps(source_path, target_path)
                    self._log_status(f"Timestamps copied from source to target")
                else:
                    # Simulate copy operation
                    result.bytes_copied = file_size
                    self._log_status(f"DRY RUN: Copy operation simulation completed")
                    self._log_status(f"DRY RUN: Would copy timestamps from source to target")
                
            except Exception as e:
                if not self.dry_run_mode:
                    # Copy failed - begin rollback procedure
                    result.error_message = f"Copy operation failed: {str(e)}"
                    self._log_status(f"Copy operation failed: {str(e)} - Beginning rollback")
                    raise  # Re-raise to trigger rollback in except block
                else:
                    # In dry run, simulate successful copy
                    result.bytes_copied = file_size
                    self._log_status(f"DRY RUN: Copy simulation completed successfully")
            
            # Step 4: Verify copy operation (or simulate in dry run)
            self._log_status(f"{dry_run_prefix}Step 4: Verifying copied file")
            if not self._verify_copy(source_path, target_path):
                if not self.dry_run_mode:
                    result.error_message = "Copy Simple verification failed"
                    self._log_status(f"STAGED copy failed: Simple verification failed - Beginning rollback")
                    raise Exception("Simple verification failed")  # Trigger rollback
                else:
                    self._log_status(f"DRY RUN: Simple verification simulation completed")
            
            # Step 5: Success - remove backup file (or simulate in dry run)
            if backup_path and (Path(backup_path).exists() or self.dry_run_mode):
                try:
                    if not self.dry_run_mode:
                        os.remove(backup_path)
                        self._log_status(f"Step 5: Removed backup file: {backup_path}")
                    else:
                        self._log_status(f"DRY RUN: Step 5: Would remove backup file: {backup_path}")
                except Exception as e:
                    # Non-critical - backup removal failed but copy succeeded
                    self._log_status(f"Warning: Could not remove backup file {backup_path}: {e}")
                    self._log_status("This is not critical - copy operation succeeded")
            
            result.success = True
            result.verification_passed = True
            self._log_status(f"{dry_run_prefix}STAGED copy completed successfully")
                
        except Exception as e:
            if not self.dry_run_mode:
                result.error_message = str(e) if not result.error_message else result.error_message
                self._log_status(f"STAGED copy failed: {result.error_message}")
                
                # ROLLBACK PROCEDURE: Restore original file and timestamps
                try:
                    self._log_status(f"Beginning rollback procedure for failed STAGED copy")
                    
                    # Remove any partial target file
                    if Path(target_path).exists():
                        try:
                            os.remove(target_path)
                            self._log_status(f"Removed partial target file: {target_path}")
                        except Exception as remove_error:
                            self._log_status(f"Warning: Could not remove partial target file: {remove_error}")
                    
                    # Restore backup file if it exists
                    if backup_path and Path(backup_path).exists():
                        try:
                            self._log_status(f"Restoring backup file: {backup_path} -> {target_path}")
                            os.rename(backup_path, target_path)
                            self._log_status(f"Backup file restored successfully")
                            
                            # Restore original timestamps if we saved them
                            if original_timestamps:
                                try:
                                    self.timestamp_manager.set_file_timestamps(target_path, *original_timestamps)
                                    self._log_status(f"Original timestamps restored successfully")
                                except Exception as timestamp_error:
                                    self._log_status(f"Warning: Could not restore original timestamps: {timestamp_error}")
                            
                        except Exception as restore_error:
                            # CRITICAL: Rollback failed
                            critical_error = f"CRITICAL ROLLBACK FAILURE: {str(restore_error)}"
                            self._log_status(critical_error)
                            self._log_status(f"CRITICAL: Original file may be lost. Backup is at: {backup_path}")
                            self._log_status("RECOMMENDED ACTION: Manually restore the backup file to recover your data.")
                            result.error_message += f" | {critical_error}"
                    else:
                        self._log_status("No backup file to restore (target file was new)")
                    
                    self._log_status(f"Rollback procedure completed")
                    
                except Exception as rollback_error:
                    rollback_failure = f"Rollback procedure failed: {str(rollback_error)}"
                    self._log_status(rollback_failure)
                    result.error_message += f" | {rollback_failure}"
            else:
                # In dry run mode, simulate successful operation
                result.success = True
                result.verification_passed = True
                self._log_status(f"DRY RUN: STAGED copy simulation completed successfully")
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def copy_file(self, source_path: str, target_path: str, overwrite: bool = True) -> FileCopyManager_class.CopyOperationResult:
        """
        Main copy method that automatically selects the appropriate strategy and supports dry run mode.
        
        Purpose:
        --------
        Orchestrates file copy operations using intelligent strategy selection based on
        file characteristics and drive types, with full dry run simulation capability.
        
        Args:
        -----
        source_path: Source file path
        target_path: Target file path  
        overwrite: Whether to overwrite existing files
        
        Returns:
        --------
        CopyOperationResult: Detailed result of the copy operation
        """
        # Increment sequence number for this operation
        self.operation_sequence += 1
        
        # Validate input paths
        if not Path(source_path).exists():
            return FileCopyManager_class.CopyOperationResult(
                success=False,
                strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,
                source_path=source_path,
                target_path=target_path,
                file_size=0,
                duration_seconds=0,
                error_message="Source file does not exist"
            )
        
        if not Path(source_path).is_file():
            return FileCopyManager_class.CopyOperationResult(
                success=False,
                strategy_used=FileCopyManager_class.CopyStrategy.DIRECT,
                source_path=source_path,
                target_path=target_path,
                file_size=0,
                duration_seconds=0,
                error_message="Source path is not a file"
            )
        
        # Get file size for strategy determination
        file_size = Path(source_path).stat().st_size
        
        # Determine copy strategy
        strategy = FileCopyManager_class.determine_copy_strategy(source_path, target_path, file_size)
        
        # Log operation start with sequence number
        dry_run_prefix = "DRY RUN: " if self.dry_run_mode else ""
        sequence_info = f"[{self.operation_sequence}]"
        
        self._log_status(f"{dry_run_prefix}Starting copy operation {sequence_info}:")
        self._log_status(f"  Source: {source_path}")
        self._log_status(f"  Target: {target_path}")
        self._log_status(f"  Size: {file_size:,} bytes")
        self._log_status(f"  Strategy: {strategy.value}")
        self._log_status(f"  Overwrite: {overwrite}")
        if self.dry_run_mode:
            self._log_status(f"  Mode: DRY RUN SIMULATION")
        
        # Execute appropriate strategy
        if strategy == FileCopyManager_class.CopyStrategy.DIRECT:
            result = self._copy_direct_strategy(source_path, target_path)
        else:  # STAGED strategy with rename-based backup
            result = self._copy_staged_strategy(source_path, target_path, overwrite)
        
        # Log final result with sequence number
        if result.success:
            self._log_status(f"{dry_run_prefix}Copy operation {sequence_info} SUCCESSFUL - {result.bytes_copied:,} bytes in {result.duration_seconds:.2f}s")
        else:
            self._log_status(f"{dry_run_prefix}Copy operation {sequence_info} FAILED - {result.error_message}")
        
        return result
    
    def start_copy_operation(self, operation_name: str, dry_run: bool = False) -> str:
        """
        Start a new copy operation session with dedicated logging and dry run support.
        
        Args:
        -----
        operation_name: Descriptive name for the operation
        dry_run: Whether this is a dry run operation
        
        Returns:
        --------
        str: Operation ID for tracking
        """
        self.operation_id = uuid.uuid4().hex[:8]
        self.operation_logger = FileCopyManager_class.create_copy_operation_logger(self.operation_id)
        self.operation_sequence = 0  # Reset sequence counter for new operation
        self.set_dry_run_mode(dry_run)
        
        dry_run_text = " (DRY RUN SIMULATION)" if dry_run else ""

        self.operation_logger.info("=" * 80)
        self.operation_logger.info(f"COPY OPERATION STARTED: {operation_name}{dry_run_text}")
        self.operation_logger.info(f"Operation ID: {self.operation_id}")
        self.operation_logger.info(f"Mode: {'DRY RUN SIMULATION' if dry_run else 'NORMAL OPERATION'}")
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
            dry_run_text = " (DRY RUN SIMULATION)" if self.dry_run_mode else ""
            
            self.operation_logger.info("=" * 80)
            self.operation_logger.info(f"COPY OPERATION COMPLETED{dry_run_text}")
            self.operation_logger.info(f"Operation ID: {self.operation_id}")
            self.operation_logger.info(f"Files processed successfully: {success_count}")
            self.operation_logger.info(f"Files failed: {error_count}")
            self.operation_logger.info(f"Total bytes processed: {total_bytes:,}")
            self.operation_logger.info(f"Total operations: {self.operation_sequence}")
            if self.dry_run_mode:
                self.operation_logger.info("NOTE: This was a DRY RUN simulation - no actual files were modified")
            self.operation_logger.info(f"Timestamp: {datetime.now().isoformat()}")
            self.operation_logger.info("=" * 80)
            
            # Close the operation logger
            for handler in self.operation_logger.handlers[:]:
                handler.close()
                self.operation_logger.removeHandler(handler)
        
        self.operation_id = None
        self.operation_logger = None
        self.operation_sequence = 0
