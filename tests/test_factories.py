"""Unit tests for the builder-pattern fixture factory."""

from __future__ import annotations

from stoat_ferret.db.models import Clip, Project, Video
from tests.factories import ProjectFactory, make_test_video

# ---------------------------------------------------------------------------
# make_test_video tests
# ---------------------------------------------------------------------------


class TestMakeTestVideo:
    """Tests for the make_test_video helper."""

    def test_returns_video_with_defaults(self) -> None:
        """Video is created with sensible defaults."""
        video = make_test_video()
        assert isinstance(video, Video)
        assert video.duration_frames == 1000
        assert video.width == 1920
        assert video.height == 1080
        assert video.video_codec == "h264"

    def test_overrides_apply(self) -> None:
        """Keyword overrides replace defaults."""
        video = make_test_video(filename="custom.mp4", width=1280)
        assert video.filename == "custom.mp4"
        assert video.width == 1280

    def test_unique_ids(self) -> None:
        """Each call produces a unique video ID."""
        v1 = make_test_video()
        v2 = make_test_video()
        assert v1.id != v2.id


# ---------------------------------------------------------------------------
# ProjectFactory.build() tests
# ---------------------------------------------------------------------------


class TestProjectFactoryBuild:
    """Tests for ProjectFactory.build() (domain objects, no HTTP)."""

    def test_build_default_project(self) -> None:
        """Build returns a Project with sensible defaults."""
        project = ProjectFactory().build()
        assert isinstance(project, Project)
        assert project.name == "Test Project"
        assert project.output_width == 1920
        assert project.output_height == 1080
        assert project.output_fps == 30
        assert project.id  # non-empty

    def test_with_name(self) -> None:
        """with_name() sets the project name."""
        project = ProjectFactory().with_name("Custom").build()
        assert project.name == "Custom"

    def test_with_output(self) -> None:
        """with_output() sets dimensions and fps."""
        project = ProjectFactory().with_output(width=3840, height=2160, fps=60).build()
        assert project.output_width == 3840
        assert project.output_height == 2160
        assert project.output_fps == 60

    def test_with_output_partial(self) -> None:
        """with_output() updates only specified fields."""
        project = ProjectFactory().with_output(fps=24).build()
        assert project.output_fps == 24
        assert project.output_width == 1920  # default unchanged

    def test_chaining_returns_self(self) -> None:
        """Each builder method returns the factory for fluent chaining."""
        factory = ProjectFactory()
        result = factory.with_name("A").with_output(fps=60).with_clip()
        assert result is factory

    def test_unique_ids(self) -> None:
        """Each build() call generates a unique project ID."""
        factory = ProjectFactory()
        p1 = factory.build()
        p2 = factory.build()
        assert p1.id != p2.id


# ---------------------------------------------------------------------------
# ProjectFactory.build_with_clips() tests
# ---------------------------------------------------------------------------


class TestProjectFactoryBuildWithClips:
    """Tests for ProjectFactory.build_with_clips()."""

    def test_no_clips(self) -> None:
        """build_with_clips() with no clip configs returns empty lists."""
        project, videos, clips = ProjectFactory().build_with_clips()
        assert isinstance(project, Project)
        assert videos == []
        assert clips == []

    def test_single_clip(self) -> None:
        """build_with_clips() produces matching video and clip."""
        project, videos, clips = (
            ProjectFactory()
            .with_clip(in_point=10, out_point=200, timeline_position=5)
            .build_with_clips()
        )
        assert len(videos) == 1
        assert len(clips) == 1

        clip = clips[0]
        assert isinstance(clip, Clip)
        assert clip.project_id == project.id
        assert clip.source_video_id == videos[0].id
        assert clip.in_point == 10
        assert clip.out_point == 200
        assert clip.timeline_position == 5

    def test_multiple_clips(self) -> None:
        """build_with_clips() handles multiple clips."""
        project, videos, clips = (
            ProjectFactory()
            .with_clip(out_point=100)
            .with_clip(out_point=200, timeline_position=100)
            .build_with_clips()
        )
        assert len(videos) == 2
        assert len(clips) == 2
        assert clips[0].out_point == 100
        assert clips[1].out_point == 200
        assert clips[1].timeline_position == 100

    def test_clip_with_explicit_video_id(self) -> None:
        """with_clip(source_video_id=...) uses the specified ID."""
        _, videos, clips = (
            ProjectFactory().with_clip(source_video_id="vid-custom").build_with_clips()
        )
        assert clips[0].source_video_id == "vid-custom"
        assert videos[0].id == "vid-custom"
