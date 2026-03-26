"""Waveform API endpoints.

Provides POST/GET endpoints for waveform generation (PNG or JSON),
metadata retrieval, and image/data serving. Follows the same pattern
as the thumbnail strip API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse

from stoat_ferret.api.schemas.waveform import (
    WaveformGenerateRequest,
    WaveformGenerateResponse,
    WaveformMetadataResponse,
    WaveformSample,
    WaveformSamplesResponse,
)
from stoat_ferret.api.services.waveform import WaveformService
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
from stoat_ferret.db.models import Waveform, WaveformFormat

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["waveforms"])


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


def _get_waveform_service(request: Request) -> WaveformService:
    """Get waveform service from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        WaveformService instance.

    Raises:
        HTTPException: 503 if service not available.
    """
    svc: WaveformService | None = getattr(request.app.state, "waveform_service", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "Waveform service not available"},
        )
    return svc


VideoRepoDep = Annotated[AsyncVideoRepository, Depends(_get_video_repository)]
WaveformServiceDep = Annotated[WaveformService, Depends(_get_waveform_service)]


# ---------- Endpoints ----------


@router.post(
    "/videos/{video_id}/waveform",
    response_model=WaveformGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_waveform(
    video_id: str,
    background_tasks: BackgroundTasks,
    video_repo: VideoRepoDep,
    waveform_service: WaveformServiceDep,
    body: WaveformGenerateRequest | None = None,
) -> WaveformGenerateResponse:
    """Queue waveform generation for a video.

    Args:
        video_id: The source video ID.
        background_tasks: FastAPI background task manager.
        video_repo: Video repository dependency.
        waveform_service: Waveform service dependency.
        body: Optional generation parameters with format selection.

    Returns:
        Response with waveform_id and pending status.

    Raises:
        HTTPException: 404 if video not found.
    """
    video = await video_repo.get(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Video {video_id} not found"},
        )

    params = body or WaveformGenerateRequest()
    fmt = WaveformFormat(params.format)
    waveform_id = Waveform.new_id()

    if fmt == WaveformFormat.PNG:
        background_tasks.add_task(
            waveform_service.generate_png,
            video_id=video_id,
            video_path=video.path,
            duration_seconds=video.duration_seconds,
            waveform_id=waveform_id,
        )
    else:
        background_tasks.add_task(
            waveform_service.generate_json,
            video_id=video_id,
            video_path=video.path,
            duration_seconds=video.duration_seconds,
            waveform_id=waveform_id,
        )

    logger.info(
        "waveform_generation_queued",
        waveform_id=waveform_id,
        video_id=video_id,
        format=params.format,
    )
    return WaveformGenerateResponse(waveform_id=waveform_id, status="pending")


@router.get(
    "/videos/{video_id}/waveform",
    response_model=WaveformMetadataResponse,
)
async def get_waveform_metadata(
    video_id: str,
    waveform_service: WaveformServiceDep,
    format: str = "png",  # noqa: A002
) -> WaveformMetadataResponse:
    """Get metadata for a video's waveform.

    Args:
        video_id: The source video ID.
        waveform_service: Waveform service dependency.
        format: Waveform format to query ("png" or "json").

    Returns:
        Waveform metadata including format, duration, channels, samples_per_second.

    Raises:
        HTTPException: 404 if no waveform exists for this video and format.
    """
    fmt = WaveformFormat(format)
    waveform = waveform_service.get_waveform(video_id, fmt)
    if waveform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "WAVEFORM_NOT_FOUND",
                "message": f"No waveform for video {video_id} in format {format}",
            },
        )

    # samples_per_second: 0 for PNG (image), 10 for JSON (amplitude data)
    samples_per_second = 10 if fmt == WaveformFormat.JSON else 0

    return WaveformMetadataResponse(
        waveform_id=waveform.id,
        video_id=waveform.video_id,
        status=waveform.status.value,
        format=waveform.format.value,
        duration=waveform.duration,
        channels=waveform.channels,
        samples_per_second=samples_per_second,
    )


@router.get("/videos/{video_id}/waveform.png")
async def get_waveform_image(
    video_id: str,
    waveform_service: WaveformServiceDep,
) -> FileResponse:
    """Serve the waveform as a PNG image.

    Args:
        video_id: The source video ID.
        waveform_service: Waveform service dependency.

    Returns:
        PNG image response.

    Raises:
        HTTPException: 404 if no waveform exists or file not ready.
    """
    waveform = waveform_service.get_waveform(video_id, WaveformFormat.PNG)
    if waveform is None or waveform.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "WAVEFORM_NOT_FOUND",
                "message": f"No PNG waveform for video {video_id}",
            },
        )

    file_path = Path(waveform.file_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "WAVEFORM_NOT_FOUND",
                "message": f"Waveform file not found for video {video_id}",
            },
        )

    return FileResponse(str(file_path), media_type="image/png")


@router.get(
    "/videos/{video_id}/waveform.json",
    response_model=WaveformSamplesResponse,
)
async def get_waveform_json(
    video_id: str,
    waveform_service: WaveformServiceDep,
) -> JSONResponse:
    """Serve waveform amplitude data as JSON.

    Args:
        video_id: The source video ID.
        waveform_service: Waveform service dependency.

    Returns:
        JSON response with samples array containing Peak_level and RMS_level values.

    Raises:
        HTTPException: 404 if no JSON waveform exists or file not ready.
    """
    waveform = waveform_service.get_waveform(video_id, WaveformFormat.JSON)
    if waveform is None or waveform.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "WAVEFORM_NOT_FOUND",
                "message": f"No JSON waveform for video {video_id}",
            },
        )

    file_path = Path(waveform.file_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "WAVEFORM_NOT_FOUND",
                "message": f"Waveform data file not found for video {video_id}",
            },
        )

    raw_data = json.loads(file_path.read_text())
    samples = [WaveformSample(**s) for s in raw_data.get("frames", [])]

    return JSONResponse(
        content=WaveformSamplesResponse(
            video_id=raw_data.get("video_id", video_id),
            channels=raw_data.get("channels", waveform.channels),
            samples_per_second=raw_data.get("samples_per_second", 10),
            samples=samples,
        ).model_dump()
    )
