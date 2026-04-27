"""Migration safety service wrapping Alembic with backup + audit (BL-266).

Provides a service layer around `alembic upgrade` / `alembic downgrade` that:

- Creates a timestamped SQLite backup prior to each upgrade attempt.
- Records an audit row in the `migration_history` table on success.
- Updates that audit row's status to `rolled_back` on successful downgrade.
- Emits structured `deployment.migration` / `deployment.migration_rollback`
  events with duration, revisions, and backup location.

Failures during backup creation or alembic invocation abort the operation
and return a failed result — no partial history row is written.
"""

from __future__ import annotations

import asyncio
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from stoat_ferret.api.middleware.metrics import stoat_migration_duration_seconds
from stoat_ferret.models.migrations import MigrationResult, RollbackResult

logger = structlog.get_logger(__name__)


# Use VACUUM INTO when available (added in SQLite 3.27); the feature spec
# (FR-002 AC) cites >=3.37 as a conservative floor, so match that threshold.
_VACUUM_INTO_MIN_VERSION = (3, 37, 0)


def _parse_sqlite_version(version: str) -> tuple[int, int, int]:
    """Parse an ``sqlite3.sqlite_version`` string into a comparable tuple."""
    parts = version.split(".")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (IndexError, ValueError):
        return (0, 0, 0)


