# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Preview session management and HLS content serving endpoints.

Provides POST/GET/DELETE for preview session lifecycle plus
GET endpoints for HLS manifest and segment file serving.
Follows established router conventions with DI via app.state
and JSON:API-style error responses.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Request, Response, status

from stoat_ferret.api.schemas.preview import (
    PreviewCacheClearResponse,
    PreviewCacheStatusResponse,
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
from stoat_ferret.preview.cache import PreviewCache
from stoat_ferret.preview.manager import (
    InvalidTransitionError,
    PreviewManager,
    SessionExpiredError,
    SessionLimitError,
    SessionNotFoundError,
    resolve_transitions_by_clip_a_id,
)
from stoat_ferret_core import (
    ClipWithEffects,
    RenderEffect,
    RenderGraphTranslator,
    RenderTransition,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["preview"])


def _build_preview_render_effects(
    clip: object, effect_registry: object | None
) -> list[RenderEffect]:
    """Build RenderEffect list for a clip in preview mode.

    Wraps the render worker helper to gracefully skip effects that cannot be
    applied in preview context (e.g. convolution_reverb, unknown types).
    Returns [RenderEffect.none()] when no applicable effects are found.
    """
    try:
        from stoat_ferret.render.worker import _build_clip_render_effects

        video_effects, _ = _build_clip_render_effects(clip, effect_registry)  # type: ignore[arg-type]
        return video_effects
    except Exception as exc:
        logger.warning(
            "preview_clip_effect_skipped",
            clip_id=getattr(clip, "id", "?"),
            reason=str(exc),
        )
        return [RenderEffect.none()]


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


def _get_project_repository(request: Request) -> AsyncProjectRepository:
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


def _get_clip_repository(request: Request) -> AsyncClipRepository:
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


def _get_preview_cache(request: Request) -> PreviewCache:
    """Get preview cache from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        PreviewCache instance.

    Raises:
        HTTPException: 503 if preview cache is not available.
    """
    cache: PreviewCache | None = getattr(request.app.state, "preview_cache", None)
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "Preview cache not available"},
        )
    return cache


def _check_ffmpeg_available() -> None:
    """Raise 503 if FFmpeg is not available on the system.

    Raises:
        HTTPException: 503 with FFMPEG_UNAVAILABLE code if ffmpeg not in PATH.
    """
    if shutil.which("ffmpeg") is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "FFMPEG_UNAVAILABLE",
                "message": "FFmpeg is not available. Preview functionality requires FFmpeg.",
            },
        )


# ---------- Endpoints ----------


@router.get(
    "/preview/cache",
)
async def get_cache_status(
    request: Request,
) -> PreviewCacheStatusResponse:
    """Get current preview cache status metrics.

    Returns cache usage statistics including session count,
    byte usage, and list of active session IDs.

    Args:
        request: The FastAPI request object.

    Returns:
        Cache status with usage metrics.
    """
    cache = _get_preview_cache(request)
    cache_status = await cache.status()

    return PreviewCacheStatusResponse(
        active_sessions=len(cache_status.active_sessions),
        used_bytes=cache_status.used_bytes,
        max_bytes=cache_status.max_bytes,
        usage_percent=cache_status.usage_percent,
        sessions=cache_status.active_sessions,
    )


@router.delete(
    "/preview/cache",
)
async def clear_cache(
    request: Request,
) -> PreviewCacheClearResponse:
    """Clear all cached preview sessions and free disk space.

    Removes all cached session data from disk and resets the cache.

    Args:
        request: The FastAPI request object.

    Returns:
        Number of cleared sessions and bytes freed.
    """
    cache = _get_preview_cache(request)
    cleared, freed = await cache.clear_all()

    logger.info("preview_cache_api_cleared", cleared_sessions=cleared, freed_bytes=freed)
    return PreviewCacheClearResponse(cleared_sessions=cleared, freed_bytes=freed)


