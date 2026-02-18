# Retrospective Insights - v005 -> v006

## Source

Previous version: **v005** (GUI Shell, Library Browser & Project Manager)
Retrospective: `comms/outbox/versions/execution/v005/retrospective.md`

## What Worked Well (Continue)

### DI Pattern Scales Cleanly
The `create_app()` kwargs pattern scaled across all v005 themes without refactoring. New components (WebSocket manager, thumbnail service) plugged in cleanly. **v006 implication:** The effect registry and discovery endpoint should follow this same DI pattern for testability.

### Feature Sequencing Was Correct
Theme ordering (infrastructure -> backend -> GUI -> E2E) was validated by clean handoffs with zero rework. **v006 implication:** Sequence Rust engine work (expression, validation, composition) before API endpoints (discovery, apply). Infrastructure-first strategy confirmed by LRN-019.

### First-Pass Quality Gate Success (100%)
All 11 features passed quality gates on first iteration across Python, TypeScript, and Playwright toolchains. **v006 implication:** Detailed implementation plans with concrete acceptance criteria lead to clean execution. Invest in design quality for v006 items.

### Handoff Documents Enable Zero-Rework Chains
Feature-to-feature handoff documents effectively communicated integration points. **v006 implication:** Critical for the BL-037->BL-040->BL-042->BL-043 dependency chain. Each feature should document what it provides for downstream consumers.

## What Didn't Work (Avoid)

### No quality-gaps.md Files Generated
Zero quality-gaps.md files across 11 features. While this reflected clean implementations, having structured debt tracking would catch minor items. **v006 implication:** Ensure quality-gaps.md generation is part of the feature completion workflow even for minor items.

### C4 Documentation Skipped
Architecture documentation was not updated for v005. Frontend, WebSocket, and GUI components are missing from C4 diagrams. **v006 implication:** Plan for C4 documentation update as part of v006 or immediately after — effects engine is a major architectural addition.

## Tech Debt From v005

| Item | Priority | v006 Relevance |
|------|----------|----------------|
| SPA fallback routing | High | Low — no frontend work in v006 |
| Dual WebSocket connections | High | Low — no WebSocket changes planned |
| Client-side sorting limitation | Medium | Low — backend sort not in scope |
| C4 documentation regeneration | Medium | High — v006 adds major Rust modules |
| Rust coverage at 75% (target 90%) | Medium | High — v006 adds significant Rust code |

## Tech Debt From Earlier Versions

| Item | Source | v006 Relevance |
|------|--------|----------------|
| Rust coverage threshold 75% vs 90% target | v004 | High — v006 should ratchet up with proptest coverage |
| Drop-frame timecode support | v001 | None — not in v006 scope |

## Architectural Decisions Informing v006

1. **Rust for safety, Python for orchestration**: Filter expression engine, graph validation, composition, drawtext builder, and speed builders all belong in Rust. Effect registry, discovery API, and clip effect application belong in Python. (LRN-011)

2. **PyO3 method chaining with PyRefMut**: All Rust builders (expression, drawtext, speed, composition) should use the `PyRefMut` return pattern for fluent Python APIs. (LRN-001)

3. **FFI overhead awareness**: Rust is justified for filter string generation (string-heavy processing where Rust is 1.9x faster) and compile-time correctness, not for simple validation. (LRN-012)

4. **Record-replay for FFmpeg contract tests**: BL-040's contract tests should use the Real/Recording/Fake executor pattern established in v004. (LRN-008)

5. **Constructor DI for new services**: Effect registry and any new services should use `create_app()` kwargs pattern, not FastAPI `dependency_overrides`. (LRN-005)
