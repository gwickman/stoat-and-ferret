# Phase 6: GUI Integration

## Component Architecture

### New Components

| Component | File | Purpose |
|-----------|------|---------|
| `WorkspaceLayout` | `src/gui/src/components/workspace/WorkspaceLayout.tsx` | Root layout with resizable panels via `react-resizable-panels` |
| `WorkspacePresetSelector` | `src/gui/src/components/workspace/WorkspacePresetSelector.tsx` | Dropdown to switch between edit/review/render presets |
| `PanelVisibilityToggle` | `src/gui/src/components/workspace/PanelVisibilityToggle.tsx` | Toggle buttons for each panel's visibility |
| `SettingsPanel` | `src/gui/src/components/settings/SettingsPanel.tsx` | Theme, keyboard shortcuts, preferences |
| `ThemeSelector` | `src/gui/src/components/settings/ThemeSelector.tsx` | Light/dark/system theme picker |
| `KeyboardShortcutOverlay` | `src/gui/src/components/settings/KeyboardShortcutOverlay.tsx` | Modal overlay listing all shortcuts (triggered by `?` key) |
| `ShortcutEditor` | `src/gui/src/components/settings/ShortcutEditor.tsx` | Rebind keyboard shortcuts |
| `AccessibilityWrapper` | `src/gui/src/components/a11y/AccessibilityWrapper.tsx` | Focus management, skip links, ARIA live regions |
| `BatchPanel` | `src/gui/src/components/batch/BatchPanel.tsx` | Batch job submission and monitoring (API-only in Phase 5) |
| `BatchJobList` | `src/gui/src/components/batch/BatchJobList.tsx` | List of batch jobs with progress |

### Modified Components

| Component | Change | Milestone |
|-----------|--------|-----------|
| `Shell.tsx` | Replace fixed layout with `WorkspaceLayout`; add preset selector to header | M6.6 |
| `App.tsx` | Wrap with `AccessibilityWrapper`; add skip navigation links | M6.9 |
| `RenderPage.tsx` | Embed `BatchPanel` as tab alongside existing render queue | M6.6 |
| `DashboardPage.tsx` | Add version info card from `/api/v1/version` | M6.2 |
| `LibraryPage.tsx` | WCAG AA: focus indicators, ARIA labels on grid items | M6.9 |
| `TimelinePage.tsx` | WCAG AA: keyboard navigation for clip selection, ARIA roles | M6.9 |

## Store Architecture

### New Stores

| Store | File | State | Actions |
|-------|------|-------|---------|
| `workspaceStore` | `src/gui/src/stores/workspaceStore.ts` | `layout`, `preset`, `panelVisibility` | `setPreset()`, `togglePanel()`, `resizePanel()`, `resetLayout()` |
| `settingsStore` | `src/gui/src/stores/settingsStore.ts` | `theme`, `shortcuts`, `preferences` | `setTheme()`, `updateShortcut()`, `resetDefaults()` |
| `batchStore` | `src/gui/src/stores/batchStore.ts` | `batches`, `activeBatchId`, `batchProgress` | `submitBatch()`, `cancelBatch()`, `refreshBatches()` |

### Modified Stores

| Store | Change |
|-------|--------|
| `activityStore` | Add version info from `/api/v1/version` response |
| `renderStore` | Add batch-related state delegation to `batchStore` |

## Hooks

| Hook | Purpose |
|------|---------|
| `useWorkspace()` | Access workspace layout state and actions |
| `useSettings()` | Access theme, shortcuts, and preferences |
| `useKeyboardShortcuts()` | Register and handle keyboard shortcuts globally |
| `useBatchJobs()` | Poll or WebSocket-subscribe to batch job progress |
| `useFocusTrap(ref)` | Trap focus within modals for accessibility |
| `useAnnounce()` | Announce state changes to screen readers via ARIA live region |

## Workspace Layout Presets

| Preset | Panels Visible | Layout |
|--------|---------------|--------|
| **Edit** | Library, Timeline, Preview, Effects | 3-column: Library (20%) \| Timeline+Effects (50%) \| Preview (30%) |
| **Review** | Preview, Timeline | 2-column: Preview (60%) \| Timeline (40%) |
| **Render** | Render Queue, Batch, Preview | 3-column: Queue (30%) \| Batch (30%) \| Preview (40%) |

Layouts persist in `localStorage` under `stoat-workspace-layout`. Custom panel sizes are saved when the user resizes.

## Keyboard Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `?` | Open keyboard shortcut overlay | Global |
| `Ctrl+1/2/3` | Switch to Edit/Review/Render preset | Global |
| `Ctrl+,` | Open settings panel | Global |
| `Ctrl+B` | Toggle batch panel | Render page |
| `Escape` | Close overlay/modal, exit Theater Mode | Global |
| `Tab` / `Shift+Tab` | Navigate between panels | Global (a11y) |

## Accessibility (WCAG AA)

### Focus Management
- Skip-to-content link at top of page
- Focus trap in all modals and overlays
- Visible focus indicators on all interactive elements (2px solid outline)
- Focus restored to trigger element when modal closes

### ARIA
- `role="main"` on primary content area
- `aria-label` on all panels and navigation landmarks
- `aria-live="polite"` region for job status announcements
- `aria-expanded` on collapsible sections

### Color Contrast
- All text meets 4.5:1 contrast ratio (AA standard)
- Status indicators use both colour and icon (not colour alone)
- Theme selector respects `prefers-color-scheme` system preference

## Features Summary

| Feature | Components | Store | Milestone |
|---------|-----------|-------|-----------|
| Workspace layout | WorkspaceLayout, PresetSelector, PanelToggle | workspaceStore | M6.6 |
| Settings | SettingsPanel, ThemeSelector, ShortcutOverlay, ShortcutEditor | settingsStore | M6.6 |
| Batch GUI | BatchPanel, BatchJobList | batchStore | M6.6 |
| Accessibility | AccessibilityWrapper, focus management, ARIA | — | M6.9 |
| E2E tests | Playwright test files | — | M6.9 |
