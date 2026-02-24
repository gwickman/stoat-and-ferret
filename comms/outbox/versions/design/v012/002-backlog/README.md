# Task 002: Backlog Analysis — v012

v012 (API Surface & Bindings Cleanup) encompasses 5 backlog items focused on reducing technical debt in the Rust-Python boundary and closing GUI/docs polish gaps. The previous version (v011) was exceptionally clean — all 5 features completed on first pass with 34/34 acceptance criteria. Key learnings emphasize wiring to existing endpoints, design-time impact checks, and documentation-only themes as low-risk investments.

## Backlog Overview

- **Total items:** 5
- **Priority distribution:** 1x P2 (BL-061), 4x P3 (BL-066, BL-067, BL-068, BL-079)
- **Size:** All items sized as L
- **All items mandatory** per PLAN.md — no deferrals permitted
- **Missing items:** None — all 5 backlog items found and fetched successfully

## Previous Version

- **Version:** v011 — GUI Usability & Developer Experience
- **Status:** Completed 2026-02-24
- **Retrospective:** `comms/outbox/versions/execution/v011/retrospective.md`
- **Detailed analysis:** `comms/outbox/versions/retrospective/v011/`

## Key Learnings Applicable to v012

1. **Wire to existing endpoints first** (LRN-060): BL-066 (transition GUI) should leverage the existing `POST /projects/{id}/effects/transition` endpoint — frontend-only wiring
2. **Design-time impact checks** (LRN-062): Reference `IMPACT_ASSESSMENT.md` during design — particularly the cross-version wiring check relevant to BL-061
3. **Detailed design specs correlate with first-pass success** (LRN-031): All 5 v012 items have well-structured descriptions with Current state/Gap/Impact format
4. **Conscious simplicity with upgrade paths** (LRN-029): When deciding wire vs remove for BL-061, document the rationale and future triggers
5. **Python business logic, Rust input safety** (LRN-011): Guides the bindings audit — retain bindings where Python needs to call Rust for safety; remove where Rust handles it internally

## Tech Debt

v012 is itself a tech debt reduction version. Key debt items being addressed:
- `execute_command()` has zero production callers (BL-061)
- v001 PyO3 bindings with no production callers (BL-067)
- v006 PyO3 bindings only used in parity tests (BL-068)
- API spec examples showing `null` for running-state progress (BL-079)
- Transition GUI missing despite backend API being complete (BL-066)

Remaining debt not in v012 scope:
- BL-069: C4 architecture documentation (19 drift items, excluded from versions)
- PR-009: Directory listing pagination (P3, deferred)

## Quality Assessment Summary

| Item | Desc Words | Desc Flag | AC Flag | Use Case | Refinement |
|------|-----------|-----------|---------|----------|------------|
| BL-061 | ~80 | No | 0 | null | None needed |
| BL-066 | ~70 | No | 0 | null | None needed |
| BL-067 | ~80 | No | 0 | null | None needed |
| BL-068 | ~80 | No | 0 | null | None needed |
| BL-079 | ~60 | No | 0 | null | None needed |

All items have well-structured descriptions (Current state/Gap/Impact format), testable acceptance criteria with action verbs, and no formulaic use cases. Use cases are null (not provided) rather than formulaic — acceptable since the descriptions provide sufficient context.
