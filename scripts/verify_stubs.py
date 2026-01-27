#!/usr/bin/env python3
"""Verify that manual stubs include all types from generated stubs.

This script:
1. Runs pyo3-stub-gen to generate stubs from Rust code
2. Extracts class and function names from the generated stubs
3. Compares against the manual stubs in stubs/stoat_ferret_core/
4. Reports any types defined in Rust but missing from manual stubs

This is a "drift detector" - it catches when new Rust types are added
but the manual stubs aren't updated to match.

Usage:
    python scripts/verify_stubs.py

Exit codes:
    0 - All types accounted for
    1 - Missing types detected
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run_stub_gen(project_root: Path) -> bool:
    """Run cargo stub_gen to generate stubs.

    Temporarily modifies pyproject.toml to output stubs to .generated-stubs/,
    runs stub_gen, then restores the original pyproject.toml.
    """
    pyproject = project_root / "pyproject.toml"
    pyproject_bak = project_root / "pyproject.toml.bak"

    # Read and backup original pyproject.toml
    original_content = pyproject.read_text(encoding="utf-8")
    shutil.copy(pyproject, pyproject_bak)

    try:
        # Modify pyproject.toml to output stubs to .generated-stubs/
        modified_content = original_content.replace(
            'python-source = "src"', 'python-source = ".generated-stubs"'
        )
        pyproject.write_text(modified_content, encoding="utf-8")

        # Run stub_gen
        rust_dir = project_root / "rust" / "stoat_ferret_core"
        result = subprocess.run(
            ["cargo", "run", "--bin", "stub_gen"],
            cwd=rust_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: stub_gen failed:\n{result.stderr}", file=sys.stderr)
            return False
        return True
    finally:
        # Restore original pyproject.toml
        shutil.move(pyproject_bak, pyproject)


def extract_names_from_stub(stub_path: Path) -> tuple[set[str], set[str]]:
    """Extract class and function names from a .pyi file.

    Returns:
        Tuple of (class_names, function_names)
    """
    classes: set[str] = set()
    functions: set[str] = set()

    if not stub_path.exists():
        return classes, functions

    content = stub_path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(content, type_comments=True)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
            elif isinstance(node, ast.FunctionDef):
                # Only top-level functions, not methods
                if isinstance(node, ast.FunctionDef):
                    functions.add(node.name)
    except SyntaxError:
        # Fallback to regex if AST parsing fails
        classes = set(re.findall(r"^class\s+(\w+)", content, re.MULTILINE))
        functions = set(re.findall(r"^def\s+(\w+)", content, re.MULTILINE))

    return classes, functions


def main() -> int:
    """Main entry point."""
    project_root = Path(__file__).parent.parent

    # Create .generated-stubs directory if it doesn't exist
    generated_stubs_dir = project_root / ".generated-stubs" / "stoat_ferret_core"
    generated_stubs_dir.mkdir(parents=True, exist_ok=True)

    # Run stub_gen
    print("Running stub_gen to generate stubs from Rust...")
    if not run_stub_gen(project_root):
        return 1

    # Paths
    generated_stub = project_root / ".generated-stubs" / "stoat_ferret_core" / "_core.pyi"
    manual_stub = project_root / "stubs" / "stoat_ferret_core" / "_core.pyi"

    if not generated_stub.exists():
        print(f"ERROR: Generated stub not found at {generated_stub}", file=sys.stderr)
        return 1

    if not manual_stub.exists():
        print(f"ERROR: Manual stub not found at {manual_stub}", file=sys.stderr)
        return 1

    # Extract names
    gen_classes, gen_functions = extract_names_from_stub(generated_stub)
    man_classes, man_functions = extract_names_from_stub(manual_stub)

    # Compare
    missing_classes = gen_classes - man_classes
    missing_functions = gen_functions - man_functions

    # Report
    has_errors = False

    if missing_classes:
        print("\nERROR: Classes in Rust but missing from manual stubs:")
        for cls in sorted(missing_classes):
            print(f"  - {cls}")
        has_errors = True

    if missing_functions:
        print("\nERROR: Functions in Rust but missing from manual stubs:")
        for func in sorted(missing_functions):
            print(f"  - {func}")
        has_errors = True

    if has_errors:
        print("\nPlease update stubs/stoat_ferret_core/_core.pyi to include these types.")
        return 1

    print("OK: All generated types are present in manual stubs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
