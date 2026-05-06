# Effect Naming Audit: `effect_name` vs `effect_type`

**Backlog item:** BL-348  
**Audit date:** 2026-05-06  
**Version:** v060  
**Status:** Complete — recommendation: standardize to `effect_type`

---

## 1. Audit Methodology

Grep search across all source, test, documentation, and GUI files:

```bash
grep -rn "effect_name" src/ tests/ docs/ gui/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md"
grep -rn "effect_type" src/ tests/ docs/ gui/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md"
```

**Results:**
- `effect_type`: 280 occurrences
- `effect_name`: 21 occurrences

---

## 2. Full Occurrence List

### 2.1 `effect_name` Occurrences (21 total)

#### src/ (4 occurrences)

| File | Line | Context |
|------|------|---------|
| `src/stoat_ferret/api/schemas/effect.py` | 101 | `effect_name: str` — field on `EffectThumbnailRequest` |
| `src/stoat_ferret/api/routers/effects.py` | 245 | `registry.get(request.effect_name)` — thumbnail endpoint |
| `src/stoat_ferret/api/routers/effects.py` | 251 | `f"Unknown effect type: {request.effect_name}"` — error message |
| `src/stoat_ferret/api/routers/effects.py` | 267 | `registry.validate(request.effect_name, ...)` — thumbnail endpoint |

#### tests/ (8 occurrences)

| File | Line | Context |
|------|------|---------|
| `tests/smoke/test_effects.py` | 266 | `"effect_name": "text_overlay"` — thumbnail payload |
| `tests/smoke/test_effects.py` | 285 | `"effect_name": "nonexistent_effect"` — thumbnail 400 test |
| `tests/test_api/test_effects.py` | 1641 | `"effect_name": "nonexistent_effect"` — thumbnail 400 test |
| `tests/test_api/test_effects.py` | 1657 | `"effect_name": "text_overlay"` — thumbnail missing video test |
| `tests/test_api/test_effects.py` | 1676 | `"effect_name": "speed_control"` — thumbnail invalid params test |
| `tests/test_api/test_effects.py` | 1721 | `"effect_name": "text_overlay"` — thumbnail 500 test |
| `tests/test_api/test_effects.py` | 1770 | `"effect_name": "text_overlay"` — thumbnail success test |
| `tests/test_api/test_effects.py` | 1821 | `"effect_name": "text_overlay"` — thumbnail command verification test |

#### gui/ (2 occurrences)

| File | Line | Context |
|------|------|---------|
| `gui/src/generated/api-types.ts` | 2805 | `effect_name: string` — generated OpenAPI type for thumbnail request |
| `gui/src/hooks/useEffectPreview.ts` | 110 | `effect_name: selectedEffect` — thumbnail POST body |

#### docs/ (7 occurrences)

| File | Line | Context |
|------|------|---------|
| `docs/C4-Documentation/c4-code-gui-generated.md` | 124 | `effect_name: string` — documents thumbnail preview field |
| `docs/C4-Documentation/c4-code-stoat-ferret-api-schemas.md` | 138 | `Fields: effect_name, video_path, parameters` — documents `EffectThumbnailRequest` |
| `docs/design/Phase 06 Design/02-rust-core-design.md` | 93 | `pub fn get_effect_parameter_schemas(effect_name: &str)` — Rust design doc function param |
| `docs/design/Phase 06 Design/06-test-strategy.md` | 29 | `effect_name in prop::sample::select(...)` — Rust proptest design |
| `docs/design/Phase 06 Design/06-test-strategy.md` | 31 | `let schemas = get_effect_parameter_schemas(&effect_name)` — Rust design |
| `docs/design/Phase 06 Design/06-test-strategy.md` | 32 | `assert!(..., "Effect {effect_name} has no parameters")` — Rust design |

### 2.2 `effect_type` Occurrences (280 total — selected representative sample)

#### src/ (≈35 occurrences)

