# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Add or check SPDX license headers in .py and .rs source files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Exclusion list — single source of truth shared by --write and --check modes.
# New entries require a documented rationale in a comment.
EXCLUDE_PATHS: set[str] = {
    "src/stoat_ferret_core/_core.pyi",  # generated PyO3 stub; not distributed as source
}

# Safety-net directory exclusions (gitignored dirs are already absent from git ls-files output).
EXCLUDE_DIRS: set[str] = {
    "target",
    ".venv",
    "node_modules",
    "build",
    "__pycache__",
}

PY_SPDX = "# SPDX-License-Identifier: AGPL-3.0-or-later"
PY_COPYRIGHT = "# Copyright (C) 2026 Grant Wickman"
PY_HEADER = f"{PY_SPDX}\n{PY_COPYRIGHT}\n"

RS_SPDX = "// SPDX-License-Identifier: AGPL-3.0-or-later"
RS_COPYRIGHT = "// Copyright (C) 2026 Grant Wickman"
RS_HEADER = f"{RS_SPDX}\n{RS_COPYRIGHT}\n"

SPDX_MARKER = "SPDX-License-Identifier:"


def _get_repo_root() -> Path:
    """Return the git repository root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Not inside a git repository")
    return Path(result.stdout.strip())


def _is_excluded(path: Path, repo_root: Path) -> bool:
    """Return True if this file should be skipped."""
    rel = path.relative_to(repo_root).as_posix()
    if rel in EXCLUDE_PATHS:
        return True
    return any(part in EXCLUDE_DIRS for part in path.parts)


def _enumerate_files(repo_root: Path) -> list[Path]:
    """Enumerate all git-tracked .py and .rs files, applying EXCLUDE_PATHS filtering."""
    result = subprocess.run(
        ["git", "ls-files", "*.py", "*.rs"],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root,
    )
    if result.returncode == 128:
        raise SystemExit("Error: not in a git repository")
    if result.returncode != 0:
        raise SystemExit(f"git ls-files failed: {result.stderr}")
    files = []
    for rel in result.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        p = repo_root / rel
        if not _is_excluded(p, repo_root):
            files.append(p)
    return files


def _header_present(lines: list[str]) -> bool:
    """Return True if SPDX marker already appears in the first 5 lines."""
    return any(SPDX_MARKER in line for line in lines[:5])


def _header_valid_py(lines: list[str]) -> bool:
    """
    Return True if the Python SPDX + copyright block is correctly placed.

    Placement rule:
      shebang (optional) → encoding cookie (optional) → SPDX → copyright → ...
    """
    idx = 0
    # Skip optional shebang
    if lines and lines[0].startswith("#!"):
        idx = 1
    # Skip optional encoding cookie
    if idx < len(lines) and lines[idx].startswith("# -*- coding"):
        idx += 1
    if idx + 1 >= len(lines):
        return False
    return lines[idx] == PY_SPDX + "\n" and lines[idx + 1] == PY_COPYRIGHT + "\n"


def _header_valid_rs(lines: list[str]) -> bool:
    """Return True if the Rust SPDX + copyright block is at the very top."""
    if len(lines) < 2:
        return False
    return lines[0] == RS_SPDX + "\n" and lines[1] == RS_COPYRIGHT + "\n"


def _insert_py_header(content: str) -> str:
    """Insert Python SPDX header at the correct position."""
    lines = content.splitlines(keepends=True)
    idx = 0
    # Keep shebang first
    if lines and lines[0].startswith("#!"):
        idx = 1
    # Keep encoding cookie next
    if idx < len(lines) and lines[idx].startswith("# -*- coding"):
        idx += 1
    header_lines = [PY_SPDX + "\n", PY_COPYRIGHT + "\n", "\n"]
    # If there's already a blank line right after position, don't double-blank
    if lines[idx:] and lines[idx] == "\n":
        header_lines = header_lines[:2]
        header_lines.append("\n")
    new_lines = lines[:idx] + header_lines + lines[idx:]
    return "".join(new_lines)


def _insert_rs_header(content: str) -> str:
    """Insert Rust SPDX header at the top of the file."""
    header = RS_HEADER + "\n"
    # Avoid double blank if content already starts with blank
    if content.startswith("\n"):
        header = RS_HEADER
    return header + content


def process_file(path: Path, check_only: bool, repo_root: Path | None = None) -> bool:
    """
    Process a single file.

    Returns True if file already has correct header (or was fixed in write mode).
    Returns False if header is missing/wrong (check mode) or file was modified (write mode).

    When `repo_root` is provided and `check_only` is False, the write is refused (raising
    `SystemExit`) if `path`'s resolved location falls outside the resolved `repo_root` — this
    closes the TOCTOU-adjacent gap where a tracked path is lexically inside `repo_root` but its
    resolved symlink target is not. `repo_root` is optional so callers that don't need the
    confinement check (e.g. tests exercising other behavior) are unaffected.
    """
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    is_py = path.suffix == ".py"

    if _header_present(lines):
        # Header token found — verify placement is correct
        valid = _header_valid_py(lines) if is_py else _header_valid_rs(lines)
        if valid:
            return True
        # Header present but malformed placement
        if check_only:
            return False
        # In write mode: leave malformed headers alone (they need manual review)
        # to avoid destructive double-insertion
        return False

    # No header — insert it
    if check_only:
        return False

    if repo_root is not None and not path.resolve().is_relative_to(repo_root.resolve()):
        raise SystemExit(f"refusing to write outside repo_root: {path}")

    new_content = _insert_py_header(content) if is_py else _insert_rs_header(content)
    path.write_text(new_content, encoding="utf-8")
    return False  # return False = "was modified"


def run_write(repo_root: Path) -> int:
    """Run --write mode: insert headers in all files missing them."""
    files = _enumerate_files(repo_root)
    modified = 0
    for f in files:
        was_ok = process_file(f, check_only=False, repo_root=repo_root)
        if not was_ok:
            modified += 1
    print(f"--write complete: {modified} files modified, {len(files) - modified} already correct")
    return 0


def run_check(repo_root: Path) -> int:
    """Run --check mode: exit 1 if any file is missing or has wrong header."""
    files = _enumerate_files(repo_root)
    violations: list[str] = []
    for f in files:
        ok = process_file(f, check_only=True)
        if not ok:
            violations.append(str(f.relative_to(repo_root)))
    if violations:
        print(f"SPDX header check FAILED: {len(violations)} file(s) missing or malformed header:")
        for v in violations:
            print(f"  {v}")
        return 1
    print(f"SPDX header check PASSED: all {len(files)} files have correct headers")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Add or check SPDX license headers")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="Insert headers in all files missing them"
    )
    mode.add_argument(
        "--check", action="store_true", help="Exit 1 if any file is missing/wrong header"
    )
    args = parser.parse_args()

    repo_root = _get_repo_root()

    if args.write:
        sys.exit(run_write(repo_root))
    else:
        sys.exit(run_check(repo_root))


if __name__ == "__main__":
    main()
