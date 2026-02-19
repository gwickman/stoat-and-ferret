# Implementation Plan: effect-builder-workflow

## Overview

Compose catalog, form, and preview into the full effect builder workflow. Add ClipSelector and EffectStack components for clip selection and effect management. Add backend CRUD endpoints (PATCH/DELETE) for editing and removing effects by array index. Create the EffectsPage as the composition root.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `gui/src/components/ClipSelector.tsx` | Clip selection component for target clip |
| Create | `gui/src/components/EffectStack.tsx` | Per-clip effect list with edit/remove actions |
| Create | `gui/src/stores/effectStackStore.ts` | Per-clip effect stack state, CRUD operations |
| Modify | `gui/src/pages/EffectsPage.tsx` | Compose all components into full workflow |
| Modify | `src/stoat_ferret/api/routers/effects.py` | Add PATCH/DELETE effect CRUD endpoints |
| Modify | `src/stoat_ferret/api/schemas/effect.py` | Add EffectUpdateRequest, EffectDeleteResponse models |
| Modify | `src/stoat_ferret/db/clip_repository.py` | Add effect update/delete methods if needed |
| Create | `gui/src/components/__tests__/ClipSelector.test.tsx` | Component tests |
| Create | `gui/src/components/__tests__/EffectStack.test.tsx` | Component tests |
| Modify | `tests/test_api/test_effects.py` | Add CRUD endpoint tests |

## Test Files

`gui/src/components/__tests__/ClipSelector.test.tsx gui/src/components/__tests__/EffectStack.test.tsx tests/test_api/test_effects.py`

## Implementation Stages

### Stage 1: Backend CRUD endpoints

1. Add Pydantic models: `EffectUpdateRequest` (parameters dict), effect CRUD response
2. Add `PATCH /projects/{project_id}/clips/{clip_id}/effects/{index}` — update effect at index
   - Validate index against effects array length (0-based)
   - Out-of-range returns 404
   - Regenerate filter string via registry dispatch
3. Add `DELETE /projects/{project_id}/clips/{clip_id}/effects/{index}` — remove effect at index
   - Validate index, pop from array, persist
4. Add Python tests for CRUD endpoints

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "crud or patch or delete"
```

### Stage 2: ClipSelector component

1. Create `ClipSelector.tsx` — renders clips from current project using projectStore
2. Each clip shows name/filename and timeline position
3. Selection handler updates effectStackStore with selected clip ID
4. Write component tests

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/ClipSelector.test.tsx
```

### Stage 3: EffectStack component

1. Create `effectStackStore.ts` — per-clip effect list from API, add/edit/remove operations
2. Create `EffectStack.tsx` — ordered list of effects for selected clip
3. Edit button: sets effectFormStore with existing parameters, switches to edit mode
4. Remove button: shows confirmation dialog, calls DELETE endpoint
5. Write component tests

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/EffectStack.test.tsx
```

### Stage 4: Full workflow composition

1. Update `EffectsPage.tsx` to compose: ClipSelector, EffectCatalog, EffectParameterForm, FilterPreview, EffectStack
2. Workflow: select clip → browse catalog → select effect → configure parameters → apply → see in stack
3. Add "Apply" button that calls POST effect endpoint and refreshes stack
4. Integrate edit/remove flows
5. Add placeholder text for visual preview: "Visual preview coming in a future version"
6. Write integration test for EffectsPage

**Verification:**
```bash
cd gui && npx vitest run
uv run pytest tests/test_api/test_effects.py -v
```

## Test Infrastructure Updates

- New test files: `ClipSelector.test.tsx`, `EffectStack.test.tsx`
- Extend `tests/test_api/test_effects.py` with CRUD tests
- May need test factory helpers for clip effects

## Quality Gates

```bash
cd gui && npx tsc -b && npx vitest run
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Effect CRUD uses array index — concurrent modifications could cause issues. Acceptable for single-user v007 scope. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`
- EffectsPage composition complexity — keep component boundaries clear

## Commit Message

```
feat: add effect builder workflow with clip selector, stack visualization, and CRUD
```