# Theme Retrospective: 01-filter-engine

**Version:** v006
**Theme:** 01-filter-engine
**Status:** Complete (3/3 features, 15/15 acceptance criteria passed)
**Execution Window:** 2026-02-18

---

## 1. Theme Summary

This theme built the foundational Rust filter infrastructure for stoat-and-ferret's effects engine: a type-safe FFmpeg expression builder, filter graph validation with cycle detection, and a programmatic graph composition API. These are the building blocks that all downstream filter builders and API endpoints (themes 02 and 03) depend on.

All three features were implemented in Rust with PyO3 bindings, Python type stubs, and comprehensive test coverage. The theme completed with zero quality gate failures and all 15 acceptance criteria passing on first iteration.

---

## 2. Feature Results

| Feature | Acceptance | Quality Gates | Iteration | Key Deliverable |
|---------|-----------|---------------|-----------|-----------------|
| 001-expression-engine | 5/5 PASS | All pass | 1 | `Expr` enum with builder API, operator overloading, precedence-aware serialization, proptest validation, PyO3 bindings |
| 002-graph-validation | 5/5 PASS | All pass | 1 | Opt-in `validate()` and `validated_to_string()` with unconnected pad, cycle (Kahn's), and duplicate label detection |
| 003-filter-composition | 5/5 PASS | All pass | 1 | `compose_chain`, `compose_branch`, `compose_merge` with auto-label management via `LabelGenerator` |

### Test Growth Across Features

| Feature | Rust Tests | Doc Tests | Python Tests | pytest Total |
|---------|-----------|-----------|-------------|-------------|
| 001-expression-engine | 237 | 90 | 644 passed | 644 |
| 002-graph-validation | 253 | 92 | 650 passed | 650 |
| 003-filter-composition | 270 | 95 | 664 passed | 664 |

---

## 3. Key Learnings

### What Worked Well

- **Infrastructure-first sequencing (LRN-019)**: Building expression types before graph validation before composition was the correct dependency order. Each feature built cleanly on the previous one with no rework needed.

- **Opt-in validation pattern**: Making `validate()` opt-in rather than automatic on `to_string()` preserved backward compatibility perfectly — all existing tests passed unchanged through every feature.

- **Auto-label generation with AtomicU64**: The `LabelGenerator` using a global atomic counter provided thread-safe, cross-instance unique labels without any coordination overhead. The `_auto_{prefix}_{seq}` format keeps labels recognizable in debugging.

- **Proptest for expression correctness**: Property-based testing on expression serialization caught edge cases that unit tests alone would miss (balanced parentheses, no NaN/Inf in output, arity validation).

- **Consistent PyO3 binding pattern**: All three features followed the same pattern — Rust implementation, `#[pymethods]` bindings, stub generation, Python tests — making each successive feature faster to implement.

### Patterns Discovered

- **Precedence-aware Display**: The expression serializer minimizes parentheses by tracking operator precedence, producing cleaner FFmpeg filter strings (e.g., `2+t*3` instead of `(2+(t*3))`).

- **Kahn's algorithm for cycle detection**: O(V+E) BFS-based topological sort is ideal for filter graph validation — detects cycles and identifies the involved labels for actionable error messages.

- **PyRefMut for composition methods**: Composition methods that mutate `FilterGraph` use `PyRefMut<'_, Self>` to properly handle Rust's borrow semantics through PyO3.

---

## 4. Technical Debt

No quality-gaps files were generated for any feature, indicating clean implementations. However, the following items merit consideration:

- **Label collision risk in long-running processes**: `LabelGenerator` uses a global `AtomicU64` counter that resets per process. For long-running server usage, label uniqueness is guaranteed within a process but labels will restart from 0 across process restarts. This is acceptable for the current architecture but worth noting.

- **Expression enum extensibility**: Adding new FFmpeg variables or functions requires modifying the `Variable`/`FuncName` enums. This is by design (type safety), but future FFmpeg version support may require enum expansion.

- **Stub sync is manual**: Type stubs in `stubs/` must be manually synced to `src/` after `stub_gen`. The `verify_stubs.py` script catches drift, but an automated step in CI could prevent it entirely.

---

## 5. Recommendations

### For Theme 02 (filter-builders)

- Build text overlay and speed control builders directly on top of `Expr`, `FilterGraph`, and the composition API. The foundations are solid and well-tested.
- Reuse the `compose_chain` pattern for builder APIs that apply sequences of filters.
- Follow the same PyO3 binding pattern established in this theme for consistency.

### For Future Similar Themes

- **Single-iteration success**: All features passed on first iteration, suggesting the design documents and acceptance criteria were well-specified. Continue this level of detail in future theme designs.
- **Incremental test growth**: The steady growth from 644 → 650 → 664 pytest tests shows healthy additive development without test churn.
- **Proptest is high-value**: Consider adding property-based tests for graph validation and composition in follow-up work — the expression proptest caught real edge cases.
