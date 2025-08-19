#!/usr/bin/env python3
from __future__ import annotations
import ast
import difflib
import importlib
import os
import sys
import py_compile
from typing import Set, Tuple, Dict, List, Iterable

CONSTANTS_MODULE = "FolderCompareSync_Global_Constants"
IMPORT_ALIAS = "C"

PAIRS: List[Tuple[str, str]] = [
    ("FolderCompareSync_class.py",          "FolderCompareSync_class_refactored.py"),
    ("FileCopyManager_class.py",            "FileCopyManager_class_refactored.py"),
    ("DeleteOrphansManager_class.py",       "DeleteOrphansManager_class_refactored.py"),
    ("DebugGlobalEditor_class.py",          "DebugGlobalEditor_class_refactored.py"),
    ("ProgressDialog_class.py",             "ProgressDialog_class_refactored.py"),
    ("FileTimestampManager_class.py",       "FileTimestampManager_class_refactored.py"),
    ("flushed_logging.py",                  "flushed_logging_refactored.py"),
    ("FolderCompareSync.py",                "FolderCompareSync_refactored.py"),
]

def gather_constants(module_name: str) -> Set[str]:
    mod = importlib.import_module(module_name)
    if getattr(mod, "__all__", None):
        names = [n for n in mod.__all__ if isinstance(n, str)]
    else:
        names = [n for n in dir(mod) if n.isupper() and not n.startswith("_")]
    return set(names)

class StripConstantsImports(ast.NodeTransformer):
    """Remove any import of the constants module from a module AST."""
    def visit_Import(self, node: ast.Import):
        names = [a for a in node.names
                 if not (a.name == CONSTANTS_MODULE and (a.asname == IMPORT_ALIAS or a.asname is None))]
        if not names:
            return None
        node.names = names
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if (node.module or "") == CONSTANTS_MODULE:
            return None
        return node

class NormalizeRefactor(ast.NodeTransformer):
    """
    Turn refactored 'C.NAME' back into bare 'NAME' (only for known constants),
    and drop 'import FolderCompareSync_Global_Constants as C'.
    """
    def __init__(self, constants: Set[str]):
        self.constants = constants

    def visit_Import(self, node: ast.Import) -> ast.AST | None:
        for alias in node.names:
            if alias.name == CONSTANTS_MODULE and alias.asname == IMPORT_ALIAS:
                return None
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == IMPORT_ALIAS:
            # py3.13: attr is a str; older: Name/Attribute
            attr_name = node.attr if isinstance(node.attr, str) else (
                node.attr.id if isinstance(node.attr, ast.Name) else None
            )
            if attr_name in self.constants:
                return ast.copy_location(ast.Name(id=attr_name, ctx=node.ctx), node)
        return node

def dump(tree: ast.AST) -> str:
    return ast.dump(tree, include_attributes=False)

def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def unparse(tree: ast.AST) -> str:
    # present in 3.9+
    return ast.unparse(tree)

# ---------- diagnostics helpers ----------

def find_c_attrs(tree: ast.AST) -> List[Tuple[int, str]]:
    """Find occurrences of C.<name> and return (lineno, attrname)."""
    hits: List[Tuple[int, str]] = []
    class V(ast.NodeVisitor):
        def visit_Attribute(self, node: ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == IMPORT_ALIAS:
                attr_name = node.attr if isinstance(node.attr, str) else (
                    node.attr.id if isinstance(node.attr, ast.Name) else repr(node.attr)
                )
                hits.append((getattr(node, "lineno", -1), str(attr_name)))
            self.generic_visit(node)
    V().visit(tree)
    return hits

def import_fingerprint(tree: ast.AST) -> List[str]:
    """Return a normalized list of non-C import statements for quick comparison."""
    lines: List[str] = []
    for n in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(n, ast.Import):
            parts = [f"{a.name} as {a.asname}" if a.asname else a.name for a in n.names]
            # skip the constants C import; it's removed in normalization anyway
            if any(a.name == CONSTANTS_MODULE and a.asname == IMPORT_ALIAS for a in n.names):
                continue
            lines.append("import " + ", ".join(parts))
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            names = ", ".join(
                f"{a.name} as {a.asname}" if a.asname else a.name
                for a in n.names
            )
            lines.append(f"from {mod} import {names}")
    return lines

def diff_unparsed(old_ast: ast.AST, new_norm_ast: ast.AST, old_label: str, new_label: str, context: int = 3) -> str:
    old_code = unparse(old_ast).splitlines(keepends=True)
    new_code = unparse(new_norm_ast).splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_code, new_code, fromfile=old_label, tofile=new_label, n=context))

