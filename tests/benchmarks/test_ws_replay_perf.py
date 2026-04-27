"""WebSocket replay buffer benchmark (BL-288, FR-002).

Benchmarks :meth:`ConnectionManager.replay_since` against a pre-filled
1000-event buffer. The 200ms target is the acceptance criterion in
``docs/benchmarks/baseline.md``; replaying from the middle of the
buffer is the typical reconnect path (the fresh half is returned, the
client already has the older half).

Run with::

    uv run pytest tests/benchmarks/test_ws_replay_perf.py --benchmark-only --no-cov -v
"""

from __future__ import annotations

import pytest

from stoat_ferret.api.websocket.manager import ConnectionManager

REPLAY_MEAN_TARGET_S = 0.200


@pytest.mark.benchmark
def test_events_after_latency(
    benchmark: object,
    replay_buffer_1000_events: tuple[ConnectionManager, list[str]],
) -> None:
    """replay_since() with last_event_id mid-buffer must mean < 200ms.

    Picking the 500th event id forces the implementation to scan the
    deque, apply the TTL filter, and slice — exercising every code
    path. A returned list of ~499 events is the expected reconnect
    payload.
    """
    manager, event_ids = replay_buffer_1000_events
    mid_event_id = event_ids[500]

    def _call() -> int:
        events = manager.replay_since(mid_event_id)
        return len(events)

    returned = benchmark(_call)  # type: ignore[operator]
    # Events strictly after index 500 → indices 501..999 → 499 entries.
    assert returned == 499

    stats = benchmark.stats.stats  # type: ignore[attr-defined]
    assert stats.mean < REPLAY_MEAN_TARGET_S, (
        f"replay_since mean {stats.mean * 1000:.1f}ms exceeds "
        f"{REPLAY_MEAN_TARGET_S * 1000:.0f}ms target"
    )
