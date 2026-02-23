# Theme 02: job-controls

## Description

Add user-facing job progress reporting and cooperative cancellation to the scan pipeline. Both features extend `AsyncioJobQueue` and touch the same layers: queue data model, scan handler, REST API, and frontend. Depends on Theme 1 completing — progress and cancellation are meaningless if the event loop is frozen.

## Features

- **001-progress-reporting**
- **002-job-cancellation**

## Live Progress

For current per-feature execution status, see `version-state.json` in the version outbox directory.
