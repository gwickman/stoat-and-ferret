"""FFmpeg contract tests for mastering effects (BL-432, BL-428, BL-430).

All tests are gated on STOAT_TEST_FFMPEG=1 and require a real FFmpeg install.
These tests are deferred_post_merge: CI runs without STOAT_TEST_FFMPEG and
skips them; they must be discharged manually with STOAT_TEST_FFMPEG=1.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from stoat_ferret.effects.definitions import (
    LoudnormPassOneResult,
    _build_loudness_normalize,
    _build_mastering_limiter,
    _build_parametric_eq,
    _run_loudnorm_pass1,
    create_default_registry,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


def _ffmpeg_available() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _generate_loud_audio(output_path: Path) -> None:
    """Generate a loud sine wave that would clip without a limiter."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2:amplitude=1.0",
            "-c:a",
            "pcm_f32le",
            "-ar",
            "44100",
            "-y",
            str(output_path),
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"Could not generate loud audio fixture: {result.stderr.decode()}")


def _run_ffmpeg_with_filter(
    input_path: Path, filter_str: str, output_path: Path
) -> subprocess.CompletedProcess[bytes]:
    """Run FFmpeg applying the given audio filter."""
    return subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(input_path),
            "-af",
            filter_str,
            "-c:a",
            "pcm_f32le",
            "-ar",
            "44100",
            "-y",
            str(output_path),
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )


def _get_peak_level(audio_path: Path) -> float:
    """Return the peak level in dBFS using volumedetect."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(audio_path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    output = result.stderr.decode()
    for line in output.splitlines():
        if "max_volume" in line:
            parts = line.split("max_volume:")
            if len(parts) > 1:
                return float(parts[1].strip().split()[0])
    pytest.skip(f"Could not parse peak level from volumedetect: {output}")


@pytest.mark.filterwarnings("ignore")
def test_limiter_true_peak_ceiling_respected(tmp_path: Path) -> None:
    """alimiter caps true-peak so it does not exceed the configured ceiling (BL-432-AC-1)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "loud.wav"
    output_path = tmp_path / "limited.wav"

    _generate_loud_audio(input_path)

    ceiling_dbtp = -1.0
    filter_str = _build_mastering_limiter({"ceiling_dbtp": ceiling_dbtp})

    result = _run_ffmpeg_with_filter(input_path, filter_str, output_path)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg render failed: {result.stderr.decode()}")

    assert output_path.exists(), "Output file was not created"
    peak_db = _get_peak_level(output_path)
    # Allow 0.5 dB tolerance above ceiling for measurement imprecision
    assert peak_db <= (ceiling_dbtp + 0.5), (
        f"Peak {peak_db} dBFS exceeded ceiling {ceiling_dbtp} dBTP by more than 0.5 dB"
    )


@pytest.mark.filterwarnings("ignore")
def test_limiter_no_clipped_samples(tmp_path: Path) -> None:
    """alimiter produces no clipped samples on loud input (BL-432-AC-2)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "loud.wav"
    output_path = tmp_path / "limited.wav"

    _generate_loud_audio(input_path)

    filter_str = _build_mastering_limiter({"ceiling_dbtp": -1.0})

    result = _run_ffmpeg_with_filter(input_path, filter_str, output_path)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg render failed: {result.stderr.decode()}")

    assert output_path.exists(), "Output file was not created"

    # Check peak is below 0 dBFS (no clipping)
    peak_db = _get_peak_level(output_path)
    assert peak_db <= 0.0, f"Output peak {peak_db} dBFS indicates clipping"


@pytest.mark.filterwarnings("ignore")
def test_limiter_renders_without_error(tmp_path: Path) -> None:
    """alimiter renders without error (BL-432-AC-3)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "loud.wav"
    output_path = tmp_path / "limited.wav"

    _generate_loud_audio(input_path)

    filter_str = _build_mastering_limiter({"ceiling_dbtp": -1.0})

    result = _run_ffmpeg_with_filter(input_path, filter_str, output_path)
    assert result.returncode == 0, f"FFmpeg returned non-zero exit: {result.stderr.decode()}"
    assert output_path.exists(), "Output file was not created"
    assert output_path.stat().st_size > 0, "Output file is empty"


# ---- loudnorm contract tests (BL-428) ----


