# 002-Backlog: v010 Backlog Analysis and Retrospective Review

v010 comprises 5 mandatory backlog items (1 P0, 2 P1, 2 P2) across 2 themes targeting async pipeline correctness and user-facing job controls. The previous version (v009) completed cleanly with 31/31 acceptance criteria, establishing DI and wiring patterns that v010 extends. Key insight from v009: incremental wiring over established patterns is fast and low-risk — v010's scope fits this model well.

## Backlog Overview

- **Total items:** 5 (all mandatory, all open)
- **Priority distribution:** 1 P0, 2 P1, 2 P2
- **Size distribution:** 1 M, 4 L
- **Theme 1 (async-pipeline-fix):** BL-072 (P0), BL-077 (P2), BL-078 (P2)
- **Theme 2 (job-controls):** BL-073 (P1), BL-074 (P1)

### Quality Assessment Summary

| Item | Desc Words | Desc Flagged | AC Flagged | Use Case Formulaic | Refinement |
|------|-----------|-------------|-----------|-------------------|------------|
| BL-072 | ~95 | No | 0 | No | None needed |
| BL-073 | ~80 | No | 0 | No | None needed |
| BL-074 | ~85 | No | 0 | No | None needed |
| BL-077 | ~100 | No | 0 | null (missing) | Attempted use_case update |
| BL-078 | ~90 | No | 0 | null (missing) | Attempted use_case update |

All descriptions are well-detailed with problem context, impact, and specific gaps. All acceptance criteria use action verbs and are testable. BL-077 and BL-078 have null use cases — update was attempted but the field may not be supported via `update_backlog_item`.

## Previous Version

- **Version:** v009 (Observability & GUI Runtime)
- **Completed:** 2026-02-22
- **Retrospective:** `comms/outbox/versions/execution/v009/retrospective.md`
- **Theme retrospectives:** `docs/versions/v009/01-observability-pipeline_retrospective.md`, `docs/versions/v009/02-gui-runtime-fixes_retrospective.md`

## Key Learnings

1. **Extend the existing `AsyncioJobQueue` pattern** (LRN-009, LRN-010) — built on stdlib asyncio.Queue with handler registration. v010 adds progress and cancellation to this foundation.
2. **DI wiring is fast when patterns are established** (LRN-050) — all v010 changes extend existing DI infrastructure.
3. **Guard optional components** (LRN-049) — progress callbacks should be optional and guarded, matching v009's broadcast pattern.
4. **Explicit timeouts in CI-bound tests** (LRN-043) — BL-078's 2-second responsiveness assertion needs explicit timeout handling for CI variability.
5. **Fix foundational issues first** (LRN-033) — BL-072 must complete before BL-077, BL-078, BL-073, and BL-074.

## Tech Debt

- C4 documentation not updated since v008 (medium — not addressed in v010)
- Growing `create_app()` kwarg count (low — v010 may add more kwargs; watch 6-7 threshold)
- No integration test for live WebSocket broadcasts (low — BL-078's approach indirectly informs this)

## Missing Items

None — all 5 backlog items (BL-072, BL-073, BL-074, BL-077, BL-078) were successfully retrieved.

## Artifacts

| File | Description |
|------|-------------|
| [backlog-details.md](./backlog-details.md) | Full details for all 5 backlog items with complexity assessments |
| [retrospective-insights.md](./retrospective-insights.md) | Synthesized insights from v009 retrospective |
| [learnings-summary.md](./learnings-summary.md) | Relevant project learnings (12 applicable from 52 total) |
