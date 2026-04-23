"""Tests for OpenAPI state machine documentation (BL-278).

Verifies that the OpenAPI spec published to ``gui/openapi.json`` and the
live ``/openapi.json`` endpoint document:

- Job state transitions on the job endpoints (``GET /jobs/{id}``,
  ``POST /jobs/{id}/cancel``, ``GET /jobs/{id}/wait``).
- The ``JobStatus`` enum with all six values.
- The ``WebSocketEvent`` envelope schema with field descriptions,
  including the monotonic ``event_id`` semantics introduced in BL-273.
- The long-poll ``/wait`` endpoint's timeout behaviour (408 response).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.jobs.queue import JobStatus

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "gui" / "openapi.json"

_TERMINAL_STATUSES = {"complete", "failed", "timeout", "cancelled"}


@pytest.fixture(scope="module")
def static_spec() -> dict:
    """Load the checked-in gui/openapi.json once per module."""
    return json.loads(OPENAPI_PATH.read_text())


@pytest.fixture
def live_spec(client: TestClient) -> dict:
    """Fetch the OpenAPI spec from the running FastAPI app."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


@pytest.mark.api
def test_get_job_endpoint_documents_state_transitions(static_spec: dict) -> None:
    """``GET /jobs/{id}`` description enumerates the state machine."""
    endpoint = static_spec["paths"]["/api/v1/jobs/{job_id}"]["get"]
    description = endpoint["description"].lower()
    assert "state transition" in description
    assert "terminal" in description
    # Every status value in the enum must appear in the description.
    for status_value in JobStatus:
        assert status_value.value in description, status_value.value


@pytest.mark.api
def test_cancel_endpoint_documents_terminal_rejection(static_spec: dict) -> None:
    """``POST /jobs/{id}/cancel`` description explains 409 on terminal."""
    endpoint = static_spec["paths"]["/api/v1/jobs/{job_id}/cancel"]["post"]
    description = endpoint["description"].lower()
    assert "cancelled" in description
    assert "terminal" in description


@pytest.mark.api
def test_wait_endpoint_documents_timeout_behavior(static_spec: dict) -> None:
    """``GET /jobs/{id}/wait`` description explains 408 and terminal block."""
    endpoint = static_spec["paths"]["/api/v1/jobs/{job_id}/wait"]["get"]
    description = endpoint["description"].lower()
    assert "408" in description
    assert "terminal" in description
    # The docs must mention that the endpoint blocks.
    assert "block" in description or "wait" in description


@pytest.mark.api
def test_job_status_enum_schema_is_present(static_spec: dict) -> None:
    """The ``JobStatus`` enum is injected into components.schemas."""
    schemas = static_spec["components"]["schemas"]
    assert "JobStatus" in schemas
    enum_values = set(schemas["JobStatus"]["enum"])
    assert enum_values == {s.value for s in JobStatus}
    description = schemas["JobStatus"]["description"].lower()
    assert "terminal" in description
    assert "pending" in description
    assert "running" in description


@pytest.mark.api
def test_job_status_enum_covers_all_terminal_states(static_spec: dict) -> None:
    """All four terminal states appear in the JobStatus enum values."""
    schemas = static_spec["components"]["schemas"]
    enum_values = set(schemas["JobStatus"]["enum"])
    assert _TERMINAL_STATUSES.issubset(enum_values)


@pytest.mark.api
def test_job_status_response_status_field_is_documented(static_spec: dict) -> None:
    """``JobStatusResponse.status`` carries a state-machine description."""
    schemas = static_spec["components"]["schemas"]
    job_response = schemas["JobStatusResponse"]
    status_field = job_response["properties"]["status"]
    description = status_field["description"].lower()
    assert "pending" in description
    assert "running" in description
    assert "terminal" in description
    for terminal in _TERMINAL_STATUSES:
        assert terminal in description


@pytest.mark.api
def test_websocket_event_schema_is_present(static_spec: dict) -> None:
    """The ``WebSocketEvent`` envelope is present in components.schemas."""
    schemas = static_spec["components"]["schemas"]
    assert "WebSocketEvent" in schemas
    event_schema = schemas["WebSocketEvent"]
    properties = event_schema["properties"]
    for field in ("type", "payload", "correlation_id", "timestamp", "event_id"):
        assert field in properties, field


@pytest.mark.api
def test_websocket_event_id_field_documents_monotonic_semantics(
    static_spec: dict,
) -> None:
    """``WebSocketEvent.event_id`` description mentions the monotonic format."""
    event_schema = static_spec["components"]["schemas"]["WebSocketEvent"]
    event_id_field = event_schema["properties"]["event_id"]
    description = event_id_field["description"].lower()
    assert "monotonic" in description
    assert "event-nnnnn" in description or "event-" in description
    assert "job" in description  # must reference the per-job scoping rule


@pytest.mark.api
def test_websocket_event_type_field_lists_catalog(static_spec: dict) -> None:
    """``WebSocketEvent.type`` description references known event types."""
    event_schema = static_spec["components"]["schemas"]["WebSocketEvent"]
    type_field = event_schema["properties"]["type"]
    description = type_field["description"]
    # A small sample of representative event types from the EventType enum.
    for sample in ("render_started", "render_completed", "heartbeat"):
        assert sample in description, sample


@pytest.mark.api
def test_wait_endpoint_documents_408_timeout_response(static_spec: dict) -> None:
    """The ``/wait`` endpoint's description mentions the 408 timeout path."""
    endpoint = static_spec["paths"]["/api/v1/jobs/{job_id}/wait"]["get"]
    description = endpoint["description"]
    assert "408" in description


@pytest.mark.api
def test_live_openapi_matches_static_state_machine_docs(live_spec: dict) -> None:
    """Live ``/openapi.json`` and gui/openapi.json agree on state machine docs."""
    # Both must expose the injected JobStatus enum and WebSocketEvent schema
    # so agents consuming either source see identical documentation.
    live_schemas = live_spec["components"]["schemas"]
    assert "JobStatus" in live_schemas
    assert "WebSocketEvent" in live_schemas
    live_job_status_values = set(live_schemas["JobStatus"]["enum"])
    assert live_job_status_values == {s.value for s in JobStatus}
    # WebSocketEvent has the expected required fields live as well.
    ws_required = set(live_schemas["WebSocketEvent"].get("required", []))
    assert {"type", "payload", "timestamp", "event_id"}.issubset(ws_required)