| File | Lines | Context |
|------|-------|---------|
| `src/stoat_ferret/effects/registry.py` | 41, 45, 48–49, 51, 55, 60, 66, 70, 74–75, 83–85 | Core identifier for effect registration, retrieval, validation |
| `src/stoat_ferret/api/schemas/effect.py` | 38, 59, 66, 74, 81, 95 | Fields on `EffectResponse`, `EffectApplyRequest`, `EffectApplyResponse`, `EffectPreviewRequest`, `EffectPreviewResponse`, `EffectDeleteResponse` |
| `src/stoat_ferret/api/routers/effects.py` | 45, 127, 143, 177, 183, 187, 192, 216, 358, 364, 369, 395, 405, 411, 415, 481, 483, 489, 493, 517, 528, 533, 600, 606 | Prometheus label, discovery loop, all non-thumbnail endpoints |

#### tests/ (≈75 occurrences)

Used in `test_api/test_effects.py`, `smoke/test_effects.py`, `smoke/test_sample_project.py`, `test_blackbox/test_core_workflow.py`, `test_clip_model.py`, `test_effects/test_effect_definitions.py`, `test_effects/test_parameter_schema.py`.

#### gui/ (≈50 occurrences)

Used in `effectStackStore.ts`, `EffectCatalog.tsx`, `EffectStack.tsx`, `TransitionPanel.tsx`, `EffectsPage.tsx`, `useEffects.ts`, `useEffectPreview.ts` (line 62), all component tests, generated `api-types.ts` (7 occurrences for non-thumbnail schemas).

#### docs/ (≈120 occurrences)

Used in `docs/design/05-api-specification.md`, `docs/design/02-architecture.md`, `docs/manual/`, `docs/setup/`, `docs/C4-Documentation/`, `docs/CHANGELOG.md`.

---

## 3. Usage Pattern Analysis

### 3.1 What is `effect_type`?

`effect_type` is the **canonical string key** identifying an effect in the registry (e.g., `"text_overlay"`, `"speed_control"`, `"video_fade"`). It functions as a primary key: the registry stores and retrieves `EffectDefinition` objects by `effect_type`. It appears in:

- API request/response payloads (`effect_type: "text_overlay"`)
- Prometheus metric labels (`effect_applications_total{effect_type}`)
- Database JSON storage (`effects_json` column stores `{effect_type, parameters, filter_string}`)
- GUI state (`effectStackStore.ts` typed as `effect_type: string`)
- All published API documentation

### 3.2 What is `effect_name`?

`effect_name` refers to **the same concept** — the string identifier for an effect type. It appears exclusively on `EffectThumbnailRequest` (the `POST /api/v1/effects/preview/thumbnail` endpoint), the handler that uses it, and all code that calls that endpoint. There is no semantic distinction: `request.effect_name` is passed directly to `registry.get()` and `registry.validate()`, which take `effect_type` parameters.

