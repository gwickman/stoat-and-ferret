# Codebase Patterns — v012

## BL-061: execute_command() Architecture

### Definition
- **File**: `src/stoat_ferret/ffmpeg/integration.py:43-88`
- **Signature**: `execute_command(executor: FFmpegExecutor, command: FFmpegCommand, *, timeout: float | None = None) -> ExecutionResult`
- **Flow**: Calls `command.build()` (Rust validation) → `executor.run(args, timeout)` (Python subprocess)
- **Export**: `src/stoat_ferret/ffmpeg/__init__.py:10,29`

### FFmpegExecutor Protocol
- **File**: `src/stoat_ferret/ffmpeg/executor.py:38-58`
- **Implementations**: RealFFmpegExecutor (blocking subprocess.run, line 96), RecordingFFmpegExecutor, FakeFFmpegExecutor
- **Observable wrapper**: `src/stoat_ferret/ffmpeg/observable.py` — adds logging/metrics

### Production FFmpeg Usage
- **ThumbnailService**: `src/stoat_ferret/api/services/thumbnail.py:69` — calls `self._executor.run(args, timeout=30)` directly, bypasses execute_command entirely
- **No other production FFmpeg usage exists**

### Tests
- `tests/test_integration.py:12-202` — 8 test methods for execute_command, 5 for CommandExecutionError, 1 for exports

## BL-066: Effect Workshop Patterns

### Transition Endpoint
- **Route**: `src/stoat_ferret/api/routers/effects.py:478-634`
- **Request schema**: `TransitionRequest` at `src/stoat_ferret/api/schemas/effect.py:74-82` — `source_clip_id`, `target_clip_id`, `transition_type`, `parameters`
- **Response schema**: `TransitionResponse` at `effect.py:84-91` — adds `filter_string`
- **Adjacency check**: `effects.py:556-566` — `target_idx == source_idx + 1`, returns 400 NOT_ADJACENT

### Effect Workshop Component Hierarchy
- **EffectsPage**: `gui/src/pages/EffectsPage.tsx` (263 lines) — main orchestrator
- **ClipSelector**: `gui/src/components/ClipSelector.tsx` — single-clip button grid, `onSelect: (clipId: string) => void`
- **EffectCatalog**: `gui/src/components/EffectCatalog.tsx:79-210` — schema-driven browser with search/filter
- **EffectParameterForm**: `gui/src/components/EffectParameterForm.tsx:324-349` — JSON Schema → form fields
- **FilterPreview**: `gui/src/components/FilterPreview.tsx:75-134` — FFmpeg filter syntax highlighting
- **EffectStack**: `gui/src/components/EffectStack.tsx:13-120` — applied effects list

### Zustand Store Pattern
- **effectCatalogStore.ts**: UI state (search, category, selected effect, view mode)
- **effectFormStore.ts:51-80**: Schema-driven params with `defaultsFromSchema()` auto-population
- **effectStackStore.ts:31-85**: Per-clip effects with `fetchEffects()` and `removeEffect()`
- **effectPreviewStore.ts:17-26**: Filter string preview state

### Schema-Driven Flow
1. Backend defines `parameter_schema` as JSON Schema in `EffectDefinition` (`definitions.py:26-46`)
2. API returns schema via `/api/v1/effects` endpoint
3. Frontend `setSchema()` extracts defaults, renders appropriate field types (number/string/enum/boolean/color)
4. Preview calls `/api/v1/effects/preview` with debounced parameter changes (300ms)

### Transition Types Available
- **xfade**: Video crossfade (transition enum, duration, offset)
- **acrossfade**: Audio crossfade (duration, curve1 enum, curve2 enum, overlap boolean)
- Category derivation: `useEffects.ts:31-43` — "xfade" → "transition" category

### Transition Storage
- **Project model**: `src/stoat_ferret/db/models.py:110-129` — `transitions: list[dict[str, Any]] | None`
- **Database**: `schema.py:93` — `transitions_json TEXT` column
- **Serialization**: `project_repository.py:110-111,155-156,199-200` — JSON encode/decode

## BL-067: v001 PyO3 Bindings

