Def and Class Relative Positions:
=Root level code block outside of def or class
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
	└── verify_timestamps()
class ErrorDetailsDialog
	├── __init__()
	├── toggle_details()
	└── copy_to_clipboard()
class CopyStrategy(Enum)
class DriveType(Enum)
@dataclass CopyOperationResult
get_drive_type()
determine_copy_strategy()
create_copy_operation_logger()
@dataclass FileMetadata_class
	└── from_path()
@dataclass ComparisonResult_class
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
	├── delete_left_orphans_onclick() # ****UPDATED****
	├── delete_right_orphans_onclick() # ****UPDATED****
	├── delete_orphans_onclick() # ****NEW****
	├── v001_0016_superseded_delete_left_orphans_onclick() # ****NEW****
	├── v001_0016_superseded_delete_right_orphans_onclick() # ****NEW****
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
	├── build_file_list_with_progress()
	├── compute_sha512_with_progress()
	├── compare_items()
	├── update_comparison_ui()
	├── update_comparison_ui_filtered()
	├── build_trees_with_filtered_results()
	├── build_trees_with_root_paths()
	├── populate_tree()
	├── get_item_path()
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
class DeleteOrphansManager_class
	├── delete_file_to_recycle_bin() [static]
	├── delete_file_permanently() [static]
	├── check_file_permissions() [static]
	├── validate_orphan_file_access() [static]
	├── detect_orphaned_files() [static] # ****UPDATED****
	├── create_orphan_metadata_dict() [static] # ****UPDATED****
	├── refresh_orphan_metadata_status() [static]
	├── build_orphan_tree_structure() [static]
	├── calculate_orphan_statistics() [static]
	├── __init__()
	├── setup_dialog()
	├── add_status_message()
	├── initialize_orphan_data()
	├── _initialize_data_direct() # ****UPDATED****
	├── _initialize_data_with_progress() # ****UPDATED****
	├── _finalize_initialization()
	├── _finalize_initialization_enhanced() # ****NEW****
	├── _cleanup_large_data()
	├── close_dialog()
	├── setup_ui()
	├── setup_header_section()
	├── setup_local_dry_run_section()
	├── setup_deletion_method_section()
	├── setup_filter_section()
	├── setup_tree_section()
	├── setup_tree_columns()
	├── setup_status_section()
	├── setup_button_section()
	├── export_status_log()
	├── build_orphan_tree()
	├── populate_orphan_tree() # ****UPDATED****
	├── is_folder_selected() # ****UPDATED****
	├── expand_all_tree_items()
	├── handle_tree_click()
	├── find_rel_path_for_item()
	├── handle_folder_selection()
	├── get_folder_children_paths()
	├── toggle_item_selection()
	├── update_tree_display()
	├── update_folder_checkboxes()
	├── update_statistics()
	├── apply_filter()
	├── clear_filter()
	├── select_all_items()
	├── clear_all_items()
	├── refresh_orphans_tree()
	├── delete_selected_files()
	├── perform_deletion()
	├── create_deletion_logger()
	├── format_completion_message()
	├── update_delete_button_appearance()
	├── on_local_dry_run_changed()
	├── log_inaccessible_files()
	└── set_enhanced_detection_metadata() # ****NEW****
main()
=Root level code block outside of def or class