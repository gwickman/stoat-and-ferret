# Retrospective Insights: v005 -> v006

Synthesized from v005's four theme retrospectives (frontend-foundation, backend-services, gui-components, e2e-testing).

## What Worked Well (Continue in v006)

### DI Pattern Consistency
The `create_app()` kwargs pattern worked cleanly for every new component in v005. v006 should continue this pattern for effect-related services (effect registry, effect application service).

### Feature Sequencing with Handoff Documents
v005 achieved zero-rework feature chains by using handoff documents between features. This is critical for v006 given the deep dependency chain: BL-037 -> BL-040/BL-041 -> BL-042 -> BL-043.

### All-First-Pass Quality Gates
Every v005 feature passed quality gates on the first iteration. Implementation plans were detailed enough to execute cleanly. v006 should maintain this standard.

### Infrastructure-First Theme Ordering
v005 followed the LRN-019 pattern: scaffolding first, then backend services, then GUI, then E2E. v006 should sequence similarly: expression engine first, then validation/composition, then builders, then API endpoints.

### Record-Replay Testing Pattern (LRN-008)
The FFmpeg executor record-replay pattern made thumbnail service testing straightforward. v006's contract tests (BL-040 AC5) can leverage this same pattern for FFmpeg filter validation.

## What Didn't Work (Avoid in v006)

### Dual WebSocket Connections
The Shell and Dashboard each opened separate WebSocket connections. While not directly relevant to v006's Rust-heavy scope, this tech debt should be noted for future GUI work.

### No Quality-Gaps Tracking
v005 generated zero quality-gaps.md files across 11 features. While this indicates clean execution, it also means no structured tech debt tracking. v006 should generate quality-gaps.md when debt is identified.

### Client-Side Sorting Limitation
Sort only applies within the current page. If v006 adds new list endpoints (e.g., effect listing), they should support server-side sorting from the start.

## Tech Debt: Addressed vs Deferred

### Addressed in v005
- Frontend scaffolding (no React project existed before v005)
- WebSocket infrastructure for real-time events
- Thumbnail generation pipeline
- Pagination total count bug fix
- E2E testing infrastructure with Playwright

### Deferred from v005 (Carrying Forward)
- SPA fallback routing for deep links
- WebSocket connection consolidation
- Search vs list `total` field semantic inconsistency
- Cross-browser E2E testing (Chromium only)
- Server-side sorting support

## Architectural Decisions Informing v006

### Python/Rust Boundary (LRN-011)
v005 was Python-heavy (React frontend, FastAPI endpoints). v006 swings back to Rust-heavy (expression engine, graph validation, filter builders). The boundary is clear: Rust owns filter expression construction and validation (BL-037-041), Python owns API routing and effect registration (BL-042-043).

### PyO3 Builder Pattern (LRN-001)
The `PyRefMut<'_, Self>` method chaining pattern from v001's FFmpegCommand should be reused for all v006 builders (expression builder, drawtext builder, speed control builder).

### PyO3 FFI Overhead (LRN-012)
Rust's value in v006 is correctness and type safety, not performance. Filter expression validation at compile time prevents runtime FFmpeg errors — that's the justification, not speed.

### Incremental Bindings Rule (AGENTS.md)
v006 must add PyO3 bindings in the same feature as Rust types. BL-037, BL-039 explicitly require this in their AC. Don't defer bindings.

## v005 Metrics (Baseline for v006 Planning)

- 4 themes, 11 features, all completed
- 627 Python tests, 85 Vitest tests, 7 Playwright E2E tests
- 93.28% Python coverage (threshold: 80%)
- All features passed on first quality gate iteration
- ~8 hours total execution time
