# Evidence Trail: Missing Job Progress Reporting

Chronological trace through design, backlog, version execution, and code.

---

## 1. Design Phase (pre-v004)

### Architecture Doc (`docs/design/02-architecture.md`)
- **Lines 806-816**: Job Queue described with "async producer-consumer pattern", no mention of progress callbacks from handlers.
- **Lines 886**: DB schema has `progress REAL` in `jobs` table — progress was architecturally intended.
- **Lines 399-408**: Render Service lists "Progress tracking with metrics (Rust ETA calculation)" but this is render-specific, not generic job queue.

### API Specification (`docs/design/05-api-specification.md`)
- **Lines 280-361**: `GET /jobs/{job_id}` response examples show `"progress": null` in ALL states (pending, running, complete, failed, timeout). No example shows a populated progress value.
- **Implication**: The API spec itself normalized `progress: null` as expected behavior.

### GUI Architecture (`docs/design/08-gui-architecture.md`)
- **Line 543**: Phase 1 checklist: "Create scan directory modal with progress"
- **Lines 375-406**: Render Control Center mockup shows progress bars with "45%" and ETA — progress was a first-class UX concern.

---

## 2. Backlog Items

### BL-027 — "Async job queue for scan operations" (added 2026-02-08)
- **Acceptance criteria #2**: "Job status queryable via GET endpoint **with progress information**"
- **Use case narrative**: "the job status endpoint tells them the scan is **73% complete**"
- **Status**: Completed (2026-02-09), assigned to v004/async-scan.

### BL-033 — "Build library browser with video grid, search, and scan UI" (added 2026-02-08)
- **Acceptance criteria #4**: "Scan modal triggers directory scan and **shows progress feedback**"
- **Status**: Completed (2026-02-09), assigned to v005/gui-components.

---

## 3. v004 Execution: Theme 03 "async-scan"

### Theme Design (`comms/inbox/versions/v004/.../THEME_DESIGN.md`)
- Goal: "Replace synchronous blocking scan with async job queue pattern, enabling **progress tracking** and non-blocking API behavior"

### Logical Design (`comms/outbox/versions/design/v004/005-logical-design/logical-design.md`)
- Theme 03 section: same "enabling **progress tracking**" language.

### Feature 001: Job Queue Infrastructure (completion-report.md)
- Built `AsyncioJobQueue` with `_AsyncJobEntry` dataclass.
- `_AsyncJobEntry` tracks: `job_id`, `job_type`, `payload`, `status`, `result`, `error`.
- **No `progress` field** in the job entry. No `set_progress()` method.

### Feature 002: Async Scan Endpoint (completion-report.md)
- **FR-2**: "`GET /jobs/{id}` returns job status, **progress**, and result when complete" — marked **PASS**.
- `JobStatusResponse` schema includes `progress: float | None = None`.
- **But**: the endpoint at `jobs.py:38-43` constructs the response without setting `progress`. It always returns `None`.
- **False pass**: FR-2 was marked PASS because the field existed in the schema, not because it was populated.

### Theme Retrospective (`03-async-scan/retrospective.md`)
- States theme goal included "progress tracking".
- Lists 4 low-priority tech debt items — **none mention progress**.
- Does not flag the unpopulated progress field.

### Version Retrospective (`v004/retrospective.md`)
- Does not mention progress tracking in deferred items.

---

## 4. v005 Execution: Theme 03 "gui-components"

### Feature 003: Library Browser (completion-report.md)
- **FR-004**: "Scan modal triggers directory scan and shows progress" — marked **PASS**.
- Created `ScanModal.tsx` with polling at 1s intervals.
- ScanModal reads `status.progress` and renders a progress bar.
- **But**: backend always returns `progress: null`, so bar stays at 0%.

### Theme Retrospective (`03-gui-components/retrospective.md`)
- "Scan modal with progress" listed as **Complete**.
- Tech debt: "Scan progress polling could be replaced with WebSocket events" — framed as optimization, not a bug.
- **Does not flag** that progress is always null.

### Version Retrospective (`v005/retrospective.md`)
- "Scan Progress Polling" listed as low-priority tech debt (optimization).
- **Does not flag** the non-functional progress bar.

---

## 5. Delivered Code State

| Component | File | Status |
|-----------|------|--------|
| `JobStatusResponse.progress` | `api/schemas/job.py:28` | Field exists (`float \| None = None`) |
| `_AsyncJobEntry` | `jobs/queue.py:268-276` | **No progress field** |
| `JobResult` | `jobs/queue.py:36-49` | **No progress field** |
| `get_job_status()` | `api/routers/jobs.py:38-43` | **Never sets progress** |
| Scan handler | `api/services/scan.py:55-103` | **No progress callback mechanism** |
| `ScanModal.tsx` | `gui/src/components/ScanModal.tsx:78,148-161` | Reads progress, renders bar — always null |

---

## 6. Gap Discovery (2026-02-23)

- **BL-073**: "Add progress reporting to job queue and scan handler" — filed today, P1, open.
- **BL-074**: "Implement job cancellation support" — filed today, P1, open.
- **BL-072**: "Fix blocking subprocess.run() in ffprobe" — filed today, P0, open.

---

## 7. Pattern Precedent

**BL-065** (v009, completed): "Wire WebSocket broadcast calls into API operations" — identical pattern where infrastructure was built (WebSocket types + frontend listeners) but the actual broadcast calls were never wired. Fixed in v009/gui-runtime-fixes. This confirms cross-version wiring gaps are a recurring pattern.
