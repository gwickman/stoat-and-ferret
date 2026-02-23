# Evidence Log — v010

## ffprobe Timeout Value

- **Value**: 30 seconds
- **Source**: `src/stoat_ferret/ffmpeg/probe.py:65` — `timeout=30`
- **Data**: Current hardcoded value in `subprocess.run()` call
- **Rationale**: Preserve existing value when converting to async. Proven adequate for production use.

## Job Queue Default Timeout

- **Value**: 300.0 seconds (5 minutes)
- **Source**: `src/stoat_ferret/jobs/queue.py:290` — `DEFAULT_TIMEOUT: float = 300.0`
- **Data**: Class constant on `AsyncioJobQueue`
- **Rationale**: Used by `asyncio.wait_for()` in `process_jobs()`. No change needed for v010.

## Health Check ffmpeg Timeout

- **Value**: 5 seconds
- **Source**: `src/stoat_ferret/api/routers/health.py:96` — `timeout=5`
- **Data**: Hardcoded in `_check_ffmpeg()` function
- **Rationale**: Short timeout appropriate for version check. Low-risk blocking (5s max, infrequent calls).

## Polling Interval (Frontend)

- **Value**: 1000ms (1 second)
- **Source**: `gui/src/components/ScanModal.tsx:72` — `setInterval(..., 1000)`
- **Data**: Frontend polls job status every 1 second
- **Rationale**: Adequate for progress updates. Progress increments per-file, so 1s interval provides smooth UX.

## Responsiveness Threshold (BL-078)

- **Value**: 2 seconds
- **Source**: BL-078 Acceptance Criteria #2 — "responds within 2 seconds"
- **Data**: Specified in backlog item. TBD — requires runtime testing on CI runners.
- **Rationale**: 2s is generous for a simple JSON GET endpoint. May need adjustment per CI runner speed. Use `@pytest.mark.slow` and explicit `asyncio.wait_for(response, timeout=2.0)`.

## create_app() Kwarg Count

- **Value**: 9 current kwargs
- **Source**: `src/stoat_ferret/api/app.py:116-219`
- **Data**: `video_repository`, `project_repository`, `clip_repository`, `job_queue`, `ws_manager`, `effect_registry`, `ffmpeg_executor`, `audit_logger`, `gui_static_path`
- **Rationale**: v010 adds 0 new kwargs. Progress and cancellation are internal to `AsyncioJobQueue`. Below the 6-7 concern threshold noted in v009 retrospective (already exceeded but stable).

## Ruff ASYNC Rule Set Version

- **Value**: Available in ruff >= 0.4 (project requires `ruff>=0.4`)
- **Source**: Ruff docs — `flake8-async` rules (ASYNC2xx)
- **Data**: Project already pins `ruff>=0.4` in dev dependencies
- **Rationale**: No dependency version change needed to enable ASYNC rules.

## Progress Field in Schema

- **Value**: Already defined as `progress: float | None = None`
- **Source**: `src/stoat_ferret/api/schemas/job.py:23`
- **Data**: Field exists in `JobStatusResponse` but is never populated by backend
- **Rationale**: Frontend already reads this field. Only backend population needed.

## Historical Session Durations

- **Source**: query_cli_sessions (session_list, project scope)
- **Data**: v009 feature sessions ranged from 67s to 840s. Typical feature: 100-650s. Explorations: 80-335s. Most sessions 0 errors.
- **Rationale**: v010 features are comparable complexity to v009. Expect similar session durations. Source: query_cli_sessions

## Tool Reliability Data

- **Source**: query_cli_sessions (tool_usage, 60 days)
- **Data**:
  - Bash: 14.8% error rate (15,573 calls) — expected for command execution
  - Edit: 9.9% error rate (2,416 calls) — unique string matching failures
  - WebFetch: 34.9% error rate (83 calls) — disabled by hook, not a risk for v010
  - DeepWiki: 13.3% error rate (45 calls) — timeout-prone (avg 14.5s latency)
  - All MCP auto-dev tools: 0% error rate — highly reliable
- **Rationale**: No tool reliability risks for v010 implementation. All core tools (Read, Grep, Glob, Write) have <4% error rates. Source: query_cli_sessions

## Learning Verification Table

| Learning | Status | Evidence |
|----------|--------|----------|
| LRN-009 | VERIFIED | Handler registration pattern present in `queue.py:303` — `register_handler()` with `_handlers` dict |
| LRN-010 | VERIFIED | `asyncio.Queue` used at `queue.py:298` — no external queue dependencies |
| LRN-050 | VERIFIED | DI pattern at `app.py:158-163` — `_deps_injected` flag active, 9 kwargs |
| LRN-049 | VERIFIED | Guard pattern at `scan.py:83,93` — `if ws_manager:` before broadcasts |
| LRN-043 | VERIFIED | Process learning — CI variability still relevant; no explicit timeouts in current scan tests |
| LRN-033 | VERIFIED | Process learning — BL-072 must complete before BL-077/078 (same dependency) |
| LRN-005 | VERIFIED | Constructor DI at `app.py:116` — all test fixtures use `create_app()` kwargs |
| LRN-040 | VERIFIED | Idempotent guard at `app.py:62-74` — `if getattr(app.state, "_deps_injected", False)` |
| LRN-042 | VERIFIED | Process learning — v010 themes already group by modification point |
| LRN-031 | VERIFIED | Process learning — all 5 BL items have detailed descriptions and testable ACs |
| LRN-045 | VERIFIED | Process learning — BL-072 is first feature in Theme 1 |
| LRN-047 | VERIFIED | WAL pattern established in v009 — not needed for v010 (in-memory progress sufficient) |
