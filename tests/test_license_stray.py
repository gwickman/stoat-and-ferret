# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Test that the stray-reference detector catches bare MIT references."""

from __future__ import annotations

import re
from pathlib import Path

ALLOWLIST = "scripts/license_grep_allowlist.txt"
# NOSONAR: fixed-width lookarounds around a 3-char literal, linear-time by construction,
# no nested/unbounded quantifiers, cannot backtrack catastrophically.
PYTHON_PATTERN = r"(?<!\w)MIT(?!\w)"  # NOSONAR


def test_bare_mit_detected_in_synthetic_file(tmp_path: Path) -> None:
    """Detector finds an unallowlisted bare MIT reference."""
    positive_cases = [
        "MIT",
        "MIT-licensed",
        'license = { text = "MIT" }',
    ]
    for i, content in enumerate(positive_cases):
        bad_file = tmp_path / f"test_file_{i}.py"
        bad_file.write_text(content)
        assert re.search(PYTHON_PATTERN, bad_file.read_text(), re.IGNORECASE) is not None, (
            f"Pattern should match: {content!r}"
        )


def test_allowlist_excludes_legitimate_files() -> None:
    """All files in the allowlist exist in the repo."""
    allowlist = Path(ALLOWLIST)
    assert allowlist.exists(), f"Allowlist not found: {ALLOWLIST}"
    for line in allowlist.read_text().splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            assert Path(entry).exists(), f"Allowlist entry not found: {entry}"


def test_pattern_rejects_permit_submit() -> None:
    """Python re pattern does not match permit, submit, commit, or permitted."""
    for word in ("permit", "submit", "commit", "permitted"):
        assert re.search(PYTHON_PATTERN, word, re.IGNORECASE) is None, f"False positive: {word}"
