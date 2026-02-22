"""Contract tests for async ProjectRepository implementations.

These tests run against both AsyncSQLiteProjectRepository and
AsyncInMemoryProjectRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import Project
from stoat_ferret.db.project_repository import (
    AsyncInMemoryProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.db.schema import create_tables_async

AsyncProjectRepositoryType = AsyncSQLiteProjectRepository | AsyncInMemoryProjectRepository


def make_test_project(**kwargs: object) -> Project:
    """Create a test project with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Project.new_id(),
        "name": "Test Project",
        "output_width": 1920,
        "output_height": 1080,
        "output_fps": 30,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Project(**defaults)  # type: ignore[arg-type]


@pytest.fixture(params=["sqlite", "memory"])
async def project_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncProjectRepositoryType, None]:
    """Provide both async project repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield AsyncSQLiteProjectRepository(conn)
        await conn.close()
    else:
        yield AsyncInMemoryProjectRepository()


@pytest.mark.contract
class TestAsyncProjectAddAndGet:
    """Tests for async add() and get() methods."""

    async def test_add_and_get(self, project_repository: AsyncProjectRepositoryType) -> None:
        """Adding a project allows retrieving it by ID."""
        project = make_test_project()
        await project_repository.add(project)
        retrieved = await project_repository.get(project.id)

        assert retrieved is not None
        assert retrieved.id == project.id
        assert retrieved.name == project.name
        assert retrieved.output_width == project.output_width
        assert retrieved.output_height == project.output_height
        assert retrieved.output_fps == project.output_fps

    async def test_get_nonexistent_returns_none(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Getting a nonexistent project returns None."""
        result = await project_repository.get("nonexistent-id")
        assert result is None

    async def test_add_duplicate_id_raises(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Adding a project with duplicate ID raises ValueError."""
        project = make_test_project()
        await project_repository.add(project)

        duplicate = make_test_project(id=project.id, name="Different Name")
        with pytest.raises(ValueError):
            await project_repository.add(duplicate)


@pytest.mark.contract
class TestAsyncProjectList:
    """Tests for async list_projects() method."""

    async def test_list_empty(self, project_repository: AsyncProjectRepositoryType) -> None:
        """Listing empty repository returns empty list."""
        result = await project_repository.list_projects()
        assert result == []

    async def test_list_returns_all_projects(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Listing returns all added projects."""
        project1 = make_test_project(name="Project 1")
        project2 = make_test_project(name="Project 2")
        await project_repository.add(project1)
        await project_repository.add(project2)

        result = await project_repository.list_projects()
        assert len(result) == 2
        ids = {p.id for p in result}
        assert project1.id in ids
        assert project2.id in ids

    async def test_list_with_limit(self, project_repository: AsyncProjectRepositoryType) -> None:
        """Limit restricts number of returned projects."""
        for i in range(5):
            await project_repository.add(make_test_project(name=f"Project {i}"))

        result = await project_repository.list_projects(limit=3)
        assert len(result) == 3

    async def test_list_with_offset(self, project_repository: AsyncProjectRepositoryType) -> None:
        """Offset skips projects."""
        for i in range(5):
            await project_repository.add(make_test_project(name=f"Project {i}"))

        result = await project_repository.list_projects(offset=2)
        assert len(result) == 3

    async def test_list_orders_by_created_at_descending(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Projects are returned newest first."""
        now = datetime.now(timezone.utc)
        old_project = make_test_project(name="Old", created_at=now - timedelta(hours=1))
        new_project = make_test_project(name="New", created_at=now)

        await project_repository.add(old_project)
        await project_repository.add(new_project)

        result = await project_repository.list_projects()
        assert result[0].id == new_project.id
        assert result[1].id == old_project.id


@pytest.mark.contract
class TestAsyncProjectCount:
    """Tests for async count() method."""

    async def test_count_empty(self, project_repository: AsyncProjectRepositoryType) -> None:
        """Count returns 0 for empty repository."""
        result = await project_repository.count()
        assert result == 0

    async def test_count_returns_total(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Count returns the total number of projects."""
        for i in range(5):
            await project_repository.add(make_test_project(name=f"Project {i}"))

        result = await project_repository.count()
        assert result == 5

    async def test_count_after_delete(self, project_repository: AsyncProjectRepositoryType) -> None:
        """Count decreases after deleting a project."""
        project = make_test_project()
        await project_repository.add(project)
        assert await project_repository.count() == 1

        await project_repository.delete(project.id)
        assert await project_repository.count() == 0


@pytest.mark.contract
class TestAsyncProjectUpdate:
    """Tests for async update() method."""

    async def test_update_changes_project(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Update modifies project fields."""
        project = make_test_project(name="Original")
        await project_repository.add(project)

        updated = replace(
            project,
            name="Updated",
            output_fps=60,
            updated_at=datetime.now(timezone.utc),
        )
        await project_repository.update(updated)

        retrieved = await project_repository.get(project.id)
        assert retrieved is not None
        assert retrieved.name == "Updated"
        assert retrieved.output_fps == 60

    async def test_update_nonexistent_raises(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Updating nonexistent project raises ValueError."""
        project = make_test_project()
        with pytest.raises(ValueError):
            await project_repository.update(project)


@pytest.mark.contract
class TestAsyncProjectDelete:
    """Tests for async delete() method."""

    async def test_delete_removes_project(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Delete removes project from repository."""
        project = make_test_project()
        await project_repository.add(project)

        result = await project_repository.delete(project.id)

        assert result is True
        assert await project_repository.get(project.id) is None

    async def test_delete_nonexistent_returns_false(
        self, project_repository: AsyncProjectRepositoryType
    ) -> None:
        """Deleting nonexistent project returns False."""
        result = await project_repository.delete("nonexistent")
        assert result is False
