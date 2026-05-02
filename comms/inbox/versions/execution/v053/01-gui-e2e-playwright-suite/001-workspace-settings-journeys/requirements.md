# Feature 001: workspace-settings-journeys

## Goal

Verify workspace layout and settings persistence across page reloads via localStorage roundtrip testing (J601–J602). Ensure workspace presets, panel sizes, theme selection, and keyboard shortcut customizations persist in browser storage and restore correctly on reload.

## Background

**Backlog Item:** BL-297 (E2E Playwright tests for critical GUI workflows)

**User Context:** Users expect their workspace layout (panel sizes, preset selection) and settings (theme, keyboard shortcuts) to persist across browser sessions. This feature validates that the `stoat-workspace-layout`, `stoat-theme`, and `stoat-shortcuts` localStorage keys correctly store and restore application state.

**Prior Work:** v044 (BL-291–295) completed WorkspaceLayout, Presets, and Settings components; localStorage persistence logic implemented in Zustand stores. v052 completed accessibility enhancements. Feature 001 validates this persistence with E2E tests.

## Functional Requirements

**FR-001: Workspace Layout Persistence**
- Initialize with default "edit" preset (library 20%, timeline 35%, effects 15%, preview 30%)
- Switch to "review" preset (preview 60%, timeline 40%)
- Manually resize panels (e.g., effects to 25%)
- Reload the page
- Assert panel layout matches the custom configuration in `stoat-workspace-layout` localStorage key
- Verify JSON structure contains: `{preset, anchorPreset, panelSizes, panelVisibility, sizesByPreset}`

**FR-002: Preset Switch Persistence**
- Use keyboard shortcuts to switch presets (Ctrl+1 → edit, Ctrl+2 → review, Ctrl+3 → render)
- For each preset, verify localStorage `stoat-workspace-layout.preset` updates immediately
- Reload page after each preset switch
- Assert active preset matches stored value and panel layout matches canonical preset sizes

**FR-003: Theme Persistence**
- Toggle theme from "light" to "dark" and "system"
- Assert HTML element `data-theme` attribute updates immediately
- Reload page
- Assert theme setting persists in `stoat-theme` localStorage key
- Verify correct theme value ("light", "dark", or "system") restored on reload

**FR-004: Keyboard Shortcut Persistence**
- Open keyboard shortcut settings panel
- Rebind a shortcut (e.g., `workspace.preset.edit` from Ctrl+1 to Ctrl+Shift+1)
- Assert rebinding succeeds (not a reserved key, within constraints)
- Reload page
- Assert rebound shortcut persists in `stoat-shortcuts` localStorage key
- Verify new binding works after reload; old binding no longer active

## Non-Functional Requirements

**NFR-001: localStorage Performance**
- All persistence operations (write on change, read on reload) complete without perceptible latency
- localStorage access is synchronous in Zustand store; no async race conditions on reload

**NFR-002: Browser Compatibility**
- Persistence works on Chromium (tested in E2E CI job)
- localStorage is standard HTML5 feature; no polyfills required

**NFR-003: No Data Loss**
- Panel resize operations do not corrupt stored JSON
- Preset switches do not lose custom overrides in `sizesByPreset` map

## Framework Decisions

Per FRAMEWORK_CONTEXT.md:

**Frontend State Management (§3, Frontend):**
- Zustand stores are the canonical pattern for cross-component state (`workspaceStore`, `settingsStore`)
- localStorage serialization via `persist` middleware is the approved pattern for durability across sessions
- Features should not bypass Zustand stores or write directly to localStorage

**Testing Patterns (§3, Frontend, Testing):**
- Playwright for E2E validation of browser-level behavior (localStorage persistence, DOM updates)
- Element-level DOM assertions over implementation details (store internals)

**Accessibility in Settings:**
- Settings panel (theme, shortcuts) must include ARIA labels and keyboard navigation support
- Keyboard shortcut rebinding must not conflict with accessibility shortcuts (e.g., skip-links)

## Out of Scope

- Syncing workspace layout across browser tabs or devices
- Cloud-based backup or restore of settings
- Migration from older localStorage key formats (assume v044+ storage format)
- Keyboard shortcut conflict detection beyond reserved-keys validation (conflicts are user responsibility)

## Test Requirements

**Test Files:**
- Create `tests/e2e/workspace-layout.spec.ts` — localStorage roundtrip for workspace presets and panel sizes
- Create `tests/e2e/settings-persistence.spec.ts` — theme and shortcuts localStorage persistence
- Update `tests/e2e/workspace-routing.spec.ts` with regression assertions (verify layout doesn't break during routing)

**Test Strategy (per Task 006):**
- Use Playwright `clearBrowserCache()` or manual localStorage clear before each test (isolate storage state)
- Navigate through preset switches and manual resizes; assert localStorage updates via `page.evaluate()`
- Reload page using `page.reload()` and verify state restoration
- No database setup required (frontend-only testing)
- No mocking: real Zustand stores and localStorage

## Reference

See `C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret\comms\outbox\versions\design\v053\005-research\` for supporting evidence:
- localStorage key names and structure (findings Q5–Q9)
- Preset definitions (3 presets: edit, review, render with canonical sizes)
- Default keyboard shortcuts (Ctrl+1/2/3 for presets, Ctrl+, for settings)
- Theme application pattern (HTML `data-theme` attribute)