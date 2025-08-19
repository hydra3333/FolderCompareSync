# from __future__ imports MUST occur at the beginning of the file, annotations become strings resolved lazily
from __future__ import annotations 

# import out global imports
from FolderCompareSync_Global_Imports import *

# import out global constants first
import FolderCompareSync_Global_Constants as C

# import our flushed_logging before other modules
#from flushed_logging import *   # includes LoggerManager
from flushed_logging import log_and_flush, get_log_level, LoggerManager

# Import the things this class references
# nil

class DebugGlobalEditor_class:
    """
    DebugGlobalEditor_class.py
    Single-class, drop-in Tkinter dialog to view/edit top-level simple globals and optionally
    recompute derived globals via AST. Python 3.13.5+. No external deps.
    
    Usage (example):
        if __debug__:
            editor = DebugGlobalEditor_class(root)  # root is your Tk() or Toplevel
            result = editor.open()

    Single-class implementation:
    - All helpers are nested as inner classes or static methods.
    - Hard guard: only top-level assignments are discovered & recomputed.
    - Supports JSON save/load, revert to defaults, dependency inspector.

    DEPENDENCIES: 
    =============
    1.  MANDATORY: "logger" MUST be setup in the main program BEFOREHAND 
        with "log_and_flush" as well (see below) ...
        Usage like :
            log_and_flush(logging.DEBUG, "Dep-graph cache hit for %s", self._module_key)

        # ============================================================================
        # Setup logging loglevel based on __debug__ flag
        # using "-O" on the python commandline turns __debug__ off:  python -O FolderCompareSync.py
        if __debug__:
            log_level = logging.DEBUG
            log_format = '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        else:
            log_level = logging.INFO
            log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # Create handlers list with UTF-8 encoding support:
        # Add a handler for file logging, since that is always enabled
        handlers = [
            logging.FileHandler(
                os.path.join(os.path.dirname(__file__), 'foldercomparesync.log'), 
                mode='w', 
                encoding='utf-8'  # Ensure UTF-8 encoding for file output
            )
        ]
        # When in debug mode, when __debug__ is True, add a handler for console logging, only 
        #    ... i.e. when -O is missing from the python commandline
        if __debug__:
            # Create console handler with UTF-8 encoding to handle Unicode filenames
            console_handler = logging.StreamHandler()
            console_handler.setStream(sys.stdout)  # Explicitly use stdout
            # Set UTF-8 encoding if possible (for Windows Unicode support)
            if hasattr(sys.stdout, 'reconfigure'):
                try:
                    sys.stdout.reconfigure(encoding='utf-8')
                except Exception:
                    pass  # If reconfigure fails, continue with default encoding
            handlers.append(console_handler)
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers
        )
        logger = logging.getLogger(__name__)
        def log_and_flush(level, msg, *args, **kwargs):
            # If you want to guarantee that a log line is on disk (or shown in the console) before the next line runs,
            # even if the program crashes, you can explicitly flush the handler(s) right after the log call.
            # Example Usage:
            #     log_and_flush(logging.INFO, "About to process file: %s", file_path)
            #
            logger.log(level, msg, *args, **kwargs)
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass  # Ignore handlers that don't support flush
    """
    # --- Config / Whitelists ---
    SIMPLE_TYPES = (str, int, float, bool)
    SAFE_BUILTINS = {"abs": abs, "round": round, "min": min, "max": max}
    SAFE_MODULES = {"math": math}

    # Global defaults and dep-graph cache (per process)
    _DEFAULTS_SNAPSHOT: dict[str, object] | None = None
    _DEP_CACHE: dict[str, tuple[dict[str, "DebugGlobalEditor_class._DepInfo"], dict[str, set[str]]]] = {}

    class _DepVisitor(ast.NodeVisitor):
        """Collect names and determine if expression is eligible for safe recompute."""
        def __init__(self, safe_builtins: set[str], safe_modules: set[str]):
            self.names: set[str] = set()
            self.eligible: bool = True
            self.reason: str | None = None
            self._safe_builtins = safe_builtins
            self._safe_modules = safe_modules

        def visit_Name(self, node: ast.Name):
            # NEW: debug log each identifier discovered
            try:
                log_and_flush(logging.DEBUG, "DepVisitor: saw name '%s'", node.id)
            except Exception:
                pass
            self.names.add(node.id)

        def visit_Call(self, node: ast.Call):
            # Allow calls to math.* or whitelisted builtins
            ok = False
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id in self._safe_modules:
                    ok = True
            elif isinstance(node.func, ast.Name):
                if node.func.id in self._safe_builtins:
                    ok = True
            if not ok:
                self.eligible = False
                self.reason = "contains non-whitelisted function call"
                return
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute):
            # Only allow attribute access on whitelisted modules
            if isinstance(node.value, ast.Name):
                if node.value.id not in self._safe_modules:
                    self.eligible = False
                    self.reason = "attribute access on non-whitelisted object"
                    return
            self.generic_visit(node)

        def visit_Import(self, node):  # pragma: no cover
            self.eligible = False
            self.reason = "import not allowed"

        def visit_ImportFrom(self, node):  # pragma: no cover
            self.eligible = False
            self.reason = "import not allowed"

        def visit_Lambda(self, node):  # pragma: no cover
            self.eligible = False
            self.reason = "lambda not allowed"

        def visit_Await(self, node):  # pragma: no cover
            self.eligible = False
            self.reason = "await not allowed"

    class _DepInfo:
        __slots__ = ("expr_str", "depends_on", "eligible", "reason", "rhs_ast")
        def __init__(self, expr_str: str | None, depends_on: set[str], eligible: bool, reason: str | None, rhs_ast: ast.AST):
            self.expr_str = expr_str
            self.depends_on = depends_on
            self.eligible = eligible
            self.reason = reason
            self.rhs_ast = rhs_ast

    def __init__(self, root: tk.Misc, module: ModuleType | None = None, *,
                 title: str = "Debug Globals",
                 column_widths: tuple[int, int, int, int, int] | None = None,
                 min_size: tuple[int, int] = (1000, 600),
                 allow_recompute: bool = True,
                 locale_floats: bool = True,
                 on_apply = None,
                 force_main: bool = True,
                 abort_on_missing_source: bool = True):
        """
        Changes in this artifact:
          • "Recompute Derived" defaults to CHECKED at startup.
          • (No other behavior changed here.)
        """
        if not __debug__:
            log_and_flush("DebugGlobalEditor_class is debug-only and requires __debug__ == True.")
            raise RuntimeError("DebugGlobalEditor_class is debug-only and requires __debug__ == True.")

        log_and_flush(logging.DEBUG, f"Entered DebugGlobalEditor_class, __init__")

        self.root = root
        self.abort_on_missing_source = abort_on_missing_source
    
        if force_main:
            main_mod = sys.modules.get("__main__")
            if not isinstance(main_mod, ModuleType):
                raise RuntimeError("No __main__ module found; cannot target main program.")
            self.module = main_mod
        else:
            self.module = module or self._get_caller_module()
            if self.module is None:
                raise RuntimeError("Unable to resolve caller module.")
    
        self.title = title
        self.column_widths = column_widths or (300, 80, 300, 90, 90)
        self.min_size = min_size
        self.allow_recompute = allow_recompute
        self.locale_floats = locale_floats
        self.on_apply = on_apply
    
        # UI state
        self._win: tk.Toplevel | None = None
        self._rows: list[dict] = []
        self._apply_btn: ttk.Button | None = None
        # DEFAULT CHANGED: start checked
        self._recompute_var = tk.BooleanVar(value=True) if allow_recompute else None
        self._message_var = tk.StringVar(value="")
    
        # Inspector state removed (no inspector pane)
        self._inspected_name: str | None = None
    
        if DebugGlobalEditor_class._DEFAULTS_SNAPSHOT is None:
            DebugGlobalEditor_class._DEFAULTS_SNAPSHOT = self._current_simple_globals_snapshot()
    
        self._module_key = self._stable_module_key(self.module)


    @staticmethod
    def _stable_module_key(mod: ModuleType) -> str:
        """
        Return a stable, process-local key for caching analysis of `mod`.
        Prefers a real file path; otherwise falls back to import metadata/name.
        """
        path = getattr(mod, "__file__", None)
        if path:
            try:
                return os.path.realpath(path)
            except Exception:
                return path
    
        spec = getattr(mod, "__spec__", None)
        spec_name = getattr(spec, "name", None) if spec else None
        if spec_name:
            return spec_name
    
        name = getattr(mod, "__name__", None)
        if name:
            return name
    
        # Last resort: stable within the process lifetime
        return f"<module@{id(mod)}>"

    # ---------------- Public API ----------------

    def open(self) -> dict:
        """Open the modal dialog and return {'applied': bool, 'changes': {...}}"""
        self._create_window()
        self._win.wait_window()
        return getattr(self, "_result", {"applied": False})

    # ---------------- Helpers ----------------

    @staticmethod
    def _get_caller_module() -> ModuleType | None:
        for frameinfo in inspect.stack():
            mod = inspect.getmodule(frameinfo.frame)
            if mod and mod is not sys.modules[__name__]:
                return mod
        return sys.modules.get("__main__", None)

    def _current_simple_globals_snapshot(self) -> dict[str, object]:
        out = {}
        for name, val in self.module.__dict__.items():
            if name.startswith("_"):
                continue
            if isinstance(val, self.SIMPLE_TYPES):
                out[name] = val
        return out

    @staticmethod
    def _unparse(node: ast.AST) -> str | None:
        try:
            return ast.unparse(node)
        except Exception:
            return None

    @classmethod
    def _top_level_assignments(cls, tree: ast.AST) -> list[tuple[str, ast.AST]]:
        """Return list of (name, rhs_expr_ast) for top-level Assign/AnnAssign simple targets only."""
        out: list[tuple[str, ast.AST]] = []
        if not isinstance(tree, ast.Module):
            return out
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                out.append((node.targets[0].id, node.value))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    out.append((node.target.id, node.value))
        # NEW: one-line summary of the discovered assignments
        try:
            summary = ", ".join(f"{name}:{type(rhs).__name__}" for name, rhs in out[:50])
            more = f" (+{len(out)-50} more)" if len(out) > 50 else ""
            log_and_flush(logging.DEBUG, "Top-level assigns: %s%s", summary, more)
        except Exception:
            pass
        return out

    @classmethod
    def _topo_sort(cls, deps: dict[str, set[str]]) -> list[str]:
        """deps: name -> set of names it depends on; return order with deps first."""
        visited: dict[str, int] = {}
        order: list[str] = []

        def visit(n: str):
            state = visited.get(n, 0)
            if state == 1:
                return  # cycle ignored
            if state == 2:
                return
            visited[n] = 1
            for m in deps.get(n, ()):
                visit(m)
            visited[n] = 2
            order.append(n)

        for k in deps:
            visit(k)
        return order

    def _build_dep_graph(self):
        """
        Build and cache the dependency graph of simple top-level assignments
        in the chosen target module (default: __main__).
    
        Logging/Abort behavior for file-less contexts (e.g., REPL, PyInstaller):
            - If __file__ is missing and source cannot be retrieved via inspect,
              we log a warning with diagnostic details.
            - If self.abort_on_missing_source is True, raise RuntimeError to
              stop the editor (useful in debug/packaging). Otherwise, we cache
              an empty graph, which disables AST-driven recompute.
        """
        log_and_flush(logging.DEBUG, f"Entered DebugGlobalEditor_class, _build_dep_graph")

        cached = DebugGlobalEditor_class._DEP_CACHE.get(self._module_key)
        if cached:
            log_and_flush(logging.DEBUG, "Dep-graph cache hit for %s", self._module_key)
            return cached
    
        info_by_name: dict[str, DebugGlobalEditor_class._DepInfo] = {}
        deps: dict[str, set[str]] = {}
    
        target_mod = self.module  # __main__ when force_main=True
        filename = getattr(target_mod, "__file__", None)
        source = None
    
        try:
            if filename:
                log_and_flush(logging.DEBUG, "Reading module source from file: %s", filename)
                with open(filename, "r", encoding="utf-8") as f:
                    source = f.read()
            else:
                log_and_flush(logging.CRITICAL, "__file__ missing for %s; trying inspect.getsource()", getattr(target_mod, "__name__", target_mod))
                source = inspect.getsource(target_mod)
                filename = getattr(target_mod, "__name__", "<module>")
        except Exception as e:
            log_and_flush(logging.CRITICAL, "Unable to obtain source for %s (key=%s). err=%r",
                           getattr(target_mod, "__name__", target_mod), self._module_key, e)
            source = None
    
        if not source:
            # Provide rich diagnostics about why we couldn't get source
            spec = getattr(target_mod, "__spec__", None)
            loader = getattr(spec, "loader", None) if spec else None
            log_and_flush(logging.CRITICAL, 
                "No readable source for module '%s'. __file__=%r, spec=%r, loader=%r. "
                "AST recompute will be disabled.",
                getattr(target_mod, "__name__", target_mod), filename, spec, loader
            )
            if self.abort_on_missing_source:
                raise RuntimeError("DebugGlobalEditor: no readable source for target module; aborting per configuration.")
            DebugGlobalEditor_class._DEP_CACHE[self._module_key] = (info_by_name, deps)
            return info_by_name, deps
    
        # Parse & collect top-level assignment dependencies
        try:
            tree = ast.parse(source, filename=filename)
            for tgt, rhs in self._top_level_assignments(tree):
                visitor = self._DepVisitor(set(self.SAFE_BUILTINS.keys()), set(self.SAFE_MODULES.keys()))
                visitor.visit(rhs)
                expr_str = self._unparse(rhs)
                info_by_name[tgt] = self._DepInfo(expr_str, set(visitor.names), visitor.eligible, visitor.reason, rhs)
                deps.setdefault(tgt, set()).update(info_by_name[tgt].depends_on)
            log_and_flush(logging.DEBUG, "Built dep-graph with %d nodes for %s", len(info_by_name), self._module_key)
        except Exception as e:
            log_and_flush(logging.CRITICAL, "AST parse failed for %s (key=%s). err=%r. Recompute disabled.",
                           filename, self._module_key, e)
            if self.abort_on_missing_source:
                raise RuntimeError("AST parse failed for %s (key=%s). err=%r. Recompute disabled.",
                           filename, self._module_key, e)
    
        DebugGlobalEditor_class._DEP_CACHE[self._module_key] = (info_by_name, deps)

        log_and_flush(logging.DEBUG, f"Exiting DebugGlobalEditor_class, _build_dep_graph at end of def with info_by_name=\n{info_by_name}\ndeps=\n{deps}")
        return info_by_name, deps

    # ---------------- UI Build ----------------

    def _create_window(self):
        win = tk.Toplevel(self.root)
        win.title(self.title)
        self._win = win
    
        # Style for grey computed checkbuttons; entries use foreground
        style = ttk.Style(win)
        style.configure("Computed.TCheckbutton", foreground="gray50")
    
        # ~90% width x 93% height
        try:
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            width = max(self.min_size[0], int(sw * 0.90))
            height = max(self.min_size[1], int(sh * 0.93))
            win.geometry(f"{width}x{height}")
        except Exception:
            pass
        win.minsize(*self.min_size)
        win.transient(self.root)
        win.grab_set()
    
        top = ttk.Frame(win); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text=self.title, font=("TkDefaultFont", 11, "bold")).pack(side="left")
        if self.allow_recompute:
            self._recompute_var.set(True)  # ensure checked by default
            ttk.Checkbutton(top, text="Recompute Derived", variable=self._recompute_var).pack(side="right")
        ttk.Label(win, textvariable=self._message_var, foreground="red").pack(fill="x", padx=8)
    
        # Scrollable grid
        container = ttk.Frame(win); container.pack(fill="both", expand=True, padx=8, pady=6)
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")
    
        # Columns (Expr/Depends are 50% wider)
        headers = ["Name", "Type", "Value", "Changed", "Apply?", "Expr", "Depends"]
        col_widths = [300, 80, 300, 90, 90, 540, 390]
        for i, h in enumerate(headers):
            ttk.Label(body, text=h, font=("TkDefaultFont", 9, "bold")).grid(
                row=0, column=i, sticky="w", padx=4, pady=(0, 4)
            )
            body.grid_columnconfigure(i, minsize=col_widths[i])
    
        # Build dep-graph once for the grid
        try:
            info_by_name, _deps = self._build_dep_graph()
        except Exception as e:
            info_by_name = {}
            self._message_var.set(str(e))
    
        # Rows
        snapshot = self._current_simple_globals_snapshot()
        row_idx = 1
        for name, val in self.module.__dict__.items():
            if name not in snapshot:
                continue
            vtype = type(val)
    
            info = info_by_name.get(name)
            expr_text = info.expr_str if (info and info.expr_str) else ""
            deps_text = ", ".join(sorted(info.depends_on)) if (info and info.depends_on) else ""
            #log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _create_window: calling        _is_computed: for name='{name}' '{vtype}' val='{val}' expr_text='{expr_text}' deps_text='{deps_text}'")
            is_computed = self._is_computed(info)
            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _create_window: returned from  _is_computed: for name='{name}' '{vtype}' val='{val}' expr_text='{expr_text}' deps_text='{deps_text}' with is_computed='{is_computed}'")
    
            rec = {
                "name": name,
                "type": vtype,
                "orig": val,
                "candidate": tk.StringVar(value=self._fmt(val, vtype)),
                "boolvar": tk.BooleanVar(value=bool(val)) if vtype is bool else None,
                "changed": tk.BooleanVar(value=False),
                "apply": tk.BooleanVar(value=False),
                "apply_overridden": False,
                "valid": True,
                "widgets": {},
            }
    
            # Name
            w_name = ttk.Label(body, text=name)
            w_name.grid(row=row_idx, column=0, sticky="w", padx=4, pady=2)
            rec["widgets"]["name"] = w_name
    
            # Type
            w_type = ttk.Label(body, text=vtype.__name__)
            w_type.grid(row=row_idx, column=1, sticky="w", padx=4, pady=2)
            rec["widgets"]["type"] = w_type
    
            # Value (READ-ONLY & grey only for computed globals)
            if vtype is bool:
                w_val = ttk.Checkbutton(body, variable=rec["boolvar"],
                                        command=lambda nm=name: self._on_value_changed(nm))
                if is_computed:
                    w_val.state(["disabled"])
                    w_val.configure(style="Computed.TCheckbutton")
                w_val.grid(row=row_idx, column=2, sticky="w", padx=4, pady=2)
            else:
                w_val = ttk.Entry(body, textvariable=rec["candidate"])
                if is_computed:
                    w_val.state(["readonly"])
                    try:
                        w_val.configure(foreground="gray50")
                    except Exception:
                        pass
                else:
                    w_val.bind("<KeyRelease>", lambda e, nm=name: self._on_value_changed(nm))
                    w_val.bind("<FocusOut>", lambda e, nm=name: self._on_value_changed(nm))
                w_val.grid(row=row_idx, column=2, sticky="ew", padx=4, pady=2)
            rec["widgets"]["value"] = w_val
    
            # Changed (read-only)
            w_changed = ttk.Checkbutton(body, variable=rec["changed"])
            w_changed.state(["disabled"])
            w_changed.grid(row=row_idx, column=3, sticky="w", padx=4, pady=2)
            rec["widgets"]["changed"] = w_changed
    
            # Apply?
            w_apply = ttk.Checkbutton(body, variable=rec["apply"], command=lambda nm=name: self._on_apply_toggled(nm))
            w_apply.grid(row=row_idx, column=4, sticky="w", padx=4, pady=2)
            rec["widgets"]["apply"] = w_apply
    
            # Expr (always readonly; grey)
            w_expr = ttk.Entry(body)
            w_expr.insert(0, expr_text)
            w_expr.state(["readonly"])
            try:
                w_expr.configure(foreground="gray50")
            except Exception:
                pass
            w_expr.grid(row=row_idx, column=5, sticky="ew", padx=4, pady=2)
    
            # Depends (always readonly; grey)
            w_deps = ttk.Entry(body)
            w_deps.insert(0, deps_text)
            w_deps.state(["readonly"])
            try:
                w_deps.configure(foreground="gray50")
            except Exception:
                pass
            w_deps.grid(row=row_idx, column=6, sticky="ew", padx=4, pady=2)
    
            self._rows.append(rec)
            row_idx += 1
    
        # Bottom bar (inspector removed)
        bottom = ttk.Frame(win); bottom.pack(fill="x", padx=8, pady=8)
        self._apply_btn = ttk.Button(bottom, text="Apply", command=self._on_apply); self._apply_btn.pack(side="right", padx=(6, 0))
        ttk.Button(bottom, text="Quit", command=self._on_quit).pack(side="right", padx=(6, 0))
        ttk.Button(bottom, text="Revert to Defaults", command=self._on_revert_defaults).pack(side="left", padx=(0, 6))
        ttk.Button(bottom, text="Save JSON", command=self._on_save_json).pack(side="left", padx=(0, 6))
        ttk.Button(bottom, text="Load JSON", command=self._on_load_json).pack(side="left", padx=(0, 6))
    
        if self._rows:
            self._select_row(self._rows[0]["name"])
    
        self._refresh_apply_enabled()

    def _is_computed(self, info) -> bool:
        """
        Return True if the variable should be treated as 'computed' (read-only in UI).
    
        Heuristic:
          • If it depends on any other names, it is computed.
          • Otherwise, if the RHS AST contains operations/calls/attribute access,
            treat it as computed even if it has no Name dependencies.
          • Pure literals (ast.Constant) are NOT computed.
    
        Examples treated as computed (locked):
          - int(1.0)                  -> Call
          - "string".lower()          -> Attribute + Call
          - (1.0 * 0.95)              -> BinOp
          - f"{1+2}"                  -> JoinedStr / FormattedValue
          - (A + 1)                   -> depends_on -> True
    
        Examples treated as NOT computed (editable):
          - 10, 3.14, "hello", True   -> Constant
        """
        if not info:
            #log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _is_computed: 'info' caught by 'if not info' so returning False")
            return False
    
        # Any dependency on names makes it computed
        if getattr(info, "depends_on", None):
            #log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _is_computed: 'info' 'depends_on' so returning True")
            return True
    
        node = getattr(info, "rhs_ast", None)
        if node is None:
            #log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _is_computed: 'info' 'rhs_ast' None so returning False")
            return False
    
        # Pure literal is not computed
        if isinstance(node, ast.Constant):
            #log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _is_computed: 'info' 'ast.Constant' so returning False")
            return False
    
        # Any of these shapes means "computed" even with no names
        computed_node_types = (
            ast.Call, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
            ast.Attribute, ast.Subscript, ast.JoinedStr, ast.FormattedValue,
        )
        if isinstance(node, computed_node_types):
            #log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _is_computed: 'info' is instance of 'computed_node_types' so returning True")
            return True
    
        # Names would have been caught by depends_on; other rare node types—err on the safe side.
        #log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _is_computed: 'info' not caught by prior if-tests so finally returning False")
        return False

    # ---------------- Value handling ----------------

    def _fmt(self, val, vtype: type) -> str:
        if vtype is float and self.locale_floats:
            try:
                return locale.format_string("%f", val, grouping=False).rstrip("0").rstrip(".")
            except Exception:
                return str(val)
        return str(val)

    def _parse(self, s: str, vtype: type):
        s2 = s.strip()
        if vtype is int:
            return int(s2, 10)
        if vtype is float:
            if self.locale_floats:
                dec = locale.localeconv().get("decimal_point") or "."
                if dec != ".":
                    s2 = s2.replace(dec, ".")
            ts = locale.localeconv().get("thousands_sep") or ","
            if ts in s2:
                raise ValueError("Thousands separators not supported")
            return float(s2)
        if vtype is str:
            return s
        if vtype is bool:
            return bool(s)
        raise TypeError("Unsupported type")

    # ---------------- Events ----------------

    def _on_value_changed(self, name: str):
        row = next((r for r in self._rows if r["name"] == name), None)
        if not row:
            return
        vtype = row["type"]
        valid = True
        try:
            new_val = row["boolvar"].get() if vtype is bool else self._parse(row["candidate"].get(), vtype)
        except Exception:
            new_val, valid = None, False

        row["valid"] = valid
        if valid:
            changed = (new_val != row["orig"])
            row["changed"].set(changed)
            if not row["apply_overridden"]:
                row["apply"].set(changed)
        else:
            row["changed"].set(False)
            if not row["apply_overridden"]:
                row["apply"].set(False)

        self._refresh_apply_enabled()

    def _on_apply_toggled(self, name: str):
        row = next((r for r in self._rows if r["name"] == name), None)
        if row:
            row["apply_overridden"] = True
            self._refresh_apply_enabled()

    def _on_quit(self):
        log_and_flush(logging.DEBUG, f"Entered DebugGlobalEditor_class, _on_quit")
        self._result = {"applied": False}
        log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: validly destroying self with applied:False ...")
        self._win.destroy()

    def _on_apply(self):
        log_and_flush(logging.DEBUG, f"Entered DebugGlobalEditor_class, _on_apply")

        # Validate all rows
        log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Validating all rows")
        for row in self._rows:
            if not row["valid"]:
                messagebox.showerror("Invalid value", f"Invalid value for {row['name']} ({row['type'].__name__})")
                return

        # Apply base changes
        log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Applying base changes")
        changes = {}
        for row in self._rows:
            if not row["apply"].get():
                continue
            name, vtype = row["name"], row["type"]
            new_val = row["boolvar"].get() if vtype is bool else self._parse(row["candidate"].get(), vtype)
            old_val = row["orig"]
            if new_val != old_val:
                setattr(self.module, name, new_val)
                row["orig"] = new_val
                changes[name] = {"old": old_val, "new": new_val}

        # Optional recompute
        recompute_report = []
        if self.allow_recompute and self._recompute_var.get():
            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: performing Optional recompute")
            info_by_name, deps = self._build_dep_graph()
            if info_by_name:
                reverse = {}
                for tgt, dep_set in deps.items():
                    for dep in dep_set:
                        reverse.setdefault(dep, set()).add(tgt)

                changed_roots = set(changes.keys())
                affected = set()
                stack = list(changed_roots)
                while stack:
                    n = stack.pop()
                    for m in reverse.get(n, ()):
                        if m not in affected:
                            affected.add(m); stack.append(m)

                if affected:
                    safe_globals = {n: v for n, v in self.module.__dict__.items() if isinstance(v, self.SIMPLE_TYPES)}
                    for k, m in self.SAFE_MODULES.items():
                        safe_globals[k] = m
                    safe_globals["__builtins__"] = self.SAFE_BUILTINS

                    order = self._topo_sort({n: info_by_name.get(n, self._DepInfo(None, set(), False, None, ast.Constant(None))).depends_on for n in affected})
                    for name in order:
                        if name in changes:  # Skip variables that were directly changed by user
                            continue
                        info = info_by_name.get(name)
                        if not info or not info.eligible:
                            continue
                        try:
                            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: name='{name}' about to get code using 'compile' ...")
                            #
                            # This (original) line fails because mode="eval" requires the AST to be wrapped in an ast.Expression node:
                            #     code = compile(info.rhs_ast, filename="<ast>", mode="eval")
                            # Technically the fix is to Wrap in ast.Expression:
                            #     expr_wrapper = ast.Expression(body=info.rhs_ast)
                            #     code = compile(expr_wrapper, filename="<ast>", mode="eval")
                            # This approach below might be safer since this class is already working with the string representation elsewhere in the code
                            code = compile(info.expr_str, filename="<ast>", mode="eval")
                            #
                            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: name='{name}' using info.expr_str='{info.expr_str}' as input to 'compile'")
                            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: name='{name}' about to get new_val using 'eval' ...")
                            new_val = eval(code, safe_globals, {})
                            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: name='{name}' info.expr_str='{info.expr_str}' new_val='{new_val}' using 'eval'")
                            if name in self.module.__dict__:
                                old_val = getattr(self.module, name)
                                log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: name='{name}' is in 'self.module.__dict__' and old_val=getattr(self.module, name)='{old_val}'")
                                # type compatibility check (keep simple)
                                if type(old_val) in self.SIMPLE_TYPES and isinstance(new_val, type(old_val)):
                                    log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: name='{name}' new_val='{new_val}', calling setattr(self.module, name, new_val)")
                                    setattr(self.module, name, new_val)
                                    safe_globals[name] = new_val
                                    if name not in changes or changes[name]["new"] != new_val:
                                        changes[name] = {"old": old_val, "new": new_val}
                                        log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: changes[{name}]: old_val='{old_val}' new_val='{new_val}'")
                                    else:
                                        log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: SKIPPED changes[{name}]")
                                else:
                                    recompute_report.append(f"{name}: type mismatch; SKIPPED")
                                    log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute: {name}: type mismatch; SKIPPED")
                        except Exception as ex:
                            recompute_report.append(f"{name}: {ex!r}")
                            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Optional recompute Exception: {name}: {ex!r}")

        if changes and self.on_apply:
            try: 
                log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: about to self.on_apply(changes) where changes={changes}")
                self.on_apply(changes)
            except Exception: 
                log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Exception on self.on_apply(changes) where changes={changes}")
                log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Exception {ex!r}")

        self.last_changes = changes
        try: 
            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: about to self.root.event_generate(...)")
            self.root.event_generate("<<DebugGlobalsApplied>>", when="tail")
        except Exception: 
            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Exception on self.root.event_generate(...)")
            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Exception {ex!r}")

        if recompute_report:
            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: recompute_report:\n{recompute_report}")
            self._message_var.set("; ".join(recompute_report))
        else:
            log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: Applied.")
            self._message_var.set("Applied.")

        self._result = {"applied": True, "changes": changes}
        log_and_flush(logging.DEBUG, f"DebugGlobalEditor_class, _on_apply: validly destroying self with applied:True changes:{changes} ...")
        self._win.destroy()

    def _on_revert_defaults(self):
        defaults = DebugGlobalEditor_class._DEFAULTS_SNAPSHOT or {}
        for row in self._rows:
            name, vtype = row["name"], row["type"]
            if name in defaults:
                val = defaults[name]
                if vtype is bool:
                    row["boolvar"].set(bool(val))
                else:
                    row["candidate"].set(self._fmt(val, vtype))
                row["apply_overridden"] = False
                self._on_value_changed(name)
        self._message_var.set("Reverted to defaults (candidate values).")

    def _on_save_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
    
        # Build dep info so we can skip computed variables
        try:
            info_by_name, _ = self._build_dep_graph()
        except Exception:
            info_by_name = {}
    
        data = {}
        for row in self._rows:
            name, vtype = row["name"], row["type"]
            info = info_by_name.get(name)
            is_computed = bool(info and info.depends_on)
            if is_computed:
                continue  # skip computed values
    
            if vtype is bool:
                data[name] = bool(row["boolvar"].get())
            else:
                try:
                    data[name] = self._parse(row["candidate"].get(), vtype)
                except Exception:
                    pass
    
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._message_var.set(f"Saved to {path}")
        except Exception as ex:
            messagebox.showerror("Save JSON failed", str(ex))

    def _on_load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All Files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as ex:
            messagebox.showerror("Load JSON failed", str(ex))
            return
    
        # Build dep info so we can skip computed variables
        try:
            info_by_name, _ = self._build_dep_graph()
        except Exception:
            info_by_name = {}
    
        for row in self._rows:
            name, vtype = row["name"], row["type"]
            if name not in data:
                continue
    
            info = info_by_name.get(name)
            is_computed = bool(info and info.depends_on)
            if is_computed:
                continue  # never load into computed variables
    
            val = data[name]
            # simple type check
            if vtype is bool:
                row["boolvar"].set(bool(val))
            elif vtype is int and isinstance(val, int):
                row["candidate"].set(str(val))
            elif vtype is float and isinstance(val, (int, float)):
                row["candidate"].set(self._fmt(float(val), float))
            elif vtype is str and isinstance(val, str):
                row["candidate"].set(val)
            else:
                continue
    
            row["apply_overridden"] = False
            self._on_value_changed(name)
    
        self._message_var.set(f"Loaded from {path}")

    # ---------------- Inspector ----------------

    def _select_row(self, name: str | None):
        """Select a row in the grid. No inspector updates (inspector removed)."""
        self._inspected_name = name
        # If you had visual highlight logic, keep it; otherwise, no-op is fine.
        # Example (optional): ensure Apply button state recalculates for UX.
        self._refresh_apply_enabled()

    # ---------------- Misc ----------------

    def _refresh_apply_enabled(self):
        if not self._apply_btn: return
        ok = all(r["valid"] for r in self._rows)
        self._apply_btn.state(["!disabled"] if ok else ["disabled"])
