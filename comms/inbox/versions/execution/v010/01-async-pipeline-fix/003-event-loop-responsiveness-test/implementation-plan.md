# Implementation Plan: event-loop-responsiveness-test

## Overview

Create an integration test using `httpx.AsyncClient` with ASGI transport that verifies the event loop stays responsive during a scan with simulated-slow async ffprobe. The test concurrently polls the job status endpoint and asserts it responds within 2 seconds.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `tests/test_integration/test_event_loop_responsiveness.py` | Create | New integration test for event-loop responsiveness during scan |
| `pyproject.toml` | Modify | Add "integration" and "slow" pytest markers if not already registered |

## Test Files

`tests/test_integration/test_event_loop_responsiveness.py`

## Implementation Stages

### Stage 1: Register pytest markers

1. In `pyproject.toml`, under `[tool.pytest.ini_options]`, add markers if not already present:
   ```toml
   markers = [
       "slow: marks tests as slow (deselect with '-m \"not slow\"')",
       "integration: marks tests as integration tests",
   ]
   ```

**Verification:**
```bash
uv run pytest --markers | grep -E "slow|integration"
```

### Stage 2: Create the integration test

1. Create `tests/test_integration/test_event_loop_responsiveness.py`:
   - Create a simulated-slow async ffprobe function that uses `asyncio.sleep(0.5)` per file
   - Build the app with the simulated ffprobe patched in
   - Use `httpx.AsyncClient` with ASGI transport (in-process, no network)
   - Start a scan via `POST /api/v1/scan`
   - While scan runs, poll `GET /api/v1/jobs/{id}` with explicit `asyncio.wait_for(response, timeout=2.0)`
   - Assert the response is received within the timeout
   - Document in the test docstring that the 2-second threshold is intentionally generous for in-process ASGI transport (typical response <10ms); if flaky on CI, increase to 5 seconds before investigating further
   - Mark with `@pytest.mark.slow` and `@pytest.mark.integration`

**Verification:**
```bash
uv run pytest tests/test_integration/test_event_loop_responsiveness.py -v -m "slow"
```

### Stage 3: Full quality gates

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Test Infrastructure Updates

- New `tests/test_integration/` directory may need an `__init__.py` or conftest
- `httpx` already a project dependency — no new dependencies
- May need a conftest fixture for creating the app with simulated-slow ffprobe

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- CI runner timing variability — 2s threshold is generous for in-process ASGI. Increase to 5s if flaky. See `006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat: add event-loop responsiveness integration test (BL-078)
```