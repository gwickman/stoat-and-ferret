# Decision Record: CI Timeout Hardening

**Date:** 2026-05-05
**Author:** auto-dev (v058 Feature 001)
**Backlog:** BL-327
**Status:** Accepted

## Context

The windows-latest CI runner with Python 3.10 has exhibited chronic test hangs across multiple
consecutive versions: v048, v053, v054, and v055. The v055 retrospective identified the pattern
explicitly, with `ci: retrigger after stuck windows-latest 3.10 runner` commits appearing on three
consecutive feature PRs (#373, #374, #375).

Despite having an informal merge policy permitting merges when windows-latest 3.10 hangs (treating
it as a known infrastructure issue), there had been no investment in root cause diagnosis or
remediation.

## Root Cause Analysis

Structural comparison of CI job configurations revealed a clear asymmetry:

| Job | `timeout-minutes` | `--timeout` on pytest | Hangs observed? |
|-----|-------------------|-----------------------|-----------------|
| `test` (main matrix) | **None** | **None** | **Yes — chronic** |
| `smoke-tests` | `10` | `--timeout=120` | No |

The `smoke-tests` job runs on all three OS targets (ubuntu-latest, macos-latest, windows-latest)
and has never exhibited hangs. The `test` job runs the same matrix with no timeouts and hangs
frequently on windows-latest Python 3.10.

**Contributing factor — Python 3.10 asyncio semantics:** In Python 3.10, `asyncio.TimeoutError`
and `builtins.TimeoutError` are distinct types (they were unified in Python 3.11+). Any
asyncio-based timeout logic that catches `TimeoutError` without fully qualifying the type
may silently not fire on Python 3.10, allowing hung async operations to block indefinitely.
The project's CI matrix tests Python 3.10, 3.11, and 3.12, and the hang is specific to
windows-latest 3.10 — consistent with this semantics difference.

## Decision

Add layered timeout guardrails to the `test` job:

1. **Per-test timeout (`--timeout=120`):** Passed to pytest via `pytest-timeout`. Kills any
   individual test that exceeds 120 seconds. This matches the smoke-tests precedent exactly.
   All legitimate tests complete well within this value on normal CI hardware.

2. **Job-level timeout (`timeout-minutes: 30`):** Added to the `test` job block in
   `.github/workflows/ci.yml`. Kills the entire job if it exceeds 30 minutes. This value was
   chosen to account for Rust compilation on cache miss (10–15 minutes) plus full Python test
   execution, while still ensuring infrastructure hangs are visible and bounded.

## Why 30 Minutes (Not 10)

The `smoke-tests` job uses `timeout-minutes: 10` because it does not run Rust compilation —
it only runs `uv run maturin develop` against a cached Rust build. The main `test` job includes
`cargo clippy`, `cargo test`, and `maturin develop` steps that can take 10–15 minutes on a cold
Rust cache. Setting `timeout-minutes: 10` would false-kill legitimate builds.

`timeout-minutes: 30` provides sufficient headroom for worst-case Rust compilation while still
bounding any infrastructure hang to a predictable duration.

## Why 120 Seconds Per Test (Not Shorter)

The 120-second per-test value matches the smoke-tests precedent and is proven not to false-kill
legitimate tests. The longest-running tests in the suite are integration tests involving async
database operations and mock HTTP round-trips; none approach 120 seconds on any platform under
normal conditions.

## Expected Outcome

After this fix:
- `windows-latest` Python 3.10 `test` jobs that would previously hang indefinitely will now
  time out at the per-test level (120s) or job level (30m) and produce a visible `timeout` result.
- Monitoring metric: hang no longer occurs across at least 2 subsequent PR runs on windows-latest
  Python 3.10 (per NFR-002 in requirements).

## References

- `.github/workflows/ci.yml` — implementation location (test job, `timeout-minutes` and
  `Python tests` step)
- `docs/auto-dev/` — v055 retrospective evidence (features #373–#375)
- BL-327 — backlog item tracking this issue
