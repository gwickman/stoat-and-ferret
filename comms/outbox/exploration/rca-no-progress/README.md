# RCA: Missing Job Progress Reporting

## Summary

The `AsyncioJobQueue`, `JobResult`, and `JobStatusResponse` have no functional progress reporting. The scan handler never reports intermediate progress. The frontend progress bar is permanently stuck at 0%. This gap was explicitly required in backlog acceptance criteria, designed into the architecture, and marked as delivered — but never actually implemented.

## Key Findings

### The gap was specified but not delivered

- **BL-027** (v004) acceptance criteria: "Job status queryable via GET endpoint **with progress information**" — marked complete.
- **v004 Theme 03** goal: "enabling **progress tracking**" — retrospective did not flag the gap.
- **BL-033** (v005) acceptance criteria: "Scan modal shows progress feedback" — marked complete.
- **v005 ScanModal** polls for progress and renders a bar, but receives null from the backend.

### The completion reports falsely passed

v004 Feature 002 marked FR-2 PASS because `JobStatusResponse.progress` exists as a schema field. But `_AsyncJobEntry` has no progress field, `JobResult` has no progress field, the endpoint never sets it, and the scan handler has no mechanism to report it. The field always returns `None`.

### No retrospective caught it

Neither v004 nor v005 theme or version retrospectives flagged the non-functional progress. v005 noted "polling could use WebSocket" as a low-priority enhancement — framing a broken feature as an optimization opportunity.

### This is a recurring pattern

**BL-065** (fixed in v009) was the same anti-pattern: WebSocket event types and frontend listeners were built across v005 themes, but `broadcast()` was never called from API operations. Cross-version wiring gaps appear to be a systemic issue.

## Root Causes

1. **Schema-level verification**: Completion reports verified that the progress field existed, not that it produced real values.
2. **No cross-version requirement tracing**: v004 built backend without progress; v005 built frontend assuming it worked. Neither verified end-to-end.
3. **Retrospective shallow checking**: Retrospectives confirmed deliverables without testing user-visible behavior.
4. **API spec normalized null**: The API spec showed `"progress": null` in running state examples, making it appear correct.

## Already Addressed

| Item | Status |
|------|--------|
| BL-073: Add progress reporting | Filed today, P1, open |
| BL-074: Job cancellation support | Filed today, P1, open |
| BL-072: Fix blocking ffprobe | Filed today, P0, open |
| BL-065: WebSocket broadcast wiring | Fixed in v009 |

No process-level changes have been made to prevent recurrence.

## Recommendations

See [recommendations.md](./recommendations.md) for specific process changes:
1. Add end-to-end wiring checks to completion reports
2. Add prior-version dependency verification to version design
3. Save a learning about the "schema without wiring" pattern
4. Fix API spec examples to show realistic progress values

## Evidence

See [evidence-trail.md](./evidence-trail.md) for the full chronological trace with file paths and line numbers.
