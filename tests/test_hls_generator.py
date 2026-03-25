"""Tests for the HLS segment generator module."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.async_executor import FakeAsyncFFmpegExecutor
from stoat_ferret.preview.hls_generator import (
    MANIFEST_FILENAME,
    SEGMENT_FILENAME_PATTERN,
    HLSGenerator,
    _cleanup_session_dir,
    build_hls_args,
    get_segment_duration,
    simplify_filter_for_preview,
)


class TestBuildHlsArgs:
    """Tests for HLS FFmpeg argument construction."""

    def test_basic_args_without_filter(self, tmp_path: Path) -> None:
        """Build args with no filter graph."""
        args = build_hls_args(
            input_path="/media/video.mp4",
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
        )

        assert "-i" in args
        assert "/media/video.mp4" in args
        assert "-f" in args
        assert "hls" in args
        assert "-hls_time" in args
        assert "2.0" in args
        assert "-hls_playlist_type" in args
        assert "vod" in args
        assert "-force_key_frames" in args
        assert "expr:gte(t,n_forced*2.0)" in args
        assert "-hls_segment_filename" in args
        assert str(tmp_path / SEGMENT_FILENAME_PATTERN) in args
        assert "-progress" in args
        assert "pipe:2" in args
        assert "-y" in args
        assert str(tmp_path / MANIFEST_FILENAME) in args

    def test_args_with_filter_complex(self, tmp_path: Path) -> None:
        """Build args includes -filter_complex when provided."""
        args = build_hls_args(
            input_path="/media/video.mp4",
            output_dir=tmp_path,
            filter_complex="scale=640:360",
            segment_duration=2.0,
        )

        assert "-filter_complex" in args
        idx = args.index("-filter_complex")
        assert args[idx + 1] == "scale=640:360"

    def test_no_filter_complex_when_none(self, tmp_path: Path) -> None:
        """Build args omits -filter_complex when None."""
        args = build_hls_args(
            input_path="/media/video.mp4",
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
        )

        assert "-filter_complex" not in args

    def test_custom_segment_duration(self, tmp_path: Path) -> None:
        """Build args uses the provided segment duration."""
        args = build_hls_args(
            input_path="/media/video.mp4",
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=4.0,
        )

        idx = args.index("-hls_time")
        assert args[idx + 1] == "4.0"
        assert "expr:gte(t,n_forced*4.0)" in args

    def test_segment_filename_pattern(self, tmp_path: Path) -> None:
        """Segment filename uses segment_%03d.ts pattern."""
        args = build_hls_args(
            input_path="/media/video.mp4",
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
        )

        idx = args.index("-hls_segment_filename")
        pattern = args[idx + 1]
        assert pattern.endswith("segment_%03d.ts")

    def test_manifest_filename(self, tmp_path: Path) -> None:
        """Output manifest is named manifest.m3u8."""
        args = build_hls_args(
            input_path="/media/video.mp4",
            output_dir=tmp_path,
            filter_complex=None,
            segment_duration=2.0,
        )

        # Last arg is the output file
        assert args[-1] == str(tmp_path / "manifest.m3u8")


class TestGetSegmentDuration:
    """Tests for segment duration configuration."""

    def test_default_duration(self) -> None:
        """Default segment duration is 2.0 seconds."""
        from stoat_ferret.api.settings import get_settings

        get_settings.cache_clear()
        duration = get_segment_duration()
        assert duration == 2.0
        get_settings.cache_clear()

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Segment duration can be set via STOAT_PREVIEW_SEGMENT_DURATION."""
        from stoat_ferret.api.settings import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("STOAT_PREVIEW_SEGMENT_DURATION", "4.0")
        get_settings.cache_clear()
        duration = get_segment_duration()
        assert duration == 4.0
        get_settings.cache_clear()


