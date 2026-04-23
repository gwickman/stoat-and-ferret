"""Event type definitions and message schema for WebSocket broadcasting."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from stoat_ferret.api.middleware.correlation import get_correlation_id

_GLOBAL_EVENT_SCOPE = "__global__"

# Job-scoped event ID counters. Initialized to 0 on first event per job;
# removed when a job reaches a terminal state via ``clear_event_counter``.
# Events without a job scope share the ``_GLOBAL_EVENT_SCOPE`` counter.
# Mutation is serialized by the asyncio event loop (all ``build_event`` call
# sites execute on the main loop; no ``run_in_executor`` usage).
_event_counters: dict[str, int] = {}


class EventType(str, Enum):
    """Types of events broadcast over WebSocket."""

    HEALTH_STATUS = "health_status"
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    PROJECT_CREATED = "project_created"
    HEARTBEAT = "heartbeat"
    TIMELINE_UPDATED = "timeline_updated"
    LAYOUT_APPLIED = "layout_applied"
    AUDIO_MIX_CHANGED = "audio_mix_changed"
    TRANSITION_APPLIED = "transition_applied"
    JOB_PROGRESS = "job_progress"
    PREVIEW_GENERATING = "preview.generating"
    PREVIEW_READY = "preview.ready"
    PREVIEW_SEEKING = "preview.seeking"
    PREVIEW_ERROR = "preview.error"
    AI_ACTION = "ai_action"
    RENDER_PROGRESS = "render_progress"
    RENDER_STARTED = "render_started"
    RENDER_COMPLETED = "render_completed"
    RENDER_FAILED = "render_failed"
    RENDER_CANCELLED = "render_cancelled"
    RENDER_QUEUED = "render_queued"
    RENDER_FRAME_AVAILABLE = "render_frame_available"
    RENDER_QUEUE_STATUS = "render_queue_status"
    PROXY_READY = "proxy.ready"


def _next_event_id(scope: str) -> str:
    """Return the next ``event-NNNNN`` identifier for a scope and increment the counter.

    Args:
        scope: Counter scope key (job_id or the global fallback).

    Returns:
        Zero-padded monotonic identifier (``event-NNNNN``). Counter rolls over
        past 99999 to ``event-NNNNNN`` without truncation (acceptable per
        INV-003; a single job emitting 100k broadcast events is unlikely).
    """
    current = _event_counters.get(scope, 0)
    event_id = f"event-{current:05d}"
    _event_counters[scope] = current + 1
    return event_id


def build_event(
    event_type: EventType,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Build a WebSocket event message with standard schema.

    Args:
        event_type: The type of event.
        payload: Event-specific data. Defaults to empty dict.
        correlation_id: Override correlation ID. If None, reads from context var.
        job_id: Optional job identifier used to scope the monotonic ``event_id``
            counter. When omitted, a global counter is used so every event still
            carries an ``event_id`` (FR-001).

    Returns:
        Dict with type, payload, correlation_id, timestamp, and event_id fields.
    """
    cid = correlation_id if correlation_id is not None else get_correlation_id()
    scope = job_id if job_id is not None else _GLOBAL_EVENT_SCOPE
    event_id = _next_event_id(scope)
    return {
        "type": event_type.value,
        "payload": payload or {},
        "correlation_id": cid or None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
    }


def clear_event_counter(job_id: str) -> None:
    """Remove the per-job event ID counter after a terminal state.

    Safe to call for unknown job IDs; a missing key is a no-op.

    Args:
        job_id: The job identifier whose counter should be discarded.
    """
    _event_counters.pop(job_id, None)


def reset_event_counters() -> None:
    """Clear all event ID counters. Intended for test isolation."""
    _event_counters.clear()
