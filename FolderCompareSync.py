#!/usr/bin/env python3
"""
FolderCompareSync - A Folder Comparison and syncing Tool
A GUI application for comparing two directory trees based on metadata

This tool provides a visual interface to compare two folder structures and identify
differences based on file existence, size, dates, and SHA512 hashes. Users can
mark files/folders for copying between the two trees with overwrite options.

Author: hydra3333
License: AGPL-3.0
GitHub: https://github.com/hydra3333/FolderCompareSync
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
import threading
from collections import defaultdict

class FileMetadata_class:
    """
    Stores and calculates metadata for a single file or directory.
    
    This class encapsulates all the metadata we need for comparison:
    - Existence check
    - File size (0 for directories)
    - Creation and modification timestamps
    - Directory flag
    - SHA512 hash (calculated on-demand for files only)
    """
    
    def __init__(self, path):
        """
        Initialize metadata for a given path.
        
        Args:
            path: File or directory path (string or Path object)
        """
        self.path = Path(path)
        self.exists = self.path.exists()
        
        if self.exists:
            # Get file system statistics
            stat = self.path.stat()
            
            # Size is 0 for directories, actual size for files
            self.size = stat.st_size if self.path.is_file() else 0
            
            # Convert timestamps to datetime objects for easier comparison
            self.date_created = datetime.fromtimestamp(stat.st_ctime)
            self.date_modified = datetime.fromtimestamp(stat.st_mtime)
            
            # Track if this is a directory
            self.is_dir = self.path.is_dir()
            
            # SHA512 hash will be calculated on-demand (lazy loading)
            self._sha512 = None
        else:
            # File doesn't exist - set default values
            self.size = 0
            self.date_created = None
            self.date_modified = None
            self.is_dir = False
            self._sha512 = None
    
    @property
    def sha512(self):
        """
        Calculate and return SHA512 hash for files (lazy loading).
        
        This property calculates the hash only when first accessed and caches
        the result. Only works for files (not directories).
        
        Returns:
            String: SHA512 hash in hexadecimal, or "ERROR" if calculation fails
        """
        # Only calculate hash once and only for existing files (not directories)
        if self._sha512 is None and self.exists and not self.is_dir:
            try:
                # Read file in binary mode and calculate SHA512
                with open(self.path, 'rb') as f:
                    self._sha512 = hashlib.sha512(f.read()).hexdigest()
            except (OSError, IOError):
                # If we can't read the file (permissions, etc), mark as error
                self._sha512 = "ERROR"
        return self._sha512

class ComparisonResult_class:
    """
    Represents the comparison result between a file/folder in left and right trees.
    
    This class stores:
    - The relative path from the root of each tree
    - Metadata for both left and right versions
    - Whether the item is marked for copying and in which direction
    - Logic to determine what differences exist based on comparison options
    """
    
    def __init__(self, rel_path, left_meta, right_meta):
        """
        Initialize a comparison result for a specific path.
        
        Args:
            rel_path: Relative path from tree root (Path object)
            left_meta: FileMetadata_class object for left tree version
            right_meta: FileMetadata_class object for right tree version
        """
        self.rel_path = rel_path
        self.left_meta = left_meta
        self.right_meta = right_meta
        
        # Copy operation tracking
        self.marked_for_copy = False  # User has marked this for copying
        self.copy_direction = None    # 'L->R' (left to right) or 'R->L' (right to left)
        
    def get_differences(self, compare_options):
        """
        Analyze what differences exist between left and right versions.
        
        Based on the user's selected comparison options, this method checks
        each type of difference and returns a list of difference types found.
        
        Args:
            compare_options: Dictionary of boolean values for each comparison type
                           {'existence': bool, 'size': bool, 'date_created': bool, 
                            'date_modified': bool, 'sha512': bool}
        
        Returns:
            List of strings: Types of differences found (e.g., ['size', 'date_modified'])
        """
        diffs = []
        
        # Check existence differences (one exists, the other doesn't)
        if compare_options['existence']:
            if self.left_meta.exists != self.right_meta.exists:
                diffs.append('existence')
        
        # For the following comparisons, both files must exist
        if self.left_meta.exists and self.right_meta.exists:
            
            # Check file size differences
            if compare_options['size']:
                if self.left_meta.size != self.right_meta.size:
                    diffs.append('size')
            
            # Check creation date differences
            if compare_options['date_created']:
                if self.left_meta.date_created != self.right_meta.date_created:
                    diffs.append('date_created')
            
            # Check modification date differences
            if compare_options['date_modified']:
                if self.left_meta.date_modified != self.right_meta.date_modified:
                    diffs.append('date_modified')
            
            # Check SHA512 hash differences (only for files, not directories)
            if compare_options['sha512']:
                if not self.left_meta.is_dir and not self.right_meta.is_dir:
                    if self.left_meta.sha512 != self.right_meta.sha512:
                        diffs.append('sha512')
        
        return diffs

class FolderCompareSync_class:
    """
    Main application class providing the GUI and core functionality.
    
    This class creates and manages:
    - The main window and all UI components
    - Folder comparison logic
    - File copying operations
    - User interaction handling
    """
    
    def __init__(self, root):
        """
        Initialize the main application window and UI components.
        
        Args:
            root: Tkinter root window object
        """
        self.root = root
        self.root.title("FolderCompareSync - Folder Comparison and syncing Tool")
        self.root.geometry("1200x800")
        
        # Comparison options - each is a BooleanVar that tracks checkbox state
        # These control which types of differences to detect and display
        self.compare_options = {
            'existence': tk.BooleanVar(value=True),      # Files that exist in one tree but not the other
            'size': tk.BooleanVar(value=True),           # Files with different sizes
            'date_created': tk.BooleanVar(value=False),  # Files with different creation dates
            'date_modified': tk.BooleanVar(value=True),  # Files with different modification dates
            'sha512': tk.BooleanVar(value=False)         # Files with different content (hash comparison)
        }
        
        # Application data storage
        self.left_path = tk.StringVar()          # Path to left folder being compared
        self.right_path = tk.StringVar()         # Path to right folder being compared
        self.comparison_results = []             # List of all ComparisonResult_class objects
        self.filtered_results = []               # Subset of results that have differences (for display)
        self.overwrite_mode = tk.BooleanVar(value=False)  # Whether to overwrite existing files during copy
        
        # Build the user interface
        self.setup_ui()
        
        # Initialize the summary display
        self.update_summary()
        
    def setup_ui(self):
        """
        Create and layout all UI components.
        
        The UI is organized into several main sections:
        1. Path selection (browse for left/right folders)
        2. Comparison options (checkboxes for what to compare)
        3. Results display (tree view showing differences)
        4. Summary and status information
        """
        
        # Main container frame with padding
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === FOLDER SELECTION SECTION ===
        path_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding=5)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Left folder selection row
        ttk.Label(path_frame, text="Left Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(path_frame, textvariable=self.left_path, width=50).grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_folder(self.left_path)).grid(row=0, column=2)
        
        # Right folder selection row
        ttk.Label(path_frame, text="Right Folder:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Entry(path_frame, textvariable=self.right_path, width=50).grid(row=1, column=1, sticky=tk.EW, padx=(0, 5), pady=(5, 0))
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_folder(self.right_path)).grid(row=1, column=2, pady=(5, 0))
        
        # Make the entry fields expand with window resizing
        path_frame.columnconfigure(1, weight=1)
        
        # === COMPARISON OPTIONS SECTION ===
        options_frame = ttk.LabelFrame(main_frame, text="Comparison Options", padding=5)
        options_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Comparison checkboxes in a horizontal row
        cb_frame = ttk.Frame(options_frame)
        cb_frame.pack(fill=tk.X)
        
        # Each checkbox controls a different type of comparison
        # When changed, automatically update the comparison results
        ttk.Checkbutton(cb_frame, text="Existence", variable=self.compare_options['existence'], 
                       command=self.update_comparison).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(cb_frame, text="Size", variable=self.compare_options['size'], 
                       command=self.update_comparison).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(cb_frame, text="Date Created", variable=self.compare_options['date_created'], 
                       command=self.update_comparison).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(cb_frame, text="Date Modified", variable=self.compare_options['date_modified'], 
                       command=self.update_comparison).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(cb_frame, text="SHA512", variable=self.compare_options['sha512'], 
                       command=self.update_comparison).pack(side=tk.LEFT, padx=(0, 10))
        
        # Control buttons row
        ctrl_frame = ttk.Frame(options_frame)
        ctrl_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Main action buttons
        ttk.Button(ctrl_frame, text="Compare", command=self.start_comparison).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(ctrl_frame, text="Overwrite Mode", variable=self.overwrite_mode).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(ctrl_frame, text="Copy Marked", command=self.copy_marked_items).pack(side=tk.RIGHT)
        
        # === RESULTS DISPLAY SECTION ===
        results_frame = ttk.LabelFrame(main_frame, text="Comparison Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Container for tree view and scrollbars
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Tree view widget for displaying comparison results
        # Columns: Path, Left Status, Right Status, Differences, Copy Direction
        self.tree = ttk.Treeview(tree_frame, columns=('left_status', 'right_status', 'differences', 'copy'), show='tree headings')
        
        # Configure column headers and widths
        self.tree.heading('#0', text='Path')                    # Tree column (file/folder paths)
        self.tree.heading('left_status', text='Left')           # Status of file in left tree
        self.tree.heading('right_status', text='Right')         # Status of file in right tree
        self.tree.heading('differences', text='Differences')    # What differences were found
        self.tree.heading('copy', text='Copy')                  # Copy direction if marked
        
        # Set column widths
        self.tree.column('#0', width=400)
        self.tree.column('left_status', width=150)
        self.tree.column('right_status', width=150)
        self.tree.column('differences', width=200)
        self.tree.column('copy', width=100)
        
        # Add scrollbars for tree view
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tree and scrollbars
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind double-click event to toggle copy marking
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        
        # === SUMMARY SECTION ===
        self.summary_frame = ttk.LabelFrame(main_frame, text="Summary", padding=5)
        self.summary_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Summary label shows counts of different types of differences
        self.summary_label = ttk.Label(self.summary_frame, text="No comparison performed yet")
        self.summary_label.pack(anchor=tk.W)
        
        # === STATUS BAR ===
        # Shows current operation status (Ready, Comparing, Copying, etc.)
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def browse_folder(self, path_var):
        """
        Open a folder selection dialog and update the path variable.
        
        Args:
            path_var: StringVar to update with selected folder path
        """
        folder = filedialog.askdirectory()
        if folder:  # Only update if user didn't cancel
            path_var.set(folder)
    
    def start_comparison(self):
        """
        Begin the folder comparison process.
        
        This method validates the input paths and starts the comparison
        in a separate thread to avoid freezing the UI during long operations.
        """
        # Validate that both paths are provided
        if not self.left_path.get() or not self.right_path.get():
            messagebox.showerror("Error", "Please select both folders")
            return
        
        # Validate that both paths exist
        if not os.path.exists(self.left_path.get()) or not os.path.exists(self.right_path.get()):
            messagebox.showerror("Error", "One or both folders do not exist")
            return
        
        # Update UI to show we're working
        self.status_var.set("Comparing folders...")
        self.root.config(cursor="wait")  # Show wait cursor
        
        # Start comparison in background thread to keep UI responsive
        thread = threading.Thread(target=self.perform_comparison)
        thread.daemon = True  # Thread will close when main program closes
        thread.start()
    
    def perform_comparison(self):
        """
        Perform the actual folder comparison in a background thread.
        
        This method:
        1. Scans both folder trees to find all files and subdirectories
        2. Creates ComparisonResult_class objects for each unique path
        3. Updates the UI with results when complete
        
        Runs in a separate thread to avoid blocking the UI.
        """
        try:
            left_root = Path(self.left_path.get())
            right_root = Path(self.right_path.get())
            
            # Collect all unique relative paths from both trees
            all_paths = set()
            
            # Scan left tree recursively
            # rglob('*') finds all files and directories recursively
            if left_root.exists():
                for item in left_root.rglob('*'):
                    # Get path relative to the root (so we can compare equivalent paths)
                    rel_path = item.relative_to(left_root)
                    all_paths.add(rel_path)
            
            # Scan right tree recursively
            if right_root.exists():
                for item in right_root.rglob('*'):
                    rel_path = item.relative_to(right_root)
                    all_paths.add(rel_path)
            
            # Create comparison results for each unique path
            # This includes files that exist in only one tree
            results = []
            for rel_path in sorted(all_paths):  # Sort for consistent display order
                # Construct full paths for both sides
                left_full = left_root / rel_path
                right_full = right_root / rel_path
                
                # Create metadata objects (these handle non-existent files gracefully)
                left_meta = FileMetadata_class(left_full)
                right_meta = FileMetadata_class(right_full)
                
                # Create comparison result object
                result = ComparisonResult_class(rel_path, left_meta, right_meta)
                results.append(result)
            
            # Store results for use by other methods
            self.comparison_results = results
            
            # Update UI in main thread (thread-safe way to update UI)
            self.root.after(0, self.update_tree)
            
        except Exception as e:
            # Handle any errors during comparison
            self.root.after(0, lambda: messagebox.showerror("Error", f"Comparison failed: {str(e)}"))
        finally:
            # Always restore normal UI state
            self.root.after(0, lambda: self.root.config(cursor=""))
            self.root.after(0, lambda: self.status_var.set("Ready"))
    
    def update_comparison(self):
        """
        Update the comparison display when options change.
        
        Called when user changes which comparison types to show.
        Only updates if we already have comparison results.
        """
        if self.comparison_results:
            self.update_tree()
    
    def update_tree(self):
        """
        Update the tree view display with current comparison results.
        
        This method:
        1. Clears the existing tree display
        2. Filters results to show only items with differences
        3. Adds filtered results to the tree with appropriate formatting and colors
        4. Updates the summary display
        """
        
        # Clear all existing items from tree display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get current comparison options as a simple dictionary
        compare_opts = {k: v.get() for k, v in self.compare_options.items()}
        
        # Filter results to show only items that have differences or missing files
        self.filtered_results = []
        for result in self.comparison_results:
            differences = result.get_differences(compare_opts)
            # Show if there are differences OR if file exists in only one location
            if differences or not result.left_meta.exists or not result.right_meta.exists:
                self.filtered_results.append(result)
        
        # Add filtered results to tree display
        for result in self.filtered_results:
            differences = result.get_differences(compare_opts)
            
            # Format status strings for display
            left_status = self.format_status(result.left_meta)
            right_status = self.format_status(result.right_meta)
            
            # Create differences summary string
            if differences:
                diff_str = ', '.join(differences)
            else:
                diff_str = 'Missing'  # File exists in only one location
            
            # Show copy direction if item is marked for copying
            copy_display = ""
            if result.marked_for_copy:
                copy_display = f"→ {result.copy_direction}"
            
            # Add item to tree
            item_id = self.tree.insert('', 'end', text=str(result.rel_path),
                                     values=(left_status, right_status, diff_str, copy_display))
            
            # Apply color coding based on difference type
            if not result.left_meta.exists:
                # File missing from left side - light red background
                self.tree.set(item_id, 'left_status', 'Missing')
                self.tree.tag_configure('missing_left', background='#ffcccc')
                self.tree.item(item_id, tags=('missing_left',))
            elif not result.right_meta.exists:
                # File missing from right side - light green background
                self.tree.set(item_id, 'right_status', 'Missing')
                self.tree.tag_configure('missing_right', background='#ccffcc')
                self.tree.item(item_id, tags=('missing_right',))
            elif differences:
                # File exists on both sides but is different - light yellow background
                self.tree.tag_configure('different', background='#ffffcc')
                self.tree.item(item_id, tags=('different',))
        
        # Update summary information
        self.update_summary()
    
    def format_status(self, meta):
        """
        Create a formatted status string for display in the tree.
        
        Args:
            meta: FileMetadata_class object
            
        Returns:
            String: Formatted status (e.g., "1.2 MB - 2024-01-15 14:30" or "Missing")
        """
        if not meta.exists:
            return "Missing"
        
        if meta.is_dir:
            # For directories, show just the type and modification date
            return f"DIR - {meta.date_modified.strftime('%Y-%m-%d %H:%M')}"
        else:
            # For files, show size and modification date
            size_str = self.format_size(meta.size)
            return f"{size_str} - {meta.date_modified.strftime('%Y-%m-%d %H:%M')}"
    
    def format_size(self, size):
        """
        Format file size in human-readable units.
        
        Args:
            size: Size in bytes
            
        Returns:
            String: Formatted size (e.g., "1.2 MB", "345.6 KB")
        """
        # Convert bytes to appropriate unit
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def on_tree_double_click(self, event):
        """
        Handle double-click events on tree items to toggle copy marking.
        
        When user double-clicks an item:
        1. If not marked for copy: mark it and determine copy direction
        2. If already marked: unmark it
        
        Copy direction is determined by:
        - If file missing from one side: copy from existing side
        - If file exists on both sides: copy from newer to older (based on modification date)
        
        Args:
            event: Tkinter event object (contains click information)
        """
        # Get the selected item (if any)
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
        
        # Find the corresponding ComparisonResult_class object
        item_text = self.tree.item(item, 'text')  # Get the path from tree display
        result = None
        for r in self.filtered_results:
            if str(r.rel_path) == item_text:
                result = r
                break
        
        if result:
            # Toggle copy marking
            if result.marked_for_copy:
                # Currently marked - unmark it
                result.marked_for_copy = False
                result.copy_direction = None
            else:
                # Not marked - mark it and determine direction
                
                # Determine copy direction based on file existence and dates
                if not result.left_meta.exists:
                    # File only exists on right side - copy right to left
                    result.copy_direction = 'R→L'
                elif not result.right_meta.exists:
                    # File only exists on left side - copy left to right
                    result.copy_direction = 'L→R'
                else:
                    # File exists on both sides - copy from newer to older
                    if result.left_meta.date_modified > result.right_meta.date_modified:
                        result.copy_direction = 'L→R'  # Left is newer
                    else:
                        result.copy_direction = 'R→L'  # Right is newer (or same age)
                
                result.marked_for_copy = True
            
            # Refresh the tree display to show updated copy markings
            self.update_tree()
    
    def copy_marked_items(self):
        """
        Copy all items that are marked for copying.
        
        This method:
        1. Finds all marked items
        2. Confirms the operation with the user
        3. Performs the copy operations with error handling
        4. Refreshes the comparison when complete
        """
        # Find all items marked for copying
        marked_items = [r for r in self.filtered_results if r.marked_for_copy]
        if not marked_items:
            messagebox.showinfo("Info", "No items marked for copy")
            return
        
        # Confirm with user before proceeding
        if not messagebox.askyesno("Confirm Copy", f"Copy {len(marked_items)} marked items?"):
            return
        
        # Update UI to show copy operation in progress
        self.status_var.set("Copying files...")
        self.root.config(cursor="wait")
        
        try:
            left_root = Path(self.left_path.get())
            right_root = Path(self.right_path.get())
            
            copied_count = 0
            
            # Process each marked item
            for result in marked_items:
                try:
                    # Determine source and destination based on copy direction
                    if result.copy_direction == 'L→R':
                        src = left_root / result.rel_path
                        dst = right_root / result.rel_path
                    else:  # R→L
                        src = right_root / result.rel_path
                        dst = left_root / result.rel_path
                    
                    # Create parent directory structure if it doesn't exist
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Check overwrite mode - if disabled and destination exists, skip
                    if dst.exists() and not self.overwrite_mode.get():
                        continue
                    
                    # Perform the copy operation
                    if src.is_file():
                        # Copy file with metadata (timestamps, permissions)
                        shutil.copy2(src, dst)
                    elif src.is_dir():
                        # Copy directory tree
                        if dst.exists():
                            # Remove existing directory if overwrite mode is on
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    
                    copied_count += 1
                    
                except Exception as e:
                    # Show error for individual file but continue with others
                    messagebox.showerror("Copy Error", f"Failed to copy {result.rel_path}: {str(e)}")
            
            # Show completion message
            messagebox.showinfo("Copy Complete", f"Successfully copied {copied_count} items")
            
            # Refresh comparison to show updated state
            self.start_comparison()
            
        finally:
            # Always restore normal UI state
            self.root.config(cursor="")
            self.status_var.set("Ready")
    
    def update_summary(self):
        """
        Update the summary display with current comparison statistics.
        
        Shows counts of:
        - Total differences found
        - Items missing from left side
        - Items missing from right side  
        - Items that exist on both sides but are different
        - Items marked for copying
        """
        if not self.filtered_results:
            self.summary_label.config(text="No comparison performed yet")
            return
        
        # Calculate summary statistics
        total = len(self.filtered_results)
        marked = len([r for r in self.filtered_results if r.marked_for_copy])
        missing_left = len([r for r in self.filtered_results if not r.left_meta.exists])
        missing_right = len([r for r in self.filtered_results if not r.right_meta.exists])
        different = len([r for r in self.filtered_results if r.left_meta.exists and r.right_meta.exists])
        
        # Create summary text
        summary_text = (f"Total differences: {total} | "
                       f"Missing left: {missing_left} | "
                       f"Missing right: {missing_right} | "
                       f"Different: {different} | "
                       f"Marked for copy: {marked}")
        
        self.summary_label.config(text=summary_text)

def main():
    """
    Application entry point.
    
    Creates the main Tkinter window and starts the application.
    """
    root = tk.Tk()
    app = FolderCompareSync_class(root)
    root.mainloop()

if __name__ == "__main__":
    main()
