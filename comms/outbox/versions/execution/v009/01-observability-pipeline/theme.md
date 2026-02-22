# Theme 01: observability-pipeline

## Description

Wire the three observability components that exist as dead code into the application's DI chain and startup sequence. After this theme, FFmpeg operations emit metrics and structured logs, database mutations produce audit entries, and all logs are persisted to rotating files.

## Features

- **001-ffmpeg-observability**
- **002-audit-logging**
- **003-file-logging**

## Live Progress

For current per-feature execution status, see `version-state.json` in the version outbox directory.
