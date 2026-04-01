"""Render job repository implementations.

Provides Protocol, SQLite, and InMemory implementations following the
established repository triple pattern used by other domain entities.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

import aiosqlite
import structlog

from stoat_ferret.render.models import (
    OutputFormat,
    QualityPreset,
    RenderJob,
    RenderStatus,
    validate_render_transition,
)

logger = structlog.get_logger(__name__)


@runtime_checkable
class AsyncRenderRepository(Protocol):
    """Protocol for async render job repository operations.

    Implementations must provide async methods for creating render jobs,
    querying by id/project/status, and updating job status and progress.
    """

    async def create(self, job: RenderJob) -> RenderJob:
        """Persist a new render job.

        Args:
            job: The render job to persist.

        Returns:
            The persisted render job.
        """
        ...

    async def get(self, job_id: str) -> RenderJob | None:
        """Get a render job by its unique ID.

        Args:
            job_id: The job UUID to query.

        Returns:
            The render job if found, None otherwise.
        """
        ...

    async def get_by_project(self, project_id: str) -> list[RenderJob]:
        """Get all render jobs for a project.

        Args:
            project_id: The project UUID to query.

        Returns:
            List of render jobs ordered by created_at.
        """
        ...

    async def list_by_status(self, status: RenderStatus) -> list[RenderJob]:
        """List all render jobs with a given status.

        Args:
            status: The status to filter by.

        Returns:
            List of render jobs ordered by created_at.
        """
        ...

    async def update_status(
        self,
        job_id: str,
        status: RenderStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        """Update the status of a render job with transition validation.

        Args:
            job_id: The job UUID to update.
            status: New status value.
            error_message: Error message (only valid when status is failed).

        Raises:
            ValueError: If the job is not found or transition is invalid.
        """
        ...

    async def update_progress(self, job_id: str, progress: float) -> None:
        """Update the progress of a render job.

        Args:
            job_id: The job UUID to update.
            progress: New progress value (0.0-1.0).

        Raises:
            ValueError: If the job is not found or progress is out of bounds.
        """
        ...

    async def list_jobs(
        self,
        *,
        status: RenderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RenderJob], int]:
        """List render jobs with pagination and optional status filtering.

        Args:
            status: Optional status filter.
            limit: Maximum number of jobs to return.
            offset: Number of jobs to skip.

        Returns:
            Tuple of (jobs, total_count).
        """
        ...

    async def delete(self, job_id: str) -> bool:
        """Delete a render job by ID.

        Args:
            job_id: The job UUID to delete.

        Returns:
            True if the job was deleted, False if not found.
        """
        ...


class AsyncSQLiteRenderRepository:
    """Async SQLite implementation of the render repository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def create(self, job: RenderJob) -> RenderJob:
        """Persist a new render job to SQLite."""
        await self._conn.execute(
            """
            INSERT INTO render_jobs
                (id, project_id, status, output_path, output_format,
                 quality_preset, render_plan, progress, error_message,
                 retry_count, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.project_id,
                job.status.value,
                job.output_path,
                job.output_format.value,
                job.quality_preset.value,
                job.render_plan,
                job.progress,
                job.error_message,
                job.retry_count,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
            ),
        )
        await self._conn.commit()
        return job

    async def get(self, job_id: str) -> RenderJob | None:
        """Get a render job by its unique ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM render_jobs WHERE id = ?",
            (job_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_job(row) if row else None

    async def get_by_project(self, project_id: str) -> list[RenderJob]:
        """Get all render jobs for a project."""
        cursor = await self._conn.execute(
            "SELECT * FROM render_jobs WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_job(row) for row in rows]

    async def list_by_status(self, status: RenderStatus) -> list[RenderJob]:
        """List all render jobs with a given status."""
        cursor = await self._conn.execute(
            "SELECT * FROM render_jobs WHERE status = ? ORDER BY created_at",
            (status.value,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_job(row) for row in rows]

    async def list_jobs(
        self,
        *,
        status: RenderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RenderJob], int]:
        """List render jobs with pagination and optional status filtering."""
        if status is not None:
            count_cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM render_jobs WHERE status = ?",
                (status.value,),
            )
            row = await count_cursor.fetchone()
            total = row[0] if row else 0

            cursor = await self._conn.execute(
                "SELECT * FROM render_jobs WHERE status = ?"
                " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status.value, limit, offset),
            )
        else:
            count_cursor = await self._conn.execute("SELECT COUNT(*) FROM render_jobs")
            row = await count_cursor.fetchone()
            total = row[0] if row else 0

            cursor = await self._conn.execute(
                "SELECT * FROM render_jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )

        rows = await cursor.fetchall()
        return [self._row_to_job(row) for row in rows], total

    async def update_status(
        self,
        job_id: str,
        status: RenderStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        """Update the status of a render job with transition validation."""
        current = await self.get(job_id)
        if current is None:
            raise ValueError(f"Render job {job_id} not found")

        validate_render_transition(current.status.value, status.value)

        now = datetime.now(timezone.utc)
        completed_at = (
            now
            if status
            in (
                RenderStatus.COMPLETED,
                RenderStatus.FAILED,
                RenderStatus.CANCELLED,
            )
            else None
        )

        # Retry resets progress and error_message
        progress = current.progress
        if status == RenderStatus.QUEUED:
            progress = 0.0
            error_message = None
            completed_at = None

        # Completed sets progress to 1.0
        if status == RenderStatus.COMPLETED:
            progress = 1.0

        retry_count = current.retry_count
        if status == RenderStatus.QUEUED and current.status == RenderStatus.FAILED:
            retry_count += 1

        await self._conn.execute(
            """
            UPDATE render_jobs
            SET status = ?, error_message = ?, progress = ?,
                retry_count = ?, updated_at = ?, completed_at = ?
            WHERE id = ?
            """,
            (
                status.value,
                error_message,
                progress,
                retry_count,
                now.isoformat(),
                completed_at.isoformat() if completed_at else None,
                job_id,
            ),
        )
        await self._conn.commit()

    async def update_progress(self, job_id: str, progress: float) -> None:
        """Update the progress of a render job."""
        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {progress}")

        current = await self.get(job_id)
        if current is None:
            raise ValueError(f"Render job {job_id} not found")

        now = datetime.now(timezone.utc)
        await self._conn.execute(
            "UPDATE render_jobs SET progress = ?, updated_at = ? WHERE id = ?",
            (progress, now.isoformat(), job_id),
        )
        await self._conn.commit()

    async def delete(self, job_id: str) -> bool:
        """Delete a render job by ID."""
        cursor = await self._conn.execute(
            "DELETE FROM render_jobs WHERE id = ?",
            (job_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_job(self, row: aiosqlite.Row) -> RenderJob:
        """Convert a database row to a RenderJob.

        Args:
            row: Database row.

        Returns:
            RenderJob instance.
        """
        return RenderJob(
            id=row["id"],
            project_id=row["project_id"],
            status=RenderStatus(row["status"]),
            output_path=row["output_path"],
            output_format=OutputFormat(row["output_format"]),
            quality_preset=QualityPreset(row["quality_preset"]),
            render_plan=row["render_plan"],
            progress=row["progress"],
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
            ),
        )


class InMemoryRenderRepository:
    """In-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._jobs: dict[str, RenderJob] = {}

    async def create(self, job: RenderJob) -> RenderJob:
        """Persist a new render job in memory."""
        self._jobs[job.id] = copy.deepcopy(job)
        return copy.deepcopy(job)

    async def get(self, job_id: str) -> RenderJob | None:
        """Get a render job by its unique ID."""
        job = self._jobs.get(job_id)
        return copy.deepcopy(job) if job else None

    async def get_by_project(self, project_id: str) -> list[RenderJob]:
        """Get all render jobs for a project."""
        jobs = [copy.deepcopy(j) for j in self._jobs.values() if j.project_id == project_id]
        return sorted(jobs, key=lambda j: j.created_at)

    async def list_by_status(self, status: RenderStatus) -> list[RenderJob]:
        """List all render jobs with a given status."""
        jobs = [copy.deepcopy(j) for j in self._jobs.values() if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at)

    async def list_jobs(
        self,
        *,
        status: RenderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RenderJob], int]:
        """List render jobs with pagination and optional status filtering."""
        all_jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        if status is not None:
            all_jobs = [j for j in all_jobs if j.status == status]
        total = len(all_jobs)
        page = [copy.deepcopy(j) for j in all_jobs[offset : offset + limit]]
        return page, total

    async def update_status(
        self,
        job_id: str,
        status: RenderStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        """Update the status of a render job with transition validation."""
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Render job {job_id} not found")

        validate_render_transition(job.status.value, status.value)

        now = datetime.now(timezone.utc)

        # Retry resets progress, error, and completed_at
        if status == RenderStatus.QUEUED:
            job.retry_count += 1
            job.progress = 0.0
            job.error_message = None
            job.completed_at = None
        elif status == RenderStatus.COMPLETED:
            job.progress = 1.0
            job.completed_at = now
        elif status == RenderStatus.FAILED:
            job.error_message = error_message
            job.completed_at = now
        elif status == RenderStatus.CANCELLED:
            job.error_message = None
            job.completed_at = now
        else:
            job.error_message = error_message

        job.status = status
        job.updated_at = now

    async def update_progress(self, job_id: str, progress: float) -> None:
        """Update the progress of a render job."""
        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {progress}")

        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Render job {job_id} not found")

        job.progress = progress
        job.updated_at = datetime.now(timezone.utc)

    async def delete(self, job_id: str) -> bool:
        """Delete a render job by ID."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False
