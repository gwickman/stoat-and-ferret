# Task 004: Research and Investigation — v012

Research investigated all 5 backlog items for v012 (API Surface & Bindings Cleanup). Key finding: the "remove" path is overwhelmingly supported for BL-061, BL-067, and BL-068 — all target functions have zero production callers. BL-066 has a mature backend endpoint with adjacency validation ready for frontend wiring. BL-079 uncovered 5 documentation inconsistencies beyond the originally scoped issue.

## Research Questions

### BL-061: execute_command() Wire vs Remove
1. Does execute_command() have any production callers? **No — zero callers in src/**
2. What render/export workflows exist that could use it? **None — only ThumbnailService exists, and it calls executor.run() directly**
3. Is FFmpegExecutor.run() blocking? **Yes — RealFFmpegExecutor uses subprocess.run()**
4. Would wiring require async safety work? **Yes — asyncio.to_thread wrapper needed**

### BL-066: Transition GUI
5. Does the transition endpoint exist and what's its schema? **Yes — POST /projects/{id}/effects/transition with TransitionRequest/TransitionResponse**
6. Does the endpoint enforce adjacency? **Yes — strict target_idx == source_idx + 1 check**
7. What GUI patterns exist for the Effect Workshop? **Schema-driven with Zustand stores, JSON Schema parameter forms**
8. Can ClipSelector support clip-pair selection? **No — single-clip model, needs new component or mode**

### BL-067: v001 PyO3 Bindings
9. Do find_gaps/merge_ranges/total_coverage have production callers? **No — zero**
10. Do validate_crf/validate_speed have production callers? **No — Rust-internal validation covers both**
11. How many parity tests exist? **22 tests across 2 test classes**

### BL-068: v006 PyO3 Bindings
12. Do Expr/validate/compose_* have production callers? **No — zero in Python production code**
13. Are these used internally by Rust? **Yes — DrawtextBuilder uses Expr, DuckingPattern uses compose_*  **
14. How many parity tests exist? **~31 tests (16 Expr + ~15 composition/validation)**

### BL-079: API Spec Progress
15. What values does the spec show for running jobs? **progress: null for ALL states including running**
16. What does actual code use? **0.0-1.0 normalized floats from scan.py**
17. Are there additional inconsistencies? **Yes — 5 total issues found**

## Findings Summary

- **BL-061**: Remove. Zero callers, no render/export workflow exists, and wiring would require async safety work (substantial impact #3) for a function that duplicates what ThumbnailService already does directly. Per LRN-029, document what was removed and the trigger for re-adding (Phase 3 Composition Engine).
- **BL-066**: Frontend-only wiring. Backend is complete with adjacency validation. Need a clip-pair selector component (substantial impact #19). Follow schema-driven pattern per LRN-032.
- **BL-067**: Remove all 5 bindings. Zero production callers. Rust-internal validation covers CRF/speed. Phase 3 Composition Engine is the trigger for re-evaluating TimeRange operations.
- **BL-068**: Remove all 6 bindings. Zero production callers. Rust uses Expr/compose internally without PyO3 wrappers. Parity tests become invalid without bindings.
- **BL-079**: Fix 5 inconsistencies: running-state progress null→0.45, complete-state progress null→1.0, cancel response status pending→cancelled, progress range 0-100→0.0-1.0 in manual, add cancelled to status enum.

## Unresolved Questions

None. All questions resolved through codebase investigation.

## Recommendations

1. **BL-061 first**: Remove execute_command() before BL-067/BL-068, as it simplifies the "unused" determination
2. **BL-067/BL-068 parallel**: Both are audit-and-trim with identical patterns — can execute in parallel after BL-061
3. **BL-066 standalone**: No dependency on other items — can execute independently
4. **BL-079 standalone**: Documentation-only — lowest risk, can execute anytime

## Learning Verifications

| Learning | Status | Evidence |
|----------|--------|----------|
| LRN-011 | VERIFIED | validate_crf/validate_speed still exist in sanitize/mod.rs; FFmpegCommand.build() and SpeedControl.new() use Rust-internal validation without Python involvement |
| LRN-016 | VERIFIED | POST /projects/{id}/effects/transition confirmed at effects.py:479; all referenced function names confirmed in codebase |
| LRN-029 | VERIFIED | Process learning — applicable to documenting removal triggers for all binding removals |
| LRN-031 | VERIFIED | All 5 v012 items use Current state/Gap/Impact format; v011 achieved 5/5 first-pass with this approach |
| LRN-032 | VERIFIED | Effect Workshop uses JSON Schema from parameter_schema field (11 occurrences in definitions.py); schema drives form rendering |
| LRN-034 | VERIFIED | Progress range mismatch found: manual says 0-100, code uses 0.0-1.0 (JobResult.progress in queue.py, scan.py line 215) |
| LRN-060 | VERIFIED | Transition endpoint exists and is functional — BL-066 is frontend-only wiring |
| LRN-062 | VERIFIED | IMPACT_ASSESSMENT.md exists at docs/auto-dev/IMPACT_ASSESSMENT.md; async safety check directly caught BL-061 blocking issue |
