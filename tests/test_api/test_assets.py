# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""System tests for asset library REST endpoints (BL-515).

Uses TestClient with an in-memory asset repository and a settings override
that redirects STOAT_ASSETS_DIR to a pytest tmp_path.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.db.asset_repository import AssetRecord
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.batch_repository import InMemoryBatchRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository

# ---------------------------------------------------------------------------
# In-memory asset repository (test double)
# ---------------------------------------------------------------------------


class InMemoryAssetRepository:
    """Dict-backed implementation of AsyncAssetRepository for tests."""

    def __init__(self) -> None:
        self._store: dict[str, AssetRecord] = {}

    async def insert(self, asset: AssetRecord) -> AssetRecord:
        self._store[asset.id] = asset
        return asset

    async def get_by_id(self, asset_id: str) -> AssetRecord | None:
        return self._store.get(asset_id)

    async def get_by_content_hash(self, content_hash: str) -> AssetRecord | None:
        for r in self._store.values():
            if r.content_hash == content_hash:
                return r
        return None

    async def list_assets(
        self,
        kind: str | None,
        tags: list[str] | None,
        offset: int,
        limit: int,
    ) -> list[AssetRecord]:
        items = [r for r in self._store.values() if r.deleted_at is None]
        if kind is not None:
            items = [r for r in items if r.kind == kind]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[offset : offset + limit]

    async def soft_delete(self, asset_id: str) -> bool:
        r = self._store.get(asset_id)
        if r is None or r.deleted_at is not None:
            return False
        r.deleted_at = datetime.now(timezone.utc).isoformat()
        return True

    async def restore(self, asset_id: str) -> AssetRecord | None:
        r = self._store.get(asset_id)
        if r is None:
            return None
        r.deleted_at = None
        r.updated_at = datetime.now(timezone.utc).isoformat()
        return r


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(0, 128, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def asset_repo() -> InMemoryAssetRepository:
    return InMemoryAssetRepository()


@pytest.fixture
def asset_app(
    asset_repo: InMemoryAssetRepository,
    tmp_path: Path,
) -> FastAPI:
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        timeline_repository=AsyncInMemoryTimelineRepository(),
        version_repository=AsyncInMemoryVersionRepository(),
        batch_repository=InMemoryBatchRepository(),
        proxy_repository=InMemoryProxyRepository(),
        render_repository=InMemoryRenderRepository(),
        job_queue=InMemoryJobQueue(),
        asset_repository=asset_repo,
    )
    return app


@pytest.fixture
def asset_client(
    asset_app: FastAPI,
    tmp_path: Path,
) -> Generator[TestClient, None, None]:
    with TestClient(asset_app) as client:
        # Override assets_dir to an isolated tmp dir (lifespan sets _settings first)
        asset_app.state._settings = Settings(assets_dir=tmp_path / "assets")
        yield client


# ---------------------------------------------------------------------------
# POST /api/v1/assets
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_upload_png_returns_201(asset_client: TestClient, tmp_path: Path) -> None:
    """Valid PNG upload returns 201 with a UUID asset_id."""
    data = _make_png()
    resp = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert len(body["id"]) == 36  # UUID
    assert body["kind"] == "image"
    assert body["mime_type"] == "image/png"
    assert body["deleted_at"] is None


@pytest.mark.api
def test_upload_jpeg_returns_201(asset_client: TestClient) -> None:
    """Valid JPEG upload is accepted."""
    data = _make_jpeg()
    resp = asset_client.post(
        "/api/v1/assets",
        files={"file": ("photo.jpg", data, "image/jpeg")},
        params={"kind": "image"},
    )
    assert resp.status_code == 201
    assert resp.json()["mime_type"] == "image/jpeg"


@pytest.mark.api
def test_upload_size_limit_returns_413(asset_client: TestClient, tmp_path: Path) -> None:
    """Upload exceeding max size returns 413."""
    # Override max_size to 10 bytes
    asset_client.app.state._settings = Settings(  # type: ignore[attr-defined]
        assets_dir=tmp_path / "assets", assets_max_size_bytes=10
    )
    data = b"X" * 20
    resp = asset_client.post(
        "/api/v1/assets",
        files={"file": ("big.png", data, "image/png")},
        params={"kind": "image"},
    )
    assert resp.status_code == 413


@pytest.mark.api
def test_upload_empty_file_returns_422(asset_client: TestClient) -> None:
    """Empty file upload returns 422."""
    resp = asset_client.post(
        "/api/v1/assets",
        files={"file": ("empty.png", b"", "image/png")},
        params={"kind": "image"},
    )
    assert resp.status_code == 422


@pytest.mark.api
def test_upload_non_image_bytes_returns_415(asset_client: TestClient) -> None:
    """Bytes that do not decode as a valid image return 415."""
    resp = asset_client.post(
        "/api/v1/assets",
        files={"file": ("fake.png", b"not-an-image\x00\x01\x02", "image/png")},
        params={"kind": "image"},
    )
    assert resp.status_code == 415


