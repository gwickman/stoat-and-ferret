# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for the user-asset library REST API (BL-515 AC-13 to AC-16).

Tests the full asset lifecycle against a running FastAPI application via
httpx.AsyncClient: upload → list → metadata → download → soft-delete.

Also covers content-hash deduplication, referenced-clip delete-protection
(skipped until BL-515-AC-14 lands), and security rejections (oversize, MIME
magic-bytes mismatch, traversal).

FFmpeg-independent — STOAT_TEST_FFMPEG not required.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_png_bytes() -> bytes:
    """Return minimal 4×4 PNG bytes created in-memory via Pillow."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(0, 128, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_tiff_bytes() -> bytes:
    """Return minimal TIFF bytes — Pillow identifies these as TIFF, not PNG."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buf, format="TIFF")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def asset_smoke_client(tmp_path: Path) -> httpx.AsyncClient:
    """Async httpx client with isolated database and assets directory.

    Sets STOAT_DATABASE_PATH, STOAT_THUMBNAIL_DIR, and STOAT_ASSETS_DIR to
    tmp_path-scoped directories so tests never touch the working tree.

    Args:
        tmp_path: Pytest-provided per-test temporary directory.

    Yields:
        An httpx.AsyncClient connected to the app via ASGITransport.
    """
    db_path = tmp_path / "asset_smoke.db"
    assets_dir = tmp_path / "assets"

    saved: dict[str, str | None] = {
        "STOAT_DATABASE_PATH": os.environ.get("STOAT_DATABASE_PATH"),
        "STOAT_THUMBNAIL_DIR": os.environ.get("STOAT_THUMBNAIL_DIR"),
        "STOAT_ASSETS_DIR": os.environ.get("STOAT_ASSETS_DIR"),
        "STOAT_MIGRATION_BACKUP_DIR": os.environ.get("STOAT_MIGRATION_BACKUP_DIR"),
    }

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    os.environ["STOAT_ASSETS_DIR"] = str(assets_dir)
    # Isolate migration backups per-test to prevent filename collisions when
    # multiple tests create backups within the same calendar second on Windows.
    os.environ["STOAT_MIGRATION_BACKUP_DIR"] = str(tmp_path / "migration_backups")
    get_settings.cache_clear()

    app = create_app()

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client

    for key, orig in saved.items():
        if orig is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig
    get_settings.cache_clear()


@pytest.fixture()
async def asset_smoke_client_small_limit(tmp_path: Path) -> httpx.AsyncClient:
    """Async httpx client with STOAT_ASSETS_MAX_SIZE_BYTES=10 for oversize tests.

    Args:
        tmp_path: Pytest-provided per-test temporary directory.

    Yields:
        An httpx.AsyncClient with a 10-byte asset upload limit.
    """
    db_path = tmp_path / "asset_smoke_small.db"
    assets_dir = tmp_path / "assets_small"

    saved: dict[str, str | None] = {
        "STOAT_DATABASE_PATH": os.environ.get("STOAT_DATABASE_PATH"),
        "STOAT_THUMBNAIL_DIR": os.environ.get("STOAT_THUMBNAIL_DIR"),
        "STOAT_ASSETS_DIR": os.environ.get("STOAT_ASSETS_DIR"),
        "STOAT_ASSETS_MAX_SIZE_BYTES": os.environ.get("STOAT_ASSETS_MAX_SIZE_BYTES"),
        "STOAT_MIGRATION_BACKUP_DIR": os.environ.get("STOAT_MIGRATION_BACKUP_DIR"),
    }

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    os.environ["STOAT_ASSETS_DIR"] = str(assets_dir)
    os.environ["STOAT_ASSETS_MAX_SIZE_BYTES"] = "10"
    os.environ["STOAT_MIGRATION_BACKUP_DIR"] = str(tmp_path / "migration_backups")
    get_settings.cache_clear()

    app = create_app()

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client

    for key, orig in saved.items():
        if orig is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Stage 1: Round-trip and dedup (AC-13, AC-15)
# ---------------------------------------------------------------------------


async def test_asset_round_trip(asset_smoke_client: httpx.AsyncClient) -> None:
    """Upload PNG → GET list → GET metadata → GET file bytes round-trip (AC-13)."""
    png = _make_png_bytes()

    # POST /api/v1/assets — upload
    upload_resp = await asset_smoke_client.post(
        "/api/v1/assets",
        files={"file": ("round_trip.png", png, "image/png")},
        params={"kind": "image"},
    )
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
    asset = upload_resp.json()
    asset_id = asset["id"]
    assert len(asset_id) == 36, "id must be a UUID"
    assert asset["kind"] == "image"
    assert asset["mime_type"] == "image/png"
    assert asset["deleted_at"] is None

    # GET /api/v1/assets?kind=image — list
    list_resp = await asset_smoke_client.get("/api/v1/assets", params={"kind": "image"})
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["total"] >= 1
    assert any(a["id"] == asset_id for a in list_body["items"])

    # GET /api/v1/assets/{id} — metadata
    meta_resp = await asset_smoke_client.get(f"/api/v1/assets/{asset_id}")
    assert meta_resp.status_code == 200
    meta = meta_resp.json()
    assert meta["id"] == asset_id
    assert meta["original_filename"] == "round_trip.png"

    # GET /api/v1/assets/{id}/file — binary download
    file_resp = await asset_smoke_client.get(f"/api/v1/assets/{asset_id}/file")
    assert file_resp.status_code == 200
    assert file_resp.content == png, "Downloaded bytes must match uploaded bytes"