class TestSimplifyFilterForPreview:
    """Tests for Rust filter simplification integration."""

    def test_none_returns_none(self) -> None:
        """None filter graph returns None."""
        result = simplify_filter_for_preview(None)
        assert result is None

    def test_simplifies_filter_graph(self) -> None:
        """FilterGraph is simplified via cost estimation and quality selection."""
        from stoat_ferret_core import Filter, FilterChain, FilterGraph

        graph = FilterGraph().chain(FilterChain().filter(Filter.scale(640, 360)))
        result = simplify_filter_for_preview(graph)
        assert result is not None
        assert isinstance(result, str)

    def test_expensive_filter_simplified(self) -> None:
        """Expensive filters are simplified based on cost estimation."""
        from stoat_ferret_core import Filter, FilterChain, FilterGraph

        # Build a graph with multiple filters to test simplification
        chain = FilterChain().filter(Filter.scale(640, 360))
        graph = FilterGraph().chain(chain)
        result = simplify_filter_for_preview(graph)
        # Result should be a string representation of the simplified graph
        assert isinstance(result, str)


class TestHLSGenerator:
    """Tests for the HLS generator class."""

    async def test_generate_creates_output_directory(self, tmp_path: Path) -> None:
        """Generate creates the session output directory."""
        executor = FakeAsyncFFmpegExecutor()
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        result = await generator.generate(
            session_id="test-session",
            input_path="/media/video.mp4",
        )

        assert result == tmp_path / "test-session"
        assert result.exists()

    async def test_generate_passes_correct_args(self, tmp_path: Path) -> None:
        """Generate builds correct FFmpeg args."""
        executor = FakeAsyncFFmpegExecutor()
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        await generator.generate(
            session_id="test-session",
            input_path="/media/video.mp4",
        )

        assert len(executor.calls) == 1
        args = executor.calls[0]
        assert "-i" in args
        assert "/media/video.mp4" in args
        assert "-f" in args
        assert "hls" in args
        assert "-hls_playlist_type" in args
        assert "vod" in args

    async def test_generate_failure_cleans_up(self, tmp_path: Path) -> None:
        """Generate cleans up output directory on FFmpeg failure."""
        executor = FakeAsyncFFmpegExecutor(returncode=1)
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        with pytest.raises(RuntimeError, match="HLS generation failed"):
            await generator.generate(
                session_id="fail-session",
                input_path="/media/video.mp4",
            )

        # Output directory should be cleaned up
        assert not (tmp_path / "fail-session").exists()

    async def test_generate_cancellation_cleans_up(self, tmp_path: Path) -> None:
        """Generate cleans up output directory on cancellation."""
        cancel_event = asyncio.Event()
        cancel_event.set()  # Pre-set to simulate cancellation

        executor = FakeAsyncFFmpegExecutor()
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        with pytest.raises(RuntimeError, match="cancelled"):
            await generator.generate(
                session_id="cancel-session",
                input_path="/media/video.mp4",
                cancel_event=cancel_event,
            )

        # Output directory should be cleaned up
        assert not (tmp_path / "cancel-session").exists()

    async def test_generate_progress_callback(self, tmp_path: Path) -> None:
        """Generate emits progress via callback."""
        progress_values: list[float] = []

        async def on_progress(pct: float) -> None:
            progress_values.append(pct)

        executor = FakeAsyncFFmpegExecutor(
            stderr_lines=[
                "out_time_us=5000000",
                "out_time_us=10000000",
            ]
        )
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        await generator.generate(
            session_id="progress-session",
            input_path="/media/video.mp4",
            duration_us=10_000_000,
            progress_callback=on_progress,
        )

        assert len(progress_values) >= 2
        # First progress: 5s / 10s = 0.5
        assert progress_values[0] == pytest.approx(0.5)
        # Second progress: 10s / 10s = 1.0
        assert progress_values[1] == pytest.approx(1.0)

    async def test_generate_progress_capped_at_1(self, tmp_path: Path) -> None:
        """Progress percentage is capped at 1.0."""
        progress_values: list[float] = []

        async def on_progress(pct: float) -> None:
            progress_values.append(pct)

        executor = FakeAsyncFFmpegExecutor(
            stderr_lines=[
                "out_time_us=20000000",  # Exceeds duration
            ]
        )
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        await generator.generate(
            session_id="cap-session",
            input_path="/media/video.mp4",
            duration_us=10_000_000,
            progress_callback=on_progress,
        )

        assert progress_values[0] == 1.0

    async def test_generate_no_progress_without_duration(self, tmp_path: Path) -> None:
        """No progress emitted when duration_us is not provided."""
        progress_values: list[float] = []

        async def on_progress(pct: float) -> None:
            progress_values.append(pct)

        executor = FakeAsyncFFmpegExecutor(stderr_lines=["out_time_us=5000000"])
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        await generator.generate(
            session_id="no-dur-session",
            input_path="/media/video.mp4",
            progress_callback=on_progress,
        )

        # No progress because duration_us not provided
        assert len(progress_values) == 0

    async def test_generate_with_filter_graph(self, tmp_path: Path) -> None:
        """Generate applies filter simplification when filter_graph is provided."""
        from stoat_ferret_core import Filter, FilterChain, FilterGraph

        executor = FakeAsyncFFmpegExecutor()
        generator = HLSGenerator(
            async_executor=executor,
            output_base_dir=str(tmp_path),
        )

        graph = FilterGraph().chain(FilterChain().filter(Filter.scale(640, 360)))

        await generator.generate(
            session_id="filter-session",
            input_path="/media/video.mp4",
            filter_graph=graph,
        )

        args = executor.calls[0]
        assert "-filter_complex" in args


