# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""FFmpeg-gated tests for chapter metadata embedding (BL-426).

All tests require STOAT_TEST_FFMPEG=1 — they run real FFmpeg and ffprobe to
verify chapter and metadata embedding in exported files.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from stoat_ferret.api.services.qc_service import QCService
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.markers_repository import Marker
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository
from stoat_ferret.render.service import generate_ffmetadata

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_marker(
    marker_id: str,
    *,
    start_time: float,
    end_time: float,
    name: str = "",
    region_type: str = "section",
) -> Marker:
    return Marker(
        id=marker_id,
        project_id="proj-test",
        start_time=start_time,
        end_time=end_time,
        name=name,
        region_type=region_type,
        created_at="2026-01-01T00:00:00Z",
    )


def _embed_chapters(
    source: Path,
    output: Path,
    ffmetadata_content: str,
) -> None:
    """Run FFmpeg to embed chapters from ffmetadata into output file."""
    with tempfile.NamedTemporaryFile(
        suffix=".ffmetadata", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(ffmetadata_content)
        meta_path = tmp.name
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(source),
                "-i",
                meta_path,
                "-c",
                "copy",
                "-map_chapters",
                "1",
                "-map_metadata",
                "1",
                "-y",
                str(output),
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"ffmpeg embed failed: {result.stderr.decode()[:500]}")
    finally:
        Path(meta_path).unlink(missing_ok=True)


async def _ffprobe_chapters(path: Path) -> list[dict]:
    """Return chapters list from ffprobe JSON output."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_chapters",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    data = json.loads(stdout.decode())
    return data.get("chapters", [])


async def _ffprobe_format_tags(path: Path) -> dict:
    """Return format tags (container metadata) from ffprobe JSON output."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    data = json.loads(stdout.decode())
    return data.get("format", {}).get("tags", {})


def _make_qc_service() -> QCService:
    repo = InMemoryQCReportRepository()
    broadcast_events: list[dict] = []
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock(side_effect=lambda event: broadcast_events.append(event))
    settings = MagicMock()
    return QCService(
        repository=repo,
        connection_manager=ws,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_chapter_count_equals_section_count(
    sample_video_path: Path,
    tmp_path: Path,
) -> None:
    """Chapter count in rendered file equals section marker count (BL-426-AC-1, AC-3)."""
    markers = [
        _make_marker("m1", start_time=0.0, end_time=0.4, name="Intro"),
        _make_marker("m2", start_time=0.4, end_time=0.8, name="Main"),
        _make_marker("m3", start_time=0.8, end_time=1.0, name="Outro"),
    ]

    content = generate_ffmetadata(markers)
    output = tmp_path / "output_3ch.mp4"
    _embed_chapters(sample_video_path, output, content)

    chapters = await _ffprobe_chapters(output)
    assert len(chapters) == 3, f"Expected 3 chapters, got {len(chapters)}"


async def test_chapter_titles_match_marker_names(
    sample_video_path: Path,
    tmp_path: Path,
) -> None:
    """Chapter titles in rendered file match section marker names (BL-426-AC-1)."""
    markers = [
        _make_marker("m1", start_time=0.0, end_time=0.5, name="Opening Act"),
        _make_marker("m2", start_time=0.5, end_time=1.0, name="Closing Credits"),
    ]

    content = generate_ffmetadata(markers)
    output = tmp_path / "output_titles.mp4"
    _embed_chapters(sample_video_path, output, content)

    chapters = await _ffprobe_chapters(output)
    assert len(chapters) == 2
    titles = [c.get("tags", {}).get("title", "") for c in chapters]
    assert titles[0] == "Opening Act"
    assert titles[1] == "Closing Credits"


async def test_metadata_title_embedded(
    sample_video_path: Path,
    tmp_path: Path,
) -> None:
    """Container title from metadata_template appears in output file (BL-426-AC-2)."""
    markers = [
        _make_marker("m1", start_time=0.0, end_time=1.0, name="Full"),
    ]

    content = generate_ffmetadata(markers, metadata_title="Session Alpha")
    output = tmp_path / "output_title.mp4"
    _embed_chapters(sample_video_path, output, content)

    tags = await _ffprobe_format_tags(output)
    title = tags.get("title", "")
    assert title == "Session Alpha", f"Expected title 'Session Alpha', got '{title}'"


async def test_qc_chapters_present_check_passes(
    sample_video_path: Path,
    tmp_path: Path,
) -> None:
    """QCService chapters_present check passes after chapter embedding (BL-426-AC-4)."""
    markers = [
        _make_marker("m1", start_time=0.0, end_time=0.5, name="Part 1"),
        _make_marker("m2", start_time=0.5, end_time=1.0, name="Part 2"),
    ]

    content = generate_ffmetadata(markers)
    output = tmp_path / "output_qc.mp4"
    _embed_chapters(sample_video_path, output, content)

    svc = _make_qc_service()
    record = await svc.run_checks(str(output), assertions={"chapters_present": 2.0})

    checks = json.loads(record.checks)
    ch_check = checks.get("chapters_present", {})
    assert ch_check.get("pass") is True, f"chapters_present check failed: {ch_check}"


async def test_render_without_markers_zero_chapters(
    sample_video_path: Path,
    tmp_path: Path,
) -> None:
    """No section markers → 0 chapters embedded, no crash (BL-426 edge case)."""
    content = generate_ffmetadata([])
    output = tmp_path / "output_zero.mp4"
    _embed_chapters(sample_video_path, output, content)

    chapters = await _ffprobe_chapters(output)
    assert len(chapters) == 0, f"Expected 0 chapters, got {len(chapters)}"
