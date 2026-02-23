# Theme Index: v010

## 01-async-pipeline-fix

Fix the P0 blocking subprocess.run() in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails and an integration test to prevent recurrence.

**Features:**

- 001-fix-blocking-ffprobe: Convert ffprobe_video() from blocking subprocess.run() to async create_subprocess_exec()
- 002-async-blocking-ci-gate: Add ruff ASYNC rules to detect blocking calls in async functions at CI time
- 003-event-loop-responsiveness-test: Integration test verifying the event loop stays responsive during scan

## 02-job-controls

Add user-facing job progress reporting and cooperative cancellation to the scan pipeline, extending AsyncioJobQueue and wiring through to the frontend. Depends on Theme 1.

**Features:**

- 001-progress-reporting: Add progress tracking to job queue and wire through scan handler to frontend
- 002-job-cancellation: Add cooperative cancellation with cancel endpoint and partial results
