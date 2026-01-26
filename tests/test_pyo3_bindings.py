"""Integration tests for PyO3 bindings.

Tests the Rust-Python bindings for timeline types, FFmpeg command building,
filter chain construction, and input sanitization.
"""

from __future__ import annotations

import pytest


class TestTimelineTypes:
    """Tests for timeline types (FrameRate, Position, Duration, TimeRange)."""

    def test_framerate_construction(self) -> None:
        """Test FrameRate construction and properties."""
        from stoat_ferret_core import FrameRate

        rate = FrameRate(24, 1)
        assert rate.numerator == 24
        assert rate.denominator == 1
        assert rate.as_float() == 24.0

    def test_framerate_presets(self) -> None:
        """Test FrameRate preset methods."""
        from stoat_ferret_core import FrameRate

        assert FrameRate.fps_24().as_float() == 24.0
        assert FrameRate.fps_25().as_float() == 25.0
        assert FrameRate.fps_30().as_float() == 30.0
        assert FrameRate.fps_60().as_float() == 60.0
        assert abs(FrameRate.ntsc_30().as_float() - 29.97) < 0.01
        assert abs(FrameRate.ntsc_60().as_float() - 59.94) < 0.01

    def test_framerate_invalid_denominator(self) -> None:
        """Test FrameRate rejects zero denominator."""
        from stoat_ferret_core import FrameRate

        with pytest.raises(ValueError):
            FrameRate(24, 0)

    def test_position_from_frames(self) -> None:
        """Test Position construction from frames."""
        from stoat_ferret_core import Position

        pos = Position.from_frames(100)
        assert pos.frames() == 100

    def test_position_from_seconds(self) -> None:
        """Test Position construction from seconds."""
        from stoat_ferret_core import FrameRate, Position

        fps = FrameRate.fps_24()
        pos = Position.from_seconds(1.0, fps)
        assert pos.frames() == 24

    def test_position_to_seconds(self) -> None:
        """Test Position conversion to seconds."""
        from stoat_ferret_core import FrameRate, Position

        fps = FrameRate.fps_24()
        pos = Position.from_frames(48)
        assert pos.to_seconds(fps) == 2.0

    def test_position_comparison(self) -> None:
        """Test Position comparison operators."""
        from stoat_ferret_core import Position

        pos1 = Position.from_frames(10)
        pos2 = Position.from_frames(20)
        pos3 = Position.from_frames(10)

        assert pos1 == pos3
        assert pos1 != pos2
        assert pos1 < pos2
        assert pos1 <= pos2
        assert pos2 > pos1
        assert pos2 >= pos1

    def test_duration_from_frames(self) -> None:
        """Test Duration construction from frames."""
        from stoat_ferret_core import Duration

        dur = Duration.from_frames(100)
        assert dur.frames() == 100

    def test_duration_between(self) -> None:
        """Test Duration.between for calculating duration between positions."""
        from stoat_ferret_core import Duration, Position

        start = Position.from_frames(10)
        end = Position.from_frames(30)
        dur = Duration.between(start, end)
        assert dur.frames() == 20

    def test_duration_between_invalid(self) -> None:
        """Test Duration.between rejects end before start."""
        from stoat_ferret_core import Duration, Position

        start = Position.from_frames(30)
        end = Position.from_frames(10)
        with pytest.raises(ValueError):
            Duration.between(start, end)

    def test_position_add_duration(self) -> None:
        """Test adding Duration to Position."""
        from stoat_ferret_core import Duration, Position

        pos = Position.from_frames(10)
        dur = Duration.from_frames(5)
        result = pos + dur
        assert result.frames() == 15

    def test_timerange_construction(self) -> None:
        """Test TimeRange construction and properties."""
        from stoat_ferret_core import Position, TimeRange

        start = Position.from_frames(10)
        end = Position.from_frames(20)
        range_ = TimeRange(start, end)
        assert range_.start.frames() == 10
        assert range_.end.frames() == 20
        assert range_.duration.frames() == 10

    def test_timerange_invalid(self) -> None:
        """Test TimeRange rejects end <= start."""
        from stoat_ferret_core import Position, TimeRange

        start = Position.from_frames(20)
        end = Position.from_frames(10)
        with pytest.raises(ValueError):
            TimeRange(start, end)

    def test_timerange_overlaps(self) -> None:
        """Test TimeRange.overlaps method."""
        from stoat_ferret_core import Position, TimeRange

        a = TimeRange(Position.from_frames(0), Position.from_frames(10))
        b = TimeRange(Position.from_frames(5), Position.from_frames(15))
        c = TimeRange(Position.from_frames(10), Position.from_frames(20))

        assert a.overlaps(b)
        assert not a.overlaps(c)  # Adjacent, not overlapping

    def test_timerange_union(self) -> None:
        """Test TimeRange.union method."""
        from stoat_ferret_core import Position, TimeRange

        a = TimeRange(Position.from_frames(0), Position.from_frames(10))
        b = TimeRange(Position.from_frames(10), Position.from_frames(20))
        union = a.union(b)
        assert union is not None
        assert union.start.frames() == 0
        assert union.end.frames() == 20


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

        chain = (
            FilterChain()
            .input("0:v")
            .filter(Filter.scale(1280, 720))
            .output("scaled")
        )
        result = str(chain)
        assert "[0:v]" in result
        assert "scale" in result
        assert "[scaled]" in result

    def test_filtergraph_construction(self) -> None:
        """Test FilterGraph construction and string output."""
        from stoat_ferret_core import Filter, FilterChain, FilterGraph

        graph = FilterGraph().chain(
            FilterChain()
            .input("0:v")
            .filter(Filter.scale(1280, 720))
            .output("v0")
        ).chain(
            FilterChain()
            .input("1:v")
            .filter(Filter.scale(1280, 720))
            .output("v1")
        ).chain(
            FilterChain()
            .input("v0")
            .input("v1")
            .filter(Filter.concat(2, 1, 0))
            .output("outv")
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


class TestModuleExports:
    """Tests verifying module exports are correct."""

    def test_all_exports_present(self) -> None:
        """Test all expected exports are in __all__."""
        import stoat_ferret_core

        expected = [
            "health_check",
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
        ]
        for name in expected:
            assert name in stoat_ferret_core.__all__
            assert hasattr(stoat_ferret_core, name)
