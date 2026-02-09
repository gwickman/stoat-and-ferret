# Theme Retrospective — 02: Black Box & Contract Testing

## Theme Summary

Theme 02 delivered end-to-end black box tests, FFmpeg executor contract tests, and unified search behavior across repository implementations. Three features were delivered independently, each targeting a different testing gap:

1. **Black box test catalog** — 30 REST API workflow tests exercising project CRUD, clips, error handling, and edge cases through HTTP with no internal imports
2. **FFmpeg contract tests** — 21 parametrized tests verifying Real, Recording, and Fake executors produce identical behavior, with a new `strict` mode for args verification
3. **Search unification** — Replaced substring matching with per-token `startswith` in InMemory repositories to match FTS5 semantics, with 7 parity tests

All three features passed quality gates (ruff, mypy, pytest) and met their acceptance criteria. The theme added 58 new tests, growing the suite from 455 to 507 passing tests while maintaining 93% coverage.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Tests Added | Status |
|---|---------|------------|---------------|-------------|--------|
| 1 | blackbox-test-catalog | 6/6 PASS | All PASS | 30 | Complete |
| 2 | ffmpeg-contract-tests | 5/5 PASS | All PASS | 21 | Complete |
| 3 | search-unification | 3/3 PASS | All PASS | 7 | Complete |

**Totals:** 14/14 acceptance criteria passed. 58 new tests. 0 regressions.

## Key Learnings

### What Went Well

- **Independent features enabled parallel-safe execution.** Unlike Theme 01's sequential chain, all three features had no inter-dependencies within the theme. Each could be implemented and merged without conflict.
- **Theme 01 infrastructure paid off immediately.** The `create_app()` DI pattern, InMemory test doubles, and fixture factory from Theme 01 were directly consumed by the blackbox tests, validating the foundation investment.
- **Recording/Fake executor pattern scales well.** The existing record-replay architecture for FFmpeg made contract testing straightforward. Adding `strict` mode was a minimal change (23 lines in `executor.py`) that enabled meaningful args verification.
- **Parity tests catch real behavioral drift.** The search unification parity tests confirmed that InMemory and SQLite repositories now produce consistent results for common query patterns, closing a gap identified during design (R3).

### Patterns Discovered

- **Conftest helpers over fixtures for API test data.** The blackbox tests use `create_project_via_api()` and `add_clip_via_api()` helper functions rather than heavy fixtures. This keeps test setup explicit and readable while exercising the real HTTP stack.
- **Per-token `startswith` is the right InMemory search strategy.** It matches FTS5 prefix-match behavior for the common case while being simple to implement and reason about. Documented known differences (multi-word phrases, field scope) rather than trying to emulate FTS5 exactly.
- **`@pytest.mark.requires_ffmpeg` for conditional CI.** Separating tests that need a real FFmpeg binary from those using fakes allows the full suite to run in any environment. 6 contract tests are skipped without FFmpeg, 15 always run.

### What Could Improve

- **No scan workflow coverage in blackbox tests.** The scan endpoint requires real video files and FFmpeg for metadata probing, so it couldn't be tested in the blackbox suite. This is deferred to future work with real FFmpeg integration.
- **Quality-gaps documents were not generated.** The prompt referenced `quality-gaps.md` files per feature, but none were produced during execution. The completion reports served as the primary quality record instead.

## Technical Debt

| Item | Source | Priority | Notes |
|------|--------|----------|-------|
| Scan endpoint lacks blackbox test coverage | Feature 1 | Medium | Requires real video files and FFmpeg; deferred to BL-024 scope |
| 3 known FTS5 behavioral differences documented but not resolved | Feature 3 | Low | Prefix vs substring, multi-word phrases, field scope — documented inline in repository code |
| Duplicate project names allowed (no unique constraint) | Feature 1 | Low | Tested and confirmed as current behavior; add constraint if business rules change |
| Existing tests not migrated to blackbox patterns | Feature 1 | Low | Migrate incrementally as tests are touched |

## Recommendations

1. **For Theme 03 (async-scan):** The blackbox test infrastructure is ready for scan workflow tests once real video files can be provisioned. Use the `@pytest.mark.requires_ffmpeg` pattern established in Feature 2.
2. **For future contract tests:** The parametrized executor pattern (`Real`, `Recording`, `Fake`) can be extended to other external dependencies (e.g., database, file system). The `strict` mode pattern is reusable.
3. **For search enhancements:** The parity test framework in `test_search_parity.py` should be extended when new search features are added. It provides a safety net against InMemory/SQLite divergence.
4. **Quality-gaps generation:** Consider making quality-gaps.md a required output of feature execution to maintain consistency with the retrospective template expectations.

## Metrics

- **Lines changed:** +1,825 / -18 across 22 files
- **Source files changed:** 4 (3 modified, 1 marker added to pyproject.toml)
- **Test files changed:** 8 (1 modified, 7 created)
- **Final test count:** 507 passed, 14 skipped
- **Coverage:** 93.04%
- **Commits:** 3 (one per feature, via PR)
