# Version Context — v006 Effects Engine Foundation

## Version Goals

**v006 — Effects Engine Foundation**

Build a greenfield Rust filter expression engine with graph validation, text overlay, speed control, and effect discovery API. Maps to Phase 2, Milestones M2.1–M2.3 from the strategic roadmap.

This is the first version to enter Phase 2 (Effects & Composition), building on the complete Phase 1 foundation (v001–v005).

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

**Total:** 7 items (5 P1, 2 P2)

## Dependency Chain

```
BL-037 (expression engine) ──┬──→ BL-040 (drawtext) ──┬──→ BL-042 (discovery API) ──→ BL-043 (clip overlay API)
                              │                         │
BL-038 (graph validation) ──→ BL-039 (composition)     │
                                                        │
BL-041 (speed control) ────────────────────────────────┘
```

Key relationships:
- BL-039 depends on BL-038 (composition needs validation)
- BL-040 depends on BL-037 (drawtext needs expression engine)
- BL-042 depends on BL-040 + BL-041 (discovery needs both filter types)
- BL-043 depends on BL-040 + BL-042 (clip API needs drawtext + discovery)

## Investigation Dependencies

| ID | Question | Status | Impact |
|----|----------|--------|--------|
| BL-043 | Clip effect model design (how effects attach to clips) | **pending** | May need exploration before BL-043 implementation |

BL-043 is noted as potentially needing an exploration for clip effect model design. This should be addressed during theme design or as a pre-implementation investigation.

## Constraints and Assumptions

1. **Independence from v005:** v006 is pure Rust + API work with no dependency on v005's GUI components
2. **Greenfield Rust work:** The filter expression engine is new — no existing filter module to extend (the current FFmpeg module handles command building but not filter expressions)
3. **PyO3 incremental binding rule:** Per AGENTS.md, all new Rust types must include PyO3 bindings in the same feature
4. **Existing FFmpeg integration point:** The Rust `stoat_ferret_core::ffmpeg` module is the integration point for new filter builders
5. **CI coverage thresholds:** Python 80%, Rust 90% (Rust currently at 75%, deferred from v004)

## Deferred Items to Be Aware Of

| Item | From | Status |
|------|------|--------|
| Rust coverage threshold at 75% (target 90%) | v004 | Deferred — v006 Rust additions should aim for 90% |
| Drop-frame timecode support | v001 | TBD — not relevant to v006 |
| SPA fallback routing for deep links | v005 | Deferred — not relevant to v006 |
| WebSocket connection consolidation | v005 | Deferred — not relevant to v006 |

## Version-Agnostic Items

These could be addressed opportunistically during v006:
- BL-011 (P3): Consolidate Python/Rust build backends
- BL-018 (P2): Create C4 architecture documentation (partially done — full C4 exists through v005)
- BL-019 (P1): Add Windows bash /dev/null guidance to AGENTS.md

## Previous Version Summary

v005 (completed 2026-02-09) delivered the GUI shell, library browser, and project manager across 4 themes and 11 features. The project now has a complete Phase 1 foundation including Rust core, database, FFmpeg integration, testing infrastructure, and web GUI.
