# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Shared FFmpeg-gated render-output oracle for pytest acceptance tests and UAT journeys."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path

from stoat_ferret.ffmpeg.probe import ffprobe_video

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")


def compute_ssim(
    output: Path, t_out: float, ref: Path, t_ref: float, duration: float = 0.3
) -> float:
    """Return overall SSIM between a segment of output and a reference via ffmpeg."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-ss",
            str(t_out),
            "-t",
            str(duration),
            "-i",
            str(output),
            "-ss",
            str(t_ref),
            "-t",
            str(duration),
            "-i",
            str(ref),
            "-filter_complex",
            "[0:v][1:v]ssim=f=-",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    m = re.search(r"All:(\d+\.\d+)", r.stderr)
    if not m:
        raise RuntimeError(f"Could not parse SSIM from ffmpeg output:\n{r.stderr[-600:]}")
    return float(m.group(1))


async def assert_frame_count(path: Path, expected_frames: int, tolerance: int = 2) -> None:
    """Assert decoded frame count matches expected_frames within tolerance.

    Uses format.duration * fps (not nb_frames) for actual count.
    Accurate for constant-FPS H.264 output. Not suitable for VFR sources
    where accumulated rounding error may cause the count to drift beyond tolerance.
    Raises ValueError for negative expected_frames; AssertionError when count is out of tolerance.
    """
    if expected_frames < 0:
        raise ValueError(f"expected_frames must be >= 0, got {expected_frames}")
    meta = await ffprobe_video(str(path))
    actual = int(meta.duration_seconds * meta.frame_rate_numerator / meta.frame_rate_denominator)
    assert abs(actual - expected_frames) <= tolerance, (
        f"expected {expected_frames} frames, got {actual}"
    )


async def assert_frame_rate(path: Path, expected_num: int, expected_den: int) -> None:
    """Assert r_frame_rate matches expected_num/expected_den rational."""
    meta = await ffprobe_video(str(path))
    assert meta.frame_rate_numerator == expected_num, (
        f"expected frame rate {expected_num}/{expected_den}, "
        f"got {meta.frame_rate_numerator}/{meta.frame_rate_denominator}"
    )
    assert meta.frame_rate_denominator == expected_den, (
        f"expected frame rate {expected_num}/{expected_den}, "
        f"got {meta.frame_rate_numerator}/{meta.frame_rate_denominator}"
    )


async def assert_stream_inventory(path: Path, video: bool = True, audio: bool = True) -> None:
    """Assert the file's stream inventory satisfies expected video/audio presence flags.

    Uses ffprobe -show_streams JSON (codec_type field). All four flag combinations enforced.
    """
    result = await asyncio.to_thread(
        subprocess.run,
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"ffprobe failed for {path}: {result.stderr[-400:]}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if video:
        assert len(video_streams) > 0, f"expected video stream in {path}, but none found"
    else:
        assert len(video_streams) == 0, (
            f"expected no video stream in {path}, but found {len(video_streams)}"
        )
    if audio:
        assert len(audio_streams) > 0, f"expected audio stream in {path}, but none found"
    else:
        assert len(audio_streams) == 0, (
            f"expected no audio stream in {path}, but found {len(audio_streams)}"
        )


async def assert_av_duration_alignment(path: Path, max_delta_ms: float = 100.0) -> None:
    """Assert audio and video stream durations are within max_delta_ms milliseconds.

    Raises ValueError for non-positive max_delta_ms.
    Raises AssertionError when the delta exceeds the threshold.
    """
    if max_delta_ms <= 0:
        raise ValueError("max_delta_ms must be > 0")
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"ffprobe failed for {path}: {result.stderr[-400:]}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not audio_streams or not video_streams:
        raise AssertionError(f"missing audio or video stream in {path}")
    a_dur = float(audio_streams[0].get("duration", 0))
    v_dur = float(video_streams[0].get("duration", 0))
    delta_ms = abs(a_dur - v_dur) * 1000.0
    assert delta_ms <= max_delta_ms, (
        f"A/V duration delta {delta_ms:.1f}ms exceeds {max_delta_ms}ms "
        f"(audio={a_dur:.3f}s, video={v_dur:.3f}s)"
    )


def assert_inpoint_identity(
    output: Path,
    output_t: float,
    source: Path,
    source_start: float,
    source_end: float,
    threshold: float = 0.99,
    check_start: bool = False,
    check_end: bool = False,
    margin_s: float = 0.1,
) -> None:
    """Assert in-point source-range identity via SSIM at the range midpoint.

    Computes source_t = (source_start + source_end) / 2 and checks SSIM >= threshold.

    Optional boundary checks (require a time-varying fixture such as testsrc2 to be
    meaningful — a static/solid-colour fixture cannot distinguish wrong-start from
    correct-start boundary SSIM):
    - check_start: asserts SSIM at output_t=margin_s vs source_t=source_start+margin_s.
    - check_end: asserts SSIM at output_t=output_duration-margin_s vs source_t=source_end-margin_s.
      output_duration is inferred from output_t for the end check via source range length.

    Raises ValueError for threshold outside (0, 1]; AssertionError when SSIM is below threshold.
    """
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    source_t = (source_start + source_end) / 2
    ssim = compute_ssim(output, output_t, source, source_t)
    assert ssim >= threshold, f"in-point SSIM {ssim:.4f} < threshold {threshold}"
    if check_start:
        start_ssim = compute_ssim(output, margin_s, source, source_start + margin_s)
        assert start_ssim >= threshold, (
            f"in-point start-boundary SSIM {start_ssim:.4f} < threshold {threshold}"
        )
    if check_end:
        output_duration = source_end - source_start
        end_ssim = compute_ssim(output, output_duration - margin_s, source, source_end - margin_s)
        assert end_ssim >= threshold, (
            f"in-point end-boundary SSIM {end_ssim:.4f} < threshold {threshold}"
        )


def assert_seam_frame_order(
    output: Path,
    seam_t: float,
    pre_source: Path,
    pre_t: float,
    post_source: Path,
    post_t: float,
    threshold: float = 0.99,
) -> None:
    """Assert transition seam frame order via SSIM at ±50ms around the seam point.

    Checks that frame at seam_t - 0.05 matches pre_source at pre_t, and frame at
    seam_t + 0.05 matches post_source at post_t.
    Raises ValueError when seam_t + 0.05 exceeds file duration or threshold is invalid.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1]")
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {output}: {r.stderr[-400:]}")
    data = json.loads(r.stdout)
    file_duration = float(data["format"]["duration"])
    if seam_t + 0.05 > file_duration:
        raise ValueError(f"seam_t {seam_t} exceeds file duration {file_duration}")
    pre_ssim = compute_ssim(output, seam_t - 0.05, pre_source, pre_t, duration=0.02)
    assert pre_ssim >= threshold, f"pre-seam SSIM {pre_ssim:.4f} < threshold {threshold}"
    post_ssim = compute_ssim(output, seam_t + 0.05, post_source, post_t, duration=0.02)
    assert post_ssim >= threshold, f"post-seam SSIM {post_ssim:.4f} < threshold {threshold}"


