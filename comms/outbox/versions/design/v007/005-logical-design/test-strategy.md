# Test Strategy - v007 Effect Workshop GUI

## Theme 01: 01-rust-filter-builders

### F001: 001-audio-mixing-builders (BL-044)

**Unit tests**:
- AmixBuilder: input count validation, weight assignment, duration modes, normalize toggle, build output (~8 tests)
- VolumeBuilder: linear/dB modes, range validation (0.0-10.0), precision options, build output (~6 tests)
- AfadeBuilder: fade in/out types, duration validation, all 12 curve types, start_time parameter (~8 tests)
- DuckingPattern: threshold/ratio/attack/release parameters, two-input filter chain, build output (~5 tests)
- Edge cases: silence input, clipping prevention, format mismatch handling (~3 tests)

**System/Golden scenarios**: None — builders produce filter strings, no execution flow changes.

**Parity tests**: Python builder calls must produce identical filter strings to direct Rust calls. Verify PyO3 bindings round-trip for all builders (~4 parity tests).

**Contract tests**: None — no new DTO models; builders return Filter structs (existing contract).

**Replay fixtures**: None — no new execution patterns.

### F002: 002-transition-filter-builders (BL-045)

**Unit tests**:
- FadeBuilder: fade in/out, duration, color parameter, alpha mode, build output (~6 tests)
- XfadeBuilder: all 64 TransitionType enum variants validation, duration range (0-60s), offset parameter, two-input filter chain (~8 tests)
- TransitionType enum: exhaustive variant test, string conversion round-trip (~3 tests)
- AcrossfadeBuilder: duration, curve pairs (curve1/curve2), overlap toggle (~4 tests)
- Parameter validation: invalid duration, invalid transition type, helpful error messages (~3 tests)

**System/Golden scenarios**: None — builders produce filter strings.

**Parity tests**: Python bindings produce identical filter strings to direct Rust calls (~3 parity tests).

**Contract tests**: None — uses existing Filter struct.

**Replay fixtures**: None.

---

## Theme 02: 02-effect-registry-api

### F001: 001-effect-registry-refactor (BL-047)

**Unit tests**:
- EffectDefinition with build_fn: callable invocation, parameter passing (~3 tests)
- JSON schema validation: valid params pass, invalid params rejected with errors, missing required fields (~5 tests)
- Registry dispatch: build_fn called for each registered effect type (~4 tests)
- All effects registered: text_overlay, speed_control, audio_mix, volume, audio_fade, audio_ducking, video_fade, xfade, acrossfade (~1 registration completeness test)
- Prometheus counter: effect_applications_total increments with correct effect_type label (~2 tests)

**System/Golden scenarios**: Effect application flow uses registry dispatch instead of if/elif. Golden test: apply text overlay effect via API, verify same filter string output as v006 (~1 regression test).

**Parity tests**: Existing effect application responses unchanged after refactoring (~2 parity tests for text_overlay, speed_control).

**Contract tests**: EffectDefinition schema with new build_fn field round-trip (~1 test).

**Replay fixtures**: None.

### F002: 002-transition-api-endpoint (BL-046)

**Unit tests**:
- Clip adjacency validation: adjacent clips pass, non-adjacent rejected, empty timeline rejected (~4 tests)
- Transition parameter validation via registry schema (~2 tests)
- Transition storage in project model (~2 tests)

**System/Golden scenarios**: POST /effects/transition: apply xfade between adjacent clips, verify filter string in response (~1 black-box test).

**Parity tests**: Response schema matches OpenAPI spec (~1 parity test).

**Contract tests**: TransitionRequest/TransitionResponse schema round-trip (~2 tests).

**Replay fixtures**: None.

### F003: 003-architecture-documentation

No tests — documentation feature.

---

## Theme 03: 03-effect-workshop-gui

### F001: 001-effect-catalog-ui (BL-048)

**Unit tests** (Vitest):
- EffectCatalog component: renders effect cards from API data, grid/list toggle (~3 tests)
- Search filter: narrows displayed effects by name (~2 tests)
- Category filter: filters by effect category (~2 tests)
- AI hint tooltips: display on hover/focus (~1 test)
- Click handler: selecting effect triggers callback (~1 test)
- useEffects hook: fetches from /effects, handles loading/error states (~3 tests)
- effectCatalogStore: search/filter state, selected effect state (~2 tests)

**System/Golden scenarios**: None — component tests cover rendering.

**Parity tests**: None — new frontend component.

