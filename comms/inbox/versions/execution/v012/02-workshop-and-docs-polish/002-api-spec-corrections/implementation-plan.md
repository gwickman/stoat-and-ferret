# Implementation Plan: api-spec-corrections

## Overview

Fix 5 documentation inconsistencies across 2 files: the API specification (`05-api-specification.md`) and the API reference manual (`03_api-reference.md`). Changes correct progress values in job status examples to match the 0.0-1.0 range used in code, fix the cancel response status, and add "cancelled" to the status enum.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `docs/design/05-api-specification.md` | Modify | Fix 4 example blocks: running progress, complete progress, cancel status, add cancelled to enum |
| `docs/manual/03_api-reference.md` | Modify | Fix progress range description from "0-100" to "0.0-1.0" |

## Test Files

None — documentation-only change.

## Implementation Stages

### Stage 1: Fix API specification examples

1. Read `docs/design/05-api-specification.md`
2. Fix running-state job example (~lines 295-302): change `"progress": null` to `"progress": 0.45`
3. Fix complete-state job example (~lines 306-319): change `"progress": null` to `"progress": 1.0`
4. Fix cancel response example (~lines 374-382): change `"status": "pending"` to `"status": "cancelled"`
5. Add "cancelled" to the status enum documentation (currently lists pending, running, complete, failed, timeout)
6. Verify all job status examples show realistic values per state:
   - pending: `"progress": null`
   - running: `"progress": 0.45`
   - complete: `"progress": 1.0`
   - failed: `"progress": 0.72`
   - timeout: `"progress": 0.38`
   - cancelled: `"progress": 0.30`

**Verification**: Manual review of all examples in file

### Stage 2: Fix API manual

1. Read `docs/manual/03_api-reference.md`
2. Fix progress field description (~line 984): change "0-100" to "0.0-1.0"
3. Review surrounding context for any other occurrences of "0-100" progress range

**Verification**: Manual review

## Test Infrastructure Updates

None — no code changes.

## Quality Gates

Manual review:
- All job status examples show realistic progress values
- Progress range description says "0.0-1.0"
- Status enum includes "cancelled"

## Risks

- Minimal risk — documentation-only change
- No runtime behavior impact
- See `comms/outbox/versions/design/v012/006-critical-thinking/risk-assessment.md`

## Commit Message

```
docs(v012): fix API spec job status examples with realistic values

Update progress values from null to realistic floats (0.0-1.0)
in running/complete job examples. Fix cancel response status.
Add "cancelled" to status enum. Fix manual progress range
description from "0-100" to "0.0-1.0".

Closes BL-079
```