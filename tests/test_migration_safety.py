"""Tests for MigrationService backup/rollback + audit logging (BL-266)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from stoat_ferret.api.services.migrations import (
    MigrationService,
    _parse_sqlite_version,
)
from stoat_ferret.models.migrations import MigrationResult, RollbackResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


@pytest.fixture
def migration_service(tmp_path: Path) -> MigrationService:
    """Build a MigrationService pointing at an isolated tmp database."""
    db_path = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"
    return MigrationService(
        backup_dir=backup_dir,
        db_path=db_path,
        alembic_config_path=ALEMBIC_INI,
    )


def _table_names(db_path: Path) -> set[str]:
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {r[0] for r in rows}


def test_parse_sqlite_version_handles_malformed_input() -> None:
    """Invalid version strings decay to a zero tuple rather than raising."""
    assert _parse_sqlite_version("3.40.1") == (3, 40, 1)
    assert _parse_sqlite_version("garbage") == (0, 0, 0)
    assert _parse_sqlite_version("") == (0, 0, 0)


def test_apply_pending_creates_backup_and_history(
    migration_service: MigrationService,
    tmp_path: Path,
) -> None:
    """Second upgrade after an initial upgrade backs up + records history."""
    first = migration_service.apply_pending_sync()
    assert isinstance(first, MigrationResult)
    assert first.success is True
    assert first.to_revision is not None

    # Fresh DB case: there was nothing to back up before the first upgrade.
    assert first.from_revision is None

    # Now force a "downgrade then re-upgrade" cycle so that the second upgrade
    # actually has something to back up and records a migration_history row.
    base_revision = "c3687b3b7a6a"  # initial schema revision
    rb = migration_service.rollback_sync(base_revision)
    assert isinstance(rb, RollbackResult)
    assert rb.success is True

    second = migration_service.apply_pending_sync()
    assert second.success is True
    assert second.from_revision == base_revision
    assert second.to_revision == first.to_revision
    assert second.backup_path is not None

    backup_file = Path(second.backup_path)
    assert backup_file.exists()
    assert backup_file.parent == tmp_path / "backups"
    assert backup_file.name.startswith("migration_")
    assert backup_file.suffix == ".db"

    # Backup is a readable SQLite database with at least one user table.
    assert "videos" in _table_names(backup_file)

    # migration_history has a row for the second upgrade.
    assert second.history_id is not None
    db_path = tmp_path / "test.db"
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT from_revision, to_revision, backup_path, "
            "rollback_revision, status FROM migration_history WHERE id = ?",
            (second.history_id,),
        ).fetchone()
    assert row is not None
    from_rev, to_rev, backup_col, rollback_rev, status = row
    assert from_rev == base_revision
    assert to_rev == second.to_revision
    assert backup_col == second.backup_path
    assert rollback_rev == base_revision
    assert status == "applied"


def test_apply_pending_is_noop_when_already_at_head(
    migration_service: MigrationService,
) -> None:
    """A second apply after full upgrade records no new history row."""
    first = migration_service.apply_pending_sync()
    assert first.success is True

    second = migration_service.apply_pending_sync()
    assert second.success is True
    assert second.history_id is None
    assert second.backup_path is None
    assert second.from_revision == second.to_revision


def test_rollback_restores_schema(
    migration_service: MigrationService,
    tmp_path: Path,
) -> None:
    """PRAGMA schema snapshot after roundtrip migration+rollback matches."""
    base_revision = "c3687b3b7a6a"
    head_revision = migration_service.apply_pending_sync().to_revision
    assert head_revision is not None

    # Roll back to the initial revision to capture the baseline schema.
    migration_service.rollback_sync(base_revision)
    baseline = migration_service.table_schema_snapshot()

    # Upgrade to head and verify schema actually changed vs. the baseline.
    migration_service.apply_pending_sync()
    post_upgrade = migration_service.table_schema_snapshot()
    assert post_upgrade != baseline

    # Roll back again — schema must match baseline exactly.
    rb = migration_service.rollback_sync(base_revision)
    assert rb.success is True
    restored = migration_service.table_schema_snapshot()
    assert restored == baseline


def test_rollback_marks_history_row_rolled_back(
    migration_service: MigrationService,
    tmp_path: Path,
) -> None:
    """Rolling back an applied migration flips its status column."""
    base_revision = "c3687b3b7a6a"
    migration_service.apply_pending_sync()
    migration_service.rollback_sync(base_revision)
    applied_again = migration_service.apply_pending_sync()
    assert applied_again.history_id is not None

    rb = migration_service.rollback_sync(base_revision)
    assert rb.success is True
    assert rb.history_id == applied_again.history_id

    db_path = tmp_path / "test.db"
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT status FROM migration_history WHERE id = ?",
            (applied_again.history_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "rolled_back"


def test_rollback_is_noop_when_already_at_target(
    migration_service: MigrationService,
) -> None:
    """Rollback to the current revision returns success without invoking alembic."""
    migration_service.apply_pending_sync()
    head = migration_service.apply_pending_sync().to_revision
    assert head is not None

    rb = migration_service.rollback_sync(head)
    assert rb.success is True
    assert rb.from_revision == head
    assert rb.to_revision == head


def test_apply_pending_returns_failure_when_backup_fails(
    migration_service: MigrationService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backup errors abort the upgrade — no migration_history row is written."""
    migration_service.apply_pending_sync()
    base_revision = "c3687b3b7a6a"
    migration_service.rollback_sync(base_revision)

    def explode(self: MigrationService) -> str | None:
        raise OSError("simulated disk failure")

    monkeypatch.setattr(MigrationService, "_create_backup", explode, raising=True)
    result = migration_service.apply_pending_sync()
    assert result.success is False
    assert result.error is not None
    assert "backup_failed" in result.error


@pytest.mark.asyncio
async def test_apply_pending_async_runs_in_thread(
    migration_service: MigrationService,
) -> None:
    """The async wrapper invokes the sync core and returns its result."""
    result = await migration_service.apply_pending()
    assert result.success is True
