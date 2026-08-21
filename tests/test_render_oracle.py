# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Test suite for the shared render-output oracle module (BL-787)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.render_oracle import (
    STOAT_TEST_FFMPEG,
    assert_audio_rms_changed,
    assert_av_duration_alignment,
    assert_frame_count,
    assert_frame_rate,
    assert_inpoint_identity,
    assert_seam_frame_order,
    assert_stream_inventory,
    assert_transition_reference,
    compute_ssim,
    measure_audio_rms_db,
)

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="Set STOAT_TEST_FFMPEG=1 to run FFmpeg-gated tests",
)


# ---------------------------------------------------------------------------
# Lavfi helper functions
# ---------------------------------------------------------------------------


def _gen_lavfi_video(path: Path, lavfi_expr: str, timeout: int = 60) -> None:
    """Generate a short test video via ffmpeg lavfi."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            lavfi_expr,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lavfi generation failed: {r.stderr.decode()[-800:]}")


def _gen_lavfi_video_with_audio(path: Path, lavfi_expr: str, timeout: int = 60) -> None:
    """Generate a short test video with stereo audio via ffmpeg lavfi.

    Uses amerge of two sine sources per AGENTS.md multi-channel audio pattern.
    """
    r = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            lavfi_expr,
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880",
            "-filter_complex",
            "[1:a][2:a]amerge=inputs=2[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-t",
            "3",
            "-y",
            str(path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        msg = f"ffmpeg lavfi audio+video generation failed: {r.stderr.decode()[-800:]}"
        raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# FFmpeg-gated tests
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_assert_frame_count_passes(tmp_path: Path) -> None:
    """Assert frame count passes for a known 5-second 30fps lavfi video."""
    out = tmp_path / "video.mp4"
    _gen_lavfi_video(out, "color=c=blue:s=320x240:r=30:d=5")
    # 5s × 30fps = 150 frames; tolerance=2
    await assert_frame_count(out, expected_frames=150, tolerance=2)


@_FFMPEG_SKIP
async def test_assert_frame_count_fails(tmp_path: Path) -> None:
    """Assert frame count raises AssertionError when expected count is wrong."""
    out = tmp_path / "video.mp4"
    _gen_lavfi_video(out, "color=c=blue:s=320x240:r=30:d=5")
    with pytest.raises(AssertionError, match="expected 999 frames"):
        await assert_frame_count(out, expected_frames=999, tolerance=2)


@_FFMPEG_SKIP
async def test_assert_frame_rate_passes(tmp_path: Path) -> None:
    """Assert frame rate passes for a 30fps lavfi video."""
    out = tmp_path / "video.mp4"
    _gen_lavfi_video(out, "color=c=blue:s=320x240:r=30:d=3")
    await assert_frame_rate(out, expected_num=30, expected_den=1)


@_FFMPEG_SKIP
async def test_assert_frame_rate_fails(tmp_path: Path) -> None:
    """Assert frame rate raises AssertionError when numerator/denominator do not match."""
    out = tmp_path / "video.mp4"
    _gen_lavfi_video(out, "color=c=blue:s=320x240:r=30:d=3")
    with pytest.raises(AssertionError, match="expected frame rate 24/1"):
        await assert_frame_rate(out, expected_num=24, expected_den=1)


@_FFMPEG_SKIP
async def test_assert_stream_inventory_passes(tmp_path: Path) -> None:
    """Assert stream inventory passes for an audio+video lavfi output."""
    out = tmp_path / "av.mp4"
    _gen_lavfi_video_with_audio(out, "color=c=blue:s=320x240:r=30:d=3")
    await assert_stream_inventory(out, video=True, audio=True)


@_FFMPEG_SKIP
async def test_assert_stream_inventory_no_audio(tmp_path: Path) -> None:
    """Assert stream inventory raises AssertionError for a video-only file when audio=True."""
    out = tmp_path / "video_only.mp4"
    _gen_lavfi_video(out, "color=c=blue:s=320x240:r=30:d=3")
    with pytest.raises(AssertionError, match="expected audio stream"):
        await assert_stream_inventory(out, video=True, audio=True)


@_FFMPEG_SKIP
async def test_assert_av_duration_alignment_passes(tmp_path: Path) -> None:
    """Assert A/V duration alignment passes for a well-formed audio+video lavfi output."""
    out = tmp_path / "av.mp4"
    _gen_lavfi_video_with_audio(out, "color=c=blue:s=320x240:r=30:d=3")
    await assert_av_duration_alignment(out, max_delta_ms=100.0)


@_FFMPEG_SKIP
async def test_assert_inpoint_identity_passes(tmp_path: Path) -> None:
    """Assert in-point identity passes for a solid-colour source compared to itself."""
    src = tmp_path / "src.mp4"
    _gen_lavfi_video(src, "color=c=blue:s=320x240:r=30:d=3")
    # Compare source to itself at the same time — SSIM should be 1.0
    assert_inpoint_identity(src, output_t=1.5, source=src, source_start=1.0, source_end=2.0)


@_FFMPEG_SKIP
async def test_assert_seam_frame_order_passes(tmp_path: Path) -> None:
    """Assert seam frame order passes for a blue-to-red hard-cut concat."""
    blue = tmp_path / "blue.mp4"
    red = tmp_path / "red.mp4"
    out = tmp_path / "concat.mp4"
    _gen_lavfi_video(blue, "color=c=blue:s=320x240:r=30:d=3")
    _gen_lavfi_video(red, "color=c=red:s=320x240:r=30:d=3")
    # Hard-cut concatenation
    r = subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-i",
            str(blue),
            "-i",
            str(red),
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[vout]",
            "-map",
            "[vout]",
            "-c:v",
            "libx264",
            "-crf",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(out),
        ],
        capture_output=True,
        timeout=60,
    )
    assert r.returncode == 0, f"concat failed: {r.stderr.decode()[-400:]}"
    # Seam at t=3.0; pre (t=2.95) should match blue at t=1.5; post (t=3.05) matches red at t=1.5
    assert_seam_frame_order(
        out,
        seam_t=3.0,
        pre_source=blue,
        pre_t=1.5,
        post_source=red,
        post_t=1.5,
    )


@_FFMPEG_SKIP
async def test_compute_ssim_returns_float(tmp_path: Path) -> None:
    """Assert compute_ssim returns a float in (0, 1] for two identical solid-colour videos."""
    src = tmp_path / "src.mp4"
    _gen_lavfi_video(src, "color=c=blue:s=320x240:r=30:d=3")
    result = compute_ssim(src, t_out=1.5, ref=src, t_ref=1.5)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert 0.0 < result <= 1.0, f"SSIM {result} out of range (0, 1]"


@_FFMPEG_SKIP
async def test_assert_stream_inventory_audio_absent_fails(tmp_path: Path) -> None:
    """Assert stream inventory raises AssertionError for audio-bearing file when audio=False."""
    audio_file = tmp_path / "audio_only.m4a"
    subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:a",
            "aac",
            "-y",
            str(audio_file),
        ],
        check=True,
        capture_output=True,
    )
    with pytest.raises(AssertionError):
        await assert_stream_inventory(audio_file, audio=False)


@_FFMPEG_SKIP
async def test_assert_stream_inventory_video_absent_fails(tmp_path: Path) -> None:
    """Assert stream inventory raises AssertionError for audio-only file when video=True."""
    audio_file = tmp_path / "audio_only.m4a"
    subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:a",
            "aac",
            "-y",
            str(audio_file),
        ],
        check=True,
        capture_output=True,
    )
    with pytest.raises(AssertionError):
        await assert_stream_inventory(audio_file, video=True)


# ---------------------------------------------------------------------------
# Transition reference oracle tests (BL-808)
# ---------------------------------------------------------------------------


def _render_xfade(
    clip_a: Path,
    clip_b: Path,
    out: Path,
    transition: str,
    duration: float,
    offset: float,
) -> None:
    """Render two clips joined by an xfade transition into *out*."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(clip_a),
            "-i",
            str(clip_b),
            "-filter_complex",
            f"[0:v][1:v]xfade=transition={transition}:duration={duration}:offset={offset}[vout]",
            "-map",
            "[vout]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(out),
        ],
        capture_output=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError(f"xfade render failed: {r.stderr.decode()[-800:]}")


