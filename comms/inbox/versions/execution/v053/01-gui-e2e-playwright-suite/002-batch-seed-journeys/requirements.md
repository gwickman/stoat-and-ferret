# Feature 002: batch-seed-journeys

## Goal

Test batch panel WebSocket event handling (J603) and seed endpoint roundtrip testing workflow (J606). Verify that batch form submissions trigger WebSocket `render_progress` events with correct payload fields, that progress updates render in the UI, and that the seed endpoint API supports creating, listing, and deleting test fixtures with correct response schemas.

## Background

**Backlog Item:** BL-297 (E2E Playwright tests for critical GUI workflows)

**User Context:** Users submit batch render jobs from the batch panel, monitor progress via real-time WebSocket events, and developers need an automated way to seed test projects for E2E testing. This feature validates both the batch panel event flow and the seed endpoint API contract.

**Prior Work:** 
- v044 (BL-295) completed batch panel WebSocket integration; `render_progress` events broadcast from `render/service.py`
- v040 (BL-276) completed seed endpoint (`POST /api/v1/testing/seed`, `DELETE /api/v1/testing/seed/{id}`)
- v052 completed accessibility; batch panel includes proper ARIA labels
- Task 007 verified WebSocket schema: event type is `render_progress` with fields `{job_id, progress, eta_seconds, speed_ratio, frame_count, fps, encoder_name, encoder_type}`

Feature 002 validates this integration with E2E tests.

## Functional Requirements

**FR-001: Batch Form Submission**
- Navigate to workspace "render" preset (which displays batch panel)
- Fill batch form with valid render parameters (output size, frame range, codec)
- Submit form via "Start Batch Job" button
- Assert HTTP POST succeeds (no error toast)
- Assert job appears in BatchJobList with "Pending" or initial progress state

**FR-002: WebSocket Progress Events**
- After batch job submission, listen for WebSocket events on `/api/v1/ws/preview`
- Verify events have type `render_progress` (confirmed in Task 007 research)
- Assert each event includes payload fields: `job_id`, `progress` (0–100), `eta_seconds`, `speed_ratio`, `frame_count`, `fps`, `encoder_name`, `encoder_type`
- Verify progress bar in BatchJobList updates in real-time as events arrive
- Verify multiple events are received (progress increments toward 100)

**FR-003: Seed Endpoint API Schema**
- Call `POST /api/v1/testing/seed` with fixture type "project"
- Request schema: `{fixture_type, name, data: {output_width, output_height, output_fps}}`
- Assert response schema: `{fixture_id, fixture_type, name}`
- Assert server prepends `seeded_` prefix to fixture name (INV-SEED-2)
- Verify created fixture is queryable via `/api/v1/projects/{fixture_id}`

**FR-004: Seed Endpoint Cleanup**
- Call `DELETE /api/v1/testing/seed/{fixture_id}?fixture_type=project`
- Assert response is HTTP 204 (no content)
- Verify deleted fixture no longer appears in Library or via API GET

**FR-005: Seed Endpoint Integration with Library**
- Create 3 test projects via seed endpoint with different output sizes (1920×1080, 1280×720, 640×480)
- Navigate to Library panel
- Assert all 3 seeded projects appear in the project list
- Assert project names include `seeded_` prefix
- Delete all seeded projects
- Assert projects disappear from Library

## Non-Functional Requirements

**NFR-001: WebSocket Latency**
- Progress events arrive within 1 second of submission (real-time user feedback)
- Progress bar updates smoothly (no jank or long delays between events)

**NFR-002: API Idempotency**
- Multiple calls to `POST /api/v1/testing/seed` with same name create separate fixtures (name is NOT a unique key)
- `DELETE /api/v1/testing/seed/{id}` is idempotent on the test fixture scope (delete once succeeds, subsequent delete on same ID should not break test)

**NFR-003: Testing Mode Gate**
- Seed endpoint requires `STOAT_TESTING_MODE=true` in CI environment
- Without the flag, endpoint returns HTTP 403
- Feature implementation must add env var to `.github/workflows/ci.yml` `e2e` job

## Framework Decisions

Per FRAMEWORK_CONTEXT.md:

**WebSocket Patterns (§3, WebSocket Replay):**
- In-memory replay buffer shared on `ConnectionManager` (server-global, not per-connection)
- Client identity transient, derived from `Last-Event-ID` HTTP header
- Events are not durable (in-memory only; lost on server restart)
- Tests should not rely on event persistence across server restarts

**Testing Mode Gate (§3, Python, Error handling):**
- `STOAT_TESTING_MODE=true` gates seed endpoint via `require_testing_mode()` dependency
- Returns HTTP 403 if disabled; no graceful fallback
- Feature 002 must verify the env var is set in CI before J606 execution

**API Schema Stability (§3, Frontend, API types):**
- OpenAPI spec in `gui/openapi.json` must stay in sync with live API
- Seed endpoint schema (`POST /api/v1/testing/seed` request/response) is documented in OpenAPI
- If API changes, `gui/openapi.json` must be regenerated before merge (`uv run python -m scripts.export_openapi`)

## Out of Scope

- Modifying batch form UI or validation logic (existing from v044)
- Creating a UI for seed endpoint management (seed is CLI/testing-only)
- Supporting fixture types other than "project" (scope limited to projects)
- Batch job cancellation or pause (covered in future versions if needed)
- WebSocket reconnection or recovery scenarios (covered in v035+ learnings but not this feature)

## Test Requirements

**Test Files:**
- Create `tests/e2e/batch-panel.spec.ts` — J603 WebSocket event handling and progress bar updates
- Create `tests/e2e/seed-endpoint.spec.ts` — J606 seed API roundtrip and Library integration
- Update `.github/workflows/ci.yml` — add `STOAT_TESTING_MODE: "true"` env var to `e2e` job's "Run E2E tests" step

**Test Strategy (per Task 006):**
- Use Playwright WebSocket interception to listen for progress events (not mocking; real server events)
- Create fixtures via HTTP API (not UI form); verify in Library via UI navigation
- No database setup required; seed endpoint creates real project records in test database
- Timeout tests appropriately (batch jobs may take 10–30 seconds in test mode)

## Reference

See `C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret\comms\outbox\versions\design\v053\005-research\` for supporting evidence:
- WebSocket event schema verified (Q11, findings 11–12): `render_progress` event type, confirmed field names
- Seed endpoint API schema (Q17–19, findings 17–18): POST/DELETE endpoints, request/response schemas, fixture type support
- Batch panel rendering patterns (Q11–12): BatchJobList component receives WebSocket events
- CI setup (Q3, findings 3): `e2e` job runs after backend startup; port 8765 configured
- Testing mode gate (finding 51–52): requires `STOAT_TESTING_MODE=true` env var; returns HTTP 403 if disabled