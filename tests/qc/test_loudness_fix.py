"""Regression test for BL-476: loudness/true-peak checks must produce non-null measurements.

FFmpeg-gated. Skip when STOAT_TEST_FFMPEG is unset.

Before this fix, QCService ran ebur128=framelog=verbose but parse_loudness_report
expected loudnorm JSON fields (input_i / integrated_loudness). The mismatch raised
ValueError on every input, causing the except clause to return _NULL_CHECK.
This test guards against future filter/parser format mismatches.
"""

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

_STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

_skip_no_ffmpeg = pytest.mark.skipif(
    not _STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


def _make_service() -> QCService:
    repo = InMemoryQCReportRepository()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    settings = MagicMock()
    return QCService(repository=repo, connection_manager=ws, settings=settings)


def _generate_sine_wav(path: Path) -> None:
    """Generate a 5-second 440 Hz sine wave WAV via FFmpeg."""
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
async def test_loudness_integrated_is_non_null(tmp_path: Path) -> None:
    """loudness_integrated.measured must be a non-null numeric after the loudnorm fix."""
    audio = tmp_path / "sine.wav"
    _generate_sine_wav(audio)

    svc = _make_service()
    record = await svc.run_checks(str(audio))
    checks = json.loads(record.checks)

    measured = checks["loudness_integrated"]["measured"]
    assert measured is not None, (
        "loudness_integrated.measured is null — filter/parser format mismatch "
        "(ebur128 vs loudnorm JSON); check qc_service.py filter string"
    )
    assert isinstance(measured, (int, float)), (
        f"loudness_integrated.measured is not numeric: {measured!r}"
    )


@_skip_no_ffmpeg
async def test_true_peak_is_non_null(tmp_path: Path) -> None:
    """true_peak.measured must be a non-null numeric after the loudnorm fix."""
    audio = tmp_path / "sine.wav"
    _generate_sine_wav(audio)

    svc = _make_service()
    record = await svc.run_checks(str(audio))
    checks = json.loads(record.checks)

    measured = checks["true_peak"]["measured"]
    assert measured is not None, (
        "true_peak.measured is null — filter/parser format mismatch "
        "(ebur128 vs loudnorm JSON); check qc_service.py filter string"
    )
    assert isinstance(measured, (int, float)), f"true_peak.measured is not numeric: {measured!r}"
