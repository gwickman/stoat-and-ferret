"""Version endpoints for listing and restoring project versions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from stoat_ferret.api.schemas.version import (
    RestoreResponse,
    VersionListResponse,
    VersionResponse,
)
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.db.version_repository import (
    AsyncSQLiteVersionRepository,
    AsyncVersionRepository,
)

router = APIRouter(prefix="/api/v1", tags=["versions"])


async def get_project_repository(request: Request) -> AsyncProjectRepository:
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


async def get_version_repository(request: Request) -> AsyncVersionRepository:
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


# Type aliases for dependencies
ProjectRepoDep = Annotated[AsyncProjectRepository, Depends(get_project_repository)]
VersionRepoDep = Annotated[AsyncVersionRepository, Depends(get_version_repository)]


@router.get("/projects/{project_id}/versions", response_model=VersionListResponse)
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
    "/projects/{project_id}/versions/{version}/restore",
    response_model=RestoreResponse,
)
async def restore_version(
    project_id: str,
    version: int,
    project_repo: ProjectRepoDep,
    version_repo: VersionRepoDep,
) -> RestoreResponse:
    """Restore a previous project version, creating a new version.

    Non-destructive: restoring version N creates a new version containing
    the restored data.

    Args:
        project_id: The unique project identifier.
        version: The version number to restore from.
        project_repo: Project repository dependency.
        version_repo: Version repository dependency.

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

    try:
        new_record = await version_repo.restore(project_id, version)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_VERSION_NOT_FOUND",
                "message": f"Version {version} not found for project {project_id}",
            },
        ) from None

    return RestoreResponse(
        restored_version=version,
        new_version=new_record.version_number,
        message=f"Restored version {version} as version {new_record.version_number}",
    )