**Contract tests**: None — consumes existing GET /effects response.

**Replay fixtures**: None.

### F002: 002-dynamic-parameter-forms (BL-049)

**Unit tests** (Vitest):
- Form generator: renders correct input type for each schema property type (~5 tests: number/range, string, enum, boolean, color)
- Range slider: respects min/max from schema (~1 test)
- Enum dropdown: populates options from schema enum values (~1 test)
- Default values: pre-populated from schema defaults (~1 test)
- Validation: inline error display from backend validation response (~2 tests)
- effectFormStore: parameter state, validation error state (~2 tests)
- onChange handlers: parameter value updates propagate to store (~1 test)

**System/Golden scenarios**: None.

**Parity tests**: None — new component.

**Contract tests**: None.

**Replay fixtures**: None.

### F003: 003-live-filter-preview (BL-050)

**Unit tests** (Vitest):
- FilterPreview component: renders filter string in monospace panel (~1 test)
- Debounced API call: verify debounce behavior (300ms) (~1 test)
- Syntax highlighting: filter names and pad labels colored (~1 test)
- Copy-to-clipboard: click copies filter string (~1 test)
- effectPreviewStore: filter string state, loading state (~2 tests)
- useEffectPreview hook: debounced fetch, error handling (~2 tests)

**System/Golden scenarios**: None.

**Parity tests**: None.

**Contract tests**: None.

**Replay fixtures**: None.

### F004: 004-effect-builder-workflow (BL-051)

**Unit tests** (Vitest):
- ClipSelector: renders clips from current project, selection handler (~3 tests)
- EffectStack: renders ordered list of effects for selected clip (~2 tests)
- Edit action: opens parameter form with existing values (~1 test)
- Remove action: shows confirmation dialog, calls delete endpoint (~2 tests)
- effectStackStore: per-clip effect list, add/edit/remove operations (~3 tests)
- EffectsPage: composes catalog, form, preview, stack into workflow (~1 integration test)

**Unit tests** (Python — effect CRUD endpoints):
- PATCH /projects/{id}/clips/{id}/effects/{index}: update effect at index (~3 tests)
- DELETE /projects/{id}/clips/{id}/effects/{index}: remove effect at index (~3 tests)
- Invalid index handling: out-of-range index returns 404 (~2 tests)

**System/Golden scenarios**: Full workflow: select effect -> configure params -> apply to clip -> verify in effect stack (~1 golden test).

**Parity tests**: CRUD endpoint responses match OpenAPI spec (~2 parity tests).

**Contract tests**: EffectUpdateRequest/EffectDeleteResponse schemas (~2 tests).

**Replay fixtures**: None.

---

## Theme 04: 04-quality-validation

### F001: 001-e2e-effect-workshop-tests (BL-052)

**E2E tests** (Playwright):
- Browse effect catalog and select an effect (~1 test)
- Configure parameters and verify filter preview updates in real time (~1 test)
- Apply effect to a clip and verify effect stack display (~1 test)
- Edit an applied effect and verify updated parameters persist (~1 test)
- Remove an applied effect with confirmation and verify removal (~1 test)
- WCAG AA accessibility: axe-core scan of all form components (~1 test)

**Accessibility tests**: All form inputs have labels, color contrast meets AA, keyboard navigation works through full workflow (~3 accessibility assertions within E2E tests).

### F002: 002-api-specification-update

No tests — documentation feature.

---

## Test Count Summary

| Theme | Feature | Rust Unit | Python Unit | Frontend Unit | Integration | E2E | Total |
|-------|---------|-----------|-------------|---------------|-------------|-----|-------|
| T01 | F001 audio | ~30 | — | — | 4 parity | — | ~34 |
| T01 | F002 transitions | ~24 | — | — | 3 parity | — | ~27 |
| T02 | F001 registry | — | ~15 | — | 3 parity | — | ~18 |
| T02 | F002 transition API | — | ~8 | — | 4 | — | ~12 |
| T03 | F001 catalog | — | — | ~14 | — | — | ~14 |
| T03 | F002 forms | — | — | ~13 | — | — | ~13 |
| T03 | F003 preview | — | — | ~8 | — | — | ~8 |
| T03 | F004 workflow | — | ~8 | ~12 | 3 | — | ~23 |
| T04 | F001 E2E | — | — | — | — | ~6 | ~6 |
| **Total** | | **~54** | **~31** | **~47** | **~17** | **~6** | **~155** |
