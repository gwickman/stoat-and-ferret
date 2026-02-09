## Context

React applications need state management for cross-component data sharing. Options range from heavyweight solutions (Redux) to lightweight alternatives (Zustand, Jotai, Context API).

## Learning

Use multiple focused Zustand stores scoped to feature domains rather than a single monolithic store or a heavier state management solution. Each store handles one concern with clear boundaries. Combined with FIFO eviction policies for unbounded data (like event logs), this keeps memory usage predictable and state management testable.

## Evidence

- v005 Theme 03: Three Zustand stores created — `activityStore` (50-entry FIFO eviction), `libraryStore` (filters, pagination), `projectStore` (selection, modal state)
- Each store was independently testable and easy to reason about
- 85 Vitest tests passed with clean separation of concerns
- No store-related bugs or complexity issues across four GUI features
- Theme retrospective noted Zustand kept implementation "lightweight and testable without the boilerplate of heavier alternatives"

## Application

- React applications with multiple feature domains needing shared state
- Prefer one store per feature/domain (library, projects, activity) over a single global store
- Add eviction policies (FIFO, LRU) for stores that accumulate data over time (event logs, notifications)
- Keep stores focused: if a store grows beyond ~5 state fields, consider splitting