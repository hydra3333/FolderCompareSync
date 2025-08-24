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
from ProgressDialog_class import ProgressDialog_class, CopyProgressManager_class

class DeleteOrphansManager_class:
    """
    Comprehensive manager for delete orphans functionality.
    
    Contains both utility functions (as static methods) and dialog interface (as instance methods).
    This keeps all delete orphans functionality organized in one place.
    
    Static Methods (Utilities):
    - File operations: delete_file_to_recycle_bin, delete_file_permanently
    - Permission checking: check_file_permissions, validate_orphan_file_access  
    - Orphan detection: detect_orphaned_files, create_orphan_metadata_dict
    - Data management: refresh_orphan_metadata_status, build_orphan_tree_structure, calculate_orphan_statistics
    
    Instance Methods (Dialog):
    - Dialog management: __init__, setup_dialog, close_dialog
    - UI setup: setup_ui, setup_header_section, etc.
    - Tree management: build_orphan_tree, handle_tree_click, etc.
    - Operations: apply_filter, delete_selected_files, perform_deletion, etc.
    """
    
    # ========================================
    # WINDOWS SHELL API STRUCTURES AND CLASSES
    # ========================================
    # Windows Shell API constants
    FO_DELETE = 0x0003                   # Delete operation
    FOF_ALLOWUNDO = 0x0040               # Allow undo (moves to Recycle Bin)
    FOF_NOCONFIRMATION = 0x0010          # No confirmation dialogs
    FOF_SILENT = 0x0004                  # No progress dialog
    FOF_NOERRORUI = 0x0400               # No error UI dialogs
    class SHFILEOPSTRUCT(Structure):
        """
        Structure for SHFileOperation - Windows Shell file operations.
        Used for moving files to Recycle Bin with proper user feedback.
        """
        _fields_ = [
            ("hwnd", wintypes.HWND),          # Handle to parent window
            ("wFunc", wintypes.UINT),         # Operation type (delete, move, etc.)
            ("pFrom", c_char_p),              # Source file paths (null-terminated)
            ("pTo", c_char_p),                # Destination paths (null for delete)
            ("fFlags", wintypes.WORD),        # Operation flags
            ("fAnyOperationsAborted", wintypes.BOOL),  # Set if user cancelled
            ("hNameMappings", c_void_p),      # Handle to name mappings
            ("lpszProgressTitle", c_char_p),  # Progress dialog title
        ]

    # ========================================================================
    # STATIC UTILITY METHODS - FILE OPERATIONS
    # ========================================================================
    
    @staticmethod
    def delete_file_to_recycle_bin(file_path: str, show_progress: bool = True) -> tuple[bool, str]:
        """
        Move a file to Windows Recycle Bin using SHFileOperation.
        
        Purpose:
        --------
        Safely moves files to Recycle Bin where they can be recovered.
        Uses Windows Shell API for proper integration with Windows Explorer.
        
        Args:
        -----
        file_path: Full path to file to move to Recycle Bin
        show_progress: Whether to show Windows progress dialog
        
        Returns:
        --------
        tuple[bool, str]: (success, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            
            # Prepare file path with double null termination required by SHFileOperation
            file_path_bytes = file_path.encode('utf-8') + b'\0\0'
            
            # Configure operation flags
            flags = DeleteOrphansManager_class.FOF_ALLOWUNDO  # Enable Recycle Bin
            if not show_progress:
                flags |= DeleteOrphansManager_class.FOF_SILENT | DeleteOrphansManager_class.FOF_NOCONFIRMATION
            
            # Create operation structure
            file_op = DeleteOrphansManager_class.SHFILEOPSTRUCT()
            file_op.hwnd = None                    # No parent window
            file_op.wFunc = DeleteOrphansManager_class.FO_DELETE             # Delete operation
            file_op.pFrom = c_char_p(file_path_bytes)  # Source file
            file_op.pTo = None                    # No destination (delete)
            file_op.fFlags = flags                # Operation flags
            file_op.fAnyOperationsAborted = False
            file_op.hNameMappings = None
            file_op.lpszProgressTitle = c_char_p(b"Moving to Recycle Bin...")
            
            # Call Windows Shell API
            result = ctypes.windll.shell32.SHFileOperationA(byref(file_op))
            
            if result == 0 and not file_op.fAnyOperationsAborted:
                return True, ""
            elif file_op.fAnyOperationsAborted:
                return False, "Operation cancelled by user"
            else:
                # Map common error codes to user-friendly messages
                error_messages = {
                    0x71: "File is being used by another process",
                    0x72: "Access denied - insufficient permissions",
                    0x73: "File is read-only or system file",
                    0x74: "Path not found",
                    0x75: "Path too long",
                    0x76: "File name too long",
                    0x78: "Destination path invalid",
                    0x79: "Security error",
                    0x7A: "Source and destination are the same",
                    0x7C: "Path is invalid",
                    0x80: "File already exists",
                    0x81: "Folder is not empty",
                    0x82: "Operation not supported",
                    0x83: "Network path not found",
                    0x84: "Disk full"
                }
                error_msg = error_messages.get(result, f"Shell operation failed with error code: 0x{result:X}")
                return False, error_msg
                
        except Exception as e:
            return False, f"Exception during Recycle Bin operation: {str(e)}"

    @staticmethod
    def delete_file_permanently(file_path: str) -> tuple[bool, str]:
        """
        Permanently delete a file bypassing the Recycle Bin.
        
        Purpose:
        --------
        Immediately removes files from the file system without recovery option.
        Use with caution - files cannot be easily recovered after this operation.
        
        Args:
        -----
        file_path: Full path to file to permanently delete
        
        Returns:
        --------
        tuple[bool, str]: (success, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
                
            # Use Python's built-in os.remove for permanent deletion
            os.remove(file_path)
            return True, ""
            
        except PermissionError:
            return False, "Access denied - file may be read-only or in use by another process"
        except FileNotFoundError:
            return False, "File not found - may have been deleted by another process"
        except OSError as e:
            return False, f"System error during deletion: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error during permanent deletion: {str(e)}"

    @staticmethod
    def check_file_permissions(file_path: str) -> tuple[bool, str]:
        """
        Check if a file can be deleted by testing permissions and access.
        
        Purpose:
        --------
        Pre-validates file deletion capability to provide user feedback
        before attempting actual deletion operations.
        
        Args:
        -----
        file_path: Full path to file to check
        
        Returns:
        --------
        tuple[bool, str]: (can_delete, status_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, "Missing"
                
            # Check if file is accessible
            if not os.access(file_path, os.R_OK):
                return False, "No Read Access"
                
            # Check if file can be deleted
            if not os.access(file_path, os.W_OK):
                return False, "Read-Only"
                
            # Check if parent directory allows deletion
            parent_dir = os.path.dirname(file_path)
            if not os.access(parent_dir, os.W_OK):
                return False, "Directory Read-Only"
                
            # Additional Windows-specific checks using file attributes
            try:
                import stat
                file_stats = os.stat(file_path)
                
                # Check for system or hidden files that might be protected
                if hasattr(stat, 'FILE_ATTRIBUTE_SYSTEM'):
                    # Windows-specific attribute checking would go here
                    # For now, use basic permission checks
                    pass
                    
            except Exception:
                # If detailed checking fails, assume basic permissions are sufficient
                pass
                
            return True, "OK"
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    @staticmethod
    def validate_orphan_file_access(file_path: str) -> tuple[bool, str, dict]:
        """
        Comprehensive validation of orphan file for deletion readiness.
        
        Purpose:
        --------
        Performs detailed validation including existence, permissions, and metadata
        to provide complete status information for orphan file deletion.
        
        Args:
        -----
        file_path: Full path to orphan file to validate
        
        Returns:
        --------
        tuple[bool, str, dict]: (accessible, status_message, metadata_dict)
        """
        try:
            if not os.path.exists(file_path):
                return False, "File Missing", {}
                
            # Get file metadata
            stat_info = os.stat(file_path)
            metadata = {
                'size': stat_info.st_size,
                'modified': stat_info.st_mtime,
                'is_directory': os.path.isdir(file_path)
            }
            
            # Check permissions
            can_delete, permission_status = DeleteOrphansManager_class.check_file_permissions(file_path)
            
            if not can_delete:
                return False, permission_status, metadata
                
            # Check if file is currently in use (Windows-specific)
            try:
                # Try to open file in exclusive mode to check if it's in use
                if os.path.isfile(file_path):
                    with open(file_path, 'r+b'):
                        pass  # File is accessible
            except PermissionError:
                return False, "File In Use", metadata
            except Exception:
                # Other errors are not necessarily blocking
                pass
                
            return True, "OK", metadata
            
        except Exception as e:
            return False, f"Validation Error: {str(e)}", {}
    
    # ========================================================================
    # STATIC UTILITY METHODS - ORPHAN DETECTION AND DATA MANAGEMENT
    # ========================================================================

    @staticmethod
    def detect_orphaned_files(comparison_results: dict, side: str, 
                             active_filter: Optional[str] = None) -> tuple[list[str], dict[str, dict[str, Any]]]: # v001.0017 changed [enhanced return type to include orphan metadata]
        """
        Detect orphaned files from comparison results - files that exist on one side but are missing on the other.
        
        Purpose:
        --------
        Analyzes comparison results to identify files that exist only on the specified side,
        with enhanced logic to distinguish truly orphaned folders from folders that just contain orphaned files. # v001.0017 added [enhanced folder orphan detection]
        
        Args:
        -----
        comparison_results: dictionary of comparison results from main application
        side: LEFT_SIDE_LOWERCASE or RIGHT_SIDE_LOWERCASE - which side to find orphans for
        active_filter: Optional wildcard filter to respect from main application
        
        Returns:
        --------
        tuple[list[str], dict[str, dict]]: (orphaned_paths, orphan_metadata) # v001.0017 changed [enhanced return type]
            orphaned_paths: List of relative paths of orphaned files on the specified side
            orphan_metadata: dict mapping rel_path -> {'is_true_orphan': bool, 'contains_orphans': bool, 'orphan_reason': str} # v001.0017 added [orphan metadata dictionary]
        """
        log_and_flush(logging.DEBUG, f"Entered DeleteOrphansManager_class: detect_orphaned_files")

        orphaned_paths = []
        orphan_metadata = {}  # v001.0017 added [orphan metadata tracking]
        
        if not comparison_results:
            log_and_flush(logging.DEBUG, f"No comparison results available for orphan detection on {side} side")
            return orphaned_paths, orphan_metadata  # v001.0017 changed [return tuple with metadata]
            
        log_and_flush(logging.DEBUG, f"Detecting orphaned files on {side} side from {len(comparison_results)} comparison results")
        
        # v001.0017 added [build folder hierarchy for true orphan detection]
        # First pass: identify all folders and their existence on both sides
        folders_on_side = set()  # v001.0017 added [track folders that exist on specified side]
        folders_on_other_side = set()  # v001.0017 added [track folders that exist on other side]
        
        for rel_path, result in comparison_results.items():
            if not rel_path:  # Skip empty paths
                continue
                
            # Track folder existence for true orphan detection # v001.0017 added [folder existence tracking]
            if side.lower() == C.LEFT_SIDE_LOWERCASE:  # v001.0017 changed [case insensitive comparison]
                if result.left_item and result.left_item.exists and result.left_item.is_folder:
                    folders_on_side.add(rel_path)  # v001.0017 added [track left folders]
                if result.right_item and result.right_item.exists and result.right_item.is_folder:
                    folders_on_other_side.add(rel_path)  # v001.0017 added [track right folders]
            else:  # side.lower() == RIGHT_SIDE_LOWERCASE  # v001.0017 changed [case insensitive comparison]
                if result.right_item and result.right_item.exists and result.right_item.is_folder:
                    folders_on_side.add(rel_path)  # v001.0017 added [track right folders]
                if result.left_item and result.left_item.exists and result.left_item.is_folder:
                    folders_on_other_side.add(rel_path)  # v001.0017 added [track left folders]
        
        # Second pass: identify orphaned items with enhanced metadata # v001.0017 added [enhanced orphan detection]
        for rel_path, result in comparison_results.items():
            if not rel_path:  # Skip empty paths
                continue
                
            # Determine if this item is orphaned on the specified side
            is_orphaned = False
            orphan_reason = ""  # v001.0017 added [track orphan reason]
            
            if side.lower() == C.LEFT_SIDE_LOWERCASE:  # v001.0017 changed [case insensitive comparison]
                # Left orphan: exists in left but missing in right
                is_orphaned = (result.left_item is not None and 
                              result.left_item.exists and
                              (result.right_item is None or not result.right_item.exists))
                if is_orphaned:
                    orphan_reason = "exists in LEFT but missing in RIGHT"  # v001.0017 added [orphan reason tracking]
            elif side.lower() == C.RIGHT_SIDE_LOWERCASE:  # v001.0017 changed [case insensitive comparison]
                # Right orphan: exists in right but missing in left  
                is_orphaned = (result.right_item is not None and
                              result.right_item.exists and
                              (result.left_item is None or not result.left_item.exists))
                if is_orphaned:
                    orphan_reason = "exists in RIGHT but missing in LEFT"  # v001.0017 added [orphan reason tracking]
            
            if is_orphaned:
                # Apply filter if active (consistent with main application filtering)
                if active_filter:
                    filename = rel_path.split('/')[-1]  # Get just the filename
                    if not fnmatch.fnmatch(filename.lower(), active_filter.lower()):
                        continue  # Skip files that don't match the filter
                        
                orphaned_paths.append(rel_path)
                
                # v001.0017 added [determine if this is a true orphan or just contains orphans]
                is_true_orphan = True  # v001.0017 added [assume true orphan initially]
                contains_orphans = False  # v001.0017 added [track if folder contains orphaned children]
                
                # For folders, check if this is a truly orphaned folder or just contains orphans # v001.0017 added [enhanced folder analysis]
                current_item = result.left_item if side.lower() == C.LEFT_SIDE_LOWERCASE else result.right_item
                if current_item and current_item.is_folder:
                    # This is a folder - check if it's truly orphaned or just contains orphans # v001.0017 added [folder orphan analysis]
                    if rel_path in folders_on_other_side:
                        # Folder exists on both sides, so it's not truly orphaned # v001.0017 added [folder exists on both sides]
                        is_true_orphan = False  # v001.0017 added [not a true orphan]
                        contains_orphans = True  # v001.0017 added [but contains orphaned children]
                        orphan_reason += " (folder exists on both sides but contains orphaned children)"  # v001.0017 added [enhanced reason]
                    else:
                        # Folder doesn't exist on other side, so it's truly orphaned # v001.0017 added [folder truly orphaned]
                        is_true_orphan = True  # v001.0017 added [true orphan folder]
                        contains_orphans = True  # v001.0017 added [orphaned folder contains everything as orphans]
                        orphan_reason += " (entire folder is orphaned)"  # v001.0017 added [enhanced reason]
                
                # Store enhanced metadata for this orphaned item # v001.0017 added [store orphan metadata]
                orphan_metadata[rel_path] = {
                    'is_true_orphan': is_true_orphan,  # v001.0017 added [true orphan flag]
                    'contains_orphans': contains_orphans,  # v001.0017 added [contains orphans flag]
                    'orphan_reason': orphan_reason,  # v001.0017 added [detailed reason]
                    'is_folder': current_item.is_folder if current_item else False  # v001.0017 added [item type]
                }
                    
        log_and_flush(logging.INFO, f"Enhanced orphan detection: found {len(orphaned_paths)} orphaned files on {side} side")
        if active_filter:
            log_and_flush(logging.INFO, f"Orphan detection used active filter: {active_filter}")
        
        # v001.0017 added [log enhanced orphan statistics]
        true_orphan_folders = sum(1 for meta in orphan_metadata.values() if meta['is_true_orphan'] and meta['is_folder'])
        contains_orphan_folders = sum(1 for meta in orphan_metadata.values() if not meta['is_true_orphan'] and meta['is_folder'])
        orphan_files = sum(1 for meta in orphan_metadata.values() if not meta['is_folder'])
        
        log_and_flush(logging.DEBUG, f"Enhanced orphan breakdown: \n{true_orphan_folders} truly orphaned folders \n{contains_orphan_folders} folders containing orphans \n{orphan_files} orphaned files")
        log_and_flush(logging.DEBUG, f"Exiting DeleteOrphansManager_class: detect_orphaned_files with sorted(orphaned_paths)=\n{sorted(orphaned_paths)}")
           
        return sorted(orphaned_paths), orphan_metadata  # v001.0017 changed [return tuple with enhanced metadata]
    
    @staticmethod
    def create_orphan_metadata_dict(comparison_results: dict, orphaned_paths: list[str], 
                                   side: str, source_folder: str, 
                                   orphan_detection_metadata: dict[str, dict[str, Any]] = None) -> dict[str, dict[str, Any]]: # v001.0017 changed [added orphan_detection_metadata parameter]
        """
        Create metadata dictionary for orphaned files with validation status and enhanced orphan classification.
        
        Purpose:
        --------
        Builds comprehensive metadata for orphaned files including file information,
        validation status, accessibility, and enhanced orphan classification (true orphan vs contains orphans). # v001.0017 added [enhanced orphan classification]
        
        Args:
        -----
        comparison_results: dictionary of comparison results from main application
        orphaned_paths: List of relative paths of orphaned files
        side: LEFT_SIDE_LOWERCASE or RIGHT_SIDE_LOWERCASE - which side the orphans are on
        source_folder: Full path to the source folder
        orphan_detection_metadata: Enhanced metadata from detect_orphaned_files (optional for backward compatibility) # v001.0017 added [enhanced metadata parameter]
        
        Returns:
        --------
        dict[str, dict]: dictionary mapping rel_path -> metadata dict with validation and enhanced orphan info # v001.0017 changed [enhanced metadata description]
        """
        orphan_metadata = {}
        
        for rel_path in orphaned_paths:
            result = comparison_results.get(rel_path)
            if not result:
                continue
                
            # Get the metadata for the correct side
            if side.lower() == C.LEFT_SIDE_LOWERCASE and result.left_item:  # v001.0017 changed [case insensitive comparison]
                file_metadata = result.left_item
            elif side.lower() == C.RIGHT_SIDE_LOWERCASE and result.right_item:  # v001.0017 changed [case insensitive comparison]
                file_metadata = result.right_item
            else:
                continue  # No metadata available
                
            # Get full file path
            full_path = str(Path(source_folder) / rel_path)
            
            # Validate file accessibility
            accessible, status_msg, validation_metadata = DeleteOrphansManager_class.validate_orphan_file_access(full_path)
            
            # v001.0017 added [get enhanced orphan classification from detection metadata]
            enhanced_orphan_info = orphan_detection_metadata.get(rel_path, {}) if orphan_detection_metadata else {}
            is_true_orphan = enhanced_orphan_info.get('is_true_orphan', True)  # v001.0017 added [default to true for backward compatibility]
            contains_orphans = enhanced_orphan_info.get('contains_orphans', False)  # v001.0017 added [contains orphans flag]
            orphan_reason = enhanced_orphan_info.get('orphan_reason', 'orphaned item')  # v001.0017 added [orphan reason]
            
            # v001.0017 added [determine initial selection based on enhanced orphan classification]
            # True orphans should be selected by default, non-true orphans (folders that just contain orphans) should not
            default_selected = is_true_orphan  # v001.0017 added [smart default selection]
            
            # Create comprehensive metadata entry
            metadata_entry = {
                'rel_path': rel_path,
                'full_path': full_path,
                'name': file_metadata.name,
                'is_folder': file_metadata.is_folder,
                'size': file_metadata.size,
                'date_created': file_metadata.date_created,
                'date_modified': file_metadata.date_modified,
                'sha512': file_metadata.sha512,
                'accessible': accessible,
                'status': status_msg,
                'validation_metadata': validation_metadata,
                'selected': default_selected,  # v001.0017 changed [use smart default selection instead of always True]
                # v001.0017 added [enhanced orphan classification fields]
                'is_true_orphan': is_true_orphan,  # v001.0017 added [true orphan classification]
                'contains_orphans': contains_orphans,  # v001.0017 added [contains orphans flag]
                'orphan_reason': orphan_reason,  # v001.0017 added [detailed orphan reason]
            }
            
            orphan_metadata[rel_path] = metadata_entry
            
        log_and_flush(logging.DEBUG, f"Created enhanced metadata for {len(orphan_metadata)} orphaned files")
        
        # v001.0017 added [log enhanced selection statistics]
        if orphan_detection_metadata:
            true_orphans_selected = sum(1 for m in orphan_metadata.values() if m['is_true_orphan'] and m['selected'])
            contains_orphans_not_selected = sum(1 for m in orphan_metadata.values() if not m['is_true_orphan'] and not m['selected'])
            log_and_flush(logging.DEBUG, f"Enhanced selection: {true_orphans_selected} true orphans auto-selected, {contains_orphans_not_selected} non-true orphans not auto-selected")
        
        return orphan_metadata

    @staticmethod
    def refresh_orphan_metadata_status(orphan_metadata: dict[str, dict[str, Any]]) -> tuple[int, int]:
        """
        Refresh the validation status of orphaned files to detect external changes.
        
        Purpose:
        --------
        Re-validates accessibility and status of orphaned files to handle cases
        where files were deleted, moved, or permissions changed externally.
        
        Args:
        -----
        orphan_metadata: dictionary of orphan metadata to refresh
        
        Returns:
        --------
        tuple[int, int]: (still_accessible_count, changed_count)
        """
        still_accessible = 0
        changed_count = 0
        
        for rel_path, metadata in orphan_metadata.items():
            old_accessible = metadata['accessible']
            old_status = metadata['status']
            
            # Re-validate the file
            accessible, status_msg, validation_metadata = DeleteOrphansManager_class.validate_orphan_file_access(metadata['full_path'])
            
            # Update metadata with current status
            metadata['accessible'] = accessible
            metadata['status'] = status_msg
            metadata['validation_metadata'] = validation_metadata
            
            # Count changes
            if accessible:
                still_accessible += 1
                
            if old_accessible != accessible or old_status != status_msg:
                changed_count += 1
                log_and_flush(logging.DEBUG, f"Status changed for {rel_path}: {old_status} -> {status_msg}")
                
        log_and_flush(logging.INFO, f"Refresh complete: {still_accessible} accessible, {changed_count} status changes detected")
        return still_accessible, changed_count

    @staticmethod
    def build_orphan_tree_structure(orphan_metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """
        Build hierarchical tree structure from orphaned file metadata.
        
        Purpose:
        --------
        Creates a nested dictionary structure representing the folder hierarchy
        of orphaned files for display in the delete orphans dialog tree.
        
        Args:
        -----
        orphan_metadata: dictionary of orphan file metadata
        
        Returns:
        --------
        dict: Nested dictionary representing folder structure
        """
        tree_structure = {}
        
        for rel_path, metadata in orphan_metadata.items():
            if not rel_path:
                continue
                
            path_parts = rel_path.split('/')
            current_level = tree_structure
            
            # Build nested structure
            for i, part in enumerate(path_parts):
                if part not in current_level:
                    # Determine if this is a file or folder
                    is_final_part = (i == len(path_parts) - 1)
                    
                    if is_final_part:
                        # This is the final part - store the metadata
                        current_level[part] = metadata
                    else:
                        # This is a folder - create nested dict
                        current_level[part] = {}
                        
                # Move to next level (only if it's a dict, not metadata)
                if isinstance(current_level[part], dict):
                    current_level = current_level[part]
                    
        log_and_flush(logging.DEBUG, f"Built tree structure with {len(orphan_metadata)} orphaned items")
        return tree_structure

    @staticmethod
    def calculate_orphan_statistics(orphan_metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """
        Calculate statistics for orphaned files including totals, sizes, and selection counts.
        
        Purpose:
        --------
        Provides comprehensive statistics for the delete orphans dialog header
        and status updates including size calculations and selection tracking.
        
        Args:
        -----
        orphan_metadata: dictionary of orphan file metadata
        
        Returns:
        --------
        dict: Statistics including total files, selected files, total size, selected size, etc.
        """
        stats = {
            'total_files': 0,
            'total_folders': 0,
            'selected_files': 0,
            'selected_folders': 0,
            'total_size': 0,
            'selected_size': 0,
            'accessible_files': 0,
            'inaccessible_files': 0,
            'size_warning_threshold': 1024 * 1024 * 1024,  # 1GB warning threshold
            'large_selection_warning': False
        }
        
        for metadata in orphan_metadata.values():
            # Count totals
            if metadata['is_folder']:
                stats['total_folders'] += 1
                if metadata['selected']:
                    stats['selected_folders'] += 1
            else:
                stats['total_files'] += 1
                if metadata['selected']:
                    stats['selected_files'] += 1
                    
            # Calculate sizes (only for files)
            if not metadata['is_folder'] and metadata['size']:
                stats['total_size'] += metadata['size']
                if metadata['selected']:
                    stats['selected_size'] += metadata['size']
                    
            # Count accessibility
            if metadata['accessible']:
                stats['accessible_files'] += 1
            else:
                stats['inaccessible_files'] += 1
                
        # Set warning flags
        if stats['selected_size'] > stats['size_warning_threshold']:
            stats['large_selection_warning'] = True
            
        return stats

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
    
    # ========================================================================
    # INSTANCE METHODS - DIALOG INITIALIZATION AND MANAGEMENT
    # ========================================================================
    
    def __init__(self, parent, orphaned_files, side, source_folder, dry_run_mode, 
                 comparison_results, active_filter=None):
        """
        Initialize the Delete Orphans Manager/Dialog.
        
        Args:
        -----
        parent: Parent window for modal dialog
        orphaned_files: List of relative paths of orphaned files
        side: LEFT_SIDE_LOWERCASE or RIGHT_SIDE_LOWERCASE - which side orphans are on
        source_folder: Full path to source folder
        dry_run_mode: Whether main app is in dry run mode
        comparison_results: Main app comparison results for metadata
        active_filter: Current filter from main app (if any)
        """
        log_and_flush(logging.DEBUG, f"Entered DeleteOrphansManager_class: __init__")
        try:
            self.parent = parent
            self.orphaned_files = orphaned_files.copy()  # Create local copy
            self.side = side.upper()
            self.source_folder = source_folder
            self.dry_run_mode = dry_run_mode  # v001.0013 Keep original for reference only
            self.comparison_results = comparison_results
            self.active_filter = active_filter
            
            # Dialog state variables
            self.deletion_method = tk.StringVar(value="recycle_bin")  # Default to safer option
            self.local_dry_run_mode = tk.BooleanVar(value=dry_run_mode)  # v001.0013 added [local dry run mode for delete orphans dialog]
            self.dialog_filter = tk.StringVar()  # Dialog-specific filter
            self.result = None  # Result of dialog operation
            
            # Large data structures for memory management
            self.orphan_metadata = {}
            self.orphan_tree_data = {}
            self.selected_items = set()
            self.path_to_item_map = {}
            
            # UI References
            self.dialog = None
            self.tree = None
            self.statistics_var = tk.StringVar()
            self.status_log_text = None
            self.status_log_lines = []
            
            # Memory management thresholds (local constants)
            self.LARGE_FILE_LIST_THRESHOLD = C.DELETE_LARGE_FILE_LIST_THRESHOLD
            self.LARGE_TREE_DATA_THRESHOLD = C.DELETE_LARGE_TREE_DATA_THRESHOLD
            self.LARGE_SELECTION_THRESHOLD = C.DELETE_LARGE_SELECTION_THRESHOLD
            
            # Initialize dialog
            log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: __init__: calling 'setup_dialog'")
            self.setup_dialog()
            log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: __init__: returned from 'setup_dialog'")
        except Exception as e:
            log_and_flush(logging.CRITICAL, f"DeleteOrphansManager_class: __init__: error ", e)

        log_and_flush(logging.DEBUG, f"Exiting DeleteOrphansManager_class: __init__")
        
    def setup_dialog(self):
        """Create and configure the modal dialog window."""
        # Create modal dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Delete Orphaned Files - {self.side.upper()} Side")
        
        # Calculate dialog size based on parent
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        dialog_width = int(parent_width * C.DELETE_ORPHANS_DIALOG_WIDTH_PERCENT)
        dialog_height = int(parent_height * C.DELETE_ORPHANS_DIALOG_HEIGHT_PERCENT)
        
        # Position at top of screen like main window
        x = self.parent.winfo_x() + (parent_width - dialog_width) // 2
        y = 0  # Top of screen
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()  # Modal dialog
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)
        
        # Setup UI components
        self.setup_ui()
        
        # Initialize with orphan data
        self.initialize_orphan_data()
        
    def add_status_message(self, message):
        """DeleteOrphansManager_class: Add timestamped message to dialog status log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_line = f"{timestamp} - {message}"
        
        self.status_log_lines.append(status_line)
        
        # Trim to maximum lines
        if len(self.status_log_lines) > C.DELETE_ORPHANS_STATUS_MAX_HISTORY:
            self.status_log_lines = self.status_log_lines[-C.DELETE_ORPHANS_STATUS_MAX_HISTORY:]
            
        # Update text widget
        if self.status_log_text:
            self.status_log_text.config(state=tk.NORMAL)
            self.status_log_text.delete('1.0', tk.END)
            self.status_log_text.insert('1.0', '\n'.join(self.status_log_lines))
            self.status_log_text.config(state=tk.DISABLED)
            self.status_log_text.see(tk.END)
            
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class:: POSTED STATUS MESSAGE: {message}")
        
    def initialize_orphan_data(self):
        """Initialize orphan metadata and build tree structure."""
        if not self.orphaned_files:
            self.add_status_message("No orphaned files found")
            return
            
        self.add_status_message(f"Initializing {len(self.orphaned_files)} orphaned files...")
        
        # Show progress for large datasets
        if len(self.orphaned_files) > 1000:
            progress = ProgressDialog_class(
                self.dialog, 
                "Loading Orphan Files", 
                "Building orphan file tree...",
                max_value=100
            )
            threading.Thread(
                target=self._initialize_data_with_progress, 
                args=(progress,), 
                daemon=True
            ).start()
        else:
            # Small dataset - initialize directly
            self._initialize_data_direct()
            
    def _initialize_data_direct(self):
        """Initialize orphan data directly for small datasets with enhanced orphan classification."""
        # v001.0017 changed [use enhanced detect_orphaned_files method]
        # Get enhanced orphan detection results
        orphaned_paths, orphan_detection_metadata = DeleteOrphansManager_class.detect_orphaned_files(
            self.comparison_results, 
            self.side, 
            self.active_filter
        )
        
        # Update our orphaned_files list with the detected paths
        self.orphaned_files = orphaned_paths  # v001.0017 added [update orphaned files list]
        
        # v001.0017 changed [pass enhanced metadata to create_orphan_metadata_dict]
        # Create metadata with validation and enhanced orphan classification
        self.orphan_metadata = DeleteOrphansManager_class.create_orphan_metadata_dict(
            self.comparison_results, 
            self.orphaned_files, 
            self.side, 
            self.source_folder,
            orphan_detection_metadata  # v001.0017 added [pass enhanced detection metadata]
        )
        
        # Build tree structure
        self.orphan_tree_data = DeleteOrphansManager_class.build_orphan_tree_structure(self.orphan_metadata)
        
        # v001.0017 changed [smart selection based on enhanced orphan classification]
        # Select only true orphans by default, not folders that just contain orphans
        self.selected_items = set()  # v001.0017 changed [start with empty selection]
        for rel_path, metadata in self.orphan_metadata.items():
            if metadata.get('selected', False):  # v001.0017 added [respect smart default selection from metadata]
                self.selected_items.add(rel_path)  # v001.0017 added [add to selection if default selected]
        
        # Log details about inaccessible files
        self.log_inaccessible_files()
        
        # v001.0017 added [log enhanced orphan classification results]
        true_orphans = sum(1 for m in self.orphan_metadata.values() if m.get('is_true_orphan', False))
        contains_orphans = sum(1 for m in self.orphan_metadata.values() if not m.get('is_true_orphan', True))
        auto_selected = len(self.selected_items)
        
        self.add_status_message(f"Enhanced classification: {true_orphans} true orphans, {contains_orphans} folders containing orphans")
        self.add_status_message(f"Smart selection: {auto_selected} items auto-selected (true orphans only)")
        
        # Update UI
        self.build_orphan_tree()
        self.update_statistics()
        
        # Log initialization results
        accessible_count = sum(1 for m in self.orphan_metadata.values() if m['accessible'])
        self.add_status_message(f"Initialization complete: {accessible_count} accessible files")

    def _initialize_data_with_progress(self, progress):
        """Initialize orphan data with progress feedback for large datasets using enhanced orphan classification."""
        try:
            progress.update_progress(10, "Performing enhanced orphan detection...")  # v001.0017 changed [enhanced detection message]
            
            # v001.0017 changed [use enhanced detect_orphaned_files method]
            # Get enhanced orphan detection results
            orphaned_paths, orphan_detection_metadata = DeleteOrphansManager_class.detect_orphaned_files(
                self.comparison_results, 
                self.side, 
                self.active_filter
            )
            
            # Update our orphaned_files list with the detected paths
            self.orphaned_files = orphaned_paths  # v001.0017 added [update orphaned files list]
            
            progress.update_progress(30, "Creating enhanced file metadata...")  # v001.0017 changed [enhanced metadata message]
            
            # v001.0017 changed [pass enhanced metadata to create_orphan_metadata_dict]
            # Create metadata with validation and enhanced orphan classification
            self.orphan_metadata = DeleteOrphansManager_class.create_orphan_metadata_dict(
                self.comparison_results, 
                self.orphaned_files, 
                self.side.upper(), 
                self.source_folder,
                orphan_detection_metadata  # v001.0017 added [pass enhanced detection metadata]
            )
            
            progress.update_progress(60, "Building tree structure...")
            
            # Build tree structure
            self.orphan_tree_data = DeleteOrphansManager_class.build_orphan_tree_structure(self.orphan_metadata)
            
            progress.update_progress(80, "Setting up smart selections...")  # v001.0017 changed [smart selection message]
            
            # v001.0017 changed [smart selection based on enhanced orphan classification]
            # Select only true orphans by default, not folders that just contain orphans
            self.selected_items = set()  # v001.0017 changed [start with empty selection]
            for rel_path, metadata in self.orphan_metadata.items():
                if metadata.get('selected', False):  # v001.0017 added [respect smart default selection from metadata]
                    self.selected_items.add(rel_path)  # v001.0017 added [add to selection if default selected]
            
            progress.update_progress(90, "Updating display...")
            
            # Update UI in main thread
            self.dialog.after(0, self._finalize_initialization_enhanced)  # v001.0017 changed [use enhanced finalization]
            
            progress.update_progress(100, "Complete")
            
        except Exception as e:
            log_and_flush(logging.ERROR, f"Error during enhanced orphan data initialization: {e}")  # v001.0017 changed [enhanced error message]
            self.dialog.after(0, lambda: self.add_status_message(f"Enhanced initialization error: {str(e)}"))  # v001.0017 changed [enhanced error message]
        finally:
            progress.close()
            
    def _finalize_initialization_enhanced(self):  # v001.0017 added [enhanced finalization for large datasets]
        """Finalize enhanced initialization in orphan main thread for large datasets."""
        # Log details about inaccessible files
        self.log_inaccessible_files()
        
        # v001.0017 added [log enhanced orphan classification results for large datasets]
        true_orphans = sum(1 for m in self.orphan_metadata.values() if m.get('is_true_orphan', False))
        contains_orphans = sum(1 for m in self.orphan_metadata.values() if not m.get('is_true_orphan', True))
        auto_selected = len(self.selected_items)
        
        self.add_status_message(f"Enhanced classification: {true_orphans} true orphans, {contains_orphans} folders containing orphans")
        self.add_status_message(f"Smart selection: {auto_selected} items auto-selected (true orphans only)")
        
        self.build_orphan_tree()
        self.update_statistics()
        
        # Log results
        accessible_count = sum(1 for m in self.orphan_metadata.values() if m['accessible'])
        self.add_status_message(f"Enhanced initialization complete: {accessible_count} accessible files")

    def set_enhanced_detection_metadata(self, orphan_detection_metadata: dict[str, dict[str, Any]]): # v001.0017 added [method to accept enhanced detection metadata]
        """
        Set enhanced detection metadata for improved orphan classification.
        
        Purpose:
        --------
        Allows the dialog to receive enhanced orphan classification metadata from the 
        main application's detect_orphaned_files method for better selection logic.
        
        Args:
        -----
        orphan_detection_metadata: Enhanced metadata from detect_orphaned_files containing
                                  is_true_orphan, contains_orphans, and orphan_reason for each item
        """
        self.enhanced_detection_metadata = orphan_detection_metadata  # v001.0017 added [store enhanced metadata]
        
        # v001.0017 added [update existing orphan metadata with enhanced classification]
        # If we already have orphan_metadata, enhance it with the new classification data
        if hasattr(self, 'orphan_metadata') and self.orphan_metadata:
            for rel_path, enhanced_info in orphan_detection_metadata.items():
                if rel_path in self.orphan_metadata:
                    # Update existing metadata with enhanced classification
                    self.orphan_metadata[rel_path].update({
                        'is_true_orphan': enhanced_info.get('is_true_orphan', True),
                        'contains_orphans': enhanced_info.get('contains_orphans', False),
                        'orphan_reason': enhanced_info.get('orphan_reason', 'orphaned item'),
                    })
                    
                    # v001.0017 added [update selection based on enhanced classification]
                    # Adjust selection based on true orphan status
                    if enhanced_info.get('is_true_orphan', True):
                        # True orphans should be selected if accessible
                        if self.orphan_metadata[rel_path].get('accessible', False):
                            self.orphan_metadata[rel_path]['selected'] = True
                            self.selected_items.add(rel_path)
                    else:
                        # Non-true orphans (folders containing orphans) should not be auto-selected
                        self.orphan_metadata[rel_path]['selected'] = False
                        self.selected_items.discard(rel_path)
            
            # v001.0017 added [log enhanced classification update results]
            true_orphans_updated = sum(1 for m in self.orphan_metadata.values() if m.get('is_true_orphan', False))
            contains_orphans_updated = sum(1 for m in self.orphan_metadata.values() if not m.get('is_true_orphan', True))
            selected_after_update = len(self.selected_items)
            
            self.add_status_message(f"Enhanced classification applied: {true_orphans_updated} true orphans, {contains_orphans_updated} folders containing orphans")
            self.add_status_message(f"Selection updated: {selected_after_update} items selected based on enhanced classification")
            
            # v001.0017 added [rebuild tree and update display with enhanced classification]
            # Rebuild tree display to reflect enhanced classification
            if hasattr(self, 'tree') and self.tree:
                self.build_orphan_tree()
                self.update_statistics()
        else:
            # v001.0017 added [store for later use during initialization]
            self.add_status_message("Enhanced detection metadata received - will be applied during initialization")

    def _cleanup_large_data(self):
        """Clean up large data structures based on thresholds."""
        # v001.0018 added [debug logging before cleanup]
        log_and_flush(logging.DEBUG, f"_cleanup_large_data starting:")
        log_and_flush(logging.DEBUG, f"  self.orphaned_files length: {len(self.orphaned_files) if hasattr(self, 'orphaned_files') and self.orphaned_files else 0}")
        log_and_flush(logging.DEBUG, f"  self.orphan_tree_data length: {len(self.orphan_tree_data) if hasattr(self, 'orphan_tree_data') and self.orphan_tree_data else 0}")
        log_and_flush(logging.DEBUG, f"  self.orphan_metadata length: {len(self.orphan_metadata) if hasattr(self, 'orphan_metadata') and self.orphan_metadata else 0}")
        log_and_flush(logging.DEBUG, f"  self.comparison_results length: {len(self.comparison_results) if hasattr(self, 'comparison_results') and self.comparison_results else 0}")
        
        cleaned_items = []
        
        if hasattr(self, 'orphaned_files') and len(self.orphaned_files) > self.LARGE_FILE_LIST_THRESHOLD: # v001.0018 changed [add hasattr check]
            self.orphaned_files.clear()
            cleaned_items.append("file list")
            
        if hasattr(self, 'orphan_tree_data') and len(self.orphan_tree_data) > self.LARGE_TREE_DATA_THRESHOLD: # v001.0018 changed [add hasattr check]
            self.orphan_tree_data.clear()
            cleaned_items.append("tree data")
            
        if hasattr(self, 'selected_items') and len(self.selected_items) > self.LARGE_SELECTION_THRESHOLD: # v001.0018 changed [add hasattr check]
            self.selected_items.clear()
            cleaned_items.append("selections")
            
        if hasattr(self, 'orphan_metadata') and len(self.orphan_metadata) > self.LARGE_FILE_LIST_THRESHOLD: # v001.0018 changed [add hasattr check]
            self.orphan_metadata.clear()
            cleaned_items.append("metadata")
            
        if hasattr(self, 'path_to_item_map') and len(self.path_to_item_map) > self.LARGE_TREE_DATA_THRESHOLD: # v001.0018 changed [add hasattr check]
            self.path_to_item_map.clear()
            cleaned_items.append("path mappings")
            
        # v001.0018 added [explicitly do NOT clean self.comparison_results as it belongs to parent application]
        # NOTE: self.comparison_results is passed from parent application and should NOT be modified
        
        if cleaned_items:
            log_and_flush(logging.DEBUG, f"Cleaned up large data structures: {', '.join(cleaned_items)}")
        else:
            log_and_flush(logging.DEBUG, f"No large data structures needed cleanup") # v001.0018 added [log when no cleanup needed]

    def close_dialog(self):
            """Close dialog with proper cleanup."""
            try:
                # v001.0018 added [set result to cancelled only if no result was previously set]
                # This handles all close scenarios: Cancel button, X button, ESC key, etc.
                if not hasattr(self, 'result') or self.result is None:
                    self.result = "cancelled".lower()  # Default to cancelled for any non-deletion close
                    log_and_flush(logging.DEBUG, f"Dialog closed without explicit result - setting to 'cancelled'")
                else:
                    log_and_flush(logging.DEBUG, f"Dialog closing with existing result: {self.result}")

                # v001.0018 added [debug logging during dialog cleanup]
                log_and_flush(logging.DEBUG, f"DeleteOrphansManager close_dialog called")
                log_and_flush(logging.DEBUG, f"  orphan_metadata length: {len(self.orphan_metadata) if self.orphan_metadata else 0}")
                log_and_flush(logging.DEBUG, f"  comparison_results is None: {self.comparison_results is None}")
                log_and_flush(logging.DEBUG, f"  comparison_results length: {len(self.comparison_results) if self.comparison_results else 0}")

                # Clean up large data structures
                self._cleanup_large_data()

                # v001.0018 added [debug logging after cleanup]
                log_and_flush(logging.DEBUG, f"After _cleanup_large_data:")
                log_and_flush(logging.DEBUG, f"  comparison_results is None: {self.comparison_results is None}")
                log_and_flush(logging.DEBUG, f"  comparison_results length: {len(self.comparison_results) if self.comparison_results else 0}")
                
                # Close dialog
                if self.dialog:
                    self.dialog.grab_release()
                    self.dialog.destroy()
                    
            except Exception as e:
                log_and_flush(logging.ERROR, f"Error during dialog cleanup: {e}")
                # v001.0018 added [additional debug logging for cleanup exceptions]
                log_and_flush(logging.ERROR, f"Cleanup exception traceback: {traceback.format_exc()}")
            finally:
                # Ensure dialog is closed even if cleanup fails
                try:
                    if self.dialog:
                        self.dialog.destroy()
                except:
                    pass

    # ========================================================================
    # INSTANCE METHODS - UI SETUP AND CONFIGURATION
    # ========================================================================
    
    def setup_ui(self):
        """Setup all UI components for the delete orphans dialog."""
        # v001.0014 added [create scaled fonts for delete orphans dialog]
        # Create scaled fonts for this dialog
        log_and_flush(logging.DEBUG, "ENTERED DeleteOrphansManager_class.setup_ui")

        default_font = tkfont.nametofont("TkDefaultFont") # v001.0014 added [create scaled fonts for delete orphans dialog]
        
        self.scaled_label_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_label_font.configure(size=C.SCALED_LABEL_FONT_SIZE) # v001.0014 added [create scaled fonts for delete orphans dialog]
        # Create a bold version
        self.scaled_label_font_bold = self.scaled_label_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_label_font_bold.configure(weight="bold")
        
        self.scaled_entry_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_entry_font.configure(size=C.SCALED_ENTRY_FONT_SIZE) # v001.0014 added [create scaled fonts for delete orphans dialog]
        
        self.scaled_checkbox_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_checkbox_font.configure(size=C.SCALED_CHECKBOX_FONT_SIZE) # v001.0014 added [create scaled fonts for delete orphans dialog]
        # Create a bold version
        self.scaled_checkbox_font_bold = self.scaled_checkbox_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_checkbox_font_bold.configure(weight="bold")
        
        self.scaled_button_font = default_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_button_font.configure(size=C.SCALED_BUTTON_FONT_SIZE)
        # Create a bold version
        self.scaled_button_font_bold = self.scaled_button_font.copy() # v001.0014 added [create scaled fonts for delete orphans dialog]
        self.scaled_button_font_bold.configure(weight="bold")
        
        # Configure tree row height for this dialog's treeviews # v001.0015 added [tree row height control for compact display]
        dialog_style = ttk.Style(self.dialog) # v001.0015 added [tree row height control for compact display]
        dialog_style.configure("Treeview", rowheight=C.TREE_ROW_HEIGHT) # v001.0015 added [tree row height control for compact display]
        
        # v001.0016 added [create button styles for delete orphans dialog]
        # Create button styles for this dialog
        dialog_style.configure("DeleteOrphansDefaultNormal.TButton", font=self.scaled_button_font) # v001.0016 added [create button styles for delete orphans dialog]
        dialog_style.configure("DeleteOrphansRedBold.TButton", foreground="red", font=self.scaled_button_font_bold) # v001.0014 added [create button style for delete orphans dialog with scaled font]
        dialog_style.configure("DeleteOrphansBlueBold.TButton", foreground="blue", font=self.scaled_button_font_bold) # v001.0014 added [create button style for delete orphans dialog with scaled font]

        dialog_style.configure("DeleteOrphansCheckbutton.TCheckbutton", font=self.scaled_checkbox_font)
        dialog_style.configure("DeleteOrphansLabel.TLabel", font=self.scaled_label_font)
        dialog_style.configure("DeleteOrphansSmallLabel.TLabel", font=(self.scaled_label_font.cget("family"), int(self.scaled_label_font.cget("size")) - 1))
        dialog_style.configure("DeleteOrphansLabelBold.TLabel", font=self.scaled_label_font_bold)
        dialog_style.configure("DeleteOrphansEntry.TEntry", font=self.scaled_entry_font)

        # Main container
        log_and_flush(logging.DEBUG, "BEFORE THE CREATE AND PACK main_frame")
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8) # v001.0014 changed [tightened padding from padx=10, pady=10 to padx=8, pady=8]
        log_and_flush(logging.DEBUG, "AFTER THE CREATE AND PACK main_frame")
        
        # Header section with explanation and statistics
        log_and_flush(logging.DEBUG, "BEFORE setup_header_section")
        self.setup_header_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_header_section")
        
        # Local dry run mode section # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "BEFORE setup_local_dry_run_section")
        self.setup_local_dry_run_section(main_frame) # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "AFTER setup_local_dry_run_section")
        
        # Deletion method selection
        log_and_flush(logging.DEBUG, "BEFORE setup_deletion_method_section")
        self.setup_deletion_method_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_deletion_method_section")
        
        # Filter controls
        log_and_flush(logging.DEBUG, "BEFORE setup_filter_section")
        self.setup_filter_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_filter_section")
        
        # Main tree area
        log_and_flush(logging.DEBUG, "BEFORE setup_tree_section")
        self.setup_tree_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_tree_section")
        
        # Status log area
        log_and_flush(logging.DEBUG, "BEFORE setup_status_section")
        self.setup_status_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_status_section")
        
        # Bottom buttons
        log_and_flush(logging.DEBUG, "BEFORE setup_button_section")
        self.setup_button_section(main_frame)
        log_and_flush(logging.DEBUG, "AFTER setup_button_section")

        log_and_flush(logging.DEBUG, "EXITING DeleteOrphansManager_class.setup_ui")

    def setup_header_section(self, parent):
        """Setup header section with explanation and statistics."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Explanatory text
        side_text = self.side.upper()
        opposite_side = C.RIGHT_SIDE_UPPERCASE if self.side.lower() == C.LEFT_SIDE_LOWERCASE else C.LEFT_SIDE_UPPERCASE
        
        explanation = (
            f"The following orphaned files exist in {side_text} but are missing in {opposite_side}.\n"
            f"Select which files to delete, then click 'DELETE SELECTED ORPHANED FILES' to remove them permanently."
        )
        
        explanation_label = ttk.Label(
            header_frame, 
            text=explanation, 
            justify=tk.CENTER,
            style="DeleteOrphansLabel.TLabel"  # ✅ Use style instead of font parameter
        )
        explanation_label.pack(pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Statistics display
        self.statistics_var.set("Loading orphaned files...")
        statistics_label = ttk.Label(
            header_frame,
            textvariable=self.statistics_var,
            foreground="blue",
            style="DeleteOrphansLabelBold.TLabel"  # ✅ Use bold style
        )
        statistics_label.pack(pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]

    def setup_local_dry_run_section(self, parent): # v001.0013 added [local dry run mode section for delete orphans dialog]
        """Setup local dry run mode section with checkbox.""" # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "1. ENTERED DeleteOrphansManager_class.setup_local_dry_run_section")

        log_and_flush(logging.DEBUG, "2. BEFORE create and pack dry_run_frame")
        dry_run_frame = ttk.LabelFrame(parent, text="Local Operation Mode", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        dry_run_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        log_and_flush(logging.DEBUG, "3. AFTER create and pack dry_run_frame")
        
        # Checkbox for local dry run mode # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "4. BEFORE create and pack dry_run_cb checkbutton create")
        dry_run_cb = ttk.Checkbutton( # v001.0013 added [local dry run mode section for delete orphans dialog]
            dry_run_frame, # v001.0013 added [local dry run mode section for delete orphans dialog]
            text="DRY RUN Only (simulate deletion without actually removing files)", # v001.0013 added [local dry run mode section for delete orphans dialog]
            variable=self.local_dry_run_mode, # v001.0013 added [local dry run mode section for delete orphans dialog]
            command=self.on_local_dry_run_changed, # v001.0013 added [local dry run mode section for delete orphans dialog]
            style="DeleteOrphansCheckbutton.TCheckbutton" # v001.0014 changed [use scaled checkbox font instead of default]
        ) # v001.0013 added [local dry run mode section for delete orphans dialog]
        dry_run_cb.pack(side=tk.LEFT, padx=(0, 10)) # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "5. AFTER create and pack dry_run_cb checkbutton create")
        
        # Status indicator showing main app setting # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "6. BEFORE create and pack main_app_text create")
        main_app_text = f"(Main app DRY RUN mode: {'ON' if self.dry_run_mode else 'OFF'})" # v001.0013 added [local dry run mode section for delete orphans dialog]
        main_app_label = ttk.Label( # v001.0013 added [local dry run mode section for delete orphans dialog]
            dry_run_frame, # v001.0013 added [local dry run mode section for delete orphans dialog]
            text=main_app_text, # v001.0013 added [local dry run mode section for delete orphans dialog]
            foreground="gray", # v001.0013 added [local dry run mode section for delete orphans dialog]
            style="DeleteOrphansSmallLabel.TLabel"
        ) # v001.0013 added [local dry run mode section for delete orphans dialog]
        main_app_label.pack(side=tk.LEFT) # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "7. AFTER create and pack main_app_text create")
        
        # Explanation text # v001.0013 added [local dry run mode section for delete orphans dialog]
        log_and_flush(logging.DEBUG, "8. BEFORE create and pack explanation_label create")
        explanation_label = ttk.Label( # v001.0013 added [local dry run mode section for delete orphans dialog]
            dry_run_frame, # v001.0013 added [local dry run mode section for delete orphans dialog]
            text="This setting is local to this dialog and overrides the main app setting", # v001.0013 added [local dry run mode section for delete orphans dialog]
            foreground="blue", # v001.0013 added [local dry run mode section for delete orphans dialog]
            style="DeleteOrphansSmallLabel.TLabel"
        ) # v001.0013 added [local dry run mode section for delete orphans dialog]
        explanation_label.pack(pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
        log_and_flush(logging.DEBUG, "9. AFTER create and pack explanation_label create")
        log_and_flush(logging.DEBUG, "10. EXITING DeleteOrphansManager_class.setup_local_dry_run_section")

    def setup_deletion_method_section(self, parent):
        """Setup deletion method selection with radio buttons."""
        method_frame = ttk.LabelFrame(parent, text="Deletion Method", padding=8) # v001.0014 changed [tightened padding from padding=10 to padding=8]
        method_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Radio button frame
        radio_frame = ttk.Frame(method_frame)
        radio_frame.pack()
        
        # Recycle Bin option (default, safer)
        recycle_rb = ttk.Radiobutton(
            radio_frame,
            text="Move to Recycle Bin (recommended)",
            variable=self.deletion_method,
            value="recycle_bin",
            style="DeleteOrphansCheckbutton.TCheckbutton"  # ✅ Reuse checkbox style for radio buttons        
        )
        recycle_rb.pack(side=tk.LEFT, padx=(0, 20))

        # Permanent deletion option
        permanent_rb = ttk.Radiobutton(
            radio_frame,
            text="Permanent Deletion (cannot be undone)",
            variable=self.deletion_method,
            value="permanent",
            style="DeleteOrphansCheckbutton.TCheckbutton"  # ✅ Reuse checkbox style for radio buttons
        )
        permanent_rb.pack(side=tk.LEFT)
        
        # Add warning text
        warning_label = ttk.Label(
            method_frame,
            text="⚠ Permanent deletion cannot be undone - files will be lost forever",
            foreground="red",
            style="DeleteOrphansSmallLabel.TLabel"  # ✅ Use style instead of font tuple
        )
        warning_label.pack(pady=(3, 0)) # v001.0014 changed [tightened padding from pady=(5, 0) to pady=(3, 0)]
        
    def setup_filter_section(self, parent):
        """Setup dialog-specific filter controls."""
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Filter label and entry
        ttk.Label(filter_frame, text="Filter Files:", style="DeleteOrphansLabel.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        filter_entry = ttk.Entry(filter_frame, textvariable=self.dialog_filter, width=20, style="DeleteOrphansEntry.TEntry")
        filter_entry.pack(side=tk.LEFT, padx=(0, 5))
        filter_entry.bind('<Return>', lambda e: self.apply_filter())
        
        # Filter buttons
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        ttk.Button(filter_frame, text="Clear Filter", command=self.clear_filter, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 10)) # v001.0016 changed [use delete orphans button style]
        
        # Filter status
        self.filter_status_var = tk.StringVar()
        if self.active_filter:
            self.filter_status_var.set(f"(Main app filter active: {self.active_filter})")
        else:
            self.filter_status_var.set("")
            
        filter_status_label = ttk.Label(filter_frame, textvariable=self.filter_status_var,
                                       foreground="gray", style="DeleteOrphansSmallLabel.TLabel")
        filter_status_label.pack(side=tk.LEFT)
        
    def setup_tree_section(self, parent):
        """Setup main tree display area."""
        tree_frame = ttk.LabelFrame(parent, text="Orphaned Files", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create tree with scrollbar
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_container, show='tree headings', selectmode='none')
        self.tree.heading('#0', text='File/Folder Structure', anchor=tk.W)
        self.tree.column('#0', width=C.DELETE_ORPHANS_TREE_STRUCTURE_WIDTH, minwidth=200)
        
        # Setup tree columns
        self.setup_tree_columns()
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind tree events
        self.tree.bind('<Button-1>', self.handle_tree_click)
        
    def setup_tree_columns(self):
        """Setup tree columns for metadata display."""
        self.tree['columns'] = ('size', 'date_created', 'date_modified', 'status')
        
        # Column headers
        self.tree.heading('size', text='Size', anchor=tk.E)
        self.tree.heading('date_created', text='Date Created', anchor=tk.CENTER)
        self.tree.heading('date_modified', text='Date Modified', anchor=tk.CENTER)
        self.tree.heading('status', text='Status', anchor=tk.W)
        
        # Column widths
        self.tree.column('size', width=C.DELETE_ORPHANS_TREE_SIZE_WIDTH, minwidth=60, anchor=tk.E)
        self.tree.column('date_created', width=150, minwidth=120, anchor=tk.CENTER)
        self.tree.column('date_modified', width=150, minwidth=120, anchor=tk.CENTER)
        self.tree.column('status', width=C.DELETE_ORPHANS_TREE_STATUS_WIDTH, minwidth=80, anchor=tk.W)
        
    def setup_status_section(self, parent):
        """Setup status log area."""
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding=5)
        status_frame.pack(fill=tk.X, pady=(0, 8)) # v001.0014 changed [tightened padding from pady=(0, 10) to pady=(0, 8)]
        
        # Status header with export button
        status_header = ttk.Frame(status_frame)
        status_header.pack(fill=tk.X, pady=(0, 3)) # v001.0014 changed [tightened padding from pady=(0, 5) to pady=(0, 3)]
        
        ttk.Label(status_header, text=f"Operation History ({C.DELETE_ORPHANS_STATUS_MAX_HISTORY:,} lines max):", 
                 style="DeleteOrphansLabel.TLabel").pack(side=tk.LEFT)
        ttk.Button(status_header, text="Export Log", command=self.export_status_log, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.RIGHT)
        
        # Status log text area
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=tk.X)
        
        self.status_log_text = tk.Text(
            status_container,
            height=C.DELETE_ORPHANS_STATUS_LINES,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier", C.SCALED_STATUS_MESSAGE_FONT_SIZE),  # tk.Text supports font parameter
            bg="#f8f8f8",
            fg="#333333"
        )
        
        status_scroll = ttk.Scrollbar(status_container, orient=tk.VERTICAL, command=self.status_log_text.yview)
        self.status_log_text.configure(yscrollcommand=status_scroll.set)
        
        self.status_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_button_section(self, parent):
        """Setup bottom button section."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        # Left side utility buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="Select All", command=self.select_all_items, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        ttk.Button(left_buttons, text="Clear All", command=self.clear_all_items, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        ttk.Button(left_buttons, text="Refresh Orphans Tree", command=self.refresh_orphans_tree, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.LEFT, padx=(0, 5)) # v001.0016 changed [use delete orphans button style]
        
        # Right side action buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="Cancel", command=self.close_dialog, style="DeleteOrphansDefaultNormal.TButton").pack(side=tk.RIGHT, padx=(5, 0)) # v001.0016 changed [use delete orphans button style]
        
        # Delete button with conditional text based on local dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        delete_text = "SIMULATE DELETION" if is_local_dry_run else "DELETE SELECTED ORPHANED FILES" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        self.delete_button = ttk.Button( # v001.0013 changed [store button reference for dynamic updates]
            right_buttons, 
            text=delete_text, 
            command=self.delete_selected_files
        )
        self.delete_button.pack(side=tk.RIGHT, padx=(5, 0)) # v001.0013 changed [use stored button reference]
        
        # Style the delete button based on local dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            # Use blue style for simulation
            self.delete_button.configure(style="DeleteOrphansBlueBold.TButton") # v001.0014 changed [use local scaled button style instead of main app style]
        else:
            # Use red style for actual deletion
            self.delete_button.configure(style="DeleteOrphansRedBold.TButton") # v001.0014 changed [use local scaled button style instead of main app style]
                                                                                                          
    def export_status_log(self):
        """Export status log to clipboard and optionally to file."""
        if not self.status_log_lines:
            messagebox.showinfo("Export Status Log", "No status log data to export.")
            return
        
        try:
            # Copy to clipboard
            export_text = "\n".join(self.status_log_lines)
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(export_text)
            self.dialog.update()
            
            # Ask about saving to file
            response = messagebox.askyesnocancel(
                "Export Status Log",
                f"Status log ({len(self.status_log_lines):,} lines) copied to clipboard!\n\n"
                "Would you also like to save to a file?"
            )
            
            if response is True:  # Yes - save to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                default_filename = f"foldercomparesync_delete_{self.side.upper()}_{timestamp}.log"
                
                file_path = filedialog.asksaveasfilename(
                    title="Save Delete Orphans Log",
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
                    
        except Exception as e:
            error_msg = f"Failed to export status log: {str(e)}"
            self.add_status_message(f"ERROR: {error_msg}")
            messagebox.showerror("Export Error", error_msg)

    # ========================================================================
    # INSTANCE METHODS - TREE BUILDING AND INTERACTION
    # ========================================================================
    
    def build_orphan_tree(self):
        """Build the orphan file tree display."""
        log_and_flush(logging.DEBUG, f"Entered DeleteOrphansManager_class: build_orphan_tree")

        if not self.tree:
            log_and_flush(logging.DEBUG, f"Exiting DeleteOrphansManager_class: build_orphan_tree: tree is False or None")
            return
            
        # Clear existing tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.path_to_item_map.clear()
        
        if not self.orphan_tree_data:
            self.add_status_message("No Orphan file tree data to display")
            log_and_flush(logging.DEBUG, f"Exiting DeleteOrphansManager_class: build_orphan_tree: No Orphan file tree data to display")
            return
            
        # Build tree from structure
        self.add_status_message("Building Orphan file tree...")
        
        # Use alphabetical ordering for stability
        log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: build_orphan_tree: Building orphan file tree by calling populate_orphan_tree...")
        self.populate_orphan_tree(self.tree, self.orphan_tree_data, '', '')
        log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: build_orphan_tree: Built orphan file tree by calling populate_orphan_tree...")
        
        # Expand all items by default
        self.expand_all_tree_items()
        
        # Update display with selections
        self.update_tree_display()
        
        self.add_status_message(f"Orphan file tree built with {len(self.orphan_metadata)} items")
        log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: build_orphan_tree: Orphan file tree built with {len(self.orphan_metadata)} items")
        log_and_flush(logging.DEBUG, f"Exiting DeleteOrphansManager_class: build_orphan_tree")
        
    def populate_orphan_tree(self, tree, structure, parent_id, current_path):
        """
        Recursively populate tree with orphan file structure using enhanced orphan classification.
        
        Purpose:
        --------
        Creates tree display that respects true orphan status vs folders that just contain orphaned files. # v001.0017 changed [enhanced orphan-aware tree population]
        Only truly orphaned folders are auto-ticked, while folders that just contain orphaned files are not.
        """
        if not structure:
            log_and_flush(logging.DEBUG, f"Exiting DeleteOrphansManager_class: populate_orphan_tree: structure False or None")
            return
            
        # Process items in alphabetical order for stability
        for name in sorted(structure.keys()):
            content = structure[name]
            
            # Build the relative path for this item
            item_rel_path = current_path + ('/' if current_path else '') + name
            
            if isinstance(content, dict) and 'rel_path' in content:
                # This is a file metadata entry
                metadata = content
                
                # Format file display
                size_str = self.format_size(metadata['size']) if metadata['size'] else ""
                date_created_str = self.format_timestamp(metadata['date_created'])
                date_modified_str = self.format_timestamp(metadata['date_modified'])
                status_str = metadata['status']
                
                # v001.0017 changed [enhanced file checkbox logic based on true orphan status]
                # Create item text with checkbox based on selection and accessibility
                if metadata['accessible']:
                    # v001.0017 added [show enhanced orphan reason in status for debugging]
                    if hasattr(metadata, 'orphan_reason') and __debug__:
                        status_str += f" ({metadata.get('orphan_reason', 'orphaned')})"
                    
                    checkbox = "☑" if metadata['rel_path'] in self.selected_items else "☐"
                    item_text = f"{checkbox} {name}"
                    tags = ()
                else:
                    # Inaccessible files - no checkbox, grayed out
                    item_text = f"{name} (inaccessible)"
                    tags = ('inaccessible',)
                
                # Insert file item
                log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: populate_orphan_tree: Insert file item_text='{item_text}' metadata['rel_path']='{metadata['rel_path']}'")
                item_id = tree.insert(
                    parent_id, 
                    tk.END, 
                    text=item_text,
                    values=(size_str, date_created_str, date_modified_str, status_str),
                    tags=tags
                )
                
                # Store path mapping
                self.path_to_item_map[metadata['rel_path']] = item_id
                
            else:
                # This is a folder - create folder entry and recurse
                # v001.0017 changed [enhanced folder checkbox logic based on true orphan classification]
                
                # Check if this folder has metadata (is an orphaned folder)
                folder_metadata = self.orphan_metadata.get(item_rel_path)
                
                if folder_metadata:
                    # This folder is in our orphan metadata
                    if folder_metadata.get('is_true_orphan', False):
                        # Truly orphaned folder - should be ticked if selected and accessible
                        if folder_metadata.get('accessible', False) and folder_metadata.get('selected', False):
                            folder_checkbox = "☑"
                        elif folder_metadata.get('accessible', False):
                            folder_checkbox = "☐"
                        else:
                            folder_checkbox = ""  # Inaccessible folder
                            
                        # v001.0017 added [show enhanced status for truly orphaned folders]
                        folder_status = f"True Orphan Folder"
                        if __debug__ and folder_metadata.get('orphan_reason'):
                            folder_status += f" ({folder_metadata['orphan_reason']})"
                    else:
                        # Folder exists on both sides but contains orphaned files - should NOT be auto-ticked
                        if folder_metadata.get('accessible', False):
                            # Check manual selection state
                            folder_checkbox = "☑" if folder_metadata.get('selected', False) else "☐"
                        else:
                            folder_checkbox = ""  # Inaccessible folder
                            
                        # v001.0017 added [show enhanced status for folders containing orphans]
                        folder_status = f"Contains Orphans"
                        if __debug__ and folder_metadata.get('orphan_reason'):
                            folder_status += f" ({folder_metadata['orphan_reason']})"
                            
                    # v001.0017 changed [enhanced folder text with better status indication]
                    if folder_checkbox:
                        folder_text = f"{folder_checkbox} {name}/"
                    else:
                        folder_text = f"{name}/ (inaccessible)"
                        
                else:
                    # Folder not in orphan metadata - use old logic as fallback
                    folder_checkbox = "☑" if self.is_folder_selected(item_rel_path) else "☐"
                    folder_text = f"{folder_checkbox} {name}/"
                    folder_status = "Folder"  # v001.0017 changed [simplified status for non-orphan folders]
                
                log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: populate_orphan_tree: Insert folder folder_text='{folder_text}' item_rel_path='{item_rel_path}'")
                folder_id = tree.insert(
                    parent_id,
                    tk.END,
                    text=folder_text,
                    values=("", "", "", folder_status),  # v001.0017 changed [use enhanced folder status]
                    open=True  # Expand by default
                )
                
                # Recursively populate children
                if isinstance(content, dict):
                    self.populate_orphan_tree(tree, content, folder_id, item_rel_path)
                    
    def is_folder_selected(self, folder_path):
        """
        Check if a folder should be considered selected based on enhanced orphan classification.
        
        Purpose:
        --------
        Determines folder checkbox state based on true orphan status rather than just containing orphaned files. # v001.0017 changed [enhanced folder selection logic]
        Only truly orphaned folders should appear as selected, not folders that just contain orphaned files.
        """
        # v001.0017 changed [enhanced logic for true orphan vs contains orphans]
        # Check if this folder itself is a true orphan
        folder_metadata = self.orphan_metadata.get(folder_path)
        if folder_metadata:
            # If this folder is in our metadata, check its true orphan status
            if folder_metadata.get('is_true_orphan', False):
                # This is a truly orphaned folder - should be selected if accessible
                return folder_metadata.get('selected', False) and folder_metadata.get('accessible', False)
            else:
                # This folder exists on both sides but contains orphaned files - should NOT be auto-selected
                # However, it could still be manually selected by user
                return folder_metadata.get('selected', False) and folder_metadata.get('accessible', False)
        
        # v001.0017 changed [fallback logic for folders not directly in metadata]
        # For folders not directly in our orphan metadata (parent folders), check if they should be selected
        # based on their children's selection status
        selected_children = 0
        total_accessible_children = 0
        
        for rel_path, metadata in self.orphan_metadata.items():
            if rel_path.startswith(folder_path + '/') or rel_path == folder_path:
                if metadata.get('accessible', False):
                    total_accessible_children += 1
                    if metadata.get('selected', False):
                        selected_children += 1
        
        # v001.0017 changed [only show folder as selected if it's a true orphan or manually selected]
        # Don't auto-select folders just because they contain orphaned files
        if total_accessible_children == 0:
            return False  # No accessible children
        
        # For folders that aren't true orphans, only show as selected if user manually selected them
        # This prevents auto-ticking of folders that just contain orphaned files
        return selected_children > 0 and selected_children == total_accessible_children  # v001.0017 changed [stricter selection criteria]
        
    def expand_all_tree_items(self):
        """Expand all tree items by default."""
        def expand_recursive(item=''):
            children = self.tree.get_children(item)
            for child in children:
                self.tree.item(child, open=True)
                expand_recursive(child)
        
        expand_recursive()
        
    def handle_tree_click(self, event):
        """Handle clicks on tree items for selection toggle."""
        # Ignore clicks on column headers or separators
        element = self.tree.identify('element', event.x, event.y)
        region = self.tree.identify('region', event.x, event.y)
        
        if element == 'Treeitem.indicator' or region in ('heading', 'separator'):
            return
            
        item_id = self.tree.identify('item', event.x, event.y)
        if item_id:
            # Check if item is accessible (has checkbox)
            item_text = self.tree.item(item_id, 'text')
            if '(inaccessible)' in item_text:
                self.add_status_message("Cannot select inaccessible file")
                return
                
            # Find the relative path for this item
            rel_path = self.find_rel_path_for_item(item_id)
            
            if rel_path:
                self.toggle_item_selection(rel_path)
            else:
                # This might be a folder - handle folder selection
                self.handle_folder_selection(item_id)
                
    def find_rel_path_for_item(self, item_id):
        """Find relative path for a tree item."""
        for rel_path, mapped_item_id in self.path_to_item_map.items():
            if mapped_item_id == item_id:
                return rel_path
        return None
        
    def handle_folder_selection(self, folder_item_id):
        """Handle selection/deselection of folder items."""
        # Get all children of this folder
        folder_children = self.get_folder_children_paths(folder_item_id)
        
        if not folder_children:
            return
            
        # Check current selection state of children
        children_selected = [path for path in folder_children if path in self.selected_items]
        
        if len(children_selected) == len(folder_children):
            # All children selected - deselect all
            for path in folder_children:
                self.selected_items.discard(path)
            self.add_status_message(f"Deselected folder contents: {len(folder_children)} items")
        else:
            # Not all children selected - select all accessible ones
            accessible_children = [
                path for path in folder_children 
                if self.orphan_metadata.get(path, {}).get('accessible', False)
            ]
            self.selected_items.update(accessible_children)
            self.add_status_message(f"Selected folder contents: {len(accessible_children)} accessible items")
            
        # Update display and statistics
        self.update_tree_display()
        self.update_statistics()
        
    def get_folder_children_paths(self, folder_item_id):
        """Get all file paths that are children of a folder item."""
        children_paths = []
        
        def collect_children(item_id):
            for child_id in self.tree.get_children(item_id):
                # Check if this child is a file (has a path mapping)
                child_path = self.find_rel_path_for_item(child_id)
                if child_path:
                    children_paths.append(child_path)
                else:
                    # This is a subfolder - recurse
                    collect_children(child_id)
                    
        collect_children(folder_item_id)
        return children_paths
        
    def toggle_item_selection(self, rel_path):
        """Toggle selection state of a single item."""
        if not rel_path or rel_path not in self.orphan_metadata:
            return
            
        metadata = self.orphan_metadata[rel_path]
        if not metadata['accessible']:
            self.add_status_message(f"Cannot select inaccessible file: {rel_path}")
            return
            
        # Toggle selection
        if rel_path in self.selected_items:
            self.selected_items.discard(rel_path)
            action = "Deselected"
        else:
            self.selected_items.add(rel_path)
            action = "Selected"
            
        self.add_status_message(f"{action}: {rel_path}")
        
        # Update display and statistics
        self.update_tree_display()
        self.update_statistics()
        
    def update_tree_display(self):
        """Update tree display to show current selection state."""
        for rel_path, item_id in self.path_to_item_map.items():
            metadata = self.orphan_metadata.get(rel_path)
            if not metadata:
                continue
                
            current_text = self.tree.item(item_id, 'text')
            
            if metadata['accessible']:
                # Remove existing checkbox
                if current_text.startswith('☑ ') or current_text.startswith('☐ '):
                    name = current_text[2:]
                else:
                    name = current_text
                    
                # Add appropriate checkbox
                if rel_path in self.selected_items:
                    new_text = f"☑ {name}"
                else:
                    new_text = f"☐ {name}"
                    
                self.tree.item(item_id, text=new_text)
                
        # Update folder checkboxes
        self.update_folder_checkboxes()
        
    def update_folder_checkboxes(self):
        """Update folder checkbox states based on children."""
        def update_folder_recursive(item_id):
            children = self.tree.get_children(item_id)
            for child_id in children:
                child_text = self.tree.item(child_id, 'text')
                
                # If this is a folder (ends with /), update its checkbox
                if child_text.endswith('/') or '/' in child_text:
                    child_paths = self.get_folder_children_paths(child_id)
                    
                    if child_paths:
                        selected_children = [p for p in child_paths if p in self.selected_items]
                        
                        # Extract folder name
                        if child_text.startswith('☑ ') or child_text.startswith('☐ '):
                            folder_name = child_text[2:]
                        else:
                            folder_name = child_text
                            
                        # Update checkbox based on children selection
                        if len(selected_children) == len(child_paths) and len(child_paths) > 0:
                            new_text = f"☑ {folder_name}"
                        else:
                            new_text = f"☐ {folder_name}"
                            
                        self.tree.item(child_id, text=new_text)
                        
                # Recurse for subfolders
                update_folder_recursive(child_id)
                
        # Start from root
        update_folder_recursive('')
        
    def update_statistics(self):
        """Update statistics display based on current selections."""
        if not self.orphan_metadata:
            self.statistics_var.set("No orphaned files")
            return
            
        stats = DeleteOrphansManager_class.calculate_orphan_statistics(self.orphan_metadata)
        
        # Update selection flags in metadata
        for rel_path, metadata in self.orphan_metadata.items():
            metadata['selected'] = rel_path in self.selected_items
            
        # Recalculate with updated selections
        stats = DeleteOrphansManager_class.calculate_orphan_statistics(self.orphan_metadata)
        
        # Format statistics message
        total_items = stats['total_files'] + stats['total_folders']
        selected_items = stats['selected_files'] + stats['selected_folders']
        
        stats_text = f"{selected_items} of {total_items} orphaned items selected"
        
        if stats['selected_size'] > 0:
            size_text = self.format_size(stats['selected_size'])
            stats_text += f" ({size_text})"
            
        if stats['large_selection_warning']:
            stats_text += " - WARNING: Large files selected"
            
        if stats['inaccessible_files'] > 0:
            stats_text += f" - {stats['inaccessible_files']} inaccessible"
            
            # Add quick tip for users about inaccessible files # v001.0013 added [quick status message for inaccessible files]
            if hasattr(self, '_last_inaccessible_count'): # v001.0013 added [quick status message for inaccessible files]
                # Only show message if count changed or first time # v001.0013 added [quick status message for inaccessible files]
                if self._last_inaccessible_count != stats['inaccessible_files']: # v001.0013 added [quick status message for inaccessible files]
                    self.add_status_message(f"NOTE: {stats['inaccessible_files']} files are inaccessible and cannot be deleted (see detailed log above)") # v001.0013 added [quick status message for inaccessible files]
            else: # v001.0013 added [quick status message for inaccessible files]
                # First time showing inaccessible files # v001.0013 added [quick status message for inaccessible files]
                self.add_status_message(f"NOTE: {stats['inaccessible_files']} files are inaccessible and cannot be deleted (see detailed log above)") # v001.0013 added [quick status message for inaccessible files]
            
            self._last_inaccessible_count = stats['inaccessible_files'] # v001.0013 added [quick status message for inaccessible files]
            
        self.statistics_var.set(stats_text)

    # ========================================================================
    # INSTANCE METHODS - FILTER, SELECTION, AND DELETION OPERATIONS
    # ========================================================================
    
    def apply_filter(self):
        """Apply dialog-specific filter to orphan tree display."""
        filter_pattern = self.dialog_filter.get().strip()
        
        if not filter_pattern:
            self.add_status_message("No filter pattern specified")
            return
            
        if not self.orphan_metadata:
            self.add_status_message("No orphan data to filter")
            return
            
        self.add_status_message(f"Applying filter: {filter_pattern}")
        
        # Filter the metadata
        filtered_metadata = {}
        
        for rel_path, metadata in self.orphan_metadata.items():
            filename = rel_path.split('/')[-1]
            
            # Apply filter to files only, not folders
            if not metadata['is_folder']:
                if fnmatch.fnmatch(filename.lower(), filter_pattern.lower()):
                    filtered_metadata[rel_path] = metadata
            else:
                # Always include folders that contain matching files
                folder_has_matches = False
                for other_path in self.orphan_metadata:
                    if other_path.startswith(rel_path + '/'):
                        other_filename = other_path.split('/')[-1]
                        if fnmatch.fnmatch(other_filename.lower(), filter_pattern.lower()):
                            folder_has_matches = True
                            break
                            
                if folder_has_matches:
                    filtered_metadata[rel_path] = metadata
                    
        # Rebuild tree with filtered data
        original_count = len(self.orphan_metadata)
        self.orphan_metadata = filtered_metadata
        self.orphan_tree_data = DeleteOrphansManager_class.build_orphan_tree_structure(self.orphan_metadata)
        
        # Update selected items to only include filtered items
        self.selected_items = self.selected_items.intersection(set(filtered_metadata.keys()))
        
        # Rebuild tree display
        self.build_orphan_tree()
        self.update_statistics()
        
        filtered_count = len(filtered_metadata)
        self.add_status_message(f"Filter applied: {filtered_count} of {original_count} items match '{filter_pattern}'")
        
    def clear_filter(self):
        """Clear dialog-specific filter and restore full orphan list."""
        self.dialog_filter.set("")
        
        if not self.orphaned_files:
            self.add_status_message("No original orphan data to restore")
            return
            
        self.add_status_message("Clearing filter - restoring full orphan list...")
        
        # Rebuild full metadata
        self.orphan_metadata = DeleteOrphansManager_class.create_orphan_metadata_dict(
            self.comparison_results,
            self.orphaned_files,
            self.side.upper(),
            self.source_folder
        )
        
        # Rebuild tree structure
        self.orphan_tree_data = DeleteOrphansManager_class.build_orphan_tree_structure(self.orphan_metadata)
        
        # Rebuild tree display
        self.build_orphan_tree()
        self.update_statistics()
        
        self.add_status_message(f"Filter cleared - showing all {len(self.orphan_metadata)} orphaned items")
        
    def select_all_items(self):
        """Select all accessible orphaned items."""
        if not self.orphan_metadata:
            self.add_status_message("No items to select")
            return
            
        # Select all accessible items
        accessible_items = [
            rel_path for rel_path, metadata in self.orphan_metadata.items()
            if metadata['accessible']
        ]
        
        self.selected_items = set(accessible_items)
        
        # Update display
        self.update_tree_display()
        self.update_statistics()
        
        self.add_status_message(f"Selected all accessible items: {len(accessible_items)} files")
        
    def clear_all_items(self):
        """Clear all selections."""
        selected_count = len(self.selected_items)
        self.selected_items.clear()
        
        # Update display
        self.update_tree_display()
        self.update_statistics()
        
        self.add_status_message(f"Cleared all selections: {selected_count} items deselected")
        
    def refresh_orphans_tree(self):
        """Refresh orphan tree to detect external changes."""
        if not self.orphaned_files:
            self.add_status_message("No orphan data to refresh")
            return
            
        self.add_status_message("Refreshing orphan file status...")
        
        # Re-validate all orphan metadata
        accessible_count, changed_count = DeleteOrphansManager_class.refresh_orphan_metadata_status(self.orphan_metadata)
        
        # Log details about currently inaccessible files after refresh # v001.0013 added [detailed logging for inaccessible files after refresh]
        self.add_status_message("Post-refresh inaccessible file analysis:") # v001.0013 added [detailed logging for inaccessible files after refresh]
        self.log_inaccessible_files() # v001.0013 added [detailed logging for inaccessible files after refresh]
        
        # Update tree display with new status
        self.build_orphan_tree()
        self.update_statistics()
        
        # Report results
        total_count = len(self.orphan_metadata)
        inaccessible_count = total_count - accessible_count
        
        self.add_status_message(
            f"Refresh complete: {accessible_count} accessible, {inaccessible_count} inaccessible, "
            f"{changed_count} status changes detected"
        )
        
    def delete_selected_files(self):
        """Start the deletion process for selected files."""
        log_and_flush(logging.DEBUG, f"Entered DeleteOrphansManager_class: delete_selected_files")

        if not self.selected_items:
            self.add_status_message("No files selected for deletion")
            messagebox.showinfo("No Selection", "Please select files to delete first.")
            log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: delete_selected_files: No files selected for deletion")
            return
            
        # Get selected accessible files only
        selected_accessible = []
        for rel_path in self.selected_items:
            metadata = self.orphan_metadata.get(rel_path)
            if metadata and metadata['accessible']:
                selected_accessible.append(rel_path)
                
        if not selected_accessible:
            self.add_status_message("No accessible files selected for deletion")
            messagebox.showinfo("No Accessible Files", "All selected files are inaccessible and cannot be deleted.")
            log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: delete_selected_files: No Accessible Files, All selected files are inaccessible and cannot be deleted.")
            return
            
        # Calculate statistics for confirmation
        total_size = sum(
            self.orphan_metadata[path].get('size', 0) or 0
            for path in selected_accessible
            if not self.orphan_metadata[path]['is_folder']
        )
        
        deletion_method = self.deletion_method.get().lower()
        method_text = "Move to Recycle Bin" if deletion_method.lower() == "recycle_bin".lower() else "Permanently Delete"
        log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: delete_selected_files: delete_method_text='{method_text}'")

        # ----- Display and count for DEBUG purposes
        log_and_flush(logging.INFO, "=" * 80)
        debug_count_selected_accessible_files = 0
        debug_count_selected_accessible_folders = 0
        for path in selected_accessible:
            if self.orphan_metadata[path]['is_folder']:
                debug_count_selected_accessible_folders = debug_count_selected_accessible_folders + 1
                log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: delete_selected_files: SELECTED folder {debug_count_selected_accessible_folders}. '{self.orphan_metadata[path]['full_path']}'")
        for path in selected_accessible:
            if not self.orphan_metadata[path]['is_folder']:
                debug_count_selected_accessible_files = debug_count_selected_accessible_files + 1
                log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: delete_selected_files: SELECTED file   {debug_count_selected_accessible_files}. '{self.orphan_metadata[path]['full_path']}'")
        log_and_flush(logging.DEBUG, f"DeleteOrphansManager_class: delete_selected_files: SELECTED {debug_count_selected_accessible_files} files, SELECTED {debug_count_selected_accessible_folders} folders")
        log_and_flush(logging.INFO, "=" * 80)
        # ----- Display and count for DEBUG purposes
        
        # Use local dry run mode instead of main app dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        # Show confirmation dialog
        dry_run_text = " (DRY RUN SIMULATION)" if is_local_dry_run else "" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        confirmation_message = (
            f"Are you SURE you want to {method_text.lower()} the selected orphaned files{dry_run_text}?\n\n"
            f"Action: {method_text} {len(selected_accessible)} files ({self.format_size(total_size)}) "
            f"from {self.side.upper()} folder\n\n"
        )
        
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            confirmation_message += "*** DRY RUN MODE - No files will be actually deleted ***\n\n"
        elif deletion_method.lower() == "permanent".lower():
            confirmation_message += "⚠ WARNING: Permanent deletion cannot be undone! ⚠\n\n"
        else:
            confirmation_message += "Files will be moved to Recycle Bin where they can be recovered.\n\n"
            
        # Show first 10 files
        preview_files = selected_accessible[:10]
        confirmation_message += "Files to delete:\n" + "\n".join(preview_files)
        
        if len(selected_accessible) > 10:
            confirmation_message += f"\n... and {len(selected_accessible) - 10} more files"
            
        # Create confirmation dialog with appropriate button styling
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            title = "Confirm Deletion Simulation"
            button_text = "Yes, SIMULATE DELETION"
        else:
            title = "Confirm Deletion"
            button_text = "Yes, DELETE FILES"
            
        result = messagebox.askyesno(title, confirmation_message)
        
        if not result:
            self.add_status_message("Deletion cancelled by user")
            return
            
        # Start deletion process
        self.add_status_message(f"Starting deletion process: {len(selected_accessible)} files/folders")
        
        # Close dialog and start deletion in background
        deletion_method_final = deletion_method.lower()
        selected_files_final = selected_accessible.copy()
        
        # Start deletion process in background thread
        threading.Thread(
            target=self.perform_deletion,
            args=(selected_files_final, deletion_method_final),
            daemon=True
        ).start()
        
        # Set result and close dialog
        self.result = "deleted".lower()
        self.close_dialog()
        
    def perform_deletion(self, selected_paths, deletion_method):
        """Perform the actual deletion operation with progress tracking."""
        
        log_and_flush(logging.DEBUG, f"Entered DeleteOrphansManager_class: perform_deletion")
    
        operation_start_time = time.time()
        operation_id = uuid.uuid4().hex[:8]
        
        # Create dedicated logger for this operation
        deletion_logger = self.create_deletion_logger(operation_id)
        
        # Use local dry run mode instead of main app dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        # Log operation start
        dry_run_text = " (DRY RUN)" if is_local_dry_run else "" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        method_text = "Recycle Bin" if deletion_method.lower() == "recycle_bin".lower() else "Permanent"
        
        # v001.0023 added [sort paths for proper deletion order - deepest/child items first]
        # Sort paths by depth (number of separators) in descending order to ensure
        # files are deleted before their parent folders
        sorted_paths = sorted(selected_paths, key=lambda path: (path.count('/'), path), reverse=True)
        
        log_and_flush(logging.INFO, "=" * 80)
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: DELETE ORPHANS OPERATION STARTED{dry_run_text}")
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Operation ID: {operation_id}")
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Side: {self.side.upper()}")
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Source Folder: {self.source_folder}")
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Deletion Method: {method_text}")
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Files/Folders to delete: {len(sorted_paths)} (sorted by depth)") # v001.0023 changed [mention sorting]
        log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Local Dry Run Mode: {is_local_dry_run}") # v001.0013 changed [log local dry run mode instead of main app dry run mode]
        log_and_flush(logging.INFO, "=" * 80)
        
        # Create progress dialog
        progress_title = f"{'Simulating' if is_local_dry_run else 'Deleting'} Orphaned Files" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        progress = ProgressDialog_class(
            self.parent,
            progress_title,
            f"{'Simulating' if is_local_dry_run else 'Processing'} orphaned files...", # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            max_value=len(sorted_paths) # v001.0023 changed [use sorted_paths length]
        )
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        total_bytes_processed = 0
        
        try:
            # v001.0023 changed [iterate through sorted_paths instead of selected_paths]
            for i, rel_path in enumerate(sorted_paths):
                try:
                    # Update progress
                    file_name = rel_path.split('/')[-1]
                    progress_text = f"{'Simulating' if is_local_dry_run else 'Processing'} {i+1} of {len(sorted_paths)}: {file_name}" # v001.0023 changed [use sorted_paths length]
                    progress.update_progress(i+1, progress_text)
                    
                    # Get full path
                    full_path = str(Path(self.source_folder) / rel_path)
                    
                    # Skip if file doesn't exist
                    if not os.path.exists(full_path):
                        skipped_count += 1
                        log_and_flush(logging.ERROR, f"DeleteOrphansManager_class: perform_deletion: ***delete_status: File not found, skipping: {full_path}")
                        continue
                        
                    # Get file size for statistics
                    try:
                        if os.path.isfile(full_path):
                            file_size = os.path.getsize(full_path)
                            total_bytes_processed += file_size
                    except:
                        file_size = 0
                        
                    # Perform deletion
                    if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
                        # Simulate deletion
                        log_and_flush(logging.INFO, f"DRY RUN: Would {method_text.lower()} delete: {full_path}")
                        success_count += 1
                    else:
                        # Actual deletion
                        if deletion_method.lower() == "recycle_bin".lower():
                            success, error_msg = DeleteOrphansManager_class.delete_file_to_recycle_bin(full_path, show_progress=False)
                        else:
                            success, error_msg = DeleteOrphansManager_class.delete_file_permanently(full_path)
                            
                        if success:
                            success_count += 1
                            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: ***delete_status: Successfully {method_text.lower()} deleted: {full_path}")
                        else:
                            error_count += 1
                            log_and_flush(logging.ERROR, f"DeleteOrphansManager_class: perform_deletion: ***delete_status: Failed to delete: {full_path}: {error_msg}")
                            
                except Exception as e:
                    error_count += 1
                    log_and_flush(logging.ERROR, f"DeleteOrphansManager_class: perform_deletion: Exception deleting {rel_path}: {str(e)}")
                    continue

        except Exception as e:
            log_and_flush(logging.CRITICAL, f"DeleteOrphansManager_class: perform_deletion: Critical error during deletion operation: {str(e)}")
            
        finally:
            progress.close()
            # Log operation completion
            elapsed_time = time.time() - operation_start_time
            log_and_flush(logging.INFO, "=" * 80)
            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: DELETE ORPHANS OPERATION COMPLETED{dry_run_text}")
            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Operation ID: {operation_id}")
            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Files processed successfully: {success_count}")
            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Files failed: {error_count}")
            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Files skipped: {skipped_count}")
            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Total bytes processed: {total_bytes_processed:,}")
            log_and_flush(logging.INFO, f"DeleteOrphansManager_class: perform_deletion: Duration: {elapsed_time:.2f} seconds")
            if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
                log_and_flush(logging.INFO, "NOTE: This was a DRY RUN simulation - no actual files were modified")
            log_and_flush(logging.INFO, "=" * 80)
            
            # Show completion dialog
            completion_message = self.format_completion_message(
                success_count, error_count, skipped_count, total_bytes_processed, 
                elapsed_time, method_text, operation_id
            )
            
            self.parent.after(0, lambda: messagebox.showinfo(
                f"{'Simulation' if is_local_dry_run else 'Deletion'} Complete", # v001.0013 changed [use local dry run mode instead of main app dry run mode]
                completion_message
            ))
            
            # Close logger
            for handler in deletion_logger.handlers[:]:
                handler.close()
                deletion_logger.removeHandler(handler)
                
    def create_deletion_logger(self, operation_id):
        """Create dedicated logger for deletion operation."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"foldercomparesync_delete_{self.side.upper()}_{timestamp}_{operation_id}.log"
        log_filepath = os.path.join(os.path.dirname(__file__), log_filename)
        
        operation_logger = logging.getLogger(f"delete_orphans_{operation_id}")
        operation_logger.setLevel(logging.DEBUG)
        
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        operation_logger.addHandler(file_handler)
        operation_logger.propagate = False
        
        return operation_logger
        
    def format_completion_message(self, success_count, error_count, skipped_count, 
                                total_bytes, elapsed_time, method_text, operation_id):
        """Format completion message for deletion operation."""
        # Use local dry run mode instead of main app dry run mode # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        is_local_dry_run = self.local_dry_run_mode.get() # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        dry_run_text = " simulation" if is_local_dry_run else "" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        action_text = "simulated" if is_local_dry_run else method_text.lower() + " deleted" # v001.0013 changed [use local dry run mode instead of main app dry run mode]
        
        message = f"Deletion{dry_run_text} completed!\n\n"
        message += f"Successfully {action_text}: {success_count} files\n"
        
        if error_count > 0:
            message += f"Failed: {error_count} files\n"
        if skipped_count > 0:
            message += f"Skipped: {skipped_count} files (not found)\n"
            
        message += f"Total size processed: {self.format_size(total_bytes)}\n"
        message += f"Time elapsed: {elapsed_time:.1f} seconds\n"
        message += f"Operation ID: {operation_id}\n\n"
        
        # Log file reference
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"foldercomparesync_delete_{self.side.upper()}_{timestamp}_{operation_id}.log"
        message += f"Detailed log saved to:\n{log_filename}\n\n"
        
        if is_local_dry_run: # v001.0013 changed [use local dry run mode instead of main app dry run mode]
            message += "*** DRY RUN SIMULATION ***\n"
            message += "No actual files were modified.\n\n"
        else:
            message += "The main window will now refresh to show the updated folder state.\n"
            
        return message

    def update_delete_button_appearance(self): # v001.0013 added [update delete button appearance based on local dry run mode]
        """Update delete button text and styling based on local dry run mode.""" # v001.0013 added [update delete button appearance based on local dry run mode]
        if not hasattr(self, 'delete_button'): # v001.0013 added [update delete button appearance based on local dry run mode]
            return  # Button not created yet # v001.0013 added [update delete button appearance based on local dry run mode]
        
        is_dry_run = self.local_dry_run_mode.get() # v001.0013 added [update delete button appearance based on local dry run mode]
        
        # Update button text based on local dry run mode # v001.0013 added [update delete button appearance based on local dry run mode]
        if is_dry_run: # v001.0013 added [update delete button appearance based on local dry run mode]
            button_text = "SIMULATE DELETION" # v001.0013 added [update delete button appearance based on local dry run mode]
            button_style = "DeleteOrphansBlueBold.TButton"  # Blue for simulation # v001.0014 changed [use local scaled button style instead of main app style]
        else: # v001.0013 added [update delete button appearance based on local dry run mode]
            button_text = "DELETE SELECTED ORPHANED FILES" # v001.0013 added [update delete button appearance based on local dry run mode]
            button_style = "DeleteOrphansRedBold.TButton"   # Red for actual deletion # v001.0014 changed [use local scaled button style instead of main app style]
        
        # Apply changes to button # v001.0013 added [update delete button appearance based on local dry run mode]
        self.delete_button.configure(text=button_text, style=button_style) # v001.0013 changed [use stored button reference]

    def on_local_dry_run_changed(self): # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        """Handle local dry run mode checkbox changes.""" # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        is_dry_run = self.local_dry_run_mode.get() # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        
        if is_dry_run: # v001.0013 added [local dry run mode change handler for delete orphans dialog]
            self.add_status_message("Local DRY RUN mode enabled - deletion will be simulated only") # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        else: # v001.0013 added [local dry run mode change handler for delete orphans dialog]
            self.add_status_message("Local DRY RUN mode disabled - actual deletion enabled") # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        
        # Update button text and styling to reflect current mode # v001.0013 added [local dry run mode change handler for delete orphans dialog]
        self.update_delete_button_appearance() # v001.0013 added [local dry run mode change handler for delete orphans dialog]

    def log_inaccessible_files(self): # v001.0013 added [detailed logging for inaccessible files]
        """Log detailed information about inaccessible files with full paths and reasons.""" # v001.0013 added [detailed logging for inaccessible files]
        if not self.orphan_metadata: # v001.0013 added [detailed logging for inaccessible files]
            return # v001.0013 added [detailed logging for inaccessible files]
        
        # Find all inaccessible files # v001.0013 added [detailed logging for inaccessible files]
        inaccessible_files = [] # v001.0013 added [detailed logging for inaccessible files]
        
        for rel_path, metadata in self.orphan_metadata.items(): # v001.0013 added [detailed logging for inaccessible files]
            if not metadata['accessible']: # v001.0013 added [detailed logging for inaccessible files]
                inaccessible_files.append({ # v001.0013 added [detailed logging for inaccessible files]
                    'rel_path': rel_path, # v001.0013 added [detailed logging for inaccessible files]
                    'full_path': metadata['full_path'], # v001.0013 added [detailed logging for inaccessible files]
                    'reason': metadata['status'], # v001.0013 added [detailed logging for inaccessible files]
                    'is_folder': metadata['is_folder'] # v001.0013 added [detailed logging for inaccessible files]
                }) # v001.0013 added [detailed logging for inaccessible files]
        
        if not inaccessible_files: # v001.0013 added [detailed logging for inaccessible files]
            self.add_status_message("All orphaned files are accessible for deletion") # v001.0013 added [detailed logging for inaccessible files]
            log_and_flush(logging.INFO, f"All {len(self.orphan_metadata)} orphaned files on {self.side.upper()} side are accessible") # v001.0013 added [detailed logging for inaccessible files]
            return # v001.0013 added [detailed logging for inaccessible files]
        
        # Log summary # v001.0013 added [detailed logging for inaccessible files]
        total_count = len(self.orphan_metadata) # v001.0013 added [detailed logging for inaccessible files]
        inaccessible_count = len(inaccessible_files) # v001.0013 added [detailed logging for inaccessible files]
        accessible_count = total_count - inaccessible_count # v001.0013 added [detailed logging for inaccessible files]
        
        self.add_status_message(f"INACCESSIBLE FILES: {inaccessible_count} of {total_count} files cannot be deleted") # v001.0013 added [detailed logging for inaccessible files]
        log_and_flush(logging.WARNING, f"Found {inaccessible_count} inaccessible orphaned files on {self.side.upper()} side out of {total_count} total") # v001.0013 added [detailed logging for inaccessible files]
        
        # Group by reason for better reporting # v001.0013 added [detailed logging for inaccessible files]
        reasons = {} # v001.0013 added [detailed logging for inaccessible files]
        for file_info in inaccessible_files: # v001.0013 added [detailed logging for inaccessible files]
            reason = file_info['reason'] # v001.0013 added [detailed logging for inaccessible files]
            if reason not in reasons: # v001.0013 added [detailed logging for inaccessible files]
                reasons[reason] = [] # v001.0013 added [detailed logging for inaccessible files]
            reasons[reason].append(file_info) # v001.0013 added [detailed logging for inaccessible files]
        
        # Log details grouped by reason # v001.0013 added [detailed logging for inaccessible files]
        for reason, files_with_reason in reasons.items(): # v001.0013 added [detailed logging for inaccessible files]
            count = len(files_with_reason) # v001.0013 added [detailed logging for inaccessible files]
            self.add_status_message(f"  {reason}: {count} files") # v001.0013 added [detailed logging for inaccessible files]
            log_and_flush(logging.WARNING, f"Inaccessible files due to '{reason}': {count} files") # v001.0013 added [detailed logging for inaccessible files]
            
            # Log first few file paths for each reason (avoid spam) # v001.0013 added [detailed logging for inaccessible files]
            max_examples = 5  # Show max 5 examples per reason # v001.0013 added [detailed logging for inaccessible files]
            for i, file_info in enumerate(files_with_reason[:max_examples]): # v001.0013 added [detailed logging for inaccessible files]
                file_type = "folder" if file_info['is_folder'] else "file" # v001.0013 added [detailed logging for inaccessible files]
                self.add_status_message(f"    {file_type}: {file_info['full_path']}") # v001.0013 added [detailed logging for inaccessible files]
                log_and_flush(logging.WARNING, f"  Inaccessible {file_type}: {file_info['full_path']} (reason: {reason})") # v001.0013 added [detailed logging for inaccessible files]
            
            # If there are more files, show count # v001.0013 added [detailed logging for inaccessible files]
            if len(files_with_reason) > max_examples: # v001.0013 added [detailed logging for inaccessible files]
                remaining = len(files_with_reason) - max_examples # v001.0013 added [detailed logging for inaccessible files]
                self.add_status_message(f"    ... and {remaining} more files with same reason") # v001.0013 added [detailed logging for inaccessible files]
                log_and_flush(logging.WARNING, f"  ... and {remaining} more inaccessible files with reason '{reason}'") # v001.0013 added [detailed logging for inaccessible files]
        
        # Add helpful message about what to do # v001.0013 added [detailed logging for inaccessible files]
        self.add_status_message("TIP: Inaccessible files will be skipped during deletion") # v001.0013 added [detailed logging for inaccessible files]
        if any(reason in ["Read-Only", "No Read Access", "Directory Read-Only"] for reason in reasons.keys()): # v001.0013 added [detailed logging for inaccessible files]
            self.add_status_message("TIP: Try running as Administrator for permission-related issues") # v001.0013 added [detailed logging for inaccessible files]
