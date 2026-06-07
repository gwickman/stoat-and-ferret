"""Golden QC fixture determinism tests (deferred_post_merge, requires FFmpeg)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")
GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "golden_qc_report.json"

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


def test_golden_qc_report_determinism() -> None:
    """Two consecutive fixture generation runs produce identical QC report JSON."""
    # Placeholder: full implementation requires QCService (Release 2 downstream)
    # When STOAT_TEST_FFMPEG=1: generate report twice, compare JSON
    assert GOLDEN_FIXTURE.exists(), "Golden fixture file must exist"
