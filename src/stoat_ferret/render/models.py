"""Render job data models for batch video rendering.

Defines RenderJob, RenderStatus, OutputFormat, and QualityPreset types
with state machine enforcement for job lifecycle transitions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class RenderStatus(str, Enum):
    """Status of a render job through its lifecycle.

    Transitions: queued -> running -> completed|failed|cancelled;
    failed -> queued (retry); queued -> cancelled; running -> cancelled.
    cancelled is terminal — no transitions from cancelled.
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputFormat(str, Enum):
    """Supported output container formats for rendered video."""

    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"
    MKV = "mkv"


class QualityPreset(str, Enum):
    """Quality presets controlling encoder settings."""

    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"


# Valid status transitions: from -> set of allowed targets
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "failed": {"queued"},
    "completed": set(),
    "cancelled": set(),
}


def validate_render_transition(current: str, new: str) -> None:
    """Validate that a render status transition is allowed.

    Args:
        current: Current status value.
        new: Proposed new status value.

    Raises:
        ValueError: If the transition is not allowed.
    """
    allowed = _VALID_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValueError(
            f"Invalid status transition: {current!r} -> {new!r}. "
            f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
        )


@dataclass
class RenderJob:
    """A render job representing a single video render operation.

    Attributes:
        id: Unique job identifier (UUID).
        project_id: The project to render.
        status: Current job status following the state machine.
        output_path: Output file path for rendered video.
        output_format: Container format (mp4, webm, mov, mkv).
        quality_preset: Quality preset (draft, standard, high).
        render_plan: Serialized RenderPlan JSON string.
        progress: Render progress 0.0-1.0.
        error_message: Error message when status is failed.
        retry_count: Number of retry attempts.
        created_at: When this job was created.
        updated_at: When this job was last modified.
        completed_at: When this job reached a terminal state.
    """

    id: str
    project_id: str
    status: RenderStatus
    output_path: str
    output_format: OutputFormat
    quality_preset: QualityPreset
    render_plan: str
    progress: float
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @staticmethod
    def create(
        *,
        project_id: str,
        output_path: str,
        output_format: OutputFormat,
        quality_preset: QualityPreset,
        render_plan: str,
    ) -> RenderJob:
        """Create a new render job in queued status.

        Args:
            project_id: The project to render.
            output_path: Output file path for rendered video.
            output_format: Container format.
            quality_preset: Quality preset.
            render_plan: Serialized RenderPlan JSON.

        Returns:
            A new RenderJob with queued status.
        """
        now = datetime.now(timezone.utc)
        return RenderJob(
            id=str(uuid.uuid4()),
            project_id=project_id,
            status=RenderStatus.QUEUED,
            output_path=output_path,
            output_format=output_format,
            quality_preset=quality_preset,
            render_plan=render_plan,
            progress=0.0,
            error_message=None,
            retry_count=0,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )

    def update_progress(self, progress: float) -> None:
        """Update the render progress.

        Args:
            progress: New progress value, must be in [0.0, 1.0].

        Raises:
            ValueError: If progress is out of bounds.
        """
        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {progress}")
        self.progress = progress
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        """Mark the job as completed.

        Raises:
            ValueError: If the current status cannot transition to completed.
        """
        validate_render_transition(self.status.value, RenderStatus.COMPLETED.value)
        now = datetime.now(timezone.utc)
        self.status = RenderStatus.COMPLETED
        self.progress = 1.0
        self.updated_at = now
        self.completed_at = now

    def fail(self, error_message: str) -> None:
        """Mark the job as failed with an error message.

        Args:
            error_message: Description of the failure.

        Raises:
            ValueError: If the current status cannot transition to failed.
        """
        validate_render_transition(self.status.value, RenderStatus.FAILED.value)
        now = datetime.now(timezone.utc)
        self.status = RenderStatus.FAILED
        self.error_message = error_message
        self.updated_at = now
        self.completed_at = now

    def retry(self) -> None:
        """Retry the job by resetting to queued status.

        Raises:
            ValueError: If the current status cannot transition to queued.
        """
        validate_render_transition(self.status.value, RenderStatus.QUEUED.value)
        self.status = RenderStatus.QUEUED
        self.progress = 0.0
        self.error_message = None
        self.retry_count += 1
        self.updated_at = datetime.now(timezone.utc)
        self.completed_at = None

    def cancel(self) -> None:
        """Cancel the job.

        Raises:
            ValueError: If the current status cannot transition to cancelled.
        """
        validate_render_transition(self.status.value, RenderStatus.CANCELLED.value)
        now = datetime.now(timezone.utc)
        self.status = RenderStatus.CANCELLED
        self.error_message = None
        self.updated_at = now
        self.completed_at = now
