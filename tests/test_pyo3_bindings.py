"""Integration tests for PyO3 bindings.

Tests the Rust-Python bindings for timeline types, FFmpeg command building,
filter chain construction, and input sanitization.
"""

from __future__ import annotations

import pytest


class TestTimelineTypes:
    """Tests for timeline types (FrameRate, Position, Duration, TimeRange).

    Note: These tests use the actual PyO3 binding API, which differs slightly
    from the Rust API. For example:
    - Position(100) instead of Position.from_frames(100)
    - pos.py_frames (property) instead of pos.frames()
    - Position.from_secs() instead of Position.from_seconds()
    """

    def test_framerate_construction(self) -> None:
        """Test FrameRate construction and properties."""
        from stoat_ferret_core import FrameRate

        rate = FrameRate(24, 1)
        assert rate.py_numerator == 24
        assert rate.py_denominator == 1
        assert rate.fps == 24.0

    def test_framerate_presets(self) -> None:
        """Test FrameRate preset methods."""
        from stoat_ferret_core import FrameRate

        assert FrameRate.fps_24().fps == 24.0
        assert FrameRate.fps_25().fps == 25.0
        assert FrameRate.fps_30().fps == 30.0
        assert FrameRate.fps_60().fps == 60.0
        assert abs(FrameRate.fps_29_97().fps - 29.97) < 0.01
        assert abs(FrameRate.fps_59_94().fps - 59.94) < 0.01

    def test_framerate_invalid_denominator(self) -> None:
        """Test FrameRate rejects zero denominator."""
        from stoat_ferret_core import FrameRate

        with pytest.raises(ValueError):
            FrameRate(24, 0)

    def test_position_from_frames(self) -> None:
        """Test Position construction from frames."""
        from stoat_ferret_core import Position

        pos = Position(100)
        assert pos.py_frames == 100

    def test_position_from_seconds(self) -> None:
        """Test Position construction from seconds."""
        from stoat_ferret_core import FrameRate, Position

        fps = FrameRate.fps_24()
        pos = Position.from_secs(1.0, fps)
        assert pos.py_frames == 24

    def test_position_to_seconds(self) -> None:
        """Test Position conversion to seconds."""
        from stoat_ferret_core import FrameRate, Position

        fps = FrameRate.fps_24()
        pos = Position(48)
        assert pos.as_secs(fps) == 2.0

    def test_position_comparison(self) -> None:
        """Test Position comparison operators."""
        from stoat_ferret_core import Position

        pos1 = Position(10)
        pos2 = Position(20)
        pos3 = Position(10)

        assert pos1 == pos3
        assert pos1 != pos2
        assert pos1 < pos2
        assert pos1 <= pos2
        assert pos2 > pos1
        assert pos2 >= pos1

    def test_duration_from_frames(self) -> None:
        """Test Duration construction from frames."""
        from stoat_ferret_core import Duration

        dur = Duration(100)
        assert dur.py_frames == 100

    def test_duration_between(self) -> None:
        """Test Duration.between_positions for calculating duration between positions."""
        from stoat_ferret_core import Duration, Position

        start = Position(10)
        end = Position(30)
        dur = Duration.between_positions(start, end)
        assert dur.py_frames == 20

    def test_duration_between_invalid(self) -> None:
        """Test Duration.between_positions rejects end before start."""
        from stoat_ferret_core import Duration, Position

        start = Position(30)
        end = Position(10)
        with pytest.raises(ValueError):
            Duration.between_positions(start, end)

    def test_position_add_duration(self) -> None:
        """Test calculating end position from position + duration."""
        from stoat_ferret_core import Duration, Position

        pos = Position(10)
        dur = Duration(5)
        # Use Duration.end_pos method since Position doesn't have __add__
        result = dur.end_pos(pos)
        assert result.py_frames == 15

    def test_timerange_construction(self) -> None:
        """Test TimeRange construction and properties."""
        from stoat_ferret_core import Position, TimeRange

        start = Position(10)
        end = Position(20)
        range_ = TimeRange(start, end)
        assert range_.py_start.py_frames == 10
        assert range_.py_end.py_frames == 20
        assert range_.py_duration.py_frames == 10

    def test_timerange_invalid(self) -> None:
        """Test TimeRange rejects end <= start."""
        from stoat_ferret_core import Position, TimeRange

        start = Position(20)
        end = Position(10)
        with pytest.raises(ValueError):
            TimeRange(start, end)

    def test_timerange_overlaps(self) -> None:
        """Test TimeRange.py_overlaps method."""
        from stoat_ferret_core import Position, TimeRange

        a = TimeRange(Position(0), Position(10))
        b = TimeRange(Position(5), Position(15))
        c = TimeRange(Position(10), Position(20))

        assert a.py_overlaps(b)
        assert not a.py_overlaps(c)  # Adjacent, not overlapping

    def test_timerange_union(self) -> None:
        """Test TimeRange.py_union method."""
        from stoat_ferret_core import Position, TimeRange

        a = TimeRange(Position(0), Position(10))
        b = TimeRange(Position(10), Position(20))
        union = a.py_union(b)
        assert union is not None
        assert union.py_start.py_frames == 0
        assert union.py_end.py_frames == 20


