# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""TTS narration cue endpoints (BL-516)."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from stoat_ferret.api.schemas.tts import (
    TtsCueCreate,
    TtsCueListResponse,
    TtsCueResponse,
    TtsCueUpdate,
    VoiceInfo,
    VoicesResponse,
    _compute_cache_key,
)
from stoat_ferret.db.models import TtsCue
from stoat_ferret.db.tts_cue_repository import AsyncSQLiteTtsCueRepository, AsyncTtsCueRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["tts"])


async def _get_tts_cue_repository(request: Request) -> AsyncTtsCueRepository:
    """Get TTS cue repository from app state or create one from db connection.

    Args:
        request: The incoming HTTP request.

    Returns:
        The TTS cue repository instance.
    """
    repo: AsyncTtsCueRepository | None = getattr(request.app.state, "tts_cue_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteTtsCueRepository(request.app.state.db)


TtsCueRepoDep = Annotated[AsyncTtsCueRepository, Depends(_get_tts_cue_repository)]


async def _validate_voice_track(request: Request, track_id: str) -> None:
    """Validate that the given track_id references a track with kind=voice.

    Args:
        request: The incoming HTTP request (provides db access).
        track_id: The track ID to validate.

    Raises:
        HTTPException: 422 if the track does not exist or is not a voice track.
    """
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT id, kind FROM tracks WHERE id = ?",
        (track_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "TRACK_NOT_FOUND",
                "message": f"Track '{track_id}' does not exist",
            },
        )
    if dict(row).get("kind") != "voice":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_TRACK_KIND",
                "message": "TTS cues require a voice track",
            },
        )


@router.post(
    "/projects/{project_id}/tts_cues",
    response_model=TtsCueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a TTS cue",
)
async def create_tts_cue(
    project_id: UUID,
    body: TtsCueCreate,
    repo: TtsCueRepoDep,
    request: Request,
) -> TtsCueResponse:
    """Create a TTS narration cue on a voice track.

    Args:
        project_id: The project UUID.
        body: TTS cue creation parameters.
        repo: TTS cue repository (injected).
        request: The incoming HTTP request.

    Returns:
        The created TTS cue.
    """
    await _validate_voice_track(request, body.track_id)

    now = datetime.now(timezone.utc)
    cache_key = _compute_cache_key(body.text, body.voice, body.backend)
    cue = TtsCue(
        id=TtsCue.new_id(),
        project_id=str(project_id),
        track_id=body.track_id,
        start_s=body.start_s,
        text=body.text,
        voice=body.voice,
        backend=body.backend,
        gain_db=body.gain_db,
        pan=body.pan,
        cache_key=cache_key,
        generated_asset_id=None,
        status="pending",
        error=None,
        created_at=now,
        updated_at=now,
    )
    created = await repo.create(cue)
    logger.info("tts.cue_created", cue_id=created.id, project_id=str(project_id))
    return _cue_to_response(created)


@router.get(
    "/projects/{project_id}/tts_cues",
    response_model=TtsCueListResponse,
    summary="List TTS cues for a project",
)
async def list_tts_cues(
    project_id: UUID,
    repo: TtsCueRepoDep,
) -> TtsCueListResponse:
    """List all TTS cues for a project.

    Args:
        project_id: The project UUID.
        repo: TTS cue repository (injected).

    Returns:
        Ordered list of TTS cues (by start_s, then created_at).
    """
    cues = await repo.list_by_project(str(project_id))
    return TtsCueListResponse(items=[_cue_to_response(c) for c in cues], total=len(cues))


@router.get(
    "/projects/{project_id}/tts_cues/{cue_id}",
    response_model=TtsCueResponse,
    summary="Get a TTS cue",
)
async def get_tts_cue(
    project_id: UUID,
    cue_id: UUID,
    repo: TtsCueRepoDep,
) -> TtsCueResponse:
    """Get a single TTS cue by ID.

    Args:
        project_id: The project UUID.
        cue_id: The TTS cue UUID.
        repo: TTS cue repository (injected).

    Returns:
        The requested TTS cue.
    """
    cue = await repo.get(str(cue_id))
    if cue is None or cue.project_id != str(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TTS_CUE_NOT_FOUND", "message": f"TTS cue {cue_id} not found"},
        )
    return _cue_to_response(cue)


@router.patch(
    "/projects/{project_id}/tts_cues/{cue_id}",
    response_model=TtsCueResponse,
    summary="Update a TTS cue",
)
async def update_tts_cue(
    project_id: UUID,
    cue_id: UUID,
    body: TtsCueUpdate,
    repo: TtsCueRepoDep,
    request: Request,
) -> TtsCueResponse:
    """Update a TTS cue.

    Updating text, voice, or backend recalculates cache_key and resets
    status to pending, audio_path to None, error to None.

    Args:
        project_id: The project UUID.
        cue_id: The TTS cue UUID.
        body: Fields to update.
        repo: TTS cue repository (injected).
        request: The incoming HTTP request.

    Returns:
        The updated TTS cue.
    """
    cue = await repo.get(str(cue_id))
    if cue is None or cue.project_id != str(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TTS_CUE_NOT_FOUND", "message": f"TTS cue {cue_id} not found"},
        )

    if body.track_id is not None:
        await _validate_voice_track(request, body.track_id)
        cue.track_id = body.track_id

    synthesis_fields_changed = False
    if body.text is not None:
        cue.text = body.text
        synthesis_fields_changed = True
    if body.voice is not None:
        cue.voice = body.voice
        synthesis_fields_changed = True
    if body.backend is not None:
        cue.backend = body.backend
        synthesis_fields_changed = True

    if synthesis_fields_changed:
        cue.cache_key = _compute_cache_key(cue.text, cue.voice, cue.backend)
        cue.status = "pending"
        cue.generated_asset_id = None
        cue.error = None

    if body.start_s is not None:
        cue.start_s = body.start_s
    if body.gain_db is not None:
        cue.gain_db = body.gain_db
    if body.pan is not None:
        cue.pan = body.pan

    cue.updated_at = datetime.now(timezone.utc)
    updated = await repo.update(cue)
    return _cue_to_response(updated)


