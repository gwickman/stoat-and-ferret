"""Event type definitions and message schema for WebSocket broadcasting."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from stoat_ferret.api.middleware.correlation import get_correlation_id

_GLOBAL_EVENT_SCOPE = "__global__"

# Vestigial per-scope dict retained for API compatibility with
# ``clear_event_counter()``; always empty under global-counter mode.
_event_counters: dict[str, int] = {}

# Single monotonic counter shared across all scopes. Asyncio's single-
# threaded event loop serializes all ``build_event`` calls — no locking
# required (FRAMEWORK_CONTEXT.md §3 asyncio safety).
_BROADCAST_COUNTER: int = 0


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
    """Return the next ``event-NNNNN`` identifier and increment the global counter.

    Args:
        scope: Ignored under global-counter mode; retained for call-site
            compatibility.

    Returns:
        Zero-padded monotonic identifier (``event-NNNNN``). Counter rolls over
        past 99999 to ``event-NNNNNN`` without truncation (acceptable per
        INV-003; a single job emitting 100k broadcast events is unlikely).
    """
    global _BROADCAST_COUNTER
    event_id = f"event-{_BROADCAST_COUNTER:05d}"
    _BROADCAST_COUNTER += 1
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
    """Vestigial no-op under global-counter mode.

    Retained so callers (e.g. ``render/service.py``) need no update.
    The global counter is unaffected; per-scope restart semantics are
    intentionally removed as the bug root cause (BL-356, RISK-003).

    Args:
        job_id: Ignored under global-counter mode.
    """
    _event_counters.pop(job_id, None)


def reset_event_counters() -> None:
    """Reset all event ID counters to zero. Intended for test isolation."""
    global _BROADCAST_COUNTER
    _event_counters.clear()
    _BROADCAST_COUNTER = 0
