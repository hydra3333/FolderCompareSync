#!/usr/bin/env python3
"""
FolderCompareSync - A Folder Comparison & Synchronization Tool

Version:
         v002.0003 - moved main classes into their own separate .py files, included by 'from xxx.py include xxx'
         v002.0000 - reorganised class and def for
                     Reduced Global Namespace Pollution,
                     Logical Grouping & Proper Encapsulation,
                     Clear Ownership of functions
         v001.0023 - ensure deletions occurs bottom up so folders do not get deleted before the files in them
         v001.0022 - reorganize bottom area button layout to put copy and delete orphan buttons on same row
         v001.0021 - fix UI recreation to use in-place rebuild instead of new instance
         v001.0020 - fix threading conflict and UI recreation timing in debug global editor
         v001.0019 - add DebugGlobalEditor_class integration with destroy/recreate UI refresh pattern
         v001.0018 - fix delete orphans dialog cancel button error by adding None check for manager result,
                     fix static method calling syntax in delete orphans functionality 
         v001.0017 - enhance delete orphans logic to distinguish true orphans from folders containing orphans
         v001.0016 - fix button and status message font scaling to use global constants consistently
         v001.0015 - add configurable tree row height control for compact folder display
         v001.0014 - add configurable font scaling system for improved UI text readability

Author: hydra3333
License: AGPL-3.0
GitHub: https://github.com/hydra3333/FolderCompareSync

LIMITS:
=======
- Maximum 200,000 files/folders supported with early abort protection
- 5,000 line status log history for comprehensive operation tracking
- Performance warnings displayed to users about large folder operation implications
- Early detection and handling of operations exceeding system limits

NOTE RE LOGGING:
    # ONLY import modules that use the logger
    # in main() AFTER setting up logging
    # eg
    ... code to setup loggin
    import module_a

KNOW THIS: "import FolderCompareSync_Global_Constants as C"  vs  "from FolderCompareSync_Global_Constants import *"
-------------------------------------------------------------------------------------------------------------------

In Python, modules are singletons per process — they live ONCE in sys.modules.
Because Python caches imported modules in sys.modules, any object you put in a module becomes
a process-wide singleton. 
Imported modules are dynamically shared by modules as long as every module imports
that same module via "import xxx as Y".
Hence module level global variables in an imported module are dynamically shared by modules as long as
every module imports that same module via "import xxx as Y".

When module A does:
    import FolderCompareSync_Global_Constants as C
Python looks in sys.modules:
If the module has not been loaded yet, it’s imported and inserted into sys.modules["FolderCompareSync_Global_Constants"].
Module A then binds its local name C to that single module object.

When module B later does the same import:
    import FolderCompareSync_Global_Constants as C
Python checks sys.modules, sees it’s already loaded, and reuses the same module object.
Module B then binds its local name C to that same object.

So:
"C in A" and "C in B" are just two different references to the same underlying module object.
If a separate module DebugGlobalEditor modifies C.STATUS_LOG_MAX_HISTORY, both module A and module B
see the updated value in C.STATUS_LOG_MAX_HISTORY IMMEDIATELY because they reference the same module object.

What wouldn’t see changes is if module D instead did:
    from FolderCompareSync_Global_Constants import STATUS_LOG_MAX_HISTORY
Using "from ... import ..." COPIES the value into module D’s local globals at import time, so 
- later updates to STATUS_LOG_MAX_HISTORY in module D will NOT propagate back into sys.modules
- later updates to "C.STATUS_LOG_MAX_HISTORY" by other modules using "import ... as C" will NOT be seen by module D

Summary:
1. "import … as C"    ->  shared live module object (safe for on-the-fly editing).
2. "from … import X"  ->  copies the value at import time (edits won’t propagate).

Example code that shares dynamically:
    from __future__ import annotations
    import FolderCompareSync_Global_Constants as C     # reference constants via "C.variable_name"

Example code that DOES NOT share dynamically:
    from __future__ import annotations
    from FolderCompareSync_Global_Constants import *   # reference constants via "variable_name" (no "C.")

"""
# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
from FolderCompareSync_Global_Imports import *

# import out global constants first
import FolderCompareSync_Global_Constants as C

# import our flushed_logging before other modules
#from flushed_logging import log_and_flush, LoggerManager_class, set_logger_manager, get_log_level, , LoggerManager
from flushed_logging import * 

