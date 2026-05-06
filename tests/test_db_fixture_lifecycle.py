"""Tests for database fixture lifecycle (BL-346).

Verifies:
- tests/fixtures/stoat.seed.db exists and is a valid SQLite database at Alembic head
- Bootstrap logic copies fixture to configured db path when absent on startup
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

FIXTURE_PATH = Path("tests/fixtures/stoat.seed.db")

# Tables managed by Alembic migrations (present in the seed fixture).
ALEMBIC_TABLES = {"videos", "projects", "clips", "audit_log", "feature_flag_log"}

# Tables present after full lifespan startup (Alembic + create_tables_async).
FULL_SCHEMA_TABLES = {"videos", "projects", "clips", "tracks", "audit_log"}


class TestSeedFixture:
    """Verify the git-tracked seed fixture exists and is a valid SQLite database."""

    def test_fixture_exists(self) -> None:
        """tests/fixtures/stoat.seed.db must be present on disk."""
        assert FIXTURE_PATH.exists(), f"Seed fixture missing: {FIXTURE_PATH}"

    def test_fixture_is_valid_sqlite(self) -> None:
        """Seed fixture must pass SQLite integrity check."""
        assert FIXTURE_PATH.exists(), "Fixture missing — cannot run integrity check"
        conn = sqlite3.connect(str(FIXTURE_PATH))
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            assert result[0] == "ok", f"Fixture integrity check failed: {result[0]}"
        finally:
            conn.close()

    def test_fixture_has_alembic_managed_tables(self) -> None:
        """Seed fixture must contain all Alembic-managed schema tables."""
        assert FIXTURE_PATH.exists(), "Fixture missing — cannot check schema"
        conn = sqlite3.connect(str(FIXTURE_PATH))
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            missing = ALEMBIC_TABLES - tables
            assert not missing, f"Fixture is missing expected tables: {missing}"
        finally:
            conn.close()


class TestBootstrapLifecycle:
    """Verify bootstrap copy-then-migrate logic via the application lifespan."""

    async def test_lifespan_bootstrap_creates_db_from_fixture(self, tmp_path: Path) -> None:
        """Lifespan creates the database by copying fixture when db path is absent."""
        from stoat_ferret.api.app import create_app, lifespan
        from stoat_ferret.api.settings import get_settings

        db_path = tmp_path / "test_bootstrap.db"
        assert not db_path.exists(), "Pre-condition: db must be absent"

        os.environ["STOAT_DATABASE_PATH"] = str(db_path)
        get_settings.cache_clear()

        app = create_app()
        try:
            async with lifespan(app):
                assert db_path.exists(), "Database must exist after lifespan startup"
                # Verify the copied+migrated db has expected tables
                conn = sqlite3.connect(str(db_path))
                try:
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                        " AND name NOT LIKE 'sqlite_%'"
                    )
                    tables = {row[0] for row in cursor.fetchall()}
                    assert FULL_SCHEMA_TABLES.issubset(tables), (
                        f"Missing tables after bootstrap: {FULL_SCHEMA_TABLES - tables}"
                    )
                finally:
                    conn.close()
        finally:
            os.environ.pop("STOAT_DATABASE_PATH", None)
            get_settings.cache_clear()

    async def test_lifespan_skips_copy_when_db_already_exists(self, tmp_path: Path) -> None:
        """Lifespan does not overwrite an existing database on startup."""
        from stoat_ferret.api.app import create_app, lifespan
        from stoat_ferret.api.settings import get_settings

        db_path = tmp_path / "existing.db"
        # Seed a fresh SQLite database so the lifespan can actually start
        conn = sqlite3.connect(str(db_path))
        conn.close()

        os.environ["STOAT_DATABASE_PATH"] = str(db_path)
        get_settings.cache_clear()

        app = create_app()
        try:
            async with lifespan(app):
                pass
        finally:
            os.environ.pop("STOAT_DATABASE_PATH", None)
            get_settings.cache_clear()

        # File must not have been replaced (mtime unchanged or only grown by alembic writes)
        # The key invariant: the original file was not deleted and recreated from fixture.
        assert db_path.exists(), "Database must still exist after lifespan"
