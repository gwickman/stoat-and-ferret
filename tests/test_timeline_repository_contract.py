"""Contract tests for async TimelineRepository implementations.

These tests run against both AsyncSQLiteTimelineRepository and
AsyncInMemoryTimelineRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import Clip, Track
from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.db.timeline_repository import (
    AsyncInMemoryTimelineRepository,
    AsyncSQLiteTimelineRepository,
)

AsyncTimelineRepositoryType = AsyncSQLiteTimelineRepository | AsyncInMemoryTimelineRepository


def make_test_track(**kwargs: object) -> Track:
    """Create a test track with default values."""
    defaults: dict[str, object] = {
        "id": Track.new_id(),
        "project_id": "project-1",
        "track_type": "video",
        "label": "Video 1",
        "z_index": 0,
        "muted": False,
        "locked": False,
    }
    defaults.update(kwargs)
    return Track(**defaults)  # type: ignore[arg-type]


def make_test_clip(**kwargs: object) -> Clip:
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


async def insert_test_project_and_video(conn: aiosqlite.Connection) -> None:
    """Insert test project and video for foreign key references."""
    await conn.execute(
        """
        INSERT INTO projects (
            id, name, output_width, output_height, output_fps, created_at, updated_at
        ) VALUES (
            'project-1', 'Test', 1920, 1080, 30,
            '2024-01-01T00:00:00', '2024-01-01T00:00:00'
        )
        """
    )
    await conn.execute(
        """
        INSERT INTO projects (
            id, name, output_width, output_height, output_fps, created_at, updated_at
        ) VALUES (
            'project-2', 'Test 2', 1920, 1080, 30,
            '2024-01-01T00:00:00', '2024-01-01T00:00:00'
        )
        """
    )
    await conn.execute(
        """
        INSERT INTO videos (
            id, path, filename, duration_frames, frame_rate_numerator,
            frame_rate_denominator, width, height, video_codec, file_size,
            created_at, updated_at
        ) VALUES (
            'video-1', '/test.mp4', 'test.mp4', 1000, 24, 1, 1920, 1080,
            'h264', 1000000, '2024-01-01T00:00:00', '2024-01-01T00:00:00'
        )
        """
    )
    await conn.commit()


@pytest.fixture(params=["sqlite", "memory"])
async def timeline_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncTimelineRepositoryType, None]:
    """Provide both async timeline repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)
        await insert_test_project_and_video(conn)

        yield AsyncSQLiteTimelineRepository(conn)
        await conn.close()
    else:
        yield AsyncInMemoryTimelineRepository()


@pytest.fixture
async def sqlite_timeline_repo() -> AsyncGenerator[AsyncSQLiteTimelineRepository, None]:
    """Provide SQLite timeline repository with pre-seeded foreign keys."""
    conn = await aiosqlite.connect(":memory:")
    await create_tables_async(conn)
    await insert_test_project_and_video(conn)
    yield AsyncSQLiteTimelineRepository(conn)
    await conn.close()


