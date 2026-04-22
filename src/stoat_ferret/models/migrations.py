"""Pydantic models for migration safety audit records (BL-266)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

MigrationStatus = Literal["applied", "rolled_back"]


class MigrationHistoryRow(BaseModel):
    """A single migration_history audit row.

    Records a database migration attempt with its source/target Alembic
    revisions, pre-migration backup location, and current applied/rolled-back
    status. All fields except status are immutable after creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    from_revision: str | None
    to_revision: str
    applied_at: str
    backup_path: str | None
    rollback_revision: str | None
    status: MigrationStatus


class MigrationResult(BaseModel):
    """Outcome of a MigrationService.apply_pending() invocation."""

    model_config = ConfigDict(from_attributes=True)

    success: bool
    from_revision: str | None
    to_revision: str | None
    backup_path: str | None
    history_id: int | None = None
    error: str | None = None
    duration_ms: float


class RollbackResult(BaseModel):
    """Outcome of a MigrationService.rollback() invocation."""

    model_config = ConfigDict(from_attributes=True)

    success: bool
    from_revision: str | None
    to_revision: str | None
    history_id: int | None = None
    error: str | None = None
    duration_ms: float
