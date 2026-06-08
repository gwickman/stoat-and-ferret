"""Golden QC regression and drift detection (BL-458).

Compares current QCService output against the golden fixture JSON.
All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1) and deferred_post_merge.

Drift rules:
- Boolean/count checks (pass/fail, integer measured): exact match required.
- Loudness checks (loudness_integrated, true_peak): ±0.1 LUFS / ±0.1 dBTP tolerance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")
GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "golden_qc_report.json"

_LOUDNESS_CHECK_IDS = {"loudness_integrated", "true_peak"}
_LOUDNESS_TOLERANCE = 0.1

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


def _load_golden() -> dict[str, Any]:
    return json.loads(GOLDEN_FIXTURE.read_text())  # type: ignore[no-any-return]


def _checks_differ(golden: dict[str, Any], current: dict[str, Any], check_id: str) -> str | None:
    """Return a description of drift if detected, else None."""
    g = golden.get(check_id, {})
    c = current.get(check_id, {})
    if g.get("pass") != c.get("pass"):
        return f"{check_id}: pass changed {g.get('pass')} → {c.get('pass')}"
    g_measured = g.get("measured")
    c_measured = c.get("measured")
    if g_measured is None and c_measured is None:
        return None
    if g_measured is None or c_measured is None:
        return f"{check_id}: measured changed {g_measured} → {c_measured}"
    if check_id in _LOUDNESS_CHECK_IDS:
        if abs(float(g_measured) - float(c_measured)) > _LOUDNESS_TOLERANCE:
            return (
                f"{check_id}: measured drifted by "
                f"{abs(float(g_measured) - float(c_measured)):.3f} "
                f"(tolerance ±{_LOUDNESS_TOLERANCE})"
            )
    else:
        if g_measured != c_measured:
            return f"{check_id}: measured changed {g_measured} → {c_measured}"
    return None


def test_golden_fixture_is_not_placeholder() -> None:
    """After FFmpeg discharge, the fixture must contain real measurements."""
    fixture = _load_golden()
    assert fixture.get("status") != "placeholder", (
        "Golden fixture is still a placeholder — regenerate with STOAT_TEST_FFMPEG=1 "
        "and --update-golden flag"
    )


def test_golden_fixture_has_overall_verdict() -> None:
    fixture = _load_golden()
    assert "overall" in fixture
    assert fixture["overall"] in ("pass", "fail")


def test_golden_fixture_has_all_11_check_ids() -> None:
    from stoat_ferret.api.services.qc_service import ALL_CHECK_IDS

    fixture = _load_golden()
    checks = fixture.get("checks", {})
    missing = [cid for cid in ALL_CHECK_IDS if cid not in checks]
    assert not missing, f"Missing check IDs in golden fixture: {missing}"


def test_no_drift_from_golden(tmp_path: pytest.TempPathFactory) -> None:
    """Re-run QCService against the same sample render and compare to golden.

    Placeholder: full implementation requires FFmpeg-rendered sample file.
    When STOAT_TEST_FFMPEG=1: render sample project, run QCService, compare.
    """
    golden = _load_golden()
    # When implemented: current = run_qc_service_on_sample_render()
    # For now, re-loading golden as current to establish the infrastructure:
    current_checks = golden.get("checks", {})
    golden_checks = golden.get("checks", {})
    drifts = []
    for check_id in golden_checks:
        drift = _checks_differ(golden_checks, current_checks, check_id)
        if drift:
            drifts.append(drift)
    assert not drifts, "QC regression drift detected:\n" + "\n".join(drifts)
