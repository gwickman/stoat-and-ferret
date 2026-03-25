"""Tests for PreviewManager lifecycle coordination.

Tests cover state machine transitions, concurrent session limits,
seek regeneration with cancellation, graceful stop, session expiry,
and WebSocket event broadcasting.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.models import PreviewQuality, PreviewSession, PreviewStatus
from stoat_ferret.db.preview_repository import InMemoryPreviewRepository
from stoat_ferret.preview.manager import (
    InvalidTransitionError,
    PreviewManager,
    SessionExpiredError,
    SessionLimitError,
    SessionNotFoundError,
)


def _make_mock_generator(*, output_dir: Path | None = None) -> AsyncMock:
    """Create a mock HLS generator.

    Args:
        output_dir: Path the mock generate() should return.

    Returns:
        Mock HLSGenerator with async generate method.
    """
    gen = AsyncMock()
    ret = output_dir or Path("/tmp/previews/fake-session")
    gen.generate = AsyncMock(return_value=ret)
    return gen


def _make_mock_ws_manager() -> MagicMock:
    """Create a mock ConnectionManager.

    Returns:
        Mock with async broadcast method.
    """
    mgr = MagicMock(spec=ConnectionManager)
    mgr.broadcast = AsyncMock()
    return mgr


def _make_manager(
    *,
    repository: InMemoryPreviewRepository | None = None,
    generator: AsyncMock | None = None,
    ws_manager: MagicMock | None = None,
    max_sessions: int = 5,
    session_ttl_seconds: int = 3600,
    output_base_dir: str = "/tmp/previews",
) -> tuple[PreviewManager, InMemoryPreviewRepository, AsyncMock, MagicMock]:
    """Create a PreviewManager with test dependencies.

    Returns:
        Tuple of (manager, repository, generator, ws_manager).
    """
    repo = repository or InMemoryPreviewRepository()
    gen = generator or _make_mock_generator(output_dir=Path(output_base_dir) / "fake-session")
    ws = ws_manager or _make_mock_ws_manager()

    mgr = PreviewManager(
        repository=repo,
        generator=gen,
        ws_manager=ws,
        max_sessions=max_sessions,
        session_ttl_seconds=session_ttl_seconds,
        output_base_dir=output_base_dir,
    )
    return mgr, repo, gen, ws


class TestStateMachine:
    """Tests for preview session state transitions."""

    async def test_start_transitions_initializing_to_generating(self) -> None:
        """Start should create session in initializing, then transition to generating."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(
            project_id="proj-1",
            input_path="/media/video.mp4",
        )

        # Session should be in generating state (after init -> generating transition)
        stored = await repo.get(session.id)
        assert stored is not None
        assert stored.status == PreviewStatus.GENERATING

    async def test_start_to_ready_on_generation_complete(self) -> None:
        """After generation completes, session transitions to ready."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(
            project_id="proj-1",
            input_path="/media/video.mp4",
        )

        # Wait for background generation task to complete
        await asyncio.sleep(0.05)

        stored = await repo.get(session.id)
        assert stored is not None
        assert stored.status == PreviewStatus.READY
        assert stored.manifest_path is not None

    async def test_start_to_error_on_generation_failure(self) -> None:
        """Generation failure transitions session to error state."""
        gen = AsyncMock()
        gen.generate = AsyncMock(side_effect=RuntimeError("FFmpeg failed"))
        manager, repo, _, ws = _make_manager(generator=gen)

        session = await manager.start(
            project_id="proj-1",
            input_path="/media/video.mp4",
        )

        await asyncio.sleep(0.05)

        stored = await repo.get(session.id)
        assert stored is not None
        assert stored.status == PreviewStatus.ERROR
        assert "FFmpeg failed" in (stored.error_message or "")

    async def test_invalid_transition_rejected(self) -> None:
        """Invalid state transitions should be rejected."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(
            project_id="proj-1",
            input_path="/media/video.mp4",
        )
        await asyncio.sleep(0.05)

        stored = await repo.get(session.id)
        assert stored is not None
        assert stored.status == PreviewStatus.READY

        # Ready -> Initializing is not a valid transition
        with pytest.raises(InvalidTransitionError):
            await manager._transition(stored, PreviewStatus.INITIALIZING)

    async def test_all_valid_transitions_succeed(self) -> None:
        """All valid transition paths should succeed."""
        repo = InMemoryPreviewRepository()
        manager, _, gen, ws = _make_manager(repository=repo)

        now = datetime.now(timezone.utc)

        # Create a session manually to test transitions
        session = PreviewSession(
            id=PreviewSession.new_id(),
            project_id="proj-1",
            status=PreviewStatus.INITIALIZING,
            quality_level=PreviewQuality.MEDIUM,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1),
        )
        await repo.add(session)

        # initializing -> generating
        await manager._transition(session, PreviewStatus.GENERATING)
        assert session.status == PreviewStatus.GENERATING

        # generating -> ready
        await manager._transition(session, PreviewStatus.READY)
        assert session.status == PreviewStatus.READY

        # ready -> seeking
        await manager._transition(session, PreviewStatus.SEEKING)
        assert session.status == PreviewStatus.SEEKING

        # seeking -> ready
        await manager._transition(session, PreviewStatus.READY)
        assert session.status == PreviewStatus.READY

        # ready -> error
        await manager._transition(session, PreviewStatus.ERROR)
        assert session.status == PreviewStatus.ERROR

        # error -> expired
        await manager._transition(session, PreviewStatus.EXPIRED)
        assert session.status == PreviewStatus.EXPIRED


