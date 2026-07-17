# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Filesystem endpoints for directory browsing."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from stoat_ferret.api.schemas.filesystem import DirectoryEntry, DirectoryListResponse
from stoat_ferret.api.services.scan import validate_scan_path
from stoat_ferret.api.settings import get_settings

router = APIRouter(prefix="/api/v1/filesystem", tags=["filesystem"])

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


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
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DirectoryListResponse:
    """List subdirectories within a given path with pagination.

    Returns a paginated list of immediate subdirectories. Hidden directories
    (starting with '.') are excluded. Uses run_in_executor for async-safe
    filesystem access.

    When path is not provided, defaults to the first allowed_scan_root
    or the user's home directory if no roots are configured.

    Args:
        path: Directory path to list. Defaults to a sensible starting location.
        limit: Maximum number of entries to return (1-100, default 20).
        offset: Number of entries to skip (default 0).

    Returns:
        Paginated directory listing with metadata.

    Raises:
        HTTPException: 400 if path is not a directory or is malformed (e.g. contains
            a null byte), 403 if outside allowed roots or if allowed_scan_roots is
            unset on a non-loopback bind, 404 if path does not exist.
    """
    settings = get_settings()

    # Security: fail closed when allowed_scan_roots is unset on a non-loopback bind.
    # Loopback binds (dev/test/UAT/chatbot) keep the existing allow-all behavior.
    if not settings.allowed_scan_roots and settings.api_host.lower() not in _LOOPBACK_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "SCAN_ROOTS_REQUIRED",
                "message": (
                    "allowed_scan_roots must be set when the server is bound to a non-loopback host"
                ),
            },
        )

    # Default path when none provided
    if path is None:
        path = settings.allowed_scan_roots[0] if settings.allowed_scan_roots else str(Path.home())

    # Security: reject null bytes explicitly — Path.resolve() only raises for
    # embedded nulls on POSIX (os.stat rejects them); Windows' non-strict resolve()
    # silently accepts them, so a string check is required for cross-platform 400s.
    if "\x00" in path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": "Path contains a null byte"},
        )

    try:
        resolved = str(Path(path).resolve())
    except (ValueError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": f"Malformed path: {e}"},
        ) from e

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
    all_directories = await loop.run_in_executor(None, _list_dirs, resolved)

    total = len(all_directories)
    page = all_directories[offset : offset + limit]

    return DirectoryListResponse(
        path=resolved,
        directories=page,
        total=total,
        limit=limit,
        offset=offset,
    )
