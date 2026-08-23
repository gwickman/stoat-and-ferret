# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Version endpoints for listing and restoring project versions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from stoat_ferret.api.routers.timeline import _build_timeline_response, _get_clips_by_track
from stoat_ferret.api.schemas.timeline import TimelineResponse
from stoat_ferret.api.schemas.version import (
    RestoreResponse,
    VersionCreateRequest,
    VersionListResponse,
    VersionResponse,
)
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.clip_repository import AsyncClipRepository, AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip, Track
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.db.timeline_repository import (
    AsyncSQLiteTimelineRepository,
    AsyncTimelineRepository,
)
from stoat_ferret.db.version_repository import (
    AsyncSQLiteVersionRepository,
    AsyncVersionRepository,
    compute_checksum,
)

router = APIRouter(prefix="/api/v1", tags=["versions"])


def get_project_repository(request: Request) -> AsyncProjectRepository:
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


def get_version_repository(request: Request) -> AsyncVersionRepository:
    """Get version repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async version repository instance.
    """
    repo: AsyncVersionRepository | None = getattr(request.app.state, "version_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteVersionRepository(request.app.state.db)


def get_timeline_repository(request: Request) -> AsyncTimelineRepository:
    """Get timeline repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async timeline repository instance.
    """
    repo: AsyncTimelineRepository | None = getattr(request.app.state, "timeline_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteTimelineRepository(request.app.state.db)


def get_clip_repository(request: Request) -> AsyncClipRepository:
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


# Type aliases for dependencies
ProjectRepoDep = Annotated[AsyncProjectRepository, Depends(get_project_repository)]
VersionRepoDep = Annotated[AsyncVersionRepository, Depends(get_version_repository)]
TimelineRepoDep = Annotated[AsyncTimelineRepository, Depends(get_timeline_repository)]
ClipRepoDep = Annotated[AsyncClipRepository, Depends(get_clip_repository)]


@router.get("/projects/{project_id}/versions")
async def list_versions(
    project_id: str,
    project_repo: ProjectRepoDep,
    version_repo: VersionRepoDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VersionListResponse:
    """List versions for a project with pagination.

    Args:
        project_id: The unique project identifier.
        project_repo: Project repository dependency.
        version_repo: Version repository dependency.
        limit: Maximum number of versions to return (1-100, default 20).
        offset: Number of versions to skip (default 0).

    Returns:
        Paginated list of versions.

    Raises:
        HTTPException: 404 if project not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    all_versions = await version_repo.list_versions(project_id)
    total = len(all_versions)
    page = all_versions[offset : offset + limit]

    return VersionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        versions=[
            VersionResponse(
                version_number=v.version_number,
                created_at=v.created_at.isoformat(),
                checksum=v.checksum,
            )
            for v in page
        ],
    )


@router.post(
    "/projects/{project_id}/versions",
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    project_id: str,
    project_repo: ProjectRepoDep,
    version_repo: VersionRepoDep,
    timeline_repo: TimelineRepoDep,
    clip_repo: ClipRepoDep,
    body: VersionCreateRequest | None = None,
) -> VersionResponse:
    """Create a new version snapshot of a project timeline.

    When body is absent or timeline_json is None, auto-snapshots the live
    timeline via _build_timeline_response() + model_dump(mode="json").

    Args:
        project_id: The unique project identifier.
        body: Optional version creation request. When absent, the server
            auto-snapshots the current live timeline.
        project_repo: Project repository dependency.
        version_repo: Version repository dependency.
        timeline_repo: Timeline repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        The created version with auto-incremented version number and checksum.

    Raises:
        HTTPException: 404 if project not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    if body is None or body.timeline_json is None:
        tracks = await timeline_repo.get_tracks_by_project(project_id)
        clips_by_track = await _get_clips_by_track(clip_repo, project_id)
        timeline = _build_timeline_response(project_id, tracks, clips_by_track)
        snapshot_json = json.dumps(timeline.model_dump(mode="json"))
        record = await version_repo.save(project_id, snapshot_json)
    else:
        record = await version_repo.save(project_id, body.timeline_json)

    retention_count = get_settings().version_retention_count
    if retention_count is not None:
        await version_repo.delete_old_versions(project_id, retention_count)

    return VersionResponse(
        version_number=record.version_number,
        created_at=record.created_at.isoformat(),
        checksum=record.checksum,
    )


@router.post(
    "/projects/{project_id}/versions/{version}/restore",
)
async def restore_version(
    project_id: str,
    version: int,
    project_repo: ProjectRepoDep,
    version_repo: VersionRepoDep,
    timeline_repo: TimelineRepoDep,
    clip_repo: ClipRepoDep,
) -> RestoreResponse:
    """Restore a previous project version to the live timeline, creating a new version.

    Replaces the current live timeline with the data from the specified version,
    then saves a new version snapshot of the restored state.

    Args:
        project_id: The unique project identifier.
        version: The version number to restore from.
        project_repo: Project repository dependency.
        version_repo: Version repository dependency.
        timeline_repo: Timeline repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Restore confirmation with source and new version numbers.

    Raises:
        HTTPException: 404 if project or version not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    source = await version_repo.get_version(project_id, version)
    if source is None or compute_checksum(source.timeline_json) != source.checksum:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_VERSION_NOT_FOUND",
                "message": f"Version {version} not found for project {project_id}",
            },
        )

    timeline = TimelineResponse.model_validate(json.loads(source.timeline_json))

    live_tracks = await timeline_repo.get_tracks_by_project(project_id)
    for track in live_tracks:
        clips = await timeline_repo.get_clips_by_track(track.id)
        for clip in clips:
            await clip_repo.delete(clip.id)
        await timeline_repo.delete_track(track.id)

    for tr in timeline.tracks:
        restored_track = Track(
            id=tr.id,
            project_id=project_id,
            track_type=tr.track_type,
            label=tr.label,
            z_index=tr.z_index,
            muted=tr.muted,
            locked=tr.locked,
            kind=tr.kind,
            volume_envelope=tr.volume_envelope,
            weight=tr.weight,
        )
        await timeline_repo.create_track(restored_track)
        for cl in tr.clips:
            restored_clip = Clip(
                id=cl.id,
                project_id=project_id,
                source_video_id=cl.source_video_id,
                in_point=cl.in_point,
                out_point=cl.out_point,
                timeline_position=0,
                clip_type=cl.clip_type,
                track_id=cl.track_id,
                timeline_start=cl.timeline_start,
                timeline_end=cl.timeline_end,
                generator_params=None,
                effects=None,
                source_asset_id=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            await clip_repo.add(restored_clip)

    new_record = await version_repo.save(project_id, source.timeline_json)

    return RestoreResponse(
        restored_version=version,
        new_version=new_record.version_number,
        message="Version restored to live timeline.",
    )
