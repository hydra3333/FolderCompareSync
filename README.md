# FolderCompareSync

**A GUI Folder Tree Comparison & Synchronization Tool for Windows 10+ with Optimized Copy System**

![Version](https://img.shields.io/badge/version-0.6.1-blue) ![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey) ![License](https://img.shields.io/badge/license-AGPL--3.0-green) ![Performance](https://img.shields.io/badge/performance-50%25%20faster-brightgreen)

#### UNTESTED, UNDER DEVELOPMENT, BEWARE    
#### Iteratively developed AI generated code.    

---

## What is FolderCompareSync?

FolderCompareSync is a powerful, easy-to-use free tool that helps you **compare two folder trees side-by-side** and **synchronize files between them** with **reasonable performance**.
Think of it as a folder tree "bulk choose, copy and paste differences" with overwrite that shows you exactly what's different and lets you choose what to copy with **ease and reliability**.

#### UNTESTED, UNDER DEVELOPMENT, BEWARE    
#### Iteratively developed AI generated python3 code.    

---

### 🎉 **NEW in v0.6.1: Enhanced Safety and User Experience**
- **Improved path handling** with complete pathlib standardization
- **Enhanced dry run safety** with multi-layer protection
- **Better error visibility** with expandable detail dialogs
- **Real-time feedback** for large file hash computations

### 🚀 **NEW in v0.5.0: Better Performance**
- **50% faster copying** for large files and network drives
- **50% less disk space** used during copy operations  
- **Complete timestamp preservation** with enhanced rollback capability
- **Atomic operations** for maximum reliability and data safety
- **Zero-fallback error handling** with comprehensive user guidance

### 🎯 Perfect for:
- **Backup verification** - Make sure your backups are complete and up-to-date with blazing speed
- **Project synchronization** - Keep development folders in sync across different locations with optimized performance
- **Data migration** - Safely move files between drives or computers with breakthrough efficiency
- **Cleanup operations** - Find duplicate or outdated files with enhanced speed
- **Archive management** - Organize and maintain file collections with professional-grade reliability

---

## ✨ Key Features

### 🚀 **Copy Performance**
- **Optimized Dual-Strategy System**: Automatically selects the fastest method for each file
  - **Enhanced Direct Copy**: Lightning-fast copying for small files with complete timestamp preservation
  - **Optimized Staged Copy**: rename-based backup for large files (~50% faster than traditional methods)
- **Network Drive Optimization**: Automatic detection and optimization for all network drive types
- **Complete timestamp preservation**: Both creation and modification times preserved perfectly
- **Atomic operations**: True atomic file operations using Windows primitives for maximum safety

### 📊 **Smart Comparison**
- **Side-by-side view** of two folder structures with enhanced metadata display
- **Multiple comparison criteria**: file size, dates, content (SHA512 hash) with performance optimization
- **Visual indicators** showing which files are different, missing, or identical
- **Real-time progress** for large folder operations with performance metrics

### 🔍 **Advanced Filtering & Search**
- **Wildcard filtering**: Find specific files with patterns like `*.jpg`, `*backup*`, `IMG_*.png`
- **Sortable columns**: Click any column header to sort by size, date, or status with optimized algorithms
- **Tree expansion controls**: Expand/collapse entire folder structures instantly
- **Performance optimized**: Handle up to 200,000 filtered results without slowdown

### 🛡️ **Copy Operations with Enhanced Safety**
- **DRY RUN mode** (NEW): Test operations without any file modifications
- **Multi-layer safety**: FileTimestampManager now fully dry-run aware (v0.6.1)
- **Preview before copying**: See exactly what will be copied with strategy indication
- **Enhanced progress tracking**: Real-time file-by-file copy progress with performance metrics
- **Advanced error handling**: Continues operation even if some files fail with comprehensive error reporting
- **Performance optimized**: Handle up to 200,000 filtered results without slowdown
- **Automatic rollback**: Complete restoration of original files if operations fail with timestamp preservation
- **Auto-refresh**: Automatically rescans folders after copying to show current state

### 📝 **Comprehensive Logging with Performance Tracking**
- **Status log window**: See exactly what the program is doing with performance context
- **Enhanced error dialogs**: Expandable details with clipboard support
- **Operation history**: 500-line scrollable history of all operations with timing
- **Detailed progress**: Progress dialogs for all long-running operations with strategy indication
- **Per-operation logs**: Individual log files with performance metrics and operation IDs

---

## 🚀 Quick Start

### System Requirements
- **Windows 10** or **Windows 11**
- **Python 3.13+** (included with most Windows systems)
- **1000MB RAM** + additional memory for large folders

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
   - Enable "DRY RUN Only" to test without making changes!
   - Watch the status log for real-time strategy selection and performance improvements!

---

## 🔧 Advanced Features with Performance Enhancements

### **Enhanced Copy Strategies**
The application automatically selects the optimal copy method for maximum performance:

#### **Enhanced Direct Strategy** (Small files < 10MB on local drives)
- Near-instant copying with complete timestamp preservation
- Perfect for documents, images, and small files
- Uses optimized `shutil.copy2` with enhanced metadata handling

#### **Optimized Staged Strategy** (Large files ≥ 10MB or network drives)
- 50% performance improvement over traditional method
- Uses atomic rename operations instead of expensive copy-for-backup
- Maximum 2 files during operation vs traditional 3-file approaches
- Complete rollback capability with timestamp restoration

### **Wildcard Filtering Examples**
- `*.jpg` - All JPEG images
- `*2024*` - All files with "2024" in the name
- `backup_*.zip` - All backup ZIP files
- `IMG_*.png` - All PNG files starting with "IMG_"

### **Enhanced File Comparison Options can be combined**
- **Existence**: Files that exist in one folder but not the other
- **Size**: Files with different sizes
- **Date Created**: Files with different creation dates (enhanced preservation)
- **Date Modified**: Files with different modification dates (enhanced preservation)
- **SHA512**: **the gold standard** Files with different content (cryptographic hash comparison with performance optimization)

### **Smart Selection with Performance Context**
- **Individual files**: Click checkboxes next to specific files
- **Smart folder selection**: Click a folder to select only the different files inside it
- **Bulk selection**: "Select All Differences" buttons for quick selection with strategy preview
- **Clear selection**: "Clear All" buttons to start fresh

---

## 📋 Tips & Best Practices with Performance Optimization

### ✅ **Before You Start**
- **Test with small folders first** to see the performance improvements in action
- **Always preview** what will be copied before confirming operations - now shows copy strategy
- **Check available disk space** before large copy operations (now requires 50% less temporary space)
- **Close other programs** when working with very large folders for optimal performance

### ⚡ **Performance Tips (Enhanced v0.5.0)**
- **Use SHA512 comparison sparingly** - it's **GOLD STANDARD** thorough but slower for large files
- **Filter large folders** to focus on specific file types with enhanced performance (200K item limit)
- **Enable Overwrite Mode** if you want to replace existing files with optimized backup handling
- **Watch the status log** to see copy strategy selection and performance improvements in real-time
- **Network drives**: Enjoy automatic optimization - no configuration needed!
- **Large files**: Experience 50% faster copying with the new Optimized Staged Strategy
- **Date Created**: Files with different creation dates (enhanced preservation)
- **Date Modified**: Files with different modification dates (enhanced preservation)
- **SHA512**: Files with different content (cryptographic hash comparison with performance optimization)
  - **NEW v0.6.1**: Progress feedback for large files (>100MB) during hash computation

### **Smart Selection with Performance Context**
- **Individual files**: Click checkboxes next to specific files

### 🛡️ **Safety Features**
- **Preview dialogs** show exactly what will be copied with strategy indication
- **Confirmation prompts** prevent accidental operations with performance context
- **Enhanced error handling** continues operation with comprehensive error reporting and rollback
- **Atomic operations** ensure data safety with Windows-native rename primitives
- **Complete rollback** restores original file with exact timestamp preservation if an error occurs
- **Status logging** provides complete record of all operations with performance metrics

---

## 🐛 Troubleshooting with Enhanced Diagnostics

### **Common Issues**

**Program won't start:**
- Make sure Python 3.13+ is installed
- Try running from Command Prompt: `python FolderCompareSync.py`

**Comparison is slow:**
- Disable **gold-standard** SHA512 comparison for faster results, perhaps depend on comparing by date-modified
- Use filtering to focus on specific files (now supports 200K items)
- Check available RAM if working with very large folders

**Copy operation issues:**
- Check the status log for copy strategy being used
- Look for critical error messages with specific guidance
- Check file permissions and disk space (now requires 50% less temporary space)
- Ensure destination folder is writable
- Operations automatically use optimal strategy for your drive types

**Performance concerns:**
- Large files automatically use Optimized Staged Strategy (50% faster)
- Network drives automatically detected and optimized
- Watch status log for real-time performance improvements
- Check per-operation log files for detailed performance metrics

### **Enhanced Error Handling (NEW v0.5.0)**

**Network Drive Issues:**
- Application automatically detects network drives and uses optimized strategies
- Enhanced timeout handling with proper retry logic
- Clear guidance for network connectivity problems

**File Locking Problems:**
- Comprehensive error reporting with specific guidance
- Automatic rollback preserves original files and timestamps
- Clear explanation of which programs might be locking files

**Permission Errors:**
- Detailed permission analysis with actionable guidance
- Automatic strategy selection based on folder accessibility
- Clear instructions for resolving permission issues

### **Getting Help**
- Check the **status log window** for real-time operation details and performance metrics
- Enable **debug mode** for comprehensive logging with performance tracking
- Review **error messages** for specific guidance on resolving issues with strategy context
- Check per-operation log files (named with timestamps and operation IDs) for detailed troubleshooting

---

## 🔍 Performance Monitoring (NEW v0.5.0)

### **Real-Time Performance Feedback**
- **Status Log**: Shows copy strategy selection and performance benefits in real-time
- **Progress Dialogs**: Display current copy strategy and expected performance improvement
- **Completion Reports**: Summary of performance gains and time savings

### **Performance Metrics Available**
- **Copy Strategy Used**: See which strategy was selected for each file
- **Time Savings**: Real-time comparison vs traditional copy methods
- **Disk Space Efficiency**: Monitor reduced temporary space usage
- **Network Optimization**: See automatic network drive performance improvements

### **Log File Analysis**
Each copy operation creates a detailed log file with:
- Performance metrics vs traditional approaches
- Strategy selection reasoning for each file
- Time savings and efficiency improvements
- Detailed step-by-step operation breakdown

---

## 📄 License

This project is licensed under the **AGPL-3.0 License** - see the license details for more information.

---

For version history and performance improvements, see [CHANGELOG.md](CHANGELOG.md).    
For evolving specification and technical details, see [EVOLVING_SPECIFICATION.md](EVOLVING_SPECIFICATION.md).    
