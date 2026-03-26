"""Thumbnail generation service using FFmpeg executor pattern."""

from __future__ import annotations

import asyncio
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.db.models import ThumbnailStrip, ThumbnailStripStatus
from stoat_ferret.ffmpeg.async_executor import ProgressInfo
from stoat_ferret.ffmpeg.executor import FFmpegExecutor

if TYPE_CHECKING:
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.ffmpeg.async_executor import AsyncFFmpegExecutor

logger = structlog.get_logger(__name__)

# Maximum columns to keep sprite sheet within JPEG 65535px dimension limit
MAX_COLUMNS = 400

# Progress throttle constants
_PROGRESS_MIN_INTERVAL_S = 0.5
_PROGRESS_MIN_DELTA = 0.05


def calculate_strip_dimensions(
    duration_seconds: float,
    interval: float,
    columns: int,
) -> tuple[int, int]:
    """Calculate frame count and row count for a sprite sheet.

    Args:
        duration_seconds: Video duration in seconds.
        interval: Seconds between frames.
        columns: Number of columns in the grid.

    Returns:
        Tuple of (frame_count, rows).
    """
    frame_count = max(1, math.ceil(duration_seconds / interval))
    rows = math.ceil(frame_count / columns)
    return frame_count, rows


def build_strip_ffmpeg_args(
    video_path: str,
    output_path: str,
    *,
    interval: float,
    frame_width: int,
    frame_height: int,
    columns: int,
    rows: int,
) -> list[str]:
    """Build FFmpeg arguments for sprite sheet generation.

    Uses fps+scale+tile filter chain to produce a grid JPEG.

    Args:
        video_path: Path to the source video.
        output_path: Path for the output sprite sheet.
        interval: Seconds between frames.
        frame_width: Width of each frame in pixels.
        frame_height: Height of each frame in pixels.
        columns: Number of columns in the tile grid.
        rows: Number of rows in the tile grid.

    Returns:
        List of FFmpeg arguments.
    """
    vf = f"fps=1/{interval},scale={frame_width}:{frame_height},tile={columns}x{rows}"
    return [
        "-i",
        video_path,
        "-vf",
        vf,
        "-frames:v",
        "1",
        "-q:v",
        "5",
        "-y",
        output_path,
    ]


def extract_frame_args(
    video_path: str,
    output_path: str,
    *,
    timestamp: float = 0,
    width: int = 320,
    height: int = -1,
    quality: int = 5,
) -> list[str]:
    """Build FFmpeg arguments for single-frame extraction.

    Shared primitive reusable by both thumbnail generation and
    effect preview code paths.

    Args:
        video_path: Path to the source video.
        output_path: Path for the output JPEG.
        timestamp: Extraction timestamp in seconds.
        width: Output width in pixels.
        height: Output height in pixels (-1 for auto).
        quality: JPEG quality (2-31, lower is better).

    Returns:
        List of FFmpeg arguments.
    """
    return [
        "-ss",
        str(timestamp),
        "-i",
        video_path,
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:{height}",
        "-q:v",
        str(quality),
        "-y",
        output_path,
    ]


