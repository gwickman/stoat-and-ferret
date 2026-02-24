# v010 Version Design

## Overview

**Version:** v010
**Title:** Fix the P0 async blocking bug, add CI guardrails to prevent recurrence, then build user-facing job progress and cancellation on the working pipeline.
**Themes:** 2

## Backlog Items

- [BL-072](docs/auto-dev/BACKLOG.md#bl-072)
- [BL-073](docs/auto-dev/BACKLOG.md#bl-073)
- [BL-074](docs/auto-dev/BACKLOG.md#bl-074)
- [BL-077](docs/auto-dev/BACKLOG.md#bl-077)
- [BL-078](docs/auto-dev/BACKLOG.md#bl-078)

## Design Context

### Rationale

BL-072 (P0) blocks all async-dependent features. Fixing it first restores event-loop correctness, enabling CI guardrails (BL-077, BL-078) and user-facing controls (BL-073, BL-074). Theme grouping by root cause (async fix) and modification point (job controls) minimizes merge conflicts.

### Constraints

- Python >=3.10 compatibility required (asyncio.Event, create_subprocess_exec)
- Theme 2 depends on Theme 1 completing — progress/cancellation need a working event loop
- No new create_app() kwargs — progress and cancellation are internal to job queue
- Frontend already reads progress field — only backend population needed

### Assumptions

- Only health.py:96 triggers ASYNC221 beyond the BL-072 target (verified)
- asyncio.Event creation is safe in _AsyncJobEntry (verified — only created inside async def submit())
- 2-second responsiveness threshold is adequate for in-process ASGI transport
- Two new scan_directory() parameters is within KISS/YAGNI bounds

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-async-pipeline-fix | Fix the P0 blocking subprocess.run() in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails and an integration test to prevent recurrence. | 3 |
| 2 | 02-job-controls | Add user-facing job progress reporting and cooperative cancellation to the scan pipeline, extending AsyncioJobQueue and wiring through to the frontend. | 2 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (async-pipeline-fix): Fix the P0 blocking subprocess.run() in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails and an integration test to prevent recurrence.
- [ ] Theme 02 (job-controls): Add user-facing job progress reporting and cooperative cancellation to the scan pipeline, extending AsyncioJobQueue and wiring through to the frontend.
