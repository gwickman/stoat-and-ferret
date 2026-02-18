# Version Context - v006

## Version Overview

- **Version:** v006 - Effects Engine Foundation
- **Status:** Planned
- **Roadmap reference:** Phase 2, Milestones M2.1-M2.3
- **Goal:** Greenfield Rust filter expression engine, graph validation, text overlay, speed control, effect discovery API
- **Estimated scope:** 7 backlog items

## Backlog Items

| ID | Priority | Title |
|----|----------|-------|
| BL-037 | P1 | Implement FFmpeg filter expression engine in Rust |
| BL-038 | P1 | Implement filter graph validation |
| BL-039 | P1 | Build filter composition system |
| BL-040 | P1 | Implement drawtext filter builder |
| BL-041 | P1 | Implement speed control filters |
| BL-042 | P2 | Create effect discovery API endpoint |
| BL-043 | P2 | Apply text overlay to clip API |

## Dependency Chain

```
BL-037 (expression engine)
  |-> BL-040 (drawtext builder)
  |-> BL-041 (speed control)
BL-038 (graph validation)
  |-> BL-039 (composition system)
BL-040 + BL-041
  |-> BL-042 (effect discovery API)
BL-040 + BL-042
  |-> BL-043 (text overlay clip API)
```

Key ordering constraints:
- BL-039 depends on BL-038
- BL-040 depends on BL-037
- BL-042 depends on BL-040 + BL-041
- BL-043 depends on BL-040 + BL-042

## Independence from Previous Versions

v006 is independent of v005 (GUI shell). It is pure Rust + API work. No frontend changes expected in v006.

## Investigation Dependencies

- **BL-043** may need an exploration for clip effect model design (how effects attach to clips)
- This is listed in PLAN.md as investigation dependency with status: pending

## Constraints and Assumptions

1. **Greenfield Rust work:** The filter expression engine is new code, not modifications to existing modules
2. **PyO3 bindings required:** Per AGENTS.md incremental binding rule, all new Rust types must include PyO3 bindings in the same feature
3. **Stub regeneration:** After each Rust API change, stubs must be regenerated and verified
4. **Coverage thresholds:** Python 80%, Rust 90%
5. **Non-destructive editing:** Core architecture principle - never modify source files

## Deferred Items to Be Aware Of

From previous versions:
- Drop-frame timecode support (from v001, deferred to TBD)
- Rust coverage threshold at 75% (target 90%, from v004)
- SPA fallback routing for deep links (from v005)
- WebSocket connection consolidation (from v005)

Version-agnostic items that could be addressed opportunistically:
- BL-011 (P3): Consolidate Python/Rust build backends
- BL-018 (P2): Create C4 architecture documentation (partially done)
- BL-019 (P1): Add Windows bash /dev/null guidance to AGENTS.md

## Predecessor Context

- **v005** (complete 2026-02-09): GUI shell, library browser, project manager - 4 themes, 11 features
- **v004** (complete 2026-02-09): Testing infrastructure - 5 themes, 15 features
- **v003** (complete 2026-01-28): API layer + clip model - 4 themes, 15 features
- **17 themes completed** across v001-v005
