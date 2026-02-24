# Impact Summary — v012

## Small Impacts (sub-task scope)

### BL-061: execute_command resolution
- **#1**: Update C4 code doc (`c4-code-stoat-ferret-ffmpeg.md`) to reflect execute_command outcome
- **#2**: Update C4 component doc (`c4-component-application-services.md`) to reflect execute_command outcome
- **#4**: Document wire-vs-remove decision rationale before BL-067/BL-068 audits begin

### BL-067: v001 PyO3 bindings audit
- **#5**: Regenerate stubs after trimming (stubs/stoat_ferret_core/_core.pyi)
- **#6**: Update src/stoat_ferret_core/__init__.py exports (imports, fallback stubs, __all__)
- **#7**: Update C4 timeline code doc for removed functions
- **#8**: Update C4 stubs doc for trimmed API surface
- **#9**: Update security audit doc if validate_crf/validate_speed are removed
- **#10**: Remove performance benchmark entries for trimmed range operations
- **#11**: Remove/update 18 parity tests in test_pyo3_bindings.py
- **#12**: Remove benchmark entries in bench_ranges.py
- **#13**: Add CHANGELOG entry for binding removals

### BL-068: v006 PyO3 bindings audit
- **#14**: Regenerate stubs after trimming (Expr class, validate, composition functions)
- **#15**: Update src/stoat_ferret_core/__init__.py exports
- **#16**: Update C4 docs for removed binding references
- **#17**: Remove/restructure ~70 parity tests in test_pyo3_bindings.py
- **#18**: Add CHANGELOG entry for binding removals

### BL-066: Transition GUI
- **#20**: Verify transition endpoint schema matches GUI expectations (cross-version wiring check)

### BL-079: API spec examples
- **#21**: Fix scan job examples in API spec (lines 280-361) to show realistic progress values
- **#22**: Update API reference manual (docs/manual/03_api-reference.md) to match

### Caller Impact (informational)
- **#23**: BL-067/BL-068 binding removals carry no caller-adoption risk — zero production callers confirmed for all 11 functions

## Substantial Impacts (feature scope)

- **#3 (BL-061)**: Async safety — if execute_command is wired into an async render workflow, the blocking subprocess.run call in FFmpegExecutor.run() must be wrapped in asyncio.to_thread or replaced with async subprocess. This requires its own design consideration within the BL-061 feature.

- **#19 (BL-066)**: Clip-pair selection UX — transitions require selecting two adjacent clips (source and target), but the current ClipSelector component only supports single-clip selection. A new clip-pair selector component with adjacency validation is needed. This is a core part of the BL-066 feature design.

- **#24 (BL-061)**: If wiring execute_command, must identify and update at least one render/export code path to actually call it. Without a production caller, the wiring is ineffective (LRN-079 pattern).

## Cross-Version Impacts (backlog scope)

None identified. All impacts can be addressed within v012 scope. The C4 documentation drift (BL-069) will accumulate further from v012 changes, but this is already acknowledged as excluded from v012 scope.