class TestFFmpegCommand:
    """Tests for FFmpegCommand builder."""

    def test_simple_command(self) -> None:
        """Test building a simple FFmpeg command."""
        from stoat_ferret_core import FFmpegCommand

        args = FFmpegCommand().input("input.mp4").output("output.mp4").build()
        assert args == ["-i", "input.mp4", "output.mp4"]

    def test_command_with_options(self) -> None:
        """Test building a command with various options."""
        from stoat_ferret_core import FFmpegCommand

        args = (
            FFmpegCommand()
            .overwrite(True)
            .loglevel("warning")
            .input("input.mp4")
            .seek(5.0)
            .duration(10.0)
            .output("output.mp4")
            .video_codec("libx264")
            .crf(23)
            .preset("fast")
            .build()
        )
        assert "-y" in args
        assert "-loglevel" in args
        assert "-ss" in args
        assert "-t" in args
        assert "-c:v" in args
        assert "-crf" in args
        assert "-preset" in args

    def test_command_with_filter_complex(self) -> None:
        """Test building a command with filter_complex."""
        from stoat_ferret_core import FFmpegCommand

        args = (
            FFmpegCommand()
            .input("input.mp4")
            .filter_complex("[0:v]scale=1280:720[out]")
            .output("output.mp4")
            .map("[out]")
            .build()
        )
        assert "-filter_complex" in args
        assert "[0:v]scale=1280:720[out]" in args
        assert "-map" in args

    def test_command_validation_no_inputs(self) -> None:
        """Test command validation rejects missing inputs."""
        from stoat_ferret_core import FFmpegCommand

        with pytest.raises(ValueError, match="input"):
            FFmpegCommand().output("output.mp4").build()

    def test_command_validation_no_outputs(self) -> None:
        """Test command validation rejects missing outputs."""
        from stoat_ferret_core import FFmpegCommand

        with pytest.raises(ValueError, match="output"):
            FFmpegCommand().input("input.mp4").build()


