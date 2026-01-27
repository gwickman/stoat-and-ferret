"""Audit logging for tracking data modifications."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from stoat_ferret.db.models import AuditEntry


class AuditLogger:
    """Logger for recording audit trail of data changes.

    Provides methods to log data modifications (INSERT, UPDATE, DELETE)
    and retrieve audit history for specific entities.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize the audit logger with a database connection.

        Args:
            conn: SQLite database connection.
        """
        self._conn = conn

    def log_change(
        self,
        operation: str,
        entity_type: str,
        entity_id: str,
        changes: dict[str, object] | None = None,
        context: str | None = None,
    ) -> AuditEntry:
        """Log a data modification to the audit log.

        Args:
            operation: Type of operation (INSERT, UPDATE, DELETE).
            entity_type: Type of entity being modified (e.g., "video").
            entity_id: ID of the entity being modified.
            changes: Dictionary of field changes for UPDATE operations.
            context: Optional context (e.g., user ID, request ID).

        Returns:
            The created audit entry.
        """
        entry = AuditEntry(
            id=AuditEntry.new_id(),
            timestamp=datetime.now(timezone.utc),
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            changes_json=json.dumps(changes) if changes else None,
            context=context,
        )
        self._conn.execute(
            """
            INSERT INTO audit_log
                (id, timestamp, operation, entity_type, entity_id, changes_json, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.timestamp.isoformat(),
                entry.operation,
                entry.entity_type,
                entry.entity_id,
                entry.changes_json,
                entry.context,
            ),
        )
        self._conn.commit()
        return entry

    def get_history(self, entity_id: str, limit: int = 100) -> list[AuditEntry]:
        """Get audit history for an entity.

        Args:
            entity_id: ID of the entity to get history for.
            limit: Maximum number of entries to return.

        Returns:
            List of audit entries, most recent first.
        """
        cursor = self._conn.execute(
            """
            SELECT id, timestamp, operation, entity_type, entity_id, changes_json, context
            FROM audit_log
            WHERE entity_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (entity_id, limit),
        )
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def _row_to_entry(self, row: tuple[object, ...]) -> AuditEntry:
        """Convert a database row to an AuditEntry object."""
        return AuditEntry(
            id=str(row[0]),
            timestamp=datetime.fromisoformat(str(row[1])),
            operation=str(row[2]),
            entity_type=str(row[3]),
            entity_id=str(row[4]),
            changes_json=str(row[5]) if row[5] is not None else None,
            context=str(row[6]) if row[6] is not None else None,
        )
