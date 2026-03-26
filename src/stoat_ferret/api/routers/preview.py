"""Preview session management and HLS content serving endpoints.

Provides POST/GET/DELETE for preview session lifecycle plus
GET endpoints for HLS manifest and segment file serving.
Follows established router conventions with DI via app.state
and JSON:API-style error responses.
"""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Request, Response, status

from stoat_ferret.api.schemas.preview import (
    PreviewSeekRequest,
    PreviewSeekResponse,
    PreviewStartRequest,
    PreviewStartResponse,
    PreviewStatusResponse,
    PreviewStopResponse,
)
from stoat_ferret.db.clip_repository import AsyncClipRepository, AsyncSQLiteClipRepository
from stoat_ferret.db.models import PreviewQuality
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.preview.manager import (
    PreviewManager,
    SessionExpiredError,
    SessionLimitError,
    SessionNotFoundError,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["preview"])

# HLS media types
HLS_MANIFEST_CONTENT_TYPE = "application/vnd.apple.mpegurl"
HLS_SEGMENT_CONTENT_TYPE = "video/MP2T"


# ---------- Dependency helpers ----------


def _get_preview_manager(request: Request) -> PreviewManager:
    """Get preview manager from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        PreviewManager instance.

    Raises:
        HTTPException: 503 if preview manager is not available.
    """
    manager: PreviewManager | None = getattr(request.app.state, "preview_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "Preview service not available"},
        )
    return manager


async def _get_project_repository(request: Request) -> AsyncProjectRepository:
    """Get project repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async project repository instance.
    """
    repo: AsyncProjectRepository | None = getattr(request.app.state, "project_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteProjectRepository(request.app.state.db)


async def _get_clip_repository(request: Request) -> AsyncClipRepository:
    """Get clip repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async clip repository instance.
    """
    repo: AsyncClipRepository | None = getattr(request.app.state, "clip_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteClipRepository(request.app.state.db)


# ---------- Endpoints ----------


@router.post(
    "/projects/{project_id}/preview/start",
    response_model=PreviewStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_preview(
    project_id: str,
    request: Request,
    body: PreviewStartRequest | None = None,
) -> PreviewStartResponse:
    """Start a new preview session for a project.

    Validates that the project exists and has a non-empty timeline,
    then starts asynchronous HLS generation.

    Args:
        project_id: The project to preview.
        request: The FastAPI request object.
        body: Optional request body with quality settings.

    Returns:
        202 Accepted with session_id.

    Raises:
        HTTPException: 404 if project not found, 422 if timeline is empty,
            429 if session limit reached.
    """
    manager = _get_preview_manager(request)
    project_repo = await _get_project_repository(request)
    clip_repo = await _get_clip_repository(request)

    # Verify project exists
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    # Check for empty timeline
    clips = await clip_repo.list_by_project(project_id)
    if not clips:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_TIMELINE", "message": "Project has no clips on the timeline"},
        )

    # Determine quality level
    quality_str = body.quality if body else "medium"
    quality_map = {
        "low": PreviewQuality.LOW,
        "medium": PreviewQuality.MEDIUM,
        "high": PreviewQuality.HIGH,
    }
    quality = quality_map.get(quality_str, PreviewQuality.MEDIUM)

    # Use the first clip's source video path as input
    # (full timeline composition is handled by the filter graph)
    first_clip = clips[0]
    video_repo = getattr(request.app.state, "video_repository", None)
    input_path = ""
    if video_repo is not None:
        video = await video_repo.get(first_clip.source_video_id)
        if video is not None:
            input_path = video.path

    try:
        session = await manager.start(
            project_id=project_id,
            input_path=input_path,
            quality_level=quality,
        )
    except SessionLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "SESSION_LIMIT",
                "message": "Maximum concurrent preview sessions reached",
            },
        ) from None

    logger.info("preview_session_started", session_id=session.id, project_id=project_id)
    return PreviewStartResponse(session_id=session.id)


