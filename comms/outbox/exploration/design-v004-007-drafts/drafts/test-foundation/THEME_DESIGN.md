# THEME DESIGN — 01: Test Foundation

## Goal

Establish core testing infrastructure — test doubles, dependency injection, and fixture factories — that all other themes depend on.

## Design Artifacts

- Refined logical design: `comms/outbox/versions/design/v004/006-critical-thinking/refined-logical-design.md` (Theme 01 section)
- Codebase patterns: `comms/outbox/versions/design/v004/004-research/codebase-patterns.md` (Repository Protocol, DI Pattern, Existing InMemory sections)
- External research: `comms/outbox/versions/design/v004/004-research/external-research.md` (§1 FastAPI DI, §2 Black Box Testing)
- Test strategy: `comms/outbox/versions/design/v004/005-logical-design/test-strategy.md` (Theme 01 section)

## Features

| # | Feature | Backlog | Dependencies |
|---|---------|---------|-------------|
| 1 | inmemory-test-doubles | BL-020 | None |
| 2 | dependency-injection | BL-021 | Feature 1 |
| 3 | fixture-factory | BL-022 | Feature 2 |

## Dependencies

- **Internal**: Strict sequential chain — each feature depends on the previous.
- **External**: None. Theme 01 has no external dependencies.
- **Downstream**: Theme 02 (blackbox-test-catalog requires fixture factory), Theme 03 (job-queue-infrastructure requires InMemoryJobQueue).

## Technical Approach

1. **InMemory test doubles** (BL-020): Enhance `AsyncInMemoryProjectRepository` with `copy.deepcopy()` isolation and seed helpers. Create `InMemoryJobQueue` with synchronous deterministic execution. Add contract tests verifying InMemory matches SQLite behavior.
2. **Dependency injection** (BL-021): Add optional `repository`, `video_repository`, `clip_repository`, `executor`, and `job_queue` params to `create_app()` defaulting to `None`. Migrate 4 `dependency_overrides` in conftest.py to `create_app()` params.
3. **Fixture factory** (BL-022): Create builder-pattern factory with `with_clip()`, `with_text_overlay()`, `build()` (domain objects), and `create_via_api()` (full HTTP path). Migrate existing inline test data construction incrementally.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R2: Deepcopy performance | Low (resolved) | Flat scalar dataclasses — negligible overhead |
| R5: Test breakage from DI migration | Low | Optional params defaulting to None; existing tests unchanged |
| `get_repository` / `get_video_repository` alias same instance | Low | Consolidate during DI migration |