@_FFMPEG_SKIP
async def test_assert_transition_reference_passing(tmp_path: Path) -> None:
    """Assert transition reference passes when output and ref have identical wipeleft/0.35."""
    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    output = tmp_path / "output_wipeleft.mp4"
    ref = tmp_path / "ref_wipeleft.mp4"

    # High-contrast testsrc2 → solid red: distinct patterns for SSIM discrimination
    _gen_lavfi_video(clip_a, "testsrc2=duration=2:size=320x240:rate=30")
    _gen_lavfi_video(clip_b, "color=c=red:s=320x240:r=30:d=2")

    # Both output and ref: wipeleft/0.35 starting at offset=1.65
    _render_xfade(clip_a, clip_b, output, "wipeleft", 0.35, 1.65)
    _render_xfade(clip_a, clip_b, ref, "wipeleft", 0.35, 1.65)

    # Same transition → high SSIM → no AssertionError
    assert_transition_reference(
        output, seam_t=1.65, transition_type="wipeleft", duration_secs=0.35, ref=ref
    )


@_FFMPEG_SKIP
async def test_assert_transition_reference_failing(tmp_path: Path) -> None:
    """Raises AssertionError when output uses fade/1.0 but ref expects wipeleft/0.35."""
    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    output = tmp_path / "output_fade.mp4"
    ref = tmp_path / "ref_wipeleft.mp4"

    # High-contrast testsrc2 → solid red: distinct patterns for SSIM discrimination
    _gen_lavfi_video(clip_a, "testsrc2=duration=2:size=320x240:rate=30")
    _gen_lavfi_video(clip_b, "color=c=red:s=320x240:r=30:d=2")

    # output: fade/1.0 starting at offset=1.65; ref: wipeleft/0.35 starting at offset=1.65
    _render_xfade(clip_a, clip_b, output, "fade", 1.0, 1.65)
    _render_xfade(clip_a, clip_b, ref, "wipeleft", 0.35, 1.65)

    # Different transitions → low SSIM in the [1.65, 2.0] window → AssertionError
    with pytest.raises(AssertionError):
        assert_transition_reference(
            output, seam_t=1.65, transition_type="wipeleft", duration_secs=0.35, ref=ref
        )


