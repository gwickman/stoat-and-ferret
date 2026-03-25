"""Proxy management API endpoints.

Provides POST/GET/DELETE for single-video proxy lifecycle and
POST for batch proxy generation. Follows established router conventions
with DI via app.state and JSON:API-style error responses.
"""

from __future__ import annotations

import contextlib
import os
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from stoat_ferret.api.schemas.job import JobSubmitResponse
from stoat_ferret.api.services.proxy_service import PROXY_JOB_TYPE
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
from stoat_ferret.db.models import ProxyStatus
from stoat_ferret.db.proxy_repository import AsyncProxyRepository, SQLiteProxyRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["proxy"])


# ---------- Pydantic models ----------


class ProxyResponse(BaseModel):
    """Single proxy status response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_video_id: str
    status: str
    quality: str
    file_size_bytes: int
    generated_at: datetime | None = None


class ProxyDeleteResponse(BaseModel):
    """Response after deleting a proxy."""

    freed_bytes: int


class ProxyBatchRequest(BaseModel):
    """Request to generate proxies for multiple videos."""

    video_ids: list[str] = Field(..., min_length=1, description="List of video IDs")


class ProxyBatchResponse(BaseModel):
    """Response from batch proxy generation."""

    queued: list[str]
    skipped: list[str]


# ---------- Dependency injection ----------


async def get_proxy_repository(request: Request) -> AsyncProxyRepository:
    """Get proxy repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async proxy repository instance.
    """
    repo: AsyncProxyRepository | None = getattr(request.app.state, "proxy_repository", None)
    if repo is not None:
        return repo
    return SQLiteProxyRepository(request.app.state.db)


async def get_video_repository(request: Request) -> AsyncVideoRepository:
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


ProxyRepoDep = Annotated[AsyncProxyRepository, Depends(get_proxy_repository)]
VideoRepoDep = Annotated[AsyncVideoRepository, Depends(get_video_repository)]


# ---------- Endpoints ----------


@router.post(
    "/videos/{video_id}/proxy",
    response_model=JobSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_proxy(
    video_id: str,
    request: Request,
    proxy_repo: ProxyRepoDep,
    video_repo: VideoRepoDep,
) -> JobSubmitResponse:
    """Queue proxy generation for a video.

    Args:
        video_id: The source video ID.
        request: The FastAPI request object for accessing app state.
        proxy_repo: Proxy repository dependency.
        video_repo: Video repository dependency.

    Returns:
        Job submission response with job_id.

    Raises:
        HTTPException: 404 if video not found, 409 if proxy already exists.
    """
    video = await video_repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )

    # Check for existing proxy (any quality) that isn't failed/stale
    existing = await proxy_repo.list_by_video(video_id)
    active = [p for p in existing if p.status not in (ProxyStatus.FAILED, ProxyStatus.STALE)]
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PROXY_ALREADY_EXISTS",
                "message": f"Proxy already exists for video {video_id}",
            },
        )

    job_queue = request.app.state.job_queue
    job_id = await job_queue.submit(
        PROXY_JOB_TYPE,
        {
            "video_id": video_id,
            "source_path": video.path,
            "source_width": video.width,
            "source_height": video.height,
            "duration_us": int(video.duration_seconds * 1_000_000),
        },
    )
    logger.info("proxy_generation_queued", job_id=str(job_id), video_id=video_id)
    return JobSubmitResponse(job_id=job_id)


@router.get("/videos/{video_id}/proxy", response_model=ProxyResponse)
async def get_proxy_status(
    video_id: str,
    proxy_repo: ProxyRepoDep,
) -> ProxyResponse:
    """Get proxy status for a video.

    Args:
        video_id: The source video ID.
        proxy_repo: Proxy repository dependency.

    Returns:
        Proxy status response.

    Raises:
        HTTPException: 404 if no proxy found for video.
    """
    proxies = await proxy_repo.list_by_video(video_id)
    if not proxies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"No proxy found for video {video_id}",
            },
        )

    # Return the most relevant proxy (prefer ready, then generating/pending)
    proxy = proxies[0]
    for p in proxies:
        if p.status == ProxyStatus.READY:
            proxy = p
            break

    return ProxyResponse(
        id=proxy.id,
        source_video_id=proxy.source_video_id,
        status=proxy.status.value,
        quality=proxy.quality.value,
        file_size_bytes=proxy.file_size_bytes,
        generated_at=proxy.generated_at,
    )


@router.delete("/videos/{video_id}/proxy", response_model=ProxyDeleteResponse)
async def delete_proxy(
    video_id: str,
    proxy_repo: ProxyRepoDep,
) -> ProxyDeleteResponse:
    """Delete proxy file and DB record for a video.

    Args:
        video_id: The source video ID.
        proxy_repo: Proxy repository dependency.

    Returns:
        Response with freed_bytes count.

    Raises:
        HTTPException: 404 if no proxy found for video.
    """
    proxies = await proxy_repo.list_by_video(video_id)
    if not proxies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"No proxy found for video {video_id}",
            },
        )

    freed_bytes = 0
    for proxy in proxies:
        freed_bytes += proxy.file_size_bytes
        # Remove file from disk
        with contextlib.suppress(OSError):
            if os.path.exists(proxy.file_path):
                os.remove(proxy.file_path)
        await proxy_repo.delete(proxy.id)

    logger.info("proxy_deleted", video_id=video_id, freed_bytes=freed_bytes)
    return ProxyDeleteResponse(freed_bytes=freed_bytes)


@router.post(
    "/proxy/batch",
    response_model=ProxyBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_generate_proxies(
    batch_request: ProxyBatchRequest,
    request: Request,
    proxy_repo: ProxyRepoDep,
    video_repo: VideoRepoDep,
) -> ProxyBatchResponse:
    """Queue proxy generation for multiple videos, skipping those with ready proxies.

    Args:
        batch_request: Request with list of video IDs.
        request: The FastAPI request object for accessing app state.
        proxy_repo: Proxy repository dependency.
        video_repo: Video repository dependency.

    Returns:
        Response listing queued and skipped video IDs.
    """
    queued: list[str] = []
    skipped: list[str] = []
    job_queue = request.app.state.job_queue

    for vid_id in batch_request.video_ids:
        video = await video_repo.get(vid_id)
        if video is None:
            # Skip missing videos
            skipped.append(vid_id)
            continue

        existing = await proxy_repo.list_by_video(vid_id)
        active = [p for p in existing if p.status not in (ProxyStatus.FAILED, ProxyStatus.STALE)]
        if active:
            skipped.append(vid_id)
            continue

        await job_queue.submit(
            PROXY_JOB_TYPE,
            {
                "video_id": vid_id,
                "source_path": video.path,
                "source_width": video.width,
                "source_height": video.height,
                "duration_us": int(video.duration_seconds * 1_000_000),
            },
        )
        queued.append(vid_id)

    logger.info(
        "proxy_batch_queued",
        queued_count=len(queued),
        skipped_count=len(skipped),
    )
    return ProxyBatchResponse(queued=queued, skipped=skipped)
