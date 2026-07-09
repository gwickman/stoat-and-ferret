# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Golden QC regression and drift detection (BL-458).

Compares current QCService output against the golden fixture JSON.
FFmpeg-gated tests require STOAT_TEST_FFMPEG=1.
test_coverage_threshold_configured runs without FFmpeg.

Drift rules:
- Boolean/count checks (pass/fail, integer measured): exact match required.
- Loudness checks (loudness_integrated, true_peak): ±0.1 LUFS / ±0.1 dBTP tolerance.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.api.services.qc_service import ALL_CHECK_IDS, QCService
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")
GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "golden_qc_report.json"

_LOUDNESS_CHECK_IDS = {"loudness_integrated", "true_peak"}
_LOUDNESS_TOLERANCE = 0.1

_skip_no_ffmpeg = pytest.mark.skipif(
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


def _make_real_service() -> tuple[QCService, InMemoryQCReportRepository]:
    repo = InMemoryQCReportRepository()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    settings = MagicMock()
    return QCService(repository=repo, connection_manager=ws, settings=settings), repo


def _generate_test_audio(path: Path) -> None:
    """Generate a 5-second sine wave test audio file via ffmpeg."""
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-y",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )


@_skip_no_ffmpeg
def test_golden_fixture_is_not_placeholder() -> None:
    """After FFmpeg discharge, the fixture must contain real measurements."""
    fixture = _load_golden()
    assert fixture.get("status") != "placeholder", (
        "Golden fixture is still a placeholder — regenerate with STOAT_TEST_FFMPEG=1 "
        "and --update-golden flag"
    )


@_skip_no_ffmpeg
def test_golden_fixture_has_overall_verdict() -> None:
    fixture = _load_golden()
    assert "overall" in fixture
    assert fixture["overall"] in ("pass", "fail")


@_skip_no_ffmpeg
def test_golden_fixture_has_all_12_check_ids() -> None:
    fixture = _load_golden()
    checks = fixture.get("checks", {})
    missing = [cid for cid in ALL_CHECK_IDS if cid not in checks]
    assert not missing, f"Missing check IDs in golden fixture: {missing}"


@_skip_no_ffmpeg
async def test_update_golden_fixture(update_golden: bool, tmp_path: Path) -> None:
    """Regenerate golden_qc_report.json from current QCService output.

    Skipped unless --update-golden is passed. Requires STOAT_TEST_FFMPEG=1.
    """
    if not update_golden:
        pytest.skip("pass --update-golden to regenerate")

    audio_path = tmp_path / "test_render.wav"
    _generate_test_audio(audio_path)

    svc, _ = _make_real_service()
    record = await svc.run_checks(str(audio_path))
    checks = json.loads(record.checks)
    golden = {"overall": record.overall_verdict, "checks": checks}
    GOLDEN_FIXTURE.write_text(json.dumps(golden, indent=2))


@_skip_no_ffmpeg
async def test_no_drift_from_golden(tmp_path: Path) -> None:
    """Re-run QCService against a sample render and compare to golden.

    Fails if loudness drifts beyond ±0.1 LUFS or structural fields differ.
    Requires a non-placeholder golden fixture (run --update-golden first).
    """
    golden = _load_golden()
    if golden.get("status") == "placeholder":
        pytest.skip("Golden fixture is still placeholder — regenerate with --update-golden")

    audio_path = tmp_path / "test_render.wav"
    _generate_test_audio(audio_path)

    svc, _ = _make_real_service()
    record = await svc.run_checks(str(audio_path))
    current_checks = json.loads(record.checks)
    golden_checks = golden.get("checks", {})

    drifts = []
    for check_id in golden_checks:
        drift = _checks_differ(golden_checks, current_checks, check_id)
        if drift:
            drifts.append(drift)
    assert not drifts, "QC regression drift detected:\n" + "\n".join(drifts)


def test_coverage_threshold_configured() -> None:
    """Assert that Python coverage fail-under threshold is configured in pyproject.toml."""
    content = Path("pyproject.toml").read_text()
    assert "fail_under" in content, (
        "Coverage threshold not configured. "
        "Add fail_under = 80 to [tool.coverage.report] in pyproject.toml."
    )
