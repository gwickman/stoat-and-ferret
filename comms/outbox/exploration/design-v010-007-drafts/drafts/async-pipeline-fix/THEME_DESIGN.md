# Theme: async-pipeline-fix

## Goal

Fix the P0 blocking `subprocess.run()` in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails (ruff ASYNC rules) and an integration test to prevent this class of bug from recurring. All three features address the same root cause — blocking subprocess calls in async context.

## Design Artifacts

See `comms/outbox/versions/design/v010/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | fix-blocking-ffprobe | BL-072 | Convert ffprobe_video() from blocking subprocess.run() to async create_subprocess_exec() |
| 002 | async-blocking-ci-gate | BL-077 | Add ruff ASYNC rules to detect blocking calls in async functions at CI time |
| 003 | event-loop-responsiveness-test | BL-078 | Integration test verifying the event loop stays responsive during scan |

## Dependencies

- No external dependencies — this is the first theme in v010
- BL-072 must complete before BL-077 (ruff ASYNC rules would fail on unfixed code)
- BL-072 must complete before BL-078 (the test validates the fix)

## Technical Approach

- Convert `ffprobe_video()` from `subprocess.run()` to `asyncio.create_subprocess_exec()` with `communicate()` — native async I/O, no thread pool overhead (see `004-research/external-research.md` Section 1)
- Enable ruff ASYNC221/210/230 rules via 1-line config change in `pyproject.toml` — AST-based detection replaces the originally-planned grep script (see `004-research/external-research.md` Section 2)
- Handle `health.py:96` ASYNC221 violation by converting `_check_ffmpeg()` to `asyncio.to_thread(subprocess.run, ...)`
- Create event-loop responsiveness integration test using `httpx.AsyncClient` with ASGI transport and simulated-slow async ffprobe (see `004-research/external-research.md` Section 4)

## Risks

| Risk | Mitigation |
|------|------------|
| CI runner timing for 2-second responsiveness threshold | Keep generous threshold; increase to 5s if flaky. See `006-critical-thinking/risk-assessment.md` |
| Additional ASYNC rule violations beyond health.py | Verified: zero additional violations. See `006-critical-thinking/investigation-log.md` Investigation 1 |
| executor.py blocking subprocess.run() future impact | Not a v010 concern — sync-only file, ruff won't flag. Documented as tech debt |
