# 005-Logical Design: v010 Async Pipeline & Job Controls

v010 is structured as 2 themes with 5 features total, addressing 5 mandatory backlog items (BL-072, BL-073, BL-074, BL-077, BL-078). Theme 1 fixes the P0 async blocking bug and adds CI guardrails. Theme 2 builds user-facing progress reporting and job cancellation on the corrected pipeline. All features are implementable with existing patterns and no external dependencies.

## Theme Overview

### Theme 1: 01-async-pipeline-fix (3 features)

Fix the blocking `subprocess.run()` in ffprobe that freezes the event loop during scans, then add CI guardrails (ruff ASYNC rules) and a runtime regression test.

| Feature | Backlog | Goal |
|---------|---------|------|
| 001-fix-blocking-ffprobe | BL-072 (P0) | Convert ffprobe to asyncio.create_subprocess_exec() |
| 002-async-blocking-ci-gate | BL-077 (P2) | Enable ruff ASYNC rules for CI detection |
| 003-event-loop-responsiveness-test | BL-078 (P2) | Integration test for event-loop responsiveness |

### Theme 2: 02-job-controls (2 features)

Add progress reporting and cooperative cancellation to the async job queue and scan pipeline.

| Feature | Backlog | Goal |
|---------|---------|------|
| 001-progress-reporting | BL-073 (P1) | Wire progress % from scan handler through to frontend |
| 002-job-cancellation | BL-074 (P1) | Add cancel endpoint and cooperative cancellation |

## Key Decisions

1. **asyncio.create_subprocess_exec() over asyncio.to_thread()** for ffprobe — native async I/O, no thread pool overhead. Source: `004-research/external-research.md`
2. **Ruff ASYNC rules over custom grep script** for CI detection — AST-aware, 1-line config change, catches broader class of blocking calls. Source: `004-research/external-research.md`
3. **asyncio.Event per job for cancellation** — lightweight, awaitable, stdlib only. Source: `004-research/external-research.md`
4. **0 new create_app() kwargs** — progress and cancellation are internal to AsyncioJobQueue. Source: `004-research/codebase-patterns.md`
5. **health.py subprocess.run() handled via asyncio.to_thread()** — consistent with v010 async theme, avoids noqa suppression.

## Dependencies

- **Theme 2 depends on Theme 1** — progress/cancellation require a responsive event loop
- **Within Theme 1**: 002 and 003 both depend on 001 (fix must land before guardrails/tests)
- **Within Theme 2**: 002 depends on 001 (both modify _AsyncJobEntry and scan_directory; sequential avoids conflicts)
- **External**: v011 depends on v010 for progress reporting (scan UX improvements)

## Risks and Unknowns

| Risk | Severity | Summary |
|------|----------|---------|
| health.py ASYNC221 violation | Medium | Enabling ruff ASYNC rules will flag health.py; needs handling in BL-077 |
| CI runner timing for 2s threshold | Medium | BL-078 responsiveness test may be flaky on slow CI runners |
| scan_directory() parameter growth | Medium | Three features modify the same function; careful ordering required |
| executor.py future blocking | Low | Sync subprocess.run in executor.py is not in async context yet; future risk |
| asyncio.Event creation timing | Low | Must be created on event loop thread; verify test fixtures |
| Additional ASYNC rule violations | Low | Full ASYNC scan may find violations beyond health.py |

See [risks-and-unknowns.md](./risks-and-unknowns.md) for detailed analysis and investigation recommendations.

## Artifacts

| File | Description |
|------|-------------|
| [logical-design.md](./logical-design.md) | Complete logical design with theme/feature breakdown, execution order, and research sources |
| [test-strategy.md](./test-strategy.md) | Per-feature test requirements (unit, integration, API, frontend) |
| [risks-and-unknowns.md](./risks-and-unknowns.md) | All identified risks and unknowns for Task 006 critical thinking |
