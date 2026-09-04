# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance tests: multi-clip + TTS audio sequencing and single-clip TTS effect bypass (BL-814).

Multi-clip TTS test (AC-4): 2-clip project (clip A ~440 Hz, clip B ~880 Hz source audio,
plus TTS cue at 2000 Hz) — asserts stream inventory, A/V alignment, per-band presence in
per-clip output windows, and TTS band in its cue window.

SC TTS effect RMS test (AC-9): single-clip + volume effect + TTS — asserts source-audio RMS
differs from no-effect baseline by >= 5 dB while TTS band remains present.

All tests are FFmpeg-gated (STOAT_TEST_FFMPEG=1).
Run with: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/test_uc_media_multiclip_tts_audio.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import CONVOLUTION_REVERB, VOLUME
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import CommandBuildError, TtsCueAudioInput, build_command_for_job
from tests.render_oracle import (
    assert_audio_band_window,
    assert_audio_rms_changed,
    assert_av_duration_alignment,
    assert_stream_inventory,
    measure_audio_rms_db,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG", "0") == "1"

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)

_PROJECT_ID_MC = "proj-mc-tts-audio-001"
_PROJECT_ID_SC = "proj-sc-tts-effect-001"


def _make_audio_video_fixture(path: Path, duration: int = 5, freq_hz: int = 440) -> Path:
    """Generate an audio+video MP4 with a single-frequency stereo track (amerge pattern)."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x240:rate=30:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq_hz}:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq_hz}:duration={duration}",
            "-filter_complex",
            "amerge=inputs=2",
            "-ac",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg fixture generation failed: {result.stderr.decode()[-800:]}")
    return path


def _make_tts_wav_fixture(path: Path, duration: float = 1.5, freq_hz: int = 2000) -> Path:
    """Generate a synthetic TTS WAV file using a sine wave at a distinct frequency."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq_hz}:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq_hz}:duration={duration}",
            "-filter_complex",
            "amerge=inputs=2",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg TTS WAV generation failed: {result.stderr.decode()[-800:]}")
    return path


def _make_video(
    vid_id: str, path: str, audio_codec: str | None = "aac", duration_frames: int = 150
) -> Video:
    """Create a Video model pointing to a fixture file."""
    now = datetime.now(timezone.utc)
    return Video(
        id=vid_id,
        path=path,
        filename="fixture.mp4",
        duration_frames=duration_frames,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=320,
        height=240,
        video_codec="h264",
        file_size=500_000,
        created_at=now,
        updated_at=now,
        audio_codec=audio_codec,
    )


def _make_clip(
    clip_id: str,
    vid_id: str,
    project_id: str,
    in_point: int = 0,
    out_point: int = 150,
    effects: list[dict[str, Any]] | None = None,
) -> Clip:
    """Create a Clip spanning the full 5-second fixture duration."""
    now = datetime.now(timezone.utc)
    return Clip(
        id=clip_id,
        project_id=project_id,
        source_video_id=vid_id,
        in_point=in_point,
        out_point=out_point,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type="file",
        effects=effects,
        source_asset_id=None,
        generator_params=None,
    )


