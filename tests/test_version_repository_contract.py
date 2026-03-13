"""Contract tests for async VersionRepository implementations.

These tests run against both AsyncSQLiteVersionRepository and
AsyncInMemoryVersionRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import aiosqlite
import pytest

from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.db.version_repository import (
    AsyncInMemoryVersionRepository,
    AsyncSQLiteVersionRepository,
    VersionRecord,
    compute_checksum,
)

AsyncVersionRepositoryType = AsyncSQLiteVersionRepository | AsyncInMemoryVersionRepository


async def insert_test_projects(conn: aiosqlite.Connection) -> None:
    """Insert test projects for foreign key references."""
    for pid in ("project-1", "project-2"):
        await conn.execute(
            """
            INSERT INTO projects (
                id, name, output_width, output_height, output_fps,
                created_at, updated_at
            ) VALUES (?, ?, 1920, 1080, 30,
                      '2024-01-01T00:00:00', '2024-01-01T00:00:00')
            """,
            (pid, f"Test {pid}"),
        )
    await conn.commit()


@pytest.fixture(params=["sqlite", "memory"])
async def version_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncVersionRepositoryType, None]:
    """Provide both async version repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)
        await insert_test_projects(conn)

        yield AsyncSQLiteVersionRepository(conn)
        await conn.close()
    else:
        yield AsyncInMemoryVersionRepository()


@pytest.mark.contract
class TestVersionSave:
    """Tests for save() method."""

    async def test_first_save_creates_version_one(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """First save for a project creates version 1."""
        record = await version_repository.save("project-1", '{"clips": []}')

        assert record.version_number == 1
        assert record.project_id == "project-1"
        assert record.timeline_json == '{"clips": []}'
        assert record.checksum == compute_checksum('{"clips": []}')
        assert record.id is not None

    async def test_subsequent_saves_increment(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """Subsequent saves auto-increment version number."""
        r1 = await version_repository.save("project-1", '{"v": 1}')
        r2 = await version_repository.save("project-1", '{"v": 2}')
        r3 = await version_repository.save("project-1", '{"v": 3}')

        assert r1.version_number == 1
        assert r2.version_number == 2
        assert r3.version_number == 3

    async def test_save_computes_sha256_checksum(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """Save computes correct SHA-256 checksum."""
        data = '{"timeline": "data"}'
        record = await version_repository.save("project-1", data)

        assert record.checksum == compute_checksum(data)


@pytest.mark.contract
class TestVersionList:
    """Tests for list_versions() method."""

    async def test_list_empty_project(self, version_repository: AsyncVersionRepositoryType) -> None:
        """Listing versions for empty project returns empty list."""
        result = await version_repository.list_versions("project-1")
        assert result == []

    async def test_list_returns_versions_descending(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """list_versions returns records ordered by version_number descending."""
        await version_repository.save("project-1", '{"v": 1}')
        await version_repository.save("project-1", '{"v": 2}')
        await version_repository.save("project-1", '{"v": 3}')

        versions = await version_repository.list_versions("project-1")

        assert len(versions) == 3
        assert versions[0].version_number == 3
        assert versions[1].version_number == 2
        assert versions[2].version_number == 1

    async def test_list_returns_checksum_and_created_at(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """list_versions returns version_number, created_at, checksum."""
        await version_repository.save("project-1", '{"data": true}')

        versions = await version_repository.list_versions("project-1")
        v = versions[0]

        assert isinstance(v, VersionRecord)
        assert v.version_number == 1
        assert v.created_at is not None
        assert v.checksum == compute_checksum('{"data": true}')


@pytest.mark.contract
class TestVersionGet:
    """Tests for get_version() method."""

    async def test_get_existing_version(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """get_version returns the correct version."""
        await version_repository.save("project-1", '{"v": 1}')
        await version_repository.save("project-1", '{"v": 2}')

        v1 = await version_repository.get_version("project-1", 1)
        v2 = await version_repository.get_version("project-1", 2)

        assert v1 is not None
        assert v1.timeline_json == '{"v": 1}'
        assert v2 is not None
        assert v2.timeline_json == '{"v": 2}'

    async def test_get_nonexistent_returns_none(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """get_version returns None for nonexistent version."""
        result = await version_repository.get_version("project-1", 99)
        assert result is None


@pytest.mark.contract
class TestVersionRestore:
    """Tests for restore() method."""

    async def test_restore_creates_new_version(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """Restoring version 3 when current is 5 creates version 6."""
        await version_repository.save("project-1", '{"v": 1}')
        await version_repository.save("project-1", '{"v": 2}')
        await version_repository.save("project-1", '{"v": 3}')
        await version_repository.save("project-1", '{"v": 4}')
        await version_repository.save("project-1", '{"v": 5}')

        restored = await version_repository.restore("project-1", 3)

        assert restored.version_number == 6
        assert restored.timeline_json == '{"v": 3}'
        assert restored.checksum == compute_checksum('{"v": 3}')

    async def test_restore_nonexistent_raises(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """Restoring nonexistent version raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await version_repository.restore("project-1", 99)


@pytest.mark.contract
class TestVersionChecksumValidation:
    """Tests for checksum validation on restore."""

    async def test_corrupted_checksum_raises_on_restore(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """Corrupted checksum is detected on restore."""
        await version_repository.save("project-1", '{"data": "original"}')

        # Corrupt the stored checksum directly
        if isinstance(version_repository, AsyncSQLiteVersionRepository):
            await version_repository._conn.execute(
                """
                UPDATE project_versions SET checksum = 'corrupted'
                WHERE project_id = ? AND version_number = ?
                """,
                ("project-1", 1),
            )
            await version_repository._conn.commit()
        else:
            # For in-memory, directly mutate internal state
            version_repository._versions["project-1"][0].checksum = "corrupted"

        with pytest.raises(ValueError, match="Checksum mismatch"):
            await version_repository.restore("project-1", 1)


@pytest.mark.contract
class TestVersionMultiProjectIsolation:
    """Tests for multi-project version isolation."""

    async def test_versions_isolated_between_projects(
        self, version_repository: AsyncVersionRepositoryType
    ) -> None:
        """Version numbers are independent per project."""
        await version_repository.save("project-1", '{"p1": 1}')
        await version_repository.save("project-1", '{"p1": 2}')
        await version_repository.save("project-2", '{"p2": 1}')

        p1_versions = await version_repository.list_versions("project-1")
        p2_versions = await version_repository.list_versions("project-2")

        assert len(p1_versions) == 2
        assert len(p2_versions) == 1
        assert p2_versions[0].version_number == 1
