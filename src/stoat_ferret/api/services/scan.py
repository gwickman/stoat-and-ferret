"""Directory scanning service."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from stoat_ferret.api.schemas.video import ScanError, ScanResponse
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.db.async_repository import AsyncVideoRepository
from stoat_ferret.db.models import Video
from stoat_ferret.ffmpeg.probe import ffprobe_video

if TYPE_CHECKING:
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
) -> Callable[[str, dict[str, Any]], Awaitable[Any]]:
    """Create a scan job handler bound to a repository.

    Args:
        repository: Video repository for storing scan results.
        thumbnail_service: Optional thumbnail service for generating thumbnails.
        ws_manager: Optional WebSocket manager for broadcasting scan events.
        queue: Optional job queue for progress reporting.

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

        # Build progress callback if queue and job_id are available
        progress_callback: Callable[[float], None] | None = None
        if queue and job_id:

            def progress_callback(value: float) -> None:
                queue.set_progress(job_id, value)

        if ws_manager:
            await ws_manager.broadcast(build_event(EventType.SCAN_STARTED, {"path": scan_path}))

        result = await scan_directory(
            path=scan_path,
            recursive=payload.get("recursive", True),
            repository=repository,
            thumbnail_service=thumbnail_service,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )

        if ws_manager:
            await ws_manager.broadcast(
                build_event(
                    EventType.SCAN_COMPLETED,
                    {"path": scan_path, "video_count": result.new + result.updated},
                )
            )

        return result.model_dump()

    return handler


async def scan_directory(
    path: str,
    recursive: bool,
    repository: AsyncVideoRepository,
    thumbnail_service: ThumbnailService | None = None,
    *,
    progress_callback: Callable[[float], None] | None = None,
    cancel_event: asyncio.Event | None = None,
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
        progress_callback: Optional callback invoked with progress 0.0-1.0 after each file.
        cancel_event: Optional event; when set, scan breaks and returns partial results.

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

    for file_path in video_files:
        if cancel_event and cancel_event.is_set():
            logger.info("scan_cancelled", path=path, processed=processed, total=total_files)
            break

        processed += 1
        str_path = str(file_path.absolute())

        try:
            # Check if already exists
            existing = await repository.get_by_path(str_path)

            # Probe video metadata
            metadata = await ffprobe_video(str_path)

            video_id = existing.id if existing else Video.new_id()

            # Generate thumbnail if service is available
            thumbnail_path: str | None = None
            if thumbnail_service is not None:
                thumbnail_path = thumbnail_service.generate(str_path, video_id)

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
            else:
                await repository.add(video)
                new += 1

        except Exception as e:
            errors.append(ScanError(path=str_path, error=str(e)))

        if progress_callback:
            progress_callback(processed / total_files)

    scanned = processed
    skipped = scanned - new - updated - len(errors)

    return ScanResponse(
        scanned=scanned,
        new=new,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )
