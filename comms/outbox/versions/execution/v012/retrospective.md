# v012 — Version Retrospective

## Version Summary

**Version:** v012 — API Surface & Bindings Cleanup
**Started:** 2026-02-24
**Completed:** 2026-02-25
**Status:** Complete

v012 reduced the Rust-Python boundary surface by removing 11 unused PyO3 bindings and 1 dead Python bridge function, then closed two independent polish gaps in the Effect Workshop GUI and API documentation. The version addressed maintenance burden from unused code introduced in v001 and v006, while also wiring transition effects into the frontend and correcting misleading API spec examples.

## Theme Results

| Theme | Goal | Features | Outcome |
|-------|------|----------|---------|
| 01: rust-bindings-cleanup | Remove unused PyO3 bindings and dead bridge code | 3/3 complete | All 21/21 acceptance criteria passed. 11 bindings + 1 bridge + 1 error class removed. ~63 tests removed (covering only deleted code). PRs #113, #114, #115. |
| 02: workshop-and-docs-polish | Wire transition GUI and fix API spec docs | 2/2 complete | All 14/14 acceptance criteria passed. Transition tab added to Effect Workshop; 6 doc inconsistencies fixed. PRs #116, #117. |

## C4 Documentation

**Status:** Regeneration failed.

C4 architecture documentation was not regenerated for this version. This should be addressed in a future version or tracked as technical debt. Since v012 only removed bindings and added a GUI tab with doc corrections, the architectural impact is low — existing C4 documentation remains accurate at the container and context levels.

## Cross-Theme Learnings

1. **Zero-caller verification is essential for safe removal** — Both themes benefited from grepping for production callers before making changes. Theme 01 used this to confirm bindings had zero callers; Theme 02 used it to confirm which doc examples were consumed by external readers.

2. **Component reuse keeps diffs small** — Theme 02's transition GUI reused `EffectParameterForm`, `deriveCategory()`, and `ClipSelector` with optional props, delivering a full new tab with only 4 new files. This pattern should continue for future GUI features.

3. **progress.md was skipped in both themes** — Neither theme produced progress tracking files (`progress.md` / `progress.json`), though the theme definitions reference them. This is a recurring gap that should be addressed in process documentation.

4. **version-state.json fell out of sync** — Theme 01 noted that `features_complete` remained at 0 despite all features completing. State file updates should be automated or enforced via checklist.

5. **Documentation-only features are low-risk, high-value** — Feature 002 in Theme 02 touched only markdown files with no test changes required, yet improved spec accuracy for all API consumers.

## Technical Debt Summary

| Item | Source | Priority | Notes |
|------|--------|----------|-------|
| 68 pre-existing mypy errors | Both themes | Low | Not introduced by v012; persists across all features |
| C4 documentation regeneration failed | Version close | Medium | Re-run C4 regeneration in next version |
| Re-add `execute_command` for Phase 3 Composition Engine | Theme 01 / LRN-029 | Deferred | Trigger: orchestrated multi-step FFmpeg pipelines |
| Re-add range bindings if Python-side batch processing needs native speed | Theme 01 / BL-067 | Deferred | Currently no Python callers; Rust internals remain |
| Re-add Expr/filter composition bindings for Python-side filter graph building | Theme 01 / BL-068 | Deferred | DrawtextBuilder and DuckingPattern use Rust-internal calls |
| No E2E test for transition submit flow | Theme 02 | Low | Unit tests cover store and component; full flow is mocked |
| API doc examples may drift again if progress field semantics change | Theme 02 | Low | Consider generating doc examples from code or adding doc-lint |
| version-state.json not updated as features complete | Theme 01 | Low | Automate or add checklist step for state file updates |
| progress.md not created for either theme | Both themes | Low | Add automation or enforce via template |

## Process Improvements

1. **Automate or enforce progress.md creation** — Two consecutive themes omitted progress tracking files. Add a checklist step or automation to create `progress.md` when a theme starts.

2. **Update version-state.json as features complete** — Automate or add a checklist step to mark features complete in the state file after each PR merges, so execution status stays accurate.

3. **Add a quality-gaps.md template** — Even when a feature ships clean, an explicit "no known gaps" entry provides a clear signal that the step was performed rather than skipped.

4. **Consider doc-lint for API examples** — A lint or snapshot test comparing doc examples against actual response schemas would catch documentation drift earlier.

5. **Consider a binding inventory script** — A script listing all `#[pyfunction]` / `#[pymethods]` registrations alongside their Python import sites would make future binding audits faster.

6. **Keep the "zero-caller grep" and "component reuse" patterns** — Both were effective across themes and should be standard practice.

## Statistics

| Metric | Value |
|--------|-------|
| Themes | 2 |
| Features | 5 (3 + 2) |
| Acceptance criteria | 35/35 passed |
| Pull requests | 5 (#113–#117) |
| PyO3 bindings removed | 11 + 1 bridge + 1 error class |
| Tests removed | ~63 (covering only deleted code) |
| Files created (Theme 02) | 4 |
| Files modified (Theme 02) | 5 |
| Final backend test suite | 903 passed, 20 skipped, 93% coverage |
| Final frontend test suite | 194 tests across 32 files |
| Cargo tests | 426 unit + 109 doc tests |
| Quality gates passed | ruff, mypy, pytest, cargo clippy, cargo test, tsc, vitest |
