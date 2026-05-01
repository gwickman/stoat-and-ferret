import { useEffect, useRef } from 'react'
import { Group, Panel, Separator } from 'react-resizable-panels'
import type { ComponentType } from 'react'
import { useWorkspace } from '../../hooks/useWorkspace'
import { PRESETS, useWorkspaceStore } from '../../stores/workspaceStore'
import type { PanelId, PanelSizes, PanelVisibility } from '../../stores/workspaceStore'
import DashboardPage from '../../pages/DashboardPage'
import EffectsPage from '../../pages/EffectsPage'
import LibraryPage from '../../pages/LibraryPage'
import PreviewPage from '../../pages/PreviewPage'
import RenderPage from '../../pages/RenderPage'
import TimelinePage from '../../pages/TimelinePage'

/** Route path → page component mapping for per-panel rendering. */
const ROUTE_COMPONENTS: Record<string, ComponentType> = {
  '/library': LibraryPage,
  '/timeline': TimelinePage,
  '/preview': PreviewPage,
  '/render': RenderPage,
  '/effects': EffectsPage,
  '/': DashboardPage,
}

function PanelContent({ route }: { route: string }) {
  const Component = ROUTE_COMPONENTS[route]
  if (!Component) return null
  return <Component />
}

/**
 * Convert workspaceStore panel sizes (percentages of the whole layout) into
 * per-group relative sizes that react-resizable-panels expects (each Panel's
 * size is a percentage of its parent Group, not of the whole layout).
 *
 * Layout topology:
 *   - root horizontal Group: library | workspace-main | workspace-right
 *   - main vertical Group: workspace-top | preview
 *   - top horizontal Group: timeline | effects
 *   - right vertical Group: render-queue | batch
 */
interface RelativeSizes {
  library: number
  main: number
  right: number
  top: number
  preview: number
  timeline: number
  effects: number
  'render-queue': number
  batch: number
}

function computeRelativeSizes(
  panelSizes: PanelSizes,
  panelVisibility: PanelVisibility,
): RelativeSizes {
  const lib = panelVisibility.library ? panelSizes.library : 0
  const rq = panelVisibility['render-queue'] ? panelSizes['render-queue'] : 0
  const bat = panelVisibility.batch ? panelSizes.batch : 0
  const tim = panelVisibility.timeline ? panelSizes.timeline : 0
  const eff = panelVisibility.effects ? panelSizes.effects : 0
  const prev = panelVisibility.preview ? panelSizes.preview : 0

  const rightTotal = rq + bat
  const mainTotal = Math.max(0, 100 - lib - rightTotal)
  const topTotal = tim + eff
  const previewInMain = mainTotal > 0 ? Math.min(100, (prev / mainTotal) * 100) : 0
  const topInMain = Math.max(0, 100 - previewInMain)

  return {
    library: lib,
    main: mainTotal,
    right: rightTotal,
    top: topInMain,
    preview: previewInMain,
    timeline: topTotal > 0 ? (tim / topTotal) * 100 : 50,
    effects: topTotal > 0 ? (eff / topTotal) * 100 : 50,
    'render-queue': rightTotal > 0 ? (rq / rightTotal) * 100 : 50,
    batch: rightTotal > 0 ? (bat / rightTotal) * 100 : 50,
  }
}

interface WorkspacePanelProps {
  panelId: PanelId
  label: string
  minSize?: number
  guardRef: React.MutableRefObject<boolean>
  defaultSize: number
  children?: React.ReactNode
}

/**
 * Single workspace panel. When the panel is hidden (visibility=false), the
 * inner content uses CSS `display: none` (LRN-140 — preserve component state)
 * and the outer Panel is collapsed to a zero-width slot so the surrounding
 * layout reclaims the space without DOM removal.
 */
function WorkspacePanel({
  panelId,
  label,
  minSize = 10,
  guardRef,
  defaultSize,
  children,
}: WorkspacePanelProps) {
  const { panelVisibility, resizePanel } = useWorkspace()
  const isVisible = panelVisibility[panelId] !== false
  const min = isVisible ? minSize : 0

  return (
    <Panel
      id={panelId}
      defaultSize={defaultSize}
      minSize={min}
      onResize={(value) => {
        if (!isVisible) return
        // BL-292 NFR-002: skip while a preset is being applied so the transient
        // resize callbacks fired by react-resizable-panels do not flip preset
        // back to 'custom'.
        if (guardRef.current) return
        resizePanel(panelId, value.asPercentage)
      }}
      className="h-full overflow-hidden"
      data-panel-id={panelId}
    >
      <div
        className="h-full w-full overflow-auto"
        data-testid={`workspace-panel-${panelId}`}
        data-visible={isVisible ? 'true' : 'false'}
        style={isVisible ? undefined : { display: 'none', pointerEvents: 'none' }}
        tabIndex={isVisible ? 0 : undefined}
      >
        {/*
         * Hidden panels render an empty wrapper (display:none) — the
         * placeholder label below would otherwise contribute searchable text
         * to the DOM and collide with routed page headings (e.g.,
         * `getByText("Library")` matching both the panel placeholder and the
         * library page heading).
         */}
        {isVisible &&
          (children ?? (
            <div className="flex h-full items-center justify-center text-sm text-gray-300">
              {label}
            </div>
          ))}
      </div>
    </Panel>
  )
}

