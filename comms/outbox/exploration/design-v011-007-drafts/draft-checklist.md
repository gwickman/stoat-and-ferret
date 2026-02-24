# Draft Checklist: v011

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
- [x] No feature requirements.md or implementation-plan.md instructs MCP tool calls (features execute with Read/Write/Edit/Bash only)

## Path Corrections Made During Verification

| Original Path | Corrected Path | Reason |
|---------------|----------------|--------|
| `src/stoat_ferret/main.py` | `src/stoat_ferret/api/app.py` | No `main.py` exists; app factory is in `api/app.py` |
| `tests/api/test_filesystem.py` | `tests/test_api/test_filesystem.py` | Test directory is `tests/test_api/` not `tests/api/` |