def _make_render_job(project_id: str, output_path: str, total_duration: float) -> RenderJob:
    """Create a RenderJob with the given total_duration."""
    now = datetime.now(timezone.utc)
    plan = json.dumps(
        {
            "total_duration": total_duration,
            "settings": {
                "output_format": "mp4",
                "codec": "libx264",
                "fps": 30.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
            },
        }
    )
    return RenderJob(
        id=f"job-{project_id}",
        project_id=project_id,
        status=RenderStatus.RUNNING,
        output_path=output_path,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=plan,
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_clip_repo(*clips: Clip) -> AsyncMock:
    """Build an async mock clip repository returning the given clips."""
    repo: AsyncMock = AsyncMock()
    repo.list_by_project = AsyncMock(return_value=list(clips))
    return repo


def _make_video_repo(*videos: Video) -> AsyncMock:
    """Build an async mock video repository indexed by video ID."""
    vid_map = {v.id: v for v in videos}
    repo: AsyncMock = AsyncMock()

    async def _get(vid_id: str) -> Video | None:
        return vid_map.get(vid_id)

    repo.get = AsyncMock(side_effect=_get)
    return repo


@_FFMPEG_SKIP
async def test_uc_media_multiclip_tts_audio(tmp_path: Path) -> None:
    """2-clip+TTS render: source-audio bands sequenced; TTS band in cue window (BL-814-AC-4).

    Clips: A=440 Hz, B=880 Hz, each 5s with 1s acrossfade. TTS=2000 Hz at start_s=0.
    Total = 5+5-1 = 9.0s.
    Assertions:
    - assert_stream_inventory(video=True, audio=True)
    - A/V duration alignment within oracle threshold
    - 440 Hz band present in clip-A pure zone (0.5-3.5s)
    - 880 Hz band present in clip-B pure zone (5.5-8.0s)
    - 2000 Hz (TTS) band present in cue window (0.5-1.0s)
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5, freq_hz=440)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5, freq_hz=880)
    tts_path = _make_tts_wav_fixture(tmp_path / "tts.wav", duration=1.5, freq_hz=2000)
    out_path = tmp_path / "output.mp4"

    vid_a = _make_video("vid-a", str(clip_a_path))
    vid_b = _make_video("vid-b", str(clip_b_path))
    clip_a = _make_clip("clip-a", "vid-a", _PROJECT_ID_MC)
    clip_b = _make_clip("clip-b", "vid-b", _PROJECT_ID_MC)

    # 5+5 - 1 acrossfade = 9.0s
    job = _make_render_job(_PROJECT_ID_MC, str(out_path), total_duration=9.0)
    tts_inputs = [
        TtsCueAudioInput(
            cue_id="cue-tts",
            audio_path=str(tts_path),
            track_id="track-1",
            start_s=0.0,
            weight=1.0,
            volume_envelope=None,
        )
    ]

    cmd = await build_command_for_job(
        job,
        _make_clip_repo(clip_a, clip_b),
        _make_video_repo(vid_a, vid_b),
        tts_inputs=tts_inputs,
    )

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    await assert_stream_inventory(out_path, video=True, audio=True)
    await assert_av_duration_alignment(out_path, max_delta_ms=150.0)

    # Clip A pure zone (440 Hz): 0.5-3.5s — source audio from clip A present
    await assert_audio_band_window(out_path, 0.5, 3.5, expected_bands_hz=[440], absent_bands_hz=[])
    # Clip B pure zone (880 Hz): 5.5-8.0s — source audio from clip B present
    await assert_audio_band_window(out_path, 5.5, 8.0, expected_bands_hz=[880], absent_bands_hz=[])
    # TTS cue window (2000 Hz): 0.5-1.0s — TTS band present (start_s=0, 1.5s duration)
    await assert_audio_band_window(out_path, 0.5, 1.0, expected_bands_hz=[2000], absent_bands_hz=[])


@_FFMPEG_SKIP
async def test_sc_tts_audio_effect_rms(tmp_path: Path) -> None:
    """Single-clip + volume=2.0 + TTS: source RMS raised >= 5 dB; TTS band present (BL-814-AC-9).

    Renders the same single-clip+TTS project twice: with and without volume=2.0 audio effect.
    Asserts source-audio-band RMS differs by >= 5 dB (volume=2.0 ≈ +6 dB change).
    Also verifies the TTS band (2000 Hz) remains detectable in both outputs.
    """
    clip_path = _make_audio_video_fixture(tmp_path / "clip.mp4", duration=3, freq_hz=440)
    tts_path = _make_tts_wav_fixture(tmp_path / "tts.wav", duration=1.5, freq_hz=2000)
    out_no_eff = tmp_path / "out_no_effect.mp4"
    out_with_eff = tmp_path / "out_with_effect.mp4"

    vid = _make_video("vid-sc", str(clip_path), duration_frames=90)
    clip_no_eff = _make_clip("clip-no-eff", "vid-sc", _PROJECT_ID_SC, out_point=90)
    clip_with_eff = _make_clip(
        "clip-with-eff",
        "vid-sc",
        _PROJECT_ID_SC,
        out_point=90,
        effects=[{"effect_type": "volume", "parameters": {"volume": 2.0}}],
    )
    tts_inputs = [
        TtsCueAudioInput(
            cue_id="cue-sc",
            audio_path=str(tts_path),
            track_id="track-1",
            start_s=0.0,
            weight=1.0,
            volume_envelope=None,
        )
    ]
    reg = EffectRegistry()
    reg.register("volume", VOLUME)

    # Render WITHOUT effect — baseline
    job_no_eff = _make_render_job(_PROJECT_ID_SC, str(out_no_eff), total_duration=3.0)
    cmd_no_eff = await build_command_for_job(
        job_no_eff,
        _make_clip_repo(clip_no_eff),
        _make_video_repo(vid),
        tts_inputs=tts_inputs,
    )
    r = await asyncio.to_thread(subprocess.run, cmd_no_eff, capture_output=True, timeout=120)
    assert r.returncode == 0, f"ffmpeg (no-effect) failed: {r.stderr.decode()[-800:]}"
    await assert_stream_inventory(out_no_eff, video=True, audio=True)
    baseline_rms_db = await measure_audio_rms_db(out_no_eff)

    # Render WITH volume=2.0 effect
    job_with_eff = _make_render_job(_PROJECT_ID_SC, str(out_with_eff), total_duration=3.0)
    cmd_with_eff = await build_command_for_job(
        job_with_eff,
        _make_clip_repo(clip_with_eff),
        _make_video_repo(vid),
        tts_inputs=tts_inputs,
        effect_registry=reg,
    )
    r2 = await asyncio.to_thread(subprocess.run, cmd_with_eff, capture_output=True, timeout=120)
    assert r2.returncode == 0, f"ffmpeg (with-effect) failed: {r2.stderr.decode()[-800:]}"
    await assert_stream_inventory(out_with_eff, video=True, audio=True)
    effect_rms_db = await measure_audio_rms_db(out_with_eff)

    # Source-audio RMS must differ by >= 5 dB (volume=2.0 ≈ +6 dB change)
    assert_audio_rms_changed(effect_rms_db, baseline_rms_db, min_delta_db=5.0)

    # TTS band (2000 Hz) must remain present in both outputs
    await assert_audio_band_window(
        out_no_eff, 0.5, 1.0, expected_bands_hz=[2000], absent_bands_hz=[]
    )
    await assert_audio_band_window(
        out_with_eff, 0.5, 1.0, expected_bands_hz=[2000], absent_bands_hz=[]
    )


@_FFMPEG_SKIP
async def test_av_alignment_2clip_1s_transition(tmp_path: Path) -> None:
    """2-clip non-TTS render: audio and video durations match within 150ms (BL-871 AC-1).

    Clips: A=440Hz, B=880Hz, each 5s with 1s acrossfade. Total = 9.0s.
    Without the fix (o=0), audio would be 10.0s vs video 9.0s (1031ms delta).
    After fix (overlap=1 default), audio duration matches video within 150ms.
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5, freq_hz=440)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5, freq_hz=880)
    out_path = tmp_path / "output.mp4"

    vid_a = _make_video("vid-a", str(clip_a_path))
    vid_b = _make_video("vid-b", str(clip_b_path))
    clip_a = _make_clip("clip-a", "vid-a", _PROJECT_ID_MC)
    clip_b = _make_clip("clip-b", "vid-b", _PROJECT_ID_MC)

    job = _make_render_job(_PROJECT_ID_MC, str(out_path), total_duration=9.0)

    cmd = await build_command_for_job(
        job,
        _make_clip_repo(clip_a, clip_b),
        _make_video_repo(vid_a, vid_b),
    )

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists()
    await assert_av_duration_alignment(out_path, max_delta_ms=150.0)


