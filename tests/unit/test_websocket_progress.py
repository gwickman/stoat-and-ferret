"""Tests for WebSocket progress callback wiring.

Tests cover progress callback broadcasting, throttling behavior,
event payload schema, and coexistence with state transition events.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from stoat_ferret.api.websocket.events import EventType
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.preview_repository import InMemoryPreviewRepository
from stoat_ferret.preview.manager import PreviewManager


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
    generator: AsyncMock | None = None,
    ws_manager: MagicMock | None = None,
    output_base_dir: str = "/tmp/previews",
) -> tuple[PreviewManager, InMemoryPreviewRepository, AsyncMock, MagicMock]:
    """Create a PreviewManager with test dependencies.

    Returns:
        Tuple of (manager, repository, generator, ws_manager).
    """
    repo = InMemoryPreviewRepository()
    gen = generator or _make_mock_generator(output_dir=Path(output_base_dir) / "fake-session")
    ws = ws_manager or _make_mock_ws_manager()

    mgr = PreviewManager(
        repository=repo,
        generator=gen,
        ws_manager=ws,
        max_sessions=5,
        session_ttl_seconds=3600,
        output_base_dir=output_base_dir,
    )
    return mgr, repo, gen, ws


class TestProgressCallbackBroadcast:
    """Tests for progress callback broadcasting WebSocket events."""

    async def test_progress_callback_broadcasts_job_progress(self) -> None:
        """Progress callback should broadcast JOB_PROGRESS events with correct payload."""
        manager, _repo, _gen, ws = _make_manager()
        callback = manager._make_progress_callback("session-123")

        await callback(0.5)

        ws.broadcast.assert_called_once()
        event = ws.broadcast.call_args.args[0]
        assert event["type"] == EventType.JOB_PROGRESS.value
        assert event["payload"]["session_id"] == "session-123"
        assert event["payload"]["progress"] == 0.5
        assert event["payload"]["status"] == "generating"

    async def test_progress_callback_payload_schema(self) -> None:
        """Event payload must contain session_id, progress, and status fields."""
        manager, _repo, _gen, ws = _make_manager()
        callback = manager._make_progress_callback("sess-abc")

        await callback(0.75)

        event = ws.broadcast.call_args.args[0]
        payload = event["payload"]
        assert "session_id" in payload
        assert "progress" in payload
        assert "status" in payload
        assert isinstance(payload["progress"], float)
        assert payload["status"] == "generating"

    async def test_progress_1_always_broadcasts(self) -> None:
        """Progress value 1.0 should always broadcast regardless of throttling."""
        manager, _repo, _gen, ws = _make_manager()
        callback = manager._make_progress_callback("session-123")

        # First call updates last_broadcast_time
        await callback(0.1)
        # Immediately send 1.0 — should not be throttled
        await callback(1.0)

        assert ws.broadcast.call_count == 2
        final_event = ws.broadcast.call_args.args[0]
        assert final_event["payload"]["progress"] == 1.0


class TestProgressThrottling:
    """Tests for progress event throttling."""

    async def test_rapid_calls_throttled(self) -> None:
        """Rapid progress calls within 500ms should be throttled."""
        manager, _repo, _gen, ws = _make_manager()
        callback = manager._make_progress_callback("session-123")

        # First call goes through
        await callback(0.1)
        # Immediate second call should be throttled
        await callback(0.2)
        await callback(0.3)

        # Only the first call should have broadcast
        assert ws.broadcast.call_count == 1

    async def test_calls_after_throttle_interval_broadcast(self) -> None:
        """Calls after the throttle interval should broadcast."""
        manager, _repo, _gen, ws = _make_manager()
        callback = manager._make_progress_callback("session-123")

        await callback(0.1)
        assert ws.broadcast.call_count == 1

        # Monkey-patch monotonic to simulate time passing
        original_monotonic = time.monotonic
        try:
            time.monotonic = lambda: original_monotonic() + 1.0  # type: ignore[assignment]
            await callback(0.5)
        finally:
            time.monotonic = original_monotonic  # type: ignore[assignment]

        assert ws.broadcast.call_count == 2


class TestProgressWithStateTransitions:
    """Tests for progress events coexisting with state transitions."""

    async def test_start_emits_progress_and_state_events(self) -> None:
        """Starting a session should emit both progress and state transition events."""

        async def capturing_generate(**kwargs):  # type: ignore[no-untyped-def]
            cb = kwargs.get("progress_callback")
            if cb:
                await cb(0.5)
                await cb(1.0)
            return Path("/tmp/previews/fake-session")

        gen = AsyncMock()
        gen.generate = AsyncMock(side_effect=capturing_generate)
        manager, repo, _, ws = _make_manager(generator=gen)

        await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        event_types = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        # State transitions still fire
        assert "preview.generating" in event_types
        assert "preview.ready" in event_types
        # Progress events also fire
        assert "job_progress" in event_types

    async def test_seek_emits_progress_and_state_events(self) -> None:
        """Seek should emit progress alongside seeking/ready state events."""
        call_count = 0

        async def generate_with_progress(**kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            cb = kwargs.get("progress_callback")
            if call_count == 2 and cb:
                # Only emit progress on the seek generation
                await cb(0.5)
            return Path("/tmp/previews/fake-session")

        gen = AsyncMock()
        gen.generate = AsyncMock(side_effect=generate_with_progress)
        manager, repo, _, ws = _make_manager(generator=gen)

        session = await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        ws.broadcast.reset_mock()
        with patch("shutil.rmtree"):
            await manager.seek(session.id, input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        event_types = [call.args[0]["type"] for call in ws.broadcast.call_args_list]
        assert "preview.seeking" in event_types
        assert "preview.ready" in event_types
        assert "job_progress" in event_types

    async def test_generator_receives_progress_callback(self) -> None:
        """Generator.generate() should receive a progress_callback argument."""
        manager, repo, gen, ws = _make_manager()

        await manager.start(project_id="p1", input_path="/v1.mp4")
        await asyncio.sleep(0.05)

        gen.generate.assert_called_once()
        call_kwargs = gen.generate.call_args.kwargs
        assert "progress_callback" in call_kwargs
        assert callable(call_kwargs["progress_callback"])


class TestProgressCallbackPerformance:
    """Tests for progress callback performance (NFR-001)."""

    async def test_callback_execution_under_5ms(self) -> None:
        """Progress callback execution should be under 5ms per invocation."""
        manager, _repo, _gen, ws = _make_manager()
        callback = manager._make_progress_callback("session-perf")

        # Warm up
        await callback(0.1)

        # Measure throttled (no-op) calls — should be very fast
        start = time.monotonic()
        for i in range(100):
            await callback(0.2 + i * 0.001)
        elapsed = time.monotonic() - start

        # 100 throttled calls should complete well under 500ms total (5ms each)
        assert elapsed < 0.5, f"100 throttled calls took {elapsed:.3f}s"


class TestProgressCallbackEdgeCases:
    """Tests for edge cases in progress callback behavior."""

    async def test_progress_zero_broadcasts(self) -> None:
        """Progress value 0.0 should broadcast on first call."""
        manager, _repo, _gen, ws = _make_manager()
        callback = manager._make_progress_callback("session-123")

        await callback(0.0)

        assert ws.broadcast.call_count == 1
        event = ws.broadcast.call_args.args[0]
        assert event["payload"]["progress"] == 0.0

    async def test_multiple_sessions_independent_throttling(self) -> None:
        """Progress callbacks for different sessions throttle independently."""
        manager, _repo, _gen, ws = _make_manager()
        cb1 = manager._make_progress_callback("session-1")
        cb2 = manager._make_progress_callback("session-2")

        await cb1(0.1)
        await cb2(0.2)

        assert ws.broadcast.call_count == 2
        payloads = [call.args[0]["payload"] for call in ws.broadcast.call_args_list]
        session_ids = {p["session_id"] for p in payloads}
        assert session_ids == {"session-1", "session-2"}
