# Implementation Plan: async-blocking-ci-gate

## Overview

Add `"ASYNC"` to the ruff lint select list in `pyproject.toml` to enable ASYNC221/210/230 rules. Fix the `health.py:96` ASYNC221 violation by converting `_check_ffmpeg()` to use `asyncio.to_thread()`.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Modify | Add "ASYNC" to ruff lint select list |
| `src/stoat_ferret/api/routers/health.py` | Modify | Convert _check_ffmpeg() to use asyncio.to_thread(subprocess.run, ...) |

## Test Files

`tests/test_api/test_health.py`

## Implementation Stages

### Stage 1: Enable ruff ASYNC rules

1. In `pyproject.toml`:
   - Change `select = ["E", "F", "I", "UP", "B", "SIM"]` to `select = ["E", "F", "I", "UP", "B", "SIM", "ASYNC"]`

2. Run ruff to identify violations:
   ```bash
   uv run ruff check src/ tests/ --select ASYNC
   ```
   Expected: only `health.py:96` triggers ASYNC221 (verified in Task 006 Investigation 1)

**Verification:**
```bash
uv run ruff check src/ tests/ --select ASYNC
```

### Stage 2: Fix health.py ASYNC221 violation

1. In `src/stoat_ferret/api/routers/health.py`:
   - Add `import asyncio` if not present
   - In `_check_ffmpeg()`, wrap the `subprocess.run()` call with `asyncio.to_thread()`:
     ```python
     result = await asyncio.to_thread(
         subprocess.run,
         [ffmpeg_path, "-version"],
         capture_output=True, timeout=5, check=False,
     )
     ```
   - Make `_check_ffmpeg()` an `async def` if not already
   - Update callers of `_check_ffmpeg()` to `await` the result

**Verification:**
```bash
uv run ruff check src/stoat_ferret/api/routers/health.py --select ASYNC
uv run pytest tests/test_api/test_health.py -v
```

### Stage 3: Full quality gates

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Test Infrastructure Updates

- Existing health endpoint tests may need update if `_check_ffmpeg()` becomes async
- No new test infrastructure needed

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Additional ASYNC violations surfacing — verified: none beyond health.py. See `006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat: enable ruff ASYNC rules and fix health.py blocking call (BL-077)
```
