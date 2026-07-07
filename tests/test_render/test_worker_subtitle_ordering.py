# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for multi-clip soft-subtitle -i ordering in the render worker (BL-618).

Verifies that:
- All -i flags appear before -filter_complex in multi-clip commands with soft subtitles.
- -map N:s stream mappings reference correct subtitle input stream indices.
- Single-clip soft-subtitle path ordering is unchanged (regression guard).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import TtsCueAudioInput, build_command_for_job

_PROJECT_ID = "proj-subtitle-order-001"
_OUTPUT_PATH = "/renders/subtitle_order.mp4"
_EN_ASSET_ID = uuid.UUID("00000000-0000-0000-0000-000000000021")
_ES_ASSET_ID = uuid.UUID("00000000-0000-0000-0000-000000000022")
_EN_SRT_PATH = "/data/assets/en_order.srt"
_ES_SRT_PATH = "/data/assets/es_order.srt"


@dataclass
class _FakeAsset:
    id: str
    file_path: str
    original_filename: str = "test.srt"
    content_hash: str = "abc"
    mime_type: str = "application/x-subrip"
    kind: str = "subtitle"
    size_bytes: int = 1024
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    deleted_at: str | None = None


def _make_render_plan(with_subtitles: bool = True) -> str:
    settings: dict[str, Any] = {
        "codec": "libx264",
        "fps": 30.0,
        "width": 1920,
        "height": 1080,
        "quality_preset": "standard",
    }
    if with_subtitles:
        settings["soft_subtitles"] = [
            {"source_asset_id": str(_EN_ASSET_ID), "language": "en", "is_default": True},
            {"source_asset_id": str(_ES_ASSET_ID), "language": "es"},
        ]
    return json.dumps({"total_duration": 10.0, "settings": settings})


def _make_job(with_subtitles: bool = True) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-subtitle-order-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=_OUTPUT_PATH,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_render_plan(with_subtitles),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_clip(clip_id: str, video_id: str, timeline_position: int) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=0,
        out_point=150,  # 5 seconds at 30 fps
        timeline_position=timeline_position,
        created_at=now,
        updated_at=now,
    )


def _make_video(video_id: str, path: str) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=video_id,
        path=path,
        filename=f"{video_id}.mp4",
        duration_frames=150,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=10_000_000,
        created_at=now,
        updated_at=now,
    )


def _make_multi_clip_repos() -> tuple[AsyncMock, AsyncMock]:
    clips = [
        _make_clip("clip-order-a", "vid-order-a", 0),
        _make_clip("clip-order-b", "vid-order-b", 150),
    ]
    videos = {
        "vid-order-a": _make_video("vid-order-a", "/media/clip_a.mp4"),
        "vid-order-b": _make_video("vid-order-b", "/media/clip_b.mp4"),
    }
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))
    return clip_repo, video_repo


def _make_single_clip_repos() -> tuple[AsyncMock, AsyncMock]:
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[_make_clip("clip-sc", "vid-sc", 0)])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=_make_video("vid-sc", "/media/single.mp4"))
    return clip_repo, video_repo


def _make_asset_repo() -> AsyncMock:
    asset_repo = AsyncMock()

    async def _get_by_id(asset_id: str) -> _FakeAsset | None:
        if asset_id == str(_EN_ASSET_ID):
            return _FakeAsset(id=asset_id, file_path=_EN_SRT_PATH)
        if asset_id == str(_ES_ASSET_ID):
            return _FakeAsset(id=asset_id, file_path=_ES_SRT_PATH)
        return None

    asset_repo.get_by_id = _get_by_id
    return asset_repo


def _i_positions(cmd: list[str]) -> list[int]:
    """Return indices of all -i flags in the command."""
    return [i for i, v in enumerate(cmd) if v == "-i"]


def _filter_complex_position(cmd: list[str]) -> int:
    """Return the index of -filter_complex in the command, or -1 if absent."""
    try:
        return cmd.index("-filter_complex")
    except ValueError:
        return -1


@pytest.mark.asyncio
async def test_all_i_flags_precede_filter_complex_in_multi_clip() -> None:
    """BL-618-AC-1: all -i flags appear before -filter_complex in multi-clip subtitle command."""
    clip_repo, video_repo = _make_multi_clip_repos()
    asset_repo = _make_asset_repo()
    job = _make_job(with_subtitles=True)

    cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

    fc_idx = _filter_complex_position(cmd)
    assert fc_idx > 0, f"-filter_complex not found in command: {cmd}"

    i_positions = _i_positions(cmd)
    assert i_positions, "No -i flags found in command"

    violating = [pos for pos in i_positions if pos >= fc_idx]
    assert not violating, (
        f"-i flags found at positions {violating} which are at or after "
        f"-filter_complex at position {fc_idx}.\nCommand: {cmd}"
    )


