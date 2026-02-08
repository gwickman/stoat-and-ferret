"""Tests for deepcopy isolation in InMemory repositories.

Verifies that mutating returned objects does not affect stored data.
"""

from __future__ import annotations

from datetime import datetime, timezone

from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project, Video
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository


def make_project(**kwargs: object) -> Project:
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


def make_video(**kwargs: object) -> Video:
    """Create a test video with default values."""
    now = datetime.now(timezone.utc)
    vid = Video.new_id()
    defaults: dict[str, object] = {
        "id": vid,
        "path": f"/videos/{vid}.mp4",
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


def make_clip(**kwargs: object) -> Clip:
    """Create a test clip with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Clip.new_id(),
        "project_id": "project-1",
        "source_video_id": "video-1",
        "in_point": 0,
        "out_point": 100,
        "timeline_position": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Clip(**defaults)  # type: ignore[arg-type]


class TestProjectIsolation:
    """Deepcopy isolation tests for AsyncInMemoryProjectRepository."""

    async def test_get_returns_isolated_copy(self) -> None:
        """Mutating a project returned by get() does not affect the store."""
        repo = AsyncInMemoryProjectRepository()
        project = make_project(name="Original")
        await repo.add(project)

        retrieved = await repo.get(project.id)
        assert retrieved is not None
        retrieved.name = "Mutated"

        stored = await repo.get(project.id)
        assert stored is not None
        assert stored.name == "Original"

    async def test_add_returns_isolated_copy(self) -> None:
        """Mutating the project returned by add() does not affect the store."""
        repo = AsyncInMemoryProjectRepository()
        project = make_project(name="Original")
        returned = await repo.add(project)
        returned.name = "Mutated"

        stored = await repo.get(project.id)
        assert stored is not None
        assert stored.name == "Original"

    async def test_add_isolates_from_caller(self) -> None:
        """Mutating the original object after add() does not affect the store."""
        repo = AsyncInMemoryProjectRepository()
        project = make_project(name="Original")
        await repo.add(project)
        project.name = "Mutated"

        stored = await repo.get(project.id)
        assert stored is not None
        assert stored.name == "Original"

    async def test_list_returns_isolated_copies(self) -> None:
        """Mutating projects returned by list_projects() does not affect the store."""
        repo = AsyncInMemoryProjectRepository()
        project = make_project(name="Original")
        await repo.add(project)

        listed = await repo.list_projects()
        listed[0].name = "Mutated"

        stored = await repo.get(project.id)
        assert stored is not None
        assert stored.name == "Original"

    async def test_update_isolates_from_caller(self) -> None:
        """Mutating the original object after update() does not affect the store."""
        repo = AsyncInMemoryProjectRepository()
        project = make_project(name="Original")
        await repo.add(project)

        project.name = "Updated"
        await repo.update(project)
        project.name = "Mutated Again"

        stored = await repo.get(project.id)
        assert stored is not None
        assert stored.name == "Updated"


class TestVideoIsolation:
    """Deepcopy isolation tests for AsyncInMemoryVideoRepository."""

    async def test_get_returns_isolated_copy(self) -> None:
        """Mutating a video returned by get() does not affect the store."""
        repo = AsyncInMemoryVideoRepository()
        video = make_video(filename="original.mp4")
        await repo.add(video)

        retrieved = await repo.get(video.id)
        assert retrieved is not None
        retrieved.filename = "mutated.mp4"

        stored = await repo.get(video.id)
        assert stored is not None
        assert stored.filename == "original.mp4"

    async def test_list_returns_isolated_copies(self) -> None:
        """Mutating videos returned by list_videos() does not affect the store."""
        repo = AsyncInMemoryVideoRepository()
        video = make_video(filename="original.mp4")
        await repo.add(video)

        listed = await repo.list_videos()
        listed[0].filename = "mutated.mp4"

        stored = await repo.get(video.id)
        assert stored is not None
        assert stored.filename == "original.mp4"

    async def test_search_returns_isolated_copies(self) -> None:
        """Mutating videos returned by search() does not affect the store."""
        repo = AsyncInMemoryVideoRepository()
        video = make_video(filename="original.mp4")
        await repo.add(video)

        results = await repo.search("original")
        results[0].filename = "mutated.mp4"

        stored = await repo.get(video.id)
        assert stored is not None
        assert stored.filename == "original.mp4"


class TestClipIsolation:
    """Deepcopy isolation tests for AsyncInMemoryClipRepository."""

    async def test_get_returns_isolated_copy(self) -> None:
        """Mutating a clip returned by get() does not affect the store."""
        repo = AsyncInMemoryClipRepository()
        clip = make_clip(in_point=0)
        await repo.add(clip)

        retrieved = await repo.get(clip.id)
        assert retrieved is not None
        retrieved.in_point = 999

        stored = await repo.get(clip.id)
        assert stored is not None
        assert stored.in_point == 0

    async def test_list_by_project_returns_isolated_copies(self) -> None:
        """Mutating clips returned by list_by_project() does not affect the store."""
        repo = AsyncInMemoryClipRepository()
        clip = make_clip(in_point=0)
        await repo.add(clip)

        listed = await repo.list_by_project("project-1")
        listed[0].in_point = 999

        stored = await repo.get(clip.id)
        assert stored is not None
        assert stored.in_point == 0