class TestFilter:
    """Tests for Filter, FilterChain, and FilterGraph."""

    def test_filter_construction(self) -> None:
        """Test Filter construction and string output."""
        from stoat_ferret_core import Filter

        f = Filter("scale").param("w", "1920").param("h", "1080")
        assert str(f) == "scale=w=1920:h=1080"

    def test_filter_scale_static(self) -> None:
        """Test Filter.scale static method."""
        from stoat_ferret_core import Filter

        f = Filter.scale(1920, 1080)
        assert "1920" in str(f)
        assert "1080" in str(f)

    def test_filter_concat_static(self) -> None:
        """Test Filter.concat static method."""
        from stoat_ferret_core import Filter

        f = Filter.concat(3, 1, 1)
        assert "n=3" in str(f)
        assert "v=1" in str(f)
        assert "a=1" in str(f)

    def test_filterchain_construction(self) -> None:
        """Test FilterChain construction and string output."""
        from stoat_ferret_core import Filter, FilterChain

        chain = FilterChain().input("0:v").filter(Filter.scale(1280, 720)).output("scaled")
        result = str(chain)
        assert "[0:v]" in result
        assert "scale" in result
        assert "[scaled]" in result

    def test_filtergraph_construction(self) -> None:
        """Test FilterGraph construction and string output."""
        from stoat_ferret_core import Filter, FilterChain, FilterGraph

        graph = (
            FilterGraph()
            .chain(FilterChain().input("0:v").filter(Filter.scale(1280, 720)).output("v0"))
            .chain(FilterChain().input("1:v").filter(Filter.scale(1280, 720)).output("v1"))
            .chain(
                FilterChain().input("v0").input("v1").filter(Filter.concat(2, 1, 0)).output("outv")
            )
        )
        result = str(graph)
        assert "[0:v]" in result
        assert "[1:v]" in result
        assert "[v0]" in result
        assert "[v1]" in result
        assert "concat" in result
        assert "[outv]" in result
        assert ";" in result  # Chain separator


class TestSanitization:
    """Tests for sanitization functions."""

    def test_escape_filter_text_basic(self) -> None:
        """Test basic text escaping."""
        from stoat_ferret_core import escape_filter_text

        assert escape_filter_text("hello world") == "hello world"
        assert escape_filter_text("test: value") == r"test\: value"
        assert escape_filter_text("[input]") == r"\[input\]"
        assert escape_filter_text("a;b") == r"a\;b"

    def test_escape_filter_text_utf8(self) -> None:
        """Test UTF-8 text is preserved."""
        from stoat_ferret_core import escape_filter_text

        assert escape_filter_text("Hello, 世界!") == "Hello, 世界!"

    def test_validate_path_valid(self) -> None:
        """Test path validation accepts valid paths."""
        from stoat_ferret_core import validate_path

        validate_path("input.mp4")  # Should not raise
        validate_path("/path/to/file.mp4")  # Should not raise
        validate_path("C:\\Users\\file.mp4")  # Should not raise

    def test_validate_path_empty(self) -> None:
        """Test path validation rejects empty paths."""
        from stoat_ferret_core import validate_path

        with pytest.raises(ValueError, match="empty"):
            validate_path("")

    def test_validate_crf_valid(self) -> None:
        """Test CRF validation accepts valid values."""
        from stoat_ferret_core import validate_crf

        assert validate_crf(0) == 0
        assert validate_crf(23) == 23
        assert validate_crf(51) == 51

    def test_validate_crf_invalid(self) -> None:
        """Test CRF validation rejects out-of-range values."""
        from stoat_ferret_core import validate_crf

        with pytest.raises(ValueError, match="range"):
            validate_crf(52)

    def test_validate_speed_valid(self) -> None:
        """Test speed validation accepts valid values."""
        from stoat_ferret_core import validate_speed

        assert validate_speed(0.25) == 0.25
        assert validate_speed(1.0) == 1.0
        assert validate_speed(4.0) == 4.0

    def test_validate_speed_invalid(self) -> None:
        """Test speed validation rejects out-of-range values."""
        from stoat_ferret_core import validate_speed

        with pytest.raises(ValueError, match="range"):
            validate_speed(0.1)
        with pytest.raises(ValueError, match="range"):
            validate_speed(5.0)

    def test_validate_volume_valid(self) -> None:
        """Test volume validation accepts valid values."""
        from stoat_ferret_core import validate_volume

        assert validate_volume(0.0) == 0.0
        assert validate_volume(1.0) == 1.0
        assert validate_volume(10.0) == 10.0

    def test_validate_volume_invalid(self) -> None:
        """Test volume validation rejects out-of-range values."""
        from stoat_ferret_core import validate_volume

        with pytest.raises(ValueError, match="range"):
            validate_volume(-0.1)
        with pytest.raises(ValueError, match="range"):
            validate_volume(11.0)

    def test_validate_video_codec_valid(self) -> None:
        """Test video codec validation accepts valid codecs."""
        from stoat_ferret_core import validate_video_codec

        assert validate_video_codec("libx264") == "libx264"
        assert validate_video_codec("libx265") == "libx265"
        assert validate_video_codec("copy") == "copy"

    def test_validate_video_codec_invalid(self) -> None:
        """Test video codec validation rejects unknown codecs."""
        from stoat_ferret_core import validate_video_codec

        with pytest.raises(ValueError, match="not valid"):
            validate_video_codec("unknown")

    def test_validate_audio_codec_valid(self) -> None:
        """Test audio codec validation accepts valid codecs."""
        from stoat_ferret_core import validate_audio_codec

        assert validate_audio_codec("aac") == "aac"
        assert validate_audio_codec("libopus") == "libopus"
        assert validate_audio_codec("copy") == "copy"

    def test_validate_audio_codec_invalid(self) -> None:
        """Test audio codec validation rejects unknown codecs."""
        from stoat_ferret_core import validate_audio_codec

        with pytest.raises(ValueError, match="not valid"):
            validate_audio_codec("unknown")

    def test_validate_preset_valid(self) -> None:
        """Test preset validation accepts valid presets."""
        from stoat_ferret_core import validate_preset

        assert validate_preset("fast") == "fast"
        assert validate_preset("medium") == "medium"
        assert validate_preset("slow") == "slow"

    def test_validate_preset_invalid(self) -> None:
        """Test preset validation rejects unknown presets."""
        from stoat_ferret_core import validate_preset

        with pytest.raises(ValueError, match="not valid"):
            validate_preset("unknown")


