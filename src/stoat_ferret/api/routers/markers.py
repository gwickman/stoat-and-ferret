# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Timeline markers CRUD endpoints for projects."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from stoat_ferret.api.schemas.markers import MarkerCreate, MarkerResponse, MarkerUpdate
from stoat_ferret.db.markers_repository import AsyncSQLiteMarkerRepository, Marker

router = APIRouter(prefix="/api/v1/projects/{pid}/markers", tags=["markers"])


def _get_repo(request: Request) -> AsyncSQLiteMarkerRepository:
    """Return the markers repository from app state."""
    repo: AsyncSQLiteMarkerRepository = request.app.state.markers_repository
    return repo


@router.post("", status_code=201, response_model=MarkerResponse)
async def create_marker(pid: str, body: MarkerCreate, request: Request) -> MarkerResponse:
    """Create a new timeline marker for a project."""
    repo = _get_repo(request)

    # Verify project exists
    project_repo = getattr(request.app.state, "project_repository", None)
    if project_repo is None:
        from stoat_ferret.db.project_repository import AsyncSQLiteProjectRepository

        project_repo = AsyncSQLiteProjectRepository(request.app.state.db)
    project = await project_repo.get(pid)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate section marker constraints
    if body.region_type == "section":
        if body.end_time is None or body.end_time <= body.start_time:
            raise HTTPException(
                status_code=422, detail="Section markers require end_time > start_time"
            )
        overlap = await repo.check_overlap(pid, body.start_time, body.end_time)
        if overlap:
            raise HTTPException(status_code=422, detail="Section markers must not overlap")

    marker = Marker(
        id=str(uuid.uuid4()),
        project_id=pid,
        start_time=body.start_time,
        end_time=body.end_time,
        name=body.name,
        region_type=body.region_type,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    saved = await repo.add(marker)
    return MarkerResponse(
        id=saved.id,
        project_id=saved.project_id,
        start_time=saved.start_time,
        end_time=saved.end_time,
        name=saved.name,
        region_type=saved.region_type,
        created_at=saved.created_at,
    )


@router.get("", response_model=list[MarkerResponse])
async def list_markers(pid: str, request: Request) -> list[MarkerResponse]:
    """List all timeline markers for a project ordered by start_time ASC."""
    repo = _get_repo(request)

    # Verify project exists
    project_repo = getattr(request.app.state, "project_repository", None)
    if project_repo is None:
        from stoat_ferret.db.project_repository import AsyncSQLiteProjectRepository

        project_repo = AsyncSQLiteProjectRepository(request.app.state.db)
    project = await project_repo.get(pid)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    markers = await repo.list_by_project(pid)
    return [
        MarkerResponse(
            id=m.id,
            project_id=m.project_id,
            start_time=m.start_time,
            end_time=m.end_time,
            name=m.name,
            region_type=m.region_type,
            created_at=m.created_at,
        )
        for m in markers
    ]


@router.patch("/{mid}", response_model=MarkerResponse)
async def update_marker(pid: str, mid: str, body: MarkerUpdate, request: Request) -> MarkerResponse:
    """Update mutable fields of a timeline marker."""
    repo = _get_repo(request)

    existing = await repo.get(mid)
    if existing is None or existing.project_id != pid:
        raise HTTPException(status_code=404, detail="Marker not found")

    new_start = body.start_time if body.start_time is not None else existing.start_time
    new_end = body.end_time if body.end_time is not None else existing.end_time
    new_name = body.name if body.name is not None else existing.name

    # Re-validate section overlap when times change
    if existing.region_type == "section":
        effective_end = new_end
        if effective_end is None or effective_end <= new_start:
            raise HTTPException(
                status_code=422, detail="Section markers require end_time > start_time"
            )
        if body.start_time is not None or body.end_time is not None:
            overlap = await repo.check_overlap(pid, new_start, effective_end, exclude_id=mid)
            if overlap:
                raise HTTPException(status_code=422, detail="Section markers must not overlap")

    updated = Marker(
        id=existing.id,
        project_id=existing.project_id,
        start_time=new_start,
        end_time=new_end,
        name=new_name,
        region_type=existing.region_type,
        created_at=existing.created_at,
    )
    result = await repo.update(updated)
    if result is None:
        raise HTTPException(status_code=404, detail="Marker not found")
    return MarkerResponse(
        id=result.id,
        project_id=result.project_id,
        start_time=result.start_time,
        end_time=result.end_time,
        name=result.name,
        region_type=result.region_type,
        created_at=result.created_at,
    )


@router.delete("/{mid}", status_code=204)
async def delete_marker(pid: str, mid: str, request: Request) -> Response:
    """Delete a timeline marker."""
    repo = _get_repo(request)

    # Verify the marker belongs to this project
    existing = await repo.get(mid)
    if existing is None or existing.project_id != pid:
        raise HTTPException(status_code=404, detail="Marker not found")

    deleted = await repo.delete(mid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Marker not found")
    return Response(status_code=204)
