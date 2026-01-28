"""Video endpoints for listing and retrieving videos."""

from __future__ import annotations

import contextlib
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from stoat_ferret.api.schemas.video import (
    ScanRequest,
    ScanResponse,
    VideoListResponse,
    VideoResponse,
    VideoSearchResponse,
)
from stoat_ferret.api.services.scan import scan_directory
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


async def get_repository(request: Request) -> AsyncVideoRepository:
    """Get video repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async video repository instance.
    """
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


@router.post("/scan", response_model=ScanResponse)
async def scan_videos(
    request: ScanRequest,
    repo: RepoDep,
) -> ScanResponse:
    """Scan directory for video files.

    Walks the specified directory, finds video files by extension,
    extracts metadata using ffprobe, and adds/updates them in the database.

    Args:
        request: Scan request with directory path and recursion flag.
        repo: Video repository dependency.

    Returns:
        Scan results summary with counts of scanned, new, updated, skipped files.

    Raises:
        HTTPException: 400 if path is not a valid directory.
    """
    try:
        return await scan_directory(
            path=request.path,
            recursive=request.recursive,
            repository=repo,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": str(e)},
        ) from None


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
