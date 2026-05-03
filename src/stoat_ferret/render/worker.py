"""Render worker command builder.

Constructs FFmpeg argument lists from RenderJob render_plan JSON
and project media paths resolved via repositories.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from stoat_ferret.db.async_repository import AsyncVideoRepository
from stoat_ferret.db.clip_repository import AsyncClipRepository
from stoat_ferret.render.models import RenderJob

logger = structlog.get_logger(__name__)

# CRF values for x264/x265 quality presets
_QUALITY_CRF: dict[str, str] = {
    "draft": "28",
    "standard": "23",
    "high": "18",
}

# Required top-level fields in render_plan JSON
_REQUIRED_PLAN_FIELDS = ("settings", "total_duration")


class CommandBuildError(Exception):
    """Raised when command building fails due to missing project resources.

    Distinct from ValueError (invalid input) — this signals a missing
    clip or video that could not be resolved from repositories.
    """


async def build_command_for_job(
    job: RenderJob,
    clip_repository: AsyncClipRepository,
    video_repository: AsyncVideoRepository,
) -> list[str]:
    """Build an FFmpeg argument list for a render job.

    Parses render_plan JSON, resolves the project's input media path via
    repository lookups, selects the first renderable segment, and assembles
    a shell-ready FFmpeg command. Does not invoke FFmpeg.

    Args:
        job: The render job containing render_plan JSON and output_path.
        clip_repository: Async clip repository for project clip lookup.
        video_repository: Async video repository for video path lookup.

    Returns:
        A list of strings representing the full FFmpeg command
        (first element is "ffmpeg").

    Raises:
        ValueError: If output_path is empty, render_plan JSON is malformed,
            a required field is missing, or no renderable content exists.
        CommandBuildError: If the project has no clips or the video is not found.
    """
    if not job.output_path:
        raise ValueError("output_path is empty or None")

    # --- Parse render_plan JSON ---
    try:
        plan = json.loads(job.render_plan)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid render_plan JSON: {exc}") from exc

    for field in _REQUIRED_PLAN_FIELDS:
        if field not in plan:
            raise ValueError(f"render_plan missing required field: {field}")

    settings: dict[str, Any] = plan["settings"]
    total_duration: float = plan["total_duration"]
    segments: list[dict[str, Any]] = plan.get("segments", [])

    # --- Resolve input path via repositories ---
    clips = await clip_repository.list_by_project(job.project_id)
    if not clips:
        raise CommandBuildError(f"Project {job.project_id} has no clips in timeline")

    video_id = clips[0].source_video_id
    video = await video_repository.get(video_id)
    if video is None or not video.path:
        raise CommandBuildError(f"Video {video_id} not found for project {job.project_id}")

    input_path = video.path

    # --- Select segment ---
    if segments:
        if len(segments) > 1:
            logger.warning(
                "render_worker.multi_segment_truncated",
                segments_count=len(segments),
                job_id=job.id,
            )
        segment = segments[0]
    else:
        if total_duration <= 0:
            raise ValueError("render_plan has no renderable content")
        segment = {
            "index": 0,
            "timeline_start": 0.0,
            "timeline_end": total_duration,
        }

    timeline_start: float = segment.get("timeline_start", 0.0)
    timeline_end: float = segment.get("timeline_end", total_duration)
    seg_duration = timeline_end - timeline_start

    # --- Extract encoder settings ---
    codec: str = settings.get("codec", "libx264")
    fps: float = settings.get("fps", 30.0)
    width: int | None = settings.get("width")
    height: int | None = settings.get("height")
    quality_preset: str = settings.get("quality_preset", "standard")
    filter_graph: str | None = settings.get("filter_graph")

    # --- Assemble FFmpeg command ---
    cmd: list[str] = ["ffmpeg", "-i", input_path]

    # Segment timing
    cmd.extend(["-ss", str(timeline_start), "-t", str(seg_duration)])

    # Video filter: use explicit filter_graph if provided, else scale from dimensions
    if filter_graph:
        cmd.extend(["-vf", filter_graph])
    elif width and height:
        cmd.extend(["-vf", f"scale={width}:{height}"])

    # Video codec
    cmd.extend(["-c:v", codec])

    # Quality via CRF for software x264/x265
    if codec in ("libx264", "libx265") and quality_preset in _QUALITY_CRF:
        cmd.extend(["-crf", _QUALITY_CRF[quality_preset]])

    # Frame rate
    cmd.extend(["-r", str(fps)])

    # Output path (must be last)
    cmd.append(job.output_path)

    return cmd
