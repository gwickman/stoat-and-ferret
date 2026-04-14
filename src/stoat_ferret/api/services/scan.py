"""Directory scanning service."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from stoat_ferret.api.schemas.video import ScanError, ScanResponse
from stoat_ferret.api.services.proxy_service import PROXY_JOB_TYPE
from stoat_ferret.api.settings import get_settings
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.db.async_repository import AsyncVideoRepository
from stoat_ferret.db.models import ProxyStatus, Video
from stoat_ferret.ffmpeg.probe import ffprobe_video

if TYPE_CHECKING:
    from stoat_ferret.api.services.proxy_service import ProxyService
    from stoat_ferret.api.services.thumbnail import ThumbnailService
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.jobs.queue import AsyncJobQueue

logger = structlog.get_logger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}


def validate_scan_path(path: str, allowed_roots: list[str]) -> str | None:
    """Check that a scan path falls under an allowed root directory.

    Args:
        path: The directory path to validate.
        allowed_roots: List of allowed root directories. Empty list allows all.

    Returns:
        An error message string if the path is not allowed, or None if valid.
    """
    if not allowed_roots:
        return None

    resolved = Path(path).resolve()
    for root in allowed_roots:
        root_resolved = Path(root).resolve()
        try:
            resolved.relative_to(root_resolved)
            return None
        except ValueError:
            continue

    return f"Path '{path}' is not under any allowed scan root"


SCAN_JOB_TYPE = "scan"


def make_scan_handler(
    repository: AsyncVideoRepository,
    thumbnail_service: ThumbnailService | None = None,
    ws_manager: ConnectionManager | None = None,
    queue: AsyncJobQueue | None = None,
    proxy_service: ProxyService | None = None,
) -> Callable[[str, dict[str, Any]], Awaitable[Any]]:
    """Create a scan job handler bound to a repository.

    Args:
        repository: Video repository for storing scan results.
        thumbnail_service: Optional thumbnail service for generating thumbnails.
        ws_manager: Optional WebSocket manager for broadcasting scan events.
        queue: Optional job queue for progress reporting.
        proxy_service: Optional proxy service for auto-generating proxies.

    Returns:
        Async handler function compatible with the job queue.
    """

    async def handler(_job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a scan job.

        Args:
            _job_type: Job type identifier (unused).
            payload: Must contain 'path' and optionally 'recursive'.

        Returns:
            Scan results as a dict.
        """
        scan_path = payload["path"]
        job_id = payload.get("_job_id")
        cancel_event: asyncio.Event | None = payload.get("_cancel_event")
        logger.info("scan_handler_started", job_id=str(job_id), path=str(scan_path))

        # Build progress callback if queue/job_id or ws_manager are available
        progress_callback: Callable[[float], Awaitable[None]] | None = None
        if (queue and job_id) or ws_manager:

            async def progress_callback(value: float) -> None:
                if queue and job_id:
                    queue.set_progress(job_id, value)
                if ws_manager and job_id:
                    await ws_manager.broadcast(
                        build_event(
                            EventType.JOB_PROGRESS,
                            {"job_id": str(job_id), "progress": value, "status": "running"},
                        )
                    )

        if ws_manager:
            logger.info("scan_broadcast_started", path=str(scan_path))
            await ws_manager.broadcast(build_event(EventType.SCAN_STARTED, {"path": scan_path}))

        video_ids: list[str] = []
        result = await scan_directory(
            path=scan_path,
            recursive=payload.get("recursive", True),
            repository=repository,
            thumbnail_service=thumbnail_service,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            video_ids_out=video_ids,
        )

        # Auto-queue proxy generation for new videos if enabled
        if proxy_service is not None and queue is not None:
            await _auto_queue_proxies(
                result=result,
                repository=repository,
                proxy_service=proxy_service,
                queue=queue,
                video_ids=video_ids,
            )

        # Broadcast SCAN_COMPLETED first, then JOB_PROGRESS(complete) last.
        # When rapid WebSocket messages are batched by React, only the final
        # setLastMessage survives.  useJobProgress filters for "job_progress",
        # so it must be the last message in the burst.
        if ws_manager:
            logger.info("scan_broadcast_completed", path=str(scan_path))
            await ws_manager.broadcast(
                build_event(
                    EventType.SCAN_COMPLETED,
                    {"path": scan_path, "video_count": result.new + result.updated},
                )
            )

        if ws_manager and job_id:
            await ws_manager.broadcast(
                build_event(
                    EventType.JOB_PROGRESS,
                    {"job_id": str(job_id), "progress": 1.0, "status": "complete"},
                )
            )

        return result.model_dump()

    return handler


