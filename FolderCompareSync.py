#!/usr/bin/env python3
"""
FolderCompareSync - A Folder Comparison and Syncing Tool

A GUI application for comparing two directory trees based on metadata and syncing them.

This tool provides a visual interface to compare two folder structures and identifying
differences based on file existence, size, dates, and SHA512 hashes.

Users can mark files/folders for copying between the two trees with overwrite options.

Author: hydra3333
License: AGPL-3.0
GitHub: https://github.com/hydra3333/FolderCompareSync
"""

import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading


@dataclass
class FileMetadata_class:
    """Stores file/folder metadata for comparison"""
    path: str
    name: str
    is_folder: bool
    size: Optional[int] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    sha512: Optional[str] = None
    exists: bool = True
    
    @classmethod
    def from_path(cls, path: str, compute_hash: bool = False):
        """Create FileMetadata from a file system path"""
        p = Path(path)
        if not p.exists():
            return cls(path=path, name=p.name, is_folder=False, exists=False)
        
        try:
            stat = p.stat()
            size = stat.st_size if p.is_file() else None
            date_created = datetime.fromtimestamp(stat.st_ctime)
            date_modified = datetime.fromtimestamp(stat.st_mtime)
            
            sha512 = None
            if compute_hash and p.is_file() and size and size < 100 * 1024 * 1024:  # Only hash files < 100MB
                try:
                    with open(path, 'rb') as f:
                        sha512 = hashlib.sha512(f.read()).hexdigest()
                except Exception:
                    pass  # Hash computation failed, leave as None
            
            return cls(
                path=path,
                name=p.name,
                is_folder=p.is_dir(),
                size=size,
                date_created=date_created,
                date_modified=date_modified,
                sha512=sha512,
                exists=True
            )
        except Exception:
            return cls(path=path, name=p.name, is_folder=False, exists=False)


@dataclass
class ComparisonResult_class:
    """Stores comparison result between left/right items"""
    left_item: Optional[FileMetadata_class]
    right_item: Optional[FileMetadata_class]
    differences: Set[str]  # Set of difference types: 'existence', 'size', 'date_created', 'date_modified', 'sha512'
    is_different: bool = False
    
    def __post_init__(self):
        self.is_different = len(self.differences) > 0


