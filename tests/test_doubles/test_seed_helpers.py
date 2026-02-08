"""Tests for seed helpers on InMemory repositories.

Verifies that seed() populates data correctly and with deepcopy isolation.
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


class TestProjectSeed:
    """Seed helper tests for AsyncInMemoryProjectRepository."""

    async def test_seed_populates_data(self) -> None:
        """Seeded projects are retrievable."""
        repo = AsyncInMemoryProjectRepository()
        p1 = make_project(name="Project 1")
        p2 = make_project(name="Project 2")
        repo.seed([p1, p2])

        retrieved1 = await repo.get(p1.id)
        retrieved2 = await repo.get(p2.id)
        assert retrieved1 is not None
        assert retrieved1.name == "Project 1"
        assert retrieved2 is not None
        assert retrieved2.name == "Project 2"

    async def test_seed_isolates_from_source(self) -> None:
        """Mutating seed source does not affect stored data."""
        repo = AsyncInMemoryProjectRepository()
        project = make_project(name="Original")
        repo.seed([project])
        project.name = "Mutated"

        stored = await repo.get(project.id)
        assert stored is not None
        assert stored.name == "Original"

    async def test_seed_appears_in_list(self) -> None:
        """Seeded projects appear in list_projects()."""
        repo = AsyncInMemoryProjectRepository()
        p1 = make_project()
        p2 = make_project()
        repo.seed([p1, p2])

        listed = await repo.list_projects()
        assert len(listed) == 2


class TestVideoSeed:
    """Seed helper tests for AsyncInMemoryVideoRepository."""

    async def test_seed_populates_data(self) -> None:
        """Seeded videos are retrievable by ID and path."""
        repo = AsyncInMemoryVideoRepository()
        video = make_video(filename="seeded.mp4")
        repo.seed([video])

        by_id = await repo.get(video.id)
        by_path = await repo.get_by_path(video.path)
        assert by_id is not None
        assert by_id.filename == "seeded.mp4"
        assert by_path is not None
        assert by_path.id == video.id

    async def test_seed_isolates_from_source(self) -> None:
        """Mutating seed source does not affect stored data."""
        repo = AsyncInMemoryVideoRepository()
        video = make_video(filename="original.mp4")
        repo.seed([video])
        video.filename = "mutated.mp4"

        stored = await repo.get(video.id)
        assert stored is not None
        assert stored.filename == "original.mp4"


class TestClipSeed:
    """Seed helper tests for AsyncInMemoryClipRepository."""

    async def test_seed_populates_data(self) -> None:
        """Seeded clips are retrievable."""
        repo = AsyncInMemoryClipRepository()
        clip = make_clip(in_point=10, out_point=50)
        repo.seed([clip])

        retrieved = await repo.get(clip.id)
        assert retrieved is not None
        assert retrieved.in_point == 10
        assert retrieved.out_point == 50

    async def test_seed_isolates_from_source(self) -> None:
        """Mutating seed source does not affect stored data."""
        repo = AsyncInMemoryClipRepository()
        clip = make_clip(in_point=10)
        repo.seed([clip])
        clip.in_point = 999

        stored = await repo.get(clip.id)
        assert stored is not None
        assert stored.in_point == 10

    async def test_seed_appears_in_list(self) -> None:
        """Seeded clips appear in list_by_project()."""
        repo = AsyncInMemoryClipRepository()
        c1 = make_clip(timeline_position=0)
        c2 = make_clip(timeline_position=100)
        repo.seed([c1, c2])

        listed = await repo.list_by_project("project-1")
        assert len(listed) == 2
