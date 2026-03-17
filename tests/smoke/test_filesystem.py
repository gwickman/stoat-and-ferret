"""Smoke tests for filesystem directory listing (BL-123).

Validates GET /api/v1/filesystem/directories with real filesystem I/O
using pytest tmp_path fixtures for deterministic, cross-platform tests.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest


@pytest.fixture()
def dir_tree(tmp_path: Path) -> Path:
    """Create a deterministic directory structure for filesystem tests.

    Creates three visible subdirectories and one hidden directory.
    Returns the root tmp_path.
    """
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / "gamma").mkdir()
    (tmp_path / ".hidden").mkdir()
    return tmp_path


async def test_filesystem_directories(
    smoke_client: httpx.AsyncClient,
    dir_tree: Path,
) -> None:
    """GET with valid path returns 200 with sorted subdirectories, hidden excluded."""
    resp = await smoke_client.get(
        "/api/v1/filesystem/directories",
        params={"path": str(dir_tree)},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["path"] == str(dir_tree.resolve())

    names = [d["name"] for d in body["directories"]]
    assert names == ["alpha", "beta", "gamma"]

    # Verify pagination metadata
    assert body["total"] == 3
    assert body["limit"] == 20
    assert body["offset"] == 0


async def test_filesystem_directories_not_found(
    smoke_client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    """GET with nonexistent path returns 404 PATH_NOT_FOUND."""
    nonexistent = tmp_path / "does_not_exist"
    resp = await smoke_client.get(
        "/api/v1/filesystem/directories",
        params={"path": str(nonexistent)},
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "PATH_NOT_FOUND"


async def test_filesystem_directories_hidden_excluded(
    smoke_client: httpx.AsyncClient,
    dir_tree: Path,
) -> None:
    """Hidden directories (starting with '.') are not included in the response."""
    resp = await smoke_client.get(
        "/api/v1/filesystem/directories",
        params={"path": str(dir_tree)},
    )
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()["directories"]]
    assert ".hidden" not in names