class FolderCompareSync_class:
    """Main application class for folder comparison and syncing"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FolderCompareSync - Folder Comparison and Syncing Tool")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Application state
        self.left_folder = tk.StringVar()
        self.right_folder = tk.StringVar()
        self.compare_existence = tk.BooleanVar(value=True)
        self.compare_size = tk.BooleanVar(value=True)
        self.compare_date_created = tk.BooleanVar(value=True)
        self.compare_date_modified = tk.BooleanVar(value=True)
        self.compare_sha512 = tk.BooleanVar(value=False)
        self.overwrite_mode = tk.BooleanVar(value=True)
        
        # Data storage
        self.comparison_results: Dict[str, ComparisonResult_class] = {}
        self.selected_left: Set[str] = set()
        self.selected_right: Set[str] = set()
        self.tree_structure: Dict[str, List[str]] = {'left': [], 'right': []}
        
        # UI References
        self.left_tree = None
        self.right_tree = None
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="Summary: No comparison performed")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding=10)
        folder_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Left folder selection
        ttk.Label(folder_frame, text="Left Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        left_entry = ttk.Entry(folder_frame, textvariable=self.left_folder, width=60)
        left_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_left_folder).grid(row=0, column=2)
        
        # Right folder selection
        ttk.Label(folder_frame, text="Right Folder:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        right_entry = ttk.Entry(folder_frame, textvariable=self.right_folder, width=60)
        right_entry.grid(row=1, column=1, sticky=tk.EW, padx=(0, 5), pady=(5, 0))
        ttk.Button(folder_frame, text="Browse", command=self.browse_right_folder).grid(row=1, column=2, pady=(5, 0))
        
        folder_frame.columnconfigure(1, weight=1)
        
        # Comparison options frame
        options_frame = ttk.LabelFrame(main_frame, text="Comparison Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Comparison criteria checkboxes
        criteria_frame = ttk.Frame(options_frame)
        criteria_frame.pack(fill=tk.X)
        
        ttk.Label(criteria_frame, text="Compare Options:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(criteria_frame, text="Existence", variable=self.compare_existence).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(criteria_frame, text="Size", variable=self.compare_size).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(criteria_frame, text="Date Created", variable=self.compare_date_created).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(criteria_frame, text="Date Modified", variable=self.compare_date_modified).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(criteria_frame, text="SHA512", variable=self.compare_sha512).pack(side=tk.LEFT, padx=(0, 10))
        
        # Overwrite mode and buttons
        control_frame = ttk.Frame(options_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Checkbutton(control_frame, text="Overwrite Mode", variable=self.overwrite_mode).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Button(control_frame, text="Compare", command=self.start_comparison).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Select All Differences - Left", command=self.select_all_left).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="Select All Differences - Right", command=self.select_all_right).pack(side=tk.LEFT)
        
        # Tree comparison frame
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Left tree
        left_frame = ttk.LabelFrame(tree_frame, text="LEFT", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.left_tree = ttk.Treeview(left_frame, show='tree headings', selectmode='none')
        self.left_tree.heading('#0', text='Structure', anchor=tk.W)
        self.left_tree.column('#0', width=300, minwidth=150)
        
        # Configure columns for metadata
        self.setup_tree_columns(self.left_tree)
        
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.left_tree.yview)
        self.left_tree.configure(yscrollcommand=left_scroll.set)
        self.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right tree
        right_frame = ttk.LabelFrame(tree_frame, text="RIGHT", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self.right_tree = ttk.Treeview(right_frame, show='tree headings', selectmode='none')
        self.right_tree.heading('#0', text='Structure', anchor=tk.W)
        self.right_tree.column('#0', width=300, minwidth=150)
        
        self.setup_tree_columns(self.right_tree)
        
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_tree.yview)
        self.right_tree.configure(yscrollcommand=right_scroll.set)
        self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Synchronize scrolling
        self.setup_synchronized_scrolling()
        
        # Copy buttons frame
        copy_frame = ttk.Frame(main_frame)
        copy_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(copy_frame, text="Copy LEFT → Right", command=self.copy_left_to_right).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Copy RIGHT → Left", command=self.copy_right_to_left).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(copy_frame, text="Quit", command=self.root.quit).pack(side=tk.RIGHT)
        
        # Status and summary frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        
        ttk.Label(status_frame, textvariable=self.summary_var).pack(side=tk.LEFT)
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        ttk.Label(status_frame, text="Status:").pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.RIGHT)
        
        # Configure tree event bindings
        self.setup_tree_events()
        
    def setup_tree_columns(self, tree):
        """Setup columns for metadata display in tree"""
        tree['columns'] = ('size', 'date_modified', 'status')
        
        tree.heading('size', text='Size', anchor=tk.E)
        tree.heading('date_modified', text='Date Modified', anchor=tk.CENTER)
        tree.heading('status', text='Status', anchor=tk.W)
        
        tree.column('size', width=80, minwidth=60, anchor=tk.E)
        tree.column('date_modified', width=120, minwidth=100, anchor=tk.CENTER)
        tree.column('status', width=100, minwidth=80, anchor=tk.W)
        
    def setup_synchronized_scrolling(self):
        """Setup synchronized scrolling between tree views"""
        def sync_yview(*args):
            self.left_tree.yview(*args)
            self.right_tree.yview(*args)
        
        # Create a shared scrollbar command
        self.left_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.right_tree, *args))
        self.right_tree.configure(yscrollcommand=lambda *args: self.sync_scrollbar(self.left_tree, *args))
        
    def sync_scrollbar(self, other_tree, *args):
        """Synchronize scrollbar between trees"""
        # Update both trees' scroll position
        self.left_tree.yview_moveto(args[0])
        self.right_tree.yview_moveto(args[0])
        
    def setup_tree_events(self):
        """Setup event bindings for tree interactions"""
        # Bind tree expansion/collapse events
        self.left_tree.bind('<<TreeviewOpen>>', lambda e: self.sync_tree_expansion(self.left_tree, self.right_tree, e))
        self.left_tree.bind('<<TreeviewClose>>', lambda e: self.sync_tree_collapse(self.left_tree, self.right_tree, e))
        self.right_tree.bind('<<TreeviewOpen>>', lambda e: self.sync_tree_expansion(self.right_tree, self.left_tree, e))
        self.right_tree.bind('<<TreeviewClose>>', lambda e: self.sync_tree_collapse(self.right_tree, self.left_tree, e))
        
        # Bind checkbox-like behavior (we'll implement custom checkboxes)
        self.left_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.left_tree, 'left', e))
        self.right_tree.bind('<Button-1>', lambda e: self.handle_tree_click(self.right_tree, 'right', e))
        
    def sync_tree_expansion(self, source_tree, target_tree, event):
        """Synchronize tree expansion between panes"""
        item = source_tree.selection()[0] if source_tree.selection() else source_tree.focus()
        if item:
            # Find corresponding item in other tree and expand it
            try:
                target_tree.item(item, open=True)
            except tk.TclError:
                pass  # Item doesn't exist in target tree
                
    def sync_tree_collapse(self, source_tree, target_tree, event):
        """Synchronize tree collapse between panes"""
        item = source_tree.selection()[0] if source_tree.selection() else source_tree.focus()
        if item:
            # Find corresponding item in other tree and collapse it
            try:
                target_tree.item(item, open=False)
            except tk.TclError:
                pass  # Item doesn't exist in target tree
                
    def handle_tree_click(self, tree, side, event):
        """Handle clicks on tree items (for checkbox behavior)"""
        item = tree.identify('item', event.x, event.y)
        if item:
            # Toggle selection for this item
            self.toggle_item_selection(item, side)
            
    def toggle_item_selection(self, item_id, side):
        """Toggle selection state of an item and handle parent/child logic"""
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        if item_id in selected_set:
            # Unticking - remove from selection and untick all parents
            selected_set.discard(item_id)
            self.untick_parents(item_id, side)
            self.untick_children(item_id, side)
        else:
            # Ticking - add to selection and tick all children
            selected_set.add(item_id)
            self.tick_children(item_id, side)
            
        self.update_tree_display()
        self.update_summary()
        
    def tick_children(self, item_id, side):
        """Tick all children of an item"""
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        def tick_recursive(item):
            selected_set.add(item)
            for child in tree.get_children(item):
                tick_recursive(child)
                
        for child in tree.get_children(item_id):
            tick_recursive(child)
            
    def untick_children(self, item_id, side):
        """Untick all children of an item"""
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        def untick_recursive(item):
            selected_set.discard(item)
            for child in tree.get_children(item):
                untick_recursive(child)
                
        for child in tree.get_children(item_id):
            untick_recursive(child)
            
    def untick_parents(self, item_id, side):
        """Untick all parents of an item"""
        selected_set = self.selected_left if side == 'left' else self.selected_right
        tree = self.left_tree if side == 'left' else self.right_tree
        
        parent = tree.parent(item_id)
        while parent:
            selected_set.discard(parent)
            parent = tree.parent(parent)
            
    def update_tree_display(self):
        """Update tree display to show selection state"""
        # Update left tree
        for item in self.left_tree.get_children():
            self.update_item_display(self.left_tree, item, 'left')
            
        # Update right tree  
        for item in self.right_tree.get_children():
            self.update_item_display(self.right_tree, item, 'right')
            
    def update_item_display(self, tree, item, side, recursive=True):
        """Update display of a single item and optionally its children"""
        selected_set = self.selected_left if side == 'left' else self.selected_right
        
        # Get current text and modify it to show selection
        current_text = tree.item(item, 'text')
        
        # Remove existing checkbox indicators
        if current_text.startswith('☑ ') or current_text.startswith('☐ '):
            current_text = current_text[2:]
            
        # Add checkbox indicator
        if item in selected_set:
            new_text = '☑ ' + current_text
        else:
            new_text = '☐ ' + current_text
            
        tree.item(item, text=new_text)
        
        if recursive:
            for child in tree.get_children(item):
                self.update_item_display(tree, child, side, True)
                
    def browse_left_folder(self):
        """Browse for left folder"""
        folder = filedialog.askdirectory(title="Select Left Folder")
        if folder:
            self.left_folder.set(folder)
            
    def browse_right_folder(self):
        """Browse for right folder"""
        folder = filedialog.askdirectory(title="Select Right Folder")
        if folder:
            self.right_folder.set(folder)
            
    def start_comparison(self):
        """Start folder comparison in background thread"""
        if not self.left_folder.get() or not self.right_folder.get():
            messagebox.showerror("Error", "Please select both folders to compare")
            return
            
        if not os.path.exists(self.left_folder.get()):
            messagebox.showerror("Error", "Left folder does not exist")
            return
            
        if not os.path.exists(self.right_folder.get()):
            messagebox.showerror("Error", "Right folder does not exist")
            return
            
        # Start comparison in background thread
        self.status_var.set("Comparing folders...")
        threading.Thread(target=self.perform_comparison, daemon=True).start()
        
    def perform_comparison(self):
        """Perform the actual folder comparison"""
        try:
            # Clear previous results
            self.comparison_results.clear()
            self.selected_left.clear()
            self.selected_right.clear()
            
            # Build file lists for both folders
            left_files = self.build_file_list(self.left_folder.get())
            right_files = self.build_file_list(self.right_folder.get())
            
            # Get all unique relative paths
            all_paths = set(left_files.keys()) | set(right_files.keys())
            
            # Compare each path
            for rel_path in all_paths:
                left_item = left_files.get(rel_path)
                right_item = right_files.get(rel_path)
                
                differences = self.compare_items(left_item, right_item)
                
                self.comparison_results[rel_path] = ComparisonResult_class(
                    left_item=left_item,
                    right_item=right_item,
                    differences=differences
                )
                
            # Update UI in main thread
            self.root.after(0, self.update_comparison_ui)
            
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"Comparison failed: {str(e)}"))
            
    def build_file_list(self, root_path: str) -> Dict[str, FileMetadata_class]:
        """Build a dictionary of relative_path -> FileMetadata for all files in folder"""
        files = {}
        root = Path(root_path)
        
        try:
            for path in root.rglob('*'):
                try:
                    rel_path = path.relative_to(root).as_posix()
                    metadata = FileMetadata_class.from_path(str(path), self.compare_sha512.get())
                    files[rel_path] = metadata
                except Exception:
                    continue  # Skip files we can't process
        except Exception:
            pass  # Handle permission errors, etc.
            
        return files
        
    def compare_items(self, left_item: Optional[FileMetadata_class], 
                     right_item: Optional[FileMetadata_class]) -> Set[str]:
        """Compare two items and return set of differences"""
        differences = set()
        
        # Check existence
        if self.compare_existence.get():
            if (left_item is None) != (right_item is None):
                differences.add('existence')
            elif left_item and right_item and (not left_item.exists or not right_item.exists):
                differences.add('existence')
                
        # If both items exist, compare other attributes
        if left_item and right_item and left_item.exists and right_item.exists:
            if self.compare_size.get() and left_item.size != right_item.size:
                differences.add('size')
                
            if self.compare_date_created.get() and left_item.date_created != right_item.date_created:
                differences.add('date_created')
                
            if self.compare_date_modified.get() and left_item.date_modified != right_item.date_modified:
                differences.add('date_modified')
                
            if (self.compare_sha512.get() and left_item.sha512 and right_item.sha512 
                and left_item.sha512 != right_item.sha512):
                differences.add('sha512')
                
        return differences
        
    def update_comparison_ui(self):
        """Update UI with comparison results"""
        # Clear existing tree content
        for item in self.left_tree.get_children():
            self.left_tree.delete(item)
        for item in self.right_tree.get_children():
            self.right_tree.delete(item)
            
        # Build tree structure
        self.build_trees()
        
        # Update status
        self.status_var.set("Ready")
        self.update_summary()
        
    def build_trees(self):
        """Build tree structures from comparison results"""
        # Organize paths into tree structure
        left_structure = {}
        right_structure = {}
        
        for rel_path, result in self.comparison_results.items():
            if not rel_path:  # Skip empty paths
                continue
                
            path_parts = rel_path.split('/')
            
            # Build left structure
            if result.left_item is not None:
                current = left_structure
                for part in path_parts[:-1]:
                    if part and part not in current:
                        current[part] = {}
                    if part:
                        current = current[part]
                if path_parts[-1]:
                    current[path_parts[-1]] = result.left_item
            
            # Build right structure  
            if result.right_item is not None:
                current = right_structure
                for part in path_parts[:-1]:
                    if part and part not in current:
                        current[part] = {}
                    if part:
                        current = current[part]
                if path_parts[-1]:
                    current[path_parts[-1]] = result.right_item
                    
        # Also need to add missing items as placeholders
        for rel_path, result in self.comparison_results.items():
            if not rel_path:
                continue
                
            path_parts = rel_path.split('/')
            
            # Add missing left items
            if result.left_item is None and result.right_item is not None:
                current = left_structure
                for part in path_parts[:-1]:
                    if part and part not in current:
                        current[part] = {}
                    if part:
                        current = current[part]
                if path_parts[-1]:
                    current[path_parts[-1]] = None  # Placeholder for missing item
                    
            # Add missing right items
            if result.right_item is None and result.left_item is not None:
                current = right_structure
                for part in path_parts[:-1]:
                    if part and part not in current:
                        current[part] = {}
                    if part:
                        current = current[part]
                if path_parts[-1]:
                    current[path_parts[-1]] = None  # Placeholder for missing item
            
        # Populate trees
        self.populate_tree(self.left_tree, left_structure, '', 'left')
        self.populate_tree(self.right_tree, right_structure, '', 'right')
        
    def populate_tree(self, tree, structure, parent_id, side):
        """Recursively populate tree with structure"""
        for name, content in sorted(structure.items()):
            if isinstance(content, dict):
                # This is a folder
                item_text = f"☐ {name}/"
                item_id = tree.insert(parent_id, tk.END, text=item_text, open=False)
                self.populate_tree(tree, content, item_id, side)
            else:
                # This is a file
                if content is None:
                    # Missing file
                    item_text = f"{name} [MISSING]"
                    item_id = tree.insert(parent_id, tk.END, text=item_text, 
                                        values=("", "", "Missing"), tags=('missing',))
                else:
                    # Existing file
                    size_str = self.format_size(content.size) if content.size else ""
                    date_str = content.date_modified.strftime("%Y-%m-%d %H:%M") if content.date_modified else ""
                    
                    # Determine status by checking if this file has differences
                    status = "Same"  # Default status
                    
                    # Find this item in comparison results
                    for rel_path, result in self.comparison_results.items():
                        if rel_path.endswith(name):
                            if result.is_different:
                                status = "Different"
                            break
                    
                    item_text = f"☐ {name}"
                    item_id = tree.insert(parent_id, tk.END, text=item_text,
                                        values=(size_str, date_str, status))
                                        
        # Configure missing item styling
        tree.tag_configure('missing', foreground='gray')
        
    def get_item_path(self, tree, item_id):
        """Get the full relative path for a tree item"""
        if not item_id:
            return ""
        path_parts = []
        current = item_id
        while current:
            text = tree.item(current, 'text')
            # Remove checkbox and extract name
            if text.startswith('☑ ') or text.startswith('☐ '):
                text = text[2:]
            path_parts.append(text)
            current = tree.parent(current)
        return '/'.join(reversed(path_parts)) + '/'
        
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes is None:
            return ""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
        
    def select_all_left(self):
        """Select all different items in left pane"""
        for rel_path, result in self.comparison_results.items():
            if result.is_different and result.left_item and result.left_item.exists:
                # Find tree item and select it
                pass  # Implementation needed
        self.update_tree_display()
        self.update_summary()
        
    def select_all_right(self):
        """Select all different items in right pane"""
        for rel_path, result in self.comparison_results.items():
            if result.is_different and result.right_item and result.right_item.exists:
                # Find tree item and select it
                pass  # Implementation needed
        self.update_tree_display() 
        self.update_summary()
        
    def copy_left_to_right(self):
        """Copy selected items from left to right"""
        if not self.selected_left:
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # For safety during development, just show what would be copied
        message = f"Would copy {len(self.selected_left)} items from LEFT to RIGHT\n"
        message += "Actual copying is disabled for safety during development."
        messagebox.showinfo("Copy Preview", message)
        
    def copy_right_to_left(self):
        """Copy selected items from right to left"""
        if not self.selected_right:
            messagebox.showinfo("Info", "No items selected for copying")
            return
            
        # For safety during development, just show what would be copied
        message = f"Would copy {len(self.selected_right)} items from RIGHT to LEFT\n"
        message += "Actual copying is disabled for safety during development."
        messagebox.showinfo("Copy Preview", message)
        
    def update_summary(self):
        """Update summary information"""
        if not self.comparison_results:
            self.summary_var.set("Summary: No comparison performed")
            return
            
        total_differences = sum(1 for r in self.comparison_results.values() if r.is_different)
        missing_left = sum(1 for r in self.comparison_results.values() 
                          if r.left_item is None or not r.left_item.exists)
        missing_right = sum(1 for r in self.comparison_results.values()
                           if r.right_item is None or not r.right_item.exists)
        selected_total = len(self.selected_left) + len(self.selected_right)
        
        summary = f"Summary: {total_differences} differences | {missing_left} missing left | {missing_right} missing right | {selected_total} marked"
        self.summary_var.set(summary)
        
    def show_error(self, message):
        """Show error message to user"""
        messagebox.showerror("Error", message)
        self.status_var.set("Ready")
        
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = FolderCompareSync_class()
    app.run()


if __name__ == "__main__":
    main()