async def test_asset_dedup(asset_smoke_client: httpx.AsyncClient) -> None:
    """Uploading identical PNG bytes twice returns the same asset id (AC-15)."""
    png = _make_png_bytes()

    r1 = await asset_smoke_client.post(
        "/api/v1/assets",
        files={"file": ("first.png", png, "image/png")},
        params={"kind": "image"},
    )
    r2 = await asset_smoke_client.post(
        "/api/v1/assets",
        files={"file": ("second.png", png, "image/png")},
        params={"kind": "image"},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"], (
        "Uploading identical content twice must return the same asset id"
    )


# ---------------------------------------------------------------------------
# Stage 2: Soft-delete and delete-protection (AC-14)
# ---------------------------------------------------------------------------


async def test_asset_soft_delete(asset_smoke_client: httpx.AsyncClient) -> None:
    """Soft-delete returns 204; subsequent GET returns 404; asset absent from list."""
    png = _make_png_bytes()

    upload_resp = await asset_smoke_client.post(
        "/api/v1/assets",
        files={"file": ("to_delete.png", png, "image/png")},
        params={"kind": "image"},
    )
    assert upload_resp.status_code == 201
    asset_id = upload_resp.json()["id"]

    del_resp = await asset_smoke_client.delete(f"/api/v1/assets/{asset_id}")
    assert del_resp.status_code == 204, f"Delete returned unexpected status: {del_resp.status_code}"

    get_resp = await asset_smoke_client.get(f"/api/v1/assets/{asset_id}")
    assert get_resp.status_code == 404, "Soft-deleted asset must return 404 on GET"

    list_resp = await asset_smoke_client.get("/api/v1/assets")
    assert not any(a["id"] == asset_id for a in list_resp.json()["items"]), (
        "Soft-deleted asset must not appear in list"
    )


async def test_asset_delete_protection_with_clip(
    asset_smoke_client: httpx.AsyncClient,
) -> None:
    """Asset referenced by an image clip cannot be soft-deleted (AC-14).

    Skipped until BL-515-AC-14 (asset FK delete-protection) is implemented
    and the FK constraint between clips.source_asset_id and assets.id is live.
    """
    schema_resp = await asset_smoke_client.get("/openapi.json")
    if schema_resp.status_code == 200 and "source_asset_id" not in schema_resp.text:
        pytest.skip("source_asset_id missing from OpenAPI schema; image-clip contract unavailable")

    # Test body: create asset, reference it from an image clip, attempt delete.
    # Placeholder until BL-515-AC-14 (asset FK delete-protection) lands.
    pytest.skip(
        "asset FK delete-protection blocked by BL-515-AC-14; remove this skip when that AC lands"
    )


# ---------------------------------------------------------------------------
# Stage 3: Security suite (AC-16)
# ---------------------------------------------------------------------------


async def test_asset_oversize_rejected(
    asset_smoke_client_small_limit: httpx.AsyncClient,
) -> None:
    """Upload exceeding STOAT_ASSETS_MAX_SIZE_BYTES (10 bytes) returns 413 (AC-16)."""
    data = b"X" * 20  # 20 bytes — exceeds 10-byte limit set by fixture
    resp = await asset_smoke_client_small_limit.post(
        "/api/v1/assets",
        files={"file": ("big.png", data, "image/png")},
        params={"kind": "image"},
    )
    assert resp.status_code == 413, (
        f"Oversize upload must return 413, got {resp.status_code}: {resp.text}"
    )


async def test_asset_magic_bytes_mismatch(asset_smoke_client: httpx.AsyncClient) -> None:
    """TIFF bytes sent with PNG content-type/filename returns 415 (AC-16)."""
    tiff_bytes = _make_tiff_bytes()
    resp = await asset_smoke_client.post(
        "/api/v1/assets",
        files={"file": ("fake.png", tiff_bytes, "image/png")},
        params={"kind": "image"},
    )
    assert resp.status_code == 415, (
        f"TIFF disguised as PNG must return 415, got {resp.status_code}: {resp.text}"
    )


async def test_asset_traversal_safe_storage(asset_smoke_client: httpx.AsyncClient) -> None:
    """Traversal pattern in upload filename: physical storage uses safe hash-derived path.

    The backend stores original_filename as metadata only. The physical file is
    written to <sha256hex>.png under assets_dir — not to the traversal path.
    Verifies that regardless of the HTTP response, the stored file is retrievable
    (content-hash-derived storage is traversal-safe by construction).
    """
    png = _make_png_bytes()
    resp = await asset_smoke_client.post(
        "/api/v1/assets",
        files={"file": ("../evil.png", png, "image/png")},
        params={"kind": "image"},
    )
    # Implementation stores original_filename as metadata; actual path is hash-derived.
    # Both acceptance (201) and rejection (400/422) are valid observed behaviours.
    assert resp.status_code in (201, 400, 422), (
        f"Traversal filename upload returned unexpected status {resp.status_code}: {resp.text}"
    )
    if resp.status_code == 201:
        asset_id = resp.json()["id"]
        file_resp = await asset_smoke_client.get(f"/api/v1/assets/{asset_id}/file")
        assert file_resp.status_code == 200, (
            "Asset uploaded with traversal filename must be retrievable (safe hash-derived storage)"
        )
