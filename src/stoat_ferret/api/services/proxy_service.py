"""Proxy generation service for lower-resolution preview files.

Orchestrates FFmpeg proxy transcoding as background jobs with progress
reporting, storage quota management, and stale proxy detection.
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus
from stoat_ferret.ffmpeg.async_executor import ProgressInfo

if TYPE_CHECKING:
    import asyncio

    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.db.proxy_repository import AsyncProxyRepository
    from stoat_ferret.ffmpeg.async_executor import AsyncFFmpegExecutor
    from stoat_ferret.jobs.queue import AsyncJobQueue

logger = structlog.get_logger(__name__)

PROXY_JOB_TYPE = "proxy"

# Storage quota defaults
DEFAULT_MAX_STORAGE_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB
CLEANUP_THRESHOLD = 0.80  # 80% triggers eviction

# Progress throttle constants
PROGRESS_MIN_INTERVAL_S = 0.5  # 500ms between events
PROGRESS_MIN_DELTA = 0.05  # 5% minimum change

# Resolution -> quality mapping thresholds
_QUALITY_MAP: list[tuple[int, ProxyQuality, int, int]] = [
    # (source_height_threshold, quality, target_width, target_height)
    (1080, ProxyQuality.HIGH, 1280, 720),
    (720, ProxyQuality.MEDIUM, 960, 540),
]

# Passthrough sentinel
_PASSTHROUGH_QUALITY = ProxyQuality.LOW


def select_proxy_quality(source_width: int, source_height: int) -> tuple[ProxyQuality, int, int]:
    """Select proxy quality and resolution based on source dimensions.

    Args:
        source_width: Source video width in pixels.
        source_height: Source video height in pixels.

    Returns:
        Tuple of (quality, target_width, target_height). For passthrough,
        returns the source dimensions unchanged.
    """
    for threshold, quality, target_w, target_h in _QUALITY_MAP:
        if source_height > threshold:
            return quality, target_w, target_h
    # Source is <= 720p: passthrough (no transcoding needed)
    return _PASSTHROUGH_QUALITY, source_width, source_height


def build_ffmpeg_args(
    source_path: str,
    output_path: str,
    target_width: int,
    target_height: int,
) -> list[str]:
    """Build FFmpeg command arguments for proxy transcoding.

    Args:
        source_path: Path to the source video file.
        output_path: Path for the output proxy file.
        target_width: Target width in pixels.
        target_height: Target height in pixels.

    Returns:
        List of FFmpeg arguments (excluding the ffmpeg command itself).
    """
    return [
        "-i",
        source_path,
        "-vf",
        f"scale={target_width}:{target_height}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-progress",
        "pipe:2",
        "-y",
        output_path,
    ]


def compute_file_checksum(file_path: str, chunk_size: int = 8192) -> str:
    """Compute SHA-256 checksum of a file.

    Args:
        file_path: Path to the file.
        chunk_size: Read buffer size in bytes.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


