# Implementation Plan — blackbox-test-catalog

## Overview

Create black box test suite exercising complete workflows through the REST API using recording/fake test doubles.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `tests/test_blackbox/__init__.py` | Package init |
| Create | `tests/test_blackbox/conftest.py` | Black box fixtures with full DI wiring |
| Create | `tests/test_blackbox/test_core_workflow.py` | Scan → project → clips workflow tests |
| Create | `tests/test_blackbox/test_error_handling.py` | Validation and failure scenario tests |
| Create | `tests/test_blackbox/test_edge_cases.py` | Edge cases (empty scan, duplicates, concurrency) |
| Modify | `pyproject.toml` | Register `blackbox` marker |

## Implementation Stages

### Stage 1: Infrastructure
Create `tests/test_blackbox/` directory. Register `blackbox` marker in `pyproject.toml`. Create conftest with `create_app()` wiring using InMemory repos and recording/fake FFmpeg executor.

### Stage 2: Core Workflow Tests
Implement scan → project → clips flow tests. Use fixture factory `create_via_api()` for data setup. Verify each API response matches expected schema and data.

### Stage 3: Error Handling Tests
Test validation errors (invalid paths, missing required fields). Test FFmpeg failure scenarios using FakeFFmpegExecutor with failure-configured outcomes.

### Stage 4: Edge Cases
Test empty scan results, duplicate project name handling, and basic concurrent request behavior.

## Quality Gates

- Black box tests: 9–15 tests total
- All tests pass without FFmpeg installed
- `@pytest.mark.blackbox` on every test
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes
- No internal module imports in test files (only API calls)

## Risks

| Risk | Mitigation |
|------|------------|
| Recording data files become stale | Include recording creation scripts; document update process |
| Complex conftest setup | Keep DI wiring in single conftest; document fixture dependency graph |

## Commit Message

```
feat: add black box test catalog for REST API workflows
```