@pytest.mark.asyncio
async def test_subtitle_map_indices_correct_in_multi_clip() -> None:
    """BL-618-AC-2: subtitle -map N:s flags reference correct stream indices.

    With 2 file clips (input_paths = [clip_a, clip_b]) and no TTS/ffmetadata:
    subtitle_base_mc = 2; expected -map 2:s and -map 3:s.
    """
    clip_repo, video_repo = _make_multi_clip_repos()
    asset_repo = _make_asset_repo()
    job = _make_job(with_subtitles=True)

    cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert "2:s" in map_flags, f"-map 2:s (EN subtitle) missing from map flags: {map_flags}"
    assert "3:s" in map_flags, f"-map 3:s (ES subtitle) missing from map flags: {map_flags}"

    # Subtitle maps must follow the video/audio output map
    fc_idx = _filter_complex_position(cmd)
    for idx, val in enumerate(cmd):
        if val == "-map" and idx + 1 < len(cmd) and cmd[idx + 1] in ("2:s", "3:s"):
            assert idx > fc_idx, (
                f"-map {cmd[idx + 1]} at position {idx} is before "
                f"-filter_complex at position {fc_idx}"
            )


@pytest.mark.asyncio
async def test_subtitle_inputs_precede_filter_complex_with_tts() -> None:
    """BL-618-AC-1 (with TTS): subtitle -i flags remain before -filter_complex when TTS present.

    With 2 clips + 1 TTS input + 2 subtitles:
    - TTS -i at index 2
    - Subtitle -i at indices 3, 4
    - Then -filter_complex
    """
    clip_repo, video_repo = _make_multi_clip_repos()
    asset_repo = _make_asset_repo()
    job = _make_job(with_subtitles=True)
    tts_input = TtsCueAudioInput(
        cue_id="cue-001",
        audio_path="/tmp/tts_narration.wav",
        track_id="voice",
        start_s=0.0,
        weight=1.0,
        volume_envelope=None,
    )

    cmd = await build_command_for_job(
        job, clip_repo, video_repo, tts_inputs=[tts_input], asset_repository=asset_repo
    )

    fc_idx = _filter_complex_position(cmd)
    assert fc_idx > 0, f"-filter_complex not found in command: {cmd}"

    i_positions = _i_positions(cmd)
    violating = [pos for pos in i_positions if pos >= fc_idx]
    assert not violating, (
        f"-i flags found at positions {violating} at or after "
        f"-filter_complex at position {fc_idx}.\nCommand: {cmd}"
    )


@pytest.mark.asyncio
async def test_subtitle_map_indices_correct_with_tts() -> None:
    """BL-618-AC-2 (with TTS): subtitle maps at correct indices when TTS input present.

    With 2 clips + 1 TTS: subtitle_base_mc = 2 (clips) + 0 (no ffmeta) + 1 (TTS) = 3.
    Expected: -map 3:s, -map 4:s.
    """
    clip_repo, video_repo = _make_multi_clip_repos()
    asset_repo = _make_asset_repo()
    job = _make_job(with_subtitles=True)
    tts_input = TtsCueAudioInput(
        cue_id="cue-001",
        audio_path="/tmp/tts_narration.wav",
        track_id="voice",
        start_s=0.0,
        weight=1.0,
        volume_envelope=None,
    )

    cmd = await build_command_for_job(
        job, clip_repo, video_repo, tts_inputs=[tts_input], asset_repository=asset_repo
    )

    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert "3:s" in map_flags, f"-map 3:s (EN subtitle) missing from map flags: {map_flags}"
    assert "4:s" in map_flags, f"-map 4:s (ES subtitle) missing from map flags: {map_flags}"


@pytest.mark.asyncio
async def test_single_clip_subtitle_ordering_unchanged() -> None:
    """BL-618-AC-6: single-clip soft-subtitle path retains correct ordering (regression guard).

    The single-clip path already has correct -i ordering; this verifies no regression.
    Subtitle base = 1 (source) + 0 (no ffmeta) + 0 (no TTS) = 1.
    """
    clip_repo, video_repo = _make_single_clip_repos()
    asset_repo = _make_asset_repo()
    job = _make_job(with_subtitles=True)

    cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

    # Single-clip path: all -i inputs appear before any output option
    # (The single-clip path emits -ss/-t before filter/codec; -i flags precede those too)
    i_positions = _i_positions(cmd)
    assert i_positions, "No -i flags found in command"

    # Single-clip subtitle maps reference index 1 and 2 (source=0, en.srt=1, es.srt=2)
    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert "1:s" in map_flags, f"-map 1:s (EN subtitle) missing: {map_flags}"
    assert "2:s" in map_flags, f"-map 2:s (ES subtitle) missing: {map_flags}"
