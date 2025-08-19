# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
from FolderCompareSync_Global_Imports import *

# import out global constants first
import FolderCompareSync_Global_Constants as C

# import our flushed_logging before other modules
#from flushed_logging import *   # includes LoggerManager

"""
    Facilitates flushed logging app-wide including within modules.

    At the very top of the main program add: 
        from __future__ import annotations
        import sys, os, threading, logging
        from typing import Optional
        from flushed_logging import *   # includes LoggerManager
    
    In main() BEFORE importing modules which depend on logging:
        # Choose settings
        if __debug__:
            log_level = logging.DEBUG
            log_format = "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
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
        #
        # ***** ONLY NOW can we import modules that use the logger: ***
        #
        import module_a
        #
        module_a.do_something()

    Now in each modules that use the logging, use code like this AFTER flushed_logging was imported and configured in main():
        # module_a.py
        from flushed_logging import *   # includes LoggerManager
        def do_something():
            LoggerManager.logger.info("a message from module_b")
            LoggerManager.logger.log(logging.INFO, "a DEBUG message from module_b")
            LoggerManager.log_and_flush(logging.DEBUG,"another DEBUG message from module_b")

    NEW NEW NEW: 
        Remember to use %(callpath)s in your debug format string in main(): like this:
            if __debug__:
                log_format = "%(asctime)s - %(levelname)s - %(callpath)s - %(message)s"
            else:
                log_format = "%(asctime)s - %(levelname)s - %(message)s"
"""

# --- call-path helpers (module-level) ------------------------------------------------
import inspect  # explicit import used for building a compact call chain

def _build_callpath(max_entries: int = 4,
                    skip_modules: tuple[str, ...] = ("logging", __name__)) -> str:
    """
    Return a compact call path like:
        'FolderCompareSync.main:178 -> FolderCompareSync_class.__init__:357'
    Skips frames from logging and this module to avoid noise.
    """
    parts: list[str] = []
    # stack[0]=_build_callpath, [1]=wrapper(_log_and_flush/log_and_flush), [2+]=actual callers
    for frameinfo in inspect.stack()[2:]:
        mod = frameinfo.frame.f_globals.get("__name__", "")
        if any(mod.startswith(s) for s in skip_modules):
            continue
        mod_short = mod.rsplit(".", 1)[-1]
        parts.append(f"{mod_short}.{frameinfo.function}:{frameinfo.lineno}")
        if len(parts) >= max_entries:
            break
    #return "->".join(parts) if parts else f"{__name__}.log_and_flush"           # innermost -> outermost
    return "->".join(reversed(parts)) if parts else f"{__name__}.log_and_flush"  # outermost -> innermost

class _DefaultCallpathFilter(logging.Filter):
    """
    Ensures record.callpath always exists so formatters with %(callpath)s don't KeyError.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "callpath"):
            record.callpath = f"{record.module}.{record.funcName}:{record.lineno}"
        return True
# --- call-path helpers (module-level) ------------------------------------------------

class LoggerManager_class:
    def __init__(
        self,
        *,
        log_name: str = "FolderCompareSync",
        log_to_stdout: bool = False,
        log_to_file: str | None = None,
        log_level: int = logging.DEBUG,
        log_format: str = "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    ) -> None:

        # Build handlers per instance
        handlers: list[logging.Handler] = []

        if log_to_file:
            fh = logging.FileHandler(log_to_file, mode="w", encoding="utf-8")
            handlers.append(fh)

        if log_to_stdout:
            ch = logging.StreamHandler(sys.stdout)
            # Best effort UTF-8 console
            if hasattr(sys.stdout, "reconfigure"):
                try:
                    sys.stdout.reconfigure(encoding="utf-8")
                except Exception:
                    pass
            handlers.append(ch)

        # Configure *this* logger
        self._logger = logging.getLogger(log_name)
        self._logger.setLevel(log_level)
        formatter = logging.Formatter(log_format)

        # Avoid duplicate handlers if an object is re-created with same name
        existing = {type(h) for h in self._logger.handlers}
        for h in handlers:
            if type(h) not in existing:
                h.setFormatter(formatter)
                self._logger.addHandler(h)

        # Attach filter so %(callpath)s is always present
        self._logger.addFilter(_DefaultCallpathFilter())
        self._handlers = self._logger.handlers  # for flushing

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    # class level method not exposed
    def _log_and_flush(self, level: int, msg: str, *args, **kwargs) -> None:
        # If caller didn't specify a stacklevel, default to 3:
        #   0 = logger.log, 1 = _log_and_flush, 2 = log_and_flush, 3 = ORIGINAL CALLER
        stacklevel = kwargs.pop("stacklevel", 3)
        
        # Inject a compact call-chain into the record (available as %(callpath)s)
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("callpath", _build_callpath())

        self._logger.log(level, msg, *args, stacklevel=stacklevel, extra=extra, **kwargs)
        for h in self._handlers:
            try:
                h.flush()
            except Exception:
                pass

# --- Expose helpers for other modules ---

def log_and_flush(level: int, msg: str, *args, **kwargs) -> None:
    """
    Convenience wrapper so modules can call `log_and_flush(...)` directly
    after main() has called set_logger_manager(...).
    """
    if LoggerManager is None:
        # Fallback: log via root logger so you don't crash before init
        # we're one wrapper frame above the caller here -> stacklevel=2
        stacklevel = kwargs.pop("stacklevel", 2)
        # Inject callpath here as well
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("callpath", _build_callpath())
        logging.log(level, msg, *args, stacklevel=stacklevel, extra=extra, **kwargs)
        for h in logging.getLogger().handlers:
            try: h.flush()
            except Exception: pass
        return
    # Delegates to _log_and_flush, which defaults stacklevel=3 and injects callpath
    LoggerManager._log_and_flush(level, msg, *args, **kwargs)

def get_log_level() -> int:
    """
    Return the effective logging level of the application logger if available,
    otherwise the root logger's effective level.
    """
    if LoggerManager is not None:
        return LoggerManager.logger.getEffectiveLevel()
    return logging.getLogger().getEffectiveLevel()


# A single slot to hold “the” instance (set by main)
LoggerManager: Optional[LoggerManager_class] = None

def set_logger_manager(m: LoggerManager_class) -> None:
    """Call this once in main() after constructing/initializing your LoggerManager."""
    global LoggerManager
    LoggerManager = m

# Handy re-exports
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# 'from flushed_logging import *' will import these things:
__all__ = [
    "LoggerManager_class",                              # the class
    "set_logger_manager",                               # method to set (save) the LoggerManager_class instantiated object reference from main()
    "LoggerManager",                                    # the saved lLoggerManager_class instantiated object reference from main()
    "log_and_flush",                                    # export reference to the Convenience wrapper 
    "get_log_level",                                    # what the prevailing level; is initialized to.
    "logging",                                          # reference for using logging.DEBUG logging.INFO logging.WARNING logging.ERROR logging.CRITICAL 
    "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL",    # short name references eg to logging.DEBUG logging.INFO etc
]
