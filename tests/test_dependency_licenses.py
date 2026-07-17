# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Regression tests for check_dependency_licenses.py."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = "scripts/check_dependency_licenses.py"
SCRIPT_PATH = Path(SCRIPT).resolve()


def _pip_licenses_available() -> bool:
    # Path 1: module entry point
    result = subprocess.run(
        [sys.executable, "-m", "pip_licenses", "--version"],
        capture_output=True,
    )
    if result.returncode == 0:
        return True
    # Path 2: console script shim
    return shutil.which("pip-licenses") is not None


def test_missing_dep_exits_nonzero(tmp_path: Path) -> None:
    """Checker exits non-zero when a dep is missing from the inventory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["test-dep-missing>=1.0"]\n')
    inventory = tmp_path / "inventory.md"
    inventory.write_text("# Dependency License Inventory\n\n(empty)\n")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--pyproject-path",
            "pyproject.toml",
            "--inventory-path",
            "inventory.md",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode != 0
    assert "test-dep-missing" in result.stdout + result.stderr


def test_pyproject_path_escaping_cwd_rejected(tmp_path: Path) -> None:
    """A --pyproject-path outside cwd is rejected with a confinement error."""
    outside = tmp_path / "outside_pyproject.toml"
    outside.write_text("[project]\ndependencies = []\n")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--pyproject-path",
            str(outside),
            "--inventory-path",
            "inventory.md",
        ],
        capture_output=True,
        text=True,
        cwd=workdir,
    )
    assert result.returncode != 0
    assert "escapes cwd" in result.stdout + result.stderr
    assert "FileNotFoundError" not in result.stderr
    assert "Traceback" not in result.stderr


def test_inventory_path_escaping_cwd_rejected(tmp_path: Path) -> None:
    """A --inventory-path outside cwd is rejected with a confinement error."""
    outside = tmp_path / "outside_inventory.md"
    outside.write_text("# Dependency License Inventory\n")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--pyproject-path",
            "pyproject.toml",
            "--inventory-path",
            str(outside),
        ],
        capture_output=True,
        text=True,
        cwd=workdir,
    )
    assert result.returncode != 0
    assert "escapes cwd" in result.stdout + result.stderr
    assert "FileNotFoundError" not in result.stderr
    assert "Traceback" not in result.stderr


def test_current_pyproject_passes() -> None:
    """Checker exits 0 on current pyproject.toml and inventory (requires pip-licenses)."""
    if not _pip_licenses_available():
        pytest.skip("pip-licenses not installed; dep-license-check CI job covers this case")
    result = subprocess.run(
        [sys.executable, SCRIPT, "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Check failed: {result.stdout}\n{result.stderr}"


def test_no_arg_prints_usage() -> None:
    """Invoking the script without --check prints a usage message and exits 0."""
    result = subprocess.run(
        [sys.executable, SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Unexpected non-zero exit: {result.stderr}"
    assert "Use --check" in result.stdout, f"Expected usage message in stdout: {result.stdout!r}"
