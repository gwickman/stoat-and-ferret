# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for TTS audio mixing in build_command_for_job (BL-578).

Tests the amix fix in both the multi-clip path and the single-clip translator path.
The single-clip non-translator path is covered by TestBuildCommandTtsMixing in
tests/test_contract/test_tts.py; these tests cover the two remaining paths.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import create_default_registry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import TtsCueAudioInput, build_command_for_job

_NOW = datetime.now(timezone.utc)
_PROJECT_ID = "proj-tts-amix-001"
_OUTPUT_PATH = "/renders/tts_mix_output.mp4"


def _make_render_plan() -> str:
    return json.dumps(
        {
            "total_duration": 10.0,
            "settings": {
                "codec": "libx264",
                "fps": 30.0,
                "width": 1920,
                "height": 1080,
                "quality_preset": "standard",
            },
        }
    )


def _make_job() -> RenderJob:
    return RenderJob(
        id="job-tts-amix-001",
        project_id=_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=_OUTPUT_PATH,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_render_plan(),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )


def _make_clip(
    clip_id: str,
    video_id: str,
    timeline_position: int,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    return Clip(
        id=clip_id,
        project_id=_PROJECT_ID,
        source_video_id=video_id,
        in_point=0,
        out_point=300,  # 10 seconds at 30 fps
        timeline_position=timeline_position,
        created_at=_NOW,
        updated_at=_NOW,
        effects=effects,
    )


def _make_video(video_id: str, path: str, *, audio_codec: str | None = "aac") -> Video:
    return Video(
        id=video_id,
        path=path,
        filename=f"{video_id}.mp4",
        duration_frames=300,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        audio_codec=audio_codec,
        file_size=10_000_000,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_tts_input() -> TtsCueAudioInput:
    return TtsCueAudioInput(
        cue_id="cue-amix-001",
        audio_path="/tmp/tts_narration.wav",
        track_id="voice-track",
        start_s=1.0,
        weight=1.0,
        volume_envelope=None,
    )


# ---------------------------------------------------------------------------
# Multi-clip path TTS amix tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_clip_tts_with_source_audio_uses_amix() -> None:
    """BL-578-AC-1/AC-4 (multi-clip): TTS + source audio → amix, single [aout] stream."""
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4", audio_codec="aac"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4", audio_codec="aac"),
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0),
        _make_clip("clip-b", "vid-b", timeline_position=300),
    ]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    cmd = await build_command_for_job(
        _make_job(), clip_repo, video_repo, tts_inputs=[_make_tts_input()]
    )

    cmd_str = " ".join(cmd)
    assert "amix=inputs=2:duration=longest" in cmd_str
    assert "[aout]" in cmd_str

    # AC-4: single audio map — no bare -map 0:a alongside tts map (parallel-stream antipattern)
    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert "0:a" not in map_flags


@pytest.mark.asyncio
async def test_multi_clip_tts_all_video_only_no_amix() -> None:
    """BL-578-AC-2/AC-6 (multi-clip): TTS + all-video-only clips → TTS-only map, no amix."""
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4", audio_codec=None),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4", audio_codec=None),
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0),
        _make_clip("clip-b", "vid-b", timeline_position=300),
    ]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    cmd = await build_command_for_job(
        _make_job(), clip_repo, video_repo, tts_inputs=[_make_tts_input()]
    )

    cmd_str = " ".join(cmd)
    assert "amix" not in cmd_str
    assert "[aout]" not in cmd_str

    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert any(f.startswith("[tts") for f in map_flags)


@pytest.mark.asyncio
async def test_multi_clip_tts_later_clip_audio_uses_amix() -> None:
    """BL-621-AC-1/AC-4: clip 0 video-only, clip 1 has audio + TTS → amix uses clip 1's stream."""
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4", audio_codec=None),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4", audio_codec="aac"),
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0),
        _make_clip("clip-b", "vid-b", timeline_position=300),
    ]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    cmd = await build_command_for_job(
        _make_job(), clip_repo, video_repo, tts_inputs=[_make_tts_input()]
    )

    cmd_str = " ".join(cmd)
    # Source audio from clip 1 (input index 1) must be amixed with TTS, not dropped.
    assert "amix=inputs=2:duration=longest" in cmd_str
    assert "[aout]" in cmd_str
    # Amix must reference input 1's audio stream, not the no-audio input 0.
    assert "[1:a]" in cmd_str
    assert "[0:a]" not in cmd_str

    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert "[aout]" in map_flags


