"""Tests for audit logging functionality."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import pytest

from stoat_ferret.db.audit import AuditLogger
from stoat_ferret.db.models import AuditEntry, Video
from stoat_ferret.db.repository import SQLiteVideoRepository
from stoat_ferret.db.schema import create_tables


def make_test_video(**kwargs: object) -> Video:
    """Create a test video with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Video.new_id(),
        "path": f"/videos/{Video.new_id()}.mp4",
        "filename": "test.mp4",
        "duration_frames": 1000,
        "frame_rate_numerator": 24,
        "frame_rate_denominator": 1,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "file_size": 1000000,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Video(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def conn() -> sqlite3.Connection:
    """Provide an in-memory SQLite connection with schema."""
    connection = sqlite3.connect(":memory:")
    create_tables(connection)
    return connection


@pytest.fixture
def audit_logger(conn: sqlite3.Connection) -> AuditLogger:
    """Provide an AuditLogger instance."""
    return AuditLogger(conn)


@pytest.fixture
def repo_with_audit(conn: sqlite3.Connection, audit_logger: AuditLogger) -> SQLiteVideoRepository:
    """Provide a SQLiteVideoRepository with audit logging enabled."""
    return SQLiteVideoRepository(conn, audit_logger=audit_logger)


class TestAuditLogger:
    """Tests for the AuditLogger class."""

    def test_log_change_creates_entry(self, audit_logger: AuditLogger) -> None:
        """log_change creates an audit entry."""
        entry = audit_logger.log_change(
            operation="INSERT",
            entity_type="video",
            entity_id="test-id",
        )

        assert entry.operation == "INSERT"
        assert entry.entity_type == "video"
        assert entry.entity_id == "test-id"
        assert entry.changes_json is None
        assert entry.context is None

    def test_log_change_with_changes(self, audit_logger: AuditLogger) -> None:
        """log_change includes changes when provided."""
        changes = {"filename": {"old": "old.mp4", "new": "new.mp4"}}
        entry = audit_logger.log_change(
            operation="UPDATE",
            entity_type="video",
            entity_id="test-id",
            changes=changes,
        )

        assert entry.changes_json is not None
        parsed = json.loads(entry.changes_json)
        assert parsed == changes

    def test_log_change_with_context(self, audit_logger: AuditLogger) -> None:
        """log_change includes context when provided."""
        entry = audit_logger.log_change(
            operation="DELETE",
            entity_type="video",
            entity_id="test-id",
            context="user:123",
        )

        assert entry.context == "user:123"

    def test_get_history_returns_entries(self, audit_logger: AuditLogger) -> None:
        """get_history returns audit entries for an entity."""
        entity_id = "test-id"
        audit_logger.log_change("INSERT", "video", entity_id)
        audit_logger.log_change("UPDATE", "video", entity_id, {"filename": {}})

        history = audit_logger.get_history(entity_id)

        assert len(history) == 2
        # Most recent first
        assert history[0].operation == "UPDATE"
        assert history[1].operation == "INSERT"

    def test_get_history_respects_limit(self, audit_logger: AuditLogger) -> None:
        """get_history respects the limit parameter."""
        entity_id = "test-id"
        for _ in range(5):
            audit_logger.log_change("UPDATE", "video", entity_id)

        history = audit_logger.get_history(entity_id, limit=2)

        assert len(history) == 2

    def test_get_history_filters_by_entity_id(self, audit_logger: AuditLogger) -> None:
        """get_history only returns entries for the specified entity."""
        audit_logger.log_change("INSERT", "video", "entity-1")
        audit_logger.log_change("INSERT", "video", "entity-2")

        history = audit_logger.get_history("entity-1")

        assert len(history) == 1
        assert history[0].entity_id == "entity-1"


class TestAuditEntry:
    """Tests for the AuditEntry model."""

    def test_new_id_generates_unique_ids(self) -> None:
        """new_id generates unique UUIDs."""
        id1 = AuditEntry.new_id()
        id2 = AuditEntry.new_id()

        assert id1 != id2
        assert len(id1) == 36  # UUID format


class TestRepositoryAuditIntegration:
    """Tests for audit logging integration with SQLiteVideoRepository."""

    def test_add_logs_insert(
        self,
        repo_with_audit: SQLiteVideoRepository,
        audit_logger: AuditLogger,
    ) -> None:
        """Adding a video logs an INSERT operation."""
        video = make_test_video()
        repo_with_audit.add(video)

        history = audit_logger.get_history(video.id)
        assert len(history) == 1
        assert history[0].operation == "INSERT"
        assert history[0].entity_type == "video"
        assert history[0].entity_id == video.id

    def test_update_logs_update_with_changes(
        self,
        repo_with_audit: SQLiteVideoRepository,
        audit_logger: AuditLogger,
    ) -> None:
        """Updating a video logs an UPDATE operation with changes."""
        video = make_test_video(filename="original.mp4")
        repo_with_audit.add(video)

        updated = replace(
            video,
            filename="updated.mp4",
            updated_at=datetime.now(timezone.utc),
        )
        repo_with_audit.update(updated)

        history = audit_logger.get_history(video.id)
        assert len(history) == 2
        assert history[0].operation == "UPDATE"
        assert history[0].changes_json is not None
        changes = json.loads(history[0].changes_json)
        assert "filename" in changes
        assert changes["filename"]["old"] == "original.mp4"
        assert changes["filename"]["new"] == "updated.mp4"

    def test_delete_logs_delete(
        self,
        repo_with_audit: SQLiteVideoRepository,
        audit_logger: AuditLogger,
    ) -> None:
        """Deleting a video logs a DELETE operation."""
        video = make_test_video()
        repo_with_audit.add(video)
        repo_with_audit.delete(video.id)

        history = audit_logger.get_history(video.id)
        assert len(history) == 2
        assert history[0].operation == "DELETE"
        assert history[0].entity_type == "video"
        assert history[0].entity_id == video.id

    def test_delete_nonexistent_does_not_log(
        self,
        repo_with_audit: SQLiteVideoRepository,
        audit_logger: AuditLogger,
    ) -> None:
        """Deleting a nonexistent video does not create an audit entry."""
        repo_with_audit.delete("nonexistent")

        # There should be no entries at all
        history = audit_logger.get_history("nonexistent")
        assert len(history) == 0

    def test_repository_works_without_audit_logger(self, conn: sqlite3.Connection) -> None:
        """Repository works correctly without audit logger."""
        repo = SQLiteVideoRepository(conn)  # No audit logger
        video = make_test_video()

        repo.add(video)
        retrieved = repo.get(video.id)

        assert retrieved is not None
        assert retrieved.id == video.id

    def test_update_with_multiple_changes(
        self,
        repo_with_audit: SQLiteVideoRepository,
        audit_logger: AuditLogger,
    ) -> None:
        """Multiple field changes are captured in a single audit entry."""
        video = make_test_video(filename="original.mp4", width=1920)
        repo_with_audit.add(video)

        updated = replace(
            video,
            filename="updated.mp4",
            width=3840,
            updated_at=datetime.now(timezone.utc),
        )
        repo_with_audit.update(updated)

        history = audit_logger.get_history(video.id)
        changes = json.loads(history[0].changes_json)  # type: ignore[arg-type]
        assert "filename" in changes
        assert "width" in changes
        assert changes["width"]["old"] == 1920
        assert changes["width"]["new"] == 3840


class TestAsyncRepositoryAuditWiring:
    """Tests for AuditLogger wiring with AsyncSQLiteVideoRepository."""

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> Path:
        """Provide a temporary database file path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def sync_conn(self, db_path: Path) -> sqlite3.Connection:
        """Provide a sync SQLite connection with schema."""
        connection = sqlite3.connect(str(db_path))
        create_tables(connection)
        return connection

    @pytest.fixture
    async def async_conn(
        self, db_path: Path, sync_conn: sqlite3.Connection
    ) -> aiosqlite.Connection:
        """Provide an async SQLite connection to the same database."""
        connection = await aiosqlite.connect(str(db_path))
        connection.row_factory = aiosqlite.Row
        yield connection  # type: ignore[misc]
        await connection.close()

    async def test_async_repo_add_produces_audit_entry(
        self, async_conn: aiosqlite.Connection, sync_conn: sqlite3.Connection
    ) -> None:
        """Adding a video via AsyncSQLiteVideoRepository produces an audit entry."""
        from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository

        audit = AuditLogger(conn=sync_conn)
        repo = AsyncSQLiteVideoRepository(async_conn, audit_logger=audit)

        video = make_test_video()
        await repo.add(video)

        history = audit.get_history(video.id)
        assert len(history) == 1
        assert history[0].operation == "INSERT"
        assert history[0].entity_type == "video"
        assert history[0].entity_id == video.id

    async def test_sync_conn_does_not_block_async_operations(
        self, async_conn: aiosqlite.Connection, sync_conn: sqlite3.Connection
    ) -> None:
        """Audit INSERT on sync connection does not block async operations."""
        from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository

        # Enable WAL mode so sync and async connections can operate concurrently
        sync_conn.execute("PRAGMA journal_mode=WAL")

        audit = AuditLogger(conn=sync_conn)
        repo = AsyncSQLiteVideoRepository(async_conn, audit_logger=audit)

        # Add multiple videos concurrently to verify no deadlock
        videos = [make_test_video() for _ in range(5)]

        async def add_video(v: Video) -> None:
            await repo.add(v)

        results = await asyncio.gather(
            *[add_video(v) for v in videos],
            return_exceptions=True,
        )

        # All operations should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception), f"Unexpected error: {result}"

        # Verify all audit entries were created
        total_entries = 0
        for v in videos:
            total_entries += len(audit.get_history(v.id))
        assert total_entries == 5


class TestLifespanAuditWiring:
    """Tests for AuditLogger creation during application lifespan."""

    @pytest.fixture(autouse=True)
    def _clear_settings_cache(self) -> None:
        """Clear settings cache so env var changes take effect."""
        from stoat_ferret.api.settings import get_settings

        get_settings.cache_clear()

    def test_lifespan_creates_audit_logger(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lifespan creates AuditLogger and stores on app.state."""
        from fastapi.testclient import TestClient

        from stoat_ferret.api.app import create_app

        db_path = tmp_path / "test.db"
        monkeypatch.setenv("STOAT_DATABASE_PATH", str(db_path))

        app = create_app()
        with TestClient(app):
            assert hasattr(app.state, "audit_logger")
            assert isinstance(app.state.audit_logger, AuditLogger)

    def test_lifespan_sync_conn_closed_after_shutdown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sync connection is closed after lifespan shutdown."""
        from fastapi.testclient import TestClient

        from stoat_ferret.api.app import create_app

        db_path = tmp_path / "test.db"
        monkeypatch.setenv("STOAT_DATABASE_PATH", str(db_path))

        app = create_app()
        with TestClient(app):
            audit = app.state.audit_logger
            # Connection should be usable during lifespan
            assert audit._conn is not None

        # After lifespan ends, the sync connection should be closed
        # Attempting to use it should raise ProgrammingError
        with pytest.raises(sqlite3.ProgrammingError):
            audit._conn.execute("SELECT 1")
