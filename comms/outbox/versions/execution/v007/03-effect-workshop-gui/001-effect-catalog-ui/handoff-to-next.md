# Handoff: 001-effect-catalog-ui -> Next Feature

## What Was Built

- `EffectCatalog` component with grid/list view, search, category filter, AI tooltips
- `useEffectCatalogStore` Zustand store tracks: `searchQuery`, `selectedCategory`, `selectedEffect`, `viewMode`
- `useEffects` hook fetches from `GET /api/v1/effects`
- `deriveCategory()` maps `effect_type` -> `audio` | `video` | `transition`
- Route at `/effects`, tab in Navigation

## Key Integration Points

- **Selected effect**: `useEffectCatalogStore.getState().selectedEffect` contains the `effect_type` string of the currently selected effect. The next feature (parameter configuration form, BL-049) should consume this to show the appropriate form.
- **Effect data**: The `useEffects` hook returns the full `Effect` objects including `parameter_schema` and `ai_hints` which the parameter form will need for rendering dynamic inputs.
- **EffectsPage**: Currently just renders the catalog. The parameter form component should be added here, conditionally shown when `selectedEffect` is non-null.

## Patterns to Follow

- Zustand stores in `gui/src/stores/`
- Custom hooks in `gui/src/hooks/`
- Component tests mock hooks via `vi.mock()` and use `@testing-library/react`
- All interactive elements have `data-testid` attributes
