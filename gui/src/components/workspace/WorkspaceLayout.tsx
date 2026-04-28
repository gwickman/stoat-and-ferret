import { useEffect, useRef } from 'react'
import { Group, Panel, Separator } from 'react-resizable-panels'
import type { ReactNode } from 'react'
import { useWorkspace } from '../../hooks/useWorkspace'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import type { PanelId } from '../../stores/workspaceStore'

interface WorkspacePanelProps {
  panelId: PanelId
  label: string
  minSize?: number
  guardRef: React.MutableRefObject<boolean>
  children?: ReactNode
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
      >
        {children ?? (
          <div className="flex h-full items-center justify-center text-sm text-gray-300">
            {label}
          </div>
        )}
      </div>
    </Panel>
  )
}

const RESIZE_HANDLE_CLASS =
  'group flex items-center justify-center bg-gray-800 hover:bg-blue-600/70 active:bg-blue-500 transition-colors data-[separator]:h-full data-[separator]:w-1 data-[orientation=vertical]:w-full data-[orientation=vertical]:h-1'

interface WorkspaceLayoutProps {
  /** Content rendered inside the preview/main panel — typically a routed Outlet. */
  children?: ReactNode
}

/**
 * Root workspace layout. Wraps the canonical six panels (library, timeline,
 * effects, preview, render-queue, batch) in nested resizable groups and
 * persists size/visibility through workspaceStore (BL-291). The `preview`
 * panel hosts the routed Outlet so existing pages render at full width when
 * other panels are hidden.
 *
 * Separators between panels are conditionally rendered: a separator is omitted
 * when either neighbouring panel is hidden, which prevents stacked zero-width
 * separators from claiming pointer events for routed content (a regression
 * observed during BL-291's UAT cycle).
 */
export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  const visibility = useWorkspace().panelVisibility
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

  // Skip a separator if either of the adjacent panels is hidden — keeps the
  // total separator width within the visible portion of the group, preventing
  // stacked zero-width separators from intercepting routed clicks.
  const showLibrarySep = visibility.library
  const showRightSep = visibility['render-queue'] || visibility.batch
  const showTimelineEffectsSep = visibility.timeline && visibility.effects
  const showRenderBatchSep = visibility['render-queue'] && visibility.batch
  const showTopPreviewSep = (visibility.timeline || visibility.effects) && visibility.preview

  return (
    <div className="h-full w-full" data-testid="workspace-layout">
      <Group
        id="workspace-root"
        orientation="horizontal"
        className="h-full w-full bg-gray-950"
      >
        <WorkspacePanel panelId="library" label="Library" minSize={10} guardRef={guardRef} />

        {showLibrarySep && (
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
                />
                {showTimelineEffectsSep && (
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
                />
              </Group>
            </Panel>

            {showTopPreviewSep && (
              <Separator
                id="sep-top-preview"
                className={RESIZE_HANDLE_CLASS}
                aria-label="Resize preview panel"
              />
            )}

            <WorkspacePanel panelId="preview" label="Preview" minSize={20} guardRef={guardRef}>
              {children}
            </WorkspacePanel>
          </Group>
        </Panel>

        {showRightSep && (
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
            />
            {showRenderBatchSep && (
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
            />
          </Group>
        </Panel>
      </Group>
    </div>
  )
}
