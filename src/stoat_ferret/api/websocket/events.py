"""Event type definitions and message schema for WebSocket broadcasting."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from stoat_ferret.api.middleware.correlation import get_correlation_id


class EventType(str, Enum):
    """Types of events broadcast over WebSocket."""

    HEALTH_STATUS = "health_status"
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    PROJECT_CREATED = "project_created"
    HEARTBEAT = "heartbeat"


def build_event(
    event_type: EventType,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build a WebSocket event message with standard schema.

    Args:
        event_type: The type of event.
        payload: Event-specific data. Defaults to empty dict.
        correlation_id: Override correlation ID. If None, reads from context var.

    Returns:
        Dict with type, payload, correlation_id, and timestamp fields.
    """
    cid = correlation_id if correlation_id is not None else get_correlation_id()
    return {
        "type": event_type.value,
        "payload": payload or {},
        "correlation_id": cid or None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