@_FFMPEG_SKIP
async def test_av_alignment_3clip_2transitions(tmp_path: Path) -> None:
    """3-clip non-TTS render: A/V durations match within 150ms (BL-871 AC-2).

    Clips: A=250Hz, B=1000Hz, C=4000Hz, each 5s with 1s acrossfades. Total = 13.0s.
    Without the fix, audio would be 15.0s vs video 13.0s (2031ms delta with 2 transitions).
    After fix, audio matches video within 150ms — verifies no per-transition accumulation.
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5, freq_hz=250)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5, freq_hz=1000)
    clip_c_path = _make_audio_video_fixture(tmp_path / "clip_c.mp4", duration=5, freq_hz=4000)
    out_path = tmp_path / "output.mp4"

    vid_a = _make_video("vid-a-3c", str(clip_a_path))
    vid_b = _make_video("vid-b-3c", str(clip_b_path))
    vid_c = _make_video("vid-c-3c", str(clip_c_path))
    clip_a = _make_clip("clip-a-3c", "vid-a-3c", _PROJECT_ID_MC)
    clip_b = _make_clip("clip-b-3c", "vid-b-3c", _PROJECT_ID_MC)
    clip_c = _make_clip("clip-c-3c", "vid-c-3c", _PROJECT_ID_MC)

    job = _make_render_job(_PROJECT_ID_MC, str(out_path), total_duration=13.0)

    cmd = await build_command_for_job(
        job,
        _make_clip_repo(clip_a, clip_b, clip_c),
        _make_video_repo(vid_a, vid_b, vid_c),
    )

    result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: ASYNC221
    assert result.returncode == 0, (
        f"Render failed (exit {result.returncode}):\n{result.stderr.decode()[-800:]}"
    )
    assert out_path.exists()
    await assert_av_duration_alignment(out_path, max_delta_ms=150.0)


@_FFMPEG_SKIP
async def test_mc_video_only_audio_effect_raises(tmp_path: Path) -> None:
    """Multi-clip: video-only clip A with audio effect raises CommandBuildError (BL-826 AC-3).

    Clip A is video-only (audio_codec=None) with a volume audio effect.
    Clip B is a normal audio+video clip.
    Asserts CommandBuildError before any output file is produced — consistent with BL-824.
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5, freq_hz=440)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5, freq_hz=880)
    out_path = tmp_path / "output.mp4"

    # clip A declared video-only: audio_codec=None (file exists but audio_codec field is None)
    vid_a = _make_video("vid-a-vo", str(clip_a_path), audio_codec=None)
    vid_b = _make_video("vid-b-vo", str(clip_b_path))
    clip_a = _make_clip(
        "clip-a-vo",
        "vid-a-vo",
        _PROJECT_ID_MC,
        effects=[{"effect_type": "volume", "parameters": {"volume": 1.5}}],
    )
    clip_b = _make_clip("clip-b-vo", "vid-b-vo", _PROJECT_ID_MC)

    job = _make_render_job(_PROJECT_ID_MC, str(out_path), total_duration=9.0)
    reg = EffectRegistry()
    reg.register("volume", VOLUME)

    with pytest.raises(CommandBuildError, match="has audio effects but no audio stream"):
        await build_command_for_job(
            job,
            _make_clip_repo(clip_a, clip_b),
            _make_video_repo(vid_a, vid_b),
            effect_registry=reg,
        )

    assert not out_path.exists(), "Output file must not be produced before CommandBuildError"


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_sc_tts_video_only_audio_effect_raises(tmp_path: Path) -> None:
    """Single-clip TTS + video-only + audio effect raises CommandBuildError (BL-873 AC-4).

    Clip is video-only (audio_codec=None) with a volume audio effect and a TTS input.
    Asserts CommandBuildError is raised before any output file is produced — consistent
    with the BL-824 non-TTS single-clip guard.
    """
    clip_path = _make_audio_video_fixture(tmp_path / "clip.mp4", duration=5, freq_hz=440)
    tts_path = _make_tts_wav_fixture(tmp_path / "tts.wav", duration=1.0)
    out_path = tmp_path / "output.mp4"

    vid = _make_video("vid-sc-tts-vo", str(clip_path), audio_codec=None)
    clip = _make_clip(
        "clip-sc-tts-vo",
        "vid-sc-tts-vo",
        _PROJECT_ID_SC,
        effects=[{"effect_type": "volume", "parameters": {"volume": 1.5}}],
    )
    tts_inputs = [
        TtsCueAudioInput(
            cue_id="cue-sc-tts-vo",
            audio_path=str(tts_path),
            track_id="track-1",
            start_s=0.0,
            weight=1.0,
            volume_envelope=None,
        )
    ]
    job = _make_render_job(_PROJECT_ID_SC, str(out_path), total_duration=5.0)
    reg = EffectRegistry()
    reg.register("volume", VOLUME)

    with pytest.raises(CommandBuildError, match="has audio effects but no audio stream"):
        await build_command_for_job(
            job,
            _make_clip_repo(clip),
            _make_video_repo(vid),
            tts_inputs=tts_inputs,
            effect_registry=reg,
        )

    assert not out_path.exists(), "Output file must not be produced before CommandBuildError"


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_convolution_reverb_fail_closed(tmp_path: Path) -> None:
    """convolution_reverb raises CommandBuildError at build time (BL-827 AC-6 / FR-001-AC-3).

    Applies convolution_reverb to a clip with audio and asserts that a structured
    CommandBuildError is raised before any output file is produced. The IR WAV is
    not wired as a second -i input in the current render path, so the guard prevents
    a guaranteed FFmpeg runtime crash.
    """
    clip_path = _make_audio_video_fixture(tmp_path / "clip.mp4", duration=5, freq_hz=440)
    out_path = tmp_path / "output.mp4"

    vid = _make_video("vid-reverb", str(clip_path))
    clip = _make_clip(
        "clip-reverb",
        "vid-reverb",
        _PROJECT_ID_SC,
        effects=[
            {
                "effect_type": "convolution_reverb",
                "parameters": {"ir_name": "hall_small", "mix": 0.4},
            }
        ],
    )

    job = _make_render_job(_PROJECT_ID_SC, str(out_path), total_duration=5.0)
    reg = EffectRegistry()
    reg.register("convolution_reverb", CONVOLUTION_REVERB)

    with pytest.raises(CommandBuildError, match="convolution_reverb requires IR WAV"):
        await build_command_for_job(
            job,
            _make_clip_repo(clip),
            _make_video_repo(vid),
            effect_registry=reg,
        )

    assert not out_path.exists(), "Output file must not be produced before CommandBuildError"