@router.post(
    "/projects/{project_id}/preview/start",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "Project not found"},
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/HTTPValidationError"}}
            },
        },
        429: {"description": "Session limit reached"},
        503: {"description": "FFmpeg unavailable or preview service not running"},
    },
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
    _check_ffmpeg_available()
    manager = _get_preview_manager(request)
    project_repo = _get_project_repository(request)
    clip_repo = _get_clip_repository(request)

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

    # Build multi-clip composition via shared RenderGraphTranslator path (BL-838 AC-8).
    video_repo = getattr(request.app.state, "video_repository", None)
    effect_registry = getattr(request.app.state, "effect_registry", None)
    cwe_list: list[ClipWithEffects] = []
    input_paths: list[str] = []
    in_point_secs_list: list[float] = []
    output_fps = float(project.output_fps or 30)

    raw_transitions: list[dict[str, object]] = project.transitions or []
    transition_lookup = resolve_transitions_by_clip_a_id(raw_transitions)

    placeable = [
        c
        for c in clips
        if c.timeline_start is not None
        and c.timeline_end is not None
        and c.source_video_id is not None
    ]

    for i, clip in enumerate(placeable):
        video = await video_repo.get(clip.source_video_id) if video_repo is not None else None
        if video is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "MISSING_VIDEO",
                    "message": f"Source video for clip {clip.id} not found",
                },
            )
        framerate = float(video.frame_rate or output_fps)
        in_point = float(clip.in_point or 0.0) / framerate if clip.clip_type == "file" else 0.0
        duration = float(clip.timeline_end or 0.0) - float(clip.timeline_start or 0.0)
        in_point_secs_list.append(in_point)
        input_paths.append(video.path)

        render_effects = _build_preview_render_effects(clip, effect_registry)

        t_data = transition_lookup.get(clip.id)
        outgoing: RenderTransition | None = None
        if t_data is not None and i < len(placeable) - 1:
            t_params = t_data.get("parameters")
            t_params_dict: dict[str, object] = t_params if isinstance(t_params, dict) else {}
            t_dur = float(t_params_dict.get("duration", t_data.get("duration", 1.0)))  # type: ignore[arg-type]
            if t_dur > 0:
                try:
                    outgoing = RenderTransition(str(t_data["transition_type"]), t_dur)
                except ValueError:
                    logger.warning(
                        "preview_transition_skipped",
                        clip_id=clip.id,
                        transition_type=t_data.get("transition_type"),
                    )

        cwe_list.append(
            ClipWithEffects(
                input_index=i,
                duration_secs=duration,
                framerate=framerate,
                source_path=video.path,
                effects=render_effects,
                outgoing_transition=outgoing,
            )
        )

    if not cwe_list:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "NO_PLACEABLE_CLIPS",
                "message": "No placeable clips found on the timeline",
            },
        )

    translator = RenderGraphTranslator()
    filter_complex_str, _ = translator.translate(cwe_list, output_fps)

    try:
        session = await manager.start(
            project_id=project_id,
            input_paths=input_paths,
            filter_complex_str=filter_complex_str,
            in_point_secs=in_point_secs_list,
            output_fps=output_fps,
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
        HTTPException: 404 if session not found, 422 if composition cannot be built.
    """
    _check_ffmpeg_available()
    manager = _get_preview_manager(request)
    project_repo = _get_project_repository(request)
    clip_repo = _get_clip_repository(request)

    # Resolve the project_id from the live session record.
    try:
        existing_session = await manager.get_status(session_id)
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

    project_id = existing_session.project_id

    # Clip set is re-derived from live DB; a seek after clip modifications will reflect
    # the modified composition, not the original.
    clips = await clip_repo.list_by_project(project_id)

    video_repo = getattr(request.app.state, "video_repository", None)
    effect_registry = getattr(request.app.state, "effect_registry", None)

    project = await project_repo.get(project_id)
    seek_output_fps = 30.0
    if project is not None:
        seek_output_fps = float(project.output_fps or 30)

    raw_transitions_seek: list[dict[str, object]] = []
    if project is not None:
        raw_transitions_seek = project.transitions or []
    transition_lookup_seek = resolve_transitions_by_clip_a_id(raw_transitions_seek)

    cwe_list_seek: list[ClipWithEffects] = []
    input_paths: list[str] = []
    in_point_secs_list_seek: list[float] = []

    placeable_seek = [
        c
        for c in clips
        if c.timeline_start is not None
        and c.timeline_end is not None
        and c.source_video_id is not None
    ]

    for i, clip in enumerate(placeable_seek):
        video = await video_repo.get(clip.source_video_id) if video_repo is not None else None
        if video is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "MISSING_VIDEO",
                    "message": f"Source video for clip {clip.id} not found",
                },
            )
        framerate = float(video.frame_rate or seek_output_fps)
        in_point = float(clip.in_point or 0.0) / framerate if clip.clip_type == "file" else 0.0
        duration = float(clip.timeline_end or 0.0) - float(clip.timeline_start or 0.0)
        in_point_secs_list_seek.append(in_point)
        input_paths.append(video.path)

        render_effects = _build_preview_render_effects(clip, effect_registry)

        t_data = transition_lookup_seek.get(clip.id)
        outgoing_seek: RenderTransition | None = None
        if t_data is not None and i < len(placeable_seek) - 1:
            t_params = t_data.get("parameters")
            t_params_dict_seek: dict[str, object] = t_params if isinstance(t_params, dict) else {}
            t_dur = float(t_params_dict_seek.get("duration", t_data.get("duration", 1.0)))  # type: ignore[arg-type]
            if t_dur > 0:
                try:
                    outgoing_seek = RenderTransition(str(t_data["transition_type"]), t_dur)
                except ValueError:
                    logger.warning(
                        "preview_transition_skipped",
                        clip_id=clip.id,
                        transition_type=t_data.get("transition_type"),
                    )

        cwe_list_seek.append(
            ClipWithEffects(
                input_index=i,
                duration_secs=duration,
                framerate=framerate,
                source_path=video.path,
                effects=render_effects,
                outgoing_transition=outgoing_seek,
            )
        )

    if not cwe_list_seek:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "NO_PLACEABLE_CLIPS",
                "message": "No placeable clips found on the timeline",
            },
        )

    translator_seek = RenderGraphTranslator()
    filter_complex_str_seek, _ = translator_seek.translate(cwe_list_seek, seek_output_fps)

    try:
        session = await manager.seek(
            session_id,
            input_paths=input_paths,
            filter_complex_str=filter_complex_str_seek,
            in_point_secs=in_point_secs_list_seek,
            output_fps=seek_output_fps,
            position=body.position,
        )
    except (SessionNotFoundError, SessionExpiredError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found"},
        ) from None
    except InvalidTransitionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": f"Session {session_id} cannot be seeked in its current state",
            },
        ) from None

    logger.info("preview_session_seek", session_id=session_id, position=body.position)
    return PreviewSeekResponse(
        session_id=session.id,
        status=session.status.value,
    )


@router.delete(
    "/preview/{session_id}",
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
    # media_type is a hardcoded HLS manifest MIME type (not attacker-influenced)
    # and X-Content-Type-Options: nosniff prevents browser MIME-sniffing, so the reflected
    # content cannot be interpreted as executable script by any browser (S5131 accepted
    # risk, BL-636).
    return Response(  # NOSONAR
        content=content,
        media_type=HLS_MANIFEST_CONTENT_TYPE,
        headers={"X-Content-Type-Options": "nosniff"},
    )


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
    # media_type is a hardcoded MPEG-TS MIME type (not attacker-influenced) and
    # X-Content-Type-Options: nosniff prevents browser MIME-sniffing, so the reflected
    # content cannot be interpreted as executable script by any browser (S5131 accepted
    # risk, BL-636).
    return Response(  # NOSONAR
        content=content,
        media_type=HLS_SEGMENT_CONTENT_TYPE,
        headers={"X-Content-Type-Options": "nosniff"},
    )
