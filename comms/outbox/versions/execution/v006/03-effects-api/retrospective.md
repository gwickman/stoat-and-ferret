# Theme Retrospective: 03-effects-api

## Theme Summary

Theme 03 bridged the Rust filter engine (themes 01–02) with the Python REST API and data model. It delivered three features: an effect discovery endpoint backed by a registry, a clip effect application endpoint with persistent storage, and architecture documentation updates. All three features passed every acceptance criterion (15/15) and all quality gates (ruff, mypy, pytest) on every iteration.

The theme corresponds to milestones M2.2–M2.3 (API integration) on the project roadmap, which were checked off upon completion.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Iterations | Outcome |
|---|---------|-----------|---------------|------------|---------|
| 001 | effect-discovery | 5/5 PASS | ruff/mypy/pytest PASS | 1 | Complete |
| 002 | clip-effect-api | 5/5 PASS | ruff/mypy/pytest PASS | 1 | Complete |
| 003 | architecture-docs | 5/5 PASS | ruff/mypy/pytest PASS | 1 | Complete |

**Test suite growth**: 722 passed (pre-theme) -> 733 passed (post-theme), +11 net new tests. Coverage held steady at ~93%.

## Key Learnings

### What Worked Well

1. **Existing DI pattern scaled cleanly.** The `create_app()` kwarg -> `app.state` pattern (already established for `clip_service`, `project_service`) extended naturally to `effect_registry` with zero friction. The fallback-to-default pattern in the dependency function kept test code simple.

2. **Rust builders as the single source of truth for filter strings.** Both the discovery endpoint (preview_fn) and the application endpoint (_build_filter_string) call the same DrawtextBuilder/SpeedControl Rust types. This guarantees that previewed filters match applied filters.

3. **Simple data structures over premature abstractions.** The registry is a plain dict wrapper. Effects are stored as a JSON list column rather than a separate table. The filter builder dispatch is if/elif rather than a plugin system. All of these were sufficient for the current scope (2 effect types) and easy to understand.

4. **Documentation as a first-class feature.** Dedicating feature 003 to architecture docs ensured the docs were updated in lockstep with the code, rather than as an afterthought. The API specification reconciliation caught discrepancies between the original design and the actual implementation.

### Patterns Discovered

- **Router prefix design**: The effects router serves both `/api/v1/effects` (global discovery) and `/api/v1/projects/{id}/clips/{id}/effects` (per-clip application). Using `/api/v1` as the router prefix with explicit full paths in each route handler accommodated both cleanly.

- **JSON column for simple nested data**: Storing effects as `effects_json TEXT` with JSON serialization/deserialization in the repository layer avoids the overhead of a join table when the data is always read/written as a unit with its parent clip.

## Technical Debt

| Item | Source | Severity | Notes |
|------|--------|----------|-------|
| `_build_filter_string()` uses if/elif dispatch | 002 handoff | Low | Sufficient for 2 effect types; refactor to registry-based dispatch when a 3rd effect is added |
| No effect remove/update/delete endpoints | 002 out-of-scope | Low | Effects are append-only; CRUD operations deferred to future version |
| No effect ordering or priority system | 002 out-of-scope | Low | Not needed until multiple effects per clip are common |
| No effect preview endpoint (dry-run) | 002 out-of-scope | Low | Marked as "Future" in API spec |
| Unimplemented endpoints marked "Future" in API spec | 003 report | Info | Preview, update, delete endpoints documented but not implemented |

## Recommendations

1. **When adding a 3rd effect type**, refactor `_build_filter_string()` to a dispatch table or registry-based approach. The current if/elif is a conscious trade-off, not an oversight.

2. **Effect CRUD** (update, delete, reorder) should be a dedicated theme in a future version. The append-only JSON list is fine for the current scope but won't support editing workflows.

3. **Continue the docs-as-feature pattern.** Having architecture docs as an explicit deliverable kept them accurate and reviewable. Future themes with API or architectural changes should include a documentation feature.

4. **The EffectRegistry is extensible.** Future dynamic effect loading (e.g., v007 Effect Workshop) can build on the existing `register()` API without modifying the discovery or application endpoints.
