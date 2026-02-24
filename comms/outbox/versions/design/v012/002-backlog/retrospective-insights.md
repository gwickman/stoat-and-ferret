# Retrospective Insights — v011 to v012

Synthesized insights from v011 (GUI Usability & Developer Experience) relevant to v012 design.

## What Worked Well (Continue)

1. **First-pass completion across all features.** v011 achieved 5/5 features complete with 0 iteration cycles. Well-scoped features with clear acceptance criteria and mature infrastructure enable single-pass delivery. v012 should maintain the same level of description quality (Current state/Gap/Impact format used in all 5 backlog items).

2. **Wiring to existing endpoints.** Both GUI features in v011 Theme 01 succeeded because the backend API surface was already mature. BL-066 (transition GUI) should follow this exact pattern — the transition endpoint already exists.

3. **Established frontend patterns scale.** The Zustand per-entity store pattern and existing modal patterns were reused successfully. BL-066 should follow Effect Workshop GUI patterns already established in v007.

4. **Documentation-only themes execute cleanly.** v011 Theme 02 had zero test regressions. BL-079 (API spec fix) is a documentation-only item and should carry the same low-risk profile.

5. **Design-time impact checks codify institutional knowledge.** The `IMPACT_ASSESSMENT.md` document created in v011 should be referenced during v012 design, particularly the cross-version wiring check (relevant to BL-061).

## What Didn't Work (Avoid)

1. **No significant failures in v011.** This was an exceptionally clean version — the retrospective found no remediation needs and all quality gates passed on first run.

2. **Architecture drift accumulation.** While not a v011 failure, BL-069 accumulated 19 drift items across v009-v011. v012's bindings cleanup may introduce new drift if C4 docs aren't updated. However, BL-069 is explicitly excluded from v012 scope.

3. **Design-ahead bindings without consumers.** The root cause of BL-067 and BL-068 — PyO3 bindings were created "just in case" in v001 and v006 without consuming code paths. v012 should avoid creating new bindings without immediate consumers (per AGENTS.md incremental binding rule).

## Tech Debt Addressed vs Deferred

### Addressed in v012
- `execute_command()` wiring gap (BL-061) — from v002
- v001 unused PyO3 bindings (BL-067) — from v001
- v006 unused PyO3 bindings (BL-068) — from v006
- Transition GUI wiring gap (BL-066) — from v007
- API spec misleading examples (BL-079) — from v010

### Deferred (Not in v012)
- BL-069: C4 architecture documentation (19 drift items) — excluded from versions
- PR-009: Directory listing pagination — P3, deferred
- Phase 3: Composition Engine — deferred to post-v010, may interact with bindings cleanup
- Drop-frame timecode — deferred TBD

## Architectural Decisions Informing v012

1. **BL-061 ordering matters.** The execute_command decision (wire vs remove) should precede BL-067/BL-068 because it may affect what counts as "unused" in the bindings audits. v012 PLAN.md already captures this dependency.

2. **Incremental binding rule.** AGENTS.md mandates adding PyO3 bindings in the same feature as the Rust type. The inverse applies for v012: if bindings are removed, stubs must be updated in the same feature.

3. **Python business logic, Rust input safety boundary** (LRN-011). When auditing sanitization bindings in BL-067, retain bindings where Python needs to call Rust for input safety. Remove only where Rust-internal validation covers the same checks without Python involvement.

4. **Conscious simplicity with documented upgrade paths** (LRN-029). If bindings are removed in BL-067/BL-068, document what was removed and what would trigger re-adding them (e.g., Phase 3 Composition Engine needing filter composition bindings).

## Process Recommendations for v012

1. Reference `IMPACT_ASSESSMENT.md` during design — check async safety (BL-061 if wiring), cross-version wiring (BL-061, BL-066), and GUI input mechanisms (BL-066).
2. Keep `.env.example` in sync if any settings change (unlikely for v012 scope).
3. Plan stub regeneration as part of BL-067 and BL-068 features, not as a separate step.