@pytest.mark.api
def test_upload_dedup_active_asset_returns_same_id(asset_client: TestClient) -> None:
    """Re-uploading identical content returns the existing asset (dedup)."""
    data = _make_png()
    r1 = asset_client.post(
        "/api/v1/assets",
        files={"file": ("a.png", data, "image/png")},
        params={"kind": "image"},
    )
    r2 = asset_client.post(
        "/api/v1/assets",
        files={"file": ("b.png", data, "image/png")},
        params={"kind": "image"},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.api
def test_upload_restores_soft_deleted_asset(
    asset_client: TestClient,
    asset_repo: InMemoryAssetRepository,
) -> None:
    """Re-uploading content of a soft-deleted asset restores it."""
    data = _make_png()
    r1 = asset_client.post(
        "/api/v1/assets",
        files={"file": ("a.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r1.json()["id"]

    # Soft-delete
    asset_client.delete(f"/api/v1/assets/{asset_id}")

    # Re-upload same bytes
    r2 = asset_client.post(
        "/api/v1/assets",
        files={"file": ("a.png", data, "image/png")},
        params={"kind": "image"},
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == asset_id
    assert r2.json()["deleted_at"] is None


# ---------------------------------------------------------------------------
# GET /api/v1/assets
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_list_assets_empty(asset_client: TestClient) -> None:
    """List returns empty items when no assets uploaded."""
    resp = asset_client.get("/api/v1/assets")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.api
def test_list_assets_returns_uploaded(asset_client: TestClient) -> None:
    """Uploaded asset appears in list."""
    data = _make_png()
    asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    resp = asset_client.get("/api/v1/assets")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.api
def test_list_assets_kind_filter(asset_client: TestClient) -> None:
    """kind= query param filters results."""
    data = _make_png()
    asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    resp = asset_client.get("/api/v1/assets", params={"kind": "font"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.api
def test_list_excludes_deleted_assets(asset_client: TestClient) -> None:
    """Soft-deleted assets do not appear in list."""
    data = _make_png()
    r = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r.json()["id"]
    asset_client.delete(f"/api/v1/assets/{asset_id}")

    resp = asset_client.get("/api/v1/assets")
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/assets/{asset_id}
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_get_asset_metadata(asset_client: TestClient) -> None:
    """GET /assets/{id} returns metadata for an uploaded asset."""
    data = _make_png()
    r = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r.json()["id"]

    resp = asset_client.get(f"/api/v1/assets/{asset_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == asset_id


@pytest.mark.api
def test_get_asset_not_found(asset_client: TestClient) -> None:
    """GET /assets/{id} returns 404 for unknown id."""
    resp = asset_client.get(f"/api/v1/assets/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.api
def test_get_deleted_asset_returns_404(asset_client: TestClient) -> None:
    """GET /assets/{id} returns 404 for soft-deleted asset."""
    data = _make_png()
    r = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r.json()["id"]
    asset_client.delete(f"/api/v1/assets/{asset_id}")

    resp = asset_client.get(f"/api/v1/assets/{asset_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/assets/{asset_id}/file
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_download_asset_file(asset_client: TestClient, tmp_path: Path) -> None:
    """GET /assets/{id}/file returns binary file content."""
    data = _make_png()
    r = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r.json()["id"]

    resp = asset_client.get(f"/api/v1/assets/{asset_id}/file")
    assert resp.status_code == 200
    assert resp.content == data


@pytest.mark.api
def test_download_asset_not_found(asset_client: TestClient) -> None:
    """GET /assets/{id}/file returns 404 for unknown asset."""
    resp = asset_client.get(f"/api/v1/assets/{uuid.uuid4()}/file")
    assert resp.status_code == 404


@pytest.mark.api
def test_download_deleted_asset_returns_404(asset_client: TestClient) -> None:
    """GET /assets/{id}/file returns 404 for soft-deleted asset."""
    data = _make_png()
    r = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r.json()["id"]
    asset_client.delete(f"/api/v1/assets/{asset_id}")

    resp = asset_client.get(f"/api/v1/assets/{asset_id}/file")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/assets/{asset_id}
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_delete_asset_returns_204(asset_client: TestClient) -> None:
    """DELETE /assets/{id} returns 204 on success."""
    data = _make_png()
    r = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r.json()["id"]

    resp = asset_client.delete(f"/api/v1/assets/{asset_id}")
    assert resp.status_code == 204


@pytest.mark.api
def test_delete_asset_not_found(asset_client: TestClient) -> None:
    """DELETE /assets/{id} returns 404 for unknown id."""
    resp = asset_client.delete(f"/api/v1/assets/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.api
def test_delete_asset_twice_returns_404(asset_client: TestClient) -> None:
    """Deleting an already-deleted asset returns 404."""
    data = _make_png()
    r = asset_client.post(
        "/api/v1/assets",
        files={"file": ("img.png", data, "image/png")},
        params={"kind": "image"},
    )
    asset_id = r.json()["id"]
    asset_client.delete(f"/api/v1/assets/{asset_id}")

    resp = asset_client.delete(f"/api/v1/assets/{asset_id}")
    assert resp.status_code == 404
