# Risks and Unknowns - v007 Effect Workshop GUI

## Risk: Two-Input Filter Pattern Untested in Builder Template

- **Severity**: medium
- **Description**: All v006 builders handle single-input filters. xfade, sidechaincompress, and acrossfade require two input streams. While FilterChain supports multiple inputs via `.input()` calls (verified in codebase-patterns.md), no existing builder has exercised this path end-to-end through PyO3 bindings and Python tests.
- **Investigation needed**: Verify FilterChain two-input handling works correctly with PyO3 bindings by building a minimal xfade example early in T01-F002. Confirm pad label assignment for two-input scenarios.
- **Current assumption**: UNVERIFIED — FilterChain's existing `.input()` API handles two-input filters without modification, based on code reading only.

## Risk: Audio Ducking Composite Pattern Complexity

- **Severity**: medium
- **Description**: The DuckingPattern (BL-044) composes multiple filters (asplit, sidechaincompress, amerge) into a single effect. This is more complex than individual filter builders and may need a different abstraction (composite pattern vs. single builder). No existing v006 builder composes multiple filters.
- **Investigation needed**: Determine whether DuckingPattern should be a builder that produces a FilterGraph or a higher-level composition that chains multiple builders. Test the FFmpeg ducking command (`asplit -> sidechaincompress -> amerge`) manually.
- **Current assumption**: UNVERIFIED — DuckingPattern can be implemented as a builder that outputs a FilterChain with multiple filters, following the existing pattern with additional internal steps.

## Risk: Registry Refactoring Scope

- **Severity**: medium
- **Description**: Replacing `_build_filter_string()` if/elif dispatch with registry-based dispatch is the documented v006 refactoring trigger. The refactoring touches the critical effect application path. While the function is private and all tests go through the API, any regression in filter string generation breaks effect application.
- **Investigation needed**: Audit all test paths that exercise `_build_filter_string()` indirectly (through the apply effect endpoint). Ensure parity tests compare exact filter string output before and after refactoring.
- **Current assumption**: The refactoring is backward-compatible because the same Rust builder functions are called; only the dispatch mechanism changes.

## Risk: Effect CRUD Operations May Need Schema Evolution

- **Severity**: low
- **Description**: Current `effects_json` stores effects as a JSON array with no per-effect ID. BL-051's edit/remove operations use array index (0-based). If effects are reordered or concurrently modified, array indices become unreliable. The evidence-log.md notes this is sufficient for v007 scope.
- **Investigation needed**: Confirm that effect ordering is always sequential (no concurrent modifications) and that array index is stable for the edit/remove use cases in BL-051.
- **Current assumption**: Array index is sufficient for v007. Document upgrade path to per-effect UUIDs if reordering or concurrent editing is needed later.

## Risk: Preview Thumbnails Deferred May Disappoint

- **Severity**: low
- **Description**: BL-051 AC #3 specifies "Preview thumbnail displays a static frame with the effect applied." Research recommends deferring actual thumbnail generation (requires server-side FFmpeg execution, temp files, cleanup). The filter string preview (BL-050) is the v007 alternative.
- **Investigation needed**: Validate that the filter string preview satisfies the transparency goal without visual thumbnail preview. Check if a placeholder/mock thumbnail is acceptable for BL-051.
- **Current assumption**: UNVERIFIED — BL-051 AC #3 can be satisfied with a filter string preview panel rather than an actual rendered thumbnail. This interpretation needs validation against the acceptance criteria intent.

## Risk: SPA Fallback Routing Still Missing

- **Severity**: low
- **Description**: The effect workshop will add new route(s) under `/gui/effects`. SPA fallback routing was deferred from v005 (LRN-023). Without it, direct URL access or page refresh on `/gui/effects` returns a 404. E2E tests work around this by navigating via client-side clicks.
- **Investigation needed**: Determine if SPA fallback is needed for v007 or can remain deferred. If users bookmark or share effect workshop URLs, they'll get 404s.
- **Current assumption**: SPA fallback remains deferred. E2E tests navigate via client-side routing (LRN-023). This is a known limitation documented since v005.

## Risk: Custom Form Generator vs. RJSF Trade-off

- **Severity**: low
- **Description**: Research recommends building a custom lightweight form generator instead of adopting RJSF as a dependency. This reduces dependencies but means implementing JSON schema interpretation, validation display, and widget mapping from scratch. If the schema complexity grows beyond the initial 5-6 parameter types, migration cost increases.
- **Investigation needed**: None for v007 — the custom approach is justified by the limited parameter type set. Document RJSF as the upgrade path if form complexity grows.
- **Current assumption**: The custom form generator handles the v007 parameter types (number, string, enum, boolean, color) without excessive complexity.

## Risk: Pre-Existing mypy Errors

- **Severity**: low
- **Description**: 11 pre-existing mypy errors were carried through v006 without resolution. New Python code in v007 (registry refactoring, API endpoints, effect CRUD) adds typed surface area that could interact with these existing errors.
- **Investigation needed**: Run mypy at the start of T02 to baseline the current error count. Ensure new code doesn't increase the count.
- **Current assumption**: New v007 code is type-correct and does not trigger additional mypy errors beyond the pre-existing 11.

## Risk: Rust Coverage Target Gap

- **Severity**: low
- **Description**: Rust coverage is at 75% (target: 90%). v007 adds substantial Rust code (audio builders, transition builders). If new code isn't well-tested, coverage drops further from the 90% target.
- **Investigation needed**: Measure Rust coverage before and after T01. Ensure new builders have comprehensive unit tests to maintain or improve coverage.
- **Current assumption**: The ~54 estimated Rust unit tests for T01 will push coverage closer to 90% by adding well-tested new code.
