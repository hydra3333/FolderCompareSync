#!/usr/bin/env python3
"""
Needs:    pip install libcst

Refactor bare references to constants into C.NAME while preserving comments/formatting.

Features
- Gathers constant names from FolderCompareSync_Global_Constants (via __all__ or UPPERCASE names)
- Rewrites:
    * Loads:  FOO           -> C.FOO
    * Stores: FOO = 1       -> C.FOO = 1
             x += FOO       -> x += C.FOO
             del FOO        -> del C.FOO
- Renames function parameters that match constants:
    def f(FOO): ...   ->   def f(FOO_param): ...  (and updates uses inside the function)
- Injects:  import FolderCompareSync_Global_Constants as C   (after any __future__ imports)
- Skips the constants module itself
- Writes outputs alongside inputs with `_refactored.py` suffix by default.

Usage
- Edit PY_FILES below, or adapt to parse args/globs as desired.
- Python 3.9+; install libcst with:  pip install libcst
"""

from __future__ import annotations
import importlib
import os
import sys
from typing import Iterable, Optional, Set, Dict, List

import libcst as cst
import libcst.matchers as m
from libcst.metadata import ParentNodeProvider, MetadataWrapper

# ------------------- CONFIG -------------------

PY_FILES = [
    "FolderCompareSync_class.py",
    "FileCopyManager_class.py",
    "DeleteOrphansManager_class.py",
    "DebugGlobalEditor_class.py",
    "ProgressDialog_class.py",
    "FileTimestampManager_class.py",
    "flushed_logging.py",
    "FolderCompareSync.py",
    # add more as needed...
]

CONSTANTS_MODULE = "FolderCompareSync_Global_Constants"
IMPORT_ALIAS = "C"

OUTPUT_DIR: Optional[str] = None   # e.g. "refactored_out"; None => same dir
SUFFIX = "_refactored"             # appended before .py when OUTPUT_DIR is None
OVERWRITE = False                  # True => overwrite inputs (start with False!)

# Parameter rename policy if arg matches a constant
def renamed_param(name: str) -> str:
    return f"{name}_param"


# ----------------- constants discovery -----------------

def gather_constants(module_name: str) -> Set[str]:
    mod = importlib.import_module(module_name)
    if getattr(mod, "__all__", None):
        names = [n for n in mod.__all__ if isinstance(n, str)]
    else:
        names = [n for n in dir(mod) if n.isupper() and not n.startswith("_")]
    return set(names)

# ----------------- CST helpers -----------------

def make_C_attr(name: str) -> cst.Attribute:
    return cst.Attribute(value=cst.Name(IMPORT_ALIAS), attr=cst.Name(name))

def ensure_import_c(mod: cst.Module) -> cst.Module:
    """
    Ensure `import FolderCompareSync_Global_Constants as C` exists after any __future__ imports.
    """
    # Already present?
    for stmt in mod.body:
        if m.matches(
            stmt,
            m.SimpleStatementLine(
                body=[m.Import(names=[m.ImportAlias(name=m.Name(CONSTANTS_MODULE), asname=m.AsName(name=m.Name(IMPORT_ALIAS)))])]
            ),
        ):
            return mod

    # Build import node
    import_node = cst.SimpleStatementLine(
        body=[cst.Import(names=[cst.ImportAlias(name=cst.Name(CONSTANTS_MODULE),
                                               asname=cst.AsName(name=cst.Name(IMPORT_ALIAS)))])]
    )

    # Find insertion point after __future__ imports
    idx = 0
    new_body: List[cst.CSTNode] = list(mod.body)
    for i, stmt in enumerate(new_body):
        if m.matches(stmt, m.SimpleStatementLine(body=[m.ImportFrom(module=m.Name("__future__"))])):
            idx = i + 1
        else:
            # stop at first non-__future__ line (keeps docstring/blank lines as-is)
            break

    new_body.insert(idx, import_node)
    return mod.with_changes(body=new_body)

# ----------------- Transformer -----------------