@router.get(
    "/preview/{session_id}",
    response_model=PreviewStatusResponse,
)
async def get_preview_status(
    session_id: str,
    request: Request,
) -> PreviewStatusResponse:
    """Get the current status of a preview session.

    When status is "ready", manifest_url is included in the response.

    Args:
        session_id: The preview session ID.
        request: The FastAPI request object.

    Returns:
        Session status with optional manifest_url.

    Raises:
        HTTPException: 404 if session not found.
    """
    manager = _get_preview_manager(request)

    try:
        session = await manager.get_status(session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found"},
        ) from None
    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_EXPIRED", "message": f"Session {session_id} has expired"},
        ) from None

    manifest_url = None
    if session.status.value == "ready" and session.manifest_path:
        manifest_url = f"/api/v1/preview/{session_id}/manifest.m3u8"

    return PreviewStatusResponse(
        session_id=session.id,
        status=session.status.value,
        manifest_url=manifest_url,
        error_message=session.error_message,
    )


@router.post(
    "/preview/{session_id}/seek",
    response_model=PreviewSeekResponse,
)
async def seek_preview(
    session_id: str,
    body: PreviewSeekRequest,
    request: Request,
) -> PreviewSeekResponse:
    """Seek to a new position in a preview session.

    Triggers regeneration of HLS segments from the new position.

    Args:
        session_id: The preview session ID.
        body: Seek request with position.
        request: The FastAPI request object.

    Returns:
        200 with status "seeking".

    Raises:
        HTTPException: 404 if session not found.
    """
    manager = _get_preview_manager(request)

    try:
        session = await manager.seek(
            session_id,
            input_path="",  # Regeneration uses session context
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found"},
        ) from None
    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_EXPIRED", "message": f"Session {session_id} has expired"},
        ) from None

    logger.info("preview_session_seek", session_id=session_id, position=body.position)
    return PreviewSeekResponse(
        session_id=session.id,
        status=session.status.value,
    )


@router.delete(
    "/preview/{session_id}",
    response_model=PreviewStopResponse,
)
async def stop_preview(
    session_id: str,
    request: Request,
) -> PreviewStopResponse:
    """Stop a preview session and clean up resources.

    Cancels any active generation, removes segment files,
    and deletes the session record.

    Args:
        session_id: The preview session ID.
        request: The FastAPI request object.

    Returns:
        200 with confirmation.

    Raises:
        HTTPException: 404 if session not found.
    """
    manager = _get_preview_manager(request)

    try:
        await manager.stop(session_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found"},
        ) from None

    logger.info("preview_session_stopped", session_id=session_id)
    return PreviewStopResponse(session_id=session_id)


@router.get(
    "/preview/{session_id}/manifest.m3u8",
)
async def get_manifest(
    session_id: str,
    request: Request,
) -> Response:
    """Serve the HLS manifest file for a preview session.

    Args:
        session_id: The preview session ID.
        request: The FastAPI request object.

    Returns:
        HLS manifest with Content-Type application/vnd.apple.mpegurl.

    Raises:
        HTTPException: 404 if session or manifest not found.
    """
    manager = _get_preview_manager(request)

    try:
        session = await manager.get_status(session_id)
    except (SessionNotFoundError, SessionExpiredError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found"},
        ) from None

    if not session.manifest_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_READY", "message": "Manifest not yet available"},
        )

    manifest_file = Path(session.manifest_path)
    if not manifest_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Manifest file not found on disk"},
        )

    content = manifest_file.read_text()
    return Response(content=content, media_type=HLS_MANIFEST_CONTENT_TYPE)


@router.get(
    "/preview/{session_id}/segment_{index}.ts",
)
async def get_segment(
    session_id: str,
    index: int,
    request: Request,
) -> Response:
    """Serve an HLS segment file for a preview session.

    Args:
        session_id: The preview session ID.
        index: The segment index number.
        request: The FastAPI request object.

    Returns:
        MPEG-TS segment with Content-Type video/MP2T.

    Raises:
        HTTPException: 404 if session or segment not found.
    """
    manager = _get_preview_manager(request)

    try:
        session = await manager.get_status(session_id)
    except (SessionNotFoundError, SessionExpiredError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found"},
        ) from None

    if not session.manifest_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_READY", "message": "Session not ready"},
        )

    # Segments are in the same directory as the manifest
    session_dir = Path(session.manifest_path).parent
    segment_file = session_dir / f"segment_{index:03d}.ts"

    if not segment_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Segment {index} not found",
            },
        )

    content = segment_file.read_bytes()
    return Response(content=content, media_type=HLS_SEGMENT_CONTENT_TYPE)
