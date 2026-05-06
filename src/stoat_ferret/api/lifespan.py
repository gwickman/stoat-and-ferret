"""Application lifespan helpers for deployment-safety services (BL-266, BL-268).

This module holds the migration-safety and feature-flag audit portions of
the FastAPI lifespan so :mod:`stoat_ferret.api.app` can delegate to them
during startup. The main ``lifespan`` context in ``app.py`` calls
:func:`run_startup_migrations` before opening the long-lived aiosqlite
connection so that any pending schema migration is applied — and backed
up — before application code begins to use the database.

:func:`record_feature_flags` writes one ``feature_flag_log`` row per
STOAT_* feature flag and emits a ``deployment.feature_flag`` structured
event so the flag state that was active at startup is captured in an
append-only audit log.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from stoat_ferret.api.middleware.metrics import stoat_feature_flag_state
from stoat_ferret.api.services.migrations import MigrationService

if TYPE_CHECKING:
    from fastapi import FastAPI

    from stoat_ferret.api.settings import Settings
    from stoat_ferret.models.migrations import MigrationResult

FEATURE_FLAG_NAMES: tuple[str, ...] = (
    "testing_mode",
    "seed_endpoint",
    "synthetic_monitoring",
    "batch_rendering",
)

logger = structlog.get_logger(__name__)


async def run_startup_migrations(
    *,
    app: FastAPI,
    settings: Settings,
) -> MigrationResult | None:
    """Instantiate a :class:`MigrationService` and apply pending migrations.

    The service is stored on ``app.state.migration_service`` for later use
    by handlers. Migration failures are logged at the ``critical`` level
    but do not raise — operator intervention may be required, and health
    probes still need to respond.

    Args:
        app: The FastAPI application whose state receives the service.
        settings: Application settings providing ``database_path`` and
            ``migration_backup_dir``.

    Returns:
        The :class:`MigrationResult` produced by ``apply_pending()``, or
        ``None`` if an unexpected exception was caught.
    """
    db_path = Path(settings.database_path)
    if not db_path.exists():
        fixture_path = Path("tests/fixtures/stoat.seed.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(fixture_path, db_path)
        logger.info("deployment.bootstrap", action="fixture_copy")

    service = MigrationService(
        backup_dir=settings.migration_backup_dir,
        db_path=settings.database_path,
    )
    app.state.migration_service = service

    try:
        result = await service.apply_pending()
    except Exception as exc:
        logger.critical(
            "deployment.migration.unexpected_error",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return None

    if not result.success:
        logger.critical(
            "deployment.migration.failed",
            from_revision=result.from_revision,
            to_revision=result.to_revision,
            error=result.error,
            backup_path=result.backup_path,
        )

    return result


def _ensure_feature_flag_log_table(conn: sqlite3.Connection) -> None:
    """Idempotently create the ``feature_flag_log`` table if missing.

    Mirrors the ``migration_history`` self-heal pattern: alembic
    revision ``e5b2c4f1a9d8`` also creates the table, but the
    service-level helper guards against the case where the alembic
    chain has not been applied (e.g., tests that use ``IF NOT EXISTS``
    schema creation without running migrations).
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feature_flag_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flag_name TEXT NOT NULL,
            flag_value INTEGER NOT NULL,
            logged_at TEXT NOT NULL
        )
        """
    )


def record_feature_flags(*, settings: Settings, db_path: str) -> None:
    """Record current feature flag values to ``feature_flag_log``.

    Inserts one row per :data:`FEATURE_FLAG_NAMES` entry and emits a
    ``deployment.feature_flag`` structured log event for each flag.
    The write and the log happen via a short-lived synchronous
    connection so this helper can be called from both async lifespan
    paths and from synchronous test setup.

    Args:
        settings: Application settings carrying the resolved flag values.
        db_path: Filesystem path to the SQLite database that should
            receive the audit rows.
    """
    logged_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        _ensure_feature_flag_log_table(conn)
        for name in FEATURE_FLAG_NAMES:
            value = bool(getattr(settings, name))
            conn.execute(
                "INSERT INTO feature_flag_log (flag_name, flag_value, logged_at) VALUES (?, ?, ?)",
                (name, int(value), logged_at),
            )
            # BL-288: Phase 6 stoat_feature_flag_state gauge — populated
            # at startup so /metrics reflects flag state even before the
            # /api/v1/flags endpoint has been hit.
            stoat_feature_flag_state.labels(flag=name).set(int(value))
            logger.info(
                "deployment.feature_flag",
                flag_name=name,
                flag_value=value,
            )
        conn.commit()


__all__ = [
    "FEATURE_FLAG_NAMES",
    "record_feature_flags",
    "run_startup_migrations",
]