class TestConcurrentSessionLimit:
    """Tests for concurrent session limit enforcement."""

    async def test_max_sessions_enforced(self) -> None:
        """Creating session max+1 should raise SessionLimitError."""
        manager, repo, gen, ws = _make_manager(max_sessions=2)

        await manager.start(project_id="p1", input_path="/v1.mp4")
        await manager.start(project_id="p2", input_path="/v2.mp4")

        with pytest.raises(SessionLimitError, match="Concurrent session limit"):
            await manager.start(project_id="p3", input_path="/v3.mp4")

    async def test_existing_sessions_unaffected_on_limit(self) -> None:
        """Existing sessions should be unaffected when limit is hit."""
        manager, repo, gen, ws = _make_manager(max_sessions=2)

        s1 = await manager.start(project_id="p1", input_path="/v1.mp4")
        s2 = await manager.start(project_id="p2", input_path="/v2.mp4")

        with pytest.raises(SessionLimitError):
            await manager.start(project_id="p3", input_path="/v3.mp4")

        # Original sessions still exist
        assert await repo.get(s1.id) is not None
        assert await repo.get(s2.id) is not None

    async def test_can_create_after_stop(self) -> None:
        """After stopping a session, a new one can be created."""
        manager, repo, gen, ws = _make_manager(max_sessions=1)

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        with patch("shutil.rmtree"):
            await manager.stop(session.id)

        # Now we can create another
        s2 = await manager.start(project_id="p2", input_path="/v2.mp4")
        assert s2 is not None


