# v010 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: async-pipeline-fix

**Path:** `comms/inbox/versions/execution/v010/01-async-pipeline-fix/`
**Goal:** Fix the P0 blocking `subprocess.run()` in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails (ruff ASYNC rules) and an integration test to prevent this class of bug from recurring. All three features address the same root cause — blocking subprocess calls in async context.

**Features:**

- 001-fix-blocking-ffprobe: Convert ffprobe_video() from blocking subprocess.run() to async create_subprocess_exec()
- 002-async-blocking-ci-gate: Add ruff ASYNC rules to detect blocking calls in async functions at CI time
- 003-event-loop-responsiveness-test: Integration test verifying the event loop stays responsive during scan
### Theme 02: job-controls

**Path:** `comms/inbox/versions/execution/v010/02-job-controls/`
**Goal:** Add user-facing job progress reporting and cooperative cancellation to the scan pipeline. Both features extend `AsyncioJobQueue` and touch the same layers: queue data model, scan handler, REST API, and frontend. Depends on Theme 1 completing — progress and cancellation are meaningless if the event loop is frozen.

**Features:**

- 001-progress-reporting: Add progress tracking to job queue and wire through scan handler to frontend
- 002-job-cancellation: Add cooperative cancellation with cancel endpoint and partial results
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
