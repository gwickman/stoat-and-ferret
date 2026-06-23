# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for scan recursion guard (BL-391).

Verifies that POST /api/v1/videos/scan with recursive=true is rejected when the
target path contains subdirectories, returning HTTP 400 RECURSIVE_SCAN_FORBIDDEN.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest


@pytest.fixture()
def multi_level_dir(tmp_path: Path) -> Path:
    """Temporary directory with one subdirectory."""
    (tmp_path / "subdir").mkdir()
    return tmp_path


@pytest.fixture()
def flat_dir(tmp_path: Path) -> Path:
    """Temporary directory with no subdirectories (files only)."""
    (tmp_path / "video.mp4").touch()
    return tmp_path


async def test_recursive_true_on_multi_level_dir_returns_400(
    smoke_client: httpx.AsyncClient,
    multi_level_dir: Path,
) -> None:
    """recursive=true on a directory with subdirs returns HTTP 400 RECURSIVE_SCAN_FORBIDDEN."""
    resp = await smoke_client.post(
        "/api/v1/videos/scan",
        json={"path": str(multi_level_dir), "recursive": True},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "RECURSIVE_SCAN_FORBIDDEN"
    assert "subdirector" in body["detail"]["message"].lower()


async def test_recursive_false_on_multi_level_dir_returns_202(
    smoke_client: httpx.AsyncClient,
    multi_level_dir: Path,
) -> None:
    """recursive=false on a directory with subdirs is accepted (HTTP 202)."""
    resp = await smoke_client.post(
        "/api/v1/videos/scan",
        json={"path": str(multi_level_dir), "recursive": False},
    )
    assert resp.status_code == 202


async def test_recursive_true_on_flat_dir_returns_202(
    smoke_client: httpx.AsyncClient,
    flat_dir: Path,
) -> None:
    """recursive=true on a directory with no subdirs is accepted (HTTP 202)."""
    resp = await smoke_client.post(
        "/api/v1/videos/scan",
        json={"path": str(flat_dir), "recursive": True},
    )
    assert resp.status_code == 202