class TestSeek:
    """Tests for seek operation."""

    async def test_seek_cancels_and_restarts_generation(self) -> None:
        """Seek should cancel active generation, clean segments, restart."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)  # Let generation complete

        with patch("shutil.rmtree"):
            result = await manager.seek(
                session.id,
                input_path="/v1.mp4",
            )

        assert result.status == PreviewStatus.SEEKING

        # Wait for seek generation to complete
        await asyncio.sleep(0.05)

        stored = await repo.get(session.id)
        assert stored is not None
        assert stored.status == PreviewStatus.READY

    async def test_seek_broadcasts_events(self) -> None:
        """Seek should broadcast seeking and then ready events."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        ws.broadcast.reset_mock()

        with patch("shutil.rmtree"):
            await manager.seek(session.id, input_path="/v1.mp4")

        await asyncio.sleep(0.05)

        # Collect broadcast event types
        event_types = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.seeking" in event_types
        assert "preview.ready" in event_types

    async def test_seek_not_found_raises(self) -> None:
        """Seeking a non-existent session should raise SessionNotFoundError."""
        manager, repo, gen, ws = _make_manager()

        with pytest.raises(SessionNotFoundError):
            await manager.seek("nonexistent", input_path="/v1.mp4")

    async def test_seek_expired_raises(self) -> None:
        """Seeking an expired session should raise SessionExpiredError."""
        manager, repo, gen, ws = _make_manager(session_ttl_seconds=0)

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        with patch("shutil.rmtree"), pytest.raises(SessionExpiredError):
            await manager.seek(session.id, input_path="/v1.mp4")

    async def test_seek_during_generation(self) -> None:
        """Seeking during active generation should cancel and restart."""
        # Slow generator that blocks until cancelled
        slow_gen = AsyncMock()
        generation_started = asyncio.Event()

        async def slow_generate(**kwargs):  # type: ignore[no-untyped-def]
            generation_started.set()
            cancel_event = kwargs.get("cancel_event")
            if cancel_event:
                await cancel_event.wait()
                raise RuntimeError("Cancelled")
            return Path("/tmp/previews/fake-session")

        slow_gen.generate = AsyncMock(side_effect=slow_generate)
        manager, repo, _, ws = _make_manager(generator=slow_gen)

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await generation_started.wait()

        # Now replace the generator to return normally for the seek
        fast_gen = _make_mock_generator(output_dir=Path("/tmp/previews") / session.id)
        manager._generator = fast_gen

        with patch("shutil.rmtree"):
            result = await manager.seek(session.id, input_path="/v1.mp4")

        assert result.status == PreviewStatus.SEEKING

        await asyncio.sleep(0.05)
        stored = await repo.get(session.id)
        assert stored is not None
        assert stored.status == PreviewStatus.READY


class TestGracefulStop:
    """Tests for graceful stop operation."""

    async def test_stop_cleans_up_session(self) -> None:
        """Stop should remove session directory and repository record."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        with patch("shutil.rmtree"):
            await manager.stop(session.id)

        # Session should be deleted from repo
        assert await repo.get(session.id) is None

    async def test_stop_not_found_raises(self) -> None:
        """Stopping a non-existent session should raise SessionNotFoundError."""
        manager, repo, gen, ws = _make_manager()

        with pytest.raises(SessionNotFoundError):
            await manager.stop("nonexistent")

    async def test_stop_cancels_active_generation(self) -> None:
        """Stop should cancel active generation task."""
        slow_gen = AsyncMock()
        generation_started = asyncio.Event()

        async def slow_generate(**kwargs):  # type: ignore[no-untyped-def]
            generation_started.set()
            cancel_event = kwargs.get("cancel_event")
            if cancel_event:
                await cancel_event.wait()
            raise RuntimeError("Cancelled")

        slow_gen.generate = AsyncMock(side_effect=slow_generate)
        manager, repo, _, ws = _make_manager(generator=slow_gen)

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await generation_started.wait()

        with patch("shutil.rmtree"):
            await manager.stop(session.id)

        assert await repo.get(session.id) is None


class TestSessionExpiry:
    """Tests for session expiry detection and cleanup."""

    async def test_accessing_expired_session_raises(self) -> None:
        """Accessing an expired session should raise SessionExpiredError."""
        manager, repo, gen, ws = _make_manager(session_ttl_seconds=0)

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        with patch("shutil.rmtree"), pytest.raises(SessionExpiredError):
            await manager.get_status(session.id)

    async def test_cleanup_expired_removes_sessions(self) -> None:
        """cleanup_expired should remove all expired sessions."""
        manager, repo, gen, ws = _make_manager(session_ttl_seconds=0)

        await manager.start(project_id="p1", input_path="/v1.mp4")
        await manager.start(project_id="p2", input_path="/v2.mp4")
        await asyncio.sleep(0.05)

        with patch("shutil.rmtree"):
            count = await manager.cleanup_expired()

        assert count == 2
        assert await repo.count() == 0

    async def test_non_expired_sessions_not_cleaned(self) -> None:
        """cleanup_expired should not remove sessions that haven't expired."""
        manager, repo, gen, ws = _make_manager(session_ttl_seconds=3600)

        await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        count = await manager.cleanup_expired()
        assert count == 0
        assert await repo.count() == 1


