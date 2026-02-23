# Theme 01: async-pipeline-fix

## Description

Fix the P0 blocking `subprocess.run()` in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails (ruff ASYNC rules) and an integration test to prevent this class of bug from recurring. All three features address the same root cause — blocking subprocess calls in async context.

## Features

- **001-fix-blocking-ffprobe**
- **002-async-blocking-ci-gate**
- **003-event-loop-responsiveness-test**

## Live Progress

For current per-feature execution status, see `version-state.json` in the version outbox directory.