class MigrationService:
    """Wraps Alembic migrations with pre-upgrade backup and audit logging.

    Constructed in the application lifespan with the database path and
    backup directory from Settings, then stored on ``app.state`` for
    later access.
    """

    def __init__(
        self,
        *,
        backup_dir: str | Path,
        db_path: str | Path,
        alembic_config_path: str | Path | None = None,
    ) -> None:
        """Create a MigrationService.

        Args:
            backup_dir: Directory where timestamped SQLite backups are stored.
                Created if missing.
            db_path: Path to the SQLite database to back up and migrate.
            alembic_config_path: Optional override for the alembic.ini location.
                Defaults to the project-root alembic.ini.
        """
        self._backup_dir = Path(backup_dir)
        self._db_path = Path(db_path)
        if alembic_config_path is None:
            self._alembic_config_path = Path("alembic.ini").resolve()
        else:
            self._alembic_config_path = Path(alembic_config_path)

    def _probe_sqlite_version(self) -> tuple[int, int, int]:
        """Return the runtime SQLite library version as a tuple."""
        version = _parse_sqlite_version(sqlite3.sqlite_version)
        logger.debug(
            "deployment.migration.sqlite_probe",
            sqlite_version=sqlite3.sqlite_version,
        )
        return version

    def _build_alembic_config(self) -> Config:
        """Build an Alembic ``Config`` pointing at this service's database."""
        config = Config(str(self._alembic_config_path))
        config.set_main_option(
            "sqlalchemy.url",
            f"sqlite:///{self._db_path.as_posix()}",
        )
        return config

    def _current_revision(self) -> str | None:
        """Return the current alembic revision in the database, or None."""
        if not self._db_path.exists():
            return None
        with sqlite3.connect(str(self._db_path)) as conn:
            try:
                cursor = conn.execute("SELECT version_num FROM alembic_version LIMIT 1")
                row = cursor.fetchone()
            except sqlite3.OperationalError:
                return None
        return row[0] if row else None

    def _head_revision(self, config: Config) -> str | None:
        """Return the head revision from the Alembic script directory."""
        script = ScriptDirectory.from_config(config)
        head = script.get_current_head()
        return head

    def _create_backup(self) -> str | None:
        """Create a timestamped backup of the SQLite database.

        Uses ``VACUUM INTO`` when SQLite >= 3.27 is available, otherwise
        falls back to ``shutil.copy``. Returns ``None`` if the database
        file does not exist yet (fresh install — nothing to back up).

        Returns:
            Absolute path to the created backup file, or ``None`` if the
            database did not exist.

        Raises:
            OSError: If backup creation fails for I/O reasons.
            sqlite3.Error: If ``VACUUM INTO`` fails.
        """
        if not self._db_path.exists():
            return None

        self._backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H_%M_%S")
        backup_name = f"migration_{timestamp}.db"
        backup_path = self._backup_dir / backup_name

        version = self._probe_sqlite_version()
        if version >= _VACUUM_INTO_MIN_VERSION:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    "VACUUM INTO ?",
                    (str(backup_path),),
                )
        else:
            shutil.copy(self._db_path, backup_path)

        return str(backup_path)

    def _ensure_history_table(self, conn: sqlite3.Connection) -> None:
        """Idempotently recreate ``migration_history`` if it is missing.

        The table is also managed by Alembic (revision d7a1b2c3e4f5) but
        a downgrade past that revision would drop it. Since this table is
        infrastructure for the safety wrapper itself, we self-heal here
        so audit recording never silently fails.
        """
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_revision TEXT,
                to_revision TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                backup_path TEXT,
                rollback_revision TEXT,
                status TEXT NOT NULL DEFAULT 'applied'
                    CHECK (status IN ('applied', 'rolled_back'))
            )
            """
        )

    def _insert_history_row(
        self,
        *,
        from_revision: str | None,
        to_revision: str,
        applied_at: str,
        backup_path: str | None,
    ) -> int:
        """Insert a ``migration_history`` row and return its id."""
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_history_table(conn)
            cursor = conn.execute(
                """
                INSERT INTO migration_history (
                    from_revision,
                    to_revision,
                    applied_at,
                    backup_path,
                    rollback_revision,
                    status
                ) VALUES (?, ?, ?, ?, ?, 'applied')
                """,
                (
                    from_revision,
                    to_revision,
                    applied_at,
                    backup_path,
                    from_revision,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid or 0)

    def _mark_history_rolled_back(self, history_id: int) -> None:
        """Update a history row's status to ``rolled_back``.

        Only rows currently in ``applied`` state are updated — the
        WHERE clause enforces the ``applied`` → ``rolled_back``
        one-way transition invariant.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_history_table(conn)
            conn.execute(
                "UPDATE migration_history SET status = 'rolled_back' "
                "WHERE id = ? AND status = 'applied'",
                (history_id,),
            )
            conn.commit()

    def _find_history_id_for_revision(self, to_revision: str) -> int | None:
        """Find the most recent applied history row matching a to_revision."""
        with sqlite3.connect(str(self._db_path)) as conn:
            self._ensure_history_table(conn)
            cursor = conn.execute(
                "SELECT id FROM migration_history "
                "WHERE to_revision = ? AND status = 'applied' "
                "ORDER BY id DESC LIMIT 1",
                (to_revision,),
            )
            row = cursor.fetchone()
        return int(row[0]) if row else None

    def apply_pending_sync(self) -> MigrationResult:
        """Synchronous core of :meth:`apply_pending`; safe to call directly."""
        start = time.perf_counter()
        config = self._build_alembic_config()
        from_revision = self._current_revision()
        head_revision = self._head_revision(config)

        if head_revision is None:
            duration_ms = (time.perf_counter() - start) * 1000.0
            stoat_migration_duration_seconds.labels(result="failure").observe(duration_ms / 1000.0)
            logger.warning(
                "deployment.migration.no_head",
                duration_ms=duration_ms,
            )
            return MigrationResult(
                success=False,
                from_revision=from_revision,
                to_revision=None,
                backup_path=None,
                duration_ms=duration_ms,
                error="No alembic head revision found",
            )

        if from_revision == head_revision:
            duration_ms = (time.perf_counter() - start) * 1000.0
            stoat_migration_duration_seconds.labels(result="success").observe(duration_ms / 1000.0)
            logger.info(
                "deployment.migration.already_current",
                from_revision=from_revision,
                to_revision=head_revision,
                duration_ms=duration_ms,
            )
            return MigrationResult(
                success=True,
                from_revision=from_revision,
                to_revision=head_revision,
                backup_path=None,
                duration_ms=duration_ms,
            )

        backup_path: str | None
        try:
            backup_path = self._create_backup()
        except (OSError, sqlite3.Error) as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            stoat_migration_duration_seconds.labels(result="failure").observe(duration_ms / 1000.0)
            logger.warning(
                "deployment.migration_rollback",
                reason="backup_failed",
                error=str(exc),
                from_revision=from_revision,
                to_revision=head_revision,
                duration_ms=duration_ms,
            )
            return MigrationResult(
                success=False,
                from_revision=from_revision,
                to_revision=head_revision,
                backup_path=None,
                duration_ms=duration_ms,
                error=f"backup_failed: {exc}",
            )

        try:
            command.upgrade(config, "head")
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            stoat_migration_duration_seconds.labels(result="failure").observe(duration_ms / 1000.0)
            logger.warning(
                "deployment.migration_rollback",
                reason="upgrade_failed",
                error=str(exc),
                from_revision=from_revision,
                to_revision=head_revision,
                backup_path=backup_path,
                duration_ms=duration_ms,
            )
            return MigrationResult(
                success=False,
                from_revision=from_revision,
                to_revision=head_revision,
                backup_path=backup_path,
                duration_ms=duration_ms,
                error=f"upgrade_failed: {exc}",
            )

        applied_at = datetime.now(timezone.utc).isoformat()
        history_id = self._insert_history_row(
            from_revision=from_revision,
            to_revision=head_revision,
            applied_at=applied_at,
            backup_path=backup_path,
        )

        duration_ms = (time.perf_counter() - start) * 1000.0
        stoat_migration_duration_seconds.labels(result="success").observe(duration_ms / 1000.0)
        logger.info(
            "deployment.migration",
            from_revision=from_revision,
            to_revision=head_revision,
            backup_path=backup_path,
            duration_ms=duration_ms,
        )
        return MigrationResult(
            success=True,
            from_revision=from_revision,
            to_revision=head_revision,
            backup_path=backup_path,
            history_id=history_id,
            duration_ms=duration_ms,
        )

    async def apply_pending(self) -> MigrationResult:
        """Apply all pending Alembic migrations with backup + audit.

        Runs the blocking Alembic invocation via :func:`asyncio.to_thread`
        so it is safe to call from async lifespan code.
        """
        return await asyncio.to_thread(self.apply_pending_sync)

    def rollback_sync(self, to_revision: str) -> RollbackResult:
        """Synchronous core of :meth:`rollback`; safe to call directly."""
        start = time.perf_counter()
        config = self._build_alembic_config()
        from_revision = self._current_revision()

        if from_revision == to_revision:
            duration_ms = (time.perf_counter() - start) * 1000.0
            return RollbackResult(
                success=True,
                from_revision=from_revision,
                to_revision=to_revision,
                duration_ms=duration_ms,
            )

        history_id = (
            self._find_history_id_for_revision(from_revision) if from_revision is not None else None
        )

        try:
            command.downgrade(config, to_revision)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            logger.warning(
                "deployment.migration_rollback",
                reason="downgrade_failed",
                error=str(exc),
                from_revision=from_revision,
                to_revision=to_revision,
                duration_ms=duration_ms,
            )
            return RollbackResult(
                success=False,
                from_revision=from_revision,
                to_revision=to_revision,
                history_id=history_id,
                duration_ms=duration_ms,
                error=f"downgrade_failed: {exc}",
            )

        if history_id is not None:
            self._mark_history_rolled_back(history_id)

        duration_ms = (time.perf_counter() - start) * 1000.0
        logger.info(
            "deployment.migration_rollback",
            reason="downgrade_success",
            from_revision=from_revision,
            to_revision=to_revision,
            history_id=history_id,
            duration_ms=duration_ms,
        )
        return RollbackResult(
            success=True,
            from_revision=from_revision,
            to_revision=to_revision,
            history_id=history_id,
            duration_ms=duration_ms,
        )

    async def rollback(self, to_revision: str) -> RollbackResult:
        """Roll the database back to ``to_revision`` via Alembic downgrade."""
        return await asyncio.to_thread(self.rollback_sync, to_revision)

    def table_schema_snapshot(self) -> dict[str, list[tuple[int, str, str]]]:
        """Return a PRAGMA-based snapshot of all user tables in the database.

        Each entry maps table name → list of ``(cid, name, type)`` tuples
        ordered by column id, enabling schema diff assertions in tests.
        """
        snapshot: dict[str, list[tuple[int, str, str]]] = {}
        with sqlite3.connect(str(self._db_path)) as conn:
            table_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
            for (table_name,) in table_rows:
                cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                snapshot[table_name] = [(int(c[0]), str(c[1]), str(c[2])) for c in cols]
        return snapshot


__all__ = [
    "MigrationResult",
    "MigrationService",
    "RollbackResult",
]