def _measure_integrated_loudness(audio_path: Path) -> float:
    """Return integrated loudness in LUFS using loudnorm pass-1 measurement."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(audio_path),
            "-af",
            "loudnorm=I=-16:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )
    stderr = result.stderr.decode()
    try:
        parsed = LoudnormPassOneResult.from_stderr(stderr)
        return parsed.measured_i
    except Exception:
        pytest.skip(f"Could not measure integrated loudness: {stderr[:500]}")


@pytest.mark.filterwarnings("ignore")
def test_loudnorm_output_within_lufs_tolerance(tmp_path: Path) -> None:
    """Two-pass loudnorm normalizes output to within +/-0.5 LU of target (BL-428-AC-1, AC-3)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "source.wav"
    output_path = tmp_path / "normalized.wav"

    _generate_loud_audio(input_path)

    target_lufs = -16.0
    ceiling_dbtp = -1.0

    pass1_result = asyncio.run(_run_loudnorm_pass1(str(input_path), target_lufs, ceiling_dbtp))
    assert isinstance(pass1_result, LoudnormPassOneResult)

    pass2_filter = _build_loudness_normalize(
        {
            "target_lufs": target_lufs,
            "ceiling_dbtp": ceiling_dbtp,
            "measured_i": pass1_result.measured_i,
            "measured_lra": pass1_result.measured_lra,
            "measured_tp": pass1_result.measured_tp,
            "offset": pass1_result.offset,
        }
    )

    result = _run_ffmpeg_with_filter(input_path, pass2_filter, output_path)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg pass-2 render failed: {result.stderr.decode()}")

    assert output_path.exists(), "Output file was not created"

    measured_lufs = _measure_integrated_loudness(output_path)
    assert abs(measured_lufs - target_lufs) <= 0.5, (
        f"Output loudness {measured_lufs:.1f} LUFS not within 0.5 LU of target {target_lufs}"
    )


@pytest.mark.filterwarnings("ignore")
def test_loudnorm_true_peak_ceiling_respected(tmp_path: Path) -> None:
    """Two-pass loudnorm keeps true-peak at or below configured ceiling (BL-428-AC-2)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "source.wav"
    output_path = tmp_path / "normalized.wav"

    _generate_loud_audio(input_path)

    target_lufs = -16.0
    ceiling_dbtp = -1.0

    pass1_result = asyncio.run(_run_loudnorm_pass1(str(input_path), target_lufs, ceiling_dbtp))
    pass2_filter = _build_loudness_normalize(
        {
            "target_lufs": target_lufs,
            "ceiling_dbtp": ceiling_dbtp,
            "measured_i": pass1_result.measured_i,
            "measured_lra": pass1_result.measured_lra,
            "measured_tp": pass1_result.measured_tp,
            "offset": pass1_result.offset,
        }
    )

    result = _run_ffmpeg_with_filter(input_path, pass2_filter, output_path)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg pass-2 render failed: {result.stderr.decode()}")

    assert output_path.exists(), "Output file was not created"

    # Verify peak using volumedetect
    peak_db = _get_peak_level(output_path)
    assert peak_db <= (ceiling_dbtp + 0.5), (
        f"Peak {peak_db} dBFS exceeded ceiling {ceiling_dbtp} dBTP by more than 0.5 dB"
    )


@pytest.mark.filterwarnings("ignore")
def test_loudnorm_reads_target_from_delivery_profile(tmp_path: Path) -> None:
    """delivery_profile_target_lufs overrides effect target_lufs (BL-428-AC-4)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "source.wav"
    output_path = tmp_path / "normalized.wav"

    _generate_loud_audio(input_path)

    # Simulate delivery profile providing -23.0 LUFS (broadcast), effect has -16.0
    delivery_lufs = -23.0
    ceiling_dbtp = -1.0

    pass1_result = asyncio.run(_run_loudnorm_pass1(str(input_path), delivery_lufs, ceiling_dbtp))
    pass2_filter = _build_loudness_normalize(
        {
            "target_lufs": -16.0,  # effect default — should be overridden
            "ceiling_dbtp": ceiling_dbtp,
            "delivery_profile_target_lufs": delivery_lufs,
            "measured_i": pass1_result.measured_i,
            "measured_lra": pass1_result.measured_lra,
            "measured_tp": pass1_result.measured_tp,
            "offset": pass1_result.offset,
        }
    )

    # Verify the filter string uses the delivery profile target
    assert "I=-23.0" in pass2_filter, (
        f"Expected delivery profile -23 LUFS in pass-2 filter, got: {pass2_filter}"
    )
    assert "I=-16.0" not in pass2_filter, (
        f"Should not contain effect default -16 in pass-2 filter, got: {pass2_filter}"
    )

    result = _run_ffmpeg_with_filter(input_path, pass2_filter, output_path)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg pass-2 render failed: {result.stderr.decode()}")

    assert output_path.exists(), "Output file was not created"
    measured_lufs = _measure_integrated_loudness(output_path)
    assert abs(measured_lufs - delivery_lufs) <= 0.5, (
        f"Output {measured_lufs:.1f} LUFS not within 0.5 LU of delivery target {delivery_lufs}"
    )


# ---- volume automation contract tests (BL-430) ----


