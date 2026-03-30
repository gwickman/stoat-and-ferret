"""Contract tests for Phase 4 preview FFmpeg commands.

Validates that HLS generation, thumbnail strip, waveform, and simplified
filter chain commands produce valid output when executed against real FFmpeg.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from stoat_ferret.api.services.thumbnail import build_strip_ffmpeg_args, calculate_strip_dimensions
from stoat_ferret.api.services.waveform import build_png_ffmpeg_args
from stoat_ferret.ffmpeg.executor import RealFFmpegExecutor
from stoat_ferret.preview.hls_generator import build_hls_args
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
@pytest.mark.contract
class TestHLSGenerationContract:
    """HLS segment generation produces a valid M3U8 manifest and playable .ts segments."""

    def test_hls_produces_valid_manifest_and_segments(
        self, sample_video_path: Path, tmp_path: Path
    ) -> None:
        """HLS generation creates a valid M3U8 manifest with at least one .ts segment."""
        output_dir = tmp_path / "hls_output"
        output_dir.mkdir()

        args = build_hls_args(
            input_path=str(sample_video_path),
            output_dir=output_dir,
            filter_complex=None,
            segment_duration=2.0,
        )

        real = RealFFmpegExecutor()
        result = real.run(args, timeout=60)
        assert result.returncode == 0, f"HLS generation failed: {result.stderr}"

        # Verify manifest exists and is valid M3U8
        manifest = output_dir / "manifest.m3u8"
        assert manifest.exists(), "manifest.m3u8 not created"
        content = manifest.read_text()
        assert content.startswith("#EXTM3U"), "Manifest missing #EXTM3U header"
        assert "#EXT-X-TARGETDURATION:" in content, "Manifest missing target duration"
        assert "#EXT-X-ENDLIST" in content, "VOD manifest missing #EXT-X-ENDLIST"

        # Verify at least one .ts segment exists and is non-empty
        segments = list(output_dir.glob("segment_*.ts"))
        assert len(segments) >= 1, "No .ts segments generated"
        for seg in segments:
            assert seg.stat().st_size > 0, f"Segment {seg.name} is empty"

    def test_hls_with_filter_complex(self, sample_video_path: Path, tmp_path: Path) -> None:
        """HLS generation with a filter_complex string produces valid output."""
        output_dir = tmp_path / "hls_filtered"
        output_dir.mkdir()

        args = build_hls_args(
            input_path=str(sample_video_path),
            output_dir=output_dir,
            filter_complex="scale=160:120",
            segment_duration=2.0,
        )

        real = RealFFmpegExecutor()
        result = real.run(args, timeout=60)
        assert result.returncode == 0, f"HLS with filter failed: {result.stderr}"

        manifest = output_dir / "manifest.m3u8"
        assert manifest.exists()
        segments = list(output_dir.glob("segment_*.ts"))
        assert len(segments) >= 1


@requires_ffmpeg
@pytest.mark.contract
class TestSimplifiedFilterChainContract:
    """Rust-simplified filter chain executes successfully with real FFmpeg."""

    def test_simplified_filter_graph_accepted_by_ffmpeg(self, sample_video_path: Path) -> None:
        """A filter graph simplified via Rust produces valid FFmpeg output."""
        from stoat_ferret_core import (
            Filter,
            FilterChain,
            FilterGraph,
            estimate_filter_cost,
            select_preview_quality,
            simplify_filter_graph,
        )

        # Build a filter graph with a scale filter
        graph = FilterGraph()
        chain = FilterChain().filter(Filter.scale(160, 120))
        graph = graph.chain(chain)

        # Simplify via Rust pipeline
        cost = estimate_filter_cost(graph)
        quality = select_preview_quality(cost)
        simplified = simplify_filter_graph(graph, quality)
        filter_str = str(simplified)

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-i",
                str(sample_video_path),
                "-filter_complex",
                filter_str,
                "-frames:v",
                "1",
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"Simplified filter rejected: {result.stderr}"

    def test_simplify_preserves_executability(self, sample_video_path: Path) -> None:
        """Simplifying a multi-filter chain still produces FFmpeg-valid output."""
        from stoat_ferret_core import (
            Filter,
            FilterChain,
            FilterGraph,
            PreviewQuality,
            simplify_filter_graph,
        )

        graph = FilterGraph()
        chain = (
            FilterChain()
            .filter(Filter.scale(320, 240))
            .filter(Filter("format").param("pix_fmts", "yuv420p"))
        )
        graph = graph.chain(chain)

        simplified = simplify_filter_graph(graph, PreviewQuality.Draft)
        filter_str = str(simplified)

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-i",
                str(sample_video_path),
                "-filter_complex",
                filter_str,
                "-frames:v",
                "1",
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"Draft-simplified filter rejected: {result.stderr}"


@requires_ffmpeg
@pytest.mark.contract
class TestThumbnailStripContract:
    """Thumbnail strip generation produces a valid JPEG sprite sheet."""

    def test_strip_produces_valid_jpeg(self, sample_video_path: Path, tmp_path: Path) -> None:
        """Sprite sheet generation outputs a valid JPEG with expected dimensions."""
        duration_seconds = 1.0
        interval = 0.5
        columns = 2
        frame_width = 160
        frame_height = 90

        _frame_count, rows = calculate_strip_dimensions(duration_seconds, interval, columns)
        output_path = tmp_path / "strip.jpg"

        args = build_strip_ffmpeg_args(
            str(sample_video_path),
            str(output_path),
            interval=interval,
            frame_width=frame_width,
            frame_height=frame_height,
            columns=columns,
            rows=rows,
        )

        real = RealFFmpegExecutor()
        result = real.run(args, timeout=60)
        assert result.returncode == 0, f"Strip generation failed: {result.stderr}"

        # Verify output is a valid JPEG
        assert output_path.exists(), "Sprite sheet not created"
        data = output_path.read_bytes()
        assert data[:2] == b"\xff\xd8", "Output is not a valid JPEG (missing SOI marker)"

        # Verify dimensions via JPEG SOF marker
        width, height = _read_jpeg_dimensions(data)
        expected_width = frame_width * columns
        expected_height = frame_height * rows
        assert width == expected_width, f"Width {width} != expected {expected_width}"
        assert height == expected_height, f"Height {height} != expected {expected_height}"


@requires_ffmpeg
@pytest.mark.contract
class TestWaveformContract:
    """Waveform generation produces a valid PNG image."""

    def test_waveform_produces_valid_png(self, sample_video_path: Path, tmp_path: Path) -> None:
        """showwavespic filter generates a valid PNG with expected dimensions."""
        width = 800
        height = 140
        output_path = tmp_path / "waveform.png"

        args = build_png_ffmpeg_args(
            str(sample_video_path),
            str(output_path),
            width=width,
            height=height,
            channels=1,
        )

        real = RealFFmpegExecutor()
        result = real.run(args, timeout=60)
        assert result.returncode == 0, f"Waveform generation failed: {result.stderr}"

        # Verify output is a valid PNG
        assert output_path.exists(), "Waveform PNG not created"
        data = output_path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", "Output is not a valid PNG"

        # Verify dimensions from IHDR chunk
        png_width, png_height = _read_png_dimensions(data)
        assert png_width == width, f"PNG width {png_width} != expected {width}"
        assert png_height == height, f"PNG height {png_height} != expected {height}"

    def test_stereo_waveform(self, sample_video_path: Path, tmp_path: Path) -> None:
        """Stereo waveform generation produces valid PNG output."""
        output_path = tmp_path / "waveform_stereo.png"

        args = build_png_ffmpeg_args(
            str(sample_video_path),
            str(output_path),
            width=800,
            height=140,
            channels=2,
        )

        real = RealFFmpegExecutor()
        result = real.run(args, timeout=60)
        assert result.returncode == 0, f"Stereo waveform failed: {result.stderr}"
        assert output_path.exists()
        data = output_path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", "Stereo output is not a valid PNG"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Extract width and height from JPEG SOF0/SOF2 marker.

    Args:
        data: Raw JPEG bytes.

    Returns:
        Tuple of (width, height).

    Raises:
        ValueError: If no SOF marker is found.
    """
    i = 2  # skip SOI
    while i < len(data) - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # SOF0 (0xC0) or SOF2 (0xC2) contain dimensions
        if marker in (0xC0, 0xC2):
            height = struct.unpack(">H", data[i + 5 : i + 7])[0]
            width = struct.unpack(">H", data[i + 7 : i + 9])[0]
            return width, height
        # Skip variable-length markers
        if marker == 0x00 or marker == 0xFF:
            i += 1
            continue
        if 0xD0 <= marker <= 0xD9:
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + length
    raise ValueError("No SOF marker found in JPEG data")


def _read_png_dimensions(data: bytes) -> tuple[int, int]:
    """Extract width and height from PNG IHDR chunk.

    Args:
        data: Raw PNG bytes.

    Returns:
        Tuple of (width, height).
    """
    # IHDR starts at byte 16 (8 signature + 4 length + 4 type)
    width = struct.unpack(">I", data[16:20])[0]
    height = struct.unpack(">I", data[20:24])[0]
    return width, height