async def _auto_queue_proxies(
    *,
    result: ScanResponse,
    repository: AsyncVideoRepository,
    proxy_service: ProxyService,
    queue: AsyncJobQueue,
    video_ids: list[str],
) -> None:
    """Auto-queue proxy generation for new videos and detect stale proxies.

    Checks the STOAT_PROXY_AUTO_GENERATE setting. When enabled, queues proxy
    generation jobs for newly discovered videos. Also checks existing proxies
    for staleness by comparing source checksums.

    Args:
        result: The scan result containing counts.
        repository: Video repository for looking up video metadata.
        proxy_service: Proxy service for stale detection.
        queue: Job queue for submitting proxy generation jobs.
        video_ids: IDs of videos discovered during the scan.
    """
    settings = get_settings()

    if not settings.proxy_auto_generate:
        logger.info(
            "proxy_auto_queue_skipped",
            video_count=len(video_ids),
            reason="auto_generate_disabled",
        )
        return

    if shutil.which("ffmpeg") is None:
        logger.warning(
            "proxy_auto_queue_skipped",
            video_count=len(video_ids),
            reason="ffmpeg_unavailable",
        )
        return

    logger.info(
        "proxy_auto_queue_started",
        video_count=len(video_ids),
        new_videos=result.new,
        updated_videos=result.updated,
    )

    queued_count = 0
    stale_count = 0

    for video_id in video_ids:
        video = await repository.get(video_id)
        if video is None:
            continue

        # Check for stale proxies on existing videos
        existing_proxies = await proxy_service.list_by_video(video.id)
        for existing_proxy in existing_proxies:
            if existing_proxy.status == ProxyStatus.READY:
                try:
                    was_stale = await proxy_service.check_stale(existing_proxy.id, video.path)
                    if was_stale:
                        stale_count += 1
                        logger.info(
                            "proxy_auto_queue_stale_detected",
                            video_id=video.id,
                            proxy_id=existing_proxy.id,
                        )
                except Exception:
                    logger.warning(
                        "proxy_auto_queue_stale_check_failed",
                        video_id=video.id,
                        proxy_id=existing_proxy.id,
                        exc_info=True,
                    )

        # Queue proxy generation for videos without any proxy
        if not existing_proxies:
            try:
                await queue.submit(
                    PROXY_JOB_TYPE,
                    {
                        "video_id": video.id,
                        "source_path": video.path,
                        "source_width": video.width,
                        "source_height": video.height,
                        "duration_us": int(video.duration_seconds * 1_000_000),
                    },
                )
                queued_count += 1
                logger.info(
                    "proxy_auto_queue_started",
                    video_id=video.id,
                    filename=video.filename,
                )
            except Exception:
                logger.warning(
                    "proxy_auto_queue_failed",
                    video_id=video.id,
                    exc_info=True,
                )

    logger.info(
        "proxy_auto_queue_complete",
        video_count=len(video_ids),
        queued=queued_count,
        stale_detected=stale_count,
    )


async def scan_directory(
    path: str,
    recursive: bool,
    repository: AsyncVideoRepository,
    thumbnail_service: ThumbnailService | None = None,
    *,
    progress_callback: Callable[[float], Awaitable[None]] | None = None,
    cancel_event: asyncio.Event | None = None,
    video_ids_out: list[str] | None = None,
) -> ScanResponse:
    """Scan directory for video files.

    Walks the specified directory (optionally recursively), finds video files
    by extension, extracts metadata using ffprobe, and adds/updates them in
    the repository. Optionally generates thumbnails for each video.

    Args:
        path: Directory path to scan.
        recursive: Whether to scan subdirectories.
        repository: Video repository for storing results.
        thumbnail_service: Optional thumbnail service for generating thumbnails.
        progress_callback: Optional async callback invoked with progress 0.0-1.0 after each file.
        cancel_event: Optional event; when set, scan breaks and returns partial results.
        video_ids_out: Optional list to collect IDs of all processed videos.

    Returns:
        ScanResponse with counts of scanned, new, updated, skipped files and errors.

    Raises:
        ValueError: If path is not a valid directory.
    """
    processed = 0
    new = 0
    updated = 0
    errors: list[ScanError] = []

    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {path}")

    pattern = "**/*" if recursive else "*"
    video_files = [
        f for f in root.glob(pattern) if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ]
    total_files = len(video_files)
    logger.info(
        "scan_files_enumerated",
        path=str(root),
        file_count=total_files,
        recursive=recursive,
    )

    for file_path in video_files:
        if cancel_event and cancel_event.is_set():
            logger.info("scan_cancelled", path=path, processed=processed, total=total_files)
            break

        processed += 1
        str_path = str(file_path.absolute())
        logger.debug(
            "scan_probing_file",
            file=str_path,
            index=processed,
            total=total_files,
        )

        try:
            # Check if already exists
            existing = await repository.get_by_path(str_path)

            # Probe video metadata
            metadata = await ffprobe_video(str_path)

            video_id = existing.id if existing else Video.new_id()

            if video_ids_out is not None:
                video_ids_out.append(video_id)

            # Generate thumbnail if service is available
            thumbnail_path: str | None = None
            if thumbnail_service is not None:
                thumbnail_path = await asyncio.to_thread(
                    thumbnail_service.generate, str_path, video_id
                )

            video = Video(
                id=video_id,
                path=str_path,
                filename=file_path.name,
                duration_frames=metadata.duration_frames,
                frame_rate_numerator=metadata.frame_rate_numerator,
                frame_rate_denominator=metadata.frame_rate_denominator,
                width=metadata.width,
                height=metadata.height,
                video_codec=metadata.video_codec,
                audio_codec=metadata.audio_codec,
                file_size=file_path.stat().st_size,
                thumbnail_path=thumbnail_path,
                created_at=existing.created_at if existing else datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            if existing:
                await repository.update(video)
                updated += 1
                logger.info("scan_video_updated", video_id=str(video_id), file=file_path.name)
            else:
                await repository.add(video)
                new += 1
                logger.info("scan_video_added", video_id=str(video_id), file=file_path.name)

        except Exception as e:
            logger.error("scan_file_error", file=str_path, error=str(e), exc_info=True)
            errors.append(ScanError(path=str_path, error=str(e)))

        if progress_callback:
            await progress_callback(processed / total_files)

    scanned = processed
    skipped = scanned - new - updated - len(errors)
    logger.info(
        "scan_directory_complete",
        path=str(root),
        scanned=scanned,
        new=new,
        updated=updated,
        error_count=len(errors),
    )

    return ScanResponse(
        scanned=scanned,
        new=new,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )
