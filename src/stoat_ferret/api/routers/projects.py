"""Project and clip endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from stoat_ferret.api.schemas.clip import (
    ClipCreate,
    ClipListResponse,
    ClipResponse,
    ClipUpdate,
)
from stoat_ferret.api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
)
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncVideoRepository
from stoat_ferret.db.clip_repository import AsyncClipRepository, AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip, ClipValidationError, Project
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


async def get_project_repository(request: Request) -> AsyncProjectRepository:
    """Get project repository from app state.

    Returns an injected repository if one was provided to create_app(),
    otherwise constructs a SQLite repository from the database connection.

    Args:
        request: The FastAPI request object.

    Returns:
        Async project repository instance.
    """
    repo: AsyncProjectRepository | None = getattr(request.app.state, "project_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteProjectRepository(request.app.state.db)


async def get_clip_repository(request: Request) -> AsyncClipRepository:
    """Get clip repository from app state.

    Returns an injected repository if one was provided to create_app(),
    otherwise constructs a SQLite repository from the database connection.

    Args:
        request: The FastAPI request object.

    Returns:
        Async clip repository instance.
    """
    repo: AsyncClipRepository | None = getattr(request.app.state, "clip_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteClipRepository(request.app.state.db)


async def get_video_repository(request: Request) -> AsyncVideoRepository:
    """Get video repository from app state.

    Returns an injected repository if one was provided to create_app(),
    otherwise constructs a SQLite repository from the database connection.

    Args:
        request: The FastAPI request object.

    Returns:
        Async video repository instance.
    """
    repo: AsyncVideoRepository | None = getattr(request.app.state, "video_repository", None)
    if repo is not None:
        return repo
    from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository

    return AsyncSQLiteVideoRepository(request.app.state.db)


# Type aliases for dependencies
ProjectRepoDep = Annotated[AsyncProjectRepository, Depends(get_project_repository)]
ClipRepoDep = Annotated[AsyncClipRepository, Depends(get_clip_repository)]
VideoRepoDep = Annotated[AsyncVideoRepository, Depends(get_video_repository)]


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    repo: ProjectRepoDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectListResponse:
    """List all projects.

    Args:
        repo: Project repository dependency.
        limit: Maximum number of projects to return (1-100, default 20).
        offset: Number of projects to skip (default 0).

    Returns:
        Paginated list of projects.
    """
    projects = await repo.list_projects(limit=limit, offset=offset)
    total = await repo.count()
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    repo: ProjectRepoDep,
) -> ProjectResponse:
    """Create a new project.

    Args:
        project_data: Project creation request.
        request: The FastAPI request object.
        repo: Project repository dependency.

    Returns:
        Created project details.
    """
    now = datetime.now(timezone.utc)
    project = Project(
        id=Project.new_id(),
        name=project_data.name,
        output_width=project_data.output_width,
        output_height=project_data.output_height,
        output_fps=project_data.output_fps,
        created_at=now,
        updated_at=now,
    )
    await repo.add(project)

    ws_manager: ConnectionManager | None = getattr(request.app.state, "ws_manager", None)
    if ws_manager:
        await ws_manager.broadcast(
            build_event(
                EventType.PROJECT_CREATED,
                {"project_id": project.id, "name": project.name},
            )
        )

    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    repo: ProjectRepoDep,
) -> ProjectResponse:
    """Get project by ID.

    Args:
        project_id: The unique project identifier.
        repo: Project repository dependency.

    Returns:
        Project details.

    Raises:
        HTTPException: 404 if project not found.
    """
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    repo: ProjectRepoDep,
) -> Response:
    """Delete project.

    Args:
        project_id: The unique project identifier.
        repo: Project repository dependency.

    Returns:
        Empty response with 204 status.

    Raises:
        HTTPException: 404 if project not found.
    """
    deleted = await repo.delete(project_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/clips", response_model=ClipListResponse)
async def list_clips(
    project_id: str,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> ClipListResponse:
    """List clips in project.

    Args:
        project_id: The unique project identifier.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        List of clips in the project.

    Raises:
        HTTPException: 404 if project not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    clips = await clip_repo.list_by_project(project_id)
    return ClipListResponse(
        clips=[ClipResponse.model_validate(c) for c in clips],
        total=len(clips),
    )


@router.post(
    "/{project_id}/clips", response_model=ClipResponse, status_code=status.HTTP_201_CREATED
)
async def add_clip(
    project_id: str,
    request: ClipCreate,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
    video_repo: VideoRepoDep,
) -> ClipResponse:
    """Add clip to project.

    Args:
        project_id: The unique project identifier.
        request: Clip creation request.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.
        video_repo: Video repository dependency.

    Returns:
        Created clip details.

    Raises:
        HTTPException: 404 if project or video not found, 400 if validation fails.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    # Lookup the source video for validation
    video = await video_repo.get(request.source_video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Video {request.source_video_id} not found",
            },
        )

    now = datetime.now(timezone.utc)
    clip = Clip(
        id=Clip.new_id(),
        project_id=project_id,
        source_video_id=request.source_video_id,
        in_point=request.in_point,
        out_point=request.out_point,
        timeline_position=request.timeline_position,
        created_at=now,
        updated_at=now,
    )

    # Validate using Rust
    try:
        clip.validate(source_path=video.path, source_duration_frames=video.duration_frames)
    except ClipValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(e)},
        ) from None

    await clip_repo.add(clip)
    return ClipResponse.model_validate(clip)


@router.patch("/{project_id}/clips/{clip_id}", response_model=ClipResponse)
async def update_clip(
    project_id: str,
    clip_id: str,
    request: ClipUpdate,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
    video_repo: VideoRepoDep,
) -> ClipResponse:
    """Update clip.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        request: Clip update request.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.
        video_repo: Video repository dependency.

    Returns:
        Updated clip details.

    Raises:
        HTTPException: 404 if project or clip not found, 400 if validation fails.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )

    # Lookup the source video for validation
    video = await video_repo.get(clip.source_video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Video {clip.source_video_id} not found",
            },
        )

    # Apply updates
    if request.in_point is not None:
        clip.in_point = request.in_point
    if request.out_point is not None:
        clip.out_point = request.out_point
    if request.timeline_position is not None:
        clip.timeline_position = request.timeline_position
    clip.updated_at = datetime.now(timezone.utc)

    # Validate using Rust
    try:
        clip.validate(source_path=video.path, source_duration_frames=video.duration_frames)
    except ClipValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(e)},
        ) from None

    await clip_repo.update(clip)
    return ClipResponse.model_validate(clip)


@router.delete("/{project_id}/clips/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    project_id: str,
    clip_id: str,
    clip_repo: ClipRepoDep,
) -> Response:
    """Delete clip.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        clip_repo: Clip repository dependency.

    Returns:
        Empty response with 204 status.

    Raises:
        HTTPException: 404 if clip not found.
    """
    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )

    await clip_repo.delete(clip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
