# Handoff: 002-dynamic-parameter-forms → 003-live-filter-preview

## What Was Built

- `effectFormStore` — Zustand store holding `parameters`, `validationErrors`, `schema`, and `isDirty`
- `EffectParameterForm` — Schema-driven component rendering input widgets per JSON schema property
- `EffectsPage` integration — Automatically sets schema in store when an effect is selected from catalog

## Key Integration Points

### For Live Filter Preview (BL-050)

The `effectFormStore` exposes the current parameter values at `useEffectFormStore((s) => s.parameters)`. Subscribe to this to trigger filter string regeneration as parameters change. The `isDirty` flag indicates whether the user has modified any default values.

### For Backend Validation

Call `useEffectFormStore.getState().setValidationErrors(errors)` with a `Record<string, string>` mapping field names to error messages. These render inline next to the corresponding form field.

### Store Shape

```typescript
{
  parameters: Record<string, unknown>   // Current form values
  validationErrors: Record<string, string>  // Per-field error messages
  schema: ParameterSchema | null        // Active JSON schema
  isDirty: boolean                      // True after first user edit
}
```

## Known Limitations

- No client-side range validation (only backend validation errors are displayed inline; the HTML `min`/`max` attributes provide native browser enforcement)
- `FR-004 AC1` notes parameter changes propagate to preview component — the store is ready but the preview component (BL-050) needs to consume it
