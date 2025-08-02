# FolderCompareSync

**A Folder Comparison & Synchronization Tool for Windows**

![Version](https://img.shields.io/badge/version-0.4.0-blue) ![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey) ![License](https://img.shields.io/badge/license-AGPL--3.0-green)

### UNTESTED, UNDER DEVELOPMENT

---

## What is FolderCompareSync?

FolderCompareSync is a powerful, easy-to-use tool that helps you **compare two folders side-by-side** and **synchronize files between them**. Think of it as a professional version of "copy and paste" that shows you exactly what's different and lets you choose what to copy.

### 🎯 Perfect for:
- **Backup verification** - Make sure your backups are complete and up-to-date
- **Project synchronization** - Keep development folders in sync across different locations
- **Data migration** - Safely move files between drives or computers
- **Cleanup operations** - Find duplicate or outdated files
- **Archive management** - Organize and maintain file collections

---

## ✨ Key Features

### 📊 **Smart Comparison**
- **Side-by-side view** of two folder structures
- **Multiple comparison criteria**: file size, dates, content (SHA512 hash)
- **Visual indicators** showing which files are different, missing, or identical
- **Real-time progress** for large folder operations

### 🔍 **Advanced Filtering & Search**
- **Wildcard filtering**: Find specific files with patterns like `*.jpg`, `*backup*`, `IMG_*.png`
- **Sortable columns**: Click any column header to sort by size, date, or status
- **Tree expansion controls**: Expand/collapse entire folder structures instantly

### 🚀 **Professional Copy Operations**
- **Preview before copying**: See exactly what will be copied
- **Progress tracking**: Real-time file-by-file copy progress
- **Error handling**: Continues operation even if some files fail
- **Auto-refresh**: Automatically rescans folders after copying to show current state

### 📝 **Comprehensive Logging**
- **Status log window**: See exactly what the program is doing
- **Operation history**: 500-line scrollable history of all operations
- **Detailed progress**: Progress dialogs for all long-running operations

---

## 🚀 Quick Start

### System Requirements
- **Windows 10** or **Windows 11**
- **Python 3.7+** (included with most Windows systems)
- **50MB RAM** + additional memory for large folders

### Installation
1. **Download** `FolderCompareSync.py` to your computer
2. **Double-click** the file to run it
   - *Or open Command Prompt and run:* `python FolderCompareSync.py`

### Basic Usage
1. **Select folders**: Click "Browse" to choose your left and right folders
2. **Choose comparison options**: Select what to compare (size, dates, content)
3. **Click "Compare"**: The program will scan both folders and show differences
4. **Select files**: Check the boxes next to files you want to copy
5. **Copy files**: Click "Copy LEFT to Right" or "Copy RIGHT to Left"

---

## 💡 Common Use Cases

### 📁 **Backup Verification**
```
Left Folder:  C:\Important Documents\
Right Folder: D:\Backup\Important Documents\
Goal: Verify backup is complete and up-to-date
```
1. Compare both folders
2. Check files marked as "Different" or "Missing"
3. Copy missing or newer files to your backup

### 🔄 **Project Synchronization**
```
Left Folder:  C:\Projects\MyApp\
Right Folder: E:\ProjectBackups\MyApp\
Goal: Keep development and backup in sync
```
1. Use date comparison to find recently modified files
2. Filter by file type (e.g., `*.py` for Python files)
3. Copy newer files to keep everything synchronized

### 🧹 **Cleanup & Organization**
```
Left Folder:  C:\Downloads\
Right Folder: C:\Organized Files\
Goal: Organize downloaded files
```
1. Filter by file type (`*.pdf`, `*.jpg`, etc.)
2. Review files before moving
3. Copy organized files to appropriate folders

---

## 🔧 Advanced Features

### **Wildcard Filtering Examples**
- `*.jpg` - All JPEG images
- `*2024*` - All files with "2024" in the name
- `backup_*.zip` - All backup ZIP files
- `IMG_*.png` - All PNG files starting with "IMG_"

### **Comparison Options**
- **Existence**: Files that exist in one folder but not the other
- **Size**: Files with different sizes
- **Date Created**: Files with different creation dates
- **Date Modified**: Files with different modification dates
- **SHA512**: Files with different content (cryptographic hash comparison)

### **Smart Selection**
- **Individual files**: Click checkboxes next to specific files
- **Smart folder selection**: Click a folder to select only the different files inside it
- **Bulk selection**: "Select All Differences" buttons for quick selection
- **Clear selection**: "Clear All" buttons to start fresh

---

## 📋 Tips & Best Practices

### ✅ **Before You Start**
- **Test with small folders first** to get familiar with the interface
- **Always preview** what will be copied before confirming operations
- **Check available disk space** before large copy operations
- **Close other programs** when working with very large folders

### ⚡ **Performance Tips**
- **Use SHA512 comparison sparingly** - it's thorough but slower for large files
- **Filter large folders** to focus on specific file types
- **Enable Overwrite Mode** if you want to replace existing files
- **Watch the status log** to monitor progress and catch any issues

### 🛡️ **Safety Features**
- **Preview dialogs** show exactly what will be copied
- **Confirmation prompts** prevent accidental operations
- **Error handling** continues operation even if individual files fail
- **Status logging** provides complete record of all operations

---

## 📚 Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Complete version history and new features
- **[SPECIFICATION.md](SPECIFICATION.md)** - Technical details and implementation status
- **Debug Mode**: Run with `python FolderCompareSync.py` for detailed logging
- **Optimized Mode**: Run with `python -O FolderCompareSync.py` for quiet operation

---

## 🐛 Troubleshooting

### **Common Issues**

**Program won't start:**
- Make sure Python 3.7+ is installed
- Try running from Command Prompt: `python FolderCompareSync.py`

**Comparison is slow:**
- Disable SHA512 comparison for faster results
- Use filtering to focus on specific files
- Check available RAM if working with very large folders

**Copy operation fails:**
- Check file permissions and disk space
- Ensure destination folder is writable
- Review the status log for specific error messages

**Missing files in tree:**
- Check if files are hidden or system files
- Verify folder permissions
- Look for error messages in the status log

### **Getting Help**
- Check the **status log window** for detailed information about operations
- Enable **debug mode** for more detailed logging
- Review **error messages** for specific guidance on resolving issues

---

## 📄 License

This project is licensed under the **AGPL-3.0 License** - see the license details for more information.

---

## 🔄 Version Information

**Current Version:** 0.3.1 - Performance Optimizations
- Enhanced support for large files (up to 25GB hash computation)
- Improved filtering capacity (up to 200,000 items)
- Optimized tree processing for massive folder structures

**Previous Major Version:** 0.3.0 - Full Feature Implementation
- Complete wildcard filtering system
- Sortable column headers
- Real file copy operations with auto-refresh
- Professional progress dialogs for all operations

For complete version history, see [CHANGELOG.md](CHANGELOG.md).

---

*FolderCompareSync - Making folder comparison and synchronization simple, safe, and professional.*
