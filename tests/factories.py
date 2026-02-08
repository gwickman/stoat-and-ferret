"""Builder-pattern fixture factories for test data construction.

Provides fluent builders for creating test domain objects (via ``build()``)
and for exercising the full HTTP path (via ``create_via_api()``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from stoat_ferret.db.models import Clip, Project, Video

# ---------------------------------------------------------------------------
# Video factory (simple function — mirrors existing make_test_video)
# ---------------------------------------------------------------------------


def make_test_video(**kwargs: object) -> Video:
    """Create a test Video with sensible defaults.

    Args:
        **kwargs: Override any Video field.

    Returns:
        A Video instance with defaults merged with overrides.
    """
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Video.new_id(),
        "path": f"/videos/{Video.new_id()}.mp4",
        "filename": "test.mp4",
        "duration_frames": 1000,
        "frame_rate_numerator": 24,
        "frame_rate_denominator": 1,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "file_size": 1_000_000,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Video(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Clip config (internal helper for ProjectFactory)
# ---------------------------------------------------------------------------


class _ClipConfig:
    """Internal configuration for a clip to be added to a project."""

    def __init__(
        self,
        *,
        source_video_id: str | None = None,
        in_point: int = 0,
        out_point: int = 100,
        timeline_position: int = 0,
    ) -> None:
        self.source_video_id = source_video_id
        self.in_point = in_point
        self.out_point = out_point
        self.timeline_position = timeline_position


# ---------------------------------------------------------------------------
# ProjectFactory
# ---------------------------------------------------------------------------


class ProjectFactory:
    """Builder for creating test projects with optional clips.

    Supports two output modes:

    * ``build()`` — returns domain objects directly (no HTTP).
    * ``create_via_api(client)`` — POSTs to the API and returns the response dict.

    Example::

        project = (
            ProjectFactory()
            .with_name("My Project")
            .with_clip(in_point=0, out_point=100)
            .build()
        )
    """

    def __init__(self) -> None:
        self._name: str = "Test Project"
        self._output_width: int = 1920
        self._output_height: int = 1080
        self._output_fps: int = 30
        self._clips: list[_ClipConfig] = []

    # -- builder methods (return self for chaining) -------------------------

    def with_name(self, name: str) -> ProjectFactory:
        """Set the project name.

        Args:
            name: Project name.

        Returns:
            Self for fluent chaining.
        """
        self._name = name
        return self

    def with_output(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
    ) -> ProjectFactory:
        """Set output dimensions and/or frame rate.

        Args:
            width: Output width in pixels.
            height: Output height in pixels.
            fps: Output frames per second.

        Returns:
            Self for fluent chaining.
        """
        if width is not None:
            self._output_width = width
        if height is not None:
            self._output_height = height
        if fps is not None:
            self._output_fps = fps
        return self

    def with_clip(
        self,
        *,
        source_video_id: str | None = None,
        in_point: int = 0,
        out_point: int = 100,
        timeline_position: int = 0,
    ) -> ProjectFactory:
        """Add a clip configuration to the project.

        Args:
            source_video_id: ID of source video (auto-generated if None).
            in_point: Clip start frame.
            out_point: Clip end frame.
            timeline_position: Position on timeline in frames.

        Returns:
            Self for fluent chaining.
        """
        self._clips.append(
            _ClipConfig(
                source_video_id=source_video_id,
                in_point=in_point,
                out_point=out_point,
                timeline_position=timeline_position,
            )
        )
        return self

    # -- terminal methods ---------------------------------------------------

    def build(self) -> Project:
        """Build a Project domain object directly (no HTTP).

        Returns:
            A Project dataclass instance with configured values.
        """
        now = datetime.now(timezone.utc)
        return Project(
            id=Project.new_id(),
            name=self._name,
            output_width=self._output_width,
            output_height=self._output_height,
            output_fps=self._output_fps,
            created_at=now,
            updated_at=now,
        )

    def build_with_clips(self) -> tuple[Project, list[Video], list[Clip]]:
        """Build a Project with its clips and required videos.

        For each clip config, creates a Video and a Clip domain object.
        Useful for seeding in-memory repositories in unit tests.

        Returns:
            Tuple of (project, videos, clips).
        """
        now = datetime.now(timezone.utc)
        project = Project(
            id=Project.new_id(),
            name=self._name,
            output_width=self._output_width,
            output_height=self._output_height,
            output_fps=self._output_fps,
            created_at=now,
            updated_at=now,
        )

        videos: list[Video] = []
        clips: list[Clip] = []
        for cfg in self._clips:
            video = make_test_video()
            vid_id = cfg.source_video_id if cfg.source_video_id else video.id
            if cfg.source_video_id:
                video = make_test_video(id=cfg.source_video_id)

            videos.append(video)
            clips.append(
                Clip(
                    id=Clip.new_id(),
                    project_id=project.id,
                    source_video_id=vid_id,
                    in_point=cfg.in_point,
                    out_point=cfg.out_point,
                    timeline_position=cfg.timeline_position,
                    created_at=now,
                    updated_at=now,
                )
            )

        return project, videos, clips

    def create_via_api(self, client: TestClient) -> dict[str, Any]:
        """Create the project (and clips) through the HTTP API.

        Exercises the full HTTP path using the provided TestClient.

        Args:
            client: FastAPI TestClient wired to the test app.

        Returns:
            Dict with ``"project"`` response and a list of ``"clips"`` responses.

        Raises:
            AssertionError: If any API call returns an unexpected status.
        """
        # Create project
        payload: dict[str, Any] = {"name": self._name}
        if self._output_width != 1920:
            payload["output_width"] = self._output_width
        if self._output_height != 1080:
            payload["output_height"] = self._output_height
        if self._output_fps != 30:
            payload["output_fps"] = self._output_fps

        resp = client.post("/api/v1/projects", json=payload)
        assert resp.status_code == 201, f"Failed to create project: {resp.text}"
        project_data = resp.json()
        project_id = project_data["id"]

        # Create clips
        clip_responses: list[dict[str, Any]] = []
        for cfg in self._clips:
            # For create_via_api, the caller must have pre-seeded the video
            # or we need a source_video_id that already exists.
            clip_payload: dict[str, Any] = {
                "source_video_id": cfg.source_video_id or "",
                "in_point": cfg.in_point,
                "out_point": cfg.out_point,
                "timeline_position": cfg.timeline_position,
            }
            clip_resp = client.post(f"/api/v1/projects/{project_id}/clips", json=clip_payload)
            assert clip_resp.status_code == 201, f"Failed to create clip: {clip_resp.text}"
            clip_responses.append(clip_resp.json())

        return {"project": project_data, "clips": clip_responses}
