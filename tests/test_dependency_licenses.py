# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Regression tests for check_dependency_licenses.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = "scripts/check_dependency_licenses.py"


def test_missing_dep_exits_nonzero(tmp_path: Path) -> None:
    """Checker exits non-zero when a dep is missing from the inventory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["test-dep-missing>=1.0"]\n')
    inventory = tmp_path / "inventory.md"
    inventory.write_text("# Dependency License Inventory\n\n(empty)\n")
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            SCRIPT,
            "--pyproject-path",
            str(pyproject),
            "--inventory-path",
            str(inventory),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "test-dep-missing" in result.stdout + result.stderr


def test_current_pyproject_passes() -> None:
    """Checker exits 0 on current pyproject.toml and inventory."""
    result = subprocess.run(
        ["uv", "run", "python", SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Check failed: {result.stdout}\n{result.stderr}"
