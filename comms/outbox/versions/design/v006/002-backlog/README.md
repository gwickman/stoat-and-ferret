# 002-Backlog: v006 Effects Engine Foundation

v006 scope includes 7 mandatory backlog items (BL-037 through BL-043): 5 P1 items forming the Rust effects engine core (expression engine, graph validation, composition system, drawtext builder, speed control) and 2 P2 items bridging to the API layer (effect discovery endpoint, text overlay clip endpoint). The previous version (v005) completed successfully with all 11 features across 4 themes, delivering the GUI shell and establishing patterns for DI, testing, and feature sequencing that carry forward into v006. All 7 backlog items have formulaic use cases that should be refined before design.

## Backlog Overview

- **Total items:** 7
- **Priority distribution:** 5x P1, 2x P2
- **Size distribution:** 6x Large, 1x Medium
- **Tags:** rust (5), api (2), filters (3), text-overlay (2), speed-control (1), discovery (1)
- **All items status:** open

## Previous Version

- **Version:** v005 (GUI Shell, Library Browser & Project Manager)
- **Completed:** 2026-02-09
- **Retrospectives:** `docs/versions/v005/01-frontend-foundation_retrospective.md` through `04-e2e-testing_retrospective.md`
- **Summary:** `docs/versions/v005/VERSION_SUMMARY.md`

## Key Learnings Applicable to v006

1. **LRN-001 (PyO3 Method Chaining):** The expression engine and filter builders (BL-037, BL-040, BL-041) should use `PyRefMut<'_, Self>` for fluent builder APIs that work identically in Rust and Python.
2. **LRN-011 (Python/Rust Boundary):** Rust handles input sanitization and type safety (filter expressions, graph validation); Python handles business rules (API routing, effect registration). BL-042/043 are Python-side; BL-037-041 are Rust-side.
3. **LRN-012 (PyO3 FFI Overhead):** Rust justification is correctness/safety, not raw speed. Filter expression building and graph validation benefit from compile-time safety — performance gains are secondary.
4. **LRN-019 (Infrastructure First):** The expression engine (BL-037) and graph validation (BL-038) are infrastructure consumed by everything else. Sequence them first.
5. **LRN-025 (Feature Handoff Documents):** v005 achieved zero-rework sequencing with handoff docs. Continue this pattern for v006's dependency chain.

## Tech Debt from v005

- **Dual WebSocket connections:** Shell and Dashboard each open separate WebSocket connections (recommended consolidation deferred)
- **SPA fallback routing:** No catch-all route for `/gui/*` deep links
- **Client-side sorting limitation:** Sort only within current page
- **Search vs list total semantics:** Inconsistent `total` field meaning across endpoints

## Missing Items

None. All 7 backlog items (BL-037 through BL-043) were fetched successfully.

## Quality Assessment Summary

All 7 items have **formulaic use cases** that should be refined. `update_backlog_item` was not authorized for this exploration — recommended rewrites are documented in `backlog-details.md`. Descriptions are generally well-written (100+ words each). Acceptance criteria are testable with clear action verbs.