class ThumbnailService:
    """Generate video thumbnails and sprite sheet strips using FFmpeg.

    Extracts single frames for video library cards and generates NxM
    grid sprite sheets for timeline seek tooltips.

    Args:
        executor: FFmpeg executor for running thumbnail extraction.
        thumbnail_dir: Directory to store generated thumbnails.
        width: Thumbnail width in pixels (height auto-calculated).
        async_executor: Optional async FFmpeg executor for strip generation.
        ws_manager: Optional WebSocket manager for progress broadcasting.
        strip_interval: Seconds between frames in sprite sheets.
    """

    def __init__(
        self,
        executor: FFmpegExecutor,
        thumbnail_dir: str | Path,
        *,
        width: int = 320,
        async_executor: AsyncFFmpegExecutor | None = None,
        ws_manager: ConnectionManager | None = None,
        strip_interval: float = 5.0,
    ) -> None:
        self._executor = executor
        self._thumbnail_dir = Path(thumbnail_dir)
        self._width = width
        self._async_executor = async_executor
        self._ws_manager = ws_manager
        self._strip_interval = strip_interval
        self._strips: dict[str, ThumbnailStrip] = {}  # video_id -> strip

    def generate(self, video_path: str, video_id: str) -> str | None:
        """Generate a thumbnail for a video file.

        Extracts a single frame at the 5-second mark, scales to configured
        width with auto-calculated height, and saves as JPEG quality 5.

        Args:
            video_path: Path to the source video file.
            video_id: Unique video identifier (used for output filename).

        Returns:
            Path to the generated thumbnail file, or None if generation failed.
        """
        self._thumbnail_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._thumbnail_dir / f"{video_id}.jpg"

        args = extract_frame_args(
            video_path,
            str(output_path),
            timestamp=5,
            width=self._width,
            height=-1,
            quality=5,
        )

        try:
            result = self._executor.run(args, timeout=30)
        except Exception:
            logger.warning(
                "thumbnail_generation_error",
                video_id=video_id,
                video_path=video_path,
            )
            return None

        if result.returncode != 0:
            logger.warning(
                "thumbnail_generation_failed",
                video_id=video_id,
                video_path=video_path,
                returncode=result.returncode,
                stderr=result.stderr.decode(errors="replace"),
            )
            return None

        logger.info(
            "thumbnail_generated",
            video_id=video_id,
            output_path=str(output_path),
            duration_seconds=result.duration_seconds,
        )
        return str(output_path)

    async def generate_effect_preview(
        self,
        video_path: str,
        effect_filter: str,
        *,
        timestamp: float = 0,
        width: int = 320,
        quality: int = 3,
    ) -> str | None:
        """Generate a thumbnail with an effect filter applied.

        Extracts a single frame at the given timestamp, applies the effect
        filter via FFmpeg ``-vf``, scales to the specified width (maintaining
        aspect ratio), and saves as JPEG.

        Args:
            video_path: Path to the source video file.
            effect_filter: FFmpeg filter string to apply (e.g. ``drawtext=...``).
            timestamp: Frame extraction timestamp in seconds.
            width: Output width in pixels (height auto-calculated).
            quality: JPEG quality (2-31, lower is better).

        Returns:
            Path to the generated thumbnail file, or None if generation failed.
        """
        self._thumbnail_dir.mkdir(parents=True, exist_ok=True)
        preview_id = uuid.uuid4().hex[:12]
        output_path = self._thumbnail_dir / f"effect_preview_{preview_id}.jpg"

        vf = f"{effect_filter},scale={width}:-1"
        args = [
            "-ss",
            str(timestamp),
            "-i",
            video_path,
            "-vf",
            vf,
            "-frames:v",
            "1",
            "-q:v",
            str(quality),
            "-y",
            str(output_path),
        ]

        try:
            result = await asyncio.to_thread(self._executor.run, args, timeout=30)
        except Exception:
            logger.warning(
                "effect_preview_generation_error",
                video_path=video_path,
                effect_filter=effect_filter,
            )
            return None

        if result.returncode != 0:
            logger.warning(
                "effect_preview_generation_failed",
                video_path=video_path,
                effect_filter=effect_filter,
                returncode=result.returncode,
                stderr=result.stderr.decode(errors="replace"),
            )
            return None

        logger.info(
            "effect_preview_generated",
            video_path=video_path,
            effect_filter=effect_filter,
            output_path=str(output_path),
            duration_seconds=result.duration_seconds,
        )
        return str(output_path)

    def get_thumbnail_path(self, video_id: str) -> str | None:
        """Check if a thumbnail file exists for a video.

        Args:
            video_id: Unique video identifier.

        Returns:
            Path to the thumbnail file if it exists, or None.
        """
        path = self._thumbnail_dir / f"{video_id}.jpg"
        if path.is_file():
            return str(path)
        return None

    def get_strip(self, video_id: str) -> ThumbnailStrip | None:
        """Get the thumbnail strip metadata for a video.

        Args:
            video_id: Unique video identifier.

        Returns:
            ThumbnailStrip if one has been generated, or None.
        """
        return self._strips.get(video_id)

    async def generate_strip(
        self,
        *,
        video_id: str,
        video_path: str,
        duration_seconds: float,
        strip_id: str | None = None,
        interval: float | None = None,
        frame_width: int = 160,
        frame_height: int = 90,
        columns: int = 10,
    ) -> ThumbnailStrip:
        """Generate a sprite sheet strip for a video.

        Runs FFmpeg with fps+scale+tile filters as a background job,
        emitting progress events via WebSocket.

        Args:
            video_id: Source video ID.
            video_path: Path to the source video file.
            duration_seconds: Video duration in seconds.
            strip_id: Optional pre-generated strip ID.
            interval: Seconds between frames (uses service default if None).
            frame_width: Width of each frame in pixels.
            frame_height: Height of each frame in pixels.
            columns: Number of columns in the tile grid (max 400).

        Returns:
            The completed ThumbnailStrip metadata.

        Raises:
            RuntimeError: If no async executor is configured or FFmpeg fails.
        """
        if self._async_executor is None:
            raise RuntimeError("Async executor required for strip generation")

        effective_interval = interval if interval is not None else self._strip_interval
        effective_columns = min(columns, MAX_COLUMNS)

        frame_count, rows = calculate_strip_dimensions(
            duration_seconds,
            effective_interval,
            effective_columns,
        )

        sid = strip_id or ThumbnailStrip.new_id()
        strip = ThumbnailStrip(
            id=sid,
            video_id=video_id,
            status=ThumbnailStripStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            frame_count=0,
            frame_width=frame_width,
            frame_height=frame_height,
            interval_seconds=effective_interval,
            columns=effective_columns,
            rows=0,
        )

        # Store strip for later retrieval and transition to generating
        self._strips[video_id] = strip
        strip.status = ThumbnailStripStatus.GENERATING

        # Prepare output
        strip_dir = self._thumbnail_dir / "strips"
        strip_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(strip_dir / f"{sid}.jpg")

        args = build_strip_ffmpeg_args(
            video_path,
            output_path,
            interval=effective_interval,
            frame_width=frame_width,
            frame_height=frame_height,
            columns=effective_columns,
            rows=rows,
        )

        # Build progress callback
        duration_us = int(duration_seconds * 1_000_000)
        progress_cb = self._make_strip_progress_callback(
            strip_id=sid,
            video_id=video_id,
            duration_us=duration_us,
        )

        start_time = time.monotonic()
        try:
            result = await self._async_executor.run(
                args,
                progress_callback=progress_cb,
            )
        except Exception:
            strip.status = ThumbnailStripStatus.ERROR
            logger.error(
                "thumbnail_strip_generation_error",
                strip_id=sid,
                video_id=video_id,
                exc_info=True,
            )
            raise RuntimeError("Thumbnail strip generation failed") from None

        generation_time = time.monotonic() - start_time

        if result.returncode != 0:
            strip.status = ThumbnailStripStatus.ERROR
            error_msg = result.stderr.decode("utf-8", errors="replace")[:500]
            logger.error(
                "thumbnail_strip_generation_failed",
                strip_id=sid,
                video_id=video_id,
                returncode=result.returncode,
                error=error_msg,
            )
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {error_msg}")

        # Update strip metadata on success
        strip.status = ThumbnailStripStatus.READY
        strip.file_path = output_path
        strip.frame_count = frame_count
        strip.rows = rows

        strip_size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        logger.info(
            "thumbnail_strip_generated",
            strip_id=sid,
            video_id=video_id,
            frame_count=frame_count,
            strip_size_bytes=strip_size_bytes,
            generation_time=round(generation_time, 2),
        )

        # Send completion progress event
        await self._send_strip_progress(
            strip_id=sid,
            video_id=video_id,
            progress=1.0,
            status="complete",
        )

        return strip

    def _make_strip_progress_callback(
        self,
        *,
        strip_id: str,
        video_id: str,
        duration_us: int,
    ) -> Any:
        """Create a throttled progress callback for strip generation.

        Args:
            strip_id: Thumbnail strip ID.
            video_id: Source video ID.
            duration_us: Video duration in microseconds.

        Returns:
            Async callback function for ProgressInfo updates.
        """
        last_progress = 0.0
        last_time = 0.0

        async def on_progress(info: ProgressInfo) -> None:
            nonlocal last_progress, last_time

            if duration_us <= 0:
                return

            progress = min(info.out_time_us / duration_us, 1.0)
            now = time.monotonic()

            time_delta = now - last_time
            progress_delta = progress - last_progress
            if time_delta < _PROGRESS_MIN_INTERVAL_S and progress_delta < _PROGRESS_MIN_DELTA:
                return

            last_progress = progress
            last_time = now

            await self._send_strip_progress(
                strip_id=strip_id,
                video_id=video_id,
                progress=progress,
                status="generating",
            )

        return on_progress

    async def _send_strip_progress(
        self,
        *,
        strip_id: str,
        video_id: str,
        progress: float,
        status: str,
    ) -> None:
        """Send a strip generation progress event via WebSocket.

        Args:
            strip_id: Thumbnail strip ID.
            video_id: Source video ID.
            progress: Progress value 0.0-1.0.
            status: Generation status string.
        """
        if self._ws_manager is not None:
            await self._ws_manager.broadcast(
                build_event(
                    EventType.JOB_PROGRESS,
                    {
                        "job_type": "thumbnail_strip",
                        "strip_id": strip_id,
                        "video_id": video_id,
                        "progress": progress,
                        "status": status,
                    },
                )
            )
