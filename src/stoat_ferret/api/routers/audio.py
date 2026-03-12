"""Audio mix configuration endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from stoat_ferret.api.schemas.audio import (
    AudioMixRequest,
    AudioMixResponse,
    TrackConfig,
)
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["audio"])


async def _get_project_repository(request: Request) -> AsyncProjectRepository:
    """Get project repository from app state.

    Args:
        request: The incoming HTTP request.

    Returns:
        The project repository instance.
    """
    repo: AsyncProjectRepository | None = getattr(request.app.state, "project_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteProjectRepository(request.app.state.db)


ProjectRepoDep = Annotated[AsyncProjectRepository, Depends(_get_project_repository)]


def _validate_volumes(tracks: list[TrackConfig], master_volume: float) -> None:
    """Validate all volume values are within the 0.0-2.0 range.

    Args:
        tracks: Per-track audio configurations.
        master_volume: Master volume multiplier.

    Raises:
        HTTPException: 422 with INVALID_AUDIO_VOLUME if any volume is out of range.
    """
    for i, track in enumerate(tracks):
        if not 0.0 <= track.volume <= 2.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "INVALID_AUDIO_VOLUME",
                    "message": (
                        f"Track {i} volume must be in range [0.0, 2.0], got {track.volume}"
                    ),
                },
            )
    if not 0.0 <= master_volume <= 2.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_AUDIO_VOLUME",
                "message": (f"master_volume must be in range [0.0, 2.0], got {master_volume}"),
            },
        )


def _validate_track_count(tracks: list[TrackConfig]) -> None:
    """Validate track count is between 2 and 8.

    Args:
        tracks: Per-track audio configurations.

    Raises:
        HTTPException: 422 if track count is out of range.
    """
    if len(tracks) < 2 or len(tracks) > 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_TRACK_COUNT",
                "message": (f"Track count must be between 2 and 8, got {len(tracks)}"),
            },
        )


def _build_filter_preview(request: AudioMixRequest) -> str:
    """Build the FFmpeg filter preview string from the audio mix request.

    Composes AudioMixSpec filter chain with VolumeBuilder for master volume
    via semicolon concatenation.

    Args:
        request: The audio mix request.

    Returns:
        The composed FFmpeg filter chain string.
    """
    from stoat_ferret_core import AudioMixSpec, TrackAudioConfig, VolumeBuilder

    rust_tracks = [TrackAudioConfig(t.volume, t.fade_in, t.fade_out) for t in request.tracks]
    mix_spec = AudioMixSpec(rust_tracks)
    filter_chain = mix_spec.build_filter_chain()

    # Append master volume via VolumeBuilder semicolon concatenation
    if request.master_volume != 1.0:
        master_filter = VolumeBuilder(request.master_volume).build()
        filter_chain = f"{filter_chain};{master_filter}"

    return filter_chain


@router.put(
    "/projects/{project_id}/audio/mix",
    response_model=AudioMixResponse,
)
async def configure_audio_mix(
    project_id: str,
    request: AudioMixRequest,
    http_request: Request,
    project_repo: ProjectRepoDep,
) -> AudioMixResponse:
    """Configure audio mix for a project.

    Validates per-track volume, fade, master volume, and track count.
    Builds filter chain via Rust AudioMixSpec with VolumeBuilder for
    master volume. Persists the mix configuration on the project.

    Args:
        project_id: The unique project identifier.
        request: Audio mix configuration request.
        project_repo: Project repository dependency.

    Returns:
        Audio mix response with filter preview and track count.

    Raises:
        HTTPException: 404 if project not found, 422 if validation fails.
    """
    # Validate project exists
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Project {project_id} not found",
            },
        )

    # Validate inputs
    _validate_track_count(request.tracks)
    _validate_volumes(request.tracks, request.master_volume)

    # Build filter preview
    filter_preview = _build_filter_preview(request)

    # Persist audio mix configuration on project
    audio_mix_entry: dict[str, Any] = {
        "tracks": [
            {
                "volume": t.volume,
                "fade_in": t.fade_in,
                "fade_out": t.fade_out,
            }
            for t in request.tracks
        ],
        "master_volume": request.master_volume,
        "normalize": request.normalize,
        "filter_preview": filter_preview,
    }
    project.audio_mix = audio_mix_entry
    project.updated_at = datetime.now(timezone.utc)
    await project_repo.update(project)

    logger.info(
        "audio_mix_configured",
        project_id=project_id,
        tracks_configured=len(request.tracks),
    )

    ws_manager: ConnectionManager | None = getattr(http_request.app.state, "ws_manager", None)
    if ws_manager:
        await ws_manager.broadcast(
            build_event(
                EventType.AUDIO_MIX_CHANGED,
                {"project_id": project_id, "tracks_configured": len(request.tracks)},
            )
        )

    return AudioMixResponse(
        filter_preview=filter_preview,
        tracks_configured=len(request.tracks),
    )


@router.post(
    "/audio/mix/preview",
    response_model=AudioMixResponse,
)
async def preview_audio_mix(
    request: AudioMixRequest,
) -> AudioMixResponse:
    """Preview audio mix filter chain without persisting.

    Validates per-track volume, fade, master volume, and track count,
    then returns the filter preview string.

    Args:
        request: Audio mix configuration request.

    Returns:
        Audio mix response with filter preview and track count.

    Raises:
        HTTPException: 422 if validation fails.
    """
    _validate_track_count(request.tracks)
    _validate_volumes(request.tracks, request.master_volume)

    filter_preview = _build_filter_preview(request)

    return AudioMixResponse(
        filter_preview=filter_preview,
        tracks_configured=len(request.tracks),
    )
