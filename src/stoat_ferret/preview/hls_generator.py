"""HLS segment generation service for preview playback.

Produces HLS VOD segments from project timelines using FFmpeg with:
- Rust filter simplification for preview performance
- Async execution via RealAsyncFFmpegExecutor
- Cooperative cancellation with directory cleanup
- Progress event emission
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from stoat_ferret.api.settings import get_settings
from stoat_ferret.ffmpeg.async_executor import ProgressInfo
from stoat_ferret.preview.metrics import preview_segment_seconds
from stoat_ferret_core import FilterGraph

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Awaitable, Callable

    from stoat_ferret.ffmpeg.async_executor import AsyncFFmpegExecutor

logger = structlog.get_logger(__name__)

# Default segment duration in seconds
DEFAULT_SEGMENT_DURATION = 2.0

# Segment filename pattern for FFmpeg HLS muxer
SEGMENT_FILENAME_PATTERN = "segment_%03d.ts"

# Manifest filename
MANIFEST_FILENAME = "manifest.m3u8"


def get_segment_duration() -> float:
    """Get the configured preview segment duration.

    Returns:
        Segment duration in seconds, from settings or default.
    """
    settings = get_settings()
    return settings.preview_segment_duration


def build_hls_args(
    input_path: str,
    output_dir: Path,
    filter_complex: str | None,
    segment_duration: float,
) -> list[str]:
    """Build FFmpeg arguments for HLS VOD segment generation.

    Args:
        input_path: Path to the source media file.
        output_dir: Directory for manifest and segment files.
        filter_complex: Optional simplified filter graph string.
        segment_duration: Target segment duration in seconds.

    Returns:
        List of FFmpeg arguments (excluding the ffmpeg command itself).
    """
    manifest_path = str(output_dir / MANIFEST_FILENAME)
    segment_pattern = str(output_dir / SEGMENT_FILENAME_PATTERN)

    args = [
        "-i",
        input_path,
    ]

    if filter_complex:
        args.extend(["-filter_complex", filter_complex])

    args.extend(
        [
            "-force_key_frames",
            f"expr:gte(t,n_forced*{segment_duration})",
            "-f",
            "hls",
            "-hls_time",
            str(segment_duration),
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            segment_pattern,
            "-progress",
            "pipe:2",
            "-y",
            manifest_path,
        ]
    )

    return args


def simplify_filter_for_preview(filter_graph: FilterGraph | None) -> str | None:
    """Apply Rust filter simplification for preview quality.

    Estimates filter cost, selects appropriate preview quality level,
    and simplifies the filter graph accordingly.

    Args:
        filter_graph: FilterGraph object to simplify, or None.

    Returns:
        Simplified filter graph string, or None if no filters.
    """
    if filter_graph is None:
        return None

    from stoat_ferret_core import (
        estimate_filter_cost,
        select_preview_quality,
        simplify_filter_graph,
    )

    cost = estimate_filter_cost(filter_graph)
    quality = select_preview_quality(cost)
    simplified = simplify_filter_graph(filter_graph, quality)

    logger.debug(
        "preview_filter_simplified",
        cost=round(cost, 3),
        quality=str(quality),
    )

    return str(simplified)


class HLSGenerator:
    """Generates HLS VOD segments from project timelines.

    Uses the async FFmpeg executor for non-blocking execution with
    progress reporting and cooperative cancellation support.
    """

    def __init__(
        self,
        *,
        async_executor: AsyncFFmpegExecutor,
        output_base_dir: str | None = None,
    ) -> None:
        """Initialize the HLS generator.

        Args:
            async_executor: Async FFmpeg executor for transcoding.
            output_base_dir: Base directory for preview output. Defaults
                to settings.preview_output_dir.
        """
        self._executor = async_executor
        if output_base_dir is None:
            output_base_dir = get_settings().preview_output_dir
        self._output_base_dir = Path(output_base_dir)

    def _session_dir(self, session_id: str) -> Path:
        """Get the output directory for a session.

        Args:
            session_id: Preview session identifier.

        Returns:
            Path to the session's output directory.
        """
        return self._output_base_dir / session_id

    async def generate(
        self,
        *,
        session_id: str,
        input_path: str,
        filter_graph: FilterGraph | None = None,
        duration_us: int | None = None,
        progress_callback: Callable[[float], Awaitable[None]] | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> Path:
        """Generate HLS VOD segments for a preview session.

        Args:
            session_id: Unique session identifier for output directory.
            input_path: Path to the source media file.
            filter_graph: Optional FilterGraph object to simplify for preview.
            duration_us: Total duration in microseconds for progress calculation.
            progress_callback: Optional async callback receiving progress (0.0-1.0).
            cancel_event: Optional event for cooperative cancellation.

        Returns:
            Path to the output directory containing manifest and segments.

        Raises:
            RuntimeError: If FFmpeg exits with a non-zero return code.
        """
        output_dir = self._session_dir(session_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        segment_duration = get_segment_duration()
        simplified_filter = simplify_filter_for_preview(filter_graph)

        args = build_hls_args(
            input_path=input_path,
            output_dir=output_dir,
            filter_complex=simplified_filter,
            segment_duration=segment_duration,
        )

        logger.info(
            "hls_generation_started",
            session_id=session_id,
            input_path=input_path,
            segment_duration=segment_duration,
            ffmpeg_command=" ".join(args),
        )

        # Wrap progress_callback to convert ProgressInfo -> percentage
        async_progress = None
        if progress_callback is not None and duration_us is not None and duration_us > 0:

            async def _on_progress(info: ProgressInfo) -> None:
                pct = min(info.out_time_us / duration_us, 1.0)
                await progress_callback(pct)

            async_progress = _on_progress

        result = await self._executor.run(
            args,
            progress_callback=async_progress,
            cancel_event=cancel_event,
        )

        # Handle cancellation
        if cancel_event is not None and cancel_event.is_set():
            _cleanup_session_dir(output_dir)
            logger.info("hls_generation_cancelled", session_id=session_id)
            raise RuntimeError(f"HLS generation cancelled for session {session_id}")

        # Handle failure
        if result.returncode != 0:
            _cleanup_session_dir(output_dir)
            error_msg = result.stderr.decode("utf-8", errors="replace")[:500]
            logger.error(
                "hls_generation_failed",
                session_id=session_id,
                returncode=result.returncode,
                error=error_msg,
            )
            raise RuntimeError(f"HLS generation failed (exit {result.returncode}): {error_msg}")

        # Record per-segment average timing
        segment_count = sum(1 for f in output_dir.iterdir() if f.suffix == ".ts")
        if segment_count > 0:
            per_segment = result.duration_seconds / segment_count
            for _ in range(segment_count):
                preview_segment_seconds.observe(per_segment)

        logger.info(
            "hls_generation_completed",
            session_id=session_id,
            duration_seconds=round(result.duration_seconds, 2),
        )

        return output_dir


def _cleanup_session_dir(output_dir: Path) -> None:
    """Remove session output directory and all contents.

    Args:
        output_dir: Directory to remove.
    """
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
        logger.debug("hls_session_dir_cleaned", path=str(output_dir))