# ---------------------------------------------------------------------------
# No-FFmpeg tests (always run)
# ---------------------------------------------------------------------------


def test_compute_ssim_importable_from_oracle() -> None:
    """Assert compute_ssim is importable and callable from the oracle module (BL-787-AC-5)."""
    from tests.render_oracle import compute_ssim as _fn

    assert callable(_fn)


async def test_assert_frame_count_invalid_threshold_type() -> None:
    """Assert assert_frame_count raises ValueError for negative expected_frames without FFmpeg."""
    with pytest.raises(ValueError, match="expected_frames must be >= 0"):
        await assert_frame_count(Path("/nonexistent.mp4"), expected_frames=-1)


def test_assert_seam_frame_order_seam_exceeds_duration(tmp_path: Path) -> None:
    """Assert assert_seam_frame_order raises ValueError when seam_t+0.05 exceeds file duration."""
    dummy = tmp_path / "out.mp4"
    dummy.write_bytes(b"")
    pre_src = tmp_path / "pre.mp4"
    pre_src.write_bytes(b"")
    post_src = tmp_path / "post.mp4"
    post_src.write_bytes(b"")

    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = json.dumps({"format": {"duration": "1.0"}})
    fake_result.stderr = ""

    with (
        patch("tests.render_oracle.subprocess.run", return_value=fake_result),
        pytest.raises(ValueError, match="seam_t"),
    ):
        assert_seam_frame_order(
            dummy,
            seam_t=2.0,
            pre_source=pre_src,
            pre_t=0.5,
            post_source=post_src,
            post_t=0.5,
        )


# ---------------------------------------------------------------------------
# Audio RMS oracle tests (BL-794)
# ---------------------------------------------------------------------------

_ASTATS_FIXTURE = Path(__file__).parent / "fixtures" / "ffmpeg-astats-ci-sample.txt"
_EXPECTED_RMS_DB = -21.172768


async def test_measure_audio_rms_db_parses_fixture() -> None:
    """measure_audio_rms_db extracts RMS level dB from the CI astats fixture (BL-794 AC-4).

    Mocks asyncio.to_thread so no FFmpeg binary is required.
    """
    from unittest.mock import AsyncMock

    fixture_text = _ASTATS_FIXTURE.read_text(encoding="utf-8", errors="replace")

    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stderr = fixture_text

    with patch("tests.render_oracle.asyncio.to_thread", new_callable=AsyncMock) as mock_th:
        mock_th.return_value = fake_result
        result = await measure_audio_rms_db(Path("/fake/video.mp4"))

    assert abs(result - _EXPECTED_RMS_DB) < 0.001, f"Expected RMS ~{_EXPECTED_RMS_DB}, got {result}"


async def test_measure_audio_rms_db_raises_when_overall_absent() -> None:
    """Raises RuntimeError when Overall block is missing in stderr."""
    from unittest.mock import AsyncMock

    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stderr = "[ffmpeg] some output without the Overall block\n"

    with patch("tests.render_oracle.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = fake_result
        with pytest.raises(RuntimeError, match="Overall block not found"):
            await measure_audio_rms_db(Path("/fake/video.mp4"))


def test_assert_audio_rms_changed_passes_when_delta_sufficient() -> None:
    """assert_audio_rms_changed passes when abs(measured - baseline) >= threshold."""
    assert_audio_rms_changed(measured_db=-15.0, baseline_db=-21.0, min_delta_db=5.0)


def test_assert_audio_rms_changed_fails_when_delta_insufficient() -> None:
    """assert_audio_rms_changed raises AssertionError when abs(measured - baseline) < threshold."""
    with pytest.raises(AssertionError, match="audio RMS delta"):
        assert_audio_rms_changed(measured_db=-21.0, baseline_db=-21.0, min_delta_db=5.0)
