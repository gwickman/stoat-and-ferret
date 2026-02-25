# Theme 01: rust-bindings-cleanup — Retrospective

## Summary

Removed 11 unused PyO3 bindings and 1 dead Python bridge function from the Rust-Python boundary, reducing the public API surface to zero unused Python-facing bindings. The theme was delivered across three features, each targeting a distinct area: the `execute_command()` bridge, v001-era range/sanitize bindings, and v006-era expression/filter bindings. All Rust-internal implementations were preserved; only the Python-facing wrappers were removed.

## Feature Results

| Feature | Outcome | Bindings Removed | Tests Removed | PR |
|---------|---------|------------------|---------------|----|
| 001-execute-command-removal | Complete (5/5 acceptance) | `execute_command`, `CommandExecutionError` | 13 | #113 |
| 002-v001-bindings-trim | Complete (9/9 acceptance) | `find_gaps`, `merge_ranges`, `total_coverage`, `validate_crf`, `validate_speed` | 19 | #114 |
| 003-v006-bindings-trim | Complete (7/7 acceptance) | `PyExpr`, `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge`, + Expr class | 31 | #115 |

All three features passed all quality gates (ruff, mypy, pytest, cargo clippy, cargo test) with zero regressions.

## Metrics

- **Bindings removed:** 11 PyO3 wrappers + 1 Python bridge function + 1 error class
- **Tests removed:** ~63 (13 + 19 + 31) — all exclusively covering removed code
- **Final test suite:** 903 passed, 20 skipped, 93% coverage
- **Cargo tests:** 426 unit + 109 doc tests passing throughout
- **Files deleted:** `integration.py`, `test_integration.py`, `benchmarks/bench_ranges.py`

## Key Learnings

### What Went Well

- **Zero-caller verification before removal** — grepping for production callers before each removal gave high confidence and made each PR straightforward to review.
- **Preserving Rust internals** — keeping the Rust-side implementations intact (e.g., `Expr` enum, `FilterGraph` methods, range operations) means these can be re-exposed later without reimplementation.
- **Staged removal order** — tackling the pure-Python bridge first (001), then v001 bindings (002), then v006 bindings (003) provided a natural progression from simple to complex, with each feature building confidence.
- **Stub regeneration workflow** — running `cargo run --bin stub_gen` followed by manual stub reconciliation caught any drift between Rust and Python type surfaces.
- **CHANGELOG re-add triggers** — documenting exactly when each binding should be re-added (e.g., Phase 3 Composition Engine for `execute_command`) provides a clear signal for future versions.

### What Could Improve

- **Version-state.json tracking** — the version state still shows `features_complete: 0` despite all three features being complete. The state file was not updated as features completed, creating a discrepancy between actual and recorded progress.
- **No progress.md** — the theme referenced a `progress.md` or `progress.json` for tracking but none was created. Feature completion was tracked only through individual completion reports and git history.

## Technical Debt

| Item | Source | Priority | Notes |
|------|--------|----------|-------|
| 68 pre-existing mypy errors | 002-v001-bindings-trim report | Low | Not introduced by this theme; noted during quality gates |
| Re-add `execute_command` for Phase 3 Composition Engine | 001 CHANGELOG | Deferred | Trigger: when orchestrated multi-step FFmpeg pipelines need a unified entry point |
| Re-add range bindings if Python-side batch processing needs native speed | 002 CHANGELOG | Deferred | Currently no Python callers; Rust internals remain |
| Re-add Expr/filter composition bindings if Python-side filter graph building is needed | 003 CHANGELOG | Deferred | DrawtextBuilder and DuckingPattern use Rust-internal calls |

## Recommendations

1. **Update version-state.json as features complete** — automate or add a checklist step to mark features complete in the state file after each PR merges, so execution status stays accurate.
2. **Keep the "zero-caller grep" pattern** — verifying zero production callers before removing bindings was the key risk-mitigation step. Apply this to any future binding cleanup.
3. **Batch similar removals by version era** — grouping by v001/v006 origin made each feature cohesive and easy to review. Continue this pattern if further cleanup is needed.
4. **Consider a binding inventory script** — a script that lists all `#[pyfunction]` / `#[pymethods]` registrations alongside their Python import sites would make future audits faster.
