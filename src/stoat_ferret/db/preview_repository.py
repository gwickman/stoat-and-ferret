"""Preview session repository implementations for preview persistence.

Provides Protocol, SQLite, and InMemory implementations following the
established repository triple pattern used by other domain entities.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

import aiosqlite
import structlog

from stoat_ferret.db.models import (
    PreviewQuality,
    PreviewSession,
    PreviewStatus,
    validate_preview_transition,
)

logger = structlog.get_logger(__name__)


@runtime_checkable
class AsyncPreviewRepository(Protocol):
    """Protocol for async preview session repository operations.

    Implementations must provide async methods for CRUD operations
    on preview session records.
    """

    async def add(self, session: PreviewSession) -> PreviewSession:
        """Add a new preview session record.

        Args:
            session: The preview session to add.

        Returns:
            The added preview session record.

        Raises:
            ValueError: If a session with the same ID already exists.
        """
        ...

    async def get(self, session_id: str) -> PreviewSession | None:
        """Get a preview session by ID.

        Args:
            session_id: The preview session UUID.

        Returns:
            The preview session if found, None otherwise.
        """
        ...

    async def list_by_project(self, project_id: str) -> list[PreviewSession]:
        """List all preview sessions for a project.

        Args:
            project_id: The project UUID.

        Returns:
            List of preview sessions for the project.
        """
        ...

    async def update(self, session: PreviewSession) -> None:
        """Update a preview session record.

        Validates state transitions when status changes.

        Args:
            session: The preview session with updated fields.

        Raises:
            ValueError: If the session is not found or transition is invalid.
        """
        ...

    async def delete(self, session_id: str) -> bool:
        """Delete a preview session record.

        Args:
            session_id: The preview session UUID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def get_expired(self, now: datetime | None = None) -> list[PreviewSession]:
        """Get all sessions where expires_at < now.

        Args:
            now: The current time. Defaults to UTC now.

        Returns:
            List of expired preview sessions.
        """
        ...

    async def count(self) -> int:
        """Count all preview session records.

        Returns:
            Total number of preview sessions.
        """
        ...


class SQLitePreviewRepository:
    """Async SQLite implementation of the preview session repository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, session: PreviewSession) -> PreviewSession:
        """Add a new preview session record to SQLite."""
        try:
            await self._conn.execute(
                """
                INSERT INTO preview_sessions
                    (id, project_id, status, manifest_path, segment_count,
                     quality_level, created_at, updated_at, expires_at,
                     error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.project_id,
                    session.status.value,
                    session.manifest_path,
                    session.segment_count,
                    session.quality_level.value,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.expires_at.isoformat(),
                    session.error_message,
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Preview session {session.id} already exists") from e
        return session

    async def get(self, session_id: str) -> PreviewSession | None:
        """Get a preview session by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM preview_sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_session(row) if row else None

    async def list_by_project(self, project_id: str) -> list[PreviewSession]:
        """List all preview sessions for a project."""
        cursor = await self._conn.execute(
            "SELECT * FROM preview_sessions WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_session(row) for row in rows]

    async def update(self, session: PreviewSession) -> None:
        """Update a preview session with transition validation."""
        current = await self.get(session.id)
        if current is None:
            raise ValueError(f"Preview session {session.id} not found")

        if current.status != session.status:
            validate_preview_transition(current.status.value, session.status.value)

        await self._conn.execute(
            """
            UPDATE preview_sessions
            SET status = ?, manifest_path = ?, segment_count = ?,
                updated_at = ?, expires_at = ?, error_message = ?
            WHERE id = ?
            """,
            (
                session.status.value,
                session.manifest_path,
                session.segment_count,
                session.updated_at.isoformat(),
                session.expires_at.isoformat(),
                session.error_message,
                session.id,
            ),
        )
        await self._conn.commit()

    async def delete(self, session_id: str) -> bool:
        """Delete a preview session record."""
        cursor = await self._conn.execute(
            "DELETE FROM preview_sessions WHERE id = ?",
            (session_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def get_expired(self, now: datetime | None = None) -> list[PreviewSession]:
        """Get all sessions where expires_at < now."""
        if now is None:
            now = datetime.now(timezone.utc)
        cursor = await self._conn.execute(
            "SELECT * FROM preview_sessions WHERE expires_at < ? ORDER BY expires_at",
            (now.isoformat(),),
        )
        rows = await cursor.fetchall()
        return [self._row_to_session(row) for row in rows]

    async def count(self) -> int:
        """Count all preview session records."""
        cursor = await self._conn.execute("SELECT COUNT(*) FROM preview_sessions")
        row = await cursor.fetchone()
        assert row is not None
        result: int = row[0]
        return result

    def _row_to_session(self, row: aiosqlite.Row) -> PreviewSession:
        """Convert a database row to a PreviewSession.

        Args:
            row: Database row.

        Returns:
            PreviewSession instance.
        """
        return PreviewSession(
            id=row["id"],
            project_id=row["project_id"],
            status=PreviewStatus(row["status"]),
            manifest_path=row["manifest_path"],
            segment_count=row["segment_count"],
            quality_level=PreviewQuality(row["quality_level"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            error_message=row["error_message"],
        )


class InMemoryPreviewRepository:
    """In-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._sessions: dict[str, PreviewSession] = {}

    async def add(self, session: PreviewSession) -> PreviewSession:
        """Add a new preview session record in memory."""
        if session.id in self._sessions:
            raise ValueError(f"Preview session {session.id} already exists")
        self._sessions[session.id] = copy.deepcopy(session)
        return copy.deepcopy(session)

    async def get(self, session_id: str) -> PreviewSession | None:
        """Get a preview session by ID."""
        session = self._sessions.get(session_id)
        return copy.deepcopy(session) if session else None

    async def list_by_project(self, project_id: str) -> list[PreviewSession]:
        """List all preview sessions for a project."""
        results = [copy.deepcopy(s) for s in self._sessions.values() if s.project_id == project_id]
        return sorted(results, key=lambda s: s.created_at)

    async def update(self, session: PreviewSession) -> None:
        """Update a preview session with transition validation."""
        current = self._sessions.get(session.id)
        if current is None:
            raise ValueError(f"Preview session {session.id} not found")

        if current.status != session.status:
            validate_preview_transition(current.status.value, session.status.value)

        self._sessions[session.id] = copy.deepcopy(session)

    async def delete(self, session_id: str) -> bool:
        """Delete a preview session record."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def get_expired(self, now: datetime | None = None) -> list[PreviewSession]:
        """Get all sessions where expires_at < now."""
        if now is None:
            now = datetime.now(timezone.utc)
        results = [copy.deepcopy(s) for s in self._sessions.values() if s.expires_at < now]
        return sorted(results, key=lambda s: s.expires_at)

    async def count(self) -> int:
        """Count all preview session records."""
        return len(self._sessions)
