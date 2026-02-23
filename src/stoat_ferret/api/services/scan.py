"""Directory scanning service."""

from __future__ import annotations

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
) -> Callable[[str, dict[str, Any]], Awaitable[Any]]:
    """Create a scan job handler bound to a repository.

    Args:
        repository: Video repository for storing scan results.
        thumbnail_service: Optional thumbnail service for generating thumbnails.
        ws_manager: Optional WebSocket manager for broadcasting scan events.

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

        if ws_manager:
            await ws_manager.broadcast(build_event(EventType.SCAN_STARTED, {"path": scan_path}))

        result = await scan_directory(
            path=scan_path,
            recursive=payload.get("recursive", True),
            repository=repository,
            thumbnail_service=thumbnail_service,
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

    Returns:
        ScanResponse with counts of scanned, new, updated, skipped files and errors.

    Raises:
        ValueError: If path is not a valid directory.
    """
    scanned = 0
    new = 0
    updated = 0
    errors: list[ScanError] = []

    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {path}")

    pattern = "**/*" if recursive else "*"
    for file_path in root.glob(pattern):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        scanned += 1
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

    skipped = scanned - new - updated - len(errors)

    return ScanResponse(
        scanned=scanned,
        new=new,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )
