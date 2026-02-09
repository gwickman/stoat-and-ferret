"""Security tests for path validation and scan root restrictions.

Tests cover:
- Path traversal attacks (../, ..\\, URL-encoded variants)
- Null byte injection in paths
- ALLOWED_SCAN_ROOTS enforcement
- Symlink path resolution
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.services.scan import validate_scan_path


class TestValidateScanPath:
    """Unit tests for the validate_scan_path function."""

    def test_empty_allowlist_permits_all(self, tmp_path: Any) -> None:
        """Empty allowed_roots list permits any path."""
        assert validate_scan_path(str(tmp_path), []) is None

    def test_path_under_allowed_root(self, tmp_path: Any) -> None:
        """Path under an allowed root is permitted."""
        subdir = tmp_path / "media"
        subdir.mkdir()
        assert validate_scan_path(str(subdir), [str(tmp_path)]) is None

    def test_path_not_under_any_root(self, tmp_path: Any) -> None:
        """Path outside all allowed roots is rejected."""
        other = tmp_path / "other"
        other.mkdir()
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        result = validate_scan_path(str(other), [str(allowed)])
        assert result is not None
        assert "not under any allowed scan root" in result

    def test_exact_root_is_allowed(self, tmp_path: Any) -> None:
        """The root directory itself is a valid scan target."""
        assert validate_scan_path(str(tmp_path), [str(tmp_path)]) is None

    def test_multiple_roots(self, tmp_path: Any) -> None:
        """Path matching any of multiple roots is permitted."""
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        root_a.mkdir()
        root_b.mkdir()
        target = root_b / "videos"
        target.mkdir()
        assert validate_scan_path(str(target), [str(root_a), str(root_b)]) is None

    def test_traversal_outside_root_is_blocked(self, tmp_path: Any) -> None:
        """Path traversal via ../ that escapes the root is rejected."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        # Try to traverse up and out of the allowed root
        traversal_path = str(allowed / ".." / "other")
        result = validate_scan_path(traversal_path, [str(allowed)])
        assert result is not None

    def test_traversal_back_slash_blocked(self, tmp_path: Any) -> None:
        r"""Path traversal via ..\\ that escapes the root is rejected."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        traversal_path = str(allowed) + "\\..\\.."
        result = validate_scan_path(traversal_path, [str(allowed)])
        assert result is not None

    @pytest.mark.skipif(sys.platform == "win32", reason="Symlinks need admin on Windows")
    def test_symlink_resolved_against_root(self, tmp_path: Any) -> None:
        """Symlinks are resolved before checking against allowed roots."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        # Create a symlink inside allowed that points outside
        link = allowed / "sneaky"
        link.symlink_to(outside)
        result = validate_scan_path(str(link), [str(allowed)])
        # The resolved path is outside, so it should be blocked
        assert result is not None


class TestPathTraversalViaApi:
    """Integration tests for path traversal attacks through the scan endpoint."""

    def test_traversal_relative_path(self, client: TestClient, tmp_path: Any) -> None:
        """Relative path traversal ../../../etc is rejected at the isdir check."""
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": "../../../etc"},
        )
        # Either 400 (not a dir) or 403 (not allowed) is acceptable
        assert response.status_code in (400, 403)

    def test_null_byte_in_path(self, client: TestClient) -> None:
        """Null byte in scan path is rejected."""
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": "/valid/path\x00/injected"},
        )
        assert response.status_code == 400

    def test_traversal_with_allowed_roots(self, client: TestClient, tmp_path: Any) -> None:
        """Path outside allowed roots returns 403."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        with patch("stoat_ferret.api.routers.videos.get_settings") as mock_settings:
            mock_settings.return_value.allowed_scan_roots = [str(allowed)]
            response = client.post(
                "/api/v1/videos/scan",
                json={"path": str(outside)},
            )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "PATH_NOT_ALLOWED"

    def test_allowed_root_permits_scan(self, client: TestClient, tmp_path: Any) -> None:
        """Path under allowed root returns 202 (scan submitted)."""
        with patch("stoat_ferret.api.routers.videos.get_settings") as mock_settings:
            mock_settings.return_value.allowed_scan_roots = [str(tmp_path)]
            response = client.post(
                "/api/v1/videos/scan",
                json={"path": str(tmp_path)},
            )
        assert response.status_code == 202

    def test_traversal_encoded_dots(self, client: TestClient) -> None:
        """URL-encoded path traversal sequences are rejected."""
        # %2e%2e = .. URL-encoded; FastAPI decodes JSON, not URLs,
        # but we test the literal string to ensure the path doesn't resolve
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": "%2e%2e/%2e%2e/etc"},
        )
        assert response.status_code == 400