@pytest.mark.contract
class TestTrackCreateAndGet:
    """Tests for create_track() and get_track() methods."""

    async def test_create_and_get(self, timeline_repository: AsyncTimelineRepositoryType) -> None:
        """Creating a track allows retrieving it by ID."""
        track = make_test_track()
        await timeline_repository.create_track(track)
        retrieved = await timeline_repository.get_track(track.id)

        assert retrieved is not None
        assert retrieved.id == track.id
        assert retrieved.project_id == track.project_id
        assert retrieved.track_type == track.track_type
        assert retrieved.label == track.label
        assert retrieved.z_index == track.z_index
        assert retrieved.muted == track.muted
        assert retrieved.locked == track.locked

    async def test_get_nonexistent_returns_none(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """Getting a nonexistent track returns None."""
        result = await timeline_repository.get_track("nonexistent-id")
        assert result is None

    async def test_create_duplicate_id_raises(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """Creating a track with duplicate ID raises ValueError."""
        track = make_test_track()
        await timeline_repository.create_track(track)

        duplicate = make_test_track(id=track.id, label="Duplicate")
        with pytest.raises(ValueError):
            await timeline_repository.create_track(duplicate)

    async def test_create_returns_track_with_id(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """create_track returns track with id set."""
        track = make_test_track()
        result = await timeline_repository.create_track(track)
        assert result.id == track.id


@pytest.mark.contract
class TestTrackGetByProject:
    """Tests for get_tracks_by_project() method."""

    async def test_empty_project(self, timeline_repository: AsyncTimelineRepositoryType) -> None:
        """Listing tracks for empty project returns empty list."""
        result = await timeline_repository.get_tracks_by_project("project-1")
        assert result == []

    async def test_returns_ordered_by_z_index(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """get_tracks_by_project returns tracks ordered by z_index."""
        track1 = make_test_track(z_index=2, label="Top")
        track2 = make_test_track(z_index=0, label="Bottom")
        track3 = make_test_track(z_index=1, label="Middle")

        await timeline_repository.create_track(track1)
        await timeline_repository.create_track(track2)
        await timeline_repository.create_track(track3)

        tracks = await timeline_repository.get_tracks_by_project("project-1")
        assert len(tracks) == 3
        assert tracks[0].z_index == 0
        assert tracks[1].z_index == 1
        assert tracks[2].z_index == 2

    async def test_filters_by_project(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """get_tracks_by_project only returns tracks for specified project."""
        track1 = make_test_track(project_id="project-1")
        track2 = make_test_track(project_id="project-2")

        await timeline_repository.create_track(track1)
        await timeline_repository.create_track(track2)

        tracks = await timeline_repository.get_tracks_by_project("project-1")
        assert len(tracks) == 1
        assert tracks[0].project_id == "project-1"


@pytest.mark.contract
class TestTrackUpdate:
    """Tests for update_track() method."""

    async def test_update_label(self, timeline_repository: AsyncTimelineRepositoryType) -> None:
        """Updating track label succeeds."""
        track = make_test_track()
        await timeline_repository.create_track(track)

        track.label = "Renamed Track"
        await timeline_repository.update_track(track)

        retrieved = await timeline_repository.get_track(track.id)
        assert retrieved is not None
        assert retrieved.label == "Renamed Track"

    async def test_update_muted_locked(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """Updating muted and locked flags succeeds."""
        track = make_test_track()
        await timeline_repository.create_track(track)

        track.muted = True
        track.locked = True
        await timeline_repository.update_track(track)

        retrieved = await timeline_repository.get_track(track.id)
        assert retrieved is not None
        assert retrieved.muted is True
        assert retrieved.locked is True

    async def test_update_nonexistent_raises(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """Updating nonexistent track raises ValueError."""
        track = make_test_track()
        with pytest.raises(ValueError):
            await timeline_repository.update_track(track)


@pytest.mark.contract
class TestTrackDelete:
    """Tests for delete_track() method."""

    async def test_delete_existing(self, timeline_repository: AsyncTimelineRepositoryType) -> None:
        """Deleting existing track returns True."""
        track = make_test_track()
        await timeline_repository.create_track(track)

        result = await timeline_repository.delete_track(track.id)
        assert result is True
        assert await timeline_repository.get_track(track.id) is None

    async def test_delete_nonexistent(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """Deleting nonexistent track returns False."""
        result = await timeline_repository.delete_track("nonexistent")
        assert result is False


@pytest.mark.contract
class TestClipsByTrack:
    """Tests for get_clips_by_track() method."""

    async def test_empty_track(self, timeline_repository: AsyncTimelineRepositoryType) -> None:
        """Querying clips for empty track returns empty list."""
        result = await timeline_repository.get_clips_by_track("track-1")
        assert result == []

    async def test_returns_clips_ordered_by_timeline_start(
        self, sqlite_timeline_repo: AsyncSQLiteTimelineRepository
    ) -> None:
        """get_clips_by_track returns clips ordered by timeline_start."""
        track = make_test_track(id="track-1")
        await sqlite_timeline_repo.create_track(track)

        clip1 = make_test_clip(track_id="track-1", timeline_start=10.0)
        clip2 = make_test_clip(track_id="track-1", timeline_start=0.0)
        clip3 = make_test_clip(track_id="track-1", timeline_start=5.0)

        # Insert clips directly via SQL since clip repo is separate
        for clip in [clip1, clip2, clip3]:
            await sqlite_timeline_repo._conn.execute(
                """
                INSERT INTO clips (id, project_id, source_video_id, in_point, out_point,
                                  timeline_position, created_at, updated_at, track_id,
                                  timeline_start)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clip.id,
                    clip.project_id,
                    clip.source_video_id,
                    clip.in_point,
                    clip.out_point,
                    clip.timeline_position,
                    clip.created_at.isoformat(),
                    clip.updated_at.isoformat(),
                    clip.track_id,
                    clip.timeline_start,
                ),
            )
        await sqlite_timeline_repo._conn.commit()

        clips = await sqlite_timeline_repo.get_clips_by_track("track-1")
        assert len(clips) == 3
        assert clips[0].timeline_start == 0.0
        assert clips[1].timeline_start == 5.0
        assert clips[2].timeline_start == 10.0

    async def test_clips_without_track_excluded(
        self, sqlite_timeline_repo: AsyncSQLiteTimelineRepository
    ) -> None:
        """Clips without track_id are excluded from results."""
        track = make_test_track(id="track-1")
        await sqlite_timeline_repo.create_track(track)

        clip_with_track = make_test_clip(track_id="track-1", timeline_start=0.0)
        clip_without_track = make_test_clip(track_id=None, timeline_start=5.0)

        for clip in [clip_with_track, clip_without_track]:
            await sqlite_timeline_repo._conn.execute(
                """
                INSERT INTO clips (id, project_id, source_video_id, in_point, out_point,
                                  timeline_position, created_at, updated_at, track_id,
                                  timeline_start)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clip.id,
                    clip.project_id,
                    clip.source_video_id,
                    clip.in_point,
                    clip.out_point,
                    clip.timeline_position,
                    clip.created_at.isoformat(),
                    clip.updated_at.isoformat(),
                    clip.track_id,
                    clip.timeline_start,
                ),
            )
        await sqlite_timeline_repo._conn.commit()

        clips = await sqlite_timeline_repo.get_clips_by_track("track-1")
        assert len(clips) == 1
        assert clips[0].id == clip_with_track.id

    async def test_inmemory_clips_by_track(self) -> None:
        """InMemory get_clips_by_track returns correct clips ordered by timeline_start."""
        repo = AsyncInMemoryTimelineRepository()
        track = make_test_track(id="track-1")
        await repo.create_track(track)

        clip1 = make_test_clip(track_id="track-1", timeline_start=10.0)
        clip2 = make_test_clip(track_id="track-1", timeline_start=0.0)
        clip3 = make_test_clip(track_id="other-track", timeline_start=5.0)

        repo.seed([], clips=[clip1, clip2, clip3])

        clips = await repo.get_clips_by_track("track-1")
        assert len(clips) == 2
        assert clips[0].timeline_start == 0.0
        assert clips[1].timeline_start == 10.0


@pytest.mark.contract
class TestCountMethods:
    """Tests for count_tracks() and count_clips() methods."""

    async def test_count_tracks_empty(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """count_tracks returns 0 for project with no tracks."""
        count = await timeline_repository.count_tracks("project-1")
        assert count == 0

    async def test_count_tracks_accurate(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """count_tracks returns accurate count per project."""
        await timeline_repository.create_track(make_test_track(project_id="project-1"))
        await timeline_repository.create_track(make_test_track(project_id="project-1"))
        await timeline_repository.create_track(make_test_track(project_id="project-2"))

        assert await timeline_repository.count_tracks("project-1") == 2
        assert await timeline_repository.count_tracks("project-2") == 1

    async def test_count_clips_empty(
        self, timeline_repository: AsyncTimelineRepositoryType
    ) -> None:
        """count_clips returns 0 for project with no clips."""
        count = await timeline_repository.count_clips("project-1")
        assert count == 0

    async def test_count_clips_sqlite(
        self, sqlite_timeline_repo: AsyncSQLiteTimelineRepository
    ) -> None:
        """count_clips returns accurate count for SQLite."""
        clip1 = make_test_clip(project_id="project-1")
        clip2 = make_test_clip(project_id="project-1")

        for clip in [clip1, clip2]:
            await sqlite_timeline_repo._conn.execute(
                """
                INSERT INTO clips (id, project_id, source_video_id, in_point, out_point,
                                  timeline_position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clip.id,
                    clip.project_id,
                    clip.source_video_id,
                    clip.in_point,
                    clip.out_point,
                    clip.timeline_position,
                    clip.created_at.isoformat(),
                    clip.updated_at.isoformat(),
                ),
            )
        await sqlite_timeline_repo._conn.commit()

        assert await sqlite_timeline_repo.count_clips("project-1") == 2

    async def test_count_clips_inmemory(self) -> None:
        """count_clips returns accurate count for InMemory."""
        repo = AsyncInMemoryTimelineRepository()
        clip1 = make_test_clip(project_id="project-1")
        clip2 = make_test_clip(project_id="project-1")
        clip3 = make_test_clip(project_id="project-2")
        repo.seed([], clips=[clip1, clip2, clip3])

        assert await repo.count_clips("project-1") == 2
        assert await repo.count_clips("project-2") == 1


@pytest.mark.contract
class TestDeepCopyIsolation:
    """Tests that InMemory implementation uses deepcopy for isolation."""

    async def test_create_returns_isolated_copy(self) -> None:
        """Mutating returned track does not affect stored track."""
        repo = AsyncInMemoryTimelineRepository()
        track = make_test_track(label="Original")
        result = await repo.create_track(track)
        result.label = "Mutated"

        retrieved = await repo.get_track(track.id)
        assert retrieved is not None
        assert retrieved.label == "Original"

    async def test_get_returns_isolated_copy(self) -> None:
        """Mutating retrieved track does not affect stored track."""
        repo = AsyncInMemoryTimelineRepository()
        track = make_test_track(label="Original")
        await repo.create_track(track)

        retrieved = await repo.get_track(track.id)
        assert retrieved is not None
        retrieved.label = "Mutated"

        retrieved_again = await repo.get_track(track.id)
        assert retrieved_again is not None
        assert retrieved_again.label == "Original"


@pytest.mark.contract
class TestFullLifecycle:
    """Full lifecycle test: create tracks, add clips, query, delete."""

    async def test_lifecycle(self, sqlite_timeline_repo: AsyncSQLiteTimelineRepository) -> None:
        """Full lifecycle: create -> get -> update -> query clips -> delete."""
        # Create tracks
        video_track = make_test_track(id="vt-1", track_type="video", label="Video 1", z_index=0)
        audio_track = make_test_track(id="at-1", track_type="audio", label="Audio 1", z_index=1)
        await sqlite_timeline_repo.create_track(video_track)
        await sqlite_timeline_repo.create_track(audio_track)

        # Verify listing by project
        tracks = await sqlite_timeline_repo.get_tracks_by_project("project-1")
        assert len(tracks) == 2
        assert tracks[0].track_type == "video"
        assert tracks[1].track_type == "audio"

        # Update a track
        video_track.label = "Main Video"
        video_track.muted = True
        await sqlite_timeline_repo.update_track(video_track)
        updated = await sqlite_timeline_repo.get_track("vt-1")
        assert updated is not None
        assert updated.label == "Main Video"
        assert updated.muted is True

        # Add clips to track via direct SQL
        clip = make_test_clip(track_id="vt-1", timeline_start=0.0)
        await sqlite_timeline_repo._conn.execute(
            """
            INSERT INTO clips (id, project_id, source_video_id, in_point, out_point,
                              timeline_position, created_at, updated_at, track_id,
                              timeline_start)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clip.id,
                clip.project_id,
                clip.source_video_id,
                clip.in_point,
                clip.out_point,
                clip.timeline_position,
                clip.created_at.isoformat(),
                clip.updated_at.isoformat(),
                clip.track_id,
                clip.timeline_start,
            ),
        )
        await sqlite_timeline_repo._conn.commit()

        # Query clips by track
        clips = await sqlite_timeline_repo.get_clips_by_track("vt-1")
        assert len(clips) == 1

        # Count methods
        assert await sqlite_timeline_repo.count_tracks("project-1") == 2
        assert await sqlite_timeline_repo.count_clips("project-1") == 1

        # Delete a track
        deleted = await sqlite_timeline_repo.delete_track("at-1")
        assert deleted is True
        assert await sqlite_timeline_repo.count_tracks("project-1") == 1


@pytest.mark.contract
class TestDIWiring:
    """Tests for DI wiring of timeline repository."""

    def test_timeline_repository_accessible_via_app_state(self) -> None:
        """Timeline repository is accessible via app.state."""
        from stoat_ferret.api.app import create_app
        from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
        from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
        from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

        timeline_repo = AsyncInMemoryTimelineRepository()
        app = create_app(
            video_repository=AsyncInMemoryVideoRepository(),
            project_repository=AsyncInMemoryProjectRepository(),
            clip_repository=AsyncInMemoryClipRepository(),
            timeline_repository=timeline_repo,
        )
        assert app.state.timeline_repository is timeline_repo
