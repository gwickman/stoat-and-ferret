"""Tests for Clip model validation."""

from datetime import datetime, timezone

import pytest

from stoat_ferret.db.models import Clip, ClipValidationError


def make_clip(**kwargs) -> Clip:
    """Create a clip with default values."""
    now = datetime.now(timezone.utc)
    defaults = {
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
    return Clip(**defaults)


class TestClipValidation:
    """Tests for Clip.validate() method."""

    def test_valid_clip_passes_validation(self) -> None:
        """Valid clip passes Rust validation."""
        clip = make_clip(
            in_point=0,
            out_point=100,
            timeline_position=0,
        )

        # Should not raise
        clip.validate("/path/to/video.mp4")

    def test_valid_clip_with_offset_in_point(self) -> None:
        """Clip with non-zero in_point passes validation."""
        clip = make_clip(
            in_point=50,
            out_point=150,
            timeline_position=200,
        )

        # Should not raise
        clip.validate("/path/to/video.mp4")

    def test_valid_clip_with_source_duration(self) -> None:
        """Clip with source duration within bounds passes validation."""
        clip = make_clip(
            in_point=0,
            out_point=100,
            timeline_position=0,
        )

        # Should not raise - clip is within source duration
        clip.validate("/path/to/video.mp4", source_duration_frames=200)

    def test_invalid_clip_out_before_in_raises(self) -> None:
        """Clip with out_point before in_point raises ClipValidationError."""
        clip = make_clip(
            in_point=100,
            out_point=50,  # Invalid: out < in
            timeline_position=0,
        )

        with pytest.raises(ClipValidationError):
            clip.validate("/path/to/video.mp4")

    def test_invalid_clip_zero_duration_raises(self) -> None:
        """Clip with zero duration (in == out) raises ClipValidationError."""
        clip = make_clip(
            in_point=100,
            out_point=100,  # Invalid: zero duration
            timeline_position=0,
        )

        with pytest.raises(ClipValidationError):
            clip.validate("/path/to/video.mp4")

    def test_invalid_clip_empty_source_path_raises(self) -> None:
        """Clip with empty source path raises ClipValidationError."""
        clip = make_clip(
            in_point=0,
            out_point=100,
            timeline_position=0,
        )

        with pytest.raises(ClipValidationError):
            clip.validate("")  # Invalid: empty path

    def test_invalid_clip_exceeds_source_duration_raises(self) -> None:
        """Clip that exceeds source duration raises ClipValidationError."""
        clip = make_clip(
            in_point=0,
            out_point=200,  # Beyond source duration
            timeline_position=0,
        )

        with pytest.raises(ClipValidationError):
            clip.validate("/path/to/video.mp4", source_duration_frames=100)


class TestClipNewId:
    """Tests for Clip.new_id() class method."""

    def test_new_id_returns_uuid(self) -> None:
        """new_id returns a valid UUID string."""
        id1 = Clip.new_id()
        id2 = Clip.new_id()

        # Should be UUID format (36 chars with hyphens)
        assert len(id1) == 36
        assert id1.count("-") == 4

        # Should be unique
        assert id1 != id2


class TestClipDataclass:
    """Tests for Clip dataclass structure."""

    def test_clip_has_all_required_fields(self) -> None:
        """Clip dataclass has all required fields."""
        now = datetime.now(timezone.utc)
        clip = Clip(
            id="clip-1",
            project_id="project-1",
            source_video_id="video-1",
            in_point=0,
            out_point=100,
            timeline_position=50,
            created_at=now,
            updated_at=now,
        )

        assert clip.id == "clip-1"
        assert clip.project_id == "project-1"
        assert clip.source_video_id == "video-1"
        assert clip.in_point == 0
        assert clip.out_point == 100
        assert clip.timeline_position == 50
        assert clip.created_at == now
        assert clip.updated_at == now
