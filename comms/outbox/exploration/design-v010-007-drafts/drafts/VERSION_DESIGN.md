# Version Design: v010

## Description

Fix the P0 async blocking bug, add CI guardrails to prevent recurrence, then build user-facing job progress and cancellation on the working pipeline.

v010 addresses the root cause of the "scan directory hangs forever" bug (BL-072) where synchronous `subprocess.run()` in `ffprobe_video()` blocks the entire asyncio event loop. After restoring async correctness, CI guardrails prevent this class of bug from recurring, and user-facing controls (progress, cancellation) are built on the now-working async pipeline.

## Design Artifacts

Full design analysis available at: `comms/outbox/versions/design/v010/`

## Constraints and Assumptions

- Python >=3.10 compatibility required across ubuntu/macos/windows CI matrix
- Theme 2 depends on Theme 1 completing — progress/cancellation need a working event loop
- No new `create_app()` kwargs — progress and cancellation are internal to the job queue
- Frontend (`ScanModal.tsx`) already reads `progress` field — only backend population needed
- Two new `scan_directory()` keyword-only parameters (`progress_callback`, `cancel_event`) are within KISS/YAGNI bounds

See `comms/outbox/versions/design/v010/001-environment/version-context.md` for full context.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `asyncio.create_subprocess_exec()` over `asyncio.to_thread()` for ffprobe | Native async I/O, no thread pool overhead, `communicate()` handles pipes cleanly |
| Ruff ASYNC rules over custom grep script for CI gate | AST-aware detection, 1-line config change, maintained by ruff community |
| `asyncio.Event` per job for cancellation | Lightweight, awaitable, thread-safe, stdlib only |
| Update `AsyncJobQueue` Protocol for `set_progress`/`cancel` | Prevents InMemoryJobQueue test double drift across 8+ test files |
| Keyword-only parameters for new `scan_directory()` args | Clean callsites, explicit intent, avoids positional confusion |

See `comms/outbox/versions/design/v010/006-critical-thinking/risk-assessment.md` for rationale.

## Theme Overview

| # | Theme | Goal | Backlog Items |
|---|-------|------|---------------|
| 1 | async-pipeline-fix | Fix P0 blocking ffprobe, add CI guardrails and regression test | BL-072, BL-077, BL-078 |
| 2 | job-controls | Add progress reporting and cooperative cancellation to scan pipeline | BL-073, BL-074 |

See THEME_INDEX.md for feature-level details.
