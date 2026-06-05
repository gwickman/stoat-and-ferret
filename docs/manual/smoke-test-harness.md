# Smoke Test Harness Guide

## Overview

The smoke test suite (`tests/smoke/`) verifies end-to-end behavior across the render, preview, WebSocket event, and library-management subsystems. It is designed to be run by operators after deployment or during release verification — not in CI (which lacks a real FFmpeg environment).

Tests are split into two tiers:

- **FFmpeg-independent**: run in any environment; verify API contracts, WS events, and FK guards.
- **FFmpeg-dependent**: require a working `ffmpeg` binary on PATH; verify actual encode/decode behavior.

Run the FFmpeg-independent tier routinely. Run the full suite (both tiers) when verifying a release or discharging a deferred AC.

## Environment Setup

### STOAT_TEST_FFMPEG

Set `STOAT_TEST_FFMPEG=1` to enable FFmpeg-dependent tests. Without it, those tests are automatically skipped via pytest markers. Requires a working `ffmpeg` binary discoverable on `PATH`.

```bash
# Verify ffmpeg is available
ffmpeg -version
```

### Running the suite

```bash
# FFmpeg-independent tests only (safe in any environment)
uv run pytest tests/smoke/ -v

# Full suite including FFmpeg-dependent tests
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -v

# Single test by keyword
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -k <keyword> -v
```

## Test Categories

| Category | FFmpeg required | Description |
|---|---|---|
| WS event assertions | No | Verifies `video_deleted`, `clip_deleted`, and render WS events |
| Output path isolation | Yes | Concurrent renders produce distinct, non-overlapping output paths |
| Render completion | Yes | `render_completed` payload contains expected fields |
| FK guard | No | FK enforcement on referenced-resource DELETE returns 409/422 |
| Preview smoke | No (mock) | Preview workflow completes; Python 3.13 asyncio behavior verified separately (see BL-393 below) |
| Cancel partial file | Yes | Mid-encode cancel sets `partial_file_detected=True` on the job |

## Deferred AC Discharge Procedures

These ACs are classified `deferred_post_merge` in v072 (DECISION-003 from `docs/design/` risk assessment). They cannot be verified in CI due to environment constraints. Run these procedures in a suitable environment before marking v072 fully verified.

**Two distinct deferral reasons:**

- **Python-version-dependent (BL-393-AC-1, BL-393-AC-2):** Deferred because Python 3.13 asyncio semantics are environment-specific. These do not require real FFmpeg — they require running under Python 3.13.
- **FFmpeg-environment-dependent (BL-415-AC-3, BL-394-AC-5):** Deferred because real FFmpeg is needed to observe actual encode/cancel/concurrency behavior. These require `STOAT_TEST_FFMPEG=1`.

---

### BL-393-AC-1: Python 3.13 asyncio race in async_executor does not occur under real FFmpeg load

**AC text:** Under Python 3.13, a preview render that exercises `async_executor.py` completes without deadlock or stall.

**Deferral reason:** Python-version-dependent. Python 3.13 changed asyncio task scheduling; the race is not reproducible under Python 3.10–3.12.

**Discharge command:**

```bash
python3.13 -m pytest tests/smoke/ -k preview_no_deadlock -v
```

**Pass criteria:** Test exits within 30 seconds; no asyncio warnings or `TimeoutError` in stderr.

---

### BL-393-AC-2: Preview smoke test on Python 3.13 completes without asyncio warning

**AC text:** `pytest tests/smoke/` under Python 3.13 emits no `asyncio` `DeprecationWarning` or `RuntimeWarning`.

**Deferral reason:** Python-version-dependent. Warnings are only raised by Python 3.13's stricter asyncio runtime; not observable under earlier versions.

**Discharge command:**

```bash
python3.13 -m pytest tests/smoke/ -W error::DeprecationWarning -W error::RuntimeWarning -v
```

**Pass criteria:** Zero warnings from the `asyncio` module. Test suite exits with code 0.

---

### BL-415-AC-3: Partial file detected after mid-encode cancel

**AC text:** Cancelling a render mid-encode sets `partial_file_detected=True` on the job record.

**Deferral reason:** FFmpeg-environment-dependent. Requires a real FFmpeg encode in progress at the moment of cancel; cannot be simulated with a mock.

**Discharge command:**

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -k partial_file_cancel -v
```

**Pass criteria:** `GET /api/v1/jobs/{id}` returns `"partial_file_detected": true` after a cancel is issued during an active encode. Job status must be `cancelled` or `failed`.

---

### BL-394-AC-5: Concurrent-render stderr drain does not produce contention

**AC text:** Two simultaneous renders complete without stderr pipe deadlock.

**Deferral reason:** FFmpeg-environment-dependent. Pipe deadlock is only observable under real concurrent FFmpeg processes. May be auto-satisfied by BL-403 per-job output path isolation (which eliminates shared pipe contention) — verify empirically.

**Discharge command:**

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -k concurrent_no_contention -v
```

**Pass criteria:** Both renders complete within the test timeout; no `asyncio.TimeoutError` in logs; both jobs reach `completed` status.