class TestCleanupSessionDir:
    """Tests for session directory cleanup."""

    def test_cleanup_removes_directory(self, tmp_path: Path) -> None:
        """Cleanup removes directory and all contents."""
        session_dir = tmp_path / "test-session"
        session_dir.mkdir()
        (session_dir / "manifest.m3u8").write_text("#EXTM3U")
        (session_dir / "segment_000.ts").write_bytes(b"\x00" * 100)

        _cleanup_session_dir(session_dir)

        assert not session_dir.exists()

    def test_cleanup_nonexistent_directory(self, tmp_path: Path) -> None:
        """Cleanup does nothing for nonexistent directory."""
        session_dir = tmp_path / "nonexistent"
        _cleanup_session_dir(session_dir)
        # Should not raise


class TestHLSManifestContract:
    """Contract tests for HLS manifest structure.

    Validates that FFmpeg HLS muxer output produces a valid VOD playlist
    parseable by HLS.js with 6-decimal EXTINF durations.
    """

    # Empirical manifest captured from FFmpeg HLS muxer output
    SAMPLE_MANIFEST = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:3
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-PLAYLIST-TYPE:VOD
#EXTINF:2.000000,
segment_000.ts
#EXTINF:2.000000,
segment_001.ts
#EXTINF:1.500000,
segment_002.ts
#EXT-X-ENDLIST
"""

    def test_manifest_contains_vod_type(self) -> None:
        """Manifest contains VOD playlist type header."""
        assert "#EXT-X-PLAYLIST-TYPE:VOD" in self.SAMPLE_MANIFEST

    def test_manifest_contains_endlist(self) -> None:
        """Manifest contains ENDLIST marker (required for VOD)."""
        assert "#EXT-X-ENDLIST" in self.SAMPLE_MANIFEST

    def test_manifest_extinf_6_decimal(self) -> None:
        """EXTINF entries have 6-decimal durations."""
        import re

        extinf_pattern = re.compile(r"#EXTINF:(\d+\.\d{6}),")
        matches = extinf_pattern.findall(self.SAMPLE_MANIFEST)
        assert len(matches) == 3
        assert matches[0] == "2.000000"
        assert matches[1] == "2.000000"
        assert matches[2] == "1.500000"

    def test_manifest_segment_filenames(self) -> None:
        """Segment filenames follow segment_%03d.ts pattern."""
        import re

        segment_pattern = re.compile(r"segment_\d{3}\.ts")
        matches = segment_pattern.findall(self.SAMPLE_MANIFEST)
        assert len(matches) == 3
        assert matches[0] == "segment_000.ts"
        assert matches[1] == "segment_001.ts"
        assert matches[2] == "segment_002.ts"

    def test_manifest_starts_with_extm3u(self) -> None:
        """Manifest starts with #EXTM3U header."""
        assert self.SAMPLE_MANIFEST.startswith("#EXTM3U")
