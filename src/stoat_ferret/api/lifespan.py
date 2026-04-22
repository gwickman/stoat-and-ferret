"""Application lifespan helpers for deployment-safety services (BL-266).

This module holds the migration-safety portion of the FastAPI lifespan so
:mod:`stoat_ferret.api.app` can delegate to it during startup. The main
``lifespan`` context in ``app.py`` calls :func:`run_startup_migrations`
before opening the long-lived aiosqlite connection so that any pending
schema migration is applied — and backed up — before application code
begins to use the database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from stoat_ferret.api.services.migrations import MigrationService

if TYPE_CHECKING:
    from fastapi import FastAPI

    from stoat_ferret.api.settings import Settings
    from stoat_ferret.models.migrations import MigrationResult

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


__all__ = ["run_startup_migrations"]
