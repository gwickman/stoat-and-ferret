# Investigation Log - v007 Critical Thinking

## Investigation 1: Two-Input Filter Pattern

**Query**: FilterChain struct implementation and multi-input support
**Files examined**:
- `rust/stoat_ferret_core/src/ffmpeg/filter.rs` (full file, 1855 lines)
- `tests/test_pyo3_bindings.py` (FilterComposition tests, lines 359-513)

**Evidence**:
- FilterChain.inputs is `Vec<String>` (filter.rs:439) - supports arbitrary input count
- `.input()` method pushes to vector (filter.rs:475-478)
- Display impl joins inputs: `self.inputs.join("")` (filter.rs:526)
- Rust test `test_filter_chain_multiple_inputs` (filter.rs:1239-1246): verifies `[0:v][1:v]concat=n=2:v=1:a=0[outv]`
- Rust test `test_validate_valid_concat_graph` (filter.rs:1401-1423): full validation passes for two-input merge
- PyO3 test `test_compose_merge_overlay` (test_pyo3_bindings.py:445-454): compose_merge works through Python
- PyO3 test `test_compose_two_inputs_merge` (test_pyo3_bindings.py:491-503): two independent chains merged via overlay

**Conclusion**: Two-input filters are proven through the full Rust -> PyO3 -> Python stack. xfade follows the same `[input1][input2]filter_name=params[output]` pattern as concat.

## Investigation 2: Audio Ducking Composition Pattern

**Query**: FilterGraph composition API suitability for asplit -> sidechaincompress -> amerge pattern
**Files examined**:
- `rust/stoat_ferret_core/src/ffmpeg/filter.rs` (compose_branch, compose_chain, compose_merge)
- `tests/test_pyo3_bindings.py` (FilterComposition tests)

**Evidence**:
- `compose_branch("0:a", 2, audio=True)` produces asplit (filter.rs:871-895)
- Rust test `test_compose_branch_audio` (filter.rs:1731-1737): verifies `asplit=outputs=2`
- PyO3 test `test_compose_branch_audio` (test_pyo3_bindings.py:419-427): Python binding works
- `compose_chain(label, filters)` applies filters sequentially (filter.rs:828-844)
- `compose_merge(inputs, filter)` merges multiple streams (filter.rs:920-940)
- Integration test `test_compose_chain_branch_merge` (filter.rs:1793-1810): full chain->branch->merge pipeline validated

**Ducking pattern mapped to composition API**:
```
graph.compose_branch("0:a", 2, audio=True)  -> [music, sidechain]
graph.compose_chain(sidechain, [sidechaincompress])  -> [compressed]
graph.compose_merge([music, compressed], amerge)  -> [ducked_output]
```

**Conclusion**: The composition API directly supports the ducking pattern. DuckingPattern should be a builder that constructs a FilterGraph, not a single FilterChain.

## Investigation 3: Registry Refactoring Scope

**Query**: _build_filter_string dispatch mechanism and EffectDefinition model
**Files examined**:
- `src/stoat_ferret/api/routers/effects.py` (lines 98-241)
- `src/stoat_ferret/effects/definitions.py` (full file)
- `src/stoat_ferret/effects/registry.py` (full file)

**Evidence**:
- `_build_filter_string()` (effects.py:98-142): only 2 branches - text_overlay and speed_control
- Called from single location: `apply_effect_to_clip()` (effects.py:207)
- EffectDefinition model (definitions.py:15-32): 5 fields, no build_fn
- Registry (registry.py:12-49): simple dict-based storage with register/get/list_all
- 2 registered effects: text_overlay and speed_control (definitions.py:141-153)
- preview_fn already demonstrates the callable pattern (definitions.py:32)

**Refactoring approach validated**:
1. Add `build_fn: Callable[[dict], str]` to EffectDefinition (additive, non-breaking)
2. Move text_overlay build logic from _build_filter_string into a callable
3. Move speed_control build logic into a callable
4. Replace if/elif with `definition.build_fn(parameters)`
5. Delete _build_filter_string function

**Conclusion**: Refactoring scope is minimal (2 branches, 1 caller). The preview_fn pattern on EffectDefinition already demonstrates the callable approach.

## Investigation 4: Effect Storage Format

**Query**: effects_json storage and access patterns
**Files examined**:
- `src/stoat_ferret/db/schema.py` (lines 96-108)
- `src/stoat_ferret/db/clip_repository.py` (full file)
- `src/stoat_ferret/api/routers/effects.py` (lines 217-227)

**Evidence**:
- clips table: `effects_json TEXT` column (schema.py:104)
- Serialization: `json.dumps(clip.effects)` on write (clip_repository.py:99, 141)
- Deserialization: `json.loads(effects_raw)` on read (clip_repository.py:172)
- Append pattern: `clip.effects.append(effect_entry)` (effects.py:225)
- No existing index-based access, no per-effect IDs
- In-memory repo uses deepcopy isolation (clip_repository.py:186-235)

**Conclusion**: Array index is stable for single-user editing. CRUD by index is simple to implement. UUID migration path is a future concern, not v007.

## Investigation 5: Prometheus Metrics Pattern

**Query**: Existing Prometheus counter naming convention
**Files examined**:
- `src/stoat_ferret/api/middleware/metrics.py` (full file)

**Evidence**:
- Counter: `http_requests_total` with labels `["method", "path", "status"]` (metrics.py:15-19)
- Histogram: `http_request_duration_seconds` with labels `["method", "path"]` (metrics.py:21-25)
- Naming: lowercase, underscores, `_total` suffix for counters, `_seconds` suffix for histograms

**Conclusion**: New effect counter should follow pattern: `effect_applications_total` with label `["effect_type"]`. Consistent with existing naming convention.

## Investigation 6: Existing Builder Pattern

**Query**: DrawtextBuilder and SpeedControl as templates for new builders
**Files examined**:
- `rust/stoat_ferret_core/src/ffmpeg/drawtext.rs` (struct definition)
- `rust/stoat_ferret_core/src/ffmpeg/speed.rs` (referenced)
- `tests/test_pyo3_bindings.py` (DrawtextBuilder tests: 1159-1353, SpeedControl tests: 1355-1570)

**Evidence**:
- DrawtextBuilder: struct with fields, fluent builder API, `.build()` returns Filter
- SpeedControl: struct with speed_factor, `.setpts_filter()` returns Filter, `.atempo_filters()` returns Vec<Filter>
- Both use `PyRefMut` chaining for PyO3 bindings
- Both have comprehensive Python tests verifying round-trip through PyO3

**Conclusion**: New audio and transition builders follow the identical pattern. The only new element is two-input filter construction (addressed in Investigation 1).
