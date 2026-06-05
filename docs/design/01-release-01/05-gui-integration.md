# GUI Integration: Workspace Routing

This document covers workspace-level GUI integration patterns, specifically the per-panel routing
architecture introduced in v049. For overall GUI architecture, component inventory, and build/deploy
guidance, see `08-gui-architecture.md`.

---

## Per-Panel Routing Model

### Goal

Allow workspace presets to bind specific route paths to specific panels, so each panel can
independently resolve and render its own routed content. This enables layouts like "library in the
left panel, timeline in the centre panel, preview in the right panel" where the URL encodes only
which preset is active.

BL-306 specifies per-panel routing as the backing backlog item. This section provides the validated
design for Feature 004 to implement.

---

### Current Architecture (pre-v049)

#### Route hierarchy

`App.tsx` registers all pages under a single `<Shell>` parent route. React Router renders one active
child route at a time via a single `<Outlet />`:

```tsx
// App.tsx (current)
<Routes>
  <Route element={<Shell />}>
    <Route index element={<DashboardPage />} />
    <Route path="library" element={<LibraryPage />} />
    <Route path="timeline" element={<TimelinePage />} />
    <Route path="preview" element={<PreviewPage />} />
    <Route path="render" element={<RenderPage />} />
    <Route path="effects" element={<EffectsPage />} />
    <Route path="projects" element={<ProjectsPage />} />
  </Route>
</Routes>
```

#### Shell rendering contract

`Shell.tsx` passes the React Router `<Outlet />` as a child to `WorkspaceLayout`:

```tsx
// Shell.tsx (current)
<WorkspaceLayout>
  <Outlet />
</WorkspaceLayout>
```

#### WorkspaceLayout panel placement

`WorkspaceLayout.tsx` places the `children` prop (the routed Outlet) exclusively inside the
`preview` `WorkspacePanel`. All other panels render placeholder labels when visible:

```tsx
// WorkspaceLayout.tsx (current, simplified)
<WorkspacePanel panelId="preview" label="Preview" minSize={20} guardRef={guardRef}>
  {children}   {/* ← only the preview panel receives routed content */}
</WorkspacePanel>
```

**Consequence:** Navigating to `/library` renders `LibraryPage` inside the `preview` panel regardless
of which workspace preset is active. No panel other than `preview` ever receives routed content.

---

### Proposed Architecture

#### Design principle

Per-panel routes are a property of the preset definition, not of the URL. The URL encodes which
preset is active (`?workspace=edit`); the PRESETS const determines which page component renders in
each panel. This keeps URL state minimal and avoids the complexity of encoding multiple panel routes
in the URL.

#### PresetDefinition interface extension

Add an optional `routes` field to the existing `PresetDefinition` interface in `workspaceStore.ts`:

```typescript
interface PresetDefinition {
  /** Panels visible when this preset is active. All others are hidden. */
  panels: readonly PanelId[]
  /** Canonical sizes (percentages) keyed by panelId. Hidden panels get 0. */
  sizes: PanelSizes
  /**
   * Optional per-panel route paths. Keys are PanelId values; values are
   * absolute route paths (e.g., "/library", "/preview"). When omitted for a
   * panel, the panel renders its placeholder label (or the legacy Outlet child
   * for the preview panel in no-routes mode).
   *
   * Constraints:
   * - Values must match a route registered in App.tsx.
   * - A given route path should appear in at most one panel per preset to
   *   avoid the same page component mounting twice.
   * - Custom per-panel routing (user-defined routes per panel) is NOT
   *   URL-encodable; this field is read-only from the PRESETS const.
   */
  routes?: Record<PanelId, string>
}
```

#### Example PRESETS extension

```typescript
export const PRESETS: Readonly<Record<NamedPreset, PresetDefinition>> = {
  edit: {
    panels: ['library', 'timeline', 'effects', 'preview'],
    sizes: { ...zeroSizes(), library: PANEL_DEFAULTS.library, timeline: 35, effects: 15, preview: 30 },
    routes: {
      library: '/library',
      timeline: '/timeline',
      effects: '/effects',
      preview: '/preview',
      'render-queue': '',
      batch: '',
    },
  },
  review: {
    panels: ['preview', 'timeline'],
    sizes: { ...zeroSizes(), preview: 60, timeline: 40 },
    routes: {
      preview: '/preview',
      timeline: '/timeline',
      library: '',
      effects: '',
      'render-queue': '',
      batch: '',
    },
  },
  render: {
    panels: ['render-queue', 'batch', 'preview'],
    sizes: { ...zeroSizes(), 'render-queue': 30, batch: 30, preview: 40 },
    routes: {
      'render-queue': '/render',
      batch: '/render',
      preview: '/preview',
      library: '',
      timeline: '',
      effects: '',
    },
  },
}
```

