# Learnings Summary — Applicable to v010

## Highly Relevant Learnings

### LRN-010: Prefer stdlib asyncio.Queue over External Queue Dependencies
**Summary:** stdlib asyncio.Queue with producer-consumer pattern eliminates external queue dependencies while meeting single-worker requirements.
**Applicability:** Directly relevant — the existing `AsyncioJobQueue` is built on this pattern. v010 extends it with progress and cancellation. No need to add external dependencies.

### LRN-009: Handler Registration Pattern for Generic Job Queues
**Summary:** Explicit handler registration with factory-based dependency injection provides clean, testable job routing without global state.
**Applicability:** Directly relevant — the scan handler is registered with the job queue via this pattern. v010's progress reporting (BL-073) and cancellation (BL-074) must work within this handler registration model. The progress callback should be injectable through the same factory pattern.

### LRN-050: Incremental DI Wiring Is Fast and Low-Risk When Patterns Are Established
**Summary:** Wiring existing code into an established DI chain is fast and low-risk; batch similar wiring tasks for efficiency.
**Applicability:** v010 extends the existing DI pattern for new capabilities (progress, cancellation) rather than building greenfield infrastructure. This should be fast.

### LRN-005: Constructor DI over dependency_overrides for FastAPI Testing
**Summary:** Use create_app() constructor parameters instead of FastAPI dependency_overrides for cleaner, explicit test wiring.
**Applicability:** All new v010 components (async ffprobe, progress mechanism, cancellation flag) should be injectable via `create_app()` kwargs, not framework dependency overrides.

### LRN-033: Fix CI Reliability Before Dependent Development Cycles
**Summary:** Fix CI reliability issues before starting development cycles that depend on CI for PR merges.
**Applicability:** v010 Theme 1 must be completed before Theme 2 (progress/cancellation are meaningless if the event loop is frozen). BL-072 is the foundational fix that everything else depends on.

### LRN-040: Idempotent Startup Functions for Lifespan Wiring
**Summary:** Startup/lifespan functions must be idempotent using operation-appropriate guards.
**Applicability:** If v010 adds any lifespan initialization for the cancellation mechanism or progress infrastructure, it must follow the idempotent pattern.

## Moderately Relevant Learnings

### LRN-049: Guard Optional Broadcast Calls to Avoid Runtime Crashes
**Summary:** Guard optional broadcast/notification calls with if-checks so they become no-ops when absent.
**Applicability:** Progress reporting callbacks in BL-073 should follow this guard pattern — if no progress listener is registered, progress updates should be a no-op.

### LRN-042: Group Features by Modification Point for Theme Cohesion
**Summary:** Group features that modify the same code path into a single theme for efficiency.
**Applicability:** v010's theme grouping already follows this: Theme 1 groups all async-fix features (same code path: ffprobe/subprocess), Theme 2 groups job-control features (same code path: job queue).

### LRN-031: Detailed Design Specifications Correlate with First-Iteration Success
**Summary:** Detailed design specs with specific acceptance criteria lead to first-iteration success.
**Applicability:** All five v010 backlog items have detailed descriptions and specific, testable acceptance criteria. This positions v010 well for first-iteration success.

### LRN-045: Single-Feature Themes for Precisely-Scoped Bug Fixes
**Summary:** Isolate bug fixes as single-feature themes with their own acceptance criteria.
**Applicability:** BL-072 (the P0 bug fix) is the first feature in Theme 1, allowing it to be fixed and validated before the CI guardrails are added. However, it shares a theme with the guardrails since they modify the same async/subprocess code path.

### LRN-043: Explicit Assertion Timeouts in CI-Bound E2E Tests
**Summary:** Add explicit timeouts to state-transition assertions in CI-bound tests.
**Applicability:** BL-078 (event-loop responsiveness test) must have explicit timing assertions (2-second response threshold) rather than relying on default timeouts. CI environment variability makes this critical.

### LRN-047: WAL Mode Enables Safe Mixed Sync/Async SQLite Access
**Summary:** Separate sync connection with WAL mode works safely alongside aiosqlite.
**Applicability:** If progress reporting or job status requires database persistence, the WAL pattern is available. However, in-memory progress tracking is likely sufficient for v010.

## Low Relevance (Context Only)

### LRN-052: Run Formatter Before Linter to Avoid Double Fix Cycles
**Summary:** Run ruff format before ruff check to reduce fix cycles.
**Applicability:** Process efficiency during v010 implementation. Standard workflow.

### LRN-046: Maintenance Versions Succeed with Well-Understood Change Scoping
**Summary:** Maintenance versions with well-understood changes achieve higher first-iteration success.
**Applicability:** v010 is partly maintenance (BL-072 bug fix) and partly feature work (BL-073, BL-074). The bug fix portion should complete quickly.
