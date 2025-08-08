# FolderCompareSync Function Structure Tree

## Version 000.0004 - SHA512 Progress with Clean Separation of Concerns

```
Def and Class relative position
_u64_to_FILETIME()
_FILETIME_to_u64()
class FileTimestampManager 
	├── __init__()
	├── get_timezone_string()
	├── _get_local_timezone()
	├── get_file_timestamps()
	├── set_file_timestamps()
	├── _datetime_to_filetime()
	├── _filetime_to_datetime()
	├── _set_file_times_windows_proper()
	├── _set_file_times_windows_fallback()
	├── copy_timestamps()
	├── format_timestamp()
	└── verify_timestamps()
class ErrorDetailsDialog
	├── __init__()
	├── toggle_details()
	└── copy_to_clipboard()
class CopyStrategy(Enum)
class DriveType(Enum)
class CopyOperationResult
	└── __post_init__()
get_drive_type()
determine_copy_strategy()
create_copy_operation_logger()
class FileMetadata_class
	└── from_path() # (UNCHANGED - stays pure)
class ComparisonResult_class
	└── __post_init__()
class ProgressDialog
	├── __init__()
	├── update_message()
	├── update_progress()
	└── close()
class FileCopyManager
	├── __init__()
	├── set_dry_run_mode()
	├── _log_status()
	├── _verify_copy()
	├── _copy_direct_strategy()
	├── _copy_staged_strategy()
	├── copy_file()
	├── start_copy_operation()
	└── end_copy_operation()
class FolderCompareSync_class
	├── __init__()
	├── add_status_message()
	├── export_status_log()
	├── on_dry_run_changed()
	├── set_debug_loglevel()
	├── setup_ui()
	├── setup_tree_columns()
	├── check_file_limit_exceeded()
	├── clear_all_data_structures()
	├── apply_filter()
	├── perform_filtering()
	├── clear_filter()
	├── expand_all_trees()
	├── collapse_all_trees()
	├── setup_synchronized_scrolling()
	├── sync_scrollbar()
	├── setup_tree_events()
	├── handle_tree_expand_collapse()
	├── is_missing_item()
	├── is_different_item()
	├── get_item_relative_path()
	├── handle_tree_click()
	├── toggle_item_selection()
	├── tick_children_smart()
	├── untick_children()
	├── untick_parents_with_root_safety()
	├── update_tree_display_safe()
	├── update_tree_display()
	├── update_item_display()
	├── browse_left_folder()
	├── browse_right_folder()
	├── start_comparison()
	├── perform_comparison()
	├── build_file_list_with_progress() # ****UPDATED**** ... put compute_sha512_with_progress() underneath this def at the same level
	├── compute_sha512_with_progress() # ****NEW****
	├── compare_items()
	├── update_comparison_ui()
	├── update_comparison_ui_filtered()
	├── build_trees_with_filtered_results()
	├── build_trees_with_root_paths()
	├── populate_tree()
	├── get_item_path()
	├── format_size()
	├── find_tree_item_by_path()
	├── select_all_differences_left()
	├── select_all_differences_right()
	├── clear_all_left()
	├── clear_all_right()
	├── copy_left_to_right()
	├── copy_right_to_left()
	├── perform_enhanced_copy_operation()
	├── refresh_after_copy_operation()
	├── update_summary()
	├── show_error()
	└── run()
main()
```

## Changes Made in v000.0004:

### **New Function:**
- **compute_sha512_with_progress()** - Standalone utility function for SHA512 computation with progress tracking

### **Updated Methods:**
- **FolderCompareSync_class.build_file_list_with_progress()** - Handles SHA512 progress at scanning level using utility function

### **Unchanged Methods:**
- **FileMetadata_class.from_path()** - Stays pure with no UI dependencies

## Clean Separation of Concerns Achieved:

### **📊 Data Layer (Pure)**
- **FileMetadata_class.from_path()**: Creates metadata, no UI knowledge
- **compute_sha512_with_progress()**: SHA512 computation utility, accepts progress interface

### **🎯 Business Logic Layer**
- **build_file_list_with_progress()**: Orchestrates scanning, delegates to appropriate functions

### **🖼️ UI Layer**
- **ProgressDialog**: Handles user feedback and progress display

## Benefits:

✅ **Testable**: Each function can be tested independently  
✅ **Reusable**: `from_path()` works without UI, `compute_sha512_with_progress()` works with any progress interface  
✅ **Maintainable**: Clear responsibilities, changes isolated to appropriate layers  
✅ **Flexible**: Can swap progress implementations or use different metadata creation approaches