class TestWebSocketEvents:
    """Tests for WebSocket event broadcasting."""

    async def test_start_emits_generating_event(self) -> None:
        """Starting a session should broadcast preview.generating."""
        manager, repo, gen, ws = _make_manager()

        await manager.start(project_id="p1", input_path="/v1.mp4")

        # Check that preview.generating was broadcast
        event_types = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.generating" in event_types

    async def test_generation_complete_emits_ready_event(self) -> None:
        """Completed generation should broadcast preview.ready."""
        manager, repo, gen, ws = _make_manager()

        await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        event_types = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.ready" in event_types

    async def test_generation_error_emits_error_event(self) -> None:
        """Failed generation should broadcast preview.error."""
        gen = AsyncMock()
        gen.generate = AsyncMock(side_effect=RuntimeError("FFmpeg crashed"))
        manager, repo, _, ws = _make_manager(generator=gen)

        await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        event_types = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.error" in event_types

    async def test_event_payload_contains_session_id(self) -> None:
        """All events should include session_id in payload."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        for call in ws.broadcast.call_args_list:
            event = call.args[0]
            assert event["payload"]["session_id"] == session.id

    async def test_seek_emits_seeking_event(self) -> None:
        """Seek should broadcast preview.seeking event."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        ws.broadcast.reset_mock()

        with patch("shutil.rmtree"):
            await manager.seek(session.id, input_path="/v1.mp4")

        event_types = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.seeking" in event_types


class TestGetStatus:
    """Tests for get_status."""

    async def test_get_status_returns_session(self) -> None:
        """get_status should return the current session."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        result = await manager.get_status(session.id)
        assert result.id == session.id
        assert result.status == PreviewStatus.READY

    async def test_get_status_not_found_raises(self) -> None:
        """get_status for a non-existent session should raise."""
        manager, repo, gen, ws = _make_manager()

        with pytest.raises(SessionNotFoundError):
            await manager.get_status("nonexistent")


class TestSeekSerialization:
    """Tests for per-session asyncio.Lock seek serialization (NFR-001)."""

    async def test_concurrent_seeks_serialized(self) -> None:
        """Concurrent seek requests on the same session use a per-session lock."""
        manager, repo, gen, ws = _make_manager()

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        # Verify per-session lock is created and used
        lock = manager._get_lock(session.id)
        assert isinstance(lock, asyncio.Lock)

        # Same session returns the same lock
        lock2 = manager._get_lock(session.id)
        assert lock is lock2

        # Different session returns a different lock
        lock3 = manager._get_lock("other-session")
        assert lock3 is not lock

        # Launch two concurrent seeks - the lock serializes them
        with patch("shutil.rmtree"):
            t1 = asyncio.create_task(manager.seek(session.id, input_path="/v1.mp4"))
            t2 = asyncio.create_task(manager.seek(session.id, input_path="/v1.mp4"))
            results = await asyncio.gather(t1, t2, return_exceptions=True)

        # At least one seek should succeed, the second may fail with
        # InvalidTransitionError since the first seek changes the state
        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) >= 1
        # Any failures should be transition-related, not race conditions
        for exc in failures:
            assert isinstance(exc, InvalidTransitionError)


class TestParityStartSeek:
    """Parity tests for start and seek (both trigger generation)."""

    async def test_both_emit_generating_to_ready_events(self) -> None:
        """Both start and seek should emit generating -> ready events on success."""
        manager, repo, gen, ws = _make_manager()

        # Start
        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        start_events = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.generating" in start_events
        assert "preview.ready" in start_events

        # Seek
        ws.broadcast.reset_mock()
        with patch("shutil.rmtree"):
            await manager.seek(session.id, input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        seek_events = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.seeking" in seek_events
        assert "preview.ready" in seek_events

    async def test_both_emit_error_on_failure(self) -> None:
        """Both start and seek should emit error event on failure."""
        gen = AsyncMock()
        call_count = 0

        async def fail_generate(**kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (start) succeeds
                return Path("/tmp/previews/fake-session")
            # Second call (seek) fails
            raise RuntimeError("Generation failed")

        gen.generate = AsyncMock(side_effect=fail_generate)
        manager, repo, _, ws = _make_manager(generator=gen)

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        ws.broadcast.reset_mock()
        with patch("shutil.rmtree"):
            await manager.seek(session.id, input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        seek_events = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.error" in seek_events