# ---------- main comparison ----------

def compare_pair(old_path: str, new_path: str, constants: Set[str]) -> bool:
    ok = True

    try:
        old_src = read(old_path)
        new_src = read(new_path)
    except Exception as e:
        print(f"[READ ERROR] {type(e).__name__}: {e}")
        return False

    # Parse ASTs
    try:
        old_ast = ast.parse(old_src, filename=old_path)
    except Exception as e:
        print(f"[{old_path}] AST PARSE ERROR: {e}")
        return False
    try:
        new_ast = ast.parse(new_src, filename=new_path)
    except Exception as e:
        print(f"[{new_path}] AST PARSE ERROR: {e}")
        return False

    # Byte-compile the new file
    try:
        py_compile.compile(new_path, doraise=True)
    except Exception as e:
        print(f"[{new_path}] BYTE-COMPILE ERROR: {e}")
        ok = False

    # Quick scan: how many C.* are present before normalization?
    c_hits_pre = find_c_attrs(new_ast)

    # Normalize C.NAME -> NAME; drop C import
    norm_new_ast = NormalizeRefactor(constants).visit(new_ast)
    ast.fix_missing_locations(norm_new_ast)

    # Quick scan after normalization (should be empty for known constants)
    c_hits_post = find_c_attrs(norm_new_ast)

    # Strip any form of constants import from BOTH trees before equality compare
    old_ast_stripped = StripConstantsImports().visit(old_ast)
    norm_new_ast_stripped = StripConstantsImports().visit(norm_new_ast)
    ast.fix_missing_locations(old_ast_stripped)
    ast.fix_missing_locations(norm_new_ast_stripped)

    # Compare non-C import fingerprints
    old_imps = import_fingerprint(old_ast_stripped)
    new_imps = import_fingerprint(norm_new_ast_stripped)
    imp_equal = (old_imps == new_imps)

    # Structural compare
    same = (dump(old_ast_stripped) == dump(norm_new_ast_stripped))

    if not same:
        print(f"[{old_path}] != normalized({new_path}) — unexpected diff (no param renames expected here)")
        # Show import differences
        if not imp_equal:
            print("  Import diff (normalized):")
            old_set = set(old_imps)
            new_set = set(new_imps)
            only_old = sorted(old_set - new_set)
            only_new = sorted(new_set - old_set)
            if only_old:
                print("    - ONLY IN OLD:")
                for line in only_old:
                    print("      ", line)
            if only_new:
                print("    - ONLY IN NEW:")
                for line in only_new:
                    print("      ", line)

        # Show C.* occurrences pre/post
        print(f"  C.* occurrences in {new_path}: {len(c_hits_pre)}")
        if c_hits_pre:
            sample = ", ".join([f"{attr}@{ln}" for ln, attr in c_hits_pre[:10]])
            print(f"    e.g., {sample}{' ...' if len(c_hits_pre) > 10 else ''}")
        print(f"  C.* occurrences after normalization: {len(c_hits_post)}")
        if c_hits_post:
            sample = ", ".join([f"{attr}@{ln}" for ln, attr in c_hits_post[:10]])
            print(f"    (unexpected) still present: {sample}{' ...' if len(c_hits_post) > 10 else ''}")

        # Unified diff of AST-unparsed code (semantic diff)
        #diff = diff_unparsed(old_ast, norm_new_ast, old_path, f"normalized({new_path})", context=3)
        diff = diff_unparsed(old_ast_stripped, norm_new_ast_stripped, old_path, f"normalized({new_path})", context=3)
        if diff:
            print("  Unified diff (AST-unparsed):")
            print(diff)
        else:
            print("  (No textual diff produced by unparse; ASTs still differ structurally.)")

        ok = False

    return ok

def main() -> None:
    try:
        constants = gather_constants(CONSTANTS_MODULE)
    except Exception as e:
        print(f"ERROR loading {CONSTANTS_MODULE}: {type(e).__name__}: {e}")
        sys.exit(1)

    if not constants:
        print(f"ERROR: no constants discovered in {CONSTANTS_MODULE}")
        sys.exit(1)

    print(f"Verifying {len(PAIRS)} pair(s) using {len(constants)} constants …")
    all_ok = True
    for old_path, new_path in PAIRS:
        res = compare_pair(old_path, new_path, constants)
        print(f"{'PASS' if res else 'FAIL'}: {old_path} vs {new_path}")
        all_ok &= res
    print("Result:", "ALL PASS" if all_ok else "SOME FAIL")
    sys.exit(0 if all_ok else 2)

if __name__ == "__main__":
    main()
