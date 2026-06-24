# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Test that the stray-reference detector catches bare MIT references."""

from __future__ import annotations

import subprocess
from pathlib import Path

ALLOWLIST = "scripts/license_grep_allowlist.txt"
PATTERN = r"(^|[^[:alnum:]_])MIT([^[:alnum:]_]|$)"


def test_bare_mit_detected_in_synthetic_file(tmp_path: Path) -> None:
    """Detector finds an unallowlisted bare MIT reference."""
    bad_file = tmp_path / "test_file.py"
    bad_file.write_text('# This code is MIT licensed\nprint("hello")\n')
    result = subprocess.run(
        ["grep", "-E", "-i", "-l", PATTERN, str(bad_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "Pattern should match the synthetic file"
    assert str(bad_file.name) in result.stdout or str(bad_file) in result.stdout


def test_allowlist_excludes_legitimate_files() -> None:
    """All files in the allowlist exist in the repo."""
    allowlist = Path(ALLOWLIST)
    assert allowlist.exists(), f"Allowlist not found: {ALLOWLIST}"
    for line in allowlist.read_text().splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            assert Path(entry).exists(), f"Allowlist entry not found: {entry}"


def test_pattern_rejects_permit_submit() -> None:
    """POSIX ERE pattern does not match permit, submit, commit, or permitted."""
    for word in ("permit", "submit", "commit", "permitted"):
        result = subprocess.run(
            ["grep", "-E", "-i", PATTERN],
            input=word,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"Pattern should NOT match '{word}'"
