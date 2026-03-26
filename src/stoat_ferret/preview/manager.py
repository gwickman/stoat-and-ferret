"""Preview session manager with lifecycle coordination.

Orchestrates session lifecycle by coordinating HLS generator, preview
repository, and WebSocket event broadcasting. Enforces concurrent session
limits, manages state transitions, handles seek-triggered regeneration
with proper cancellation, and cleans up expired sessions.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from stoat_ferret.api.middleware.correlation import get_correlation_id
from stoat_ferret.api.settings import get_settings
from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.db.models import (
    PreviewQuality,
    PreviewSession,
    PreviewStatus,
    validate_preview_transition,
)
from stoat_ferret.preview.metrics import (
    preview_errors_total,
    preview_generation_seconds,
    preview_seek_latency_seconds,
    preview_sessions_active,
    preview_sessions_total,
)

if TYPE_CHECKING:
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.db.preview_repository import AsyncPreviewRepository
    from stoat_ferret.preview.hls_generator import HLSGenerator
    from stoat_ferret_core import FilterGraph

logger = structlog.get_logger(__name__)


class PreviewManagerError(Exception):
    """Base error for preview manager operations."""


class SessionLimitError(PreviewManagerError):
    """Raised when the concurrent session limit is reached."""


class SessionNotFoundError(PreviewManagerError):
    """Raised when a session is not found."""


class SessionExpiredError(PreviewManagerError):
    """Raised when accessing an expired session."""


class InvalidTransitionError(PreviewManagerError):
    """Raised when an invalid state transition is attempted."""


class PreviewManager:
    """Coordinate preview session lifecycle.

    Manages the full lifecycle of preview sessions: creation, HLS generation,
    seek regeneration, stop/cleanup, and expiry detection. Broadcasts WebSocket
    events for each state transition.

    Args:
        repository: Async preview session repository.
        generator: HLS segment generator.
        ws_manager: WebSocket connection manager for broadcasting events.
        max_sessions: Maximum concurrent sessions. Defaults to settings value.
        session_ttl_seconds: Session TTL in seconds. Defaults to settings value.
        output_base_dir: Base directory for preview output. Defaults to settings value.
    """

    def __init__(
        self,
        *,
        repository: AsyncPreviewRepository,
        generator: HLSGenerator,
        ws_manager: ConnectionManager,
        max_sessions: int | None = None,
        session_ttl_seconds: int | None = None,
        output_base_dir: str | None = None,
    ) -> None:
        settings = get_settings()
        self._repository = repository
        self._generator = generator
        self._ws_manager = ws_manager
        self._max_sessions = (
            max_sessions if max_sessions is not None else settings.preview_cache_max_sessions
        )
        self._session_ttl = (
            session_ttl_seconds
            if session_ttl_seconds is not None
            else settings.preview_session_ttl_seconds
        )
        if output_base_dir is None:
            output_base_dir = settings.preview_output_dir
        self._output_base_dir = Path(output_base_dir)

        # Per-session locks for seek serialization
        self._session_locks: dict[str, asyncio.Lock] = {}
        # Per-session cancel events for cooperative cancellation
        self._cancel_events: dict[str, asyncio.Event] = {}
        # Track active generation tasks
        self._generation_tasks: dict[str, asyncio.Task[None]] = {}

    def _session_dir(self, session_id: str) -> Path:
        """Get the output directory for a session.

        Args:
            session_id: Preview session identifier.

        Returns:
            Path to the session's output directory.
        """
        return self._output_base_dir / session_id

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create a per-session lock.

        Args:
            session_id: Preview session identifier.

        Returns:
            asyncio.Lock for the session.
        """
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    # Minimum interval between progress broadcasts (seconds)
    _PROGRESS_THROTTLE_SECONDS = 0.5

    def _make_progress_callback(self, session_id: str) -> Callable[[float], Awaitable[None]]:
        """Create a throttled progress callback that broadcasts via WebSocket.

        Returns an async callback that broadcasts JOB_PROGRESS events at most
        once per _PROGRESS_THROTTLE_SECONDS interval. Progress value 1.0 is
        always broadcast regardless of throttling.

        Args:
            session_id: The session ID to include in event payloads.

        Returns:
            Async callback accepting a progress float (0.0-1.0).
        """
        last_broadcast_time = 0.0

        async def _on_progress(progress: float) -> None:
            nonlocal last_broadcast_time
            now = time.monotonic()
            # Always broadcast final progress; throttle intermediate updates
            if progress < 1.0 and (now - last_broadcast_time) < self._PROGRESS_THROTTLE_SECONDS:
                return
            last_broadcast_time = now
            await self._broadcast_event(
                EventType.JOB_PROGRESS,
                session_id,
                progress=progress,
                status="generating",
            )

        return _on_progress

    async def _broadcast_event(
        self, event_type: EventType, session_id: str, **extra: object
    ) -> None:
        """Broadcast a WebSocket event for a session.

        Args:
            event_type: The event type to broadcast.
            session_id: The session ID to include in the payload.
            **extra: Additional payload fields.
        """
        payload: dict[str, object] = {"session_id": session_id, **extra}
        event = build_event(event_type, payload)
        await self._ws_manager.broadcast(event)

    async def _transition(self, session: PreviewSession, new_status: PreviewStatus) -> None:
        """Validate and apply a state transition, updating the repository.

        Args:
            session: The session to transition.
            new_status: The target status.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        try:
            validate_preview_transition(session.status.value, new_status.value)
        except ValueError as e:
            raise InvalidTransitionError(str(e)) from e
        session.status = new_status
        session.updated_at = datetime.now(timezone.utc)
        await self._repository.update(session)

    async def _check_expired(self, session: PreviewSession) -> None:
        """Check if a session is expired and clean up if so.

        Args:
            session: The session to check.

        Raises:
            SessionExpiredError: If the session has expired.
        """
        if datetime.now(timezone.utc) >= session.expires_at:
            await self._cleanup_session(session)
            raise SessionExpiredError(
                f"Session {session.id} expired at {session.expires_at.isoformat()}"
            )

    async def _cleanup_session(self, session: PreviewSession) -> None:
        """Clean up a session: cancel generation, remove files, update status.

        Args:
            session: The session to clean up.
        """
        preview_sessions_active.dec()

        # Cancel active generation
        cancel_event = self._cancel_events.get(session.id)
        if cancel_event is not None:
            cancel_event.set()

        task = self._generation_tasks.pop(session.id, None)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task

        # Remove session directory
        session_dir = self._session_dir(session.id)
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
            logger.debug("preview_session_dir_cleaned", session_id=session.id)

        # Transition to expired if possible
        if session.status != PreviewStatus.EXPIRED:
            with contextlib.suppress(InvalidTransitionError):
                await self._transition(session, PreviewStatus.EXPIRED)

        # Clean up tracking state
        self._session_locks.pop(session.id, None)
        self._cancel_events.pop(session.id, None)

    async def start(
        self,
        *,
        project_id: str,
        input_path: str,
        filter_graph: FilterGraph | None = None,
        duration_us: int | None = None,
        quality_level: PreviewQuality = PreviewQuality.MEDIUM,
    ) -> PreviewSession:
        """Start a new preview session.

        Creates the session record, enforces the concurrent session limit,
        and starts HLS generation in the background.

        Args:
            project_id: The project this preview belongs to.
            input_path: Path to the source media file.
            filter_graph: Optional FilterGraph for preview simplification.
            duration_us: Total duration in microseconds for progress.
            quality_level: Quality level for the preview.

        Returns:
            The newly created PreviewSession.

        Raises:
            SessionLimitError: If the concurrent session limit is reached.
        """
        # Enforce concurrent session limit
        count = await self._repository.count()
        if count >= self._max_sessions:
            raise SessionLimitError(
                f"Concurrent session limit reached ({self._max_sessions}). "
                "Stop an existing session before starting a new one."
            )

        now = datetime.now(timezone.utc)
        session = PreviewSession(
            id=PreviewSession.new_id(),
            project_id=project_id,
            status=PreviewStatus.INITIALIZING,
            quality_level=quality_level,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=self._session_ttl),
        )
        await self._repository.add(session)

        logger.info(
            "preview_session_created",
            session_id=session.id,
            project_id=project_id,
            quality=quality_level.value,
            correlation_id=get_correlation_id(),
        )

        # Record metrics
        preview_sessions_total.labels(quality=quality_level.value).inc()
        preview_sessions_active.inc()

        # Transition to generating and broadcast
        await self._transition(session, PreviewStatus.GENERATING)
        await self._broadcast_event(EventType.PREVIEW_GENERATING, session.id)

        logger.info(
            "preview_generation_started",
            session_id=session.id,
            input_path=input_path,
            correlation_id=get_correlation_id(),
        )

        # Set up cancellation
        cancel_event = asyncio.Event()
        self._cancel_events[session.id] = cancel_event

        # Start generation task
        task = asyncio.create_task(
            self._run_generation(
                session_id=session.id,
                input_path=input_path,
                filter_graph=filter_graph,
                duration_us=duration_us,
                cancel_event=cancel_event,
            )
        )
        self._generation_tasks[session.id] = task

        return session

    async def _run_generation(
        self,
        *,
        session_id: str,
        input_path: str,
        filter_graph: FilterGraph | None,
        duration_us: int | None,
        cancel_event: asyncio.Event,
    ) -> None:
        """Run HLS generation and update session state on completion.

        Args:
            session_id: The session to generate for.
            input_path: Path to the source media file.
            filter_graph: Optional FilterGraph object.
            duration_us: Duration in microseconds for progress.
            cancel_event: Event for cooperative cancellation.
        """
        gen_start = time.monotonic()
        try:
            progress_callback = self._make_progress_callback(session_id)
            output_dir = await self._generator.generate(
                session_id=session_id,
                input_path=input_path,
                filter_graph=filter_graph,
                duration_us=duration_us,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )

            # Update session to ready
            session = await self._repository.get(session_id)
            if session is None:
                return

            elapsed = time.monotonic() - gen_start
            preview_generation_seconds.labels(
                quality=session.quality_level.value,
            ).observe(elapsed)

            segment_count = sum(1 for f in output_dir.iterdir() if f.suffix == ".ts")
            logger.info(
                "preview_segment_generated",
                session_id=session_id,
                segment_count=segment_count,
                duration_seconds=round(elapsed, 2),
                correlation_id=get_correlation_id(),
            )

            manifest_path = str(output_dir / "manifest.m3u8")
            session.manifest_path = manifest_path
            await self._transition(session, PreviewStatus.READY)
            await self._broadcast_event(EventType.PREVIEW_READY, session.id)

            logger.info(
                "preview_session_ready",
                session_id=session_id,
                correlation_id=get_correlation_id(),
            )

        except Exception as exc:
            # Don't set error on cancelled sessions
            if cancel_event.is_set():
                return

            preview_errors_total.labels(error_type="ffmpeg_error").inc()

            session = await self._repository.get(session_id)
            if session is None:
                return

            error_msg = str(exc)[:500]
            session.error_message = error_msg
            with contextlib.suppress(InvalidTransitionError):
                await self._transition(session, PreviewStatus.ERROR)
            await self._broadcast_event(EventType.PREVIEW_ERROR, session.id, error=error_msg)
            logger.error(
                "preview_generation_failed",
                session_id=session_id,
                error=error_msg,
                correlation_id=get_correlation_id(),
            )
        finally:
            self._generation_tasks.pop(session_id, None)
            self._cancel_events.pop(session_id, None)

    async def seek(
        self,
        session_id: str,
        *,
        input_path: str,
        filter_graph: FilterGraph | None = None,
        duration_us: int | None = None,
    ) -> PreviewSession:
        """Seek to a new position, regenerating HLS segments.

        Acquires the per-session lock to serialize concurrent seek requests.
        Cancels active generation, cleans up old segments, and starts new
        generation from the requested position.

        Args:
            session_id: The session to seek.
            input_path: Path to the source media file.
            filter_graph: Optional FilterGraph for preview simplification.
            duration_us: Duration in microseconds for progress.

        Returns:
            The updated PreviewSession.

        Raises:
            SessionNotFoundError: If the session is not found.
            SessionExpiredError: If the session has expired.
            InvalidTransitionError: If the session is not in a seekable state.
        """
        logger.info(
            "preview_seek_requested",
            session_id=session_id,
            correlation_id=get_correlation_id(),
        )

        lock = self._get_lock(session_id)
        async with lock:
            session = await self._repository.get(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")

            await self._check_expired(session)

            # Cancel active generation if any
            cancel_event = self._cancel_events.get(session_id)
            if cancel_event is not None:
                cancel_event.set()

            task = self._generation_tasks.pop(session_id, None)
            if task is not None and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task

            # Re-fetch session after potential cancellation updates
            session = await self._repository.get(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")

            # Clean up old segments
            session_dir = self._session_dir(session_id)
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)

            # If still in generating state (cancelled mid-generation),
            # transition to ready first since generating -> seeking is invalid
            if session.status == PreviewStatus.GENERATING:
                await self._transition(session, PreviewStatus.READY)

            # Transition to seeking
            await self._transition(session, PreviewStatus.SEEKING)
            await self._broadcast_event(EventType.PREVIEW_SEEKING, session.id)

            # Re-fetch after transition
            session = await self._repository.get(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")

            # Set up new cancellation
            new_cancel = asyncio.Event()
            self._cancel_events[session_id] = new_cancel

            # Start new generation
            gen_task = asyncio.create_task(
                self._run_seek_generation(
                    session_id=session_id,
                    input_path=input_path,
                    filter_graph=filter_graph,
                    duration_us=duration_us,
                    cancel_event=new_cancel,
                )
            )
            self._generation_tasks[session_id] = gen_task

            return session

    async def _run_seek_generation(
        self,
        *,
        session_id: str,
        input_path: str,
        filter_graph: FilterGraph | None,
        duration_us: int | None,
        cancel_event: asyncio.Event,
    ) -> None:
        """Run HLS generation after a seek and transition to ready.

        Args:
            session_id: The session to generate for.
            input_path: Path to the source media file.
            filter_graph: Optional FilterGraph object.
            duration_us: Duration in microseconds for progress.
            cancel_event: Event for cooperative cancellation.
        """
        seek_start = time.monotonic()
        try:
            progress_callback = self._make_progress_callback(session_id)
            output_dir = await self._generator.generate(
                session_id=session_id,
                input_path=input_path,
                filter_graph=filter_graph,
                duration_us=duration_us,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )

            session = await self._repository.get(session_id)
            if session is None:
                return

            preview_seek_latency_seconds.observe(time.monotonic() - seek_start)

            manifest_path = str(output_dir / "manifest.m3u8")
            session.manifest_path = manifest_path
            # seeking -> ready
            await self._transition(session, PreviewStatus.READY)
            await self._broadcast_event(EventType.PREVIEW_READY, session.id)

        except Exception as exc:
            if cancel_event.is_set():
                return

            preview_errors_total.labels(error_type="ffmpeg_error").inc()

            session = await self._repository.get(session_id)
            if session is None:
                return

            error_msg = str(exc)[:500]
            session.error_message = error_msg
            with contextlib.suppress(InvalidTransitionError):
                await self._transition(session, PreviewStatus.ERROR)
            await self._broadcast_event(EventType.PREVIEW_ERROR, session.id, error=error_msg)
            logger.error(
                "preview_seek_generation_failed",
                session_id=session_id,
                error=error_msg,
                correlation_id=get_correlation_id(),
            )
        finally:
            self._generation_tasks.pop(session_id, None)
            self._cancel_events.pop(session_id, None)

    async def stop(self, session_id: str) -> None:
        """Stop a preview session, cancel generation, and clean up.

        Sets the cancel event, waits for process termination, and
        removes the session directory and repository record.

        Args:
            session_id: The session to stop.

        Raises:
            SessionNotFoundError: If the session is not found.
        """
        session = await self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session {session_id} not found")

        await self._cleanup_session(session)
        await self._repository.delete(session_id)

    async def get_status(self, session_id: str) -> PreviewSession:
        """Get the current status of a preview session.

        Checks for expiry on access.

        Args:
            session_id: The session to query.

        Returns:
            The current PreviewSession.

        Raises:
            SessionNotFoundError: If the session is not found.
            SessionExpiredError: If the session has expired.
        """
        session = await self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session {session_id} not found")

        await self._check_expired(session)
        return session

    async def cleanup_expired(self) -> int:
        """Clean up all expired sessions.

        Returns:
            Number of sessions cleaned up.
        """
        expired = await self._repository.get_expired()
        for session in expired:
            await self._cleanup_session(session)
            await self._repository.delete(session.id)
            logger.info(
                "preview_session_expired",
                session_id=session.id,
                correlation_id=get_correlation_id(),
            )
        return len(expired)