### Function Locations (Rust)
| Function | File | Lines |
|----------|------|-------|
| find_gaps | `rust/stoat_ferret_core/src/timeline/range.rs` | impl:443-462, PyO3:549-554 |
| merge_ranges | `range.rs` | impl:490-507, PyO3:567-571 |
| total_coverage | `range.rs` | impl:531-535, PyO3:584-588 |
| validate_crf | `rust/stoat_ferret_core/src/sanitize/mod.rs` | impl:267-278, PyO3:559-562 |
| validate_speed | `sanitize/mod.rs` | impl:306-317, PyO3:579-582 |

### Rust-Internal Validation
- **CRF**: `ffmpeg/command.rs:582-586` — FFmpegCommand.validate() checks `crf > 51`
- **Speed**: `ffmpeg/speed.rs:116-117` — SpeedControl.new() delegates to `sanitize::validate_speed()`

### Python Exports
- **__init__.py**: All 5 imported (lines 87-98), in `__all__`, fallback stubs as `_not_built`
- **Stubs**: `stubs/stoat_ferret_core/_core.pyi` — find_gaps:496, merge_ranges:510, total_coverage:524, validate_crf:1734, validate_speed:1748

### Tests & Benchmarks
- **Parity tests**: `tests/test_pyo3_bindings.py` — TestRangeListOperations:786-950 (15 tests), TestSanitization:515-642 (4 tests for crf/speed + others)
- **Benchmarks**: `benchmarks/bench_ranges.py` — merge_ranges (2 benchmarks), find_gaps (1 benchmark)

## BL-068: v006 PyO3 Bindings

### Component Locations (Rust)
| Component | File | Lines |
|-----------|------|-------|
| Expr (PyExpr) | `rust/stoat_ferret_core/src/ffmpeg/expression.rs` | enum:199-210, PyO3:537-542 |
| validate | `ffmpeg/filter.rs` | FilterGraph method:686 |
| validated_to_string | `filter.rs` | method:799, PyO3:984-989 |
| compose_chain | `filter.rs` | method:828-865, PyO3:1006-1012 |
| compose_branch | `filter.rs` | method:871-913, PyO3:1031-1038 |
| compose_merge | `filter.rs` | method:920-961, PyO3:1056-1063 |

### Internal Rust Usage (NOT via PyO3)
- **DrawtextBuilder**: `ffmpeg/drawtext.rs:319-356` — uses Expr for alpha fade expressions
- **DuckingPattern**: `ffmpeg/audio.rs:720-745` — uses compose_branch, compose_merge, compose_chain

### Expr API Surface (17 static methods + operators)
- Static: constant, var, negate, between, if_then_else, if_not, lt, gt, eq_expr, gte, lte, clip, abs, min, max, modulo, not_
- Instance: `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__neg__`, `__str__`, `__repr__`

### Tests
- **Expr**: `test_pyo3_bindings.py:1006-1140` — TestExpr (16 methods)
- **Composition**: `test_pyo3_bindings.py:362-505` — ~14 methods
- **Stubs**: `_core.pyi:1464-1621` (Expr), `_core.pyi:1369-1450` (FilterGraph)

## BL-079: Job Status Schema

### Code Implementation
- **JobStatus enum**: `src/stoat_ferret/jobs/queue.py:17-25` — PENDING, RUNNING, COMPLETE, FAILED, TIMEOUT, CANCELLED (6 values)
- **JobResult**: `queue.py:36-52` — progress: `float | None`, documented as 0.0-1.0
- **set_progress**: `queue.py:349-358` — `value: float` between 0.0-1.0
- **Scan progress**: `src/stoat_ferret/api/services/scan.py:214-215` — `processed / total_files` (0.0 to 1.0)

### Spec Issues Found
- `docs/design/05-api-specification.md:295-302` — running state shows progress: null (should be 0.45)
- `05-api-specification.md:306-319` — complete state shows progress: null (should be 1.0)
- `05-api-specification.md:374-382` — cancel response shows status: "pending" (should be "cancelled")
- `docs/manual/03_api-reference.md:984` — says "Progress percentage (0-100)" (should be 0.0-1.0)
- Status enum in spec missing "cancelled" value
