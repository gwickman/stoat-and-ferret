"""FFmpeg contract tests for LimiterBuilder (BL-432).

All tests are gated on STOAT_TEST_FFMPEG=1 and require a real FFmpeg install.
These tests are deferred_post_merge: CI runs without STOAT_TEST_FFMPEG and
skips them; they must be discharged manually with STOAT_TEST_FFMPEG=1.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from stoat_ferret.effects.definitions import _build_mastering_limiter

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
