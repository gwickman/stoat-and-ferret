# Feature 002: batch-seed-journeys — Implementation Plan

## Overview

Implement J603 and J606 E2E tests covering batch panel WebSocket event handling and seed endpoint roundtrip testing. J603 tests verify that batch form submissions trigger `render_progress` WebSocket events with correct payload and that the progress bar updates in real-time. J606 tests verify seed endpoint API schema, fixture creation/deletion, and Library integration. Also adds mandatory `STOAT_TESTING_MODE: "true"` env var to CI workflow to unblock J606 execution.

## Framework Guardrails

Per FRAMEWORK_CONTEXT.md:

**WebSocket Testing Patterns (§3, WebSocket Replay):**
- Replay buffer is server-global (shared on `ConnectionManager`), not per-connection
- Client identity is transient (derived from `Last-Event-ID` header); no durable session
- Events survive reconnection within TTL but NOT server restart (in-memory only)
- Tests should use `page.on("websocket")` to intercept real events, not mock WebSocket

**Testing Mode Gate (§3, Python, Error handling):**
- `STOAT_TESTING_MODE=true` gates seed endpoint via `require_testing_mode()` dependency
- Gate returns HTTP 403 if disabled; no fallback or retry logic
- Feature 002 is RESPONSIBLE for adding env var to CI workflow
- Without the env var, J606 will fail with HTTP 403 on first seed attempt

**API Schema Stability (§3, Frontend, API types):**
- Seed endpoint request/response schemas are documented in OpenAPI spec
- If API changes, regenerate `gui/openapi.json` via `uv run python -m scripts.export_openapi` before merge
- Tests should assert response structure against expected schema

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|----------|
| `tests/e2e/batch-panel.spec.ts` | Create | J603 tests: batch form submission, WebSocket event listening, progress bar updates |
| `tests/e2e/seed-endpoint.spec.ts` | Create | J606 tests: seed API roundtrip, fixture creation/deletion, Library integration |
| `.github/workflows/ci.yml` | Modify | Add `STOAT_TESTING_MODE: "true"` env var to `e2e` job's "Run E2E tests" step (MANDATORY for J606) |

## Test Files

Tests to run for targeted validation (Stage 1 verification):
```
tests/e2e/batch-panel.spec.ts tests/e2e/seed-endpoint.spec.ts
```

## Implementation Stages

### Stage 1: CI Workflow Setup (Prerequisite)

**Objectives:**
- Add `STOAT_TESTING_MODE: "true"` env var to CI `e2e` job
- Ensure J606 can reach seed endpoint without HTTP 403 errors

**Implementation Steps:**
1. Open `.github/workflows/ci.yml`
2. Locate "Run E2E tests" step in `e2e` job (runs `npx playwright test`)
3. Add environment variables block:
   ```yaml
   - name: Run E2E tests
     env:
       STOAT_TESTING_MODE: "true"
     run: npx playwright test
   ```
4. Verify syntax is valid YAML (indentation critical)
5. No other changes to workflow; this is a minimal, surgical addition

**Verification Commands:**
```bash
# Verify YAML syntax
npx yaml-lint .github/workflows/ci.yml
# Or run the workflow in act (GitHub Actions emulator) if available
```

### Stage 2: J603 — Batch Panel WebSocket Events

**Objectives:**
- Create batch-panel.spec.ts with real WebSocket event interception
- Verify `render_progress` event schema and payload fields
- Assert progress bar updates match event progress values

**Implementation Steps:**
1. Create `tests/e2e/batch-panel.spec.ts`
2. Test setup: navigate to `/gui/?workspace=render` (render preset with batch panel visible)
3. Setup WebSocket listener via `page.on("websocket", ws => ...)`
4. Fill batch form (output size 1920×1080, frame range, codec)
5. Click "Start Batch Job" button
6. Wait for WebSocket events: listen for `render_progress` messages
7. Assert first event payload includes: `{job_id, progress: 0, eta_seconds, speed_ratio, frame_count, fps, encoder_name, encoder_type}`
8. Verify subsequent events have increasing `progress` values (0 → 25 → 50 → 75 → 100)
9. Assert BatchJobList UI updates in sync with events (progress bar reflects latest progress value)
10. Verify final event has `progress: 100` and job list shows "Completed" or final status

**Verification Commands:**
```bash
npx playwright test tests/e2e/batch-panel.spec.ts
```

### Stage 3: J606 — Seed Endpoint API

**Objectives:**
- Create seed-endpoint.spec.ts with API roundtrip testing
- Verify POST request/response schema and fixture creation
- Verify DELETE cleanup and Library integration

**Implementation Steps:**
1. Create `tests/e2e/seed-endpoint.spec.ts`
2. Test setup: Call `POST /api/v1/testing/seed` with valid request:
   ```json
   {
     "fixture_type": "project",
     "name": "e2e_test_project_1",
     "data": {
       "output_width": 1920,
       "output_height": 1080,
       "output_fps": 30
     }
   }
   ```
3. Assert response is HTTP 201 with schema: `{fixture_id, fixture_type, name}`
4. Verify response name includes `seeded_` prefix: `seeded_e2e_test_project_1`
5. Store `fixture_id` for later cleanup
6. Navigate to Library panel (via UI or direct route `/gui/?workspace=edit` then click Library)
7. Verify created project appears in project list with `seeded_` name and correct output size (1920×1080)
8. Test cleanup: Call `DELETE /api/v1/testing/seed/{fixture_id}?fixture_type=project`
9. Assert response is HTTP 204 (no content)
10. Refresh Library (reload page or trigger API refresh)
11. Verify deleted fixture no longer appears in project list
12. Repeat for 2 additional fixtures with different sizes (1280×720, 640×480)

