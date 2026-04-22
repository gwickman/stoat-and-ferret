"""Application version endpoint backed by Rust VersionInfo (BL-267)."""

from __future__ import annotations

import asyncio
import sqlite3
import sys

import structlog
from fastapi import APIRouter, Request

from stoat_ferret.api.settings import Settings, get_settings
from stoat_ferret.models.version import AppVersionResponse
from stoat_ferret_core import VersionInfo

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["version"])


def _settings_from_request(request: Request) -> Settings:
    """Return Settings from app.state when present, falling back to get_settings().

    Mirrors the helper used by ``routers/flags.py`` so the endpoint stays
    callable in test mode that skips lifespan (``app.state._deps_injected``).
    """
    state_settings: Settings | None = getattr(request.app.state, "_settings", None)
    if state_settings is not None:
        return state_settings
    return get_settings()


def _read_alembic_revision(db_path: str) -> str:
    """Return the current ``alembic_version.version_num`` revision hash.

    Returns the literal string ``"none"`` if the database file is missing,
    the ``alembic_version`` table does not exist, or the table is empty.
    A synchronous sqlite3 connection is used so the call is safe from a
    thread-pool executor — matching the pattern used by the migration
    service.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = cursor.fetchone()
    except sqlite3.OperationalError:
        return "none"
    except sqlite3.DatabaseError:
        return "none"
    if row is None:
        return "none"
    revision = row[0]
    if not revision:
        return "none"
    return str(revision)


def _python_version_string() -> str:
    """Return the running Python interpreter version as ``major.minor.micro``."""
    info = sys.version_info
    return f"{info.major}.{info.minor}.{info.micro}"


@router.get("/version", response_model=AppVersionResponse)
async def get_version(request: Request) -> AppVersionResponse:
    """Return deployment version metadata for the running build (BL-267).

    The response combines three sources:

    - FastAPI app version (``app.version``) for ``app_version``.
    - Rust :class:`stoat_ferret_core.VersionInfo` for ``core_version``,
      ``build_timestamp``, and ``git_sha``; populated at compile time by
      ``build.rs``.
    - The current alembic revision (``alembic_version.version_num``) for
      ``database_version``. Returns ``"none"`` when the table is empty or
      missing so the response always validates.

    No expensive work runs inside the handler — the alembic lookup is a
    single indexed row read, and the Rust binding returns compile-time
    constants. The sqlite3 call is run on the default thread pool via
    :func:`asyncio.to_thread` so the event loop stays responsive.

    Args:
        request: The FastAPI request object; used to reach ``app.state``
            for settings resolution and the app version string.

    Returns:
        A :class:`AppVersionResponse` with the six deployment metadata fields.
    """
    settings = _settings_from_request(request)
    info = VersionInfo.current()
    database_version = await asyncio.to_thread(_read_alembic_revision, settings.database_path)
    response = AppVersionResponse(
        app_version=str(request.app.version),
        core_version=info.core_version,
        build_timestamp=info.build_timestamp,
        git_sha=info.git_sha,
        python_version=_python_version_string(),
        database_version=database_version,
    )
    logger.info(
        "version.requested",
        app_version=response.app_version,
        core_version=response.core_version,
        database_version=response.database_version,
    )
    return response
