"""Unit tests for monotonic event_id generation in ``build_event`` (BL-273)."""

from __future__ import annotations

import re

import pytest

from stoat_ferret.api.websocket.events import (
    EventType,
    build_event,
    clear_event_counter,
    reset_event_counters,
)

EVENT_ID_PATTERN = re.compile(r"^event-\d{5,}$")


@pytest.fixture(autouse=True)
def _isolate_counters() -> None:
    """Ensure each test starts with a clean counter dict."""
    reset_event_counters()


def test_counter_init_zero() -> None:
    """First event for a job returns ``event-00000`` (INV-001)."""
    event = build_event(EventType.RENDER_STARTED, {"job_id": "job-1"}, job_id="job-1")

    assert event["event_id"] == "event-00000"


def test_counter_increment() -> None:
    """Subsequent events within the same job increment monotonically (INV-002)."""
    first = build_event(EventType.RENDER_PROGRESS, {"job_id": "job-2"}, job_id="job-2")
    second = build_event(EventType.RENDER_PROGRESS, {"job_id": "job-2"}, job_id="job-2")
    third = build_event(EventType.RENDER_PROGRESS, {"job_id": "job-2"}, job_id="job-2")

    assert first["event_id"] == "event-00000"
    assert second["event_id"] == "event-00001"
    assert third["event_id"] == "event-00002"


def test_counter_job_scoped() -> None:
    """Two jobs have independent counters."""
    job_a_1 = build_event(EventType.RENDER_PROGRESS, job_id="job-a")
    job_b_1 = build_event(EventType.RENDER_PROGRESS, job_id="job-b")
    job_a_2 = build_event(EventType.RENDER_PROGRESS, job_id="job-a")
    job_b_2 = build_event(EventType.RENDER_PROGRESS, job_id="job-b")

    assert job_a_1["event_id"] == "event-00000"
    assert job_a_2["event_id"] == "event-00001"
    assert job_b_1["event_id"] == "event-00000"
    assert job_b_2["event_id"] == "event-00001"


def test_counter_cleanup_restarts_at_zero() -> None:
    """Counter removed after terminal state; next event starts at zero again."""
    build_event(EventType.RENDER_STARTED, job_id="job-3")
    build_event(EventType.RENDER_PROGRESS, job_id="job-3")
    build_event(EventType.RENDER_COMPLETED, job_id="job-3")

    clear_event_counter("job-3")

    # A later event for the same job id begins a fresh sequence.
    resumed = build_event(EventType.RENDER_STARTED, job_id="job-3")
    assert resumed["event_id"] == "event-00000"


def test_clear_event_counter_unknown_is_noop() -> None:
    """Clearing a counter for an unknown job does not raise."""
    clear_event_counter("never-existed")  # Should not raise


def test_counter_rollover_past_five_digits() -> None:
    """Counter beyond 99999 continues incrementing; format widens (acceptable)."""
    # Seed the counter near the five-digit limit without executing 100k calls.
    from stoat_ferret.api.websocket import events

    events._event_counters["job-overflow"] = 99_999

    at_limit = build_event(EventType.RENDER_PROGRESS, job_id="job-overflow")
    past_limit = build_event(EventType.RENDER_PROGRESS, job_id="job-overflow")

    assert at_limit["event_id"] == "event-99999"
    # Rollover widens the format; value remains strictly monotonic.
    assert past_limit["event_id"] == "event-100000"
    assert int(past_limit["event_id"].split("-")[1]) > int(at_limit["event_id"].split("-")[1])


def test_global_scope_used_when_job_id_missing() -> None:
    """Events built without a ``job_id`` still receive a monotonic event_id (FR-001)."""
    first = build_event(EventType.HEARTBEAT)
    second = build_event(EventType.HEALTH_STATUS)

    assert EVENT_ID_PATTERN.match(first["event_id"])
    assert EVENT_ID_PATTERN.match(second["event_id"])
    first_n = int(first["event_id"].split("-")[1])
    second_n = int(second["event_id"].split("-")[1])
    assert second_n == first_n + 1


def test_event_id_format_is_string_and_pattern() -> None:
    """``event_id`` is a string matching ``event-\\d{5,}`` format (FR-001)."""
    event = build_event(EventType.RENDER_STARTED, job_id="job-fmt")

    assert isinstance(event["event_id"], str)
    assert EVENT_ID_PATTERN.match(event["event_id"])


def test_build_event_schema_includes_event_id() -> None:
    """Every event payload must contain the ``event_id`` key alongside standard fields."""
    event = build_event(EventType.SCAN_STARTED, {"path": "/tmp"}, job_id="job-schema")

    assert set(event.keys()) >= {
        "type",
        "payload",
        "correlation_id",
        "timestamp",
        "event_id",
    }


def test_event_id_monotonic_within_job_strictly_increasing() -> None:
    """NFR-002: strictly monotonically increasing within one job."""
    ids: list[int] = []
    for _ in range(20):
        evt = build_event(EventType.RENDER_PROGRESS, job_id="job-mono")
        ids.append(int(evt["event_id"].split("-")[1]))

    for prev, nxt in zip(ids, ids[1:], strict=False):
        assert nxt == prev + 1