class TestClip:
    """Tests for Clip type."""

    def test_clip_construction(self) -> None:
        """Test Clip construction and properties."""
        from stoat_ferret_core import Clip, Position

        clip = Clip("video.mp4", Position(0), Position(100), None)
        assert clip.source_path == "video.mp4"
        assert clip.in_point.py_frames == 0
        assert clip.out_point.py_frames == 100
        assert clip.source_duration is None

    def test_clip_with_source_duration(self) -> None:
        """Test Clip with source duration."""
        from stoat_ferret_core import Clip, Duration, Position

        clip = Clip("video.mp4", Position(10), Position(50), Duration(200))
        assert clip.source_path == "video.mp4"
        assert clip.in_point.py_frames == 10
        assert clip.out_point.py_frames == 50
        assert clip.source_duration is not None
        assert clip.source_duration.py_frames == 200

    def test_clip_duration(self) -> None:
        """Test Clip.duration() method."""
        from stoat_ferret_core import Clip, Position

        clip = Clip("video.mp4", Position(10), Position(50), None)
        dur = clip.duration()
        assert dur is not None
        assert dur.py_frames == 40

    def test_clip_duration_invalid(self) -> None:
        """Test Clip.duration() returns None for invalid clips."""
        from stoat_ferret_core import Clip, Position

        clip = Clip("video.mp4", Position(100), Position(50), None)
        dur = clip.duration()
        assert dur is None

    def test_clip_repr(self) -> None:
        """Test Clip string representation."""
        from stoat_ferret_core import Clip, Position

        clip = Clip("video.mp4", Position(0), Position(100), None)
        repr_str = repr(clip)
        assert "Clip" in repr_str
        assert "video.mp4" in repr_str


class TestClipValidationError:
    """Tests for ClipValidationError struct (not the exception)."""

    def test_validation_error_basic(self) -> None:
        """Test ClipValidationError construction with field and message only."""
        from stoat_ferret_core import ClipValidationError

        err = ClipValidationError("in_point", "must be non-negative")
        assert err.field == "in_point"
        assert err.message == "must be non-negative"
        assert err.actual is None
        assert err.expected is None

    def test_validation_error_with_values(self) -> None:
        """Test ClipValidationError.with_values_py static method."""
        from stoat_ferret_core import ClipValidationError

        err = ClipValidationError.with_values_py(
            "in_point", "must be before out_point", "100", "< 50"
        )
        assert err.field == "in_point"
        assert err.message == "must be before out_point"
        assert err.actual == "100"
        assert err.expected == "< 50"

    def test_validation_error_str(self) -> None:
        """Test ClipValidationError string representation."""
        from stoat_ferret_core import ClipValidationError

        err = ClipValidationError("field", "message")
        assert "field" in str(err)
        assert "message" in str(err)


