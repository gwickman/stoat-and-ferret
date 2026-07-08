# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Golden QC fixture determinism tests (BL-424-AC-5, requires FFmpeg)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.api.services.qc_service import QCService
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")
GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "golden_qc_report.json"

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


def _make_real_service() -> QCService:
    repo = InMemoryQCReportRepository()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    settings = MagicMock()
    return QCService(repository=repo, connection_manager=ws, settings=settings)


def _generate_audio(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=5",
            "-ar", "48000",
            "-ac", "2",
            "-y", str(path),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )


async def test_golden_qc_report_determinism(tmp_path: Path) -> None:
    """Two consecutive QCService runs on identical input produce identical reports.

    Discharges BL-424-AC-5: confirms the parser+analysis pipeline is deterministic
    for the same FFmpeg lavfi source, so golden fixture comparisons are meaningful.
    Runs twice against the same WAV file and asserts per-check identity.
    """
    assert GOLDEN_FIXTURE.exists(), "Golden fixture must exist before determinism check"
    audio_path = tmp_path / "det_test.wav"
    _generate_audio(audio_path)

    rec_a = await _make_real_service().run_checks(str(audio_path))
    rec_b = await _make_real_service().run_checks(str(audio_path))

    checks_a = json.loads(rec_a.checks)
    checks_b = json.loads(rec_b.checks)
    diffs = {
        k: (checks_a.get(k), checks_b.get(k))
        for k in set(checks_a) | set(checks_b)
        if checks_a.get(k) != checks_b.get(k)
    }
    assert not diffs, (
        "QCService produced non-deterministic output on identical input.\n"
        "Differing checks:\n"
        + "\n".join(f"  {k}: run1={v[0]} run2={v[1]}" for k, v in diffs.items())
    )
    assert rec_a.overall_verdict == rec_b.overall_verdict
