#!/usr/bin/env python3
"""
A Folder Comparison and syncing Tool
A GUI application for comparing two directory trees based on metadata
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

class FileMetadata:
    def __init__(self, path):
        self.path = Path(path)
        self.exists = self.path.exists()
        if self.exists:
            stat = self.path.stat()
            self.size = stat.st_size if self.path.is_file() else 0
            self.date_created = datetime.fromtimestamp(stat.st_ctime)
            self.date_modified = datetime.fromtimestamp(stat.st_mtime)
            self.is_dir = self.path.is_dir()
            self._sha512 = None
        else:
            self.size = 0
            self.date_created = None
            self.date_modified = None
            self.is_dir = False
            self._sha512 = None
    
    @property
    def sha512(self):
        if self._sha512 is None and self.exists and not self.is_dir:
            try:
                with open(self.path, 'rb') as f:
                    self._sha512 = hashlib.sha512(f.read()).hexdigest()
            except (OSError, IOError):
                self._sha512 = "ERROR"
        return self._sha512

class ComparisonResult:
    def __init__(self, rel_path, left_meta, right_meta):
        self.rel_path = rel_path
        self.left_meta = left_meta
        self.right_meta = right_meta
        self.marked_for_copy = False
        self.copy_direction = None  # 'L->R' or 'R->L'
        
    def get_differences(self, compare_options):
        """Return list of difference types based on comparison options"""
        diffs = []
        
        if compare_options['existence']:
            if self.left_meta.exists != self.right_meta.exists:
                diffs.append('existence')
        
        if compare_options['size'] and self.left_meta.exists and self.right_meta.exists:
            if self.left_meta.size != self.right_meta.size:
                diffs.append('size')
        
        if compare_options['date_created'] and self.left_meta.exists and self.right_meta.exists:
            if self.left_meta.date_created != self.right_meta.date_created:
                diffs.append('date_created')
        
        if compare_options['date_modified'] and self.left_meta.exists and self.right_meta.exists:
            if self.left_meta.date_modified != self.right_meta.date_modified:
                diffs.append('date_modified')
        
        if compare_options['sha512'] and self.left_meta.exists and self.right_meta.exists:
            if not self.left_meta.is_dir and not self.right_meta.is_dir:
                if self.left_meta.sha512 != self.right_meta.sha512:
                    diffs.append('sha512')
        
        return diffs

class XTreeClone:
    def __init__(self, root):
        self.root = root
        self.root.title("XTree Clone - Folder Comparison Tool")
        self.root.geometry("1200x800")
        
        # Comparison options
        self.compare_options = {
            'existence': tk.BooleanVar(value=True),
            'size': tk.BooleanVar(value=True),
            'date_created': tk.BooleanVar(value=False),
            'date_modified': tk.BooleanVar(value=True),
            'sha512': tk.BooleanVar(value=False)
        }
        
        # Data
        self.left_path = tk.StringVar()
        self.right_path = tk.StringVar()
        self.comparison_results = []
        self.filtered_results = []
        self.overwrite_mode = tk.BooleanVar(value=False)
        
        self.setup_ui()
        self.update_summary()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Path selection frame
        path_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding=5)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Left path
        ttk.Label(path_frame, text="Left Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(path_frame, textvariable=self.left_path, width=50).grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_folder(self.left_path)).grid(row=0, column=2)
        
        # Right path
        ttk.Label(path_frame, text="Right Folder:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Entry(path_frame, textvariable=self.right_path, width=50).grid(row=1, column=1, sticky=tk.EW, padx=(0, 5), pady=(5, 0))
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_folder(self.right_path)).grid(row=1, column=2, pady=(5, 0))
        
        path_frame.columnconfigure(1, weight=1)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Comparison Options", padding=5)
        options_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Comparison checkboxes
        cb_frame = ttk.Frame(options_frame)
        cb_frame.pack(fill=tk.X)
        
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
        
        # Control buttons
        ctrl_frame = ttk.Frame(options_frame)
        ctrl_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(ctrl_frame, text="Compare", command=self.start_comparison).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(ctrl_frame, text="Overwrite Mode", variable=self.overwrite_mode).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(ctrl_frame, text="Copy Marked", command=self.copy_marked_items).pack(side=tk.RIGHT)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Comparison Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.tree = ttk.Treeview(tree_frame, columns=('left_status', 'right_status', 'differences', 'copy'), show='tree headings')
        
        # Configure columns
        self.tree.heading('#0', text='Path')
        self.tree.heading('left_status', text='Left')
        self.tree.heading('right_status', text='Right') 
        self.tree.heading('differences', text='Differences')
        self.tree.heading('copy', text='Copy')
        
        self.tree.column('#0', width=400)
        self.tree.column('left_status', width=150)
        self.tree.column('right_status', width=150)
        self.tree.column('differences', width=200)
        self.tree.column('copy', width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind events
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        
        # Summary frame
        self.summary_frame = ttk.LabelFrame(main_frame, text="Summary", padding=5)
        self.summary_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.summary_label = ttk.Label(self.summary_frame, text="No comparison performed yet")
        self.summary_label.pack(anchor=tk.W)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def browse_folder(self, path_var):
        folder = filedialog.askdirectory()
        if folder:
            path_var.set(folder)
    
    def start_comparison(self):
        if not self.left_path.get() or not self.right_path.get():
            messagebox.showerror("Error", "Please select both folders")
            return
        
        if not os.path.exists(self.left_path.get()) or not os.path.exists(self.right_path.get()):
            messagebox.showerror("Error", "One or both folders do not exist")
            return
        
        # Start comparison in separate thread
        self.status_var.set("Comparing folders...")
        self.root.config(cursor="wait")
        
        thread = threading.Thread(target=self.perform_comparison)
        thread.daemon = True
        thread.start()
    
    def perform_comparison(self):
        try:
            left_root = Path(self.left_path.get())
            right_root = Path(self.right_path.get())
            
            # Get all relative paths from both trees
            all_paths = set()
            
            # Scan left tree
            if left_root.exists():
                for item in left_root.rglob('*'):
                    rel_path = item.relative_to(left_root)
                    all_paths.add(rel_path)
            
            # Scan right tree
            if right_root.exists():
                for item in right_root.rglob('*'):
                    rel_path = item.relative_to(right_root)
                    all_paths.add(rel_path)
            
            # Create comparison results
            results = []
            for rel_path in sorted(all_paths):
                left_full = left_root / rel_path
                right_full = right_root / rel_path
                
                left_meta = FileMetadata(left_full)
                right_meta = FileMetadata(right_full)
                
                result = ComparisonResult(rel_path, left_meta, right_meta)
                results.append(result)
            
            self.comparison_results = results
            
            # Update UI in main thread
            self.root.after(0, self.update_tree)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Comparison failed: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.root.config(cursor=""))
            self.root.after(0, lambda: self.status_var.set("Ready"))
    
    def update_comparison(self):
        """Update comparison when options change"""
        if self.comparison_results:
            self.update_tree()
    
    def update_tree(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get current comparison options
        compare_opts = {k: v.get() for k, v in self.compare_options.items()}
        
        # Filter results to show only items with differences
        self.filtered_results = []
        for result in self.comparison_results:
            differences = result.get_differences(compare_opts)
            if differences or not result.left_meta.exists or not result.right_meta.exists:
                self.filtered_results.append(result)
        
        # Add items to tree
        for result in self.filtered_results:
            differences = result.get_differences(compare_opts)
            
            # Format status strings
            left_status = self.format_status(result.left_meta)
            right_status = self.format_status(result.right_meta)
            diff_str = ', '.join(differences) if differences else 'Missing'
            
            # Determine copy direction display
            copy_display = ""
            if result.marked_for_copy:
                copy_display = f"→ {result.copy_direction}"
            
            # Add to tree
            item_id = self.tree.insert('', 'end', text=str(result.rel_path),
                                     values=(left_status, right_status, diff_str, copy_display))
            
            # Color coding
            if not result.left_meta.exists:
                self.tree.set(item_id, 'left_status', 'Missing')
                self.tree.tag_configure('missing_left', background='#ffcccc')
                self.tree.item(item_id, tags=('missing_left',))
            elif not result.right_meta.exists:
                self.tree.set(item_id, 'right_status', 'Missing')
                self.tree.tag_configure('missing_right', background='#ccffcc')
                self.tree.item(item_id, tags=('missing_right',))
            elif differences:
                self.tree.tag_configure('different', background='#ffffcc')
                self.tree.item(item_id, tags=('different',))
        
        self.update_summary()
    
    def format_status(self, meta):
        if not meta.exists:
            return "Missing"
        
        if meta.is_dir:
            return f"DIR - {meta.date_modified.strftime('%Y-%m-%d %H:%M')}"
        else:
            size_str = self.format_size(meta.size)
            return f"{size_str} - {meta.date_modified.strftime('%Y-%m-%d %H:%M')}"
    
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def on_tree_double_click(self, event):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
        
        # Find the corresponding result
        item_text = self.tree.item(item, 'text')
        result = None
        for r in self.filtered_results:
            if str(r.rel_path) == item_text:
                result = r
                break
        
        if result:
            # Toggle copy marking
            if result.marked_for_copy:
                result.marked_for_copy = False
                result.copy_direction = None
            else:
                # Determine copy direction based on existence
                if not result.left_meta.exists:
                    result.copy_direction = 'R→L'
                elif not result.right_meta.exists:
                    result.copy_direction = 'L→R'
                else:
                    # Both exist, let user choose or default to newer
                    if result.left_meta.date_modified > result.right_meta.date_modified:
                        result.copy_direction = 'L→R'
                    else:
                        result.copy_direction = 'R→L'
                
                result.marked_for_copy = True
            
            self.update_tree()
    
    def copy_marked_items(self):
        marked_items = [r for r in self.filtered_results if r.marked_for_copy]
        if not marked_items:
            messagebox.showinfo("Info", "No items marked for copy")
            return
        
        if not messagebox.askyesno("Confirm Copy", f"Copy {len(marked_items)} marked items?"):
            return
        
        self.status_var.set("Copying files...")
        self.root.config(cursor="wait")
        
        try:
            left_root = Path(self.left_path.get())
            right_root = Path(self.right_path.get())
            
            copied_count = 0
            for result in marked_items:
                try:
                    if result.copy_direction == 'L→R':
                        src = left_root / result.rel_path
                        dst = right_root / result.rel_path
                    else:  # R→L
                        src = right_root / result.rel_path
                        dst = left_root / result.rel_path
                    
                    # Create parent directory if needed
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Check if destination exists and overwrite mode
                    if dst.exists() and not self.overwrite_mode.get():
                        continue
                    
                    # Copy file or directory
                    if src.is_file():
                        shutil.copy2(src, dst)
                    elif src.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    
                    copied_count += 1
                    
                except Exception as e:
                    messagebox.showerror("Copy Error", f"Failed to copy {result.rel_path}: {str(e)}")
            
            messagebox.showinfo("Copy Complete", f"Successfully copied {copied_count} items")
            
            # Refresh comparison
            self.start_comparison()
            
        finally:
            self.root.config(cursor="")
            self.status_var.set("Ready")
    
    def update_summary(self):
        if not self.filtered_results:
            self.summary_label.config(text="No comparison performed yet")
            return
        
        total = len(self.filtered_results)
        marked = len([r for r in self.filtered_results if r.marked_for_copy])
        missing_left = len([r for r in self.filtered_results if not r.left_meta.exists])
        missing_right = len([r for r in self.filtered_results if not r.right_meta.exists])
        different = len([r for r in self.filtered_results if r.left_meta.exists and r.right_meta.exists])
        
        summary_text = f"Total differences: {total} | Missing left: {missing_left} | Missing right: {missing_right} | Different: {different} | Marked for copy: {marked}"
        self.summary_label.config(text=summary_text)

def main():
    root = tk.Tk()
    app = XTreeClone(root)
    root.mainloop()

if __name__ == "__main__":
    main()
