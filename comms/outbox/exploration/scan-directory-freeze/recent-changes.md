# Recent Changes to Scan-Related Code

## Relevant Commits (chronological)

| Commit | Date | Description | Impact |
|--------|------|-------------|--------|
| `cd03e00` | v008 | `feat: build library browser with video grid, search, and scan (#70)` | Initial scan implementation including ScanModal |
| `758db32` | v009 | `feat: add E2E tests for navigation, scan, project creation (#73)` | E2E test coverage |
| `9944b9e` | v009 | `feat(websocket): wire broadcast calls into API operations (#101) (#102)` | Added WebSocket events for scan |
| `82d99b0` | v010 | `exploration: scan-directory-stuck complete` | Identified blocking subprocess + missing progress |
| `32859cc` | v010 | `feat: convert ffprobe_video to async subprocess execution (BL-072) (#103)` | **Fixed** blocking event loop |
| `81984e4` | v010 | `feat: add progress reporting to job queue and scan handler (BL-073) (#106)` | **Fixed** missing progress |
| `a2cdd4a` | v011 | `feat(gui): add directory browser for scan path selection (BL-070) (#108)` | Added DirectoryBrowser component |

## How the Bug Was Introduced

The status string mismatch was present from the **initial implementation** in commit `cd03e00` (v008). The `ScanModal.tsx` `JobStatus` interface was written with `'completed'` while the backend `JobStatus` Python enum used `COMPLETE = "complete"`.

This bug was not caught earlier because:

1. **Masked by the blocking subprocess bug**: Before commit `32859cc`, the event loop was blocked by synchronous `subprocess.run()` calls, so the dialog was already frozen before progress could reach 100%. The previous exploration (`scan-directory-stuck`) focused on that more severe issue.

2. **E2E tests don't catch it**: The E2E test in `gui/e2e/scan.spec.ts` checks for feedback appearing (progress, completion, or error) but uses a mock/stub backend (`InMemoryJobQueue`) that returns results synchronously — the polling loop is never exercised.

3. **Unit tests use mocked fetch**: The `ScanModal.test.tsx` tests mock the fetch responses and hardcode the expected status strings, so they may use `'completed'` consistently between mock and assertion without testing against the real backend.

## What v010 Fixed and What It Didn't

**v010 fixed:**
- Blocking `subprocess.run()` → async subprocess (commit `32859cc`)
- Missing progress field → `set_progress()` with callback (commit `81984e4`)
- Missing cancellation support → cooperative cancel via `asyncio.Event`

**v010 did NOT fix:**
- Status string mismatch (`"complete"` vs `"completed"`) — **still broken**
- Missing `"timeout"` handling in frontend — **still broken**

These two issues are the remaining blockers for the scan feature to work end-to-end. With the v010 fixes, the scan now correctly processes files, reports progress, and reaches 100% — but the frontend never transitions out of the scanning state because it's looking for the wrong completion string.
