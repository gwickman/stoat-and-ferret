# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Regression tests for SPDX header gate (scripts/add_license_headers.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "add_license_headers.py"

SPDX_PY_HEADER = (
    "# SPDX-License-Identifier: AGPL-3.0-or-later\n# Copyright (C) 2026 Grant Wickman\n"
)


def _init_git_repo(path: Path) -> None:
    """Initialize a minimal git repo with user config."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_check_exits_nonzero_for_missing_header(tmp_path: Path) -> None:
    """--check exits non-zero and names the file when a header is missing."""
    _init_git_repo(tmp_path)
    missing = tmp_path / "no_header.py"
    missing.write_text("print('hello')\n")
    subprocess.run(["git", "add", "no_header.py"], cwd=tmp_path, check=True, capture_output=True)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert result.returncode != 0
    assert "no_header.py" in result.stdout


def test_check_exits_zero_with_header(tmp_path: Path) -> None:
    """--check exits 0 when all tracked files have SPDX headers."""
    _init_git_repo(tmp_path)
    with_header = tmp_path / "has_header.py"
    with_header.write_text(SPDX_PY_HEADER + "print('hello')\n")
    subprocess.run(["git", "add", "has_header.py"], cwd=tmp_path, check=True, capture_output=True)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert result.returncode == 0
