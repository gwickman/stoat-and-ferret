# Evidence Trail: Blocking subprocess.run() in ffprobe_video()

Chronological trace from design through implementation to discovery.

## 1. Design Docs Specified Async FFprobe (Pre-v002)

**`docs/design/02-architecture.md:77-83`** — The Processing Layer diagram shows "FFprobe Query (metadata) +caching" alongside "Job Executor (async queue)". The architecture doc describes the subprocess manager as wrapping FFmpeg/FFprobe with "Timeout management with configurable limits" (line 786).

**`docs/design/03-prototype-design.md:111-114`** — The Processing Layer diagram shows `FFprobe Wrapper` alongside `FFmpeg Executor (Protocol)` and `Job Queue`. No explicit async requirement is stated for FFprobe, but the enclosing layer is presented as async infrastructure.

**Gap:** Neither design doc explicitly specifies whether `ffprobe_video()` itself must be async or whether it runs in a thread pool. The async requirement is implicit from the context but never stated as a constraint.

## 2. v002/T04/F001 — ffprobe-wrapper Implemented as Sync (Jan 27, 2026)

**`comms/inbox/versions/execution/v002/04-ffmpeg-integration/001-ffprobe-wrapper/requirements.md`** — Requirements specify `ffprobe_video(path: str, ffprobe_path: str = "ffprobe") -> VideoMetadata`. No async requirement mentioned.

**`comms/inbox/versions/execution/v002/04-ffmpeg-integration/001-ffprobe-wrapper/implementation-plan.md:37-64`** — The plan explicitly uses `subprocess.run()`. No mention of async, `asyncio.create_subprocess_exec()`, or `asyncio.to_thread()`.

**`src/stoat_ferret/ffmpeg/probe.py:65`** — Delivered code uses `subprocess.run()` with `capture_output=True, timeout=30`.

**`comms/outbox/versions/execution/v002/04-ffmpeg-integration/001-ffprobe-wrapper/completion-report.md`** — All 3/3 acceptance criteria passed. Quality gates (ruff, mypy, pytest) all passed. No note about async compatibility.

**Context:** At this point (v002), there was no async caller. The scan endpoint didn't exist yet. `subprocess.run()` was a reasonable choice for a standalone utility.

## 3. v003/T03/F003 — Sync ffprobe Called from Async Scan (Jan 28, 2026)

**`comms/inbox/versions/execution/v003/03-library-api/003-videos-scan/implementation-plan.md:49-79`** — The plan defines `async def scan_directory()` and calls `probe_video(str_path)` (sync) on line 79 inside the async function. **This is where the blocking-in-async bug was introduced.**

**`comms/outbox/versions/execution/v003/03-library-api/003-videos-scan/completion-report.md`** — 4/4 acceptance criteria passed. Quality gates passed. No mention of the sync/async mismatch.

**`src/stoat_ferret/api/services/scan.py:154`** — Current code: `metadata = ffprobe_video(str_path)` inside `async def scan_directory()`.

**Gap:** The v003 implementation plan was designed with the blocking call from the start. Neither the design phase nor the completion report identified the sync-in-async hazard.

## 4. v004/T03 — Async Job Queue Added, Blocking Call Preserved (Feb 8-9, 2026)

**`comms/outbox/versions/design/v004/004-research/codebase-patterns.md:100`** — The v004 research explicitly identified the problem: *"Synchronous blocking within async context — iterates root.glob(pattern), calls ffprobe_video() per file, writes to repo. No job queue, no progress reporting."*

**`comms/outbox/versions/execution/v004/03-async-scan/retrospective.md`** — Describes wrapping scan in `AsyncioJobQueue` with `asyncio.wait_for()` timeout. Notes "no quality-gaps documents were generated." Does not mention that the underlying `ffprobe_video()` still blocks the event loop.

**Gap:** v004 research correctly identified the blocking pattern but the remediation only added the job queue wrapper — it did not convert `ffprobe_video()` to async. The retrospective did not flag this as residual debt.

## 5. Bug Discovered via User Testing (Feb 23, 2026)

**`comms/outbox/exploration/scan-directory-stuck/README.md`** — Exploration triggered by user-reported scan hang. Traced the root cause to `subprocess.run()` in `probe.py:65`.

**`docs/auto-dev/BACKLOG.md` (BL-072)** — P0 backlog item created: "Fix blocking subprocess.run() in ffprobe freezing async event loop."

## 6. Other Blocking subprocess.run() Instances (Current)

Grep of `src/` shows three blocking `subprocess.run()` calls:
- `src/stoat_ferret/ffmpeg/probe.py:65` — **ffprobe** (critical: called in scan loop)
- `src/stoat_ferret/ffmpeg/executor.py:96` — **ffmpeg** (called from `RealFFmpegExecutor.run()`)
- `src/stoat_ferret/api/routers/health.py:96` — **ffmpeg -version** (health check, low impact)

The executor is not currently called from async context in production, but will be when render jobs are implemented via the async job queue — the same pattern will recur.

## Summary of Responsibility

| Stage | Version | What Happened | Who Could Have Caught It |
|-------|---------|---------------|-------------------------|
| Design | v002 | Requirements didn't specify async | Requirements author |
| Implementation | v002 | `subprocess.run()` used (appropriate at the time) | N/A — no async caller existed |
| Design | v003 | Implementation plan called sync fn from async | Plan author / reviewer |
| Implementation | v003 | Delivered as planned with blocking call | Quality gates (none check for this) |
| Research | v004 | **Explicitly identified** the blocking pattern | N/A — it was identified |
| Implementation | v004 | Added job queue but didn't fix the blocking call | Theme scope / retrospective |
| Discovery | user | User-reported scan hang ~4 weeks later | Integration/E2E testing |