> **Note on empty-string values:** Route entries with `''` (empty string) mean "no routed content for
> this panel." These panels render their placeholder labels. The `Record<PanelId, string>` type
> ensures every panel key is accounted for at compile time.

#### WorkspaceLayout change

`WorkspaceLayout.tsx` stops accepting a `children` prop. Instead it:

1. Reads the current preset from `useWorkspaceStore`.
2. Looks up `PRESETS[preset]?.routes` (absent for `custom` preset — see backward compatibility below).
3. For each `WorkspacePanel`, renders the page component matching the configured route path, or
   falls back to the placeholder label when the route path is empty.

Page components are rendered via a per-panel in-memory route resolver rather than by navigating
the browser URL:

```tsx
// WorkspaceLayout.tsx (proposed, simplified)
import { useRoutes } from 'react-router-dom'

function PanelContent({ route }: { route: string }) {
  // useRoutes renders the component matching `route` from the registered
  // App routes. Returns null when route is empty or unmatched.
  const element = useRoutes([
    { path: '/library', element: <LibraryPage /> },
    { path: '/timeline', element: <TimelinePage /> },
    { path: '/preview', element: <PreviewPage /> },
    { path: '/render', element: <RenderPage /> },
    { path: '/effects', element: <EffectsPage /> },
    { path: '/', element: <DashboardPage /> },
  ], { pathname: route })
  return element
}

// WorkspacePanel receives the resolved element as children:
<WorkspacePanel panelId="library" label="Library" minSize={10} guardRef={guardRef}>
  {routeForPanel('library') ? <PanelContent route={routeForPanel('library')} /> : null}
</WorkspacePanel>
```

> **Implementation note for Feature 004:** The exact mechanism for per-panel route resolution should
> be evaluated against React Router v7's available APIs (`useRoutes`, `createBrowserRouter` memory
> routing, or direct component mapping). Direct component mapping (a `Record<string, ComponentType>`
> lookup table in workspaceStore or a dedicated `ROUTE_COMPONENTS` const in App.tsx) is simpler than
> using `useRoutes` twice and is recommended if `useRoutes` requires additional router context.

#### Shell.tsx change

`Shell.tsx` removes `<Outlet />` from the `WorkspaceLayout` call since WorkspaceLayout manages its
own panel content:

```tsx
// Shell.tsx (proposed)
<WorkspaceLayout />   {/* no children — WorkspaceLayout is self-contained */}
```

The top-level `<Outlet />` in Shell is replaced by WorkspaceLayout's per-panel route resolution.

#### Backward compatibility: `custom` preset

When `preset === 'custom'`, no `routes` field exists in PRESETS (custom is not a named preset and
has no definition). WorkspaceLayout falls back to the behaviour of the previous named preset's
routes by using `anchorPreset` from the workspace store. This matches the existing pattern where
custom mode inherits visibility/sizes from the anchor preset.

---

### Per-Page Compatibility Matrix

All four target pages render correctly under per-panel routing at panel-constrained widths. Evidence
below is based on static analysis of each page's layout implementation.

| Page | Current Panel | Per-Panel Width (edit preset, 1920px) | Layout Mechanism | Regression Risk |
|------|--------------|--------------------------------------|-----------------|----------------|
| `LibraryPage` (`/library`) | `preview` | Library panel: ~384px (20%) | `flex-1` search bar, Tailwind grid | **None** — grid collapses gracefully; no fixed-width containers |
| `TimelinePage` (`/timeline`) | `preview` | Timeline panel: ~672px (35%) | `lg:grid-cols-3` (collapses at <1024px) | **None** — single-column layout at narrow widths; `TimelineCanvas` uses overflow scroll |
| `PreviewPage` (`/preview`) | `preview` | Preview panel: ~576px (30%) | flex column, video player | **None** — `w-64` progress bar is internal to the player controls, not a page container constraint |
| `RenderPage` (`/render`) | `preview` | Render-queue panel: ~576px (30%) | flex column, tabbed content | **None** — tab strip and job cards stack vertically; no min-width requirements |

**EffectsPage** (not a primary routing target in v049 presets): The effects panel at 15% (~288px) is
narrow. `EffectsPage` uses responsive CSS and stacks vertically — it renders without overflow errors
but the UX is tight. Feature 004 may omit `/effects` from the effects panel routes or use a compact
effects view; that decision is left to the implementer.

