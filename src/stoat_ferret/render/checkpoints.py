"""Render checkpoint manager for crash recovery.

Writes per-segment checkpoints to SQLite after each segment completes,
scans for interrupted jobs on startup, resumes from the last completed
segment, and cleans up stale checkpoints for deleted or cancelled jobs.
"""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)


class RenderCheckpointManager:
    """Manages per-segment render checkpoints for crash recovery.

    Checkpoints are write-once: a row is inserted after each segment
    completes successfully.  On recovery, the manager scans for
    interrupted (``running``) jobs and determines which segment to
    resume from.

    Args:
        conn: Async SQLite database connection.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def write_checkpoint(self, job_id: str, segment_index: int) -> None:
        """Record a completed segment checkpoint.

        Args:
            job_id: The render job ID.
            segment_index: Zero-based index of the completed segment.

        Raises:
            ValueError: If segment_index is negative.
        """
        if segment_index < 0:
            raise ValueError(f"segment_index must be non-negative, got {segment_index}")
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT INTO render_checkpoints (job_id, segment_index, completed_at) VALUES (?, ?, ?)",
            (job_id, segment_index, now),
        )
        await self._conn.commit()
        logger.info(
            "render_checkpoint.write",
            job_id=job_id,
            segment_index=segment_index,
        )

    async def get_completed_segments(self, job_id: str) -> list[int]:
        """Return sorted list of completed segment indexes for a job.

        Args:
            job_id: The render job ID.

        Returns:
            Sorted list of segment indexes that have checkpoints.
        """
        cursor = await self._conn.execute(
            "SELECT segment_index FROM render_checkpoints WHERE job_id = ? ORDER BY segment_index",
            (job_id,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_next_segment(self, job_id: str, total_segments: int) -> int | None:
        """Return the next uncompleted segment index.

        Args:
            job_id: The render job ID.
            total_segments: Total number of segments in the render plan.

        Returns:
            The next segment index to render, or None if all are done.
        """
        completed = await self.get_completed_segments(job_id)
        completed_set = set(completed)
        for i in range(total_segments):
            if i not in completed_set:
                return i
        return None

    async def recover(self) -> list[tuple[str, int]]:
        """Scan for interrupted jobs and determine resume points.

        Finds all render jobs with status ``running`` (indicating they
        were in progress when the server stopped) and computes how many
        segments each has already completed.

        Returns:
            List of ``(job_id, next_segment_index)`` pairs. The
            ``next_segment_index`` is the count of completed checkpoints
            (i.e. the first uncompleted segment when segments are
            numbered 0..N-1).
        """
        cursor = await self._conn.execute(
            "SELECT rj.id, COUNT(rc.id) AS completed "
            "FROM render_jobs rj "
            "LEFT JOIN render_checkpoints rc ON rj.id = rc.job_id "
            "WHERE rj.status = 'running' "
            "GROUP BY rj.id "
            "ORDER BY rj.created_at",
        )
        rows = await cursor.fetchall()
        results: list[tuple[str, int]] = [(row[0], row[1]) for row in rows]
        logger.info(
            "render_checkpoint.recovery",
            interrupted_jobs=len(results),
        )
        for job_id, next_seg in results:
            logger.info(
                "render_checkpoint.resume",
                job_id=job_id,
                next_segment=next_seg,
            )
        return results

    async def cleanup_stale(self, job_ids: list[str]) -> int:
        """Delete checkpoints for the given job IDs.

        Used to remove orphaned checkpoints after jobs are deleted or
        cancelled.

        Args:
            job_ids: List of job IDs whose checkpoints should be removed.

        Returns:
            Number of checkpoint rows deleted.
        """
        if not job_ids:
            return 0
        placeholders = ",".join("?" for _ in job_ids)
        cursor = await self._conn.execute(
            f"DELETE FROM render_checkpoints WHERE job_id IN ({placeholders})",
            job_ids,
        )
        await self._conn.commit()
        deleted = cursor.rowcount
        logger.info(
            "render_checkpoint.cleanup",
            job_ids=job_ids,
            deleted_count=deleted,
        )
        return deleted
