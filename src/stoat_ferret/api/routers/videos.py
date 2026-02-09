"""Video endpoints for listing and retrieving videos."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from stoat_ferret.api.schemas.job import JobSubmitResponse
from stoat_ferret.api.schemas.video import (
    ScanRequest,
    VideoListResponse,
    VideoResponse,
    VideoSearchResponse,
)
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, validate_scan_path
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)

_PLACEHOLDER_PATH = (
    Path(__file__).resolve().parent.parent.parent / "static" / "placeholder-thumb.jpg"
)

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


async def get_repository(request: Request) -> AsyncVideoRepository:
    """Get video repository from app state.

    Returns an injected repository if one was provided to create_app(),
    otherwise constructs a SQLite repository from the database connection.

    Args:
        request: The FastAPI request object.

    Returns:
        Async video repository instance.
    """
    repo: AsyncVideoRepository | None = getattr(request.app.state, "video_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteVideoRepository(request.app.state.db)


# Type alias for repository dependency
RepoDep = Annotated[AsyncVideoRepository, Depends(get_repository)]


@router.get("", response_model=VideoListResponse)
async def list_videos(
    repo: RepoDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VideoListResponse:
    """List videos with pagination.

    Args:
        limit: Maximum number of videos to return (1-100, default 20).
        offset: Number of videos to skip (default 0).
        repo: Video repository dependency.

    Returns:
        Paginated list of videos.
    """
    videos = await repo.list_videos(limit=limit, offset=offset)

    return VideoListResponse(
        videos=[VideoResponse.model_validate(v) for v in videos],
        total=len(videos),
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=VideoSearchResponse)
async def search_videos(
    repo: RepoDep,
    q: Annotated[str, Query(min_length=1, description="Search query")],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> VideoSearchResponse:
    """Search videos by filename or path.

    Args:
        repo: Video repository dependency.
        q: Search query string.
        limit: Maximum number of results to return (1-100, default 20).

    Returns:
        Search results with query echoed back.
    """
    videos = await repo.search(q, limit=limit)

    return VideoSearchResponse(
        videos=[VideoResponse.model_validate(v) for v in videos],
        total=len(videos),
        query=q,
    )


@router.get("/{video_id}/thumbnail")
async def get_thumbnail(
    video_id: str,
    repo: RepoDep,
) -> FileResponse:
    """Get thumbnail image for a video.

    Returns the generated thumbnail if available, or a placeholder image
    if thumbnail generation failed or hasn't been run.

    Args:
        video_id: The unique video identifier.
        repo: Video repository dependency.

    Returns:
        JPEG image response.

    Raises:
        HTTPException: 404 if video not found.
    """
    video = await repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )

    if video.thumbnail_path and Path(video.thumbnail_path).is_file():
        return FileResponse(video.thumbnail_path, media_type="image/jpeg")

    return FileResponse(str(_PLACEHOLDER_PATH), media_type="image/jpeg")


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    repo: RepoDep,
) -> VideoResponse:
    """Get video by ID.

    Args:
        video_id: The unique video identifier.
        repo: Video repository dependency.

    Returns:
        Video details.

    Raises:
        HTTPException: 404 if video not found.
    """
    video = await repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )
    return VideoResponse.model_validate(video)


@router.post("/scan", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def scan_videos(
    scan_request: ScanRequest,
    request: Request,
) -> JobSubmitResponse:
    """Submit a directory scan as an async job.

    Creates a scan job and returns the job ID immediately.
    Use GET /api/v1/jobs/{job_id} to poll for status and results.

    Args:
        scan_request: Scan request with directory path and recursion flag.
        request: The FastAPI request object for accessing app state.

    Returns:
        Job submission response with the job ID.

    Raises:
        HTTPException: 400 if path is not a valid directory.
    """
    path = scan_request.path
    if not os.path.isdir(path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": f"Not a directory: {path}"},
        )

    settings = get_settings()
    error = validate_scan_path(path, settings.allowed_scan_roots)
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PATH_NOT_ALLOWED", "message": error},
        )

    job_queue = request.app.state.job_queue
    job_id = await job_queue.submit(
        SCAN_JOB_TYPE,
        {"path": path, "recursive": scan_request.recursive},
    )
    return JobSubmitResponse(job_id=job_id)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    repo: RepoDep,
    delete_file: Annotated[bool, Query(description="Also delete source file from disk")] = False,
) -> Response:
    """Delete video from library.

    Args:
        video_id: The unique video identifier.
        repo: Video repository dependency.
        delete_file: If True, also delete the source file from disk.

    Returns:
        Empty response with 204 status.

    Raises:
        HTTPException: 404 if video not found.
    """
    video = await repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )

    await repo.delete(video_id)

    if delete_file and os.path.exists(video.path):
        with contextlib.suppress(OSError):
            os.remove(video.path)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
