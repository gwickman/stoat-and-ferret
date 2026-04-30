import { useEffect, useRef } from 'react'
import { Group, Panel, Separator } from 'react-resizable-panels'
import type { ComponentType } from 'react'
import { useWorkspace } from '../../hooks/useWorkspace'
import { PRESETS, useWorkspaceStore } from '../../stores/workspaceStore'
import type { PanelId } from '../../stores/workspaceStore'
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

interface WorkspacePanelProps {
  panelId: PanelId
  label: string
  minSize?: number
  guardRef: React.MutableRefObject<boolean>
  children?: React.ReactNode
}

/**
 * Single workspace panel. When the panel is hidden (visibility=false), the
 * inner content uses CSS `display: none` (LRN-140 — preserve component state)
 * and the outer Panel is collapsed to a zero-width slot so the surrounding
 * layout reclaims the space without DOM removal.
 */
function WorkspacePanel({ panelId, label, minSize = 10, guardRef, children }: WorkspacePanelProps) {
  const { panelSizes, panelVisibility, resizePanel } = useWorkspace()
  const isVisible = panelVisibility[panelId] !== false
  const size = isVisible ? panelSizes[panelId] : 0
  const min = isVisible ? minSize : 0

  return (
    <Panel
      id={panelId}
      defaultSize={size}
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

const RESIZE_HANDLE_CLASS =
  'group flex items-center justify-center bg-gray-800 hover:bg-blue-600/70 active:bg-blue-500 transition-colors data-[separator]:h-full data-[separator]:w-1 data-[orientation=vertical]:w-full data-[orientation=vertical]:h-1'

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
 */
export default function WorkspaceLayout() {
  const visibility = useWorkspace().panelVisibility
  const preset = useWorkspaceStore((s) => s.preset)
  const anchorPreset = useWorkspaceStore((s) => s.anchorPreset)

  // Resolve effective preset for route lookup: custom falls back to anchorPreset.
  const effectivePreset = preset === 'custom' ? anchorPreset : preset
  const routes = PRESETS[effectivePreset]?.routes

  // Bidirectional-loop guard (LRN-141 / BL-292 NFR-002). When `preset` changes
  // via `setPreset` we set the flag synchronously so the transient `onResize`
  // callbacks fired by react-resizable-panels do not feed back into the store.
  const guardRef = useRef(false)
  const prevPresetRef = useRef<string | null>(null)

  useEffect(() => {
    // Subscribe directly to the store so we can flip the guard before React
    // commits the preset-driven re-render.
    return useWorkspaceStore.subscribe((state) => {
      if (prevPresetRef.current === null) {
        prevPresetRef.current = state.preset
        return
      }
      if (state.preset !== prevPresetRef.current) {
        prevPresetRef.current = state.preset
        guardRef.current = true
        // Release the guard after layout has settled. Two RAFs gives
        // react-resizable-panels' internal observers time to flush.
        if (typeof requestAnimationFrame === 'function') {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              guardRef.current = false
            })
          })
        } else {
          guardRef.current = false
        }
      }
    })
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

  return (
    <div className="h-full w-full" data-testid="workspace-layout">
      <Group
        id="workspace-root"
        orientation="horizontal"
        className="h-full w-full bg-gray-950"
      >
        <WorkspacePanel panelId="library" label="Library" minSize={10} guardRef={guardRef}>
          {routes?.library ? <PanelContent route={routes.library} /> : undefined}
        </WorkspacePanel>

        {librarySepVisible && (
          <Separator
            id="sep-library-main"
            className={RESIZE_HANDLE_CLASS}
            aria-label="Resize library panel"
          />
        )}

        <Panel id="workspace-main" minSize={30} className="h-full overflow-hidden">
          <Group id="workspace-main-vertical" orientation="vertical" className="h-full w-full">
            <Panel id="workspace-top" minSize={0} className="overflow-hidden">
              <Group id="workspace-top-horizontal" orientation="horizontal" className="h-full w-full">
                <WorkspacePanel
                  panelId="timeline"
                  label="Timeline"
                  minSize={15}
                  guardRef={guardRef}
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

            <WorkspacePanel panelId="preview" label="Preview" minSize={20} guardRef={guardRef}>
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

        <Panel id="workspace-right" minSize={0} className="h-full overflow-hidden">
          <Group id="workspace-right-vertical" orientation="vertical" className="h-full w-full">
            <WorkspacePanel
              panelId="render-queue"
              label="Render Queue"
              minSize={15}
              guardRef={guardRef}
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
            >
              {routes?.batch ? <PanelContent route={routes.batch} /> : undefined}
            </WorkspacePanel>
          </Group>
        </Panel>
      </Group>
    </div>
  )
}
