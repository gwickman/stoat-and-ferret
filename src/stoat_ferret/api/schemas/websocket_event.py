"""Pydantic schema documenting the WebSocket event envelope (BL-278).

This module is **documentation-only**: the live broadcast pipeline still
builds events as plain dicts via
:func:`stoat_ferret.api.websocket.events.build_event`. The Pydantic model
defined here mirrors that dict shape so the schema can be injected into
the OpenAPI spec (``#/components/schemas/WebSocketEvent``) for external
AI agents that learn the contract from ``gui/openapi.json`` rather than
source code.

Keep this model in sync with ``build_event`` in
:mod:`stoat_ferret.api.websocket.events` — if a field is added or
renamed there, mirror it here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WebSocketEvent(BaseModel):
    """Documentation-only schema for a broadcast WebSocket event envelope.

    Every event sent on the ``/ws`` endpoint is a JSON object with the
    fields enumerated below. Event-type-specific payload fields live
    inside the ``payload`` object and vary per ``type`` — consult the
    ``EventType`` values in
    :mod:`stoat_ferret.api.websocket.events` for the catalogue of
    recognised ``type`` strings.
    """

    type: str = Field(
        description=(
            "Event type discriminator. Values are drawn from the "
            "``EventType`` enum and include render lifecycle events "
            "(``render_started``, ``render_progress``, "
            "``render_completed``, ``render_failed``, "
            "``render_cancelled``, ``render_queued``, "
            "``render_frame_available``, ``render_queue_status``), "
            "scan events (``scan_started``, ``scan_completed``), "
            "proxy events (``proxy.ready``), preview events "
            "(``preview.generating``, ``preview.ready``, "
            "``preview.seeking``, ``preview.error``), timeline events "
            "(``timeline_updated``, ``layout_applied``, "
            "``audio_mix_changed``, ``transition_applied``), "
            "AI events (``ai_action``), generic job events "
            "(``job_progress``), project events (``project_created``), "
            "and system events (``health_status``, ``heartbeat``)."
        ),
    )
    payload: dict[str, Any] = Field(
        description="Event-specific payload. Fields vary with ``type``; "
        "always a JSON object (may be empty).",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional correlation identifier propagated from the "
        "triggering HTTP request (``X-Correlation-ID`` header). ``null`` "
        "for server-originated events (e.g. heartbeat) with no inbound "
        "correlation context.",
    )
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp at which the event was built. "
        "Example: ``2026-04-23T12:34:56.789012+00:00``.",
    )
    event_id: str = Field(
        description=(
            "Monotonic event identifier in the format "
            "``event-NNNNN`` (zero-padded to 5 digits; widens beyond "
            "5 digits once the scope counter exceeds 99999). Counter is "
            "scoped per ``job_id`` — job-scoped events carry a sequence "
            "local to that job, while events without a job scope share "
            "a single global counter. Within a single scope the "
            "identifier is strictly increasing, which lets clients "
            "detect gaps, reconnect with ``Last-Event-ID``, and replay "
            "missed events from the server buffer."
        ),
    )
