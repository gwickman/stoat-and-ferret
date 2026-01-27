"""Tests for the ffprobe wrapper module."""

from __future__ import annotations

from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.probe import FFprobeError, VideoMetadata, ffprobe_video
from tests.conftest import requires_ffprobe


class TestVideoMetadata:
    """Tests for VideoMetadata dataclass."""

    def test_frame_rate_property(self) -> None:
        """Test frame_rate returns tuple of numerator and denominator."""
        metadata = VideoMetadata(
            duration_seconds=1.0,
            width=320,
            height=240,
            frame_rate_numerator=24,
            frame_rate_denominator=1,
            video_codec="h264",
            audio_codec="aac",
            file_size=1000,
        )
        assert metadata.frame_rate == (24, 1)

    def test_frame_rate_property_ntsc(self) -> None:
        """Test frame_rate with NTSC values (30000/1001)."""
        metadata = VideoMetadata(
            duration_seconds=1.0,
            width=320,
            height=240,
            frame_rate_numerator=30000,
            frame_rate_denominator=1001,
            video_codec="h264",
            audio_codec="aac",
            file_size=1000,
        )
        assert metadata.frame_rate == (30000, 1001)

    def test_duration_frames_computed(self) -> None:
        """Test duration_frames is computed from duration_seconds and frame_rate."""
        metadata = VideoMetadata(
            duration_seconds=1.0,
            width=320,
            height=240,
            frame_rate_numerator=24,
            frame_rate_denominator=1,
            video_codec="h264",
            audio_codec="aac",
            file_size=1000,
        )
        assert metadata.duration_frames == 24

    def test_duration_frames_with_fractional(self) -> None:
        """Test duration_frames handles fractional seconds."""
        metadata = VideoMetadata(
            duration_seconds=2.5,
            width=320,
            height=240,
            frame_rate_numerator=30,
            frame_rate_denominator=1,
            video_codec="h264",
            audio_codec=None,
            file_size=1000,
        )
        # 2.5 seconds * 30 fps = 75 frames
        assert metadata.duration_frames == 75

    def test_audio_codec_optional(self) -> None:
        """Test audio_codec can be None for video-only files."""
        metadata = VideoMetadata(
            duration_seconds=1.0,
            width=320,
            height=240,
            frame_rate_numerator=24,
            frame_rate_denominator=1,
            video_codec="h264",
            audio_codec=None,
            file_size=1000,
        )
        assert metadata.audio_codec is None


@requires_ffprobe
class TestFFprobeVideoContract:
    """Contract tests for ffprobe_video with real ffprobe.

    These tests require ffprobe to be installed and verify the integration
    with the actual ffprobe binary.
    """

    def test_ffprobe_video_success(self, sample_video_path: Path) -> None:
        """Test ffprobe_video returns correct metadata for a sample video."""
        metadata = ffprobe_video(str(sample_video_path))

        assert metadata.width == 320
        assert metadata.height == 240
        assert metadata.frame_rate_numerator == 24
        assert metadata.frame_rate_denominator == 1
        # Duration should be approximately 1 second
        assert 0.9 <= metadata.duration_seconds <= 1.1
        assert metadata.video_codec == "h264"
        assert metadata.audio_codec == "aac"
        assert metadata.file_size > 0

    def test_ffprobe_video_no_audio(self, video_only_path: Path) -> None:
        """Test ffprobe_video handles video without audio stream."""
        metadata = ffprobe_video(str(video_only_path))

        assert metadata.width == 320
        assert metadata.height == 240
        assert metadata.video_codec == "h264"
        assert metadata.audio_codec is None

    def test_ffprobe_video_duration_frames(self, sample_video_path: Path) -> None:
        """Test duration_frames is correctly computed."""
        metadata = ffprobe_video(str(sample_video_path))

        # 1 second at 24 fps should be approximately 24 frames
        assert 20 <= metadata.duration_frames <= 28


class TestFFprobeVideoErrors:
    """Tests for ffprobe_video error handling."""

    def test_file_not_found(self) -> None:
        """Test FileNotFoundError raised for non-existent file."""
        with pytest.raises(FileNotFoundError, match="not found"):
            ffprobe_video("/nonexistent/path/to/video.mp4")

    def test_ffprobe_not_installed(self, tmp_path: Path) -> None:
        """Test FFprobeError raised when ffprobe binary not found."""
        # Create a file to avoid FileNotFoundError
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"not a real video")

        with pytest.raises(FFprobeError, match="ffprobe not found"):
            ffprobe_video(str(video_file), ffprobe_path="/nonexistent/ffprobe")

    @requires_ffprobe
    def test_not_a_video_file(self, tmp_path: Path) -> None:
        """Test ValueError raised for non-video file."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("this is not a video file")

        with pytest.raises((ValueError, FFprobeError)):
            ffprobe_video(str(text_file))

    @requires_ffprobe
    def test_empty_file(self, tmp_path: Path) -> None:
        """Test error handling for empty file."""
        empty_file = tmp_path / "empty.mp4"
        empty_file.write_bytes(b"")

        with pytest.raises((ValueError, FFprobeError)):
            ffprobe_video(str(empty_file))


class TestFFprobeExports:
    """Tests for module exports."""

    def test_exports_from_ffmpeg_package(self) -> None:
        """Test that ffmpeg package exports the expected symbols."""
        from stoat_ferret.ffmpeg import FFprobeError, VideoMetadata, ffprobe_video

        assert FFprobeError is not None
        assert VideoMetadata is not None
        assert ffprobe_video is not None
        assert callable(ffprobe_video)

    def test_ffprobe_error_is_exception(self) -> None:
        """Test FFprobeError is an exception type."""
        assert issubclass(FFprobeError, Exception)
