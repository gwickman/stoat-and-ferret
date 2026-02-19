"""Project repository implementations."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

import aiosqlite

from stoat_ferret.db.models import Project

if TYPE_CHECKING:
    pass


class AsyncProjectRepository(Protocol):
    """Protocol for async project repository operations.

    Implementations must provide async methods for CRUD operations
    on project metadata.
    """

    async def add(self, project: Project) -> Project:
        """Add a project to the repository.

        Args:
            project: The project to add.

        Returns:
            The added project.

        Raises:
            ValueError: If a project with the same ID already exists.
        """
        ...

    async def get(self, id: str) -> Project | None:
        """Get a project by its ID.

        Args:
            id: The project ID.

        Returns:
            The project if found, None otherwise.
        """
        ...

    async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """List projects with pagination.

        Args:
            limit: Maximum number of projects to return.
            offset: Number of projects to skip.

        Returns:
            List of projects.
        """
        ...

    async def update(self, project: Project) -> Project:
        """Update an existing project.

        Args:
            project: The project with updated fields.

        Returns:
            The updated project.

        Raises:
            ValueError: If the project does not exist.
        """
        ...

    async def delete(self, id: str) -> bool:
        """Delete a project by its ID.

        Args:
            id: The project ID.

        Returns:
            True if the project was deleted, False if it didn't exist.
        """
        ...


class AsyncSQLiteProjectRepository:
    """Async SQLite implementation of the ProjectRepository protocol."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, project: Project) -> Project:
        """Add a project to the repository."""
        transitions_json = (
            json.dumps(project.transitions) if project.transitions is not None else None
        )
        try:
            await self._conn.execute(
                """
                INSERT INTO projects (
                    id, name, output_width, output_height, output_fps,
                    transitions_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.name,
                    project.output_width,
                    project.output_height,
                    project.output_fps,
                    transitions_json,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Project already exists: {e}") from e
        return project

    async def get(self, id: str) -> Project | None:
        """Get a project by its ID."""
        cursor = await self._conn.execute("SELECT * FROM projects WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return self._row_to_project(row) if row else None

    async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """List projects with pagination."""
        cursor = await self._conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._row_to_project(row) for row in rows]

    async def update(self, project: Project) -> Project:
        """Update an existing project."""
        transitions_json = (
            json.dumps(project.transitions) if project.transitions is not None else None
        )
        cursor = await self._conn.execute(
            """
            UPDATE projects SET
                name = ?,
                output_width = ?,
                output_height = ?,
                output_fps = ?,
                transitions_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                project.name,
                project.output_width,
                project.output_height,
                project.output_fps,
                transitions_json,
                project.updated_at.isoformat(),
                project.id,
            ),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Project {project.id} does not exist")
        return project

    async def delete(self, id: str) -> bool:
        """Delete a project by its ID."""
        cursor = await self._conn.execute("DELETE FROM projects WHERE id = ?", (id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_project(self, row: Any) -> Project:
        """Convert a database row to a Project object."""
        transitions_raw = row["transitions_json"]
        transitions = json.loads(transitions_raw) if transitions_raw is not None else None
        return Project(
            id=row["id"],
            name=row["name"],
            output_width=row["output_width"],
            output_height=row["output_height"],
            output_fps=row["output_fps"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            transitions=transitions,
        )


class AsyncInMemoryProjectRepository:
    """Async in-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._projects: dict[str, Project] = {}

    async def add(self, project: Project) -> Project:
        """Add a project to the repository."""
        if project.id in self._projects:
            raise ValueError(f"Project {project.id} already exists")
        self._projects[project.id] = copy.deepcopy(project)
        return copy.deepcopy(project)

    async def get(self, id: str) -> Project | None:
        """Get a project by its ID."""
        project = self._projects.get(id)
        return copy.deepcopy(project) if project is not None else None

    async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
        """List projects with pagination."""
        sorted_projects = sorted(self._projects.values(), key=lambda p: p.created_at, reverse=True)
        return [copy.deepcopy(p) for p in sorted_projects[offset : offset + limit]]

    async def update(self, project: Project) -> Project:
        """Update an existing project."""
        if project.id not in self._projects:
            raise ValueError(f"Project {project.id} does not exist")
        self._projects[project.id] = copy.deepcopy(project)
        return copy.deepcopy(project)

    async def delete(self, id: str) -> bool:
        """Delete a project by its ID."""
        if id not in self._projects:
            return False
        del self._projects[id]
        return True

    def seed(self, projects: list[Project]) -> None:
        """Populate the repository with initial test data.

        Args:
            projects: List of projects to seed. Stored as deepcopies.
        """
        for project in projects:
            self._projects[project.id] = copy.deepcopy(project)
