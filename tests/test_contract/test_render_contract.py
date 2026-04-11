"""Contract tests for render output format and encoder detection.

Validates that render commands produce valid output files in all 4 supported
formats (mp4, webm, mov, mkv) using real FFmpeg execution with lavfi virtual
inputs (LRN-100), and that the encoder detection parser correctly identifies
software encoders from real FFmpeg output.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.executor import RealFFmpegExecutor
from stoat_ferret_core import detect_hardware_encoders
from tests.conftest import requires_ffmpeg


@pytest.fixture(scope="session")
def ffmpeg_encoder_output() -> str:
    """Capture real ``ffmpeg -encoders`` output once per test session.

    Used by encoder detection contract tests to avoid re-running FFmpeg for
    each test method and to provide a stable snapshot for regression comparison.

    Returns:
        The raw stdout from ``ffmpeg -encoders``.
    """
    result = subprocess.run(
        ["ffmpeg", "-encoders"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.stdout


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


@requires_ffmpeg
@pytest.mark.contract
class TestEncoderDetectionContract:
    """Encoder detection parser correctly identifies encoders from real FFmpeg output.

    Stage 1 tests use the ``ffmpeg_encoder_output`` session fixture to validate
    the parser against the host's actual FFmpeg installation. Stage 2 tests use
    synthetic input to validate specific edge cases in the parser.
    """

    def test_software_encoders_detected(self, ffmpeg_encoder_output: str) -> None:
        """Real ``ffmpeg -encoders`` output contains expected software encoders.

        FR-001, FR-002, FR-003: Runs ``ffmpeg -encoders``, parses via
        ``detect_hardware_encoders``, and asserts libx264, libx265, and
        libvpx-vp9 are in the results.
        """
        encoders = detect_hardware_encoders(ffmpeg_encoder_output)
        names = {enc.name for enc in encoders}

        assert "libx264" in names, f"libx264 not found in detected encoders: {sorted(names)}"
        assert "libx265" in names, f"libx265 not found in detected encoders: {sorted(names)}"
        assert "libvpx-vp9" in names, f"libvpx-vp9 not found in detected encoders: {sorted(names)}"

    def test_encoder_output_captured_for_regression(self, ffmpeg_encoder_output: str) -> None:
        """Captured ``ffmpeg -encoders`` output is non-empty and yields parseable results.

        FR-004: The session fixture stores the captured output; this test asserts the
        snapshot is non-empty so any future format change that breaks parsing is detected.
        """
        assert len(ffmpeg_encoder_output) > 0, (
            "ffmpeg -encoders produced no stdout — output may have gone to stderr"
        )
        encoders = detect_hardware_encoders(ffmpeg_encoder_output)
        assert len(encoders) > 0, (
            "detect_hardware_encoders returned no video encoders from real FFmpeg output"
        )

    def test_audio_only_lines_filtered(self) -> None:
        """Audio encoder lines (``A`` type flag) are excluded from detection results.

        FR-005: Edge case — the ``A`` type flag must be filtered; only ``V`` lines
        are returned.
        """
        synthetic = (
            "Encoders:\n"
            " V..... = Video\n"
            " A..... = Audio\n"
            " ------\n"
            " A..... aac                  AAC (Advanced Audio Coding)\n"
            " A..... mp3lame              libmp3lame MP3 (MPEG audio layer 3)\n"
            " VFS... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10\n"
        )
        encoders = detect_hardware_encoders(synthetic)
        names = [enc.name for enc in encoders]

        assert "aac" not in names, "Audio encoder 'aac' should be filtered out (A flag)"
        assert "mp3lame" not in names, "Audio encoder 'mp3lame' should be filtered out (A flag)"
        assert "libx264" in names, "Video encoder 'libx264' should be included (V flag)"

    def test_optional_codec_suffix_extracted(self) -> None:
        """Encoder with ``(codec xxx)`` suffix uses extracted codec, not encoder name.

        FR-005: Edge case — when ``(codec xxx)`` is present, the codec field must be
        the extracted value; when absent, the encoder name is used as the codec.
        """
        synthetic = (
            "Encoders:\n"
            " ------\n"
            " V..... h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)\n"
            " VFS... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10\n"
        )
        encoders = detect_hardware_encoders(synthetic)
        by_name = {enc.name: enc for enc in encoders}

        assert "h264_nvenc" in by_name, "h264_nvenc should be detected"
        assert by_name["h264_nvenc"].codec == "h264", (
            f"Expected codec 'h264' for h264_nvenc (from suffix), "
            f"got '{by_name['h264_nvenc'].codec}'"
        )

        assert "libx264" in by_name, "libx264 should be detected"
        assert by_name["libx264"].codec == "libx264", (
            f"Expected codec 'libx264' for libx264 (no suffix, falls back to name), "
            f"got '{by_name['libx264'].codec}'"
        )

    def test_varying_flag_positions_parsed(self) -> None:
        """Encoders with varying flag combinations are all correctly parsed.

        FR-005: Edge case — flag slots 2-6 (F, S, X, B, D) may be set or unset
        in any combination; the parser must handle all variants.
        """
        synthetic = (
            "Encoders:\n"
            " ------\n"
            # Minimal flags (no optional capabilities)
            " V..... av1_amf              AMD AMF AV1 encoder (codec av1)\n"
            # Frame-level multithreading only
            " VF.... h264_amf             AMD AMF H.264 encoder (codec h264)\n"
            # Frame + slice multithreading
            " VFS... libx265              libx265 H.265 / HEVC\n"
            # All six flags set
            " VFSXBD libvpx-vp9           libvpx VP9\n"
        )
        encoders = detect_hardware_encoders(synthetic)
        by_name = {enc.name: enc for enc in encoders}

        assert "av1_amf" in by_name, "Encoder with minimal flags (V.....) should be parsed"
        assert "h264_amf" in by_name, "Encoder with F flag (VF....) should be parsed"
        assert "libx265" in by_name, "Encoder with FS flags (VFS...) should be parsed"
        assert "libvpx-vp9" in by_name, "Encoder with all flags (VFSXBD) should be parsed"

        # Hardware classification: AMF suffix → hardware; lib prefix → software
        assert by_name["h264_amf"].is_hardware is True, (
            "h264_amf should be classified as hardware (AMF suffix)"
        )
        assert by_name["libx265"].is_hardware is False, (
            "libx265 should be classified as software (no hardware suffix)"
        )
