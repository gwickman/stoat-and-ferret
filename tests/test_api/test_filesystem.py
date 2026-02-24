"""Tests for the filesystem directory listing endpoint."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_list_directories_valid_path(client: TestClient, tmp_path: os.PathLike) -> None:
    """Valid directory path returns subdirectory list."""
    # Create subdirectories
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / ".hidden").mkdir()
    # Create a file (should be excluded)
    (tmp_path / "file.txt").touch()

    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = []
        response = client.get(
            "/api/v1/filesystem/directories",
            params={"path": str(tmp_path)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["path"] == str(tmp_path)
    names = [d["name"] for d in data["directories"]]
    assert "alpha" in names
    assert "beta" in names
    # Hidden dirs and files should be excluded
    assert ".hidden" not in names
    assert "file.txt" not in names


@pytest.mark.api
def test_list_directories_nonexistent_path(client: TestClient) -> None:
    """Non-existent path returns 404."""
    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = []
        response = client.get(
            "/api/v1/filesystem/directories",
            params={"path": "/nonexistent/path/that/does/not/exist"},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PATH_NOT_FOUND"


@pytest.mark.api
def test_list_directories_file_path(client: TestClient, tmp_path: os.PathLike) -> None:
    """File path (not a directory) returns 400."""
    file_path = tmp_path / "afile.txt"
    file_path.touch()

    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = []
        response = client.get(
            "/api/v1/filesystem/directories",
            params={"path": str(file_path)},
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "NOT_A_DIRECTORY"


@pytest.mark.api
def test_list_directories_outside_allowed_roots(client: TestClient, tmp_path: os.PathLike) -> None:
    """Path outside allowed_scan_roots returns 403."""
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = [str(allowed_root)]
        response = client.get(
            "/api/v1/filesystem/directories",
            params={"path": str(outside)},
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PATH_NOT_ALLOWED"


@pytest.mark.api
def test_list_directories_path_traversal(client: TestClient, tmp_path: os.PathLike) -> None:
    """Path traversal attempts (../) are rejected when restricted."""
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    # Try to escape via path traversal
    traversal_path = str(allowed_root / ".." / "outside")

    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = [str(allowed_root)]
        response = client.get(
            "/api/v1/filesystem/directories",
            params={"path": traversal_path},
        )

    assert response.status_code in (403, 404)


@pytest.mark.api
def test_list_directories_default_path_with_roots(
    client: TestClient, tmp_path: os.PathLike
) -> None:
    """When no path given and roots configured, defaults to first root."""
    root_dir = tmp_path / "media"
    root_dir.mkdir()
    (root_dir / "subdir").mkdir()

    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = [str(root_dir)]
        response = client.get("/api/v1/filesystem/directories")

    assert response.status_code == 200
    data = response.json()
    assert data["path"] == str(root_dir)
    assert len(data["directories"]) == 1
    assert data["directories"][0]["name"] == "subdir"


@pytest.mark.api
def test_list_directories_sorted(client: TestClient, tmp_path: os.PathLike) -> None:
    """Directories are returned sorted alphabetically (case-insensitive)."""
    (tmp_path / "zebra").mkdir()
    (tmp_path / "Apple").mkdir()
    (tmp_path / "banana").mkdir()

    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = []
        response = client.get(
            "/api/v1/filesystem/directories",
            params={"path": str(tmp_path)},
        )

    assert response.status_code == 200
    names = [d["name"] for d in response.json()["directories"]]
    assert names == ["Apple", "banana", "zebra"]


@pytest.mark.api
def test_list_directories_empty(client: TestClient, tmp_path: os.PathLike) -> None:
    """Empty directory returns empty list."""
    with patch("stoat_ferret.api.routers.filesystem.get_settings") as mock_settings:
        mock_settings.return_value.allowed_scan_roots = []
        response = client.get(
            "/api/v1/filesystem/directories",
            params={"path": str(tmp_path)},
        )

    assert response.status_code == 200
    assert response.json()["directories"] == []
