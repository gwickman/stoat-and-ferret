"""Render service orchestrating job lifecycle.

Coordinates pre-flight checks, queue management, executor dispatch,
progress broadcasting via WebSocket, retry logic, and cleanup.
Includes dual-threshold throttling for progress and frame events.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import structlog

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.metrics import (
    render_disk_usage_bytes,
    render_duration_seconds,
    render_jobs_total,
)
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import QueueFullError, RenderQueue
from stoat_ferret.render.render_repository import AsyncRenderRepository

try:
    from stoat_ferret_core import (
        RenderSettings,
        estimate_eta,
        estimate_output_size,
        validate_render_settings,
    )

    _HAS_RUST_BINDINGS = True
except ImportError:
    _HAS_RUST_BINDINGS = False

logger = structlog.get_logger(__name__)


class PreflightError(Exception):
    """Raised when pre-flight checks fail before queuing a render job.

    Attributes:
        reason: Human-readable description of the failure.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class RenderUnavailableError(Exception):
    """Raised when the render subsystem cannot accept requests.

    Used for shutdown-in-progress and FFmpeg-unavailable scenarios,
    both of which should result in HTTP 503 responses.

    Attributes:
        reason: Human-readable description of why rendering is unavailable.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class RenderService:
    """Orchestrates the full render job lifecycle.

    Handles pre-flight validation, queue coordination, executor dispatch,
    progress broadcasting via WebSocket, retry on transient failure, and
    cleanup on completion or failure.

    Args:
        repository: Async render job repository for persistence.
        queue: Render queue for job scheduling.
        executor: Render executor for FFmpeg process management.
        checkpoint_manager: Checkpoint manager for crash recovery.
        connection_manager: WebSocket connection manager for broadcasting.
        settings: Application settings.
    """

    # Throttle constants
    THROTTLE_INTERVAL: float = 0.5  # seconds between broadcasts
    THROTTLE_PROGRESS_DELTA: float = 0.05  # 5% progress delta

    def __init__(
        self,
        *,
        repository: AsyncRenderRepository,
        queue: RenderQueue,
        executor: RenderExecutor,
        checkpoint_manager: RenderCheckpointManager,
        connection_manager: ConnectionManager,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._queue = queue
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager
        self._ws = connection_manager
        self._max_retries = settings.render_retry_count
        self._shutting_down = False
        self._ffmpeg_available = shutil.which("ffmpeg") is not None
        # Per-job-per-event-type throttle state: (job_id, event_type) -> last_broadcast_time
        self._last_broadcast_time: dict[tuple[str, str], float] = {}
        # Per-job last broadcast progress for delta throttling
        self._last_broadcast_progress: dict[str, float] = {}

    def initiate_shutdown(self) -> None:
        """Set the shutdown flag to reject new render requests.

        Once called, all subsequent ``submit_job`` calls will raise
        ``RenderUnavailableError`` with a "shutting down" message.
        """
        self._shutting_down = True
        logger.info("render_service.shutdown_initiated")

    @property
    def is_shutting_down(self) -> bool:
        """Whether the service is in shutdown mode.

        Returns:
            True if shutdown has been initiated.
        """
        return self._shutting_down

    @property
    def ffmpeg_available(self) -> bool:
        """Whether FFmpeg is available on this system.

        Returns:
            True if FFmpeg was found in PATH at service creation time.
        """
        return self._ffmpeg_available

    async def submit_job(
        self,
        *,
        project_id: str,
        output_path: str,
        output_format: OutputFormat,
        quality_preset: QualityPreset,
        render_plan_json: str,
    ) -> RenderJob:
        """Submit a new render job after pre-flight checks.

        Validates render settings via Rust bindings, checks disk space,
        and verifies queue capacity before creating and enqueuing the job.

        Args:
            project_id: The project to render.
            output_path: Output file path for rendered video.
            output_format: Container format.
            quality_preset: Quality preset.
            render_plan_json: Serialized RenderPlan JSON string.

        Returns:
            The created and enqueued render job.

        Raises:
            PreflightError: If any pre-flight check fails.
            RenderUnavailableError: If shutting down or FFmpeg unavailable.
        """
        if self._shutting_down:
            raise RenderUnavailableError("Render service is shutting down")

        if not self._ffmpeg_available:
            raise RenderUnavailableError(
                "FFmpeg is not installed — render operations are unavailable"
            )

        log = logger.bind(project_id=project_id, output_path=output_path)

        # Pre-flight: validate settings via Rust
        self._validate_settings(render_plan_json)

        # Pre-flight: check disk space
        self._check_disk_space(output_path, render_plan_json, quality_preset)

        # Pre-flight: check queue capacity (fail-fast before creating the job)
        queue_depth = await self._queue.get_queue_depth()
        if queue_depth >= self._queue._max_depth:
            raise PreflightError(
                f"Render queue at capacity: {queue_depth}/{self._queue._max_depth}"
            )

        # Create and enqueue
        job = RenderJob.create(
            project_id=project_id,
            output_path=output_path,
            output_format=output_format,
            quality_preset=quality_preset,
            render_plan=render_plan_json,
        )

        log.info("render_job.created", job_id=job.id)

        try:
            job = await self._queue.enqueue(job)
        except QueueFullError as exc:
            raise PreflightError(str(exc)) from exc

        log.info("render_job.queued", job_id=job.id)

        await self._broadcast_event(EventType.RENDER_QUEUED, job)
        await self._broadcast_queue_status()
        await self._broadcast_event(EventType.RENDER_STARTED, job)
        return job

    async def run_job(self, job: RenderJob, command: list[str]) -> None:
        """Execute a render job with progress tracking and retry logic.

        Dequeues the job, runs it via the executor with progress broadcasting,
        and handles completion, failure (with retry), or cancellation.

        Args:
            job: The render job to execute.
            command: Full FFmpeg command arguments.
        """
        job_id = job.id
        log = logger.bind(job_id=job_id)

        # Parse total duration for progress calculation
        total_duration_us = self._extract_duration_us(job.render_plan)

        # Track milestones already logged to avoid duplicates
        logged_milestones: set[int] = set()
        total_duration_s = total_duration_us / 1_000_000 if total_duration_us > 0 else 0.0

        async def progress_callback(jid: str, progress: float, elapsed_seconds: float) -> None:
            # Log progress milestones at 25%, 50%, 75%, 100%
            pct = int(progress * 100)
            for milestone in (25, 50, 75, 100):
                if pct >= milestone and milestone not in logged_milestones:
                    logged_milestones.add(milestone)
                    log.info(
                        "render_job.progress_milestone",
                        milestone_pct=milestone,
                        progress=round(progress, 4),
                    )

            # Compute ETA via Rust binding
            eta_seconds: float | None = None
            if _HAS_RUST_BINDINGS:
                eta_seconds = estimate_eta(elapsed_seconds, progress)

            # Compute speed ratio
            speed_ratio: float | None = None
            if elapsed_seconds > 0 and total_duration_s > 0 and progress > 0:
                speed_ratio = (total_duration_s * progress) / elapsed_seconds

            await self._repo.update_progress(jid, progress)
            await self._broadcast_throttled_progress(
                jid, progress, eta_seconds=eta_seconds, speed_ratio=speed_ratio
            )
            await self._broadcast_throttled_frame(jid, progress)

        # Wire progress callback into executor
        self._executor._progress_callback = progress_callback

        log.info("render_job.started")
        render_start = time.monotonic()
        success = await self._executor.execute(job, command, total_duration_us=total_duration_us)

        render_elapsed = time.monotonic() - render_start

        if success:
            await self._complete_job(job, render_elapsed)
        else:
            # Check if job was cancelled
            current = await self._repo.get(job_id)
            if current and current.status == RenderStatus.CANCELLED:
                log.info("render_job.cancelled")
                return

            await self._handle_failure(job, "FFmpeg process failed")

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a render job.

        Cancels the executor process if running, updates status to cancelled,
        and broadcasts the RENDER_CANCELLED event.

        Args:
            job_id: The render job ID to cancel.

        Returns:
            True if the job was found and cancelled, False otherwise.
        """
        log = logger.bind(job_id=job_id)
        job = await self._repo.get(job_id)
        if job is None:
            log.warning("render_service.cancel_not_found")
            return False

        if job.status not in (RenderStatus.QUEUED, RenderStatus.RUNNING):
            log.info(
                "render_service.cancel_not_cancellable",
                status=job.status.value,
            )
            return False

        # Cancel executor process if running
        if job.status == RenderStatus.RUNNING:
            await self._executor.cancel(job_id)

        await self._repo.update_status(job_id, RenderStatus.CANCELLED)
        render_jobs_total.labels(status="cancelled").inc()
        log.info("render_job.cancelled")
        await self._broadcast_event(EventType.RENDER_CANCELLED, job)
        await self._broadcast_queue_status()
        self._clear_throttle_state(job_id)
        return True

    async def recover(self) -> list[tuple[str, int]]:
        """Recover from server restart.

        Delegates to queue recovery (marks running jobs as failed)
        and checkpoint recovery (finds resume points).

        Returns:
            List of (job_id, next_segment_index) pairs from checkpoint recovery.
        """
        await self._queue.recover()
        resume_points = await self._checkpoint_manager.recover()
        logger.info(
            "render_service.recovery_complete",
            resume_points=len(resume_points),
        )
        return resume_points

    async def _complete_job(self, job: RenderJob, elapsed_seconds: float = 0.0) -> None:
        """Mark a job as completed, broadcast event, update metrics, and clean up.

        Args:
            job: The render job that completed successfully.
            elapsed_seconds: Wall-clock render time in seconds.
        """
        await self._repo.update_status(job.id, RenderStatus.COMPLETED)
        render_jobs_total.labels(status="completed").inc()
        if elapsed_seconds > 0:
            render_duration_seconds.observe(elapsed_seconds)
        self._update_disk_usage(job.output_path)
        logger.info(
            "render_job.completed",
            job_id=job.id,
            elapsed_seconds=round(elapsed_seconds, 2),
        )
        await self._broadcast_event(EventType.RENDER_COMPLETED, job)
        await self._broadcast_queue_status()
        self._clear_throttle_state(job.id)
        await self._cleanup(job.id)

    async def _handle_failure(self, job: RenderJob, error_message: str) -> None:
        """Handle a job failure with retry logic.

        If the job has not exceeded the max retry count, requeue it.
        Otherwise, mark it as permanently failed.

        Args:
            job: The failed render job.
            error_message: Description of the failure.
        """
        log = logger.bind(job_id=job.id)

        # Reload current state from repo
        current = await self._repo.get(job.id)
        if current is None:
            log.error("render_service.failure_job_not_found")
            return

        if current.retry_count < self._max_retries:
            # Transition: running -> failed -> queued (retry)
            await self._repo.update_status(job.id, RenderStatus.FAILED, error_message=error_message)
            await self._repo.update_status(job.id, RenderStatus.QUEUED)
            log.info(
                "render_service.job_retrying",
                retry_count=current.retry_count + 1,
                max_retries=self._max_retries,
            )
        else:
            await self._repo.update_status(job.id, RenderStatus.FAILED, error_message=error_message)
            render_jobs_total.labels(status="failed").inc()
            log.error(
                "render_job.failed",
                retry_count=current.retry_count,
                error=error_message,
            )
            await self._broadcast_event(EventType.RENDER_FAILED, job)
            await self._broadcast_queue_status()
            self._clear_throttle_state(job.id)
            await self._cleanup(job.id)

    async def _cleanup(self, job_id: str) -> None:
        """Clean up temp files and stale checkpoints for a job.

        Args:
            job_id: The render job ID to clean up.
        """
        self._executor._cleanup_temp_files(job_id)
        await self._checkpoint_manager.cleanup_stale([job_id])
        logger.debug("render_service.cleanup_complete", job_id=job_id)

    async def _broadcast_event(self, event_type: EventType, job: RenderJob) -> None:
        """Broadcast a render lifecycle event via WebSocket.

        Args:
            event_type: The event type to broadcast.
            job: The render job associated with the event.
        """
        await self._ws.broadcast(
            build_event(
                event_type,
                {
                    "job_id": job.id,
                    "project_id": job.project_id,
                    "status": job.status.value,
                },
            )
        )

    def _should_throttle(self, job_id: str, event_type: EventType) -> bool:
        """Check if an event should be throttled based on time interval.

        Args:
            job_id: The render job ID.
            event_type: The event type to check.

        Returns:
            True if the event should be suppressed (throttled).
        """
        key = (job_id, event_type.value)
        now = time.monotonic()
        last = self._last_broadcast_time.get(key, 0.0)
        if now - last < self.THROTTLE_INTERVAL:
            return True
        self._last_broadcast_time[key] = now
        return False

    async def _broadcast_throttled_progress(
        self,
        job_id: str,
        progress: float,
        *,
        eta_seconds: float | None = None,
        speed_ratio: float | None = None,
    ) -> None:
        """Broadcast render.progress with dual-threshold throttling.

        Applies both time interval (0.5s) and progress delta (5%) thresholds.
        Final progress (1.0) is always sent.

        Args:
            job_id: The render job ID.
            progress: Current progress value 0.0-1.0.
            eta_seconds: Estimated time remaining in seconds, or None.
            speed_ratio: Render speed relative to real-time, or None.
        """
        is_final = progress >= 1.0
        last_progress = self._last_broadcast_progress.get(job_id, 0.0)
        progress_delta = progress - last_progress

        if not is_final:
            if self._should_throttle(job_id, EventType.RENDER_PROGRESS):
                return
            if progress_delta < self.THROTTLE_PROGRESS_DELTA:
                # Reset the time stamp since we didn't actually broadcast
                key = (job_id, EventType.RENDER_PROGRESS.value)
                self._last_broadcast_time.pop(key, None)
                return

        self._last_broadcast_progress[job_id] = progress
        # Update time stamp for final progress too
        self._last_broadcast_time[(job_id, EventType.RENDER_PROGRESS.value)] = time.monotonic()
        await self._ws.broadcast(
            build_event(
                EventType.RENDER_PROGRESS,
                {
                    "job_id": job_id,
                    "progress": progress,
                    "eta_seconds": eta_seconds,
                    "speed_ratio": speed_ratio,
                },
            )
        )

    async def _broadcast_throttled_frame(self, job_id: str, progress: float) -> None:
        """Broadcast render.frame_available with throttling.

        Throttled to max 2/sec. Includes a 540p JPEG frame URL.

        Args:
            job_id: The render job ID.
            progress: Current progress value 0.0-1.0.
        """
        if self._should_throttle(job_id, EventType.RENDER_FRAME_AVAILABLE):
            return

        frame_url = f"/api/v1/render/{job_id}/frame_preview.jpg"
        await self._ws.broadcast(
            build_event(
                EventType.RENDER_FRAME_AVAILABLE,
                {
                    "job_id": job_id,
                    "frame_url": frame_url,
                    "resolution": "540p",
                    "progress": progress,
                },
            )
        )

    async def _broadcast_queue_status(self) -> None:
        """Broadcast render.queue_status event with current queue snapshot."""
        active_count = await self._queue.get_active_count()
        pending_count = await self._queue.get_queue_depth()

        await self._ws.broadcast(
            build_event(
                EventType.RENDER_QUEUE_STATUS,
                {
                    "active_count": active_count,
                    "pending_count": pending_count,
                    "max_concurrent": self._queue._max_concurrent,
                    "max_queue_depth": self._queue._max_depth,
                },
            )
        )

    def _clear_throttle_state(self, job_id: str) -> None:
        """Remove throttle state for a completed/failed/cancelled job.

        Args:
            job_id: The render job ID to clean up.
        """
        keys_to_remove = [k for k in self._last_broadcast_time if k[0] == job_id]
        for k in keys_to_remove:
            del self._last_broadcast_time[k]
        self._last_broadcast_progress.pop(job_id, None)

    def _update_disk_usage(self, output_path: str) -> None:
        """Update the render disk usage metric from the output directory.

        Args:
            output_path: Output file path whose parent directory is measured.
        """
        try:
            output_dir = Path(output_path).parent
            if output_dir.exists():
                usage = shutil.disk_usage(str(output_dir))
                render_disk_usage_bytes.set(usage.used)
        except OSError:
            logger.debug("render_service.disk_usage_update_failed", exc_info=True)

    def _validate_settings(self, render_plan_json: str) -> None:
        """Validate render settings via Rust bindings.

        Args:
            render_plan_json: Serialized RenderPlan JSON containing settings.

        Raises:
            PreflightError: If settings are invalid.
        """
        if not _HAS_RUST_BINDINGS:
            return

        try:
            plan_data = json.loads(render_plan_json)
            settings_data = plan_data.get("settings")
            if settings_data is None:
                return
            settings_obj = RenderSettings(
                output_format=settings_data.get("output_format", "mp4"),
                width=settings_data.get("width", 1920),
                height=settings_data.get("height", 1080),
                codec=settings_data.get("codec", "libx264"),
                quality_preset=settings_data.get("quality_preset", "standard"),
                fps=settings_data.get("fps", 30.0),
            )
            validate_render_settings(settings_obj)
        except (json.JSONDecodeError, KeyError) as exc:
            raise PreflightError("Invalid render plan JSON") from exc
        except (ValueError, TypeError) as exc:
            raise PreflightError(f"Invalid render settings: {exc}") from exc

    def _check_disk_space(
        self,
        output_path: str,
        render_plan_json: str,
        quality_preset: QualityPreset,
    ) -> None:
        """Check that sufficient disk space is available.

        Uses the Rust estimate_output_size() binding to estimate the output
        file size, then checks against available disk space.

        Args:
            output_path: Output file path for rendered video.
            render_plan_json: Serialized RenderPlan JSON.
            quality_preset: Quality preset for size estimation.

        Raises:
            PreflightError: If insufficient disk space.
        """
        if not _HAS_RUST_BINDINGS:
            return

        try:
            plan_data = json.loads(render_plan_json)
            duration = plan_data.get("total_duration", 0.0)
            settings_data = plan_data.get("settings", {})
            codec = settings_data.get("codec", "libx264")

            estimated_bytes = estimate_output_size(duration, codec, quality_preset.value)

            output_dir = Path(output_path).parent
            if output_dir.exists():
                usage = shutil.disk_usage(str(output_dir))
                if usage.free < estimated_bytes:
                    raise PreflightError(
                        f"Insufficient disk space: need {estimated_bytes} bytes, "
                        f"have {usage.free} bytes free"
                    )
        except PreflightError:
            raise
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.warning(
                "render_service.disk_check_skipped",
                reason=str(exc),
            )

    @staticmethod
    def _extract_duration_us(render_plan_json: str) -> int:
        """Extract total duration in microseconds from render plan JSON.

        Args:
            render_plan_json: Serialized RenderPlan JSON.

        Returns:
            Total duration in microseconds, or 0 if not available.
        """
        try:
            plan_data = json.loads(render_plan_json)
            duration_seconds = plan_data.get("total_duration", 0.0)
            return int(duration_seconds * 1_000_000)
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0