@_FFMPEG_SKIP
@pytest.mark.asyncio
async def test_mc_oversized_transition_raises(tmp_path: Path) -> None:
    """Multi-clip: oversized transition duration raises CommandBuildError (BL-862 AC-2).

    Clip A is a 5-second clip; the transition duration is 5.0s (== clip duration).
    Guard fires in _build_clip_input_list before RenderTransition is constructed,
    preventing a negative xfade offset from reaching FFmpeg.
    """
    clip_a_path = _make_audio_video_fixture(tmp_path / "clip_a.mp4", duration=5, freq_hz=440)
    clip_b_path = _make_audio_video_fixture(tmp_path / "clip_b.mp4", duration=5, freq_hz=880)
    out_path = tmp_path / "output.mp4"

    # duration_frames=150, frame_rate=30 -> 5.0s; transition_dur=5.0 >= 5.0 -> guard fires
    vid_a = _make_video("vid-ot-a", str(clip_a_path), duration_frames=150)
    vid_b = _make_video("vid-ot-b", str(clip_b_path), duration_frames=150)
    clip_a = _make_clip("clip-ot-a", "vid-ot-a", "proj-ot-001", out_point=150)
    clip_b = _make_clip("clip-ot-b", "vid-ot-b", "proj-ot-001", out_point=150)

    plan = json.dumps(
        {
            "total_duration": 5.0,
            "settings": {
                "output_format": "mp4",
                "codec": "libx264",
                "fps": 30.0,
                "width": 320,
                "height": 240,
                "quality_preset": "standard",
                "transitions": [
                    {"clip_a_id": "clip-ot-a", "transition_type": "fade", "duration": 5.0}
                ],
            },
        }
    )
    now = datetime.now(timezone.utc)
    job = RenderJob(
        id="job-ot-001",
        project_id="proj-ot-001",
        status=RenderStatus.RUNNING,
        output_path=str(out_path),
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=plan,
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )

    with pytest.raises(CommandBuildError, match="transition duration"):
        await build_command_for_job(
            job,
            _make_clip_repo(clip_a, clip_b),
            _make_video_repo(vid_a, vid_b),
        )

    assert not out_path.exists(), "Output file must not be produced before CommandBuildError"