@router.delete(
    "/projects/{project_id}/tts_cues/{cue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a TTS cue",
)
async def delete_tts_cue(
    project_id: UUID,
    cue_id: UUID,
    repo: TtsCueRepoDep,
) -> None:
    """Delete a TTS cue.

    Args:
        project_id: The project UUID.
        cue_id: The TTS cue UUID.
        repo: TTS cue repository (injected).
    """
    cue = await repo.get(str(cue_id))
    if cue is None or cue.project_id != str(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TTS_CUE_NOT_FOUND", "message": f"TTS cue {cue_id} not found"},
        )
    await repo.delete(str(cue_id))


@router.post(
    "/projects/{project_id}/tts_cues/{cue_id}/synthesise",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Dispatch TTS synthesis for a cue",
)
async def synthesise_tts_cue(
    project_id: UUID,
    cue_id: UUID,
    repo: TtsCueRepoDep,
    request: Request,
) -> dict[str, str]:
    """Dispatch TTS synthesis for a cue.

    Idempotent: concurrent calls while already synthesising return 202 without
    spawning a duplicate task. A previously failed cue is reset to pending on re-call.

    Args:
        project_id: The project UUID.
        cue_id: The TTS cue UUID.
        repo: TTS cue repository (injected).
        request: The incoming HTTP request (provides TtsService access).

    Returns:
        Accepted acknowledgement with cue ID and dispatch status.
    """
    from stoat_ferret.api.services.tts_service import TtsService

    cue = await repo.get(str(cue_id))
    if cue is None or cue.project_id != str(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TTS_CUE_NOT_FOUND", "message": f"TTS cue {cue_id} not found"},
        )

    tts_service: TtsService | None = getattr(request.app.state, "tts_service", None)
    if tts_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "TTS_SERVICE_UNAVAILABLE",
                "message": "TTS service not initialised",
            },
        )

    dispatched = await tts_service.synthesise_cue(str(cue_id))
    dispatch_status = "dispatched" if dispatched else "already_synthesising"
    return {"status": dispatch_status, "cue_id": str(cue_id)}


@router.get(
    "/tts/voices",
    response_model=VoicesResponse,
    summary="List available TTS voices",
)
async def list_tts_voices(
    request: Request,
) -> VoicesResponse:
    """Return available TTS voices per backend.

    Piper voices are discovered from the filesystem (blocking I/O runs in executor).
    Kokoro voices are a static list (real API query implemented in Feature 004).

    Args:
        request: The incoming HTTP request (provides settings access).

    Returns:
        List of available voices across all configured backends.
    """
    settings = request.app.state._settings

    loop = asyncio.get_event_loop()
    piper_voices = await loop.run_in_executor(
        None,
        _scan_piper_models_dir,
        settings.tts_piper_models_dir,
    )

    kokoro_voices: list[VoiceInfo] = []
    if settings.openrouter_api_key:
        kokoro_voices = _get_kokoro_voices_static()

    return VoicesResponse(voices=piper_voices + kokoro_voices)


def _scan_piper_models_dir(models_dir: str) -> list[VoiceInfo]:
    """Scan Piper models directory for available voice ONNX files.

    Runs in a thread executor to avoid blocking the event loop.

    Args:
        models_dir: Path to the Piper models directory.

    Returns:
        List of VoiceInfo for discovered Piper models.
    """
    voices: list[VoiceInfo] = []
    if not os.path.isdir(models_dir):
        return voices
    for entry in os.scandir(models_dir):
        if entry.is_file() and entry.name.endswith(".onnx"):
            voice_id = entry.name[:-5]
            voices.append(
                VoiceInfo(
                    voice_id=voice_id,
                    backend="piper_local",
                    description=f"Piper local voice: {voice_id}",
                )
            )
    return sorted(voices, key=lambda v: v.voice_id)


def _get_kokoro_voices_static() -> list[VoiceInfo]:
    """Return a static list of known Kokoro voices (Feature 004 adds live query).

    Returns:
        Static list of Kokoro voice IDs.
    """
    return [
        VoiceInfo(
            voice_id="af_heart",
            backend="openrouter_kokoro",
            language="en",
            description="Kokoro af_heart",
        ),
        VoiceInfo(
            voice_id="af_bella",
            backend="openrouter_kokoro",
            language="en",
            description="Kokoro af_bella",
        ),
    ]


def _cue_to_response(cue: TtsCue) -> TtsCueResponse:
    """Convert a TtsCue model to a TtsCueResponse.

    Args:
        cue: The database model.

    Returns:
        The API response schema.
    """
    return TtsCueResponse(
        id=UUID(cue.id),
        project_id=UUID(cue.project_id),
        track_id=cue.track_id,
        start_s=cue.start_s,
        text=cue.text,
        voice=cue.voice,
        backend=cue.backend,  # type: ignore[arg-type]
        gain_db=cue.gain_db,
        pan=cue.pan,
        cache_key=cue.cache_key,
        audio_path=cue.generated_asset_id,
        status=cue.status,  # type: ignore[arg-type]
        error=cue.error,
        created_at=cue.created_at,
        updated_at=cue.updated_at,
    )