# import the main controller
from FolderCompareSync_class import FolderCompareSync_class

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def main():
    # ----- Start SETUP THE GLOBAL LOGGER -----
    # Choose logging settings. Remember, debug log format relies on our home grown callpath.
    if __debug__:
        log_level = logging.DEBUG
        log_format = "%(asctime)s - %(levelname)s - %(callpath)s - %(message)s"
        log_to_stdout = True
    else:
        log_level = logging.INFO
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        log_to_stdout = False
    # Construct and publish the logging manager
    lm = LoggerManager_class(
        log_name="FolderCompareSync",
        log_to_stdout=log_to_stdout,
        log_to_file=os.path.join(os.path.dirname(__file__), "FolderCompareSync.log"),
        log_level=log_level,
        log_format=log_format,
    )
    set_logger_manager(lm)
    # ***** ONLY after that can we import modules that use the logger or use the logger ***
    # ----- End  SETUP THE GLOBAL LOGGER -----
    
    # ------------------------ START These imports MUST be in def main() AFTER setting up the logger and dynamic imports ------------------------
    # Import all of the reorganised Classes etc
    # The "dynamic imports" have already been done above so impoting here should pick up every global import
    from ProgressDialog_class        import ProgressDialog_class, CopyProgressManager_class
    from FileTimestampManager_class  import FileTimestampManager_class
    from FileCopyManager_class       import FileCopyManager_class
    from DeleteOrphansManager_class  import DeleteOrphansManager_class
    from DebugGlobalEditor_class     import DebugGlobalEditor_class
    from FolderCompareSync_class     import FolderCompareSync_class
    # ------------------------ END  These imports MUST be in def main() AFTER setting up the logger and dependencies checked ------------------------

    log_and_flush(logging.INFO, "=== FolderCompareSync Startup ===")
    if __debug__:
        log_and_flush(logging.DEBUG, "Working directory : " + os.getcwd())
        log_and_flush(logging.DEBUG, "Python version    : " + sys.version)
        log_and_flush(logging.DEBUG, "Computer name     : " + platform.node())
        log_and_flush(logging.DEBUG, "Platform          : " + sys.platform)
        log_and_flush(logging.DEBUG, "Architecture      : " + platform.architecture()[0])
        log_and_flush(logging.DEBUG, "Machine           : " + platform.machine())
        log_and_flush(logging.DEBUG, "Processor         : " + platform.processor())

    # Detailed Windows information
    if sys.platform == "win32":
        try:
            win_ver = platform.win32_ver()
            log_and_flush(logging.DEBUG, f"Windows version   : {win_ver[0]}")
            log_and_flush(logging.DEBUG, f"Windows build     : {win_ver[1]}")
            if win_ver[2]:  # Service pack
                log_and_flush(logging.DEBUG, f"Service pack      : {win_ver[2]}")
            log_and_flush(logging.DEBUG, f"Windows type      : {win_ver[3]}")
            # Try to get Windows edition
            try:
                edition = platform.win32_edition()
                if edition:
                    log_and_flush(logging.DEBUG, f"Windows edition   : {edition}")
            except:
                pass
            # Extract build number from version string like "10.0.26100"
            version_parts = win_ver[1].split('.')
            if len(version_parts) >= 3:
                build_num = version_parts[2]  # Get "26100" from "10.0.26100"
            else:
                build_num = win_ver[1]  # Fallback to full string
                
            win_versions = {
                # Windows 11 versions
                "22000": "21H2 (Original release)",
                "22621": "22H2", 
                "22631": "23H2",
                "26100": "24H2",
                # Future Windows versions (anticipated)
                "27000": "25H1 (anticipated)",
                "27100": "25H2 (anticipated)"
            }
            if build_num in win_versions:
                log_and_flush(logging.DEBUG, f"Windows 11 version: {win_versions[build_num]} (build {build_num})")
            elif build_num.startswith("27") or build_num.startswith("28"):
                log_and_flush(logging.DEBUG, f"Windows version   : Future windows build {build_num}")
            elif build_num.startswith("26") or build_num.startswith("22"):
                log_and_flush(logging.DEBUG, f"Windows 11 version: Unknown windows build {build_num}")
            elif build_num.startswith("19"):
                log_and_flush(logging.DEBUG, f"Windows 10 build  : {build_num}")
            else:
                log_and_flush(logging.DEBUG, f"Windows version   : Unknown windows build {build_num}")
        except Exception as e:
            log_and_flush(logging.DEBUG, f"Error getting Windows details: {e}")

    # Log  configuration including new limits and features
    log_and_flush(logging.DEBUG, "FolderCompareSync Configuration:")
    log_and_flush(logging.DEBUG, f"  Max files/folders: {C.MAX_FILES_FOLDERS:,}")
    log_and_flush(logging.DEBUG, f"  Status log history: {C.STATUS_LOG_MAX_HISTORY:,} lines")
    log_and_flush(logging.DEBUG, f"  Copy strategy threshold: {C.FILECOPY_COPY_STRATEGY_THRESHOLD_BYTES:.1f} GB")
    log_and_flush(logging.DEBUG, f"  SHA512 status threshold: {C.SHA512_STATUS_MESSAGE_THRESHOLD / (1024*1024):.1f} MB")
    log_and_flush(logging.DEBUG, f"  Simple verification enabled: {C.COPY_VERIFICATION_ENABLED}")
    log_and_flush(logging.DEBUG, f"  Retry count: {C.COPY_RETRY_COUNT}")
    log_and_flush(logging.DEBUG, f"  Network timeout: {C.COPY_NETWORK_TIMEOUT}s")
    log_and_flush(logging.DEBUG, f"  Dry run support: Enabled")
    log_and_flush(logging.DEBUG, f"  Status log export: Enabled")
    log_and_flush(logging.DEBUG, f"  Error details dialog: Enabled")
    log_and_flush(logging.DEBUG, f"  Path handling: Standardized on pathlib")
    
    try:
        FolderCompareSync_class_app = FolderCompareSync_class()
        FolderCompareSync_class_app.run()    # start the application GUI event loop
    except Exception as e:
        log_and_flush(logging.ERROR, f"Fatal error: {type(e).__name__}: {str(e)}")
        if __debug__:
            log_and_flush(logging.DEBUG, "Fatal error traceback:")
            log_and_flush(logging.DEBUG, traceback.format_exc())
        raise
    finally:
        log_and_flush(logging.INFO, "=== FolderCompareSync Shutdown ===")


if __name__ == "__main__":
    main()
