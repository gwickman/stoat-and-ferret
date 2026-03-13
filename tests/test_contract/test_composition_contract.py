"""Contract tests for Phase 3 composition filter builders against real FFmpeg.

Validates that overlay, composition graph, and audio mix filter builders
produce valid FFmpeg filter syntax by executing against the real binary.
"""

from __future__ import annotations

import pytest

from stoat_ferret.ffmpeg.executor import RealFFmpegExecutor
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
@pytest.mark.contract
class TestOverlayFilterContract:
    """Verify build_overlay_filter() output is accepted by real FFmpeg."""

    def test_overlay_pip_position(self) -> None:
        """Overlay filter for PIP position executes with FFmpeg exit code 0."""
        from stoat_ferret_core import LayoutPosition, build_overlay_filter, build_scale_for_layout

        pos = LayoutPosition(0.5, 0.5, 0.25, 0.25, 1)
        scale_str = build_scale_for_layout(pos, 320, 240, False)
        overlay_str = build_overlay_filter(pos, 320, 240, 0.0, 1.0)

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:d=0.1",
                "-f",
                "lavfi",
                "-i",
                "color=c=red:s=320x240:d=0.1",
                "-filter_complex",
                f"[1:v]{scale_str}[pip];[0:v][pip]{overlay_str}",
                "-frames:v",
                "1",
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"FFmpeg rejected overlay filter: {result.stderr}"

    def test_overlay_with_time_window(self) -> None:
        """Overlay filter with non-zero start time executes with FFmpeg exit code 0."""
        from stoat_ferret_core import LayoutPosition, build_overlay_filter

        pos = LayoutPosition(0.0, 0.0, 1.0, 1.0, 0)
        overlay_str = build_overlay_filter(pos, 320, 240, 0.5, 2.0)

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:d=1",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=320x240:d=1",
                "-filter_complex",
                f"[0:v][1:v]{overlay_str}",
                "-frames:v",
                "1",
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"FFmpeg rejected timed overlay: {result.stderr}"


@requires_ffmpeg
@pytest.mark.contract
class TestCompositionGraphContract:
    """Verify build_composition_graph() output is accepted by real FFmpeg."""

    def test_sequential_two_clips(self) -> None:
        """Sequential composition graph for 2 clips executes with FFmpeg exit code 0."""
        from stoat_ferret_core import CompositionClip, build_composition_graph

        clips = [
            CompositionClip(0, 0.0, 0.5, 0, 0),
            CompositionClip(1, 0.5, 1.0, 0, 0),
        ]
        graph = build_composition_graph(clips, [], None, None, 320, 240)
        filter_str = str(graph)

        # Each lavfi input uses named pads to produce both video and audio streams
        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:d=0.5[out0];sine=frequency=440:duration=0.5[out1]",
                "-f",
                "lavfi",
                "-i",
                "color=c=red:s=320x240:d=0.5[out0];sine=frequency=880:duration=0.5[out1]",
                "-filter_complex",
                filter_str,
                "-map",
                "[outv]",
                "-map",
                "[outa]",
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"FFmpeg rejected sequential graph: {result.stderr}"

    def test_spatial_side_by_side(self) -> None:
        """Spatial composition with side-by-side layout executes with FFmpeg exit code 0."""
        from stoat_ferret_core import (
            CompositionClip,
            LayoutPosition,
            LayoutSpec,
            build_composition_graph,
        )

        clips = [
            CompositionClip(0, 0.0, 0.5, 0, 0),
            CompositionClip(1, 0.0, 0.5, 1, 1),
        ]
        positions = [
            LayoutPosition(0.0, 0.0, 0.5, 1.0, 0),
            LayoutPosition(0.5, 0.0, 0.5, 1.0, 1),
        ]
        layout = LayoutSpec(positions)
        graph = build_composition_graph(clips, [], layout, None, 320, 240)
        filter_str = str(graph)

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:d=0.5",
                "-f",
                "lavfi",
                "-i",
                "color=c=red:s=320x240:d=0.5",
                "-filter_complex",
                filter_str,
                "-map",
                "[outv]",
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"FFmpeg rejected spatial graph: {result.stderr}"


@requires_ffmpeg
@pytest.mark.contract
class TestAudioMixContract:
    """Verify AudioMixSpec.build_filter_chain() output is accepted by real FFmpeg."""

    def test_two_track_mix(self) -> None:
        """Audio mix filter chain for 2 tracks executes with FFmpeg exit code 0."""
        from stoat_ferret_core import AudioMixSpec, TrackAudioConfig

        tracks = [
            TrackAudioConfig(0.8, 0.0, 0.0),
            TrackAudioConfig(0.5, 0.0, 0.0),
        ]
        spec = AudioMixSpec(tracks)
        chain = spec.build_filter_chain()

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=0.5",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:duration=0.5",
                "-filter_complex",
                chain,
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"FFmpeg rejected audio mix: {result.stderr}"

    def test_three_track_mix_with_fades(self) -> None:
        """Audio mix with volume and fades for 3 tracks executes with FFmpeg exit code 0."""
        from stoat_ferret_core import AudioMixSpec, TrackAudioConfig

        tracks = [
            TrackAudioConfig(0.8, 0.1, 0.1),
            TrackAudioConfig(0.5, 0.0, 0.0),
            TrackAudioConfig(1.0, 0.0, 0.0),
        ]
        spec = AudioMixSpec(tracks)
        chain = spec.build_filter_chain()

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=0.5",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:duration=0.5",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:duration=0.5",
                "-filter_complex",
                chain,
                "-y",
                "-f",
                "null",
                "-",
            ]
        )
        assert result.returncode == 0, f"FFmpeg rejected 3-track audio mix: {result.stderr}"
