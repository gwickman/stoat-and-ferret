"""Contract tests for render output format commands.

Validates that render commands produce valid output files in all 4 supported
formats (mp4, webm, mov, mkv) using real FFmpeg execution with lavfi virtual
inputs (LRN-100).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.executor import RealFFmpegExecutor
from tests.conftest import requires_ffmpeg


def _run_ffprobe(output_path: Path) -> dict:
    """Run ffprobe on the output file and return parsed JSON.

    Args:
        output_path: Path to the file to probe.

    Returns:
        Parsed ffprobe JSON output with format and streams keys.

    Raises:
        pytest.skip.Exception: If ffprobe is not available.
    """
    if shutil.which("ffprobe") is None:
        pytest.skip("ffprobe not available — skipping codec/container validation")
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(output_path),
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert probe.returncode == 0, (
        f"ffprobe failed: {probe.stderr.decode('utf-8', errors='replace')}"
    )
    return json.loads(probe.stdout)  # type: ignore[no-any-return]


@requires_ffmpeg
@pytest.mark.contract
class TestRenderOutputFormatContract:
    """Render commands produce valid output files in all 4 supported formats."""

    @pytest.mark.parametrize(
        "output_ext,video_codec,format_flag,expected_codec,expected_format",
        [
            ("mp4", "libx264", "mp4", "h264", "mp4"),
            ("webm", "libvpx-vp9", "webm", "vp9", "webm"),
            ("mov", "libx264", "mov", "h264", "mov"),
            ("mkv", "libx265", "matroska", "hevc", "matroska"),
        ],
        ids=["mp4", "webm", "mov", "mkv"],
    )
    def test_render_format_produces_valid_output(
        self,
        tmp_path: Path,
        output_ext: str,
        video_codec: str,
        format_flag: str,
        expected_codec: str,
        expected_format: str,
    ) -> None:
        """Render command produces a valid file with correct codec and container.

        Uses lavfi testsrc2 virtual input to avoid requiring real media files.
        Validates the output via ffprobe for codec name and container format.
        """
        output_path = tmp_path / f"output.{output_ext}"

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc2=duration=1:size=320x240:rate=24",
                "-c:v",
                video_codec,
                "-an",
                "-t",
                "1",
                "-f",
                format_flag,
                "-y",
                str(output_path),
            ],
            timeout=30,
        )

        assert result.returncode == 0, (
            f"FFmpeg render failed for {output_ext} ({video_codec}): "
            f"{result.stderr.decode('utf-8', errors='replace')}"
        )
        assert output_path.exists(), f"Output file not created for {output_ext}"
        assert output_path.stat().st_size > 0, f"Output file is empty for {output_ext}"

        probe_data = _run_ffprobe(output_path)

        # Validate container format — ffprobe returns comma-separated format names
        format_name = probe_data.get("format", {}).get("format_name", "")
        format_names = format_name.split(",")
        assert expected_format in format_names, (
            f"Expected format '{expected_format}' in ffprobe "
            f"format_name '{format_name}' for {output_ext}"
        )

        # Validate video codec
        video_streams = [s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"]
        assert len(video_streams) >= 1, f"No video streams found in {output_ext} output"
        codec_name = video_streams[0].get("codec_name", "")
        assert codec_name == expected_codec, (
            f"Expected video codec '{expected_codec}', got '{codec_name}' in {output_ext}"
        )


@requires_ffmpeg
@pytest.mark.contract
class TestRenderEdgeCases:
    """Edge case validation for render command behaviour."""

    def test_unavailable_codec_fails(self, tmp_path: Path) -> None:
        """FFmpeg returns non-zero when a nonexistent video codec is requested."""
        output_path = tmp_path / "bad_codec.mp4"

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc2=duration=1:size=320x240:rate=24",
                "-c:v",
                "nonexistent_codec_xyz_abc",
                "-an",
                "-f",
                "mp4",
                "-y",
                str(output_path),
            ],
            timeout=10,
        )

        assert result.returncode != 0, (
            "Expected FFmpeg to fail with a nonexistent codec, but it succeeded"
        )

    def test_zero_duration_produces_no_video_frames(self, tmp_path: Path) -> None:
        """A zero-duration render produces a container with no encoded video frames.

        FFmpeg exits successfully but logs "Output file is empty, nothing was encoded"
        and writes only a minimal container stub (~261 bytes on this platform).
        """
        output_path = tmp_path / "zero_dur.mp4"

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc2=duration=0:size=320x240:rate=24",
                "-c:v",
                "libx264",
                "-an",
                "-f",
                "mp4",
                "-y",
                str(output_path),
            ],
            timeout=10,
        )

        if result.returncode != 0:
            return  # FFmpeg rejected the zero-duration input outright — acceptable

        # FFmpeg succeeded but must have produced no usable video content.
        # The output is either absent or a minimal container stub with 0 frames.
        if not output_path.exists():
            return  # No output file created — acceptable

        if shutil.which("ffprobe") is None:
            # Without ffprobe, verify the file is tiny (header-only container)
            assert output_path.stat().st_size < 1024, (
                f"Zero-duration render produced unexpectedly large output: "
                f"{output_path.stat().st_size} bytes"
            )
            return

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                str(output_path),
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
        if probe.returncode == 0:
            data = json.loads(probe.stdout)
            video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
            total_frames = sum(int(s.get("nb_frames", 0) or 0) for s in video_streams)
            assert total_frames == 0, (
                f"Expected 0 video frames for zero-duration render, got {total_frames}"
            )
