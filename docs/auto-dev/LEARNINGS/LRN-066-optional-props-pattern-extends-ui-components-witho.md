## Context

When a UI component needs new behavior for a new feature (e.g., pair-selection mode for transitions) but existing callers depend on the current behavior (e.g., single-selection mode for effects), the component must be extended without breaking backward compatibility.

## Learning

Add new behavior as optional props with sensible defaults that preserve existing behavior. All new props should be optional (undefined by default), and when absent, the component behaves exactly as before. This avoids forking the component into two variants and keeps the codebase DRY. The same pattern applies to reusing existing form components (e.g., parameter forms) across different feature contexts.

## Evidence

A clip selector component was extended with optional pair-mode props (`pairMode`, `selectedFromId`, `selectedToId`, `onSelectPair`). All existing callers continued to work unchanged because the new props defaulted to undefined. A parameter form component was reused for transition parameter rendering without modification. The result: a full new feature tab was delivered with only 4 new files by reusing existing components.

## Application

1. When extending a component for a new feature, add new props as optional with `?` / `undefined` defaults
2. Guard new behavior behind `if (newProp)` checks so existing callers see no change
3. Before creating a new component, check if an existing one can be reused with optional props
4. Write tests for both the original behavior (props absent) and the new behavior (props present)
5. Use color-coding or visual differentiation to distinguish modes when the same component serves multiple purposes