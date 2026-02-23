# Theme: job-controls

## Goal

Add user-facing job progress reporting and cooperative cancellation to the scan pipeline. Both features extend `AsyncioJobQueue` and touch the same layers: queue data model, scan handler, REST API, and frontend. Depends on Theme 1 completing — progress and cancellation are meaningless if the event loop is frozen.

## Design Artifacts

See `comms/outbox/versions/design/v010/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | progress-reporting | BL-073 | Add progress tracking to job queue and wire through scan handler to frontend |
| 002 | job-cancellation | BL-074 | Add cooperative cancellation with cancel endpoint and partial results |

## Dependencies

- Theme 1 (async-pipeline-fix) must complete first — progress and cancellation require a working async event loop
- Feature 002 (job-cancellation) depends on Feature 001 (progress-reporting) — cancellation builds on the callback pattern established in progress reporting

## Technical Approach

- Add `progress: float | None = None` to `_AsyncJobEntry` and `set_progress()` to `AsyncioJobQueue`; pass callback into `scan_directory()` via factory closure (see `004-research/codebase-patterns.md` Sections 3-6)
- Add `cancel_event: asyncio.Event` to `_AsyncJobEntry` and `cancel()` to `AsyncioJobQueue`; check event between files in scan loop (see `004-research/external-research.md` Section 3)
- Update `AsyncJobQueue` Protocol with `set_progress()` and `cancel()` methods; add no-op stubs to `InMemoryJobQueue` for protocol compliance
- Use keyword-only parameters: `scan_directory(..., *, progress_callback=None, cancel_event=None)`
- Frontend `ScanModal.tsx` already reads `progress` — only backend population needed; cancel button needs enabling and API wiring

## Risks

| Risk | Mitigation |
|------|------------|
| scan_directory() accumulating callback parameters | Two params within KISS bounds; use keyword-only syntax. See `006-critical-thinking/risk-assessment.md` |
| InMemoryJobQueue test double drift | Update Protocol and add no-ops to InMemoryJobQueue. See `006-critical-thinking/investigation-log.md` Investigation 3 |
| asyncio.Event creation timing in _AsyncJobEntry | Verified safe — only created inside async def submit(). See `006-critical-thinking/risk-assessment.md` |