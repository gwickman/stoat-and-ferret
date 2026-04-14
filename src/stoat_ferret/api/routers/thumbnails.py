"""Thumbnail strip API endpoints.

Provides POST/GET endpoints for thumbnail strip sprite sheet generation,
metadata retrieval, and image serving. Follows the same pattern as
proxy and preview endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from stoat_ferret.api.schemas.thumbnail import (
    ThumbnailStripGenerateRequest,
    ThumbnailStripGenerateResponse,
    ThumbnailStripMetadataResponse,
)
from stoat_ferret.api.services.thumbnail import ThumbnailService
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
from stoat_ferret.db.models import ThumbnailStrip

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["thumbnails"])


# ---------- Dependency injection ----------


async def _get_video_repository(request: Request) -> AsyncVideoRepository:
    """Get video repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async video repository instance.
    """
    repo: AsyncVideoRepository | None = getattr(request.app.state, "video_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteVideoRepository(request.app.state.db)


def _get_thumbnail_service(request: Request) -> ThumbnailService:
    """Get thumbnail service from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        ThumbnailService instance.

    Raises:
        HTTPException: 503 if service not available.
    """
    svc: ThumbnailService | None = getattr(request.app.state, "thumbnail_service", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "Thumbnail service not available"},
        )
    return svc


VideoRepoDep = Annotated[AsyncVideoRepository, Depends(_get_video_repository)]
ThumbnailServiceDep = Annotated[ThumbnailService, Depends(_get_thumbnail_service)]


# ---------- Endpoints ----------


@router.post(
    "/videos/{video_id}/thumbnails/strip",
    response_model=ThumbnailStripGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_strip(
    video_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    video_repo: VideoRepoDep,
    thumbnail_service: ThumbnailServiceDep,
    body: ThumbnailStripGenerateRequest | None = None,
) -> ThumbnailStripGenerateResponse:
    """Queue thumbnail strip generation for a video.

    Args:
        video_id: The source video ID.
        request: The FastAPI request object.
        background_tasks: FastAPI background task manager.
        video_repo: Video repository dependency.
        thumbnail_service: Thumbnail service dependency.
        body: Optional generation parameters.

    Returns:
        Response with strip_id and pending status.

    Raises:
        HTTPException: 404 if video not found.
    """
    video = await video_repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )

    params = body or ThumbnailStripGenerateRequest()
    strip_id = ThumbnailStrip.new_id()

    background_tasks.add_task(
        thumbnail_service.generate_strip,
        video_id=video_id,
        video_path=video.path,
        duration_seconds=video.duration_seconds,
        strip_id=strip_id,
        interval=params.interval_seconds,  # None = service default
        frame_width=params.frame_width if params.frame_width is not None else 160,
        frame_height=params.frame_height if params.frame_height is not None else 90,
    )

    logger.info("thumbnail_strip_generation_queued", strip_id=strip_id, video_id=video_id)
    return ThumbnailStripGenerateResponse(strip_id=strip_id, status="pending")


@router.get(
    "/videos/{video_id}/thumbnails/strip",
    response_model=ThumbnailStripMetadataResponse,
)
async def get_strip_metadata(
    video_id: str,
    thumbnail_service: ThumbnailServiceDep,
) -> ThumbnailStripMetadataResponse:
    """Get metadata for a video's thumbnail strip.

    Args:
        video_id: The source video ID.
        thumbnail_service: Thumbnail service dependency.

    Returns:
        Strip metadata including frame count, dimensions, columns, and rows.

    Raises:
        HTTPException: 404 if no strip exists for this video.
    """
    strip = await thumbnail_service.get_strip(video_id)
    if strip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "STRIP_NOT_FOUND",
                "message": f"No thumbnail strip for video {video_id}",
            },
        )

    return ThumbnailStripMetadataResponse(
        strip_id=strip.id,
        video_id=strip.video_id,
        status=strip.status.value,
        frame_count=strip.frame_count,
        frame_width=strip.frame_width,
        frame_height=strip.frame_height,
        interval_seconds=strip.interval_seconds,
        columns=strip.columns,
        rows=strip.rows,
    )


@router.get("/videos/{video_id}/thumbnails/strip.jpg")
async def get_strip_image(
    video_id: str,
    thumbnail_service: ThumbnailServiceDep,
) -> FileResponse:
    """Serve the thumbnail strip sprite sheet as a JPEG image.

    Args:
        video_id: The source video ID.
        thumbnail_service: Thumbnail service dependency.

    Returns:
        JPEG image response.

    Raises:
        HTTPException: 404 if no strip exists or file not ready.
    """
    strip = await thumbnail_service.get_strip(video_id)
    if strip is None or strip.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "STRIP_NOT_FOUND",
                "message": f"No thumbnail strip for video {video_id}",
            },
        )

    file_path = Path(strip.file_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "STRIP_NOT_FOUND",
                "message": f"Thumbnail strip file not found for video {video_id}",
            },
        )

    return FileResponse(str(file_path), media_type="image/jpeg")