async def measure_audio_rms_db(path: Path) -> float:
    """Return the overall RMS level dB from ffmpeg astats stderr output.

    Runs ``ffmpeg -i <path> -af astats -f null -`` via asyncio.to_thread, then parses
    "RMS level dB:" from the "Overall" block in stderr.

    Raises:
        RuntimeError: If ffmpeg fails or the Overall block is not found in output.
        ValueError: If the RMS level line is malformed or not present in the Overall block.
    """
    result = await asyncio.to_thread(
        subprocess.run,
        ["ffmpeg", "-i", str(path), "-af", "astats", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    stderr = result.stderr
    overall_idx = stderr.find("] Overall\n")
    if overall_idx == -1:
        overall_idx = stderr.find("] Overall\r\n")
    if overall_idx == -1:
        raise RuntimeError(
            f"Overall block not found in ffmpeg astats output for {path}:\n{stderr[-800:]}"
        )
    overall_section = stderr[overall_idx:]
    m = re.search(r"RMS level dB:\s*([-\d.]+)", overall_section)
    if not m:
        raise ValueError(
            f"RMS level dB not found in Overall block for {path}:\n{overall_section[:400]}"
        )
    return float(m.group(1))


def assert_audio_rms_changed(
    measured_db: float,
    baseline_db: float,
    min_delta_db: float = 5.0,
) -> None:
    """Assert that measured_db differs from baseline_db by at least min_delta_db.

    Raises:
        AssertionError: If abs(measured_db - baseline_db) < min_delta_db.
    """
    delta = abs(measured_db - baseline_db)
    assert delta >= min_delta_db, (
        f"audio RMS delta {delta:.2f} dB < threshold {min_delta_db} dB "
        f"(measured={measured_db:.2f} dB, baseline={baseline_db:.2f} dB)"
    )


def assert_transition_reference(
    output: Path,
    seam_t: float,
    transition_type: str,
    duration_secs: float,
    ref: Path,
    tolerance: float = 0.95,
) -> None:
    """Assert that the transition window at seam_t in *output* matches *ref*.

    Compares SSIM of frames sampled from [seam_t, seam_t + duration_secs] in
    *output* vs the same window in *ref* (a pre-rendered output produced with
    the expected transition type).

    Raises AssertionError if mean SSIM < tolerance.

    Note: Distinguishing similar transitions requires high-contrast fixture content
    (e.g. testsrc2). Low-contrast fixtures may fail to discriminate transition types.
    """
    try:
        ssim = compute_ssim(output, seam_t, ref, seam_t, duration=duration_secs)
    except RuntimeError as exc:
        raise AssertionError(
            f"no frames extracted from transition window at seam_t={seam_t}: {exc}"
        ) from exc
    assert ssim >= tolerance, (
        f"transition window SSIM {ssim:.4f} < tolerance {tolerance} "
        f"(expected {transition_type!r} at seam_t={seam_t}, window={duration_secs}s)"
    )
