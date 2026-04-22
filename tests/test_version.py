"""Tests for VersionResponse and GET /api/v1/version (BL-267)."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings
from stoat_ferret.models.version import VersionResponse
from stoat_ferret_core import VersionInfo

# ---------------------------------------------------------------------------
# FR-001: Pydantic model accepts all six required fields
# ---------------------------------------------------------------------------


def test_version_response_has_required_fields() -> None:
    """VersionResponse validates when all six required fields are supplied."""
    payload = {
        "app_version": "0.1.0",
        "core_version": "0.1.0",
        "build_timestamp": "2026-04-22T12:00:00Z",
        "git_sha": "abc1234",
        "python_version": "3.12.0",
        "database_version": "1e895699ad50",
    }
    parsed = VersionResponse.model_validate(payload)
    assert parsed.app_version == "0.1.0"
    assert parsed.core_version == "0.1.0"
    assert parsed.build_timestamp == "2026-04-22T12:00:00Z"
    assert parsed.git_sha == "abc1234"
    assert parsed.python_version == "3.12.0"
    assert parsed.database_version == "1e895699ad50"


def test_version_response_rejects_missing_fields() -> None:
    """Omitting any of the six required fields is a validation error."""
    with pytest.raises(ValueError):
        VersionResponse.model_validate(
            {
                "app_version": "0.1.0",
                "core_version": "0.1.0",
                "build_timestamp": "2026-04-22T12:00:00Z",
                "git_sha": "abc1234",
                "python_version": "3.12.0",
                # database_version missing
            }
        )


# ---------------------------------------------------------------------------
# FR-002: core_version comes from Rust VersionInfo.current()
# ---------------------------------------------------------------------------


@pytest.fixture
async def version_client(tmp_path: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async client with a fresh app, isolated SQLite db, real lifespan migrations."""
    db_path = tmp_path / "version_api.db"
    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")
    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
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

    if orig_db is None:
        os.environ.pop("STOAT_DATABASE_PATH", None)
    else:
        os.environ["STOAT_DATABASE_PATH"] = orig_db
    if orig_thumb is None:
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
    else:
        os.environ["STOAT_THUMBNAIL_DIR"] = orig_thumb
    get_settings.cache_clear()


async def test_version_endpoint_calls_rust_binding(
    version_client: httpx.AsyncClient,
) -> None:
    """Endpoint core_version matches VersionInfo.current().core_version."""
    expected = VersionInfo.current().core_version

    resp = await version_client.get("/api/v1/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["core_version"] == expected


# ---------------------------------------------------------------------------
# FR-001/FR-006: Contract — response body round-trips through VersionResponse
# ---------------------------------------------------------------------------


async def test_version_endpoint_schema(
    version_client: httpx.AsyncClient,
) -> None:
    """GET /api/v1/version returns a body that deserialises to VersionResponse."""
    resp = await version_client.get("/api/v1/version")
    assert resp.status_code == 200

    body = resp.json()
    parsed = VersionResponse.model_validate(body)
    assert parsed.app_version
    assert parsed.core_version
    assert parsed.build_timestamp
    assert parsed.git_sha  # non-empty (may be literal "unknown")
    assert parsed.python_version
    assert parsed.database_version  # non-empty (may be literal "none")


# ---------------------------------------------------------------------------
# FR-003: database_version matches alembic_version.version_num
# ---------------------------------------------------------------------------


async def test_version_endpoint_database_version_matches_alembic(
    tmp_path: Path,
    version_client: httpx.AsyncClient,
) -> None:
    """database_version in the response equals the alembic_version.version_num row."""
    db_path = os.environ["STOAT_DATABASE_PATH"]
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    assert row is not None, "alembic_version table should be populated after lifespan"
    expected_revision = row[0]

    resp = await version_client.get("/api/v1/version")
    assert resp.status_code == 200
    assert resp.json()["database_version"] == expected_revision
