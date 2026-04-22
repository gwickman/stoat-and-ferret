"""Tests for feature flag settings, startup audit, and /api/v1/flags (BL-268)."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.lifespan import (
    FEATURE_FLAG_NAMES,
    record_feature_flags,
)
from stoat_ferret.api.settings import Settings, get_settings
from stoat_ferret.models.flags import FlagsResponse

FLAG_ENV_VARS: tuple[str, ...] = (
    "STOAT_TESTING_MODE",
    "STOAT_SEED_ENDPOINT",
    "STOAT_SYNTHETIC_MONITORING",
    "STOAT_BATCH_RENDERING",
    "STOAT_WS_REPLAY_BUFFER_SIZE",
    "STOAT_WS_REPLAY_TTL_SECONDS",
)


@pytest.fixture
def clear_flag_env() -> Generator[None, None, None]:
    """Remove STOAT_* flag env vars and restore afterwards.

    Also clears the Settings lru_cache so each test observes its own
    fresh process state rather than values captured by a prior test.
    """
    saved: dict[str, str] = {}
    for name in FLAG_ENV_VARS:
        if name in os.environ:
            saved[name] = os.environ.pop(name)
    get_settings.cache_clear()
    try:
        yield
    finally:
        for name in FLAG_ENV_VARS:
            os.environ.pop(name, None)
        for name, value in saved.items():
            os.environ[name] = value
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# FR-002: Default flag values
# ---------------------------------------------------------------------------


def test_feature_flags_default_values(clear_flag_env: None) -> None:
    """Without STOAT_* env vars Settings produces the documented defaults."""
    settings = Settings()
    assert settings.testing_mode is False
    assert settings.seed_endpoint is False
    assert settings.synthetic_monitoring is False
    assert settings.batch_rendering is True


# ---------------------------------------------------------------------------
# FR-005: Replay buffer settings
# ---------------------------------------------------------------------------


def test_ws_replay_settings_added(clear_flag_env: None) -> None:
    """ws_replay_buffer_size and ws_replay_ttl_seconds carry BL-313 defaults."""
    settings = Settings()
    assert settings.ws_replay_buffer_size == 1000
    assert settings.ws_replay_ttl_seconds == 300


# ---------------------------------------------------------------------------
# FR-001: STOAT_* env vars populate Settings (Pydantic V2 bool coercion)
# ---------------------------------------------------------------------------


def test_feature_flags_loaded_from_env(
    monkeypatch: pytest.MonkeyPatch, clear_flag_env: None
) -> None:
    """STOAT_* env values flow through to the corresponding Settings fields."""
    monkeypatch.setenv("STOAT_TESTING_MODE", "true")
    monkeypatch.setenv("STOAT_SEED_ENDPOINT", "true")
    monkeypatch.setenv("STOAT_SYNTHETIC_MONITORING", "true")
    monkeypatch.setenv("STOAT_BATCH_RENDERING", "false")

    settings = Settings()
    assert settings.testing_mode is True
    assert settings.seed_endpoint is True
    assert settings.synthetic_monitoring is True
    assert settings.batch_rendering is False


def test_feature_flags_string_true_is_truthy(
    monkeypatch: pytest.MonkeyPatch, clear_flag_env: None
) -> None:
    """The literal string ``"true"`` coerces to ``True`` via Pydantic V2."""
    monkeypatch.setenv("STOAT_TESTING_MODE", "true")

    settings = Settings()
    assert settings.testing_mode is True


# ---------------------------------------------------------------------------
# FR-003: Startup audit inserts 4 rows (NFR-001: audit completeness)
# ---------------------------------------------------------------------------


def test_record_feature_flags_inserts_four_rows(tmp_path: Path, clear_flag_env: None) -> None:
    """record_feature_flags() writes one row per flag with matching values."""
    db_path = tmp_path / "flags.db"
    # Pre-create schema so the helper only performs the insert path.
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE feature_flag_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flag_name TEXT NOT NULL,
                flag_value INTEGER NOT NULL,
                logged_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    settings = Settings(
        testing_mode=True,
        seed_endpoint=False,
        synthetic_monitoring=True,
        batch_rendering=False,
    )
    record_feature_flags(settings=settings, db_path=str(db_path))

    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT flag_name, flag_value FROM feature_flag_log ORDER BY id"
        ).fetchall()

    names = [r[0] for r in rows]
    values = {r[0]: bool(r[1]) for r in rows}
    assert len(rows) == 4
    assert set(names) == set(FEATURE_FLAG_NAMES)
    assert values["testing_mode"] is True
    assert values["seed_endpoint"] is False
    assert values["synthetic_monitoring"] is True
    assert values["batch_rendering"] is False


def test_record_feature_flags_self_heals_missing_table(
    tmp_path: Path, clear_flag_env: None
) -> None:
    """The helper creates feature_flag_log when the table is absent."""
    db_path = tmp_path / "flags.db"
    # Ensure the file exists but has no tables.
    sqlite3.connect(str(db_path)).close()

    settings = Settings()
    record_feature_flags(settings=settings, db_path=str(db_path))

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM feature_flag_log").fetchone()
    assert row[0] == 4


async def test_startup_audit_inserts_rows(tmp_path: Path, clear_flag_env: None) -> None:
    """Running the full lifespan writes exactly four feature_flag_log rows."""
    db_path = tmp_path / "startup.db"
    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    get_settings.cache_clear()

    try:
        app = create_app()
        async with lifespan(app):
            pass

        with sqlite3.connect(str(db_path)) as conn:
            rows = conn.execute(
                "SELECT flag_name, flag_value, logged_at FROM feature_flag_log"
            ).fetchall()
    finally:
        os.environ.pop("STOAT_DATABASE_PATH", None)
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
        get_settings.cache_clear()

    assert len(rows) == 4
    names = {r[0] for r in rows}
    assert names == set(FEATURE_FLAG_NAMES)
    for _name, value, logged_at in rows:
        assert value in (0, 1)
        assert isinstance(logged_at, str) and len(logged_at) > 0


# ---------------------------------------------------------------------------
# FR-001, FR-006: GET /api/v1/flags contract + schema
# ---------------------------------------------------------------------------


@pytest.fixture
async def flags_client(tmp_path: Path, clear_flag_env: None) -> httpx.AsyncClient:
    """Async client exercising the real lifespan, isolated to tmp_path.

    The caller may set STOAT_* env vars before entering the fixture; they
    are cleared by ``clear_flag_env`` on teardown.
    """
    db_path = tmp_path / "flags_api.db"
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

    os.environ.pop("STOAT_DATABASE_PATH", None)
    os.environ.pop("STOAT_THUMBNAIL_DIR", None)
    get_settings.cache_clear()


async def test_flags_endpoint_schema(flags_client: httpx.AsyncClient) -> None:
    """GET /api/v1/flags returns a body that deserialises to FlagsResponse."""
    resp = await flags_client.get("/api/v1/flags")
    assert resp.status_code == 200

    body = resp.json()
    parsed = FlagsResponse.model_validate(body)
    assert parsed.testing_mode is False
    assert parsed.seed_endpoint is False
    assert parsed.synthetic_monitoring is False
    assert parsed.batch_rendering is True


async def test_flags_endpoint_returns_correct_values(tmp_path: Path, clear_flag_env: None) -> None:
    """With STOAT_TESTING_MODE=true the endpoint returns ``testing_mode: true``.

    Re-creates its own app within the test rather than reusing the fixture
    so the env var is in place before ``get_settings()`` is cached.
    """
    os.environ["STOAT_TESTING_MODE"] = "true"
    db_path = tmp_path / "flags_api.db"
    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    get_settings.cache_clear()

    try:
        app = create_app()
        async with (
            lifespan(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client,
        ):
            resp = await client.get("/api/v1/flags")
    finally:
        os.environ.pop("STOAT_TESTING_MODE", None)
        os.environ.pop("STOAT_DATABASE_PATH", None)
        os.environ.pop("STOAT_THUMBNAIL_DIR", None)
        get_settings.cache_clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["testing_mode"] is True
    assert body["batch_rendering"] is True  # default preserved
