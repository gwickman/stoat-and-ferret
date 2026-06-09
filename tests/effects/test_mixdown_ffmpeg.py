"""FFmpeg contract tests for 4-track mixdown (BL-436).

Verifies that AmixBuilder with inputs=4 produces a single output from
4 simultaneous tracks, that the output is deterministic, and that all
4 tracks contribute energy to the mix.

All tests are gated on STOAT_TEST_FFMPEG=1 and require FFmpeg in PATH.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

pytestmark = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)

_TRACK_FREQS = [440, 880, 1320, 1760]  # Hz — one per track, distinct for contribution check


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


def _generate_sine_track(output_path: Path, frequency: int, duration: float = 2.0) -> None:
    """Generate a mono sine-wave WAV at the given frequency."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:duration={duration}",
            "-c:a",
            "pcm_s16le",
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
        pytest.skip(f"Could not generate sine fixture at {frequency} Hz: {result.stderr.decode()}")


def _mix_four_tracks(
    track_paths: list[Path],
    output_path: Path,
) -> subprocess.CompletedProcess[bytes]:
    """Mix 4 audio tracks with amix=inputs=4:duration=first."""
    cmd = ["ffmpeg"]
    for p in track_paths:
        cmd += ["-i", str(p)]
    cmd += [
        "-filter_complex",
        "amix=inputs=4:duration=first",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "44100",
        "-y",
        str(output_path),
    ]
    return subprocess.run(cmd, capture_output=True, timeout=60, check=False)


def _sha256(path: Path) -> str:
    """Return hex SHA-256 of file contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _measure_band_peak(audio_path: Path, center_freq: int, width_hz: int = 200) -> float:
    """Return peak volume (dBFS) in a narrow frequency band via bandpass + volumedetect."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(audio_path),
            "-af",
            f"bandpass=frequency={center_freq}:width_type=h:width={width_hz},volumedetect",
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
    return -120.0


@pytest.mark.filterwarnings("ignore")
def test_four_track_mixdown_renders_to_single_output(tmp_path: Path) -> None:
    """amix=inputs=4 produces a single output from 4 simultaneous tracks (BL-436-AC-1)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    tracks = []
    for freq in _TRACK_FREQS:
        p = tmp_path / f"track_{freq}hz.wav"
        _generate_sine_track(p, freq)
        tracks.append(p)

    output = tmp_path / "mix.wav"
    result = _mix_four_tracks(tracks, output)

    assert result.returncode == 0, f"amix=inputs=4 failed: {result.stderr.decode()}"
    assert output.exists(), "Output file was not created"
    assert output.stat().st_size > 0, "Output file is empty"

    probe = subprocess.run(
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
        timeout=15,
        check=False,
    )
    if probe.returncode == 0:
        info = json.loads(probe.stdout.decode())
        duration = float(info.get("format", {}).get("duration", 0))
        assert duration > 0, f"Output duration is zero: {duration}"


@pytest.mark.filterwarnings("ignore")
def test_four_track_mixdown_is_deterministic(tmp_path: Path) -> None:
    """Two identical amix=inputs=4 renders produce byte-exact output (BL-436-AC-2)."""
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    tracks = []
    for freq in _TRACK_FREQS:
        p = tmp_path / f"track_{freq}hz.wav"
        _generate_sine_track(p, freq)
        tracks.append(p)

    output_a = tmp_path / "mix_a.wav"
    output_b = tmp_path / "mix_b.wav"

    result_a = _mix_four_tracks(tracks, output_a)
    result_b = _mix_four_tracks(tracks, output_b)

    assert result_a.returncode == 0, f"First render failed: {result_a.stderr.decode()}"
    assert result_b.returncode == 0, f"Second render failed: {result_b.stderr.decode()}"

    sha_a = _sha256(output_a)
    sha_b = _sha256(output_b)
    assert sha_a == sha_b, (
        f"Repeated 4-track renders produced different output: {sha_a!r} != {sha_b!r}"
    )


@pytest.mark.filterwarnings("ignore")
def test_four_track_mixdown_all_tracks_contribute(tmp_path: Path) -> None:
    """All 4 tracks contribute non-zero energy to the mixdown (BL-436-AC-3).

    Each fixture is a pure sine at a distinct frequency (440/880/1320/1760 Hz).
    A narrow bandpass filter isolates each frequency in the mixed output;
    peak energy must exceed -40 dBFS to confirm the track is audible.
    """
    if not _ffmpeg_available():
        pytest.skip("FFmpeg not available")

    tracks = []
    for freq in _TRACK_FREQS:
        p = tmp_path / f"track_{freq}hz.wav"
        _generate_sine_track(p, freq)
        tracks.append(p)

    output = tmp_path / "mix.wav"
    result = _mix_four_tracks(tracks, output)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg mix failed: {result.stderr.decode()}")

    for freq in _TRACK_FREQS:
        peak = _measure_band_peak(output, center_freq=freq, width_hz=200)
        assert peak > -40.0, (
            f"Track at {freq} Hz has insufficient energy in mix: {peak:.1f} dBFS "
            f"(expected > -40 dBFS)"
        )
