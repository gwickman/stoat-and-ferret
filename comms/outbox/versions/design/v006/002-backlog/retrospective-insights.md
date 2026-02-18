# Retrospective Insights - v005

Synthesized insights from the most recent completed version (v005 - GUI Shell, Library Browser & Project Manager, completed 2026-02-09).

## What Worked Well (Continue)

### DI Pattern Scales Cleanly
The `create_app()` kwargs dependency injection pattern consistently scaled across all v005 themes. New components (WebSocket manager, thumbnail service, GUI static path) plugged in without breaking existing tests or requiring refactoring. **v006 implication:** New effect-related services (effect registry, effect application service) should follow this same DI pattern.

### Feature Sequencing Was Correct
Theme ordering (infrastructure -> backend services -> GUI components -> E2E testing) was validated by clean handoffs. Each theme built on the previous without rework. **v006 implication:** Sequence Rust engine work before API endpoints; the expression engine (BL-037) and validation (BL-038) must precede builders (BL-040, BL-041) and API layers (BL-042, BL-043).

### First-Pass Quality Gate Success
All 11 features passed quality gates on first iteration across all three toolchains. This indicates implementation plans were detailed enough to execute cleanly. **v006 implication:** Invest in detailed implementation plans, especially for the greenfield Rust expression engine where the design space is largest.

### Handoff Documents Enable Zero-Rework Chains
Feature-to-feature handoff documents effectively communicated integration points and patterns. **v006 implication:** Critical for the dependency chain (BL-037 -> BL-040 -> BL-042 -> BL-043) where each feature must understand the API surface of its predecessor.

## What Didn't Work (Avoid)

### C4 Documentation Skipped
Architecture documentation was not updated for v005. The frontend, WebSocket, and GUI components are not captured in C4 diagrams. **v006 implication:** v006 adds significant new Rust modules. Schedule C4 documentation update or accept the growing gap.

### No quality-gaps.md Generated
No quality-gaps.md files were generated across any of the 11 features. While reflecting clean implementations, this means minor items may be lost. **v006 implication:** Ensure quality gap tracking is active for v006, especially for the greenfield Rust code where gaps are more likely.

### Formulaic Use Cases
All backlog items had template-generated use cases that added no information beyond the title. **v006 implication:** Already addressed in this task -- all 7 v006 items now have authentic use cases.

## Tech Debt Addressed vs Deferred

### From v005 (Deferred)
1. **SPA fallback routing** - Deep link bookmarks won't work. Not relevant to v006 (pure Rust + API work).
2. **Dual WebSocket connections** - Shell and Dashboard open separate connections. Not relevant to v006.
3. **Client-side sorting limitation** - Sort only applies within current page. Not relevant to v006.
4. **Synchronous FFmpeg for thumbnails** - Blocks thread pool. Not directly relevant but may inform FFmpeg execution patterns in v006.

### From Earlier Versions (Still Open)
1. **Rust coverage at 75%** (target 90%, from v004) - Directly relevant: v006 adds substantial Rust code and should target 90%.
2. **Drop-frame timecode** (from v001) - Not relevant to v006.

## Architectural Decisions to Inform v006

1. **Rust for safety, not speed:** LRN-012 showed PyO3 FFI overhead makes Rust slower for simple operations. v006's Rust filter engine is justified by type safety and correctness (preventing invalid FFmpeg syntax), not performance.

2. **Python for business logic, Rust for input safety:** LRN-011 established the architectural boundary. For v006: Rust owns filter expression construction, validation, and serialization. Python owns API routing, effect registry, and clip model management.

3. **PyO3 builder pattern with PyRefMut:** LRN-001 provides the method chaining pattern needed for filter expression and drawtext builders. Use `PyRefMut<'_, Self>` for fluent builder APIs.

4. **Constructor DI for new services:** LRN-005 and v005's success with `create_app()` kwargs means new effect-related services should follow the same pattern.

5. **Validate AC against codebase during design:** LRN-016 warns against acceptance criteria referencing non-existent domain models. BL-043's AC references "clip/project model" effects storage -- this model extension must be designed before implementation.

## Statistics Reference

- v005: 4 themes, 11 features, 58/58 AC, all first-pass quality gates
- 627 Python tests, 93.28% coverage
- ~5,400 lines added across ~80 files
