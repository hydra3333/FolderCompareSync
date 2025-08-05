# FolderCompareSync

**A GUI Folder Tree Comparison & Synchronization Tool for Windows 10+ with Optimized Copy System**

![Version](https://img.shields.io/badge/version-0.6.1-blue) ![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey) ![License](https://img.shields.io/badge/license-AGPL--3.0-green) ![Performance](https://img.shields.io/badge/performance-50%25%20faster-brightgreen)

#### UNTESTED, UNDER DEVELOPMENT, BEWARE    
#### Iteratively developed AI generated code.    

---

## What is FolderCompareSync?

FolderCompareSync is an easy-to-use free tool that helps you **compare two folder trees side-by-side** and **synchronize selected files between them** with **date-created/date-modified timestamp preservation**.    

Think of it as a folder tree "bulk choose, copy and paste the differences" with optional overwrite that shows you exactly what's different and lets you choose what to copy.
Enabling SHA512 comparison is slow (where lots of files or large files eg 2GB+) but detects differences in file content where they may cheekily have the same folder/date-created/date-modified/size.

### UNTESTED, UNDER DEVELOPMENT, BEWARE    
#### Iteratively developed AI generated python3 code.    

### 🎯 Good for:
- **Backup verification** - Make sure your backup copies are complete and up-to-date
- **Project synchronization** - Keep development folder trees in sync across different locations
- **Data migration** - Safely copy files between drives or computers
- **Cleanup operations** - Find duplicate or outdated files with ease

---

## ✨ Key Features

### 🚀 **Copying**
- **DateTime timestamp preservation**: date-created and date-modified timestamps are always copied along with the file
- **Optimized Dual-Strategy Copy System**: Automatically selects the fastest method for each file
  - **Direct Copy**: fast copying for smaller files
  - **Safe Staged Copy**: rename/copy based backup for large files enabling original file recovery
  - **Network Drive Copy**: Automatic detection, always uses Safe Staged Copy
- **Large limits**: Handle up to 200,000 files (very large folder trees = very very slow, likely laggy responses)
- **Atomic operations**: True atomic file operations using Windows primitives

### 📊 **Selectable Smart Comparison**
- **Side-by-side view** of two folder structures with relevant metadata display
- **Multiple optional comparison criteria**: file size, dates-created/date-modified, content (SHA512 hash, very slow but safest)
- **Visual indicators** showing which files are different, missing, or identical

### 🔍 **Advanced Filtering & Search**
- **Wildcard filtering**: Find specific files in the folder trees with patterns like `*.jpg`, `*backup*`, `IMG_*.png`
- **Sortable columns**: Click any column header to sort by size, date, maintaining folder locations
- **Tree expansion controls**: Expand/collapse entire or partial folder tree structures instantly

### 🛡️ **Copy Operations with Safety**
- **DRY RUN mode** (NEW): Test operations without any file modifications
- **Progress tracking**: Real-time file-by-file copy progress
- **Error handling**: Continues operation even if some files fail, with comprehensive error reporting
- **Automatic rollback**: Complete restoration of original files with timestamp preservation if "Safe Staged Copy" operations fail during copying
- **Auto-refresh**: Automatically rescans folders after copying to show current state

### 📝 **Logging with Performance Tracking**
- **Detailed progress**: Progress dialogs for all long-running operations with strategy indication
- **Status log window**: See exactly what the program is doing with performance context
- **Enhanced error dialogs**: Expandable details with clipboard support
- **Operation history**: 5000-line scrollable history of operations with timing
- **Debug Log**: If using `python` to run the .py without the `-O` commandline switch, a debug log file is produced

---

## 🚀 Quick Start

### System Requirements
- **Windows 10** or **Windows 11**
- **Python 3.13+** (included with most Windows systems)
- **8GB RAM** + additional memory for large folders

### Installation
1. **Download** `FolderCompareSync.py` to your computer and use python to run it
   - *Or open Command Prompt and run:* `python FolderCompareSync.py`

### Basic Usage
1. **Select folders**: Click "Browse" to choose your "Left" and "Right" folders
2. **Choose comparison options**: Select how to compare (size, dates, content)
3. **Compare Folder Trees**: Click "Compare" to scan both folders and show differences
4. **Select files**: Check the boxes next to files you want to copy, notice ticks in both "Left" and "Right"
5. **Check what will happen** Perhaps first enable "DRY RUN Only" to test without making changes!
6. **Copy files**: Click "Copy LEFT to Right" or "Copy RIGHT to Left"
   - Watch the status log for real-time strategy selection and copying!

---

## 🔧 More Details

### **Copy Strategies**
The program automatically selects the optimal copy method.    
File date-created and date-modified timestamps are always copied along with the file.

#### **Direct Copy Strategy** (Small files < 10MB on local drives)
- Good, fast, for documents, images, and small files
- Uses optimized python3 `shutil.copy2` with enhanced metadata handling

#### **Safe Staged Copy Strategy** (Large files ≥ 10MB or network drives)
- Uses atomic rename operations to backup target file before copying
- Rollback capability with timestamp restoration

#### **Network Drive Copy Strategy** (Large files ≥ 10MB or network drives)
- Automatic detection of network drive letters, always uses Safe Staged Copy

### **Wildcard Filtering Examples**
- `*.jpg` - All JPEG images
- `*2024*` - All files with "2024" in the name
- `backup_*.zip` - All backup ZIP files
- `IMG_*.png` - All PNG files starting with "IMG_"

### **Enhanced File Comparison Options can be combined**
- **Existence**: Files that exist in one folder but not the other
- **Size**: Files with different sizes
- **Date Created**: Files with different creation dates
- **Date Modified**: Files with different modification dates
- **SHA512**: **the gold standard safest** Files with different content (cryptographic hash comparison with performance optimization), very slow but safest

### **Smart Selection with Performance Context**
- **Individual files**: Click checkboxes next to specific files to select them for copying
- **Smart folder selection**: Click a folder to select only the different files inside it
- **Bulk selection**: "Select All Differences" buttons for quick selection of the entire folder tree
- **Bulk clear selection**: "Clear All" buttons to start afresh

---


## 🐛 Troubleshooting with Enhanced Diagnostics

### **Potential Issues**

**Copy operation issues:**
- Check the status log for copy strategy being used
- Look for critical error messages with specific guidance
- Check file permissions and disk space
- Ensure destination folders are writable
- Operations automatically use optimal strategy for your drive types


### **Getting Help**
- Check the **status log window** for real-time operation details and performance metrics
- Enable the **debug log** for comprehensive logging with performance tracking
- Review **error messages** for specific guidance on resolving issues with strategy context
- Check per-operation log files (named with timestamps and operation IDs) for detailed troubleshooting


### **Operation Log File Analysis**
Each tree copy operation creates a detailed log file with:
- Performance metrics
- Strategy selection reasoning for each file
- Detailed step-by-step operation breakdown

---

## 📄 License

This project is licensed under the **AGPL-3.0 License** - see the license details for more information.