**Verification Commands:**
```bash
npx playwright test tests/e2e/seed-endpoint.spec.ts
```

### Stage 4: Integration Validation

**Objectives:**
- Run all batch/seed tests together to ensure no interference
- Verify CI workflow is ready for merge

**Implementation Steps:**
1. Run combined test suite: `npx playwright test tests/e2e/batch-panel.spec.ts tests/e2e/seed-endpoint.spec.ts`
2. Verify no cross-test pollution (each test cleans up fixtures)
3. Check CI workflow YAML is syntactically valid
4. Confirm `.github/workflows/ci.yml` change is minimal (only added env var line)

**Verification Commands:**
```bash
npx playwright test tests/e2e/batch-panel.spec.ts tests/e2e/seed-endpoint.spec.ts
```

## AC Traceability

| AC | File(s) | Stage |
|----|---------|-------|
| FR-001: Batch Form Submission — fill form, submit, verify success, assert job in list | `tests/e2e/batch-panel.spec.ts` | Stage 2 |
| FR-002: WebSocket Progress Events — listen for `render_progress` events, verify payload fields, assert progress bar updates | `tests/e2e/batch-panel.spec.ts` | Stage 2 |
| FR-003: Seed Endpoint API Schema — POST with request schema, verify response schema, assert `seeded_` prefix | `tests/e2e/seed-endpoint.spec.ts` | Stage 3 |
| FR-004: Seed Endpoint Cleanup — DELETE fixture, verify HTTP 204, assert fixture removed from Library | `tests/e2e/seed-endpoint.spec.ts` | Stage 3 |
| FR-005: Seed Endpoint Integration with Library — create 3 fixtures, verify in Library, delete all, assert cleanup | `tests/e2e/seed-endpoint.spec.ts` | Stage 3 |
| NFR-001: WebSocket Latency — progress events within 1s, progress bar updates smoothly | `tests/e2e/batch-panel.spec.ts` (real-time event assertions) | Stage 2 |
| NFR-002: API Idempotency — multiple POST creates separate fixtures, DELETE idempotent on scope | `tests/e2e/seed-endpoint.spec.ts` | Stage 3 |
| NFR-003: Testing Mode Gate — seed endpoint requires `STOAT_TESTING_MODE=true`, returns HTTP 403 without it | `.github/workflows/ci.yml` (env var added), `tests/e2e/seed-endpoint.spec.ts` (verification) | Stage 1, 3 |

## Quality Gates

### Pre-Implementation Checks
- Verify `STOAT_TESTING_MODE` is recognized by `require_testing_mode()` dependency in API
- Confirm WebSocket event schema: `render_progress` type with correct payload fields
- Verify seed endpoint returns HTTP 201 on success, HTTP 403 if testing mode disabled

### Test Execution (CI)
```bash
# Stage 2 verification
npx playwright test tests/e2e/batch-panel.spec.ts

# Stage 3 verification
npx playwright test tests/e2e/seed-endpoint.spec.ts

# Stage 4 integration
npx playwright test tests/e2e/batch-panel.spec.ts tests/e2e/seed-endpoint.spec.ts
```

### CI Integration
- `.github/workflows/ci.yml` updated with `STOAT_TESTING_MODE: "true"` env var
- Tests run in existing `e2e` job on every PR merge
- Timeout: batch tests may take 30–60 seconds (real batch job processing); Playwright test timeout should be ≥60s for feature 002
- No additional CI jobs or workflow changes beyond env var addition

## Risks

| Risk | Probability | Mitigation |
|------|-------------|------------|
| STOAT_TESTING_MODE not set in CI | High if skipped | Feature 002 is RESPONSIBLE for CI change; Stage 1 is prerequisite for Stages 2–3 |
| Seed endpoint returns HTTP 403 in PR checks | High if Stage 1 skipped | Add env var to workflow before running J606 tests |
| Batch job takes too long, test times out | Medium | Use reasonable timeout (60s); real batch jobs are mocked in test mode (fast) |
| WebSocket events don't arrive | Medium | Verify server is broadcasting events; use `page.waitForEvent("websocket")` with explicit event type check |
| Fixture name collision in parallel tests | Low | Use `Date.now()` suffix in fixture names to guarantee uniqueness across parallel workers |

## Commit Message

```
feat(BL-297): Add E2E tests for batch panel WebSocket and seed endpoint (J603, J606)

Implement J603 and J606 test journeys covering batch panel WebSocket event
handling and seed endpoint API roundtrip testing. J603 verifies render_progress
event schema and progress bar updates in real-time. J606 tests seed endpoint
creation, deletion, and Library integration.

Also adds STOAT_TESTING_MODE=true env var to ci.yml e2e job to unblock seed
endpoint (returns HTTP 403 without the flag).

Acceptance Criteria:
- FR-001: Batch form submission succeeds and job appears in list
- FR-002: WebSocket progress events arrive with correct payload, bar updates real-time
- FR-003: Seed endpoint POST creates fixtures with seeded_ prefix
- FR-004: Seed endpoint DELETE removes fixtures from Library
- FR-005: Multiple seeded fixtures coexist and are cleanable

Test Files:
- tests/e2e/batch-panel.spec.ts (new)
- tests/e2e/seed-endpoint.spec.ts (new)
- .github/workflows/ci.yml (updated: add STOAT_TESTING_MODE env var)

Backlog: BL-297
```