# Requirements: websocket-broadcasts

## Goal

Wire broadcast() into scan service and project router for real-time WebSocket events.

## Background

Backlog Item: BL-065

The backend defines WebSocket event types (SCAN_STARTED, SCAN_COMPLETED, PROJECT_CREATED, HEALTH_STATUS) and the frontend ActivityLog listens for them, but no API operation ever calls `ConnectionManager.broadcast()`. The only messages sent are heartbeat pings. This feature connects the existing broadcast infrastructure to the operations that should trigger events.

## Functional Requirements

**FR-001: SCAN_STARTED broadcast**
- Scan operations trigger a SCAN_STARTED WebSocket broadcast at the beginning of the scan job handler
- Event payload includes relevant context (scan path)
- Acceptance: WebSocket client receives SCAN_STARTED event after triggering a scan

**FR-002: SCAN_COMPLETED broadcast**
- Scan operations trigger a SCAN_COMPLETED WebSocket broadcast at the end of the scan job handler
- Event payload includes relevant context (scan path, video count)
- Acceptance: WebSocket client receives SCAN_COMPLETED event after scan finishes

**FR-003: PROJECT_CREATED broadcast**
- Project creation triggers a PROJECT_CREATED WebSocket broadcast in the projects router
- Event payload includes project ID and name
- Acceptance: WebSocket client receives PROJECT_CREATED event after creating a project

**FR-004: Event payload structure**
- All broadcasts use `build_event(EventType, payload, correlation_id)` for consistent event structure
- Acceptance: Event payloads match the structure expected by the frontend ActivityLog

## Non-Functional Requirements

**NFR-001: No impact on API response times**
- Broadcast calls are fire-and-forget — they do not block the API response
- Metric: API response times for scan and project creation endpoints remain unchanged

## Handler Pattern

Not applicable for v009 — no new MCP tool handlers introduced.

## Out of Scope

- HEALTH_STATUS broadcast wiring (no clear trigger point identified — deferred)
- Adding new event types beyond the existing 5
- WebSocket authentication or authorization
- Modifying frontend ActivityLog rendering logic
- WebSocket reconnection or retry logic

## Test Requirements

- Unit: Verify scan operations call `broadcast()` with SCAN_STARTED event type (AC1)
- Unit: Verify scan completion calls `broadcast()` with SCAN_COMPLETED event type (AC1)
- Unit: Verify project creation calls `broadcast()` with PROJECT_CREATED event type (AC2)
- Unit: Verify event payloads include relevant context (AC4)
- Integration: Verify WebSocket client receives SCAN_STARTED/SCAN_COMPLETED events after triggering a scan
- Integration: Verify WebSocket client receives PROJECT_CREATED event after creating a project
- E2E: Verify Dashboard ActivityLog displays real application events, not just heartbeats (AC3)
- Existing: Router tests for scan and project endpoints may need WebSocket manager mock injection

See `comms/outbox/versions/design/v009/005-logical-design/test-strategy.md` for full test strategy.

## Reference

See `comms/outbox/versions/design/v009/004-research/` for supporting evidence.