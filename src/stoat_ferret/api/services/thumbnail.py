"""Thumbnail generation service using FFmpeg executor pattern."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import structlog

from stoat_ferret.ffmpeg.executor import FFmpegExecutor

logger = structlog.get_logger(__name__)


class ThumbnailService:
    """Generate video thumbnails using FFmpeg.

    Extracts a single frame at the 5-second mark, scales to the configured
    width (maintaining aspect ratio), and saves as JPEG.

    Args:
        executor: FFmpeg executor for running thumbnail extraction.
        thumbnail_dir: Directory to store generated thumbnails.
        width: Thumbnail width in pixels (height auto-calculated).
    """

    def __init__(
        self,
        executor: FFmpegExecutor,
        thumbnail_dir: str | Path,
        *,
        width: int = 320,
    ) -> None:
        self._executor = executor
        self._thumbnail_dir = Path(thumbnail_dir)
        self._width = width

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

        args = [
            "-ss",
            "5",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-vf",
            f"scale={self._width}:-1",
            "-q:v",
            "5",
            "-y",
            str(output_path),
        ]

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
