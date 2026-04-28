"""Batch job repository implementations for batch render persistence.

Provides Protocol, SQLite, and InMemory implementations following the
established repository triple pattern used by other domain entities.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)

# Valid status transitions: from -> set of allowed targets.
# Terminal states (completed, failed, cancelled) have no outgoing transitions.
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
}


@dataclass
class BatchJobRecord:
    """A single job within a batch render operation.

    Attributes:
        id: Database row ID (None for unsaved records).
        batch_id: UUID grouping jobs into a batch.
        job_id: Unique UUID for this individual job.
        project_id: The project to render.
        output_path: Output file path for rendered video.
        quality: Render quality preset.
        status: Job status (queued, running, completed, failed, cancelled).
        progress: Render progress 0.0-1.0.
        error: Error message when status is failed.
        created_at: When this job was created.
        updated_at: When this job was last modified.
    """

    id: int | None
    batch_id: str
    job_id: str
    project_id: str
    output_path: str
    quality: str
    status: str
    progress: float
    error: str | None
    created_at: datetime
    updated_at: datetime


def _validate_status_transition(current: str, new: str) -> None:
    """Validate that a status transition is allowed.

    Args:
        current: Current status value.
        new: Proposed new status value.

    Raises:
        ValueError: If the transition is not allowed.
    """
    allowed = _VALID_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValueError(
            f"Invalid status transition: {current!r} -> {new!r}. "
            f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
        )


@runtime_checkable
class AsyncBatchRepository(Protocol):
    """Protocol for async batch job repository operations.

    Implementations must provide async methods for creating batch jobs,
    querying by batch ID, and updating job status and progress.
    """

    async def create_batch_job(
        self,
        *,
        batch_id: str,
        job_id: str,
        project_id: str,
        output_path: str,
        quality: str,
    ) -> BatchJobRecord:
        """Create a new batch job record.

        Args:
            batch_id: UUID grouping jobs into a batch.
            job_id: Unique UUID for this individual job.
            project_id: The project to render.
            output_path: Output file path for rendered video.
            quality: Render quality preset.

        Returns:
            The created batch job record.
        """
        ...

    async def get_by_batch_id(self, batch_id: str) -> list[BatchJobRecord]:
        """Get all jobs belonging to a batch.

        Args:
            batch_id: The batch UUID to query.

        Returns:
            List of batch job records for the given batch, ordered by id.
        """
        ...

    async def get_by_job_id(self, job_id: str) -> BatchJobRecord | None:
        """Get a single job by its unique job ID.

        Args:
            job_id: The job UUID to query.

        Returns:
            The batch job record if found, None otherwise.
        """
        ...

    async def update_status(
        self,
        job_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> None:
        """Update the status of a batch job.

        Validates state transitions per the allowed transitions:
        queued -> running | cancelled; running -> completed | failed | cancelled.

        Args:
            job_id: The job UUID to update.
            status: New status value.
            error: Error message (only valid when status is 'failed').

        Raises:
            ValueError: If the job is not found or transition is invalid.
        """
        ...

    async def update_progress(self, job_id: str, progress: float) -> None:
        """Update the progress of a batch job.

        Args:
            job_id: The job UUID to update.
            progress: New progress value (0.0-1.0).

        Raises:
            ValueError: If the job is not found.
        """
        ...


class AsyncSQLiteBatchRepository:
    """Async SQLite implementation of the batch repository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def create_batch_job(
        self,
        *,
        batch_id: str,
        job_id: str,
        project_id: str,
        output_path: str,
        quality: str,
    ) -> BatchJobRecord:
        """Create a new batch job record in SQLite."""
        now = datetime.now(timezone.utc)
        cursor = await self._conn.execute(
            """
            INSERT INTO batch_jobs
                (batch_id, job_id, project_id, output_path, quality,
                 status, progress, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'queued', 0.0, NULL, ?, ?)
            """,
            (batch_id, job_id, project_id, output_path, quality, now.isoformat(), now.isoformat()),
        )
        await self._conn.commit()

        return BatchJobRecord(
            id=cursor.lastrowid,
            batch_id=batch_id,
            job_id=job_id,
            project_id=project_id,
            output_path=output_path,
            quality=quality,
            status="queued",
            progress=0.0,
            error=None,
            created_at=now,
            updated_at=now,
        )

    async def get_by_batch_id(self, batch_id: str) -> list[BatchJobRecord]:
        """Get all jobs belonging to a batch."""
        cursor = await self._conn.execute(
            "SELECT * FROM batch_jobs WHERE batch_id = ? ORDER BY id",
            (batch_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    async def get_by_job_id(self, job_id: str) -> BatchJobRecord | None:
        """Get a single job by its unique job ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM batch_jobs WHERE job_id = ?",
            (job_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_record(row) if row else None

    async def update_status(
        self,
        job_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> None:
        """Update the status of a batch job with transition validation."""
        current = await self.get_by_job_id(job_id)
        if current is None:
            raise ValueError(f"Batch job {job_id} not found")

        _validate_status_transition(current.status, status)

        now = datetime.now(timezone.utc)
        await self._conn.execute(
            "UPDATE batch_jobs SET status = ?, error = ?, updated_at = ? WHERE job_id = ?",
            (status, error, now.isoformat(), job_id),
        )
        await self._conn.commit()

    async def update_progress(self, job_id: str, progress: float) -> None:
        """Update the progress of a batch job."""
        current = await self.get_by_job_id(job_id)
        if current is None:
            raise ValueError(f"Batch job {job_id} not found")

        now = datetime.now(timezone.utc)
        await self._conn.execute(
            "UPDATE batch_jobs SET progress = ?, updated_at = ? WHERE job_id = ?",
            (progress, now.isoformat(), job_id),
        )
        await self._conn.commit()

    def _row_to_record(self, row: aiosqlite.Row) -> BatchJobRecord:
        """Convert a database row to a BatchJobRecord.

        Args:
            row: Database row.

        Returns:
            BatchJobRecord instance.
        """
        return BatchJobRecord(
            id=row["id"],
            batch_id=row["batch_id"],
            job_id=row["job_id"],
            project_id=row["project_id"],
            output_path=row["output_path"],
            quality=row["quality"],
            status=row["status"],
            progress=row["progress"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class InMemoryBatchRepository:
    """In-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._jobs: dict[str, BatchJobRecord] = {}  # keyed by job_id
        self._next_id = 1

    async def create_batch_job(
        self,
        *,
        batch_id: str,
        job_id: str,
        project_id: str,
        output_path: str,
        quality: str,
    ) -> BatchJobRecord:
        """Create a new batch job record in memory."""
        now = datetime.now(timezone.utc)
        record = BatchJobRecord(
            id=self._next_id,
            batch_id=batch_id,
            job_id=job_id,
            project_id=project_id,
            output_path=output_path,
            quality=quality,
            status="queued",
            progress=0.0,
            error=None,
            created_at=now,
            updated_at=now,
        )
        self._next_id += 1
        self._jobs[job_id] = copy.deepcopy(record)
        return record

    async def get_by_batch_id(self, batch_id: str) -> list[BatchJobRecord]:
        """Get all jobs belonging to a batch."""
        jobs = [copy.deepcopy(j) for j in self._jobs.values() if j.batch_id == batch_id]
        return sorted(jobs, key=lambda j: j.id or 0)

    async def get_by_job_id(self, job_id: str) -> BatchJobRecord | None:
        """Get a single job by its unique job ID."""
        job = self._jobs.get(job_id)
        return copy.deepcopy(job) if job else None

    async def update_status(
        self,
        job_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> None:
        """Update the status of a batch job with transition validation."""
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Batch job {job_id} not found")

        _validate_status_transition(job.status, status)

        job.status = status
        job.error = error
        job.updated_at = datetime.now(timezone.utc)

    async def update_progress(self, job_id: str, progress: float) -> None:
        """Update the progress of a batch job."""
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Batch job {job_id} not found")

        job.progress = progress
        job.updated_at = datetime.now(timezone.utc)
