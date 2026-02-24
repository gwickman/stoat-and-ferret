# Risk Assessment: v011

## Risk: BL-075 `label` field mismatch between AC and schema

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Searched all clip-related schemas (Pydantic, SQLAlchemy, Alembic migration, Rust core) for any `label` field. Searched backlog and exploration documents for "label" references in clip context.
- **Finding**: No `label` field exists anywhere in the clip data model — not in `ClipCreate`, `ClipUpdate`, `ClipResponse` (schemas/clip.py), not in the `Clip` database model (db/models.py), not in the Alembic migration (39896ab3d0b7), and not in the Rust `Clip` struct (clip/mod.rs). The only reference is in BL-075 AC3 text: "pre-populated with current clip properties (in/out points, label)". This is an AC drafting error referencing a field that was never implemented.
- **Resolution**: Design correctly drops `label` from the clip form. AC3 should be interpreted as "pre-populated with current clip properties (in/out points, timeline_position)". No design change needed — Task 005 already handles this correctly.
- **Affected themes/features**: Theme 1 / 002-clip-crud-controls

## Risk: Directory listing security — path traversal

- **Original severity**: high
- **Category**: Investigate now
- **Investigation**: Read the `validate_scan_path()` function in `src/stoat_ferret/api/services/scan.py:29-51` and the security test suite in `tests/test_security/test_path_validation.py`.
- **Finding**: The existing validation is robust. `validate_scan_path()` uses `pathlib.Path.resolve()` (not `os.path.realpath()` — the Task 005 assumption was slightly wrong on the API but functionally equivalent). `Path.resolve()` normalizes `../` sequences, resolves symlinks, and converts to absolute paths. The function then uses `Path.relative_to()` for containment checks. Test coverage includes: path traversal via `../` (lines 59-67), backslash traversal `..\..` (lines 68-74), symlink resolution (lines 76-88), and API integration returning 403 (lines 91-146).
- **Resolution**: The new directory listing endpoint must import and call `validate_scan_path()` from `src/stoat_ferret/api/services/scan.py` — the same function the scan endpoint uses. No new security code needed. Update design note: use `Path.resolve()` not `os.path.realpath()` to match existing codebase convention.
- **Affected themes/features**: Theme 1 / 001-browse-directory

## Risk: BL-075 scope creep — source video selection UX

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Searched frontend for existing dropdown/select patterns and video data access. Found 3 existing `<select>` elements (SortControls.tsx, EffectCatalog.tsx, EffectParameterForm.tsx) and a `useVideos` hook with `GET /api/v1/videos` support. Also found `ProjectDetails.tsx` already fetches clips and displays them in a table.
- **Finding**: The codebase has established `<select>` dropdown patterns with consistent Tailwind styling (`rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white`). The `useVideos` hook already provides paginated video listing via `GET /api/v1/videos?limit={limit}&offset={offset}`. A simple `<select>` dropdown populated from the library videos list is straightforward to implement using existing patterns. For v011 scope, a basic dropdown is sufficient — the library is unlikely to exceed hundreds of videos in typical use.
- **Resolution**: Use a simple `<select>` dropdown for source video selection, styled with the existing Tailwind pattern. Populate from `useVideos` hook. No scope creep — this is a standard pattern already used elsewhere. Add note: if library exceeds ~100 videos, a searchable dropdown would be needed (future backlog item).
- **Affected themes/features**: Theme 1 / 002-clip-crud-controls

## Risk: BL-070 UX when `allowed_scan_roots` is empty

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Read the Settings class definition (`settings.py:89-93`) and `validate_scan_path()` function (`scan.py:29-51`). Also read the dedicated test (`test_path_validation.py:25-27`) and the learning document LRN-017.
- **Finding**: Conclusively resolved. The Settings field description states "Empty list allows all directories." The `validate_scan_path()` function returns `None` immediately when `allowed_roots` is empty (line 39-40), meaning any path is valid. This is tested explicitly (`test_empty_allowlist_permits_all`). LRN-017 documents this as a deliberate backwards-compatibility decision.
- **Resolution**: When `allowed_scan_roots` is empty, the directory browser should show filesystem contents starting from a sensible default (e.g., user home directory or `/`). The browse feature is fully functional with an empty allowlist. Add a note in the implementation plan: the initial browse path should default to something useful (not `/` on Unix which shows everything). Consider using the first `allowed_scan_roots` entry as the starting path when configured, or a platform-appropriate default.
- **Affected themes/features**: Theme 1 / 001-browse-directory

## Risk: Clip CRUD refresh race condition

- **Original severity**: low
- **Category**: Accept with mitigation
- **Investigation**: Analyzed all 7 Zustand stores in `gui/src/stores/`. No store implements AbortController, request deduplication, or optimistic updates. The `effectStackStore` (closest pattern) uses sequential `await` in mutation handlers — `removeEffect()` awaits `fetchEffects()` after deletion.
- **Finding**: No explicit race condition protection exists in any store. However, the pattern of sequential await (delete → then fetch) means each mutation completes before the next starts in normal usage. Rapid clicking is mitigated by UI loading states (`isLoading` boolean disabling buttons). True race conditions require near-simultaneous operations from different sources, which is unlikely in a single-user GUI.
- **Resolution**: Accept this risk for v011 with mitigation: the new `clipStore` should follow the existing pattern (sequential await, `isLoading` guard that disables action buttons during operations). This matches the established codebase convention. A more robust solution (AbortController, optimistic updates) can be added later if user feedback indicates issues.
- **Affected themes/features**: Theme 1 / 002-clip-crud-controls

## Risk: IMPACT_ASSESSMENT.md format not machine-parseable

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Read the Task 003 impact assessment prompt (`docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/003-impact-assessment.md`). Analyzed what format the consuming agent expects.
- **Finding**: The Task 003 prompt reads `docs/auto-dev/IMPACT_ASSESSMENT.md` "if it exists" and "executes each check category defined there." If the file doesn't exist, the agent documents "No project-specific impact checks configured" and continues. There is no formal schema — the agent reads markdown and interprets check sections. The format is consumed by a Claude Code agent which can handle reasonable markdown structures. The file's absence is explicitly handled as a graceful skip.
- **Resolution**: The recommended format (check name heading + "What to look for" / "Why it matters" / "Concrete example" subsections) is appropriate. The Claude Code agent consuming this file will interpret markdown headings as check categories. No format change needed from Task 005's design.
- **Affected themes/features**: Theme 2 / 003-impact-assessment

## Risk: Theme 2 feature 003 dependency on feature 001

- **Original severity**: low
- **Category**: Accept with mitigation
- **Investigation**: None needed — this was already identified and addressed in the execution order.
- **Finding**: The dependency is correctly captured in the logical design's execution order: 001-env-example precedes 003-impact-assessment within Theme 2.
- **Resolution**: No change. The execution order already handles this. The dependency is explicit in the design.
- **Affected themes/features**: Theme 2 / 001-env-example, 003-impact-assessment