The thumbnail endpoint was added in v060 (feat/v060/thumbnails, PR #400) and introduced `effect_name` as a divergent field name. It was not flagged during review.

### 3.3 Inconsistencies Identified

| Endpoint | Schema field | Consistent? |
|----------|-------------|-------------|
| `POST /effects` (apply) | `effect_type` | ✓ |
| `POST /effects/preview` (filter string) | `effect_type` | ✓ |
| `POST /effects/preview/thumbnail` | `effect_name` | ✗ — should be `effect_type` |
| `PUT /effects/{index}` (update params) | n/a (no type in body) | ✓ |
| `DELETE /effects/{index}` | `deleted_effect_type` | ✓ |

The only inconsistency is the thumbnail endpoint. The `EffectThumbnailRequest.effect_name` field is semantically identical to `EffectApplyRequest.effect_type`, `EffectPreviewRequest.effect_type`, and so on.

**Note on Phase 06 Design docs:** The three occurrences in `docs/design/Phase 06 Design/` are historical design documents for the Rust layer. The Rust function parameter `effect_name: &str` in those documents does not correspond to any current Python API field — it's a Rust-internal variable name in a design sketch. This is not an inconsistency in the production codebase.

---

## 4. Recommendation

**Standardize to `effect_type`.** Rename `EffectThumbnailRequest.effect_name` → `effect_type` and update all callsites.

### Rationale

1. **Dominant usage (280:21):** `effect_type` is used in 93% of all occurrences. Every schema class, every endpoint, the registry, Prometheus metrics, the database schema, and all documentation except the thumbnail endpoint uses `effect_type`.

2. **Semantic accuracy:** The field is a type/category identifier, not a human-readable display name. The `EffectResponse` schema already has a separate `name` field for the display name (e.g., `"Text Overlay"` vs `"text_overlay"`). Using `effect_name` for the identifier blurs this distinction.

3. **Registry contract:** `EffectRegistry.get(effect_type: str)` and `EffectRegistry.validate(effect_type: str, ...)` take `effect_type` as their parameter name. The thumbnail handler passes `request.effect_name` directly to these methods — the naming mismatch is visible at the call site.

4. **Minimal scope:** The fix is confined to one schema class, one endpoint handler (3 lines), one GUI hook (1 line), two test files (~8 assertions), generated files, and two C4 docs. No database migration required.

5. **No semantic tradeoff:** Keeping `effect_name` provides no benefit — it refers to the same concept, breaks consistency, and adds cognitive overhead for anyone working across endpoints.

**Alternative considered — keep as-is:** Acceptable only if the thumbnail endpoint stays permanently isolated with no cross-endpoint sharing of request types. Not recommended because it would require future developers to remember the inconsistency and creates API surface inconsistency for external integrators.

---

## 5. Implementation Impact Assessment

### Files Requiring Code Changes

| File | Change | Scope |
|------|--------|-------|
| `src/stoat_ferret/api/schemas/effect.py` | Rename `effect_name` → `effect_type` on `EffectThumbnailRequest` (line 101) | 1 line |
| `src/stoat_ferret/api/routers/effects.py` | Update `request.effect_name` → `request.effect_type` in thumbnail handler (lines 245, 251, 267) | 3 lines |
| `gui/src/hooks/useEffectPreview.ts` | Update thumbnail fetch body: `effect_name` → `effect_type` (line 110) | 1 line |
| `tests/smoke/test_effects.py` | Update 2 thumbnail test payloads (lines 266, 285) | 2 lines |
| `tests/test_api/test_effects.py` | Update 6 thumbnail test payloads (lines 1641, 1657, 1676, 1721, 1770, 1821) | 6 lines |

### Files Requiring Regeneration (no manual edits)

| File | Action |
|------|--------|
| `gui/openapi.json` | `uv run python -m scripts.export_openapi` after schema change |
| `gui/src/generated/api-types.ts` | Regenerate from updated OpenAPI spec |

### Files Requiring Documentation Updates

| File | Change | Scope |
|------|--------|-------|
| `docs/C4-Documentation/c4-code-gui-generated.md` | Line 124: `effect_name: string` → `effect_type: string` | 1 line |
| `docs/C4-Documentation/c4-code-stoat-ferret-api-schemas.md` | Line 138: update `EffectThumbnailRequest` fields description | 1 line |

### Files to Leave Unchanged

| File | Reason |
|------|--------|
| `docs/design/Phase 06 Design/02-rust-core-design.md` | Historical design doc; Rust function parameter, not Python API field |
| `docs/design/Phase 06 Design/06-test-strategy.md` | Historical Rust test strategy; Rust-local variable, not Python API field |

### Total Scope

- **Source code:** 5 lines across 2 Python files, 1 TypeScript file
- **Tests:** 8 lines across 2 test files
- **Docs:** 2 lines across 2 C4 doc files
- **Generated:** 2 files (openapi.json, api-types.ts) regenerated automatically
- **Risk:** Low — API breaking change for callers of `POST /api/v1/effects/preview/thumbnail`, but this endpoint was added in v060 and is not yet in a stable release

### API Breaking Change Note

Renaming `effect_name` → `effect_type` in the thumbnail request body is a breaking API change for any client currently sending `effect_name`. Since the thumbnail endpoint was introduced in v060 (not yet released), the practical impact is zero external callers. The canonical deprecation approach (support both fields temporarily) is not necessary for this case.

---

## 6. Follow-on Backlog Item

A follow-on backlog item has been filed (see Section 7 of the completion report) to implement this standardization in v061+.

---

## 7. Appendix: Grep Evidence

```
effect_name count: 21
effect_type count: 280
```

All 21 `effect_name` occurrences trace back to one feature: the thumbnail preview endpoint introduced in v060. All 280 `effect_type` occurrences span the full codebase: core registry, all API schemas, all other endpoints, all tests, the GUI frontend, and all documentation.
