"""Filesystem endpoints for directory browsing."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status

from stoat_ferret.api.schemas.filesystem import DirectoryEntry, DirectoryListResponse
from stoat_ferret.api.services.scan import validate_scan_path
from stoat_ferret.api.settings import get_settings

router = APIRouter(prefix="/api/v1/filesystem", tags=["filesystem"])


def _list_dirs(path: str) -> list[DirectoryEntry]:
    """List subdirectories within a path using os.scandir.

    Filters to directories only, skips hidden entries (starting with '.'),
    and returns results sorted by name.

    Args:
        path: Absolute directory path to list.

    Returns:
        Sorted list of DirectoryEntry objects for each subdirectory.
    """
    entries: list[DirectoryEntry] = []
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                entries.append(
                    DirectoryEntry(name=entry.name, path=str(Path(entry.path).resolve()))
                )
    entries.sort(key=lambda e: e.name.lower())
    return entries


@router.get("/directories", response_model=DirectoryListResponse)
async def list_directories(
    path: str | None = Query(default=None, description="Directory path to list"),
) -> DirectoryListResponse:
    """List subdirectories within a given path.

    Returns a flat list of immediate subdirectories. Hidden directories
    (starting with '.') are excluded. Uses run_in_executor for async-safe
    filesystem access.

    When path is not provided, defaults to the first allowed_scan_root
    or the user's home directory if no roots are configured.

    Args:
        path: Directory path to list. Defaults to a sensible starting location.

    Returns:
        Directory listing with parent path and subdirectory entries.

    Raises:
        HTTPException: 400 if path is not a directory, 403 if outside allowed roots,
            404 if path does not exist.
    """
    settings = get_settings()

    # Default path when none provided
    if path is None:
        path = settings.allowed_scan_roots[0] if settings.allowed_scan_roots else str(Path.home())

    resolved = str(Path(path).resolve())

    # Security: validate against allowed_scan_roots
    error = validate_scan_path(resolved, settings.allowed_scan_roots)
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PATH_NOT_ALLOWED", "message": error},
        )

    # Validate path exists
    if not os.path.exists(resolved):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PATH_NOT_FOUND", "message": f"Path does not exist: {path}"},
        )

    # Validate path is a directory
    if not os.path.isdir(resolved):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NOT_A_DIRECTORY", "message": f"Path is not a directory: {path}"},
        )

    # List directories in executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    directories = await loop.run_in_executor(None, _list_dirs, resolved)

    return DirectoryListResponse(path=resolved, directories=directories)
