# Recommendations: Preventing Cross-Version Wiring Gaps

## Already-Addressed Gaps

| Gap | Status | Reference |
|-----|--------|-----------|
| Missing progress in job data structures | BL-073 filed (P1, open) | Backlog |
| Missing cancel mechanism | BL-074 filed (P1, open) | Backlog |
| Blocking ffprobe | BL-072 filed (P0, open) | Backlog |
| WebSocket broadcast not wired | BL-065 fixed in v009 | Completed |

No process-level learnings or product requests exist to prevent this pattern from recurring.

---

## Root Causes Requiring Process Changes

### RC-1: Completion reports accept schema-level existence as functional delivery

**Evidence**: v004 Feature 002 marked FR-2 ("GET /jobs/{id} returns job status, progress, and result") as PASS. The `progress` field existed in `JobStatusResponse` but was never populated. The completion report verified the schema, not the behavior.

**Recommendation**: Completion report quality checks should include a "wiring verification" step that tests not just that a field/endpoint exists, but that it produces non-default values under realistic conditions. For progress fields specifically: verify that a running job returns a non-null progress value.

### RC-2: No cross-version requirement tracing for split deliveries

**Evidence**: Progress was a backend concern in v004 and a frontend concern in v005. Neither version verified end-to-end integration. BL-027's acceptance criteria were checked against v004 alone; BL-033's acceptance criteria were checked against v005 alone. Nobody verified that v005's ScanModal actually received real progress data from v004's job queue.

**Recommendation**: When a backlog item's acceptance criteria span backend + frontend (or multiple versions), the later version's design phase should include an integration verification step. The version design's "dependencies" section should explicitly list prior-version behaviors it depends on and verify they actually work, not just exist.

### RC-3: Retrospectives don't cross-check acceptance criteria against actual behavior

**Evidence**: v004 Theme 03 retrospective stated the goal was "enabling progress tracking" but did not verify progress tracking actually worked. v005 Theme 03 retrospective listed "scan modal with progress" as complete without testing that progress was non-null.

**Recommendation**: Theme retrospectives should include a "behavioral verification" section that runs the feature manually or via test and confirms the user-visible behavior matches the stated goal. A scan should have been triggered and the progress bar observed during retrospective.

### RC-4: API spec examples normalized null progress

**Evidence**: `docs/design/05-api-specification.md` lines 280-361 show `"progress": null` in all job status examples, including the "running" state. This made null progress appear correct to implementors.

**Recommendation**: API specification examples should show realistic values for all states. A "running" job example should show `"progress": 0.45`, not `null`. Spec examples set implementor expectations.

---

## Specific Process Changes

### 1. Add "end-to-end wiring check" to completion reports

When a feature creates an API field, endpoint, or UI element intended to display dynamic data:
- The completion report must include evidence that the data flows end-to-end (not just that the schema exists).
- For progress fields: show a log or test output where a running job returns `progress > 0`.

### 2. Add "prior-version dependency verification" to version design

During the design phase (stage 002-backlog or 004-research), when the version depends on behavior from a prior version:
- Explicitly list the assumed behaviors.
- Run a quick smoke test to verify each assumed behavior actually works.
- If it doesn't, file a backlog item before proceeding.

### 3. Save a learning about the "schema without wiring" pattern

This is the second instance of the same pattern (first: BL-065 WebSocket broadcasts). A learning should be saved so future design phases can check for this anti-pattern.

### 4. Fix API spec examples

Update `docs/design/05-api-specification.md` to show non-null progress in the "running" job status example.
