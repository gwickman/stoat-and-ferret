# v010 Backlog Verification

Backlog verification for v010 (Async Pipeline & Job Controls): 5 items checked, 5 completed by this task, 0 already complete.

## Items Verified

**5** unique BL-XXX references found across PLAN.md and feature requirements.

All 5 items were planned in PLAN.md and confirmed in feature requirements.md files. No discrepancies between the two sources.

## Items Completed

All 5 items were open and completed by this task:

| Item | Title | Theme | Version |
|------|-------|-------|---------|
| BL-072 | Fix blocking subprocess.run() in ffprobe freezing async event loop | async-pipeline-fix | v010 |
| BL-073 | Add progress reporting to job queue and scan handler | job-controls | v010 |
| BL-074 | Implement job cancellation support for scan and job queue | job-controls | v010 |
| BL-077 | Add CI quality gate for blocking calls in async context | async-pipeline-fix | v010 |
| BL-078 | Add event-loop responsiveness integration test for scan pipeline | async-pipeline-fix | v010 |

## Already Complete

None. All 5 items were still open at the time of verification.

## Unplanned Items

None. All BL-XXX references in feature requirements.md files matched those listed in PLAN.md.

## Orphaned Items

None. No open backlog items reference v010 in their description or notes outside of the planned feature set.

## Issues

None. All 5 items were completed successfully.

## Hygiene Observations

### Staleness Detection

- **Stale items (open > 90 days):** 0
- **Intentionally deferred items:** 0

All 11 open items were created within the last 90 days (earliest: BL-019, 2026-02-06). No staleness concerns.

### Tag Consistency Review

- **Orphaned tags:** 81 tags exist only on completed/cancelled items and are unused by any active item
- This is expected given the project's history: 65 completed items across v001-v010 accumulated version-specific tags (e.g., `v004`, `v005`, `v006`, `v007`) and feature-specific tags (e.g., `filters`, `database`, `thumbnails`) that are no longer relevant to the 11 open items

**Top 10 active tags (on open items):**

| Tag | Count |
|-----|-------|
| wiring-gap | 3 |
| rust-python | 3 |
| gui | 3 |
| documentation | 3 |
| user-feedback | 3 |
| dead-code | 2 |
| api-surface | 2 |
| rca | 2 |
| windows | 1 |
| agents-md | 1 |

### Size Calibration

**v010 completed items by size:**

| Size | Count | Items |
|------|-------|-------|
| L | 4 | BL-072, BL-073, BL-077, BL-078 |
| M | 1 | BL-074 |

**Observations:**
- BL-077 (CI quality gate, size L) was implemented as a 1-line ruff config change plus a small health.py conversion. Actual complexity was closer to S/M. The original description assumed a custom grep-based CI script; the ruff ASYNC rules approach was significantly simpler.
- BL-074 (job cancellation, size M) involved changes across 5 layers (queue data model, protocol, scan handler, REST API, frontend). Actual complexity may have been closer to L.
- BL-072, BL-073, BL-078 (all size L) appeared appropriately sized given cross-layer changes and test migration work.