class RewriteConstants(cst.CSTTransformer):
    """
    - Rewrites bare names that match constants to C.NAME (loads)
      while skipping attribute contexts like `obj.FOO` (attr part), imports, etc.
    - Rewrites assignment/annotation/augassign/delete *targets* that match constants to C.NAME (stores).
    - Renames function parameters that match constants; updates internal uses accordingly.
    """
    METADATA_DEPENDENCIES = (ParentNodeProvider,)

    def __init__(self, constants: Set[str]):
        super().__init__()
        self.constants = constants
        self.param_stack: List[Dict[str, str]] = []  # mapping per function: old -> new

    # ---------- parameter renaming in function signatures ----------

    def _rename_param(self, p: cst.Param, current_args: List[cst.Param]) -> tuple[cst.Param, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        name = p.name.value
        if name in self.constants:
            # compute a unique replacement among current args
            base = renamed_param(name)
            new = base
            i = 0
            existing = {arg.name.value for arg in current_args if arg.name is not None}
            while new in existing:
                i += 1
                new = f"{base}_{i}"
            mapping[name] = new
            p = p.with_changes(name=cst.Name(new))
        return p, mapping

    def _rename_params_block(self, params: cst.Parameters) -> tuple[cst.Parameters, Dict[str, str]]:
        mapping_total: Dict[str, str] = {}

        # collect in order, keeping a working list to check collisions
        def process_list(lst: List[cst.Param]) -> List[cst.Param]:
            out: List[cst.Param] = []
            for p in lst:
                new_p, mapping = self._rename_param(p, out + list(lst))
                mapping_total.update(mapping)
                out.append(new_p)
            return out

        posonly = process_list(list(params.posonly_params))
        params_ = process_list(list(params.params))
        kwonly = process_list(list(params.kwonly_params))

        star_arg = params.star_arg
        if isinstance(star_arg, cst.Param) and star_arg.name.value in self.constants:
            new_p, mapping = self._rename_param(star_arg, posonly + params_ + kwonly)
            mapping_total.update(mapping)
            star_arg = new_p

        star_kwarg = params.star_kwarg
        if isinstance(star_kwarg, cst.Param) and star_kwarg.name.value in self.constants:
            new_p, mapping = self._rename_param(star_kwarg, posonly + params_ + kwonly)
            mapping_total.update(mapping)
            star_kwarg = new_p

        new_params = params.with_changes(
            posonly_params=tuple(posonly),
            params=tuple(params_),
            kwonly_params=tuple(kwonly),
            star_arg=star_arg,
            star_kwarg=star_kwarg,
        )
        return new_params, mapping_total

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        # push a new mapping scope; we'll fill it in leave_FunctionDef
        self.param_stack.append({})

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.CSTNode:
        # rename params if needed
        new_params, mapping = self._rename_params_block(updated_node.params)
        self.param_stack[-1] = mapping  # set mapping for use inside body
        # apply mapping to body Names
        body_transform = _RenameParamUses(mapping)
        new_body = [s.visit(body_transform) for s in updated_node.body.body]
        # pop scope
        self.param_stack.pop()
        return updated_node.with_changes(params=new_params, body=updated_node.body.with_changes(body=tuple(new_body)))

    def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> None:
        self.param_stack.append({})

    def leave_AsyncFunctionDef(self, original_node: cst.AsyncFunctionDef, updated_node: cst.AsyncFunctionDef) -> cst.CSTNode:
        new_params, mapping = self._rename_params_block(updated_node.params)
        self.param_stack[-1] = mapping
        body_transform = _RenameParamUses(mapping)
        new_body = [s.visit(body_transform) for s in updated_node.body.body]
        self.param_stack.pop()
        return updated_node.with_changes(params=new_params, body=updated_node.body.with_changes(body=tuple(new_body)))

    # ---------- store targets: Assign, AnnAssign, AugAssign, Del ----------

    def _transform_target_expr(self, expr: cst.BaseExpression) -> cst.BaseExpression:
        # Replace a Name target that matches constants with C.NAME; recurse into Tuple/List destructuring.
        if isinstance(expr, cst.Name) and expr.value in self.constants:
            return make_C_attr(expr.value)
        if isinstance(expr, (cst.Tuple, cst.List)):
            elts = []
            for e in expr.elements:
                if e is None or e.value is None:
                    elts.append(e)
                else:
                    elts.append(e.with_changes(value=self._transform_target_expr(e.value)))
            return expr.with_changes(elements=tuple(elts))
        return expr

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.CSTNode:
        new_targets = []
        for t in updated_node.targets:
            new_target = t.with_changes(target=self._transform_target_expr(t.target))
            new_targets.append(new_target)
        return updated_node.with_changes(targets=tuple(new_targets))

    def leave_AnnAssign(self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign) -> cst.CSTNode:
        return updated_node.with_changes(target=self._transform_target_expr(updated_node.target))

    def leave_AugAssign(self, original_node: cst.AugAssign, updated_node: cst.AugAssign) -> cst.CSTNode:
        return updated_node.with_changes(target=self._transform_target_expr(updated_node.target))

    def leave_Del(self, original_node: cst.Del, updated_node: cst.Del) -> cst.CSTNode:
        # libcst.Del has a single 'target' expression (which may itself be a Tuple/List)
        new_target = self._transform_target_expr(updated_node.target)
        return updated_node.with_changes(target=new_target)

    # ---------- loads: bare Names -> C.NAME (avoiding attributes/imports) ----------

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.CSTNode:
        name = original_node.value

        # If inside a function and this name was a renamed parameter, ignore (handled by _RenameParamUses)
        if self.param_stack and name in self.param_stack[-1]:
            return updated_node

        if name not in self.constants:
            return updated_node

        parent = self.get_metadata(ParentNodeProvider, original_node)

        # Skip parts of attributes like obj.FOO (attr side), and names already under C.FOO
        if isinstance(parent, cst.Attribute):
            if parent.attr is original_node:
                return updated_node
            if isinstance(parent.value, cst.Name) and parent.value.value == IMPORT_ALIAS:
                return updated_node

        # Skip import statements and parameter definitions
        if m.matches(parent, m.ImportFrom() | m.Import()) or isinstance(parent, cst.Param):
            return updated_node

        # Stores handled in leave_Assign/leave_AnnAssign/leave_AugAssign/leave_Del
        if isinstance(parent, (cst.AssignTarget, cst.AnnAssign, cst.AugAssign, cst.Del)):
            return updated_node

        # Default: treat as a load and rewrite to C.NAME
        return make_C_attr(name)

class _RenameParamUses(cst.CSTTransformer):
    """
    Replace references to renamed parameters inside a single function body.
    """
    def __init__(self, mapping: Dict[str, str]):
        super().__init__()
        self.mapping = mapping

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.CSTNode:
        if original_node.value in self.mapping:
            return cst.Name(self.mapping[original_node.value])
        return updated_node

# ----------------- processing -----------------

def compute_output_path(in_path: str) -> str:
    if OVERWRITE:
        return in_path
    base = os.path.basename(in_path)
    if OUTPUT_DIR:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        return os.path.join(OUTPUT_DIR, base)
    root, ext = os.path.splitext(in_path)
    return f"{root}{SUFFIX}{ext or '.py'}"

def process_files(files: Iterable[str], constants: Set[str]) -> None:
    const_mod = importlib.import_module(CONSTANTS_MODULE)
    const_path = os.path.abspath(getattr(const_mod, "__file__", "") or "")

    for path in files:
        in_abs = os.path.abspath(path)

        if not os.path.isfile(in_abs):
            print(f"WARNING: not found: {path}")
            continue

        # Skip the constants module itself
        if const_path and os.path.abspath(in_abs) == const_path:
            print(f"SKIP constants module: {path}")
            continue

        out_path = compute_output_path(in_abs)

        try:
            src = open(in_abs, "r", encoding="utf-8").read()
            module = cst.parse_module(src)
            wrapper = MetadataWrapper(module)
            transformer = RewriteConstants(constants)
            new_module = wrapper.visit(transformer)
            new_module = ensure_import_c(new_module)

            new_code = new_module.code
            if new_code != src or OVERWRITE:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(new_code)
                print(f"WROTE: {out_path}")
            else:
                print(f"UNCHANGED: {path}")
        except Exception as e:
            print(f"ERROR processing {path}: {type(e).__name__}: {e}")

def main() -> None:
    try:
        constants = gather_constants(CONSTANTS_MODULE)
    except Exception as e:
        print(f"ERROR loading {CONSTANTS_MODULE}: {type(e).__name__}: {e}")
        sys.exit(1)

    if not constants:
        print(f"ERROR: No constants discovered in {CONSTANTS_MODULE}")
        sys.exit(1)

    print(f"Refactoring {len(PY_FILES)} file(s) using {len(constants)} constants from {CONSTANTS_MODULE} …")
    process_files(PY_FILES, constants)
    print("Done.")

if __name__ == "__main__":
    main()
