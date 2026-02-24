# Investigation Log: v011

## 1. Label Field Investigation

**Query**: Search all clip schemas, models, database migrations, and Rust types for `label` field.

**Method**: Codebase search across Python schemas, SQLAlchemy models, Alembic migrations, Rust structs, and backlog documents.

**Files examined**:
- `src/stoat_ferret/api/schemas/clip.py` — ClipCreate (lines 11-17), ClipUpdate (lines 20-25), ClipResponse (lines 28-41): no `label` field
- `src/stoat_ferret/db/models.py` (lines 59-108): Clip dataclass has no `label` field
- `alembic/versions/39896ab3d0b7_add_clips_table.py` (lines 23-32): no `label` column
- `rust/stoat_ferret_core/src/clip/mod.rs` (lines 63-76): Rust Clip struct has no `label` field
- `docs/auto-dev/BACKLOG.md` (line 130): BL-075 AC3 mentions "label" in acceptance criteria text

**Conclusion**: `label` exists only as a word in the BL-075 AC text. It was never implemented in any data model. AC drafting error.

---

## 2. Path Traversal Security Investigation

**Query**: Review `allowed_scan_roots` validation for path traversal resistance.

**Method**: Read validation function, settings definition, and security test suite.

**Files examined**:
- `src/stoat_ferret/api/services/scan.py:29-51` — `validate_scan_path()` uses `Path.resolve()` + `relative_to()`
- `src/stoat_ferret/api/routers/videos.py:194-200` — scan endpoint calls validation
- `src/stoat_ferret/api/settings.py:89-93` — `allowed_scan_roots: list[str]`, default empty
- `tests/test_security/test_path_validation.py` — 8+ test cases including traversal, backslash, symlinks

**Conclusion**: Security validation is robust. Uses `Path.resolve()` (not `os.path.realpath()` as Task 005 assumed). Three layers: path normalization, containment check, ValueError handling. Well-tested.

---

## 3. Video Selection UX Investigation

**Query**: Find existing dropdown/select patterns and video data access in frontend.

**Method**: Codebase search for `<select>` elements, video hooks, and component patterns.

**Files examined**:
- `gui/src/components/SortControls.tsx` — `<select>` with Tailwind styling
- `gui/src/components/EffectCatalog.tsx` (lines 154-168) — `<select>` for category filtering
- `gui/src/components/EffectParameterForm.tsx` (lines 110-154) — `<select>` for enum parameters
- `gui/src/hooks/useVideos.ts` — provides `GET /api/v1/videos` with pagination
- `gui/src/components/ProjectDetails.tsx` — fetches and displays clips in table

**Conclusion**: Three established `<select>` patterns with consistent styling. `useVideos` hook provides video listing. Simple dropdown is viable and matches codebase conventions.

---

## 4. Empty Allowed Scan Roots Investigation

**Query**: Determine behavior when `allowed_scan_roots` is empty.

**Method**: Read settings definition, validation function logic, and test coverage.

**Files examined**:
- `src/stoat_ferret/api/settings.py:89-93` — description: "Empty list allows all directories"
- `src/stoat_ferret/api/services/scan.py:39-40` — `if not allowed_roots: return None`
- `tests/test_security/test_path_validation.py:25-27` — `test_empty_allowlist_permits_all`
- `docs/auto-dev/LEARNINGS/LRN-017` — documents empty=unrestricted as deliberate

**Conclusion**: Definitively resolved. Empty list = all directories allowed. Documented, tested, and intentional per LRN-017.

---

## 5. Zustand Async Pattern Investigation

**Query**: Analyze race condition handling in existing Zustand stores.

**Method**: Read all 7 stores, focusing on async mutations and state management.

**Files examined**:
- `gui/src/stores/effectStackStore.ts` (86 lines) — async fetchEffects, removeEffect with sequential await
- `gui/src/stores/projectStore.ts` (28 lines) — UI state only
- `gui/src/stores/effectCatalogStore.ts` (29 lines) — UI state only
- `gui/src/stores/effectFormStore.ts` (81 lines) — form state, isDirty
- `gui/src/stores/effectPreviewStore.ts` (27 lines) — loading/error state
- `gui/src/stores/libraryStore.ts` (29 lines) — pagination state
- `gui/src/stores/activityStore.ts` (28 lines) — append-only log, max 50

**Conclusion**: No explicit race condition protection (no AbortController, no deduplication). Pattern relies on sequential await + isLoading guards. Sufficient for single-user GUI.

---

## 6. IMPACT_ASSESSMENT.md Format Investigation

**Query**: Check what format Task 003 expects for project-specific impact checks.

**Method**: Read the Task 003 prompt document.

**File examined**:
- `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/003-impact-assessment.md`

**Conclusion**: No formal schema. Agent reads markdown, interprets headings as check categories. Graceful skip when file absent. Recommended format (check name + what/why/example) is appropriate.

---

## 7. Persistence Coherence Check

**Query**: Check if Task 004 produced a `persistence-analysis.md`.

**Method**: Glob search for `004-*/persistence-analysis.md`.

**Result**: No file found. v011 introduces no new persistent state — features are frontend UI controls (clip CRUD wiring existing endpoints), documentation (.env.example, AGENTS.md, IMPACT_ASSESSMENT.md), and a new API endpoint (directory listing) that is stateless. No persistence concerns apply.