// Separator sizing keys off `aria-orientation` (set by react-resizable-panels)
// rather than `data-orientation`. Within a horizontal Group the separator's
// orientation is "vertical" (a vertical line dividing left/right panels) and
// must be 1px wide × full height. Within a vertical Group the separator's
// orientation is "horizontal" (a horizontal line dividing top/bottom panels)
// and must be full width × 1px tall. The earlier `data-[orientation=...]`
// selectors silently never matched, leaving every separator at full height
// — which collapses neighbouring panels in vertical Groups (BL-322).
const RESIZE_HANDLE_CLASS =
  'group flex items-center justify-center bg-gray-800 hover:bg-blue-600/70 active:bg-blue-500 transition-colors aria-[orientation=vertical]:h-full aria-[orientation=vertical]:w-1 aria-[orientation=horizontal]:w-full aria-[orientation=horizontal]:h-1'

/**
 * Root workspace layout. Wraps the canonical six panels (library, timeline,
 * effects, preview, render-queue, batch) in nested resizable groups and
 * persists size/visibility through workspaceStore (BL-291). Each panel
 * renders its configured page component from PRESETS[preset].routes (BL-306).
 *
 * Separators between panels are conditionally rendered: a separator is omitted
 * when either neighbouring panel is hidden, which prevents stacked zero-width
 * separators from claiming pointer events for routed content (a regression
 * observed during BL-291's UAT cycle).
 *
 * Layout remount strategy (BL-322): react-resizable-panels' Panel uses
 * `defaultSize` only on first mount and ignores subsequent prop updates.
 * Calls to the imperative `setLayout` for nested Panels (e.g., the
 * workspace-top Panel containing timeline+effects) are also rejected when the
 * parent's children have changed minSize constraints. The pragmatic fix is to
 * remount the entire Group tree by changing its key whenever the preset or
 * visibility set changes — every Panel mounts fresh with the correct
 * `defaultSize`. Page components inside the panels keep their state via
 * zustand stores, so remount does not lose user data.
 */
