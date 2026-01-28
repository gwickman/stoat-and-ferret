"""Video endpoints for listing and retrieving videos."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from stoat_ferret.api.schemas.video import VideoListResponse, VideoResponse
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
