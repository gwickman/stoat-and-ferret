# RCA: Job Cancellation Omission

## Summary

Job cancellation was specified in **6 locations** across the original design documents (roadmap, API spec, architecture, GUI wireframes, database schema) but was never implemented. The root cause is a chain of three process failures:

1. **Backlog creation gap:** BL-027 (async job queue) did not include cancellation in its acceptance criteria, despite the design docs requiring it.
2. **Descoping without tracking:** v004's async-scan-endpoint requirements explicitly descoped cancellation but created no backlog item to track the deferred work.
3. **Retrospective dead end:** Both v004 theme and version retrospectives identified the gap as tech debt but did not create backlog items, leaving it invisible to future version planning.

The consequence was compounded in v005, where the library browser shipped a `Cancel` button in the scan modal that is **disabled during scanning** — the button exists in the UI but has no backend to call. No version between v004 and v009 addressed the gap. BL-074 (cancellation) was only created on 2026-02-23.

## Key Findings

### What the design docs specified
- `POST /render/cancel/{job_id}` endpoint with `cancelled` status response
- `cancelled` as an explicit status in the database schema
- `[Cancel]` button on active render jobs in GUI wireframes
- "Build job cancellation capability" as a roadmap milestone item

### What was delivered
- `AsyncioJobQueue` with no `cancel()` method
- `JobStatus` enum: PENDING, RUNNING, COMPLETE, FAILED, TIMEOUT — no CANCELLED
- No cancel API endpoint
- Scan handler with no cancellation checkpoint
- Frontend cancel button disabled during scans, calling only `onClose()` (close modal, not cancel job)

### Root cause chain
1. **BL-027 was underspecified** — acceptance criteria covered async submission and polling but omitted cancellation despite the design docs requiring it
2. **v004 requirements descoped without backlog** — `002-async-scan-endpoint/requirements.md:32` explicitly lists "Scan cancellation — not required for initial implementation" under Out of Scope, but no deferred backlog item was created
3. **Retrospectives didn't close the loop** — both the theme retrospective (`retrospective.md:49`) and version retrospective (`retrospective.md:72`) noted the gap as low-priority tech debt but neither generated a backlog item
4. **v005 GUI built against the incomplete API** — scan modal shipped a cancel button without verifying the backend supported cancellation

### Already addressed
- **BL-074** (cancellation) and **BL-073** (progress reporting) created 2026-02-23
- **LRN-016** captures the principle of validating acceptance criteria against the codebase during design (though for a different failure mode)

## Recommendations

Five process changes are recommended (see `recommendations.md` for details):

1. **Track descoped items as backlog** — When requirements descope a design-doc feature, create a `deferred` backlog item
2. **Retrospective debt ingestion** — Cross-reference tech debt from retrospectives into the backlog
3. **Design-doc traceability** — Verify backlog items cover all sub-items of referenced design-doc milestones
4. **GUI-backend API validation** — Require acceptance criteria verifying backend endpoints exist for interactive UI controls
5. **Split Out of Scope sections** — Distinguish "deferred" (needs backlog) from "not applicable" (no tracking needed)

## Evidence Sources

| Document | Key Evidence |
|----------|-------------|
| `docs/design/01-roadmap.md:455,462,483` | Cancellation specified in 3 milestones |
| `docs/design/05-api-specification.md:1146-1158` | Full cancel API spec |
| `docs/design/02-architecture.md:885` | `cancelled` in DB schema |
| `docs/design/08-gui-architecture.md:381` | Cancel button in wireframe |
| `comms/inbox/.../002-async-scan-endpoint/requirements.md:32` | Explicit descoping |
| `comms/outbox/.../03-async-scan/retrospective.md:49` | Tech debt acknowledgment |
| `comms/outbox/.../v004/retrospective.md:72` | Version-level debt note |
| `gui/src/components/ScanModal.tsx:186-190` | Dead cancel button |
| `src/stoat_ferret/jobs/queue.py:17-24` | No CANCELLED status |