export default function WorkspaceLayout() {
  const visibility = useWorkspace().panelVisibility
  const panelSizes = useWorkspace().panelSizes
  const preset = useWorkspaceStore((s) => s.preset)
  const anchorPreset = useWorkspaceStore((s) => s.anchorPreset)

  // Resolve effective preset for route lookup: custom falls back to anchorPreset.
  const effectivePreset = preset === 'custom' ? anchorPreset : preset
  const routes = PRESETS[effectivePreset]?.routes

  // Bidirectional-loop guard (LRN-141 / BL-292 NFR-002). Suppresses transient
  // onResize callbacks fired by react-resizable-panels during layout remounts
  // so they do not feed back into the store as user drags.
  //
  // The guard window must outlast react-resizable-panels' internal layout
  // settle. Empirically (BL-322 deep-link path), the layout-induced onResize
  // can fire 25-30ms after a setPreset call. We use a 300ms setTimeout
  // fallback to cover this window without coupling to browser frame timing.
  const guardRef = useRef(false)
  const guardTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prevPresetRef = useRef(useWorkspaceStore.getState().preset)
  const prevVisibilityRef = useRef(useWorkspaceStore.getState().panelVisibility)

  useEffect(() => {
    prevPresetRef.current = useWorkspaceStore.getState().preset
    prevVisibilityRef.current = useWorkspaceStore.getState().panelVisibility

    const fireGuard = () => {
      guardRef.current = true
      if (guardTimerRef.current) clearTimeout(guardTimerRef.current)
      guardTimerRef.current = setTimeout(() => {
        guardRef.current = false
        guardTimerRef.current = null
      }, 300)
    }

    const unsubscribe = useWorkspaceStore.subscribe((state) => {
      const presetChanged = state.preset !== prevPresetRef.current
      const visibilityChanged = state.panelVisibility !== prevVisibilityRef.current
      prevPresetRef.current = state.preset
      prevVisibilityRef.current = state.panelVisibility
      if (presetChanged || visibilityChanged) {
        fireGuard()
      }
    })

    return () => {
      unsubscribe()
      if (guardTimerRef.current) clearTimeout(guardTimerRef.current)
    }
  }, [])

  // Separator culling: separators adjacent to hidden panels are excluded from
  // the DOM. react-resizable-panels v4.10.0 always overrides tabIndex after
  // rest prop spread, making tabIndex={-1} inert — DOM removal is the only
  // mechanism for WCAG-compliant tab order management (BL-305).
  const librarySepVisible = visibility.library
  const rightPanelSepVisible = visibility['render-queue'] || visibility.batch
  const timelineEffectsSepVisible = visibility.timeline && visibility.effects
  const renderBatchSepVisible = visibility['render-queue'] && visibility.batch
  const topPreviewSepVisible = (visibility.timeline || visibility.effects) && visibility.preview

  const sizes = computeRelativeSizes(panelSizes, visibility)

  // Remount the entire Group tree on preset/visibility change. See JSDoc above.
  const layoutKey = `${effectivePreset}|${[
    visibility.library,
    visibility.timeline,
    visibility.preview,
    visibility.effects,
    visibility['render-queue'],
    visibility.batch,
  ].join(',')}`

  return (
    <div className="h-full w-full" data-testid="workspace-layout">
      <Group
        id="workspace-root"
        key={layoutKey}
        orientation="horizontal"
        className="h-full w-full bg-gray-950"
        defaultLayout={{
          library: sizes.library,
          'workspace-main': sizes.main,
          'workspace-right': sizes.right,
        }}
      >
        <WorkspacePanel
          panelId="library"
          label="Library"
          minSize={10}
          guardRef={guardRef}
          defaultSize={sizes.library}
        >
          {routes?.library ? <PanelContent route={routes.library} /> : undefined}
        </WorkspacePanel>

        {librarySepVisible && (
          <Separator
            id="sep-library-main"
            className={RESIZE_HANDLE_CLASS}
            aria-label="Resize library panel"
          />
        )}

        <Panel
          id="workspace-main"
          defaultSize={sizes.main}
          minSize={30}
          className="flex h-full min-h-0 flex-col overflow-hidden"
          style={{ height: '100%' }}
        >
          <Group
            id="workspace-main-vertical"
            orientation="vertical"
            className="h-full w-full"
            defaultLayout={{
              'workspace-top': sizes.top,
              preview: sizes.preview,
            }}
          >
            <Panel
              id="workspace-top"
              defaultSize={sizes.top}
              minSize={0}
              className="flex h-full min-h-0 flex-col overflow-hidden"
          style={{ height: '100%' }}
            >
              <Group
                id="workspace-top-horizontal"
                orientation="horizontal"
                className="h-full w-full"
                defaultLayout={{
                  timeline: sizes.timeline,
                  effects: sizes.effects,
                }}
              >
                <WorkspacePanel
                  panelId="timeline"
                  label="Timeline"
                  minSize={15}
                  guardRef={guardRef}
                  defaultSize={sizes.timeline}
                >
                  {routes?.timeline ? <PanelContent route={routes.timeline} /> : undefined}
                </WorkspacePanel>
                {timelineEffectsSepVisible && (
                  <Separator
                    id="sep-timeline-effects"
                    className={RESIZE_HANDLE_CLASS}
                    aria-label="Resize timeline panel"
                  />
                )}
                <WorkspacePanel
                  panelId="effects"
                  label="Effects"
                  minSize={15}
                  guardRef={guardRef}
                  defaultSize={sizes.effects}
                >
                  {routes?.effects ? <PanelContent route={routes.effects} /> : undefined}
                </WorkspacePanel>
              </Group>
            </Panel>

            {topPreviewSepVisible && (
              <Separator
                id="sep-top-preview"
                className={RESIZE_HANDLE_CLASS}
                aria-label="Resize preview panel"
              />
            )}

            <WorkspacePanel
              panelId="preview"
              label="Preview"
              minSize={20}
              guardRef={guardRef}
              defaultSize={sizes.preview}
            >
              {routes?.preview ? <PanelContent route={routes.preview} /> : undefined}
            </WorkspacePanel>
          </Group>
        </Panel>

        {rightPanelSepVisible && (
          <Separator
            id="sep-main-right"
            className={RESIZE_HANDLE_CLASS}
            aria-label="Resize render-queue panel"
          />
        )}

        <Panel
          id="workspace-right"
          defaultSize={sizes.right}
          minSize={0}
          className="flex h-full min-h-0 flex-col overflow-hidden"
          style={{ height: '100%' }}
        >
          <Group
            id="workspace-right-vertical"
            orientation="vertical"
            className="h-full w-full"
            defaultLayout={{
              'render-queue': sizes['render-queue'],
              batch: sizes.batch,
            }}
          >
            <WorkspacePanel
              panelId="render-queue"
              label="Render Queue"
              minSize={15}
              guardRef={guardRef}
              defaultSize={sizes['render-queue']}
            >
              {routes?.['render-queue'] ? <PanelContent route={routes['render-queue']} /> : undefined}
            </WorkspacePanel>
            {renderBatchSepVisible && (
              <Separator
                id="sep-render-batch"
                className={RESIZE_HANDLE_CLASS}
                aria-label="Resize batch panel"
              />
            )}
            <WorkspacePanel
              panelId="batch"
              label="Batch"
              minSize={15}
              guardRef={guardRef}
              defaultSize={sizes.batch}
            >
              {routes?.batch ? <PanelContent route={routes.batch} /> : undefined}
            </WorkspacePanel>
          </Group>
        </Panel>
      </Group>
    </div>
  )
}
