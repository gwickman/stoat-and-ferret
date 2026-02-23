# RCA: Blocking subprocess.run() in ffprobe_video()

## Summary

The `ffprobe_video()` function (`src/stoat_ferret/ffmpeg/probe.py:65`) uses synchronous `subprocess.run()`, which blocks the asyncio event loop when called from the async scan handler. This was introduced in v003 (Jan 28, 2026), identified but not remediated in v004 research (Feb 8, 2026), and discovered by a user ~4 weeks later (Feb 23, 2026).

## How It Was Introduced

**v002/T04/F001** (Jan 27) created `ffprobe_video()` as a sync utility with `subprocess.run()`. This was appropriate — no async caller existed yet.

**v003/T03/F003** (Jan 28) created `async def scan_directory()` which calls `ffprobe_video()` directly. The implementation plan designed it this way from the start. Neither the plan nor the completion report flagged the sync/async mismatch.

**v004/T03** (Feb 8-9) wrapped the scan in an `AsyncioJobQueue` with `asyncio.wait_for()` timeout, but did not convert the underlying `ffprobe_video()` to async. The v004 research phase (`codebase-patterns.md:100`) explicitly identified: *"Synchronous blocking within async context — iterates root.glob(pattern), calls ffprobe_video() per file"* — but no backlog item was created and the theme scope only added the queue wrapper.

## Why It Wasn't Caught

1. **No automated check exists.** Ruff, mypy, and pytest all pass. No lint rule flags `subprocess.run()` inside async functions. No integration test verifies event loop responsiveness during scan.

2. **All tests mock the blocking call.** Every scan test patches `ffprobe_video()` with a mock, so the blocking behavior is invisible to the test suite.

3. **Known issue fell through the cracks.** v004 research documented the blocking pattern but the remediation only addressed the job queue layer, not the underlying sync call. No backlog item was created from the research finding.

4. **Feature requirements didn't carry async constraints.** v002's requirements for `ffprobe_video()` had no async specification. When v003 consumed it from async context, there was no review step to verify async compatibility.

## Additional Risk

Two other `subprocess.run()` calls exist in `src/`:
- `executor.py:96` (RealFFmpegExecutor) — will cause the same problem when render jobs use the async job queue
- `health.py:96` (ffmpeg version check) — low impact (runs once, fast timeout)

## Recommendations (Summary)

See `recommendations.md` for full details. Top priorities:

1. **Custom lint check** for blocking calls (`subprocess.run`, `time.sleep`) inside files containing `async def` — catches this class of bug at CI time
2. **Event-loop responsiveness integration test** — the test that would have caught this
3. **Backlog items from research findings** — v004 research identified the issue but no BL-xxx was created

## Output Files

- `evidence-trail.md` — Chronological trace through design, implementation, and discovery
- `recommendations.md` — Specific process/tooling changes with priority ranking