class ProxyService:
    """Orchestrates proxy file generation, quota management, and staleness detection.

    Attributes:
        max_storage_bytes: Maximum total proxy storage in bytes.
        cleanup_threshold: Fraction of max_storage triggering LRU eviction.
    """

    def __init__(
        self,
        *,
        proxy_repository: AsyncProxyRepository,
        async_executor: AsyncFFmpegExecutor,
        ws_manager: ConnectionManager | None = None,
        job_queue: AsyncJobQueue | None = None,
        proxy_dir: str = "proxies",
        max_storage_bytes: int = DEFAULT_MAX_STORAGE_BYTES,
        cleanup_threshold: float = CLEANUP_THRESHOLD,
    ) -> None:
        """Initialize the proxy service.

        Args:
            proxy_repository: Repository for proxy file records.
            async_executor: Async FFmpeg executor for transcoding.
            ws_manager: Optional WebSocket manager for progress broadcasting.
            job_queue: Optional job queue for progress tracking.
            proxy_dir: Directory to store proxy files.
            max_storage_bytes: Maximum storage quota in bytes.
            cleanup_threshold: Fraction triggering cleanup (0.0-1.0).
        """
        self._repo = proxy_repository
        self._executor = async_executor
        self._ws_manager = ws_manager
        self._job_queue = job_queue
        self._proxy_dir = proxy_dir
        self.max_storage_bytes = max_storage_bytes
        self.cleanup_threshold = cleanup_threshold

    async def generate_proxy(
        self,
        *,
        video_id: str,
        source_path: str,
        source_width: int,
        source_height: int,
        duration_us: int,
        job_id: str | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> ProxyFile:
        """Generate a proxy file for a source video.

        Selects quality based on source resolution, checks storage quota,
        evicts LRU proxies if needed, runs FFmpeg, and updates the DB.

        Args:
            video_id: Source video ID.
            source_path: Path to the source video.
            source_width: Source video width.
            source_height: Source video height.
            duration_us: Source duration in microseconds (for progress calculation).
            job_id: Optional job ID for progress reporting.
            cancel_event: Optional cancellation event.

        Returns:
            The created ProxyFile record.

        Raises:
            RuntimeError: If FFmpeg transcoding fails.
        """
        quality, target_w, target_h = select_proxy_quality(source_width, source_height)

        logger.info(
            "proxy_generation_started",
            job_id=job_id,
            video_id=video_id,
            quality=quality.value,
            target_resolution=f"{target_w}x{target_h}",
        )

        # Check storage quota and evict if necessary
        await self._check_quota_and_evict()

        # Compute source checksum
        source_checksum = await _run_in_thread(compute_file_checksum, source_path)

        # Create proxy directory
        proxy_dir = Path(self._proxy_dir)
        proxy_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(proxy_dir / f"{video_id}_{quality.value}.mp4")

        # Create pending proxy record
        from datetime import datetime, timezone

        proxy = ProxyFile(
            id=ProxyFile.new_id(),
            source_video_id=video_id,
            quality=quality,
            file_path=output_path,
            file_size_bytes=0,
            status=ProxyStatus.PENDING,
            source_checksum=source_checksum,
            generated_at=None,
            last_accessed_at=datetime.now(timezone.utc),
        )
        await self._repo.add(proxy)

        # Transition to generating
        await self._repo.update_status(proxy.id, ProxyStatus.GENERATING)

        # Build FFmpeg args
        if quality == _PASSTHROUGH_QUALITY:
            # Passthrough: no transcoding needed, just copy
            target_w = source_width
            target_h = source_height

        args = build_ffmpeg_args(source_path, output_path, target_w, target_h)

        # Build throttled progress callback
        progress_cb = self._make_progress_callback(
            job_id=job_id,
            video_id=video_id,
            quality=quality,
            target_resolution=f"{target_w}x{target_h}",
            duration_us=duration_us,
        )

        try:
            result = await self._executor.run(
                args,
                progress_callback=progress_cb,
                cancel_event=cancel_event,
            )

            if cancel_event and cancel_event.is_set():
                # Cleanup partial file on cancellation
                _remove_file_if_exists(output_path)
                await self._repo.update_status(proxy.id, ProxyStatus.FAILED)
                logger.info(
                    "proxy_generation_cancelled",
                    job_id=job_id,
                    video_id=video_id,
                )
                raise RuntimeError("Proxy generation cancelled")

            if result.returncode != 0:
                # Cleanup partial file on failure
                _remove_file_if_exists(output_path)
                await self._repo.update_status(proxy.id, ProxyStatus.FAILED)
                error_msg = result.stderr.decode("utf-8", errors="replace")[:500]
                logger.error(
                    "proxy_generation_failed",
                    job_id=job_id,
                    video_id=video_id,
                    quality=quality.value,
                    error=error_msg,
                )
                raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {error_msg}")

            # Get file size and mark as ready
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            await self._repo.update_status(proxy.id, ProxyStatus.READY, file_size_bytes=file_size)

            logger.info(
                "proxy_generation_complete",
                job_id=job_id,
                video_id=video_id,
                quality=quality.value,
                file_size_bytes=file_size,
            )

            # Send final completion progress event
            await self._send_progress(
                job_id=job_id,
                progress=1.0,
                status="complete",
                quality=quality.value,
                target_resolution=f"{target_w}x{target_h}",
            )

            # Re-fetch from repo to get updated fields
            updated = await self._repo.get(proxy.id)
            return updated if updated is not None else proxy

        except RuntimeError:
            raise
        except Exception:
            _remove_file_if_exists(output_path)
            await self._repo.update_status(proxy.id, ProxyStatus.FAILED)
            logger.error(
                "proxy_generation_failed",
                job_id=job_id,
                video_id=video_id,
                quality=quality.value,
                exc_info=True,
            )
            raise

    async def check_stale(self, proxy_id: str, source_path: str) -> bool:
        """Check if a proxy is stale by comparing source checksums.

        Args:
            proxy_id: The proxy file ID.
            source_path: Path to the current source video.

        Returns:
            True if the proxy was marked stale, False if current.

        Raises:
            ValueError: If the proxy is not found.
        """
        proxy = await self._repo.get(proxy_id)
        if proxy is None:
            raise ValueError(f"Proxy {proxy_id} not found")

        current_checksum = await _run_in_thread(compute_file_checksum, source_path)
        if current_checksum != proxy.source_checksum:
            await self._repo.update_status(proxy.id, ProxyStatus.STALE)
            logger.info(
                "proxy_marked_stale",
                proxy_id=proxy_id,
                video_id=proxy.source_video_id,
            )
            return True
        return False

    async def _check_quota_and_evict(self) -> None:
        """Check storage quota and evict LRU proxies if over threshold."""
        total = await self._repo.total_size_bytes()
        threshold = int(self.max_storage_bytes * self.cleanup_threshold)

        while total > threshold:
            oldest = await self._repo.get_oldest_accessed()
            if oldest is None:
                break

            # Delete the file
            _remove_file_if_exists(oldest.file_path)
            await self._repo.delete(oldest.id)

            logger.info(
                "proxy_evicted",
                proxy_id=oldest.id,
                video_id=oldest.source_video_id,
                file_size_bytes=oldest.file_size_bytes,
            )

            total = await self._repo.total_size_bytes()

    def _make_progress_callback(
        self,
        *,
        job_id: str | None,
        video_id: str,
        quality: ProxyQuality,
        target_resolution: str,
        duration_us: int,
    ) -> Any:
        """Create a throttled progress callback for FFmpeg progress events.

        Args:
            job_id: Job ID for progress reporting.
            video_id: Source video ID.
            quality: Proxy quality level.
            target_resolution: Target resolution string.
            duration_us: Source duration in microseconds.

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

            # Throttle: skip unless >=500ms or >=5% change
            time_delta = now - last_time
            progress_delta = progress - last_progress
            if time_delta < PROGRESS_MIN_INTERVAL_S and progress_delta < PROGRESS_MIN_DELTA:
                return

            last_progress = progress
            last_time = now

            await self._send_progress(
                job_id=job_id,
                progress=progress,
                status="running",
                quality=quality.value,
                target_resolution=target_resolution,
            )

        return on_progress

    async def _send_progress(
        self,
        *,
        job_id: str | None,
        progress: float,
        status: str,
        quality: str,
        target_resolution: str,
    ) -> None:
        """Send a JOB_PROGRESS event via WebSocket and update job queue.

        Args:
            job_id: Job ID.
            progress: Progress value 0.0-1.0.
            status: Job status string.
            quality: Proxy quality level string.
            target_resolution: Target resolution string.
        """
        if self._job_queue and job_id:
            self._job_queue.set_progress(job_id, progress)

        if self._ws_manager and job_id:
            await self._ws_manager.broadcast(
                build_event(
                    EventType.JOB_PROGRESS,
                    {
                        "job_id": job_id,
                        "progress": progress,
                        "status": status,
                        "proxy_quality": quality,
                        "target_resolution": target_resolution,
                    },
                )
            )


def make_proxy_handler(
    proxy_service: ProxyService,
) -> Any:
    """Create a proxy job handler for the job queue.

    Args:
        proxy_service: The proxy service instance.

    Returns:
        Async handler function compatible with the job queue.
    """

    async def handler(_job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a proxy generation job.

        Args:
            _job_type: Job type identifier (unused).
            payload: Must contain video_id, source_path, source_width,
                source_height, duration_us.

        Returns:
            Result dict with proxy_id and quality.
        """
        job_id = payload.get("_job_id")
        cancel_event = payload.get("_cancel_event")

        proxy = await proxy_service.generate_proxy(
            video_id=payload["video_id"],
            source_path=payload["source_path"],
            source_width=payload["source_width"],
            source_height=payload["source_height"],
            duration_us=payload["duration_us"],
            job_id=job_id,
            cancel_event=cancel_event,
        )

        return {
            "proxy_id": proxy.id,
            "quality": proxy.quality.value,
            "file_path": proxy.file_path,
        }

    return handler


def _remove_file_if_exists(path: str) -> None:
    """Remove a file if it exists, silently ignoring errors.

    Args:
        path: Path to the file to remove.
    """
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


async def _run_in_thread(fn: Any, *args: Any) -> Any:
    """Run a blocking function in a thread pool.

    Args:
        fn: The function to run.
        *args: Arguments to pass to the function.

    Returns:
        The function's return value.
    """
    import asyncio

    return await asyncio.to_thread(fn, *args)
