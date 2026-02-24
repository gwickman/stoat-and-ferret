# Feature: api-spec-corrections

## Goal

Fix 5 documentation inconsistencies in the API specification and manual so examples show realistic values matching actual code behavior.

## Background

The API specification at `docs/design/05-api-specification.md` shows `"progress": null` in running-state and complete-state job examples. This normalized null progress as correct behavior, misleading implementors. The code uses 0.0-1.0 normalized floats (`src/stoat_ferret/jobs/queue.py:36-52`, `src/stoat_ferret/api/services/scan.py:214-215`). The manual incorrectly says "0-100" for progress range. The status enum is missing "cancelled".

Backlog Item: BL-079

## Functional Requirements

**FR-001**: Fix running-state job example
- Acceptance: `docs/design/05-api-specification.md` lines ~295-302 show `"progress": 0.45` instead of `null`

**FR-002**: Fix complete-state job example
- Acceptance: `docs/design/05-api-specification.md` lines ~306-319 show `"progress": 1.0` instead of `null`

**FR-003**: Fix cancel response example
- Acceptance: `docs/design/05-api-specification.md` lines ~374-382 show `"status": "cancelled"` instead of `"pending"`

**FR-004**: Fix manual progress description
- Acceptance: `docs/manual/03_api-reference.md` line ~984 says "0.0-1.0" instead of "0-100"

**FR-005**: Add "cancelled" to status enum
- Acceptance: Status enum in `05-api-specification.md` includes "cancelled" alongside pending, running, complete, failed, timeout

**FR-006**: Ensure all job status examples show realistic values
- Acceptance: pending: null, running: 0.45, complete: 1.0, failed: 0.72, timeout: 0.38, cancelled: 0.30

## Non-Functional Requirements

None — documentation-only change with no runtime behavior impact.

## Handler Pattern

Not applicable for v012 — no new handlers introduced.

## Out of Scope

- Code changes to progress reporting logic (already correct)
- Adding new job states or modifying the JobStatus enum in code
- Updating other documentation beyond the 2 files specified

## Test Requirements

- No automated tests — documentation-only change
- Manual review: all job status examples show realistic values
- Manual review: progress range description says "0.0-1.0"
- Manual review: status enum includes "cancelled"

## Reference

See `comms/outbox/versions/design/v012/004-research/` for supporting evidence.