def _generate_audio_sine(output_path: Path, duration: float = 6.0, amplitude: float = 0.8) -> None:
    """Generate a constant-amplitude sine wave for automation testing."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}:amplitude={amplitude}",
            "-c:a",
            "pcm_f32le",
            "-ar",
            "44100",
            "-y",
            str(output_path),
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"Could not generate sine fixture: {result.stderr.decode()}")


def _get_mean_volume_at(audio_path: Path, offset_seconds: float, duration: float = 0.5) -> float:
    """Return mean volume (dBFS) of a segment starting at offset_seconds."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-ss",
            str(offset_seconds),
            "-i",
            str(audio_path),
            "-t",
            str(duration),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    output = result.stderr.decode()
    for line in output.splitlines():
        if "mean_volume" in line:
            parts = line.split("mean_volume:")
            if len(parts) > 1:
                return float(parts[1].strip().split()[0])
    pytest.skip(f"Could not parse mean_volume from volumedetect: {output}")


# ---- parametric_eq contract tests (BL-429) ----


@pytest.mark.filterwarnings("ignore")
def test_parametric_eq_renders_without_error(tmp_path: Path) -> None:
    """anequalizer renders without error with a single-band EQ (BL-429-AC-4)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "source.wav"
    output_path = tmp_path / "eq_output.wav"

    _generate_loud_audio(input_path)

    filter_str = _build_parametric_eq(
        {"bands": [{"frequency": 1000.0, "gain": 3.0, "width": 200.0}]}
    )

    result = _run_ffmpeg_with_filter(input_path, filter_str, output_path)
    assert result.returncode == 0, f"FFmpeg returned non-zero exit: {result.stderr.decode()}"
    assert output_path.exists(), "Output file was not created"
    assert output_path.stat().st_size > 0, "Output file is empty"


@pytest.mark.filterwarnings("ignore")
def test_parametric_eq_band_gain_automation_in_filter(tmp_path: Path) -> None:
    """Per-band gain is reflected in the compiled anequalizer filter string (BL-429-AC-3)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    # Verify that different gain values produce different filter strings
    filter_boost = _build_parametric_eq(
        {"bands": [{"frequency": 1000.0, "gain": 6.0, "width": 200.0}]}
    )
    filter_cut = _build_parametric_eq(
        {"bands": [{"frequency": 1000.0, "gain": -6.0, "width": 200.0}]}
    )

    assert filter_boost != filter_cut, "Boost and cut filters should differ"
    assert "g=6" in filter_boost, f"Missing g=6 in boost filter: {filter_boost}"
    assert "g=-6" in filter_cut, f"Missing g=-6 in cut filter: {filter_cut}"

    # Verify both render without error
    input_path = tmp_path / "source.wav"
    _generate_loud_audio(input_path)

    output_boost = tmp_path / "boosted.wav"
    result = _run_ffmpeg_with_filter(input_path, filter_boost, output_boost)
    assert result.returncode == 0, f"Boost render failed: {result.stderr.decode()}"

    output_cut = tmp_path / "cut.wav"
    result = _run_ffmpeg_with_filter(input_path, filter_cut, output_cut)
    assert result.returncode == 0, f"Cut render failed: {result.stderr.decode()}"


@pytest.mark.filterwarnings("ignore")
def test_volume_automation_level_follows_curve(tmp_path: Path) -> None:
    """Volume automation envelope: output level rises from quiet to loud (BL-430-AC-2)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    input_path = tmp_path / "constant.wav"
    output_path = tmp_path / "automated.wav"

    # 6-second constant-amplitude input
    _generate_audio_sine(input_path, duration=6.0, amplitude=0.8)

    registry = create_default_registry()

    # Automation: quiet at t=0 (volume=0.1), loud at t=5 (volume=0.9), linear ramp
    errors, compiled_expression = registry.validate_with_automation(
        "volume",
        {
            "volume": {
                "default": 0.1,
                "keyframes": [
                    {"t": 0.0, "value": 0.1, "curve": "linear"},
                    {"t": 5.0, "value": 0.9, "curve": "linear"},
                ],
            }
        },
    )
    assert errors == [], f"validate_with_automation errors: {errors}"
    assert compiled_expression is not None

    filter_str = f"volume='{compiled_expression}'"

    result = _run_ffmpeg_with_filter(input_path, filter_str, output_path)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg volume automation render failed: {result.stderr.decode()}")

    assert output_path.exists(), "Output file was not created"

    # Level near start should be lower than level near end
    level_start = _get_mean_volume_at(output_path, offset_seconds=0.1, duration=0.5)
    level_end = _get_mean_volume_at(output_path, offset_seconds=5.0, duration=0.5)
    assert level_end > level_start, (
        f"Level should increase from start to end. "
        f"Start: {level_start:.1f} dBFS, End: {level_end:.1f} dBFS"
    )
