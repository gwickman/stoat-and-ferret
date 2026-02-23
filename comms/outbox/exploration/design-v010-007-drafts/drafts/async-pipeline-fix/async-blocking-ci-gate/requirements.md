# Requirements: async-blocking-ci-gate

## Goal

Add ruff ASYNC rules to detect blocking calls in async functions at CI time, preventing recurrence of the BL-072 class of bug.

## Background

Backlog Item: BL-077

No automated check exists to detect synchronous blocking calls inside async code. Ruff, mypy, and pytest all passed despite `subprocess.run()` being called from an async scan handler. The ruff ASYNC rule set (ASYNC221, ASYNC210, ASYNC230) provides AST-based detection as a 1-line config change, replacing the originally-planned grep-based CI script.

## Functional Requirements

**FR-001: Enable ruff ASYNC rules**
- Add `"ASYNC"` to the ruff lint `select` list in `pyproject.toml`
- This enables ASYNC221 (blocking subprocess), ASYNC210 (blocking HTTP), ASYNC230 (blocking file I/O)
- Acceptance: ruff check with ASYNC rules flags a test file containing subprocess.run() inside async def

**FR-002: Fix health.py ASYNC221 violation**
- Convert `_check_ffmpeg()` in `src/stoat_ferret/api/routers/health.py` to use `asyncio.to_thread(subprocess.run, ...)`
- Acceptance: health.py passes ruff ASYNC221 check after conversion

**FR-003: Clean codebase pass**
- `uv run ruff check src/ tests/` must pass with ASYNC rules enabled after BL-072 fix
- Acceptance: zero ASYNC rule violations on the fixed codebase

## Non-Functional Requirements

**NFR-001: Zero CI configuration changes**
- ASYNC rules run as part of existing `uv run ruff check src/ tests/` — no new CI jobs or steps needed

**NFR-002: No false positives**
- AST-based detection only flags `async def` functions, not sync-only files
- Verified: executor.py has subprocess.run() but no async def — will not trigger

## Handler Pattern

Not applicable for v010 — no new handlers introduced.

## Out of Scope

- Converting `executor.py:96` blocking subprocess.run() — sync-only file, not flagged by ruff
- Custom grep-based CI script — replaced by ruff ASYNC rules (superior detection)

## Test Requirements

- Verify ruff check with ASYNC rules flags blocking calls in async functions (manual verification during implementation)
- Verify ruff check passes on the fixed codebase after BL-072 and health.py conversion
- Verify all three ASYNC rules (221, 210, 230) are active

## Reference

See `comms/outbox/versions/design/v010/004-research/` for supporting evidence.
