# Implementation Plan: effect-catalog-ui

## Overview

Build the EffectCatalog component for browsing and selecting available effects. Creates a grid/list view consuming the GET /effects endpoint, with search, category filter, and AI hint tooltips. Adds a new Zustand store, custom hook, and routing for the effects workshop.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `gui/src/components/EffectCatalog.tsx` | Grid/list view component with search/filter |
| Create | `gui/src/stores/effectCatalogStore.ts` | Catalog state: search, filter, selected effect |
| Create | `gui/src/hooks/useEffects.ts` | Fetch effects from GET /effects endpoint |
| Create | `gui/src/pages/EffectsPage.tsx` | Initial effects workshop page (shell) |
| Modify | `gui/src/App.tsx` | Add /gui/effects route |
| Modify | `gui/src/components/Navigation.tsx` | Add "Effects" tab to navigation |
| Create | `gui/src/components/__tests__/EffectCatalog.test.tsx` | Component tests |
| Create | `gui/src/hooks/__tests__/useEffects.test.ts` | Hook tests |

## Test Files

`gui/src/components/__tests__/EffectCatalog.test.tsx gui/src/hooks/__tests__/useEffects.test.ts`

## Implementation Stages

### Stage 1: Store, hook, and routing

1. Create `effectCatalogStore.ts` following existing store pattern (projectStore.ts as template)
   - State: searchQuery, selectedCategory, selectedEffect, viewMode (grid/list)
   - Actions: setSearchQuery, setSelectedCategory, selectEffect, toggleViewMode
2. Create `useEffects.ts` hook following `useProjects.ts` pattern
   - Fetches from GET /effects
   - Returns effects, loading, error, refetch
3. Create shell `EffectsPage.tsx`
4. Add route in `App.tsx`: `<Route path="effects" element={<EffectsPage />} />`
5. Add "Effects" tab in `Navigation.tsx`

**Verification:**
```bash
cd gui && npx vitest run src/hooks/__tests__/useEffects.test.ts
```

### Stage 2: EffectCatalog component

1. Create `EffectCatalog.tsx` with grid layout (default) and list view toggle
2. Effect cards show name, description, category badge
3. AI hint tooltips using title/aria-describedby for accessibility
4. Search input filters effects by name (client-side)
5. Category filter dropdown/tabs
6. Click handler calls `selectEffect()` from store
7. Connect to EffectsPage

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/EffectCatalog.test.tsx
```

### Stage 3: Full integration and test coverage

1. Write component tests: renders cards, grid/list toggle, search, filter, tooltip, click
2. Write store tests: search/filter state, selection
3. Verify responsive layout at different widths

**Verification:**
```bash
cd gui && npx vitest run
```

## Test Infrastructure Updates

- New test files: `EffectCatalog.test.tsx`, `useEffects.test.ts`
- Mock data: effect definitions matching registry output

## Quality Gates

```bash
cd gui && npx tsc -b && npx vitest run
```

## Risks

- API response format must match expected structure — verify against registry output. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat(gui): add effect catalog UI with search, filter, and AI hints
```