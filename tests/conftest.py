"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _ffmpeg_available() -> bool:
    """Check if ffmpeg is available in PATH."""
    return shutil.which("ffmpeg") is not None


def _ffprobe_available() -> bool:
    """Check if ffprobe is available in PATH."""
    return shutil.which("ffprobe") is not None


# Skip markers
requires_ffmpeg = pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
requires_ffprobe = pytest.mark.skipif(not _ffprobe_available(), reason="ffprobe not available")


@pytest.fixture(scope="session")
def sample_video_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a sample video file for testing.

    Creates a 1-second 320x240 video at 24fps with H.264 video and AAC audio.
    The fixture is session-scoped and generates the video once per test run.

    Returns:
        Path to the generated sample.mp4 file.

    Raises:
        pytest.skip: If ffmpeg is not available.
    """
    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available - cannot generate test video")

    fixtures_dir = tmp_path_factory.mktemp("fixtures")
    sample_path = fixtures_dir / "sample.mp4"

    # Generate a 1-second test video with video and audio streams
    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-y",
            str(sample_path),
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        pytest.skip(f"ffmpeg failed to generate test video: {result.stderr.decode()}")

    return sample_path


@pytest.fixture(scope="session")
def video_only_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a video file without audio for testing.

    Creates a 1-second 320x240 video at 24fps with H.264 video only (no audio).

    Returns:
        Path to the generated video_only.mp4 file.

    Raises:
        pytest.skip: If ffmpeg is not available.
    """
    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available - cannot generate test video")

    fixtures_dir = tmp_path_factory.mktemp("fixtures_video_only")
    video_path = fixtures_dir / "video_only.mp4"

    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=24",
            "-c:v",
            "libx264",
            "-an",  # No audio
            "-y",
            str(video_path),
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        pytest.skip(f"ffmpeg failed to generate test video: {result.stderr.decode()}")

    return video_path
