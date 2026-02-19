# Implementation Plan: live-filter-preview

## Overview

Build the FilterPreview component that shows the Rust-generated FFmpeg filter string in real time as users adjust parameters. Uses debounced API calls (300ms) to avoid excessive requests. Adds simple regex-based syntax highlighting for filter names and pad labels, and a copy-to-clipboard button.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `gui/src/components/FilterPreview.tsx` | Monospace filter string panel with syntax highlighting |
| Create | `gui/src/stores/effectPreviewStore.ts` | Filter string state, loading state |
| Create | `gui/src/hooks/useEffectPreview.ts` | Debounced preview API call hook |
| Modify | `gui/src/pages/EffectsPage.tsx` | Integrate preview panel below form |
| Create | `gui/src/components/__tests__/FilterPreview.test.tsx` | Component tests |
| Create | `gui/src/hooks/__tests__/useEffectPreview.test.ts` | Hook tests |

## Test Files

`gui/src/components/__tests__/FilterPreview.test.tsx gui/src/hooks/__tests__/useEffectPreview.test.ts`

## Implementation Stages

### Stage 1: Preview store and hook

1. Create `effectPreviewStore.ts`
   - State: filterString, isLoading, error
   - Actions: setFilterString, setLoading, setError
2. Create `useEffectPreview.ts` hook
   - Watches effectFormStore parameters for changes
   - Uses existing `useDebounce` hook (300ms) for debouncing
   - Makes API call to get preview filter string
   - Updates effectPreviewStore

**Verification:**
```bash
cd gui && npx vitest run src/hooks/__tests__/useEffectPreview.test.ts
```

### Stage 2: FilterPreview component

1. Create `FilterPreview.tsx` with monospace `<pre>` panel
2. Simple regex-based syntax highlighting:
   - Filter names (e.g., `volume`, `xfade`) in keyword color
   - Pad labels (e.g., `[0:v]`, `[out]`) in label color
   - Parameters in default color
3. Copy-to-clipboard button using `navigator.clipboard.writeText()`
4. Visual feedback on copy (icon change or tooltip)
5. Loading and error states

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/FilterPreview.test.tsx
```

### Stage 3: Integration

1. Add FilterPreview to EffectsPage below parameter form
2. Preview updates automatically when form parameters change
3. Verify debounce behavior end-to-end

**Verification:**
```bash
cd gui && npx vitest run
```

## Test Infrastructure Updates

- New test files: `FilterPreview.test.tsx`, `useEffectPreview.test.ts`
- Mock API responses for preview endpoint

## Quality Gates

```bash
cd gui && npx tsc -b && npx vitest run
```

## Risks

- Preview API endpoint must exist — verify it's created by T02. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat(gui): add live FFmpeg filter string preview with syntax highlighting
```