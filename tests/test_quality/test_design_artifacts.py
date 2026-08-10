# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Regression guard: drift_fix_scope_scan_query entries must resolve to real HEAD matches.

BL-491 found that BL-489's v079 design ledger entry pointed drift_fix_scope_scan_query at
``api/routers/`` while the schema it describes (``CreateRenderRequest``) lives in
``api/schemas/`` — a scope-scan query that returns 0 matches regardless of whether the
underlying issue is fixed, making it useless for verification. This guard catches the same
class of mistake in any future ledger entry: a ``target_tree``/``pattern`` pair that is
supposed to find >=1 match post-fix but structurally cannot.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V079_LEDGER_RELATIVE_PATH = "comms/outbox/versions/design/v079/source-intent-ledger.json"
_NOISE_DIR_NAMES = frozenset({"__pycache__", ".git", "node_modules", "dist", ".venv", "venv"})


def _get_artifacts_root() -> Path | None:
    """Resolve the auto-dev-projects artifacts root, or None if unavailable (e.g. in CI).

    Never hardcodes a user-specific absolute path (BL-491-AC-3): prefers the ARTIFACTS_ROOT
    env var, falling back to the conventional sibling-directory layout used by every
    stoat-and-ferret dev checkout (``<projects>/auto-dev-projects/<repo-name>`` next to
    ``<projects>/<repo-name>``).
    """
    env_root = os.environ.get("ARTIFACTS_ROOT")
    if env_root:
        candidate = Path(env_root)
        return candidate if candidate.exists() else None
    candidate = _REPO_ROOT.parent / "auto-dev-projects" / _REPO_ROOT.name
    return candidate if candidate.exists() else None


def _count_pattern_matches(target_tree: Path, pattern: str) -> int:
    """Count regex ``pattern`` occurrences under ``target_tree`` (file or directory)."""
    if not target_tree.exists():
        return 0
    regex = re.compile(pattern)
    if target_tree.is_file():
        candidates = [target_tree]
    else:
        candidates = [
            p
            for p in target_tree.rglob("*")
            if p.is_file() and not any(part in _NOISE_DIR_NAMES for part in p.parts)
        ]
    total = 0
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        total += len(regex.findall(text))
    return total


def find_broken_drift_fix_scope_scans(items: list[dict[str, object]], repo_root: Path) -> list[str]:
    """Return failure messages for drift_fix_scope_scan_query entries that cannot match.

    An entry with ``expected_post_fix_match_count == 0`` intentionally records that its
    pattern should find nothing once the underlying drift is fixed (e.g. BL-489's pattern
    searches for text describing the bug, which is correctly absent once fixed) — asserting
    ">= 1 match" for those would invert the ledger's own recorded intent, so they are not
    checked here. Entries expecting >=1 match (the normal case, and the only case a wrong
    ``target_tree`` can silently break) are checked for real.
    """
    failures: list[str] = []
    for item in items:
        query = item.get("drift_fix_scope_scan_query")
        if not query:
            continue
        assert isinstance(query, dict)
        item_id = item.get("item_id", "?")
        pattern = query.get("pattern", "")
        target_tree = query.get("target_tree", "")
        if not pattern or not target_tree:
            continue
        expected = query.get("expected_post_fix_match_count")
        if expected == 0:
            continue
        observed = _count_pattern_matches(repo_root / str(target_tree), str(pattern))
        if observed == 0:
            failures.append(
                f"{item_id}: pattern {pattern!r} returned 0 matches in {target_tree!r} "
                f"(expected >= {expected if expected is not None else 1})"
            )
    return failures


def test_drift_fix_scope_scan_helper_flags_broken_target_tree() -> None:
    """Positive/negative unit test for the comparison logic, independent of the artifacts repo.

    Uses this repo's own known-good CreateRenderRequest location (the exact entity BL-489/
    BL-491 concern) as the positive case, and a pattern guaranteed absent as the negative
    case — proving the helper actually discriminates a correct target_tree from a broken one.
    """
    good_items: list[dict[str, object]] = [
        {
            "item_id": "BL-TEST-GOOD",
            "drift_fix_scope_scan_query": {
                "target_tree": "src/stoat_ferret/api/schemas/",
                "pattern": "class CreateRenderRequest",
                "expected_post_fix_match_count": 1,
            },
        }
    ]
    assert find_broken_drift_fix_scope_scans(good_items, _REPO_ROOT) == []

    broken_items: list[dict[str, object]] = [
        {
            "item_id": "BL-TEST-BROKEN",
            "drift_fix_scope_scan_query": {
                "target_tree": "src/stoat_ferret/api/routers/",
                "pattern": "class CreateRenderRequest",
                "expected_post_fix_match_count": 1,
            },
        }
    ]
    failures = find_broken_drift_fix_scope_scans(broken_items, _REPO_ROOT)
    assert len(failures) == 1
    assert "BL-TEST-BROKEN" in failures[0]


def test_drift_fix_scope_scan_helper_skips_zero_expectation_and_null_items() -> None:
    """Items with expected_post_fix_match_count == 0 or a null query are not flagged."""
    items: list[dict[str, object]] = [
        {"item_id": "BL-TEST-NULL", "drift_fix_scope_scan_query": None},
        {
            "item_id": "BL-TEST-ZERO-EXPECTED",
            "drift_fix_scope_scan_query": {
                "target_tree": "src/stoat_ferret/api/schemas/",
                "pattern": "this_pattern_should_never_match_anything_xyz",
                "expected_post_fix_match_count": 0,
            },
        },
    ]
    assert find_broken_drift_fix_scope_scans(items, _REPO_ROOT) == []


def test_v079_drift_fix_scope_scan_patterns_match_head() -> None:
    """Every non-zero-expectation drift_fix_scope_scan_query in the v079 ledger matches HEAD."""
    artifacts_root = _get_artifacts_root()
    if artifacts_root is None:
        pytest.skip("ARTIFACTS_ROOT not available (expected in CI)")

    ledger_path = artifacts_root / _V079_LEDGER_RELATIVE_PATH
    if not ledger_path.exists():
        pytest.skip(f"v079 ledger not found at {ledger_path}")

    import json

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    items = ledger.get("items", [])
    assert items, f"v079 ledger at {ledger_path} unexpectedly has no items"

    failures = find_broken_drift_fix_scope_scans(items, _REPO_ROOT)
    if failures:
        pytest.fail(
            "drift_fix_scope_scan_query entries returned 0 matches at HEAD despite "
            "expecting >=1:\n" + "\n".join(failures),
            pytrace=False,
        )
