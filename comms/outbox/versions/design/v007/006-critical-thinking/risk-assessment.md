# Risk Assessment - v007 Effect Workshop GUI

## Risk: Two-Input Filter Pattern Untested in Builder Template

- **Original severity**: medium
- **Category**: investigate now
- **Investigation**: Queried FilterChain struct, compose_merge API, and PyO3 binding tests for multi-input filter usage.
- **Finding**: Two-input filters are already fully supported and tested. FilterChain stores inputs as `Vec<String>` and `.input()` simply pushes labels. FilterGraph's `compose_merge()` explicitly wires multiple inputs into a single filter. Rust tests (filter.rs:1239-1246) verify `[0:v][1:v]concat=n=2:v=1:a=0[outv]`. Python PyO3 tests (test_pyo3_bindings.py:445-503) verify compose_merge with overlay and concat through the full binding stack.
- **Resolution**: Risk resolved. The two-input pattern for xfade/acrossfade follows the identical multi-input pattern already proven through concat. XfadeBuilder will use `FilterChain::new().input("0:v").input("1:v").filter(xfade_filter).output("out")`. No design change needed.
- **Affected themes/features**: T01-F002 (transition builders) - confirmed feasible as designed.

## Risk: Audio Ducking Composite Pattern Complexity

- **Original severity**: medium
- **Category**: investigate now
- **Investigation**: Analyzed FilterGraph composition API (compose_branch, compose_chain, compose_merge) for suitability to the ducking pattern (asplit -> sidechaincompress -> amerge).
- **Finding**: The composition API is purpose-built for this pattern. `compose_branch("0:a", 2, audio=True)` produces asplit with two output labels (filter.rs:871-895, tested in test_pyo3_bindings.py:419-427). `compose_chain()` applies sidechaincompress to one branch. `compose_merge()` combines branches via amerge. The full chain->branch->merge pattern is integration-tested (filter.rs:1793-1810, test_pyo3_bindings.py:475-489).
- **Resolution**: DuckingPattern should build a FilterGraph (not a single FilterChain) using the composition API. Implementation: `compose_branch` for asplit, `compose_chain` for sidechaincompress on the sidechain branch, `compose_merge` for amerge. This is a design clarification, not a structural change. The existing composition API handles the complexity.
- **Affected themes/features**: T01-F001 (audio mixing builders) - DuckingPattern uses FilterGraph composition.

## Risk: Registry Refactoring Scope

- **Original severity**: medium
- **Category**: investigate now
- **Investigation**: Audited `_build_filter_string()` in effects.py, EffectDefinition model, and all test paths exercising effect application.
- **Finding**: The refactoring scope is small and well-contained. `_build_filter_string()` (effects.py:98-142) has only 2 branches (text_overlay, speed_control). It is called from a single location: `apply_effect_to_clip()` (effects.py:207). EffectDefinition (definitions.py:15-32) has 5 fields; adding `build_fn` is additive. All existing tests exercise effects through the HTTP API, making the dispatch change transparent. The registry (registry.py) is a simple dict-based lookup.
- **Resolution**: Risk resolved. The refactoring adds `build_fn: Callable` to EffectDefinition, moves builder logic from `_build_filter_string()` into per-effect build functions, and replaces if/elif with `definition.build_fn(parameters)`. Parity tests should verify identical filter string output for text_overlay and speed_control before/after refactoring.
- **Affected themes/features**: T02-F001 (registry refactor) - confirmed small, well-bounded scope.

## Risk: Effect CRUD Operations May Need Schema Evolution

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: Confirmed storage format. effects_json is TEXT in clips table (schema.py:104). Effects stored as JSON array via `json.dumps(clip.effects)` (clip_repository.py:99). Append-only: `clip.effects.append(effect_entry)` (effects.py:225). No existing index-based access code.
- **Finding**: Array index is stable for single-user editing. No concurrent modification path exists in the current architecture. CRUD endpoints (PATCH/DELETE by index) would be new in v007.
- **Resolution**: Accept array index for v007. New CRUD endpoints validate index bounds and return 404 for out-of-range. Document UUID-based effect IDs as upgrade path for future multi-user support.
- **Affected themes/features**: T03-F004 (effect builder workflow) - CRUD endpoints use array index.

## Risk: Preview Thumbnails Deferred May Disappoint

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: Reviewed BL-051 AC #3 ("Preview thumbnail displays a static frame with the effect applied") against the filter string preview design (BL-050).
- **Finding**: The filter string preview IS the transparency feature - users see exact FFmpeg commands. Rendered thumbnails require server-side FFmpeg execution, temp file management, and cleanup - significant additional scope. The filter string preview satisfies the transparency goal directly.
- **Resolution**: BL-051 AC #3 implemented as a filter string preview panel showing the generated FFmpeg command. This satisfies the transparency intent. A placeholder section notes "visual preview coming in a future version." No structural design change.
- **Affected themes/features**: T03-F004 (effect builder workflow) - preview panel instead of rendered thumbnail.

## Risk: SPA Fallback Routing Still Missing

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: Known limitation since v005 (LRN-023). Effect workshop adds /gui/effects route under the same constraint.
- **Finding**: E2E tests work around this by navigating via client-side clicks. Direct URL access/refresh on /gui/effects returns 404.
- **Resolution**: Continue deferred approach. E2E tests use client-side navigation. Document as known limitation in API specification update (T04-F002). No design change.
- **Affected themes/features**: T04-F001 (E2E tests) - tests navigate via client-side routing.

## Risk: Custom Form Generator vs. RJSF Trade-off

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: None needed - decision already made in Task 005 based on research evaluation.
- **Finding**: Custom form generator justified by limited parameter type set (5-6 types). RJSF adds 50KB+ dependency for functionality largely unused.
- **Resolution**: Custom form generator for v007. Document RJSF as upgrade path if form complexity grows beyond current 5-6 parameter types.
- **Affected themes/features**: T03-F002 (dynamic parameter forms) - custom implementation.

## Risk: Pre-Existing mypy Errors

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: Unable to run mypy empirically in this exploration context. The 11 pre-existing errors are documented from v006.
- **Finding**: New v007 Python code (registry refactoring, API endpoints, CRUD) adds typed surface area. The risk is that new code interacts with existing unresolved type issues.
- **Resolution**: Add mypy baseline step at start of T02-F001: run mypy, record current error count. New code must not increase the count. If new errors surface, they must be resolved within the feature that introduces them.
- **Affected themes/features**: T02-F001 (registry refactor), T02-F002 (transition API), T03-F004 (effect CRUD).

## Risk: Rust Coverage Target Gap

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: Current coverage at 75% vs 90% target. v007 T01 adds ~54 new Rust unit tests.
- **Finding**: New builders with comprehensive tests should improve coverage. The gap is in existing code, not new code.
- **Resolution**: Require >90% coverage for new Rust modules added in T01. Track coverage before/after T01 completion. If overall coverage doesn't reach 90%, document remaining gaps as tech debt.
- **Affected themes/features**: T01 (Rust filter builders) - coverage tracking per feature.