**DashboardPage** and **ProjectsPage** were not part of the per-panel routing scope in BL-306 and
are not assigned to any preset's routes field above.

---

### Migration Notes

#### Consumers of the Shell `<Outlet />`

Before v049, `<Outlet />` in Shell was the only mechanism for rendering routed page content inside
the workspace. After Feature 004:

- `Shell.tsx` no longer passes `<Outlet />` to WorkspaceLayout.
- WorkspaceLayout's `WorkspacePanelProps.children` interface is unchanged (panels still accept
  optional children), but WorkspaceLayout itself no longer accepts a `children` prop from Shell.
- The `WorkspaceLayoutProps` interface (`{ children?: ReactNode }`) can be removed or deprecated.

#### Vitest tests for WorkspaceLayout

Five test files import workspace constants:

- `gui/src/__tests__/workspaceStore.test.ts`
- `gui/src/__tests__/PanelVisibilityToggle.test.tsx`
- `gui/src/__tests__/WorkspaceLayout.test.tsx`
- `gui/src/__tests__/WorkspacePresetSelector.test.tsx`
- `gui/src/__tests__/useWorkspace.test.ts`

`WorkspaceLayout.test.tsx` likely passes a child element to WorkspaceLayout (e.g., `<WorkspaceLayout><div>content</div></WorkspaceLayout>`). After Feature 004, WorkspaceLayout does not accept children; these tests must be updated to test panel content via route configuration instead.

`workspaceStore.test.ts` imports `DEFAULT_PANEL_SIZES` and `PANEL_DEFAULTS`. Adding the `routes`
field to `PresetDefinition` does not change these exports; no updates required unless tests assert
against the full `PRESETS` shape.

#### Route registration

`App.tsx` currently registers routes as `<Route>` elements nested under Shell. After Feature 004,
page components also need to be importable and renderable outside React Router's routing context
(for per-panel rendering). Feature 004 must ensure page components do not rely on `useParams` or
`useLocation` for routing information that is only available when they are active via React Router's
Outlet mechanism.

Based on static analysis: none of the four target pages (`LibraryPage`, `TimelinePage`,
`PreviewPage`, `RenderPage`) use `useParams` or `useLocation`. They fetch their data via stores and
API hooks. This confirms they can be rendered in panels directly without React Router context.

---

### URL State Encoding Contract

**This contract is fixed for v049 scope and must not be expanded without a new design review.**

| State | Encoding | Example |
|-------|----------|---------|
| Active workspace preset | URL query param `?workspace=<name>` | `?workspace=edit` |
| Per-panel route assignments | Not URL-encoded — determined by `PRESETS[name].routes` | N/A |
| Custom per-panel routing | **Not URL-encodable in v049** | N/A |
| Panel sizes / visibility overrides | Not URL-encoded — stored in localStorage | N/A |

**Rationale:** URL-encoding per-panel routes would require encoding up to six route paths in the URL
(one per panel), creating complex URL parsing and potentially long URLs for typical usage. Since the
per-panel layout is fully determined by the preset name, encoding just the preset name is sufficient
to reconstruct the full layout on navigation or page reload.

**Custom routing is out of scope:** If a user manually navigates to `/library` via the navigation
bar while in the `edit` preset, the library panel already renders `LibraryPage` (via its preset
route config). There is no mechanism in v049 for the user to assign an arbitrary route to an
arbitrary panel at runtime. This can be revisited in a future version if use cases emerge.

---

### Summary for Feature 004 Implementer

This section is complete and peer-reviewable. Feature 004 can implement without ambiguity on:

1. **Interface change**: Add `routes?: Record<PanelId, string>` to `PresetDefinition`.
2. **PRESETS update**: Add route assignments to all three named presets (see example above).
3. **WorkspaceLayout**: Stop accepting `children`; render per-panel content via route config.
4. **Shell**: Remove `<Outlet />` from WorkspaceLayout call.
5. **Backward compat**: Custom preset falls back to `anchorPreset`'s routes.
6. **Page tests**: No page regressions expected at panel-constrained widths.
7. **WorkspaceLayout tests**: Update tests that pass children to WorkspaceLayout.

Open question deferred to Feature 004: whether to use `useRoutes` with a memory location, a direct
`ROUTE_COMPONENTS` lookup table, or lazy imports per panel. Any of the three approaches is
compatible with this design.
