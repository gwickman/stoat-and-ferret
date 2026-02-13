# Draft Checklist: v006

- [x] manifest.json is valid JSON with all required fields
- [x] Every theme in manifest has a corresponding folder under drafts/
- [x] Every feature in manifest has a corresponding folder with both requirements.md and implementation-plan.md
- [x] VERSION_DESIGN.md and THEME_INDEX.md exist in drafts/
- [x] THEME_INDEX.md feature lines match format `- \d{3}-[\w-]+: .+`
- [x] No placeholder text in any draft (`_Theme goal_`, `_Feature description_`, `[FILL IN]`, `TODO`)
- [x] All backlog IDs from manifest appear in at least one requirements.md
- [x] No theme or feature slug starts with a digit prefix (`^\d+-`)
- [x] Backlog IDs in each requirements.md cross-referenced against Task 002 backlog analysis (no mismatches)
- [x] All "Files to Modify" paths verified via Glob structure query (no unverified paths)

## Backlog ID Cross-Reference Verification

| Backlog ID | requirements.md Location | Verified Against Task 002 |
|------------|-------------------------|---------------------------|
| BL-037 | expression-engine/requirements.md | Yes — "Implement FFmpeg filter expression engine in Rust" |
| BL-038 | graph-validation/requirements.md | Yes — "Implement filter graph validation" |
| BL-039 | filter-composition/requirements.md | Yes — "Build filter composition system" |
| BL-040 | drawtext-builder/requirements.md | Yes — "Implement drawtext filter builder" |
| BL-041 | speed-control/requirements.md | Yes — "Implement speed control filters" |
| BL-042 | effect-discovery/requirements.md | Yes — "Create effect discovery API endpoint" |
| BL-043 | clip-effect-model/requirements.md + text-overlay-apply/requirements.md | Yes — "Apply text overlay to clip API" (split into 2 features) |

## File Path Verification Summary

All "Files to Modify" paths verified against Glob output of the codebase:
- Rust source: 6 existing files confirmed
- Python source: 7 existing files confirmed
- Type stubs: 1 existing file confirmed
- Test files: 3 existing files confirmed
- All "Files to Create" parent directories exist in the codebase

## THEME_INDEX.md Format Verification

All feature lines match the required regex `- \d{3}-[\w-]+: .+`:
- `- 001-expression-engine: ...`
- `- 002-graph-validation: ...`
- `- 001-filter-composition: ...`
- `- 002-drawtext-builder: ...`
- `- 003-speed-control: ...`
- `- 001-effect-discovery: ...`
- `- 002-clip-effect-model: ...`
- `- 003-text-overlay-apply: ...`

## Slug Naming Verification

No theme or feature slug starts with a digit prefix:
- Theme slugs: `filter-expression-infrastructure`, `filter-builders-and-composition`, `effects-api-layer`
- Feature slugs: `expression-engine`, `graph-validation`, `filter-composition`, `drawtext-builder`, `speed-control`, `effect-discovery`, `clip-effect-model`, `text-overlay-apply`
