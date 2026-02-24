# Impact Table — v012

| # | Area | Description | Classification | Resulting Work Item | Caused By |
|---|------|-------------|----------------|---------------------|-----------|
| 1 | C4-docs | c4-code-stoat-ferret-ffmpeg.md references execute_command as FFmpeg Integration component | small | Update C4 code doc to remove/update execute_command reference | BL-061 |
| 2 | C4-docs | c4-component-application-services.md lists execute_command in FFmpeg Executor operations | small | Update C4 component doc to reflect execute_command outcome | BL-061 |
| 3 | async-safety | execute_command uses subprocess.run (blocking) via FFmpegExecutor.run(); if wired into async render workflow, this blocks the event loop | substantial | If wiring: wrap executor call in asyncio.to_thread or use async subprocess; if removing: N/A | BL-061 |
| 4 | cross-version-wiring | execute_command depends on FFmpegCommand.build() from Rust; decision to wire or remove affects what counts as "used" for BL-067/BL-068 | small | Document decision rationale before starting BL-067/BL-068 audits | BL-061 |
| 5 | stubs | stubs/stoat_ferret_core/_core.pyi contains find_gaps, merge_ranges, total_coverage, validate_crf, validate_speed definitions | small | Regenerate stubs after removing trimmed bindings | BL-067 |
| 6 | __init__.py | src/stoat_ferret_core/__init__.py exports all 5 functions (imports, fallback stubs, __all__) | small | Update __init__.py exports to match trimmed API surface | BL-067 |
| 7 | C4-docs | c4-code-rust-stoat-ferret-core-timeline.md documents find_gaps, merge_ranges, total_coverage | small | Update C4 timeline code doc to remove trimmed functions | BL-067 |
| 8 | C4-docs | c4-code-stubs-stoat-ferret-core.md documents all 5 v001 binding stubs | small | Update C4 stubs doc to reflect trimmed API surface | BL-067 |
| 9 | security-audit | docs/design/09-security-audit.md marks validate_crf and validate_speed as "Secure" with complete coverage | small | Update security audit to note removal rationale if sanitization bindings are trimmed | BL-067 |
| 10 | performance-docs | docs/design/10-performance-benchmarks.md benchmarks find_gaps and merge_ranges (shows Python is 3.4-4.8x faster due to FFI overhead) | small | Remove benchmark entries for trimmed bindings | BL-067 |
| 11 | tests | tests/test_pyo3_bindings.py has 18 tests for the 5 v001 functions | small | Remove or update parity tests for trimmed bindings | BL-067 |
| 12 | benchmarks | benchmarks/bench_ranges.py benchmarks find_gaps and merge_ranges | small | Remove benchmark entries for trimmed bindings | BL-067 |
| 13 | CHANGELOG | docs/CHANGELOG.md references v001 binding additions | small | Add CHANGELOG entry for binding removals in v012 | BL-067 |
| 14 | stubs | stubs/stoat_ferret_core/_core.pyi contains Expr class (~157 lines), validate, validated_to_string, compose_chain, compose_branch, compose_merge | small | Regenerate stubs after removing trimmed bindings | BL-068 |
| 15 | __init__.py | src/stoat_ferret_core/__init__.py exports all 6 v006 functions/types | small | Update __init__.py exports to match trimmed API surface | BL-068 |
| 16 | C4-docs | c4-code-rust-stoat-ferret-core-timeline.md and c4-code-stoat-ferret-core.md document v006 binding functions | small | Update C4 docs to remove trimmed binding references | BL-068 |
| 17 | tests | tests/test_pyo3_bindings.py has ~70 test methods for v006 bindings (Expr, validate, composition) | small | Remove or restructure parity tests for trimmed bindings | BL-068 |
| 18 | CHANGELOG | docs/CHANGELOG.md references v006 binding additions | small | Add CHANGELOG entry for binding removals in v012 | BL-068 |
| 19 | gui-input | Transition GUI (BL-066) requires clip-pair selection (source + target); current ClipSelector only supports single-clip selection | substantial | Design clip-pair selector component with adjacency validation for transition UX | BL-066 |
| 20 | cross-version-wiring | BL-066 depends on POST /projects/{id}/effects/transition endpoint from v007; must verify endpoint interface matches GUI expectations | small | Verify transition endpoint request/response schema before GUI implementation | BL-066 |
| 21 | docs-api-spec | docs/design/05-api-specification.md scan job examples (lines 280-361) all show progress: null | small | Fix scan job examples to show realistic progress values alongside render examples | BL-079 |
| 22 | docs-manual | docs/manual/03_api-reference.md mirrors the problematic progress: null scan example | small | Update API reference manual to show realistic progress values | BL-079 |
| 23 | caller-impact | BL-067/BL-068 binding removal: no production callers exist — all 11 functions have zero callers in src/; only test and benchmark consumers | small | No caller-adoption risk; removal is safe from caller perspective | BL-067, BL-068 |
| 24 | caller-impact | BL-061 execute_command has zero production callers; if wiring, must identify and update at least one render/export caller to exercise the bridge | substantial | If wiring: identify render/export code path to call execute_command; if removing: no caller risk | BL-061 |