class TestClipValidation:
    """Tests for clip validation functions."""

    def test_validate_clip_valid(self) -> None:
        """Test py_validate_clip returns empty list for valid clip."""
        from stoat_ferret_core import Clip, Position, py_validate_clip

        clip = Clip("video.mp4", Position(0), Position(100), None)
        errors = py_validate_clip(clip)
        assert len(errors) == 0

    def test_validate_clip_empty_path(self) -> None:
        """Test py_validate_clip catches empty source path."""
        from stoat_ferret_core import Clip, Position, py_validate_clip

        clip = Clip("", Position(0), Position(100), None)
        errors = py_validate_clip(clip)
        assert len(errors) == 1
        assert errors[0].field == "source_path"
        assert "empty" in errors[0].message.lower()

    def test_validate_clip_out_before_in(self) -> None:
        """Test py_validate_clip catches out_point <= in_point."""
        from stoat_ferret_core import Clip, Position, py_validate_clip

        clip = Clip("video.mp4", Position(100), Position(50), None)
        errors = py_validate_clip(clip)
        assert len(errors) == 1
        assert errors[0].field == "out_point"
        assert errors[0].actual == "50"
        assert errors[0].expected == ">100"

    def test_validate_clip_exceeds_duration(self) -> None:
        """Test py_validate_clip catches points exceeding source duration."""
        from stoat_ferret_core import Clip, Duration, Position, py_validate_clip

        clip = Clip("video.mp4", Position(50), Position(150), Duration(100))
        errors = py_validate_clip(clip)
        assert len(errors) == 1
        assert errors[0].field == "out_point"

    def test_validate_clips_batch(self) -> None:
        """Test py_validate_clips validates multiple clips."""
        from stoat_ferret_core import Clip, Position, py_validate_clips

        clips = [
            Clip("good.mp4", Position(0), Position(100), None),  # Valid
            Clip("", Position(0), Position(100), None),  # Invalid: empty path
            Clip("bad.mp4", Position(100), Position(50), None),  # Invalid: out < in
        ]
        errors = py_validate_clips(clips)
        # Should have errors for clips at index 1 and 2
        indices = [err[0] for err in errors]
        assert 1 in indices
        assert 2 in indices
        assert 0 not in indices


class TestModuleExports:
    """Tests verifying module exports are correct."""

    def test_all_exports_present(self) -> None:
        """Test all expected exports are in __all__."""
        import stoat_ferret_core

        expected = [
            "health_check",
            # Clip types
            "Clip",
            "ClipValidationError",
            "py_validate_clip",
            "py_validate_clips",
            # Timeline types
            "FrameRate",
            "Position",
            "Duration",
            "TimeRange",
            "FFmpegCommand",
            "Filter",
            "FilterChain",
            "FilterGraph",
            "scale_filter",
            "concat_filter",
            "escape_filter_text",
            "validate_path",
            "validate_crf",
            "validate_speed",
            "validate_volume",
            "validate_video_codec",
            "validate_audio_codec",
            "validate_preset",
            "ValidationError",
            "CommandError",
            "SanitizationError",
        ]
        for name in expected:
            assert name in stoat_ferret_core.__all__
            assert hasattr(stoat_ferret_core, name)


class TestExceptions:
    """Tests for custom exception types."""

    def test_validation_error_is_exception(self) -> None:
        """Test ValidationError is an exception type."""
        from stoat_ferret_core import ValidationError

        assert issubclass(ValidationError, Exception)

    def test_command_error_is_exception(self) -> None:
        """Test CommandError is an exception type."""
        from stoat_ferret_core import CommandError

        assert issubclass(CommandError, Exception)

    def test_sanitization_error_is_exception(self) -> None:
        """Test SanitizationError is an exception type."""
        from stoat_ferret_core import SanitizationError

        assert issubclass(SanitizationError, Exception)