@pytest.mark.asyncio
async def test_multi_clip_no_tts_no_amix() -> None:
    """BL-578-AC-3 (multi-clip): no TTS → no amix, no filter_complex audio stream (regression)."""
    videos = {
        "vid-a": _make_video("vid-a", "/media/clip_a.mp4", audio_codec="aac"),
        "vid-b": _make_video("vid-b", "/media/clip_b.mp4", audio_codec="aac"),
    }
    clips = [
        _make_clip("clip-a", "vid-a", timeline_position=0),
        _make_clip("clip-b", "vid-b", timeline_position=300),
    ]
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=clips)
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(side_effect=lambda vid_id: videos.get(vid_id))

    cmd = await build_command_for_job(_make_job(), clip_repo, video_repo, tts_inputs=[])

    cmd_str = " ".join(cmd)
    assert "amix" not in cmd_str
    assert "-an" in cmd


# ---------------------------------------------------------------------------
# Single-clip translator path TTS amix tests
# ---------------------------------------------------------------------------

_BLUR_EFFECT: list[dict[str, Any]] = [
    {"effect_type": "blur", "parameters": {"sigma": 2.0}, "filter_string": "gblur=sigma=2"},
]


@pytest.mark.asyncio
async def test_translator_tts_with_source_audio_uses_amix() -> None:
    """BL-578-AC-1/AC-4 (translator): TTS + file clip with audio → amix, single [aout] stream."""
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(
        return_value=[_make_clip("clip-sc", "vid-sc", 0, effects=_BLUR_EFFECT)]
    )
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(
        return_value=_make_video("vid-sc", "/media/source.mp4", audio_codec="aac")
    )

    cmd = await build_command_for_job(
        _make_job(),
        clip_repo,
        video_repo,
        effect_registry=create_default_registry(),
        tts_inputs=[_make_tts_input()],
    )

    cmd_str = " ".join(cmd)
    assert "amix=inputs=2:duration=longest" in cmd_str
    assert "[aout]" in cmd_str

    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert "0:a" not in map_flags


@pytest.mark.asyncio
async def test_translator_tts_video_only_source_no_amix() -> None:
    """BL-578-AC-2/AC-6 (translator): TTS + video-only source → TTS-only map, no amix."""
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(
        return_value=[_make_clip("clip-sc", "vid-sc", 0, effects=_BLUR_EFFECT)]
    )
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(
        return_value=_make_video("vid-sc", "/media/source.mp4", audio_codec=None)
    )

    cmd = await build_command_for_job(
        _make_job(),
        clip_repo,
        video_repo,
        effect_registry=create_default_registry(),
        tts_inputs=[_make_tts_input()],
    )

    cmd_str = " ".join(cmd)
    assert "amix" not in cmd_str
    assert "[aout]" not in cmd_str

    map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
    assert any(f.startswith("[tts") for f in map_flags)


@pytest.mark.asyncio
async def test_translator_no_tts_no_amix() -> None:
    """BL-578-AC-3 (translator): no TTS → no amix, standard filter_complex path (regression)."""
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(
        return_value=[_make_clip("clip-sc", "vid-sc", 0, effects=_BLUR_EFFECT)]
    )
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(
        return_value=_make_video("vid-sc", "/media/source.mp4", audio_codec="aac")
    )

    cmd = await build_command_for_job(
        _make_job(),
        clip_repo,
        video_repo,
        effect_registry=create_default_registry(),
        tts_inputs=[],
    )

    cmd_str = " ".join(cmd)
    assert "amix" not in cmd_str
    assert "-filter_complex" in cmd
    assert "-an" in cmd
