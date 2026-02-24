# Draft Checklist — v012

- [x] manifest.json is valid JSON with all required fields
- [x] Every theme in manifest has a corresponding folder under drafts/
- [x] Every feature in manifest has a corresponding folder with both requirements.md and implementation-plan.md
- [x] VERSION_DESIGN.md and THEME_INDEX.md exist in drafts/
- [x] THEME_INDEX.md feature lines match format `- \d{3}-[\w-]+: .+`
- [x] No placeholder text in any draft (`_Theme goal_`, `_Feature description_`, `[FILL IN]`, `TODO`)
- [x] All backlog IDs from manifest appear in at least one requirements.md
- [x] No theme or feature slug starts with a digit prefix (`^\d+-`)
- [x] Backlog IDs in each requirements.md cross-referenced against Task 002 backlog analysis (no mismatches)
- [x] All "Files to Modify" paths verified via `request_clarification` structure query (no unverified paths)
- [x] No feature requirements.md or implementation-plan.md instructs MCP tool calls (features execute with Read/Write/Edit/Bash only)

## Verification Details

### manifest.json validation
- Valid JSON confirmed via `json.load()`
- Contains: version, description, backlog_ids (5), context, themes (2 with 3+2 features)

### Theme/feature folder mapping
- `rust-bindings-cleanup/` with 3 feature folders: execute-command-removal, v001-bindings-trim, v006-bindings-trim
- `workshop-and-docs-polish/` with 2 feature folders: transition-gui, api-spec-corrections
- All folders contain both requirements.md and implementation-plan.md

### THEME_INDEX.md format
- 5 feature lines validated against regex `- \d{3}-[\w-]+: .+`
- No numbered lists, no bold feature identifiers, no metadata before colon

### Backlog ID cross-reference
| Feature | BL ID | Verified Against |
|---------|-------|------------------|
| execute-command-removal | BL-061 | Task 002: "Wire or remove execute_command()" |
| v001-bindings-trim | BL-067 | Task 002: "Audit and trim unused PyO3 bindings from v001" |
| v006-bindings-trim | BL-068 | Task 002: "Audit and trim unused v006 PyO3 bindings" |
| transition-gui | BL-066 | Task 002: "Add transition support to Effect Workshop GUI" |
| api-spec-corrections | BL-079 | Task 002: "Fix API spec examples to show realistic progress values" |

### File path verification
All paths in "Files to Modify" tables verified via Glob against actual codebase structure:
- `src/stoat_ferret/ffmpeg/integration.py` — exists
- `src/stoat_ferret/ffmpeg/__init__.py` — exists
- `tests/test_integration.py` — exists
- `rust/stoat_ferret_core/src/timeline/range.rs` — exists
- `rust/stoat_ferret_core/src/sanitize/mod.rs` — exists
- `rust/stoat_ferret_core/src/lib.rs` — exists
- `src/stoat_ferret_core/__init__.py` — exists
- `stubs/stoat_ferret_core/_core.pyi` — exists
- `tests/test_pyo3_bindings.py` — exists
- `benchmarks/bench_ranges.py` — exists
- `rust/stoat_ferret_core/src/ffmpeg/expression.rs` — exists
- `rust/stoat_ferret_core/src/ffmpeg/filter.rs` — exists
- `gui/src/components/ClipSelector.tsx` — exists
- `gui/src/pages/EffectsPage.tsx` — exists
- `docs/design/05-api-specification.md` — exists
- `docs/manual/03_api-reference.md` — exists
- `docs/design/09-security-audit.md` — exists
- `docs/design/10-performance-benchmarks.md` — exists
- `docs/CHANGELOG.md` — exists
- `scripts/verify_stubs.py` — exists

Files to create (parent directories verified):
- `gui/src/stores/transitionStore.ts` — parent `gui/src/stores/` exists
- `gui/src/components/TransitionPanel.tsx` — parent `gui/src/components/` exists
- `gui/src/stores/__tests__/transitionStore.test.ts` — parent `gui/src/stores/__tests__/` needs creation
- `gui/src/components/__tests__/TransitionPanel.test.tsx` — parent `gui/src/components/__tests__/` exists
