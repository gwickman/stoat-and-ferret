# Requirements: event-loop-responsiveness-test

## Goal

Create an integration test verifying the event loop stays responsive during scan, serving as a regression guard against future async/blocking issues.

## Background

Backlog Item: BL-078

All current scan tests mock `ffprobe_video()`, making the blocking behavior that caused the "scan hangs forever" bug invisible to the test suite. An event-loop responsiveness test using simulated-slow async processing (not mocks) would have caught the ffprobe blocking bug and guards against regression.

## Functional Requirements

**FR-001: Simulated-slow scan test**
- Create an integration test that starts a directory scan with simulated-slow async ffprobe (`asyncio.sleep()` per file)
- The test must NOT mock ffprobe_video — it must exercise simulated subprocess behavior to detect event-loop blocking
- Acceptance: test starts a scan and concurrently polls job status

**FR-002: Responsiveness assertion**
- While the scan runs, poll `GET /api/v1/jobs/{id}` using `httpx.AsyncClient` with ASGI transport
- Assert response received within 2 seconds via explicit `asyncio.wait_for()`
- Acceptance: polling request completes within 2-second threshold during active scan

**FR-003: Regression detection**
- If someone regresses to blocking `time.sleep()` calls, the event loop would be starved and the polling request would time out, failing the test
- Acceptance: test fails when event loop is blocked (negative validation)

**FR-004: Test markers**
- Mark with `@pytest.mark.slow` and `@pytest.mark.integration`
- Acceptance: test is excluded from fast test runs and included in integration runs

## Non-Functional Requirements

**NFR-001: CI stability**
- 2-second threshold is intentionally generous for in-process ASGI transport (typical response <10ms)
- If flaky on CI, increase to 5 seconds before investigating further
- Document threshold rationale in the test docstring

## Handler Pattern

Not applicable for v010 — no new handlers introduced.

## Out of Scope

- Testing real ffprobe binary — uses simulated-slow async processing
- Testing multiple concurrent scans — single scan responsiveness only
- WebSocket responsiveness testing — HTTP polling only

## Test Requirements

- Integration: app with simulated-slow async ffprobe (asyncio.sleep(0.5) per file)
- Integration: start scan via POST, poll GET /api/v1/jobs/{id} concurrently
- Integration: assert response within 2s via asyncio.wait_for()
- Markers: @pytest.mark.slow, @pytest.mark.integration

## Reference

See `comms/outbox/versions/design/v010/004-research/` for supporting evidence.
