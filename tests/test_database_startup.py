"""Tests for database schema creation at startup."""

from __future__ import annotations

import os

import aiosqlite

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.schema import create_tables_async


class TestCreateTablesAsync:
    """Unit tests for create_tables_async()."""

    async def test_creates_all_ddl_objects(self) -> None:
        """create_tables_async() creates all 12 expected DDL objects."""
        db = await aiosqlite.connect(":memory:")
        try:
            await create_tables_async(db)

            # Query sqlite_master for all created objects
            cursor = await db.execute(
                "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            objects = await cursor.fetchall()
            names = {row[1] for row in objects}

            # Tables
            assert "videos" in names
            assert "audit_log" in names
            assert "projects" in names
            assert "clips" in names

            # Indexes
            assert "idx_videos_path" in names
            assert "idx_audit_log_entity" in names
            assert "idx_clips_project" in names
            assert "idx_clips_timeline" in names

            # FTS virtual table
            assert "videos_fts" in names

            # Triggers
            assert "videos_fts_insert" in names
            assert "videos_fts_delete" in names
            assert "videos_fts_update" in names
        finally:
            await db.close()

    async def test_idempotent(self) -> None:
        """Calling create_tables_async() twice does not error."""
        db = await aiosqlite.connect(":memory:")
        try:
            await create_tables_async(db)
            await create_tables_async(db)  # Should not raise
        finally:
            await db.close()


class TestLifespanSchemaCreation:
    """Integration tests for schema creation during application lifespan."""

    async def test_lifespan_creates_schema_on_fresh_db(self, tmp_path: object) -> None:
        """Application lifespan creates schema on a fresh database."""
        from stoat_ferret.api.settings import get_settings

        db_path = os.path.join(str(tmp_path), "test.db")
        os.environ["STOAT_DATABASE_PATH"] = db_path
        get_settings.cache_clear()

        app = create_app()

        try:
            async with lifespan(app):
                # Lifespan has started — schema should be created
                assert hasattr(app.state, "db")

            # Verify tables exist by connecting directly
            db = await aiosqlite.connect(db_path)
            try:
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = {row[0] for row in await cursor.fetchall()}
                assert "videos" in tables
                assert "projects" in tables
                assert "clips" in tables
                assert "audit_log" in tables
            finally:
                await db.close()
        finally:
            os.environ.pop("STOAT_DATABASE_PATH", None)
            get_settings.cache_clear()

    async def test_deps_injected_skips_schema_creation(self) -> None:
        """_deps_injected=True bypass skips schema creation (test mode)."""
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
        )

        # Verify _deps_injected is set
        assert app.state._deps_injected is True

        async with lifespan(app):
            # Lifespan should not open a database in test mode
            assert not hasattr(app.state, "db")
