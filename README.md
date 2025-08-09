# FolderCompareSync

**A GUI Folder Tree Comparison & Synchronization Tool for Windows 10+ with Optimized Copy System**

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey)
![License](https://img.shields.io/badge/license-AGPL--3.0-green) 
![Language](https://img.shields.io/badge/language-Python3-blue)
![Status](https://img.shields.io/badge/status-Initial%20Release-green)

<!--
Common Statuses
![Status: Active](https://img.shields.io/badge/status-active-brightgreen)
![Status: Beta](https://img.shields.io/badge/status-beta-blue)
![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)
![Status: Deprecated](https://img.shields.io/badge/status-deprecated-red)
![Status: Inactive](https://img.shields.io/badge/status-inactive-lightgrey)
![Status](https://img.shields.io/badge/status-Under%20Development-orange) 

Common status labels
active, maintained, stable
alpha, beta, experimental
deprecated, legacy, archived, inactive

Typical named colors
Greens: brightgreen, green, yellowgreen
Yellows/Oranges: yellow, orange
Reds: red, crimson, firebrick
Blues/Purples: blue, navy, blueviolet
Neutrals: lightgrey, grey/gray, black

Semantic: 
success (brightgreen), informational (blue), critical (red), inactive (lightgrey), important (orange) 

How to craft your own
https://img.shields.io/badge/<LABEL>-<MESSAGE>-<COLOR>
Replace <LABEL>, <MESSAGE>, and <COLOR> with whatever text and named color you like. (Spaces become %20)
-->

#### Iteratively developed AI generated code.    

---

## What is FolderCompareSync?

**FolderCompareSync** is a python GUI based tool to **compare two folder trees side-by-side** and **synchronize selected files between them** with **date-created/date-modified timestamp preservation**.    

Think of it as a folder tree "bulk choose, copy and paste the differences" with optional overwrite that shows you exactly what's different and lets you choose what to copy.
Enabling SHA512 comparison is slow (where lots of files or large files eg 2GB+) but detects differences in file content where they may cheekily have the same folder/filename/size/date-created/date-modified.

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
- **Large limits**: Handle up to 100,000 files (very large folder trees = very very slow, likely laggy responses)
- **Atomic operations**: True atomic file operations using Windows primitives

### 📊 **Selectable Comparison Criteria**
- **Side-by-side view** of two folder structures with relevant metadata display
- **Multiple optional comparison criteria**: file size, dates-created/date-modified, content (SHA512 hash, very slow but safest)
- **Visual indicators** showing which files are different, missing, or identical

### 🔍 **Advanced Filtering & Search**
- **Wildcard filtering**: Find specific files in the folder trees with patterns like `*.jpg`, `*backup*`, `IMG_*.png`
- **Sortable columns**: Click any column header to sort by size, date, maintaining folder locations
- **Tree expansion controls**: Expand/collapse entire or partial folder tree structures instantly

### 🛡️ **Copy Operations with Safety**
- **DRY RUN mode**: Test operations without any actual changes, to see what will happen without it happening
- **Progress tracking**: Real-time file-by-file copy progress
- **Error handling**: Continues operation even if some files fail, with comprehensive error reporting
- **Automatic rollback**: Complete restoration of original files with timestamp preservation if "Safe Staged Copy" operations fail during copying
- **Auto-refresh**: Automatically rescans folders after copying to show current state

### 📝 **Logging with Performance Tracking**
- **Detailed progress**: Progress dialogs for all long-running operations with strategy indication
- **Status log window**: See exactly what the program is doing with performance context
- **Error dialogs**: Expandable details with clipboard support
- **Operation history**: 5000-line scrollable history of operations with timing
- **Debug Log**: If using `python` to run the .py without the `-O` commandline switch, a debug log file is produced

---

## 🚀 Quick Start

### System Requirements
- **Windows 10** or **Windows 11**
- **Python 3.13+** installer downloadable from [python.org](https://www.python.org/downloads/) - installation is per-user, no need for Admin privilege
- **8GB RAM** + additional memory for large folders

### Installation Requirements
- **Self-contained Standalone EXE version:** No requirements (**PyInstaller** packs a python interpreter runtime into the .exe so no need to install python separately)
- **Python script version:** 
1. Python 3.13+ i.e. if running the source .py rather than the self-contained Standalone EXE
2. Python moodules `tzdata` and `python-dateutil`

#### Installation

`FolderCompareSync.py`can be downloaded and run as a single Windows Self-contained Standalone `.exe` without installing Python,
or alternatively as a standard .py file in the Release source (the .exe is built automatically by github for each Release).

If running the source `FolderCompareSync.py` then ensure the latest timezone modules and data 
(modules `tzdata` and `python-dateutil`) are available for python to correctly perform timestamping actions.
Install modules `tzdata` and `python-dateutil` using the pip command (you may need upgrade these when timezone data updates are released):
```
pip install --upgrade --retries 10 tzdata python-dateutil
```
You may also need upgrade these modules when timezone data updates are released).

#### ✅ [**Download the latest Windows self-contained Standalone EXE here**](https://github.com/hydra3333/FolderCompareSync/releases/latest/download/FolderCompareSync.exe)

- This is a **self-contained Standalone EXE** built using **PyInstaller**.
- No Python installation or external dependencies are required since these are bundled inside the self-contained Standalone EXE file.
- Works on **Windows 10 and 11**.
- Once automatically packed into a **self-contained Standalone EXE** by the ubiquitous **PyInstaller**, Windows Defender falsely flags it as containing malware.
If you're uncomfortable with that, perhaps download (and review) the source .py and run that instead.
- Or, perhaps, to verify that the `FolderCompareSync.exe` you downloaded matches the published github auto-built Release and has not been tampered with, you may choose to follow these steps:
1. Download both of these from the Release:
   - `FolderCompareSync.exe`
   - `FolderCompareSync.exe.sha512`
2. Open **Command Prompt** in the folder containing these files.
3. Run the following command to compute the SHA512 hash of the EXE:
```
certutil -hashfile FolderCompareSync.exe SHA512
```
4. Compare the output hash with the contents of the `FolderCompareSync.exe.sha512` file. They **should** match exactly.
If the SHA512 hashes do not match, do not run the executable as it may have been tampered with.

#### ✅ [**Or, Download the latest source .zip to obtain `FolderCompareSync.py`**](https://github.com/hydra3333/FolderCompareSync/releases/latest)

- `FolderCompareSync.py` is in the downloadable .zip file and can be reviewed by you for your safety and peace of mind.
- Requires and works in **Python 3.13.5+**.

### Running the Self-contained Standalone EXE   

Open **Command Prompt** in the folder with your patch file and run:

```cmd
REM Ensure latest timezone modules and data are available to python for correct timestamping actions
pip install --upgrade --retries 10 tzdata python-dateutil
python FolderCompareSync.py -O
```

### Basic Usage
1. **Select folders**: Click "Browse" to choose your "Left" and "Right" folders
2. **Choose comparison options**: Select how to compare (size, dates, content)
3. **Compare Folder Trees**: Click "Compare" to scan both folders and show differences
4. **Select files**: Check the boxes next to files you want to copy, notice ticks in both "Left" and "Right"
5. **Check what will happen** Perhaps first enable "DRY RUN Only" to test without making changes!
6. **Copy files**: Click "Copy LEFT to Right" or "Copy RIGHT to Left"
   - Watch the status log for real-time strategy selection and copying!

---

## 🔧 More Info

### **Foreward**
Drafted, fixed, and extended by Claude AI.

### **Copy Strategies**
The program automatically selects the optimal copy method.    
File date-created and date-modified timestamps are always copied along with the file.

#### **Direct Copy Strategy** (Small files < 10MB on local drives)
- Good, fast, for documents, images, and small files
- Uses optimized python3 `shutil.copy2` and native timestamp metadata handling

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

### **File Comparison Options can be combined**
- **Existence**: Files that exist in one folder but not the other
- **Size**: Files with different sizes
- **Date Created**: Files with different creation dates
- **Date Modified**: Files with different modification dates
- **SHA512**: **the gold standard safest** Files with different content (cryptographic hash comparison with performance optimization), very slow but safest

### **Selectable Selection with Performance Context**
- **Individual files**: Click checkboxes next to specific files to select them for copying
- **Quick folder differences selection**: Click a folder checkbox to select only the different files inside it
- **Bulk selection**: "Select All Differences" buttons for quick selection of the entire folder tree
- **Bulk clear selection**: "Clear All" buttons to start afresh

---

## 🐛 Troubleshooting with Diagnostics

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
