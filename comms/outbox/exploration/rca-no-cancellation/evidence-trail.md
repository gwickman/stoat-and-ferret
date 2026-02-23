# Evidence Trail: Job Cancellation Omission

## 1. Design Phase — Cancellation Was Specified

The original design documents explicitly specify job cancellation as a requirement:

- **`docs/design/01-roadmap.md:455`** — Milestone 5.4 (Job Queue): "Build job cancellation capability"
- **`docs/design/01-roadmap.md:462`** — Milestone 5.5 (Export API): "Implement `/render/cancel/{job_id}`"
- **`docs/design/01-roadmap.md:483`** — Milestone 5.8 (GUI Render Queue): "Implement cancel and remove job actions"
- **`docs/design/05-api-specification.md:1146-1158`** — Full API spec for `POST /render/cancel/{job_id}` with response schema including `"status": "cancelled"` and `cancelled_at` timestamp
- **`docs/design/02-architecture.md:885`** — Database schema defines `status TEXT NOT NULL` with `cancelled` as an explicit enum value
- **`docs/design/08-gui-architecture.md:381`** — Render Queue wireframe shows `[Cancel]` button on active jobs

**Conclusion:** Cancellation was a first-class design requirement across API, database, and GUI layers.

## 2. Backlog Phase — Cancellation Was Absent

**BL-027** ("Async job queue for scan operations") was the sole backlog item for the job queue. Its acceptance criteria were:
1. Scan endpoint returns job ID immediately
2. Job status queryable via GET endpoint
3. InMemoryJobQueue supports synchronous test execution
4. Existing scan tests updated to async pattern

No acceptance criterion mentions cancellation. No separate backlog item for cancellation existed until BL-074, created **2026-02-23** (today) — well after implementation.

## 3. Version Design Phase — v004 Theme 03 (Async Scan)

**`comms/inbox/versions/execution/v004/03-async-scan/THEME_DESIGN.md`** — Three features defined:
1. job-queue-infrastructure
2. async-scan-endpoint
3. scan-doc-updates

No mention of cancellation in the theme design.

**`comms/inbox/versions/execution/v004/03-async-scan/001-job-queue-infrastructure/requirements.md`**:
- FR-6 defines tracked statuses as: `pending, running, completed, failed` — no `cancelled`
- Out of scope is not listed at all for this feature

**`comms/inbox/versions/execution/v004/03-async-scan/002-async-scan-endpoint/requirements.md:32`**:
- **Out of Scope** explicitly lists: "Scan cancellation — not required for initial implementation"

This is the critical moment. Cancellation was explicitly descoped but no backlog item was created to track the deferred work.

## 4. Implementation Phase — v004

**`comms/outbox/versions/execution/v004/03-async-scan/001-job-queue-infrastructure/completion-report.md`**:
- `AsyncioJobQueue` implemented with statuses: pending, running, completed, failed (no cancelled)
- No `cancel()` method in protocol or implementation
- `JobStatus` enum (`src/stoat_ferret/jobs/queue.py:17-24`): PENDING, RUNNING, COMPLETE, FAILED, TIMEOUT — no CANCELLED

## 5. Retrospective Phase — v004

**`comms/outbox/versions/execution/v004/03-async-scan/retrospective.md:49`**:
- Tech debt table lists: "No job cancellation API | Feature 2 | Low | `DELETE /jobs/{id}` not implemented; add if users need to cancel long-running scans"

**`comms/outbox/versions/execution/v004/retrospective.md:72`**:
- Version-level tech debt: "No job expiration/cleanup or cancellation API | Theme 03 | Jobs remain in memory indefinitely"

Both retrospectives acknowledged the gap but rated it "Low" priority. No backlog item was created.

## 6. GUI Phase — v005 Theme 03 (GUI Components)

**`comms/inbox/versions/execution/v005/03-gui-components/003-library-browser/requirements.md:28-29`**:
- FR-004 (Scan modal): "Scan modal triggers directory scan via the jobs API and shows progress feedback"
- No mention of cancel button in requirements

**`gui/src/components/ScanModal.tsx:186-190`** — The delivered code has a Cancel button:
```tsx
<button data-testid="scan-cancel" disabled={scanStatus === 'scanning'}>
  {scanStatus === 'complete' ? 'Close' : 'Cancel'}
</button>
```
The button is **disabled during scanning** (`disabled={scanStatus === 'scanning'}`). It only calls `onClose()` — there is no cancel API call. During an active scan, the user cannot interact with this button at all.

## 7. Post-Implementation — Gap Persists Through v006-v009

No version between v006 and v009 addressed the cancellation gap. BL-073 (progress reporting) and BL-074 (cancellation support) were only created on 2026-02-23, prompted by the user's exploration request and associated investigations.

## Timeline Summary

| Date | Event | Cancellation Status |
|------|-------|-------------------|
| Pre-v001 | Design docs written | Specified in roadmap, API spec, GUI wireframes, DB schema |
| 2026-02-08 | BL-027 created | Not mentioned in acceptance criteria |
| 2026-02-08 | v004 Theme 03 designed | Explicitly descoped in requirements |
| 2026-02-09 | v004 Theme 03 implemented | Not implemented; noted as low-priority tech debt |
| 2026-02-09 | v004 retrospective | Acknowledged gap; no backlog item created |
| 2026-02-09 | v005 Theme 03 designed | Cancel button not in requirements |
| 2026-02-09 | v005 Theme 03 implemented | Dead cancel button shipped |
| 2026-02-23 | BL-074 created | First backlog item for cancellation |
