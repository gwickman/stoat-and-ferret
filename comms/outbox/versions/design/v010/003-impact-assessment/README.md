# 003-Impact Assessment: v010

18 impacts identified across v010's 5 backlog items: 6 substantial (feature scope), 12 small (sub-task scope), 0 cross-version. The most critical finding is a cluster of caller-adoption risks around BL-073 (progress) and BL-074 (cancellation) — the job queue infrastructure changes are necessary but insufficient without wiring through the router, scan handler, handler signature, and frontend.

## Generic Impacts

- **Documentation:** 8 impacts across C4 docs (3), design docs (2), manual (2), and CHANGELOG (1)
- **Caller-impact:** 8 impacts — the primary risk area for v010
- **CI configuration:** 1 impact (BL-077 quality gate integration)
- **Test infrastructure:** 1 impact (test fixtures needing protocol updates)

## Project-Specific Impacts

N/A — no `docs/auto-dev/IMPACT_ASSESSMENT.md` exists for this project.

## Work Items Generated

| Classification | Count | Notes |
|---------------|-------|-------|
| Substantial | 6 | All caller-adoption risks requiring design decisions |
| Small | 12 | Documentation updates and mechanical code changes |
| Cross-version | 0 | All impacts fit within v010 scope |

## Recommendations

### For Logical Design (Task 005)

1. **BL-073 (progress) must include router wiring, handler context, and scan handler updates as explicit acceptance criteria.** The current BL-073 AC focuses on queue-level changes but the progress field will never reach the API response without impact items #1, #5, and #6. These are not separate features — they are essential parts of BL-073 delivery.

2. **BL-074 (cancellation) must include scan handler checkpoint and frontend wiring as explicit scope.** AC item 3 ("scan handler checks cancellation flag") already implies impact #4, but the frontend cancel button (#7) and JobStatus enum (#8) should be called out.

3. **Handler signature extension (#6) is a design decision affecting both BL-073 and BL-074.** The current `(job_type, payload)` signature lacks job context. Options: (a) extend to `(job_type, payload, job_context)`, (b) pass a callback closure, (c) provide job_id via payload. This decision should be made once and applied to both progress and cancellation.

4. **Documentation updates (9 small impacts) should be handled as sub-tasks within each feature**, not as separate features. C4 doc staleness is a known tech debt item from v009; v010 should update only the specific sections affected by its changes.

5. **Test fixture updates (#17, #18) are mechanical consequences** of the protocol and signature changes. They do not need separate features but should be accounted for in effort estimates.

## Artifacts

| File | Description |
|------|-------------|
| [impact-table.md](./impact-table.md) | Complete impact table with 18 entries |
| [impact-summary.md](./impact-summary.md) | Impacts grouped by classification |
