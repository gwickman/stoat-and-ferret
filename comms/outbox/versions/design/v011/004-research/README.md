# Task 004: Research and Investigation — v011

Research covered all 5 mandatory backlog items across 2 themes (scan-and-clip-ux, developer-onboarding). Key findings: BL-075's backend clip CRUD endpoints are fully implemented and verified; BL-070 requires a backend directory listing endpoint because `showDirectoryPicker()` lacks Firefox/Safari support; BL-071 needs to document 10 Settings fields (config docs only cover 9); BL-076 has 4 concrete project-history examples ready for each check pattern; BL-019 is a straightforward AGENTS.md addition. All 6 referenced learnings verified as active and applicable.

## Research Questions

1. **BL-075**: Do clip CRUD endpoints (POST/PATCH/DELETE) exist with expected signatures? What Pydantic models are used? What frontend form/modal/store patterns exist?
2. **BL-070**: What folder picker mechanism is viable for cross-browser support? Does a backend directory listing API exist?
3. **BL-071**: What Settings fields exist? What env vars are referenced across the codebase? Is there existing documentation?
4. **BL-076**: What format does auto-dev expect for IMPACT_ASSESSMENT.md? What are the concrete historical examples for each check pattern?
5. **BL-019**: Where should the Windows section go in AGENTS.md? Is the `nul` gitignore entry already present?

## Findings Summary

| BL | Key Finding | Status |
|----|-------------|--------|
| BL-075 | All 3 write endpoints exist and are integration-tested. Frontend has zero callers of write endpoints. 7 Zustand stores provide clear composition pattern. Schema-driven EffectParameterForm provides form pattern precedent. | Ready for design |
| BL-070 | `showDirectoryPicker()` is Chromium-only (no Firefox/Safari). No backend directory listing endpoint exists. Recommend backend-assisted approach: new `GET /api/v1/filesystem/directories` endpoint. | Requires new API endpoint |
| BL-071 | Settings class has 10 fields with `STOAT_` prefix. Config docs only cover 9 (missing `log_backup_count`, `log_max_bytes`). No `.env.example` exists. `.env` already in `.gitignore`. | Ready for design |
| BL-076 | Auto-dev Task 003 consumes `docs/auto-dev/IMPACT_ASSESSMENT.md` when it exists. All 4 check patterns have concrete project-history examples with file paths and line references. | Ready for design |
| BL-019 | Best location: after Commands section (line 46) in AGENTS.md. `nul` already in `.gitignore` (line 219). Scope is documentation-only. | Ready for design |

## Learning Verification

| Learning | Status | Evidence |
|----------|--------|----------|
| LRN-031 | VERIFIED | Design-spec-to-success correlation pattern still active; v010 retrospective confirms continued relevance |
| LRN-032 | VERIFIED | `EffectParameterForm.tsx` uses JSON Schema for dynamic form generation; pattern active in gui/src/components/ |
| LRN-037 | VERIFIED | 7 independent Zustand stores in `gui/src/stores/` follow the pattern (projectStore, effectStackStore, libraryStore, etc.) |
| LRN-016 | VERIFIED | Clip CRUD endpoints confirmed at `src/stoat_ferret/api/routers/projects.py:245-412` with exact signatures matching BL-075 AC |
| LRN-029 | VERIFIED | Conscious simplicity principle still active; directly applicable to BL-070 browse button approach decision |
| LRN-030 | VERIFIED | Documentation-as-feature pattern still active; v011 has 3 documentation-focused backlog items |

## Unresolved Questions

- **BL-070 allowed_scan_roots integration**: If the browse endpoint exists, should it respect `allowed_scan_roots` security setting? Likely yes, but the exact filtering behavior needs design-time decision.
- **BL-075 clip label field**: `ClipCreate` and `ClipUpdate` have no `label` field despite BL-075 AC3 mentioning "label". The AC may need adjustment or a backend schema change.

## Recommendations

1. **BL-075**: Design should reference exact endpoint signatures from `projects.py`. Create a `clipStore.ts` following the independent Zustand store pattern. Note that `ClipCreate` has no `label` field — AC3 should reference actual fields (in_point, out_point, timeline_position).
2. **BL-070**: Use backend-assisted directory listing (new endpoint) rather than `showDirectoryPicker()`. Apply LRN-029: simple backend `os.listdir` approach now, document upgrade path to File System Access API when browser support broadens.
3. **BL-071**: Audit all 10 Settings fields from `settings.py` plus cross-check with `docs/setup/04_configuration.md`. The 2 missing fields (`log_backup_count`, `log_max_bytes`) must be included.
4. **BL-076**: Each check section should include: what to look for (grep pattern or design review question), why it matters (1 sentence), concrete example from project history (with file paths). Format for auto-dev Task 003 consumption.
5. **BL-019**: Place Windows section after Commands, before Type Stubs. Include correct (`/dev/null`) and incorrect (`nul`) examples with explanation.
